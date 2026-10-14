"""Unit tests for child profile assembly helpers — no fabricated clinical values."""

from datetime import date

from app.services.child_profile import (
    ALERT_HEADLINES,
    calibrated_status_probabilities,
    data_quality_label,
    follow_up_overdue_days,
    parse_clinician_review,
    probability_delta_pp,
    progress_display,
    risk_velocity_pp_month,
    since_baseline_pp,
    visit_review_label,
)


def test_probability_delta_uses_percentage_points():
    assert probability_delta_pp(0.58, 0.33) == 25.0
    assert probability_delta_pp(0.33, 0.58) == -25.0
    assert probability_delta_pp(0.58, None) is None
    assert probability_delta_pp(None, 0.33) is None


def test_risk_velocity_scales_stored_fraction():
    assert risk_velocity_pp_month(0.12) == 12.0
    assert risk_velocity_pp_month(None) is None


def test_since_baseline_requires_two_visits():
    assert since_baseline_pp(0.58, 0.78, 1) is None
    assert since_baseline_pp(0.58, 0.78, 4) == -20.0


def test_single_visit_is_insufficient_history_not_stable():
    assert progress_display("stable", 1, True) == "insufficient_history"
    assert progress_display("baseline", 1, True) == "insufficient_history"
    assert progress_display(None, 0, True) == "not_available"
    assert progress_display("improving", 3, True) == "improving"


def test_incompatible_model_blocks_progress_label():
    assert progress_display("improving", 4, False) == "incompatible_model"
    assert progress_display("incompatible_model", 4, True) == "incompatible_model"


def test_data_quality_label_from_stored_report():
    assert data_quality_label({"complete": True}) == "complete"
    assert data_quality_label({"complete": False}) == "review_required"
    assert data_quality_label({"blocking_errors": [{"field": "weight_kg"}]}) == "review_required"
    assert data_quality_label(None) is None


def test_clinician_review_parse_does_not_overwrite_ai():
    parsed = parse_clinician_review(
        "[Clinician review] Assessment: agree. Workflow: monitor. Caregiver counselled.",
        reviewer_name="Dr. Perera",
        note_id="n1",
    )
    assert parsed["assessment_key"] == "agree"
    assert parsed["workflow_key"] == "monitor"
    assert parsed["note_excerpt"] == "Caregiver counselled."
    assert "58%" not in parsed["note_excerpt"]


def test_visit_review_label():
    assert visit_review_label(False, None) == "AWAITING_REVIEW"
    assert visit_review_label(True, "agree") == "REVIEWED"
    assert visit_review_label(True, "disagree") == "DISAGREED"
    assert visit_review_label(True, "uncertain") == "FURTHER_ASSESSMENT"


def test_follow_up_overdue_days_not_invented():
    assert follow_up_overdue_days(None, None, date(2026, 8, 22)) is None
    assert follow_up_overdue_days(date(2026, 7, 1), "OVERDUE", date(2026, 8, 22)) == 52
    assert follow_up_overdue_days(date(2026, 9, 5), "SCHEDULED", date(2026, 8, 22)) is None


def test_alert_headlines_use_factual_language():
    assert ALERT_HEADLINES["DETERIORATION"] == "Deterioration detected"
    assert ALERT_HEADLINES["STAGNATION"] == "Limited improvement detected"
    assert ALERT_HEADLINES["RELAPSE"] == "Possible regression"
    assert ALERT_HEADLINES["MISSED_FOLLOW_UP"] == "Follow-up overdue"
    joined = " ".join(ALERT_HEADLINES.values()).lower()
    assert "treatment failed" not in joined
    assert "non-adherence" not in joined
    assert "patient relapsed" not in joined


def test_calibrated_status_probabilities_use_stored_values_only():
    stored = {"status": {"wasting": 0.58, "normal": 0.12, "stunting": 0.1, "underweight": 0.2}, "risk": 0.58}
    assert calibrated_status_probabilities(stored) == {
        "normal": 0.12,
        "stunting": 0.1,
        "wasting": 0.58,
        "underweight": 0.2,
    }
    assert calibrated_status_probabilities(None) is None
    assert calibrated_status_probabilities({"risk": 0.58}) is None
    partial = calibrated_status_probabilities({"status": {"wasting": 0.58}})
    assert partial == {"wasting": 0.58}
    assert "normal" not in partial
