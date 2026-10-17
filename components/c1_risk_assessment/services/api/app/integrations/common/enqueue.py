"""Domain-facing integration enqueue helpers (no HTTP in the request path)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.c3.mapper import build_c3_reassessment_payload
from app.integrations.c4.mapper import build_c4_clinician_review_observation, build_c4_prediction_observation
from app.integrations.common.outbox import enqueue_integration_event
from app.models.enums import (
    AuditAction,
    C3RequestStatus,
    ClinicianWorkflowAction,
    IntegrationEventType,
)
from app.models.intelligence import ModelVersion, Prediction
from app.models.operations import C3ReassessmentRequest, ClinicianReview, IntegrationEvent
from app.models.paediatric import Child, Visit
from app.services.audit import write_audit


def enqueue_c4_prediction_observation(
    db: Session,
    *,
    child: Child,
    visit: Visit,
    prediction: Prediction,
    model: ModelVersion,
) -> IntegrationEvent:
    event_id = uuid4()
    correlation_id = uuid4()
    payload = build_c4_prediction_observation(
        db,
        child=child,
        visit=visit,
        prediction=prediction,
        model=model,
        event_id=event_id,
        correlation_id=correlation_id,
    )
    event = enqueue_integration_event(
        db,
        event_type=IntegrationEventType.PREDICTION_COMPLETED,
        target="c4",
        payload=payload,
        idempotency_key=f"c4-prediction:{prediction.id}",
        correlation_id=correlation_id,
    )
    write_audit(
        db,
        action=AuditAction.C4_PREDICTION_OBSERVATION_QUEUED,
        resource_type="integration",
        resource_id=str(event.id),
        facility_id=child.facility_id,
        metadata={"prediction_id": str(prediction.id), "target": "c4"},
    )
    return event


def enqueue_c4_clinician_review_observation(
    db: Session,
    *,
    child: Child,
    visit: Visit,
    prediction: Prediction,
    model: ModelVersion,
    review: ClinicianReview,
) -> IntegrationEvent:
    event_id = uuid4()
    correlation_id = uuid4()
    payload = build_c4_clinician_review_observation(
        child=child,
        visit=visit,
        prediction=prediction,
        model=model,
        review=review,
        event_id=event_id,
        correlation_id=correlation_id,
    )
    return enqueue_integration_event(
        db,
        event_type=IntegrationEventType.CLINICIAN_REVIEW_COMPLETED,
        target="c4",
        payload=payload,
        idempotency_key=f"c4-review:{review.id}",
        correlation_id=correlation_id,
    )


def enqueue_c3_reassessment_for_review(
    db: Session,
    *,
    child: Child,
    visit: Visit,
    prediction: Prediction,
    model: ModelVersion,
    review: ClinicianReview,
    user_id=None,
) -> C3ReassessmentRequest | None:
    if review.workflow_action != ClinicianWorkflowAction.REQUEST_INTERVENTION_REASSESSMENT:
        return None

    existing = db.scalar(
        select(C3ReassessmentRequest).where(C3ReassessmentRequest.clinician_review_id == review.id)
    )
    if existing is not None:
        return existing

    request_row = C3ReassessmentRequest(
        id=uuid4(),
        facility_id=child.facility_id,
        child_id=child.id,
        visit_id=visit.id,
        prediction_id=prediction.id,
        clinician_review_id=review.id,
        status=C3RequestStatus.QUEUED,
        requested_at=datetime.now(UTC),
    )
    db.add(request_row)
    db.flush()

    correlation_id = uuid4()
    payload = build_c3_reassessment_payload(
        db,
        child=child,
        visit=visit,
        prediction=prediction,
        model=model,
        review=review,
        request_id=request_row.id,
        correlation_id=correlation_id,
    )
    payload["c3_request_row_id"] = str(request_row.id)

    event = enqueue_integration_event(
        db,
        event_type=IntegrationEventType.COUNTERFACTUAL_REQUESTED,
        target="c3",
        payload=payload,
        idempotency_key=f"c3-reassessment:{prediction.id}:{review.id}",
        correlation_id=correlation_id,
    )
    request_row.integration_event_id = event.id

    write_audit(
        db,
        action=AuditAction.C3_REASSESSMENT_REQUESTED,
        resource_type="c3_reassessment_request",
        resource_id=str(request_row.id),
        user_id=user_id,
        facility_id=child.facility_id,
        metadata={
            "prediction_id": str(prediction.id),
            "clinician_review_id": str(review.id),
            "event_id": str(event.id),
        },
    )
    return request_row


def enqueue_c4_model_activated(db: Session, *, model: ModelVersion, user_id=None) -> IntegrationEvent:
    correlation_id = uuid4()
    payload = {
        "contract_version": "1.0",
        "event_id": str(uuid4()),
        "event_type": "c1.model.activated",
        "occurred_at": datetime.now(UTC).isoformat(),
        "correlation_id": str(correlation_id),
        "model": {
            "model_version": f"{model.model_key}-{model.version}",
            "feature_schema_version": model.feature_schema_version,
            "label_schema_version": model.label_schema_version,
            "calibration_version": model.calibration_version,
            "embedding_space_id": model.embedding_space_id,
            "status": model.status.value,
        },
    }
    return enqueue_integration_event(
        db,
        event_type=IntegrationEventType.MODEL_ACTIVATED,
        target="c4",
        payload=payload,
        idempotency_key=f"c4-model-activated:{model.id}:{model.activated_at.isoformat() if model.activated_at else 'na'}",
        correlation_id=correlation_id,
    )
