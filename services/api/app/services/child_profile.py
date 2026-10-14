"""Child profile assembly helpers. Frontend must not invent these values."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.models.enums import AlertType, FollowUpStatus, ProgressState

ALERT_HEADLINES: dict[str, str] = {
    AlertType.DETERIORATION.value: "Deterioration detected",
    AlertType.STAGNATION.value: "Limited improvement detected",
    AlertType.RELAPSE.value: "Possible regression",
    AlertType.MISSED_FOLLOW_UP.value: "Follow-up overdue",
}

WORKFLOW_LABELS = {
    "monitor": "Continue monitoring",
    "nutrition": "Nutrition review",
    "investigate": "Further investigation",
    "refer": "Refer",
    "reassess": "Request intervention reassessment",
}

ANTHRO_FIELDS = [
    "age_months",
    "sex",
    "height_cm",
    "weight_kg",
    "muac_cm",
    "birth_weight_kg",
    "head_circumference_cm",
]
SOCIO_FIELDS = [
    "wealth_proxy",
    "maternal_education",
    "paternal_education",
    "maternal_employment",
    "household_size",
    "geographical_area",
    "drinking_water",
    "sanitation",
]
DIETARY_FIELDS = [
    "breastfeeding_status",
    "breastfeeding_duration_months",
    "complementary_feeding",
    "dietary_diversity_score",
    "meal_frequency",
    "food_groups",
    "micronutrient_supplementation",
]
MCH_FIELDS = [
    "maternal_bmi",
    "gestational_age_weeks",
    "immunization_uptodate",
    "vitamin_a",
    "recent_diarrhoea",
    "recent_respiratory_illness",
    "recent_hospitalization",
    "birth_characteristics",
]


def is_present(value) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    return True


def field_value(obj, name):
    if obj is None:
        return None
    val = getattr(obj, name, None)
    return val.value if hasattr(val, "value") else val


def count_fields(obj, names: list[str]) -> dict:
    available = 0
    details = []
    for name in names:
        val = field_value(obj, name)
        present = is_present(val)
        if present:
            available += 1
        details.append({"field": name, "available": present})
    return {"available": available, "total": len(names), "fields": details}


def probability_delta_pp(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round((current - previous) * 100, 1)


def risk_velocity_pp_month(stored_velocity: float | None) -> float | None:
    if stored_velocity is None:
        return None
    return round(stored_velocity * 100, 1)


def since_baseline_pp(current: float | None, baseline: float | None, visit_count: int) -> float | None:
    if visit_count < 2 or current is None or baseline is None:
        return None
    return round((current - baseline) * 100, 1)


def progress_display(state: str | None, predicted_visit_count: int, comparable: bool) -> str:
    if predicted_visit_count == 0:
        return "not_available"
    if not comparable:
        return "incompatible_model"
    if predicted_visit_count <= 1 or state in {None, "unknown", "baseline"}:
        return "insufficient_history"
    if state == "incompatible_model":
        return "incompatible_model"
    return state


def data_quality_label(quality: dict | None) -> str | None:
    if not quality:
        return None
    if quality.get("blocking_errors"):
        return "review_required"
    if quality.get("complete") is True:
        return "complete"
    if quality.get("complete") is False:
        return "review_required"
    return None


def parse_clinician_review(body: str, *, reviewer_name: str | None = None, created_at=None, note_id=None) -> dict:
    lower = body.lower()
    assessment_key = "reviewed"
    assessment = "Reviewed"
    if "assessment: agree" in lower:
        assessment_key = "agree"
        assessment = "Agree"
    elif "assessment: disagree" in lower:
        assessment_key = "disagree"
        assessment = "Disagree"
    elif "assessment: uncertain" in lower or "further assessment" in lower:
        assessment_key = "uncertain"
        assessment = "Further assessment required"

    workflow_key = None
    workflow_label = None
    workflow_match = re.search(r"Workflow:\s*(\w+)", body, re.I)
    if workflow_match:
        workflow_key = workflow_match.group(1).lower()
        workflow_label = WORKFLOW_LABELS.get(workflow_key, workflow_key.replace("_", " ").title())

    note_excerpt = body
    stripped = re.sub(r"^\[Clinician review\]\s*", "", body, flags=re.I).strip()
    excerpt_match = re.match(r"Assessment:\s*\w+\.\s*Workflow:\s*\w+\.\s*(.*)", stripped, re.I | re.S)
    if excerpt_match and excerpt_match.group(1).strip():
        note_excerpt = excerpt_match.group(1).strip()

    created = created_at.isoformat() if hasattr(created_at, "isoformat") else created_at
    return {
        "note_id": str(note_id) if note_id is not None else None,
        "assessment": assessment,
        "assessment_key": assessment_key,
        "workflow": workflow_label,
        "workflow_key": workflow_key,
        "reviewer_name": reviewer_name,
        "note_excerpt": note_excerpt,
        "created_at": created,
    }


def visit_review_label(has_review_note: bool, assessment_key: str | None) -> str:
    if not has_review_note:
        return "AWAITING_REVIEW"
    if assessment_key == "disagree":
        return "DISAGREED"
    if assessment_key == "uncertain":
        return "FURTHER_ASSESSMENT"
    return "REVIEWED"


def follow_up_overdue_days(expected: date | None, status: str | None, today: date) -> int | None:
    if expected is None:
        return None
    if status in {
        FollowUpStatus.COMPLETED.value,
        FollowUpStatus.CANCELLED.value,
        FollowUpStatus.SUGGESTED.value,
    }:
        return None
    if status == FollowUpStatus.OVERDUE.value or expected < today:
        return max((today - expected).days, 0)
    return None


def record_as_inputs(obj, names: list[str]) -> dict:
    out = {}
    for name in names:
        out[name] = field_value(obj, name)
    return out


STATUS_PROBABILITY_KEYS = ("normal", "stunting", "wasting", "underweight")


def calibrated_status_probabilities(calibrated: dict | None) -> dict[str, float] | None:
    """Return stored class probabilities only. Does not invent missing classes or SHAP values."""
    if not isinstance(calibrated, dict):
        return None
    status = calibrated.get("status")
    if not isinstance(status, dict):
        return None
    out: dict[str, float] = {}
    for key in STATUS_PROBABILITY_KEYS:
        value = status.get(key)
        if value is None:
            continue
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            continue
    return out or None
