"""Map C1 prediction/review → C4 observation contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.common.contracts import C4ClinicianReviewObservationV1, C4PredictionObservationV1, ScoreSemanticsV1
from app.integrations.common.feature_snapshot import build_approved_external_feature_snapshot, data_quality_status_from_visit
from app.models.intelligence import ModelVersion, Prediction, TrajectoryMetric
from app.models.operations import ClinicianReview
from app.models.paediatric import Child, Visit
from app.services.model_display import get_model_output_display_metadata


def build_c4_prediction_observation(
    db: Session,
    *,
    child: Child,
    visit: Visit,
    prediction: Prediction,
    model: ModelVersion,
    event_id: UUID | None = None,
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
    features = build_approved_external_feature_snapshot(
        visit, child, feature_schema_version=prediction.feature_schema_version or model.feature_schema_version
    )
    traj = db.scalar(select(TrajectoryMetric).where(TrajectoryMetric.to_visit_id == visit.id).limit(1))
    longitudinal = None
    if traj is not None:
        previous = traj.previous_risk
        current = traj.current_risk
        delta = None if previous is None else float(current) - float(previous)
        longitudinal = {
            "previous_prediction_id": None,
            "progress_state": traj.progress_state.value if traj.progress_state else None,
            "score_delta": delta,
            "score_velocity": traj.risk_velocity,
        }
    obs = C4PredictionObservationV1(
        event_id=event_id or uuid4(),
        occurred_at=datetime.now(UTC),
        correlation_id=correlation_id or uuid4(),
        child={"pseudonymous_child_id": child.pseudonymous_id},
        visit={
            "visit_id": str(visit.id),
            "visit_number": visit.visit_number,
            "visit_date": visit.visit_date.isoformat(),
        },
        features=features,
        prediction={
            "prediction_id": str(prediction.id),
            "status": prediction.status_prediction,
            "severity": prediction.severity_prediction,
            "score": score.model_dump(),
            "class_outputs": {
                "raw": prediction.raw_probabilities,
                "calibrated": prediction.calibrated_probabilities,
                "is_demo_synthetic": bool(model.is_demo),
            },
        },
        model={
            "model_version": f"{model.model_key}-{model.version}",
            "feature_schema_version": model.feature_schema_version,
            "label_schema_version": model.label_schema_version,
            "calibration_version": model.calibration_version,
            "embedding_space_id": model.embedding_space_id,
        },
        quality=data_quality_status_from_visit(visit),
        longitudinal=longitudinal,
    )
    return obs.model_dump(mode="json")


def build_c4_clinician_review_observation(
    *,
    child: Child,
    visit: Visit,
    prediction: Prediction,
    model: ModelVersion,
    review: ClinicianReview,
    event_id: UUID | None = None,
    correlation_id: UUID | None = None,
) -> dict[str, Any]:
    obs = C4ClinicianReviewObservationV1(
        event_id=event_id or uuid4(),
        occurred_at=datetime.now(UTC),
        correlation_id=correlation_id or uuid4(),
        prediction_id=prediction.id,
        visit_id=visit.id,
        pseudonymous_child_id=child.pseudonymous_id,
        clinician_review={
            "assessment": review.clinician_assessment.value if review.clinician_assessment else None,
            "clinician_status": review.clinician_status,  # may be null — do not invent
            "clinician_severity": review.clinician_severity,
            "workflow_action": review.workflow_action.value if review.workflow_action else None,
            "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
            # clinical free-text notes are NOT included
        },
        model_version=f"{model.model_key}-{model.version}",
    )
    return obs.model_dump(mode="json")
