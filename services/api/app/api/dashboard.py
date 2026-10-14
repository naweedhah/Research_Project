from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.policy import load_product
from app.models.enums import AlertStatus, AlertType, FollowUpStatus, ModelStatus, ProgressState
from app.models.identity import Facility, User
from app.models.intelligence import ModelVersion, Prediction, TrajectoryMetric
from app.models.operations import Alert, FollowUpSchedule
from app.models.paediatric import Child, Visit
from app.security.rbac import facility_scope_ids
from app.services.child_list import child_is_synthetic
from app.services.model_display import get_model_output_display_metadata, semantics_for_prediction

router = APIRouter(tags=["dashboard"])


def _age_months(dob: date, ref: date | None = None) -> int:
    ref = ref or date.today()
    months = (ref.year - dob.year) * 12 + (ref.month - dob.month)
    if ref.day < dob.day:
        months -= 1
    return max(0, months)


def _latest_metric_map(db: Session, child_ids: list) -> dict:
    if not child_ids:
        return {}
    metrics = db.scalars(
        select(TrajectoryMetric)
        .where(TrajectoryMetric.child_id.in_(child_ids))
        .order_by(TrajectoryMetric.created_at.desc())
    ).all()
    out: dict = {}
    for m in metrics:
        if m.child_id not in out:
            out[m.child_id] = m
    return out


