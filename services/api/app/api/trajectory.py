from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.models.intelligence import LatentEmbedding, Prediction, TrajectoryMetric
from app.models.paediatric import Child, Visit
from app.security.rbac import assert_child_access

router = APIRouter(tags=["trajectory"])


@router.get("/children/{child_id}/trajectory")
def trajectory(child_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    visits = db.scalars(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number)).all()
    points = []
    spaces = set()
    for visit in visits:
        emb = db.scalar(select(LatentEmbedding).where(LatentEmbedding.visit_id == visit.id))
        pred = db.scalar(select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True)))
        if not emb or not pred:
            continue
        spaces.add(emb.embedding_space_id)
        points.append(
            {
                "visit_number": visit.visit_number,
                "visit_id": str(visit.id),
                "date": visit.visit_date.isoformat(),
                "x": emb.projection_x,
                "y": emb.projection_y,
                "risk": pred.primary_risk_score,
                "status": pred.status_prediction,
                "severity": pred.severity_prediction,
                "embedding_space_id": emb.embedding_space_id,
                "dimension": emb.embedding_dimension,
                "model_version_id": str(emb.model_version_id),
            }
        )
    warning = None
    if len(spaces) > 1:
        warning = "Model version changed — latent trajectory restarted/re-aligned"
    return {
        "child": child.pseudonymous_id,
        "points": points,
        "warning": warning,
        "disclaimer": (
            "Illustrative 2D latent projection for demonstrating the multi-visit trajectory interface. "
            "This is not PCA or UMAP and has no independent clinical meaning."
        ),
        "projection_label": "Illustrative 2D Latent Projection",
    }


@router.get("/children/{child_id}/risk-history")
def risk_history(child_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    visits = db.scalars(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number)).all()
    series = []
    for visit in visits:
        pred = db.scalar(select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True)))
        metric = db.scalar(select(TrajectoryMetric).where(TrajectoryMetric.to_visit_id == visit.id))
        anthro = visit.anthropometry
        if pred:
            series.append(
                {
                    "visit_number": visit.visit_number,
                    "date": visit.visit_date.isoformat(),
                    "risk": pred.primary_risk_score,
                    "severity": pred.severity_prediction,
                    "status": pred.status_prediction,
                    "progress": metric.progress_state.value if metric else None,
                    "risk_velocity": metric.risk_velocity if metric else None,
                    "weight_kg": anthro.weight_kg if anthro else None,
                    "height_cm": anthro.height_cm if anthro else None,
                    "muac_cm": anthro.muac_cm if anthro else None,
                }
            )
    return {"child": child.pseudonymous_id, "series": series}


@router.get("/children/{child_id}/progress")
def progress(child_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    metric = db.scalar(
        select(TrajectoryMetric).where(TrajectoryMetric.child_id == child_id).order_by(TrajectoryMetric.created_at.desc())
    )
    if not metric:
        return {"child": child.pseudonymous_id, "progress_state": "unknown"}
    return {
        "child": child.pseudonymous_id,
        "progress_state": metric.progress_state.value,
        "risk_velocity": metric.risk_velocity,
        "baseline_recovery_rate": metric.baseline_recovery_rate,
        "current_risk": metric.current_risk,
        "previous_risk": metric.previous_risk,
        "warning": metric.warning,
    }


@router.get("/children/{child_id}/report")
def report(child_id: UUID, request=None, db: Session = Depends(get_db), current=Depends(require_permission("report:export", "child:read"))):
    from app.models.enums import AlertStatus, AuditAction, FollowUpStatus
    from app.models.identity import User
    from app.models.operations import Alert, FollowUpSchedule
    from app.services.audit import write_audit
    from app.services.child_list import active_model_is_demo
    from app.services.clinician_review import get_review_for_visit, serialize_review
    from app.services.model_display import get_model_output_display_metadata

    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    write_audit(
        db,
        action=AuditAction.REPORT_EXPORTED,
        resource_type="child_report",
        resource_id=child.pseudonymous_id,
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
    )
    hist = risk_history(child_id, db, current)
    prog = progress(child_id, db, current)
    semantics = get_model_output_display_metadata(is_demo=active_model_is_demo(db))
    series = hist["series"]
    latest = series[-1] if series else None
    previous = series[-2] if len(series) >= 2 else None

    visits = db.scalars(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number)).all()
    latest_visit = visits[-1] if visits else None
    anthro = latest_visit.anthropometry if latest_visit else None
    prev_anthro = visits[-2].anthropometry if len(visits) >= 2 else None

    review_payload = None
    if latest_visit:
        review = get_review_for_visit(db, latest_visit.id)
        reviewer = db.get(User, review.reviewer_user_id) if review else None
        pred = db.scalar(select(Prediction).where(Prediction.visit_id == latest_visit.id, Prediction.is_active.is_(True)))
        review_payload = serialize_review(review, reviewer, has_prediction=pred is not None)

    alerts = db.scalars(
        select(Alert)
        .where(
            Alert.child_id == child_id,
            Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_REVIEW]),
        )
        .order_by(Alert.created_at.desc())
    ).all()
    follow = db.scalar(
        select(FollowUpSchedule)
        .where(
            FollowUpSchedule.child_id == child_id,
            FollowUpSchedule.status.in_(
                [
                    FollowUpStatus.SUGGESTED,
                    FollowUpStatus.SCHEDULED,
                    FollowUpStatus.OVERDUE,
                    FollowUpStatus.RESCHEDULED,
                ]
            ),
        )
        .order_by(FollowUpSchedule.expected_date.desc())
        .limit(1)
    )

    return {
        "pseudonymous_id": child.pseudonymous_id,
        "age_months": None,
        "sex": child.sex.value if hasattr(child.sex, "value") else child.sex,
        "disclaimer": semantics["report_disclaimer"],
        "research_demonstration": semantics["is_demo"],
        "clinical_use": semantics["clinical_use"],
        "score_label": semantics["score_label"],
        "velocity_label": semantics["velocity_label"],
        "display_semantics": semantics,
        "progress": prog,
        "risk_history": series,
        "latest_measurements": None
        if not anthro
        else {
            "weight_kg": anthro.weight_kg,
            "height_cm": anthro.height_cm,
            "muac_cm": anthro.muac_cm,
            "previous_weight_kg": prev_anthro.weight_kg if prev_anthro else None,
            "previous_height_cm": prev_anthro.height_cm if prev_anthro else None,
            "previous_muac_cm": prev_anthro.muac_cm if prev_anthro else None,
        },
        "ai_assessment": None
        if not latest
        else {
            "status": latest.get("status"),
            "severity": latest.get("severity"),
            "score": latest.get("risk"),
            "previous_score": previous.get("risk") if previous else None,
            "visit_date": latest.get("date"),
            "visit_number": latest.get("visit_number"),
        },
        "clinical_attention": [
            {
                "id": str(a.id),
                "type": a.type.value,
                "severity": a.severity.value,
                "status": a.status.value,
                "message": a.message,
                "trigger_value": a.trigger_value,
            }
            for a in alerts
        ],
        "clinician_review": review_payload,
        "follow_up": None
        if not follow
        else {
            "id": str(follow.id),
            "expected_date": follow.expected_date.isoformat(),
            "status": follow.status.value,
        },
        "latent_vectors_excluded": True,
    }
