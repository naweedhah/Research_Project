"""Integration status, C2 stubs, C3/C4 contracts, and inbound C4 model proposals."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.integrations.c2 import client as c2_client
from app.integrations.c3 import client as c3_client
from app.integrations.c4 import client as c4_client
from app.integrations.common.auth import require_c4_token
from app.integrations.common.contracts import C4ModelUpdateProposalV1, IntegrationContractError
from app.integrations.common.enqueue import enqueue_c3_reassessment_for_review
from app.integrations.common.outbox import enqueue_integration_event, kick_delivery_best_effort, pop_scheduled_delivery_ids
from app.models.enums import (
    AuditAction,
    C3RequestStatus,
    IntegrationDeliveryStatus,
    IntegrationEventType,
    ModelStatus,
    NotificationChannel,
)
from app.models.intelligence import ModelVersion
from app.models.operations import C3ReassessmentRequest, IntegrationEvent, Notification
from app.models.paediatric import Child, Visit
from app.security.rbac import assert_child_access
from app.schemas.common import CounterfactualRequest
from app.services.audit import write_audit
from app.services.clinician_review import active_prediction_for_visit, get_review_for_visit

router = APIRouter(tags=["integrations"])


def _component_runtime_status(target: str, *, configured: bool, url: str) -> dict:
    settings = get_settings()
    db_counts_pending = 0
    db_counts_failed = 0
    last_success = None
    # Counts filled by callers with a session when available
    if not url or settings.integration_mode.lower() == "mock":
        status = "NOT_CONFIGURED"
    elif not configured:
        status = "NOT_CONFIGURED"
    else:
        status = "CONNECTED"
    return {
        "configured": bool(url) and settings.integration_mode.lower() != "mock",
        "status": status,
        "base_url_configured": bool(url),
        "mode": settings.integration_mode,
        "pending_events": db_counts_pending,
        "failed_events": db_counts_failed,
        "last_success_at": last_success,
    }


def _enrich_status(db: Session, target: str, base: dict) -> dict:
    pending = (
        db.scalar(
            select(func.count())
            .select_from(IntegrationEvent)
            .where(
                IntegrationEvent.target == target,
                IntegrationEvent.delivery_status.in_(
                    [IntegrationDeliveryStatus.PENDING, IntegrationDeliveryStatus.FAILED_RETRYABLE]
                ),
            )
        )
        or 0
    )
    failed = (
        db.scalar(
            select(func.count())
            .select_from(IntegrationEvent)
            .where(
                IntegrationEvent.target == target,
                IntegrationEvent.delivery_status == IntegrationDeliveryStatus.FAILED_FINAL,
            )
        )
        or 0
    )
    last = db.scalar(
        select(IntegrationEvent)
        .where(IntegrationEvent.target == target, IntegrationEvent.delivery_status == IntegrationDeliveryStatus.DELIVERED)
        .order_by(IntegrationEvent.delivered_at.desc())
        .limit(1)
    )
    base["pending_events"] = int(pending)
    base["failed_events"] = int(failed)
    base["last_success_at"] = last.delivered_at.isoformat() if last and last.delivered_at else None
    if base["configured"]:
        if failed and pending:
            base["status"] = "DEGRADED"
        elif pending > 10:
            base["status"] = "DEGRADED"
        else:
            # If recent deliveries failed retryably without success, mark degraded/offline
            recent_fail = db.scalar(
                select(IntegrationEvent)
                .where(
                    IntegrationEvent.target == target,
                    IntegrationEvent.delivery_status == IntegrationDeliveryStatus.FAILED_RETRYABLE,
                )
                .order_by(IntegrationEvent.last_attempt_at.desc().nullslast())
                .limit(1)
            )
            if recent_fail and (not last or (recent_fail.last_attempt_at and last.delivered_at and recent_fail.last_attempt_at > last.delivered_at)):
                base["status"] = "OFFLINE" if pending else "DEGRADED"
            else:
                base["status"] = "CONNECTED"
    return base


@router.get("/integrations/status")
def integrations_status(db: Session = Depends(get_db), current=Depends(require_permission("admin:system", "research:read"))):
    settings = get_settings()
    c3 = _enrich_status(
        db,
        "c3",
        _component_runtime_status("c3", configured=c3_client.is_configured(), url=settings.c3_counterfactual_url),
    )
    c4 = _enrich_status(
        db,
        "c4",
        _component_runtime_status("c4", configured=c4_client.is_configured(), url=settings.c4_drift_url),
    )
    c2 = {
        "configured": bool(settings.c2_explainability_url) and settings.integration_mode.lower() != "mock",
        "status": "CONNECTED" if settings.c2_explainability_url and settings.integration_mode.lower() != "mock" else "NOT_CONFIGURED",
        "message": c2_client.MESSAGE if not settings.c2_explainability_url else "Component 2 endpoint configured",
    }
    return {"c2": c2, "c3": c3, "c4": c4, "integration_mode": settings.integration_mode}


@router.get("/children/{child_id}/c3-reassessment")
def child_c3_reassessment(child_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    row = db.scalar(
        select(C3ReassessmentRequest)
        .where(C3ReassessmentRequest.child_id == child_id)
        .order_by(C3ReassessmentRequest.requested_at.desc())
        .limit(1)
    )
    settings = get_settings()
    connected = c3_client.is_configured()
    if row is None:
        return {
            "connected": connected,
            "configured": bool(settings.c3_counterfactual_url),
            "request": None,
            "message": "Component 3 not connected" if not connected else "No intervention reassessment requested",
        }
    return {
        "connected": connected,
        "configured": bool(settings.c3_counterfactual_url),
        "request": {
            "id": str(row.id),
            "status": row.status.value,
            "requested_at": row.requested_at.isoformat() if row.requested_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "result_url": row.result_url,
            "result_ref": row.result_ref,
            "external_request_id": row.external_request_id,
            "last_error": row.last_error,
            "queued_offline": (not connected) and row.status == C3RequestStatus.QUEUED,
        },
        "message": (
            "Request queued. Component 3 is temporarily unavailable. The clinical review was saved successfully."
            if (not connected and row.status == C3RequestStatus.QUEUED)
            else None
        ),
    }


@router.post("/integrations/counterfactual/request")
def request_counterfactual(
    body: CounterfactualRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current=Depends(require_permission("integration:request")),
):
    """Manual C3 trigger (legacy). Prefer clinician workflow REQUEST_INTERVENTION_REASSESSMENT."""
    visit = db.get(Visit, body.visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    prediction = active_prediction_for_visit(db, visit.id)
    if prediction is None:
        raise HTTPException(422, "No active prediction for visit")
    model = db.get(ModelVersion, prediction.model_version_id)
    review = get_review_for_visit(db, visit.id)
    if review is None or model is None:
        # Fall back to enqueueing a raw typed event without review linkage
        from app.integrations.c3.mapper import build_c3_reassessment_payload
        from app.models.operations import ClinicianReview
        from app.models.enums import ClinicianAssessment, ClinicianReviewState, ClinicianWorkflowAction

        # Create ephemeral mapper input using a lightweight namespace-like review if missing
        if review is None:
            raise HTTPException(422, "Complete a clinician review with Request Intervention Reassessment first")
    assert model is not None and review is not None
    row = enqueue_c3_reassessment_for_review(
        db, child=child, visit=visit, prediction=prediction, model=model, review=review, user_id=current.id
    )
    deliver_ids = pop_scheduled_delivery_ids(db)
    if deliver_ids:
        background_tasks.add_task(kick_delivery_best_effort, deliver_ids)
    write_audit(
        db,
        action=AuditAction.REASSESSMENT_REQUESTED,
        resource_type="integration",
        resource_id=str(row.id) if row else None,
        user_id=current.id,
        role=current.role.value,
        ip=request.client.host if request.client else None,
        metadata={"trigger": body.trigger, "child_id": body.child_id},
    )
    return {
        "status": "queued",
        "c3_request_id": str(row.id) if row else None,
        "adapter": "c3" if c3_client.is_configured() else "mock",
        "message": None if c3_client.is_configured() else c3_client.MESSAGE_NOT_CONNECTED,
    }


@router.get("/integrations/explainability/status")
def explainability_status(current=Depends(require_permission("child:read"))):
    """C2 connection state. Does not generate SHAP or feature attributions."""
    settings = get_settings()
    connected = bool(settings.c2_explainability_url) and settings.integration_mode.lower() != "mock"
    from app.services.model_display import get_model_output_display_metadata

    semantics = get_model_output_display_metadata()
    return {
        "owner": "c2",
        "connected": connected,
        "shap_available": False,
        "fusion_attention_available": False,
        "message": "Component 2 is configured." if connected else c2_client.MESSAGE,
        "fusion_attention_message": "Cross-attention weights are not stored for this visit.",
        "task": semantics["prediction_task_label"],
        "prediction_task": semantics["prediction_task"],
    }


@router.post("/integrations/explainability/request")
def request_explainability(visit_id: str, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    settings = get_settings()
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    payload = {"visit_id": visit_id, "model_inputs": "approved_feature_schema", "component": "c2", "explanation_context_ref": None}
    event = enqueue_integration_event(
        db,
        event_type=IntegrationEventType.EXPLAINABILITY_REQUESTED,
        target="c2",
        payload=payload,
        idempotency_key=f"c2-explain:{visit_id}",
    )
    return {
        "event_id": str(event.id),
        "connected": bool(settings.c2_explainability_url) and settings.integration_mode.lower() != "mock",
        "shap_available": False,
        "message": c2_client.MESSAGE,
    }


@router.post("/integrations/c4/model-update-proposals", dependencies=[Depends(require_c4_token)])
def receive_c4_model_update_proposal(
    body: dict,
    db: Session = Depends(get_db),
):
    """Inbound C4 proposal. Registers CANDIDATE only — never auto-activates."""
    try:
        proposal = C4ModelUpdateProposalV1.model_validate(body)
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, IntegrationContractError):
            raise HTTPException(422, str(exc)) from exc
        raise HTTPException(422, f"Invalid C4 model-update proposal: {exc}") from exc

    # Compatibility vs active model
    active = db.scalar(select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE).limit(1))
    if active is None:
        raise HTTPException(503, "No active model to compare compatibility against")
    if proposal.feature_schema_version != active.feature_schema_version:
        raise HTTPException(
            409,
            f"Incompatible feature_schema_version: proposed={proposal.feature_schema_version} active={active.feature_schema_version}",
        )
    if proposal.label_schema_version != active.label_schema_version:
        raise HTTPException(
            409,
            f"Incompatible label_schema_version: proposed={proposal.label_schema_version} active={active.label_schema_version}",
        )
    if proposal.embedding_dimension is not None and proposal.embedding_dimension != active.embedding_dimension:
        raise HTTPException(409, "Incompatible embedding_dimension")
    artifact = proposal.artifact or {}
    if not artifact.get("uri") or not artifact.get("sha256"):
        raise HTTPException(422, "artifact.uri and artifact.sha256 are required")

    # Parse model_key-version
    version_label = proposal.model_version
    if "-" in version_label:
        model_key, version = version_label.rsplit("-", 1)
    else:
        model_key, version = "MCA", version_label

    existing = db.scalar(
        select(ModelVersion).where(ModelVersion.model_key == model_key, ModelVersion.version == version)
    )
    if existing is not None:
        if existing.status == ModelStatus.ACTIVE:
            raise HTTPException(409, "Proposed model version is already ACTIVE")
        existing.status = ModelStatus.CANDIDATE
        existing.artifact_path = artifact.get("uri")
        existing.artifact_checksum = artifact.get("sha256")
        existing.notes = (existing.notes or "") + f"\nC4 proposal {proposal.c4_decision_id}"
        candidate = existing
    else:
        candidate = ModelVersion(
            id=uuid4(),
            model_key=model_key,
            version=version,
            architecture=active.architecture,
            feature_schema_version=proposal.feature_schema_version,
            label_schema_version=proposal.label_schema_version,
            calibration_version=proposal.calibration_version,
            embedding_dimension=proposal.embedding_dimension or active.embedding_dimension,
            embedding_space_id=proposal.embedding_space_id,
            artifact_path=artifact.get("uri"),
            artifact_checksum=artifact.get("sha256"),
            status=ModelStatus.CANDIDATE,
            is_demo=False,
            notes=f"Registered from C4 proposal {proposal.c4_decision_id}. Not auto-activated.",
            compatible_with=[f"{active.model_key}-{active.version}"],
        )
        db.add(candidate)
        db.flush()

    enqueue_integration_event(
        db,
        event_type=IntegrationEventType.MODEL_UPDATE_PROPOSED,
        target="internal",
        payload=proposal.model_dump(mode="json"),
        idempotency_key=f"c4-model-proposal:{proposal.c4_decision_id}",
    )
    write_audit(
        db,
        action=AuditAction.C4_MODEL_UPDATE_RECEIVED,
        resource_type="model_version",
        resource_id=str(candidate.id),
        metadata={"c4_decision_id": str(proposal.c4_decision_id), "status": "CANDIDATE"},
    )
    write_audit(
        db,
        action=AuditAction.MODEL_CANDIDATE_REGISTERED,
        resource_type="model_version",
        resource_id=str(candidate.id),
        metadata={"model": f"{candidate.model_key}-{candidate.version}"},
    )
    return {
        "ok": True,
        "model_id": str(candidate.id),
        "status": candidate.status.value,
        "active_model_unchanged": True,
        "message": "Candidate registered. Authorized activation required in C1.",
    }


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), current=Depends(require_permission("child:read", "alert:read", "research:read"))):
    rows = db.scalars(
        select(Notification).where(Notification.user_id == current.id).order_by(Notification.created_at.desc()).limit(50)
    ).all()
    return {
        "items": [
            {
                "id": str(n.id),
                "title": n.title,
                "body": n.body,
                "severity": n.severity,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat(),
                "resource_type": n.resource_type,
                "resource_id": n.resource_id,
            }
            for n in rows
        ]
    }


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, db: Session = Depends(get_db), current=Depends(require_permission("child:read", "alert:read"))):
    row = db.get(Notification, notification_id)
    if not row or row.user_id != current.id:
        raise HTTPException(404, "Notification not found")
    row.read_at = datetime.now(UTC)
    return {"ok": True}


@router.get("/product")
def product():
    from app.core.policy import load_product
    from app.services.model_display import get_model_output_display_metadata

    data = load_product()
    semantics = get_model_output_display_metadata()
    data["model_mode"] = semantics["model_mode"]
    data["clinical_use"] = semantics["clinical_use"]
    data["display_semantics"] = semantics
    return data


@router.get("/integrations/component1/visits/{visit_id}")
def component1_visit_output(
    visit_id: UUID,
    db: Session = Depends(get_db),
    current=Depends(require_permission("child:read")),
):
    """Component 1 prediction contract for C2/C3. Served by the application API only."""
    from app.services.malnutrition_type import component1_output

    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    if child is None:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    prediction = active_prediction_for_visit(db, visit.id)
    if prediction is None:
        raise HTTPException(404, "No active prediction for this visit")
    return component1_output(prediction)


@router.get("/runtime/model-display")
def runtime_model_display(
    db: Session = Depends(get_db),
    current=Depends(require_permission("child:read")),
):
    """Authoritative display semantics for the active inference mode."""
    from app.services.model_display import get_model_output_display_metadata

    model = db.scalar(select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE).limit(1))
    return get_model_output_display_metadata(is_demo=bool(model.is_demo) if model else None)


@router.get("/runtime/ga-rgca")
def runtime_ga_rgca(current=Depends(require_permission("child:read"))):
    """Whether the GA-RGCA v3 weight files are loaded by the inference service."""
    import httpx

    from app.core.config import get_settings

    try:
        response = httpx.get(f"{get_settings().inference_url}/model-info", timeout=5.0)
        response.raise_for_status()
        info = response.json()
    except httpx.HTTPError:
        return {
            "ga_rgca_loaded": False,
            "ga_rgca_error": "Inference service is not reachable",
            "ga_rgca_required_files": [
                "ga_rgca_v3_states.pt",
                "multimodal_preprocessor.joblib",
                "binary_calibrators.joblib",
            ],
        }
    return {
        "ga_rgca_loaded": bool(info.get("ga_rgca_loaded")),
        "ga_rgca_error": info.get("ga_rgca_error"),
        "ga_rgca_required_files": info.get("ga_rgca_required_files") or [],
        "model_version": info.get("model_version"),
        "adapter": info.get("adapter"),
        "active_model": info.get("active_model"),
        "configured_model_mode": info.get("configured_model_mode"),
        "prediction_source": info.get("prediction_source"),
        "ensemble_members": info.get("ensemble_members"),
        "architecture": info.get("architecture"),
        "prediction_type": info.get("prediction_type"),
        "outputs": info.get("outputs"),
        "uncertainty_method": info.get("uncertainty_method"),
        "clinical_use": False,
        "external_validation_complete": False,
        "demo": False,
    }
