"""Structured clinician-review helpers — never mutate AI prediction records."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import (
    AlertStatus,
    ClinicianAssessment,
    ClinicianReviewState,
    ClinicianWorkflowAction,
)
from app.models.identity import User
from app.models.intelligence import Prediction
from app.models.operations import Alert, ClinicianReview
from app.models.paediatric import Child, Visit

_ASSESSMENT_DISPLAY = {
    ClinicianAssessment.AGREE: "Agree",
    ClinicianAssessment.DISAGREE: "Disagree",
    ClinicianAssessment.FURTHER_ASSESSMENT_REQUIRED: "Further assessment required",
}

_WORKFLOW_DISPLAY = {
    ClinicianWorkflowAction.CONTINUE_MONITORING: "Continue monitoring",
    ClinicianWorkflowAction.NUTRITION_REVIEW: "Nutrition review",
    ClinicianWorkflowAction.FURTHER_INVESTIGATION: "Further investigation",
    ClinicianWorkflowAction.REFER: "Refer",
    ClinicianWorkflowAction.REQUEST_INTERVENTION_REASSESSMENT: "Request intervention reassessment",
    ClinicianWorkflowAction.NO_ACTION_RECORDED: "No action recorded",
}

_LEGACY_ASSESSMENT = {
    "agree": ClinicianAssessment.AGREE,
    "disagree": ClinicianAssessment.DISAGREE,
    "uncertain": ClinicianAssessment.FURTHER_ASSESSMENT_REQUIRED,
    "further_assessment": ClinicianAssessment.FURTHER_ASSESSMENT_REQUIRED,
    "further assessment": ClinicianAssessment.FURTHER_ASSESSMENT_REQUIRED,
}

_LEGACY_WORKFLOW = {
    "monitor": ClinicianWorkflowAction.CONTINUE_MONITORING,
    "continue_monitoring": ClinicianWorkflowAction.CONTINUE_MONITORING,
    "nutrition": ClinicianWorkflowAction.NUTRITION_REVIEW,
    "nutrition_review": ClinicianWorkflowAction.NUTRITION_REVIEW,
    "investigate": ClinicianWorkflowAction.FURTHER_INVESTIGATION,
    "further_investigation": ClinicianWorkflowAction.FURTHER_INVESTIGATION,
    "refer": ClinicianWorkflowAction.REFER,
    "intervention": ClinicianWorkflowAction.REQUEST_INTERVENTION_REASSESSMENT,
    "request_intervention_reassessment": ClinicianWorkflowAction.REQUEST_INTERVENTION_REASSESSMENT,
}


def normalize_assessment(value: str) -> ClinicianAssessment:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _LEGACY_ASSESSMENT:
        return _LEGACY_ASSESSMENT[key]
    return ClinicianAssessment(value.strip().upper())


def normalize_workflow(value: str | None) -> ClinicianWorkflowAction:
    if not value:
        return ClinicianWorkflowAction.NO_ACTION_RECORDED
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _LEGACY_WORKFLOW:
        return _LEGACY_WORKFLOW[key]
    try:
        return ClinicianWorkflowAction(value.strip().upper())
    except ValueError:
        return ClinicianWorkflowAction.NO_ACTION_RECORDED


def display_status_for_review(review: ClinicianReview | None, *, has_prediction: bool, alert_in_review: bool = False) -> str:
    """Stable list/dashboard labels compatible with existing UI filters."""
    if alert_in_review and (review is None or review.review_state != ClinicianReviewState.COMPLETED):
        return "IN_REVIEW"
    if not has_prediction:
        return "NOT_REQUIRED"
    if review is None or review.review_state != ClinicianReviewState.COMPLETED:
        return "AWAITING_REVIEW"
    if review.clinician_assessment == ClinicianAssessment.DISAGREE:
        return "DISAGREED"
    if review.clinician_assessment == ClinicianAssessment.FURTHER_ASSESSMENT_REQUIRED:
        return "FURTHER_ASSESSMENT"
    return "REVIEWED"


def serialize_review(review: ClinicianReview | None, reviewer: User | None = None, *, has_prediction: bool = True) -> dict:
    if review is None:
        return {
            "status": "AWAITING_REVIEW" if has_prediction else "NOT_REQUIRED",
            "review_state": ClinicianReviewState.PENDING.value if has_prediction else None,
            "assessment": None,
            "assessment_key": None,
            "workflow": None,
            "workflow_key": None,
            "reviewer_name": None,
            "note_excerpt": None,
            "clinical_note": None,
            "created_at": None,
            "reviewed_at": None,
            "id": None,
        }
    status = display_status_for_review(review, has_prediction=True)
    assessment = review.clinician_assessment
    workflow = review.workflow_action
    return {
        "id": str(review.id),
        "status": status,
        "review_state": review.review_state.value,
        "assessment": _ASSESSMENT_DISPLAY.get(assessment) if assessment else None,
        "assessment_key": assessment.value.lower() if assessment else None,
        "workflow": _WORKFLOW_DISPLAY.get(workflow) if workflow else None,
        "workflow_key": workflow.value.lower() if workflow else None,
        "workflow_action": workflow.value if workflow else None,
        "clinician_assessment": assessment.value if assessment else None,
        "reviewer_name": reviewer.full_name if reviewer else None,
        "reviewer_user_id": str(review.reviewer_user_id),
        "note_excerpt": (review.clinical_note or "")[:240] or None,
        "clinical_note": review.clinical_note,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
        "prediction_id": str(review.prediction_id),
        "visit_id": str(review.visit_id),
    }


def get_review_for_prediction(db: Session, prediction_id: UUID) -> ClinicianReview | None:
    return db.scalar(select(ClinicianReview).where(ClinicianReview.prediction_id == prediction_id))


def get_review_for_visit(db: Session, visit_id: UUID) -> ClinicianReview | None:
    return db.scalar(
        select(ClinicianReview)
        .where(ClinicianReview.visit_id == visit_id)
        .order_by(ClinicianReview.updated_at.desc())
        .limit(1)
    )


def latest_completed_review_for_child(db: Session, child_id: UUID) -> ClinicianReview | None:
    return db.scalar(
        select(ClinicianReview)
        .where(
            ClinicianReview.child_id == child_id,
            ClinicianReview.review_state == ClinicianReviewState.COMPLETED,
        )
        .order_by(ClinicianReview.reviewed_at.desc().nullslast(), ClinicianReview.updated_at.desc())
        .limit(1)
    )


def active_prediction_for_visit(db: Session, visit_id: UUID) -> Prediction | None:
    return db.scalar(
        select(Prediction).where(Prediction.visit_id == visit_id, Prediction.is_active.is_(True)).limit(1)
    )


def upsert_completed_review(
    db: Session,
    *,
    child: Child,
    visit: Visit,
    prediction: Prediction,
    reviewer: User,
    assessment: ClinicianAssessment,
    workflow: ClinicianWorkflowAction,
    clinical_note: str | None,
    clinician_status: str | None = None,
    clinician_severity: str | None = None,
) -> ClinicianReview:
    """Create or update a completed review. Does not mutate Prediction fields."""
    existing = get_review_for_prediction(db, prediction.id)
    now = datetime.now(UTC)
    if existing is None:
        row = ClinicianReview(
            facility_id=child.facility_id,
            child_id=child.id,
            visit_id=visit.id,
            prediction_id=prediction.id,
            reviewer_user_id=reviewer.id,
            review_state=ClinicianReviewState.COMPLETED,
            clinician_assessment=assessment,
            clinician_status=clinician_status,
            clinician_severity=clinician_severity,
            clinical_note=clinical_note,
            workflow_action=workflow,
            reviewed_at=now,
        )
        db.add(row)
        db.flush()
        return row

    existing.reviewer_user_id = reviewer.id
    existing.review_state = ClinicianReviewState.COMPLETED
    existing.clinician_assessment = assessment
    existing.clinician_status = clinician_status
    existing.clinician_severity = clinician_severity
    existing.clinical_note = clinical_note
    existing.workflow_action = workflow
    existing.reviewed_at = now
    db.flush()
    return existing


def child_has_awaiting_review(db: Session, child_id: UUID, latest_visit: Visit | None) -> bool:
    if latest_visit is None:
        return False
    pred = active_prediction_for_visit(db, latest_visit.id)
    if pred is None:
        return False
    review = get_review_for_prediction(db, pred.id)
    return review is None or review.review_state != ClinicianReviewState.COMPLETED


def alert_in_review_for_child(db: Session, child_id: UUID) -> bool:
    return (
        db.scalar(
            select(Alert.id)
            .where(Alert.child_id == child_id, Alert.status == AlertStatus.IN_REVIEW)
            .limit(1)
        )
        is not None
    )
