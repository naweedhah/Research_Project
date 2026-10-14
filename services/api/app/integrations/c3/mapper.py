"""Map C1 domain objects → C3InterventionRequestV1. No intervention content invented."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.common.contracts import C3InterventionRequestV1, ScoreSemanticsV1
from app.integrations.common.feature_snapshot import build_approved_external_feature_snapshot, data_quality_status_from_visit
from app.models.intelligence import ModelVersion, Prediction, TrajectoryMetric
from app.models.operations import Alert, ClinicianReview
from app.models.paediatric import Child, Visit
from app.services.model_display import get_model_output_display_metadata


def build_c3_reassessment_payload(
    db: Session,
    *,
    child: Child,
    visit: Visit,
    prediction: Prediction,
    model: ModelVersion,
    review: ClinicianReview,
    request_id: UUID | None = None,
    correlation_id: UUID | None = None,
) -> dict[str, Any]:
    semantics = get_model_output_display_metadata(is_demo=bool(model.is_demo))
    score = ScoreSemanticsV1(
        value=float(prediction.primary_risk_score),
        kind=semantics["score_kind"],
        label=semantics["score_label"],
        is_probability=bool(semantics["score_is_probability"]),
        is_calibrated=bool(semantics["score_is_calibrated"]),
        calibration_version=prediction.calibration_version,
    )
    traj = db.scalar(select(TrajectoryMetric).where(TrajectoryMetric.to_visit_id == visit.id).limit(1))
    longitudinal = None
    if traj is not None:
        previous = traj.previous_risk
        current = traj.current_risk
        delta = None if previous is None else float(current) - float(previous)
        longitudinal = {
            "previous_score": previous,
            "score_delta": delta,
            "score_velocity": traj.risk_velocity,
            "progress_state": traj.progress_state.value if traj.progress_state else None,
        }
    alerts = [
        a.type.value if hasattr(a.type, "value") else str(a.type)
        for a in db.scalars(select(Alert).where(Alert.child_id == child.id).order_by(Alert.created_at.desc()).limit(5)).all()
    ]
    features = build_approved_external_feature_snapshot(
        visit, child, feature_schema_version=prediction.feature_schema_version or model.feature_schema_version
    )
    req = C3InterventionRequestV1(
        request_id=request_id or uuid4(),
        correlation_id=correlation_id or uuid4(),
        child={"pseudonymous_child_id": child.pseudonymous_id, "child_uuid": str(child.id)},
        visit={
            "visit_id": str(visit.id),
            "visit_number": visit.visit_number,
            "visit_date": visit.visit_date.isoformat(),
        },
        prediction={
            "prediction_id": str(prediction.id),
            "status": prediction.status_prediction,
            "severity": prediction.severity_prediction,
            "score": score.model_dump(),
            "class_outputs": {
                "raw": prediction.raw_probabilities,
                "calibrated": prediction.calibrated_probabilities,
                "semantics": {
                    "demo": bool(model.is_demo),
                    "note": "Demo class outputs are synthetic demonstration values, not validated clinical probabilities."
                    if model.is_demo
                    else "Research model class outputs; clinical review required.",
                },
            },
        },
        longitudinal=longitudinal,
        alerts=alerts,
        model={
            "model_version": f"{model.model_key}-{model.version}",
            "feature_schema_version": model.feature_schema_version,
            "label_schema_version": model.label_schema_version,
            "calibration_version": model.calibration_version,
            "embedding_space_id": model.embedding_space_id,
        },
        features={"approved_feature_snapshot": features},
        data_quality=data_quality_status_from_visit(visit),
        explanation_context_ref=None,
        requested_by={"clinician_user_id": str(review.reviewer_user_id)},
        requested_at=datetime.now(UTC),
    )
    return req.model_dump(mode="json")
