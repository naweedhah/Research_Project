"""P1 clinician-review domain tests."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import (
    ClinicianAssessment,
    ClinicianReviewState,
    ClinicianWorkflowAction,
    FollowUpStatus,
    UserRole,
)
from app.services.clinician_review import (
    display_status_for_review,
    normalize_assessment,
    normalize_workflow,
    serialize_review,
)
from app.services.quality import REQUIRED_ANTHRO


def test_normalize_assessment_maps_legacy_and_enum():
    assert normalize_assessment("agree") == ClinicianAssessment.AGREE
    assert normalize_assessment("disagree") == ClinicianAssessment.DISAGREE
    assert normalize_assessment("uncertain") == ClinicianAssessment.FURTHER_ASSESSMENT_REQUIRED
    assert normalize_assessment("AGREE") == ClinicianAssessment.AGREE


def test_normalize_workflow_maps_legacy():
    assert normalize_workflow("monitor") == ClinicianWorkflowAction.CONTINUE_MONITORING
    assert normalize_workflow("intervention") == ClinicianWorkflowAction.REQUEST_INTERVENTION_REASSESSMENT
    assert normalize_workflow(None) == ClinicianWorkflowAction.NO_ACTION_RECORDED


def test_display_status_awaiting_when_no_completed_review():
    assert display_status_for_review(None, has_prediction=True) == "AWAITING_REVIEW"
    assert display_status_for_review(None, has_prediction=False) == "NOT_REQUIRED"


def test_serialize_completed_review_does_not_include_ai_overwrite():
    review = SimpleNamespace(
        id=uuid4(),
        review_state=ClinicianReviewState.COMPLETED,
        clinician_assessment=ClinicianAssessment.DISAGREE,
        workflow_action=ClinicianWorkflowAction.REFER,
        clinical_note="Needs referral",
        created_at=datetime.now(UTC),
        reviewed_at=datetime.now(UTC),
        reviewer_user_id=uuid4(),
        prediction_id=uuid4(),
        visit_id=uuid4(),
    )
    reviewer = SimpleNamespace(full_name="Dr. Demo")
    payload = serialize_review(review, reviewer, has_prediction=True)
    assert payload["status"] == "DISAGREED"
    assert payload["clinician_assessment"] == "DISAGREE"
    assert payload["workflow_action"] == "REFER"
    assert "primary_risk_score" not in payload


def test_anthropometric_required_fields_include_height_and_weight():
    assert "height_cm" in REQUIRED_ANTHRO
    assert "weight_kg" in REQUIRED_ANTHRO
    assert "age_months" in REQUIRED_ANTHRO


def test_suggested_follow_up_is_distinct_from_scheduled():
    assert FollowUpStatus.SUGGESTED.value == "SUGGESTED"
    assert FollowUpStatus.SUGGESTED != FollowUpStatus.SCHEDULED


def test_doctor_has_note_write_researcher_does_not():
    from app.core.security import PERMISSIONS

    assert "note:write" in PERMISSIONS[UserRole.DOCTOR]
    assert "note:write" not in PERMISSIONS[UserRole.RESEARCHER]
    assert "child:write" not in PERMISSIONS[UserRole.NUTRITIONIST]
