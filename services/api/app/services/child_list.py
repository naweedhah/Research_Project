"""Children monitoring worklist — list item assembly and summary metrics."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import AlertStatus, AlertType, FollowUpStatus, ModelStatus, ProgressState
from app.models.identity import Facility
from app.models.intelligence import ModelVersion, Prediction, TrajectoryMetric
from app.models.operations import Alert, FollowUpSchedule
from app.models.paediatric import Child, Visit
from app.services.malnutrition_type import resolve_display
from app.services.model_display import semantics_for_prediction

ACTIVE_ALERT_STATUSES = {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_REVIEW}


def child_is_synthetic(child: Child) -> bool:
    """True when a child was loaded as sample data rather than registered in clinic."""
    for visit in child.visits or []:
        quality = visit.data_quality
        if isinstance(quality, dict) and quality.get("synthetic") is True:
            return True
    return False

_ALERT_LABELS: dict[AlertType, str] = {
    AlertType.DETERIORATION: "Deterioration detected",
    AlertType.STAGNATION: "Limited improvement across follow-ups",
    AlertType.RELAPSE: "Possible regression",
    AlertType.MISSED_FOLLOW_UP: "Follow-up overdue",
}

_PROGRESS_PRIORITY: dict[ProgressState, int] = {
    ProgressState.DETERIORATING: 80,
    ProgressState.STAGNATING: 60,
    ProgressState.INCOMPATIBLE_MODEL: 50,
    ProgressState.UNKNOWN: 20,
    ProgressState.BASELINE: 10,
    ProgressState.STABLE: 5,
    ProgressState.IMPROVING: 0,
}

_REVIEW_PRIORITY: dict[str, int] = {
    "AWAITING_REVIEW": 40,
    "IN_REVIEW": 35,
    "FURTHER_ASSESSMENT": 30,
    "DISAGREED": 25,
    "NOT_REQUIRED": 0,
    "REVIEWED": 0,
}


def age_months(dob: date, on: date | None = None) -> int:
    ref = on or date.today()
    return max(0, (ref.year - dob.year) * 12 + (ref.month - dob.month))


def review_status(db: Session, child_id, alerts: list[Alert], latest_visit: Visit | None) -> str:
    from app.services.clinician_review import (
        active_prediction_for_visit,
        display_status_for_review,
        get_review_for_prediction,
    )

    alert_in_review = any(a.status == AlertStatus.IN_REVIEW for a in alerts)
    if latest_visit is None:
        return display_status_for_review(None, has_prediction=False, alert_in_review=alert_in_review)
    pred = active_prediction_for_visit(db, latest_visit.id)
    review = get_review_for_prediction(db, pred.id) if pred else None
    return display_status_for_review(review, has_prediction=pred is not None, alert_in_review=alert_in_review)


def progress_display(state: str | None, visit_count: int, has_assessment: bool) -> str:
    if not has_assessment:
        return "not_available"
    if visit_count <= 1 or state in {None, "unknown", "baseline"}:
        return "insufficient_history"
    if state == "incompatible_model":
        return "incompatible_model"
    return state or "insufficient_history"


def follow_up_context(follow: FollowUpSchedule | None, today: date) -> tuple[date | None, str | None, int | None]:
    if not follow:
        return None, "none", None
    expected = follow.expected_date
    status = follow.status.value
    if status in {FollowUpStatus.COMPLETED.value, FollowUpStatus.CANCELLED.value}:
        return None, "none", None
    if status == FollowUpStatus.OVERDUE.value or (status != FollowUpStatus.SUGGESTED.value and expected < today):
        overdue_days = (today - expected).days
        return expected, "overdue", max(overdue_days, 0)
    if status == FollowUpStatus.SUGGESTED.value:
        return expected, "suggested", None
    if expected == today:
        return expected, "due_today", None
    return expected, "scheduled", None


def requires_clinical_attention(item: dict) -> bool:
    if item.get("clinician_review_status") in {"AWAITING_REVIEW", "IN_REVIEW", "FURTHER_ASSESSMENT"}:
        return True
    progress = item.get("progress_display")
    if progress in {"deteriorating", "incompatible_model"}:
        return True
    if progress == "stagnating":
        return True
    for alert in item.get("clinical_attention") or []:
        if alert.get("type") in {"DETERIORATION", "RELAPSE", "STAGNATION", "MISSED_FOLLOW_UP"}:
            return True
    if item.get("follow_up_display_status") == "overdue":
        return True
    return False


def priority_score(item: dict) -> int:
    score = _REVIEW_PRIORITY.get(item.get("clinician_review_status", ""), 0)
    progress_key = item.get("progress_display")
    if progress_key == "deteriorating":
        score += _PROGRESS_PRIORITY[ProgressState.DETERIORATING]
    elif progress_key == "stagnating":
        score += _PROGRESS_PRIORITY[ProgressState.STAGNATING]
    elif progress_key == "incompatible_model":
        score += _PROGRESS_PRIORITY[ProgressState.INCOMPATIBLE_MODEL]
    for alert in item.get("clinical_attention") or []:
        if alert.get("type") == "DETERIORATION":
            score += 90
        elif alert.get("type") == "RELAPSE":
            score += 85
        elif alert.get("type") == "STAGNATION":
            score += 70
        elif alert.get("type") == "MISSED_FOLLOW_UP":
            score += 50
    if item.get("follow_up_display_status") == "overdue":
        score += 45
    return score


def build_list_item(db: Session, child: Child, *, today: date | None = None, model_is_demo: bool = False) -> dict:
    today = today or date.today()
    visits = db.scalars(
        select(Visit)
        .where(Visit.child_id == child.id)
        .options(joinedload(Visit.anthropometry))
        .order_by(Visit.visit_number)
    ).unique().all()

    last = visits[-1] if visits else None
    pred = None
    metric = None
    if last:
        pred = db.scalar(select(Prediction).where(Prediction.visit_id == last.id, Prediction.is_active.is_(True)))
        metric = db.scalar(
            select(TrajectoryMetric).where(TrajectoryMetric.to_visit_id == last.id).order_by(TrajectoryMetric.created_at.desc())
        )

    assessment_count = 0
    probability_history: list[float] = []
    for visit in visits:
        p = db.scalar(select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True)))
        if p and p.primary_risk_score is not None:
            assessment_count += 1
            probability_history.append(round(p.primary_risk_score * 100))

    probability_history = probability_history[-5:]

    previous_risk = metric.previous_risk if metric else None
    current_risk = pred.primary_risk_score if pred else None
    risk_change_pp = None
    if previous_risk is not None and current_risk is not None:
        risk_change_pp = round((current_risk - previous_risk) * 100)

    rv_pp_month: float | None = None
    rv_available = False
    progress_warning = metric.warning if metric else None
    if metric and metric.risk_velocity is not None and metric.progress_state != ProgressState.INCOMPATIBLE_MODEL:
        rv_pp_month = round(metric.risk_velocity * 100, 1)
        rv_available = True

    progress_raw = metric.progress_state.value if metric else None
    has_assessment = pred is not None
    progress_disp = progress_display(progress_raw, len(visits), has_assessment)

    alerts = db.scalars(
        select(Alert)
        .where(Alert.child_id == child.id, Alert.status.in_(ACTIVE_ALERT_STATUSES))
        .order_by(Alert.created_at.desc())
    ).all()

    clinical_attention = []
    seen_types: set[str] = set()
    for alert in alerts:
        t = alert.type.value
        if t in seen_types:
            continue
        seen_types.add(t)
        clinical_attention.append(
            {
                "type": t,
                "label": _ALERT_LABELS.get(alert.type, alert.message),
                "severity": alert.severity.value,
                "status": alert.status.value,
            }
        )

    follow = db.scalar(
        select(FollowUpSchedule)
        .where(
            FollowUpSchedule.child_id == child.id,
            FollowUpSchedule.status.notin_([FollowUpStatus.COMPLETED, FollowUpStatus.CANCELLED]),
        )
        .order_by(FollowUpSchedule.expected_date.asc())
        .limit(1)
    )
    next_follow_up, follow_display, overdue_days = follow_up_context(follow, today)

    review = review_status(db, child.id, list(alerts), last)

    measurements = None
    if last and last.anthropometry:
        anthro = last.anthropometry
        prev_anthro = visits[-2].anthropometry if len(visits) > 1 and visits[-2].anthropometry else None
        measurements = {
            "weight_kg": anthro.weight_kg,
            "height_cm": anthro.height_cm,
            "muac_cm": anthro.muac_cm,
            "previous_weight_kg": prev_anthro.weight_kg if prev_anthro else None,
            "previous_muac_cm": prev_anthro.muac_cm if prev_anthro else None,
        }

    model_version = db.get(ModelVersion, last.model_version_id) if last and last.model_version_id else None
    fac = db.get(Facility, child.facility_id)
    demo_flag = model_is_demo or (bool(model_version.is_demo) if model_version else False)
    semantics = semantics_for_prediction(pred, is_demo=True)
    displayed_status, displayed_ga = (
        resolve_display(pred.status_prediction, pred.calibrated_probabilities) if pred else (None, None)
    )

    item = {
        "id": child.id,
        "pseudonymous_id": child.pseudonymous_id,
        "age_months": age_months(child.date_of_birth),
        "sex": child.sex.value,
        "responsible_team": child.responsible_team,
        "facility_code": fac.code if fac else None,
        "last_visit": last.visit_date if last else None,
        "latest_visit_number": last.visit_number if last else None,
        "visit_count": len(visits),
        "assessment_count": assessment_count,
        "has_assessment": has_assessment,
        "current_status": displayed_status,
        "predicted_malnutrition_type": displayed_ga.get("predicted_malnutrition_type") if displayed_ga else None,
        "detected_conditions": displayed_ga.get("detected_conditions") if displayed_ga else None,
        "severity": pred.severity_prediction if pred else None,
        "current_risk": current_risk,
        "previous_risk": previous_risk,
        "risk_change_pp": risk_change_pp,
        "probability_label": semantics["score_label"],
        "score_kind": semantics["score_kind"],
        "score_is_probability": semantics["score_is_probability"],
        "velocity_label": semantics["velocity_label"],
        "prediction_confidence": pred.confidence if pred else None,
        "risk_velocity_pp_month": rv_pp_month,
        "risk_velocity_available": rv_available,
        "progress": progress_raw,
        "progress_display": progress_disp,
        "progress_warning": progress_warning,
        "probability_history": probability_history,
        "clinical_attention": clinical_attention,
        "clinician_review_status": review,
        "next_follow_up": next_follow_up,
        "follow_up_status": follow.status.value if follow else None,
        "follow_up_display_status": follow_display,
        "follow_up_overdue_days": overdue_days,
        "measurements": measurements,
        "model_is_demo": bool(semantics.get("is_demo")),
        "display_semantics": semantics,
        "alert_type": clinical_attention[0]["type"] if clinical_attention else None,
        "alert_severity": clinical_attention[0]["severity"] if clinical_attention else None,
    }
    item["priority_score"] = priority_score(item)
    item["requires_attention"] = requires_clinical_attention(item)
    return item


def list_summary(items: list[dict]) -> dict:
    requiring = sum(1 for i in items if i.get("requires_attention"))
    awaiting_review = sum(
        1 for i in items if i.get("clinician_review_status") in {"AWAITING_REVIEW", "IN_REVIEW", "FURTHER_ASSESSMENT"}
    )
    upcoming = sum(1 for i in items if i.get("follow_up_display_status") in {"scheduled", "due_today"})
    overdue = sum(1 for i in items if i.get("follow_up_display_status") == "overdue")
    return {
        "children_under_monitoring": len(items),
        "requiring_clinical_attention": requiring,
        "awaiting_clinical_review": awaiting_review,
        "follow_up_upcoming": upcoming,
        "follow_up_overdue": overdue,
    }


def active_model_is_demo(db: Session) -> bool:
    model = db.scalar(select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE).limit(1))
    return bool(model.is_demo) if model else False