def _visit_count_map(db: Session, child_ids: list) -> dict:
    if not child_ids:
        return {}
    rows = db.execute(
        select(Visit.child_id, func.count())
        .where(Visit.child_id.in_(child_ids))
        .group_by(Visit.child_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def _review_status(db: Session, child_id, alerts: list[Alert], latest_visit: Visit | None) -> str:
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


def _attention_priority(
    *,
    review: str,
    alerts: list[Alert],
    metric: TrajectoryMetric | None,
    follow_overdue: bool,
) -> tuple[int, list[str]]:
    """Transparent priority: lower rank number = higher attention. Returns (sort_key, badges)."""
    badges: list[str] = []
    alert_types = {a.type for a in alerts}
    deteriorating = AlertType.DETERIORATION in alert_types or (
        metric and metric.progress_state == ProgressState.DETERIORATING
    )
    relapse = AlertType.RELAPSE in alert_types
    stagnating = AlertType.STAGNATION in alert_types or (
        metric and metric.progress_state == ProgressState.STAGNATING
    )
    awaiting = review in {"AWAITING_REVIEW", "IN_REVIEW", "FURTHER_ASSESSMENT"}

    if deteriorating:
        badges.append("Deterioration")
    if relapse:
        badges.append("Possible regression")
    if stagnating:
        badges.append("Limited improvement")
    if awaiting:
        badges.append("Awaiting clinical review")
    if follow_overdue or AlertType.MISSED_FOLLOW_UP in alert_types:
        badges.append("Follow-up overdue")

    if deteriorating and awaiting:
        rank = 1
    elif relapse and awaiting:
        rank = 2
    elif awaiting:
        rank = 3
    elif stagnating:
        rank = 4
    elif follow_overdue or AlertType.MISSED_FOLLOW_UP in alert_types:
        rank = 5
    else:
        rank = 6
    return rank, badges


_WORKFLOW_LABELS = {
    "monitor": "Continue monitoring",
    "nutrition": "Nutrition review",
    "investigate": "Further investigation",
    "refer": "Refer",
    "reassess": "Request intervention reassessment",
    "continue_monitoring": "Continue monitoring",
}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current=Depends(require_permission("child:read", "research:read"))):
    scope = facility_scope_ids(current)
    today = date.today()
    product = load_product()

    child_stmt = select(Child).where(Child.deleted_at.is_(None))
    if scope:
        child_stmt = child_stmt.where(Child.facility_id.in_(scope))
    children = [c for c in db.scalars(child_stmt).all() if not child_is_synthetic(c)]
    child_ids = [c.id for c in children]
    child_map = {c.id: c for c in children}

    latest_metrics = _latest_metric_map(db, child_ids)
    visit_counts = _visit_count_map(db, child_ids)

    deteriorating_ids: set = set()
    stagnating_ids: set = set()
    improving = stable = insufficient = 0

    for child in children:
        m = latest_metrics.get(child.id)
        vc = visit_counts.get(child.id, 0)
        if not m or vc < 2:
            insufficient += 1
            continue
        if m.progress_state == ProgressState.DETERIORATING:
            deteriorating_ids.add(child.id)
        elif m.progress_state == ProgressState.STAGNATING:
            stagnating_ids.add(child.id)
        elif m.progress_state == ProgressState.IMPROVING:
            improving += 1
        elif m.progress_state in {ProgressState.STABLE, ProgressState.BASELINE}:
            stable += 1
        else:
            insufficient += 1

    alert_stmt = select(Alert).where(
        Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_REVIEW])
    )
    if scope:
        alert_stmt = alert_stmt.where(Alert.facility_id.in_(scope))
    active_alerts = [
        alert
        for alert in db.scalars(alert_stmt.order_by(Alert.created_at.desc())).all()
        if alert.child_id in child_map
    ]

    alerts_by_child: dict = defaultdict(list)
    for alert in active_alerts:
        alerts_by_child[alert.child_id].append(alert)

    follow_stmt = select(FollowUpSchedule).where(
        FollowUpSchedule.status.in_(
            [FollowUpStatus.SUGGESTED, FollowUpStatus.SCHEDULED, FollowUpStatus.OVERDUE, FollowUpStatus.RESCHEDULED]
        )
    )
    if scope:
        follow_stmt = follow_stmt.where(FollowUpSchedule.facility_id.in_(scope))
    all_follows = [
        follow
        for follow in db.scalars(follow_stmt.order_by(FollowUpSchedule.expected_date)).all()
        if follow.child_id in child_map
    ]
    overdue_children = len({follow.child_id for follow in all_follows if follow.status == FollowUpStatus.OVERDUE})

    awaiting_review_ids: set = set()
    # Count unique children with an active prediction and no completed structured review.
    for child in children:
        last_visit = db.scalar(
            select(Visit).where(Visit.child_id == child.id).order_by(Visit.visit_number.desc()).limit(1)
        )
        review = _review_status(db, child.id, alerts_by_child.get(child.id, []), last_visit)
        if review in {"AWAITING_REVIEW", "IN_REVIEW", "FURTHER_ASSESSMENT"}:
            awaiting_review_ids.add(child.id)

    priority_rows: list[dict] = []
    priority_child_ids: set = set()

    def _build_priority_row(child_id, alerts: list[Alert], *, follow_overdue: bool = False) -> dict | None:
        child = child_map.get(child_id)
        if not child:
            return None
        last_visit = db.scalar(
            select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number.desc()).limit(1)
        )
        metric = latest_metrics.get(child_id)
        pred = None
        if last_visit:
            pred = db.scalar(
                select(Prediction).where(Prediction.visit_id == last_visit.id, Prediction.is_active.is_(True))
            )

        review = _review_status(db, child_id, alerts, last_visit)
        current_risk = metric.current_risk if metric else (pred.primary_risk_score if pred else None)
        previous_risk = metric.previous_risk if metric else None
        prob_delta_pp = None
        if current_risk is not None and previous_risk is not None:
            prob_delta_pp = round((current_risk - previous_risk) * 100)
        semantics = semantics_for_prediction(pred, is_demo=True)
        rank, badges = _attention_priority(
            review=review, alerts=alerts, metric=metric, follow_overdue=follow_overdue
        )
        # Only surface children that need attention.
        if rank >= 6 and not alerts and not follow_overdue:
            return None

        return {
            "child_id": str(child_id),
            "pseudonymous_id": child.pseudonymous_id,
            "age_months": _age_months(child.date_of_birth),
            "sex": child.sex.value,
            "latest_visit": last_visit.visit_date.isoformat() if last_visit else None,
            "current_status": pred.status_prediction if pred else None,
            "severity": pred.severity_prediction if pred else None,
            "probability_label": semantics["score_label"],
            "score_kind": semantics["score_kind"],
            "score_is_probability": semantics["score_is_probability"],
            "velocity_label": semantics["velocity_label"],
            "current_probability": current_risk,
            "previous_probability": previous_risk,
            "probability_delta_pp": prob_delta_pp,
            "risk_velocity": metric.risk_velocity if metric and metric.risk_velocity is not None else None,
            "progress_state": metric.progress_state.value if metric else None,
            "alerts": [
                {"type": a.type.value, "severity": a.severity.value, "status": a.status.value, "id": str(a.id)}
                for a in alerts
            ],
            "attention_badges": badges,
            "review_status": review,
            "priority_rank": rank,
            "priority_score": 1000 - rank * 100,
            "display_semantics": semantics,
        }

    # Include awaiting-review children even without alerts.
    attention_child_ids = set(alerts_by_child.keys()) | awaiting_review_ids
    for child_id in attention_child_ids:
        row = _build_priority_row(child_id, alerts_by_child.get(child_id, []))
        if row:
            priority_rows.append(row)
            priority_child_ids.add(child_id)

    overdue_only = [f for f in all_follows if f.status == FollowUpStatus.OVERDUE and f.child_id not in priority_child_ids]
    for f in overdue_only[:6]:
        row = _build_priority_row(f.child_id, [], follow_overdue=True)
        if row:
            if not any(a.get("type") == AlertType.MISSED_FOLLOW_UP.value for a in row["alerts"]):
                row["alerts"] = row["alerts"] + [
                    {"type": AlertType.MISSED_FOLLOW_UP.value, "severity": "MODERATE", "status": "OPEN", "id": None}
                ]
            priority_rows.append(row)
            priority_child_ids.add(f.child_id)

    priority_rows.sort(key=lambda r: (r.get("priority_rank", 99), r["pseudonymous_id"]))

    def _follow_item(f: FollowUpSchedule) -> dict:
        child = child_map.get(f.child_id) or db.get(Child, f.child_id)
        fac = db.get(Facility, f.facility_id)
        overdue_days = (today - f.expected_date).days if f.status == FollowUpStatus.OVERDUE else None
        return {
            "child": child.pseudonymous_id if child else None,
            "child_id": str(f.child_id),
            "date": f.expected_date.isoformat(),
            "clinic": fac.name if fac else None,
            "status": f.status.value,
            "overdue_days": overdue_days,
        }

    overdue_list = [_follow_item(f) for f in all_follows if f.status == FollowUpStatus.OVERDUE][:6]
    today_list = [
        _follow_item(f)
        for f in all_follows
        if f.expected_date == today and f.status not in {FollowUpStatus.OVERDUE, FollowUpStatus.SUGGESTED}
    ][:4]
    upcoming_list = [
        _follow_item(f)
        for f in all_follows
        if f.expected_date > today and f.status not in {FollowUpStatus.OVERDUE}
    ][:4]

    children_multi_assessment = sum(1 for cid in child_ids if visit_counts.get(cid, 0) >= 2)
    comparable_trajectories = sum(
        1
        for m in latest_metrics.values()
        if m.risk_velocity is not None and m.previous_risk is not None
    )

    from app.models.enums import ClinicianReviewState
    from app.models.operations import ClinicianReview
    from app.services.clinician_review import serialize_review

    review_stmt = select(ClinicianReview).where(ClinicianReview.review_state == ClinicianReviewState.COMPLETED)
    if scope:
        review_stmt = review_stmt.where(ClinicianReview.facility_id.in_(scope))
    recent_reviews = []
    for row in db.scalars(review_stmt.order_by(ClinicianReview.reviewed_at.desc().nullslast()).limit(12)).all():
        child = child_map.get(row.child_id)
        if child is None:
            continue
        author = db.get(User, row.reviewer_user_id)
        parsed = serialize_review(row, author, has_prediction=True)
        parsed["pseudonymous_id"] = child.pseudonymous_id
        recent_reviews.append(parsed)
        if len(recent_reviews) >= 4:
            break

    model = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.status.in_([ModelStatus.ACTIVE, ModelStatus.EXPERIMENTAL]))
        .order_by(ModelVersion.activated_at.desc().nullslast(), ModelVersion.created_at.desc())
        .limit(1)
    )
    facility = db.get(Facility, current.user.facility_id) if current.user.facility_id else None
    semantics = get_model_output_display_metadata(is_demo=bool(model.is_demo) if model else None)

    monitored = len(children)
    progress_total = improving + stable + len(stagnating_ids) + len(deteriorating_ids)

    return {
        "synthetic": False,
        "facility": {
            "name": facility.name if facility else None,
            "code": facility.code if facility else None,
        },
        "model": {
            "label": semantics["banner_title"],
            "version": f"{model.model_key}-{model.version}" if model else "MCA-2026-001",
            "is_demo": semantics["is_demo"],
            "clinical_use": semantics["clinical_use"],
        },
        "display_semantics": semantics,
        "generated_at": datetime.now().isoformat(),
        "kpis": {
            "children_under_monitoring": monitored,
            "awaiting_clinical_review": len(awaiting_review_ids),
            "deteriorating": len(deteriorating_ids),
            "stagnating": len(stagnating_ids),
            "overdue_follow_ups": overdue_children,
            "open_alerts": len(active_alerts),
        },
        "priority_patients": priority_rows,
        "risk_trend": {
            "improving": improving,
            "stable": stable,
            "stagnating": len(stagnating_ids),
            "deteriorating": len(deteriorating_ids),
            "insufficient_history": insufficient,
            "total_classified": progress_total,
        },
        "longitudinal_intelligence": {
            "children_with_two_plus_assessments": children_multi_assessment,
            "active_progress_alerts": len(active_alerts),
            "comparable_trajectories": comparable_trajectories,
        },
        "follow_ups": {
            "overdue": overdue_list,
            "today": today_list,
            "upcoming": upcoming_list,
            "total_scheduled": len(all_follows),
        },
        "recent_clinical_reviews": recent_reviews,
    }


@router.get("/search")
def search(q: str = Query(min_length=1), db: Session = Depends(get_db), current=Depends(require_permission("child:read", "alert:read"))):
    scope = facility_scope_ids(current)
    like = f"%{q.strip()}%"
    child_stmt = select(Child).where(Child.deleted_at.is_(None), Child.pseudonymous_id.ilike(like))
    if scope:
        child_stmt = child_stmt.where(Child.facility_id.in_(scope))
    children = [
        {"type": "child", "id": str(c.id), "label": c.pseudonymous_id}
        for c in db.scalars(child_stmt.limit(8)).all()
        if not child_is_synthetic(c)
    ]
    alert_stmt = select(Alert).where(Alert.message.ilike(like))
    if scope:
        alert_stmt = alert_stmt.where(Alert.facility_id.in_(scope))
    alerts = [
        {"type": "alert", "id": str(a.id), "label": a.message, "child_id": str(a.child_id)}
        for a in db.scalars(alert_stmt.limit(8)).all()
    ]
    return {"items": children + alerts}
