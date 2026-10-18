from __future__ import annotations

import calendar
import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.policy import load_clinical_policy
from app.models.enums import (
    AlertStatus,
    AlertType,
    AuditAction,
    FollowUpStatus,
    IntegrationEventType,
    ModelStatus,
    NotificationChannel,
    ProgressState,
    VisitStatus,
)
from app.models.intelligence import LatentEmbedding, ModelVersion, Prediction, TrajectoryMetric
from app.models.operations import Alert, FollowUpSchedule, IntegrationEvent, Notification
from app.models.paediatric import Child, Visit
from app.services.alerts import deterioration_alert, event_window_key, relapse_alert, severity_for, stagnation_alert
from app.services.audit import write_audit
from app.services.longitudinal import LongitudinalError, classify_progress, elapsed_months
from app.services.malnutrition_type import apply_new_prediction_interpretation
from app.services.model_display import DEMO_PROJECTION_VERSION


def _stored_model_version(prediction) -> str | None:
    calibrated = getattr(prediction, "calibrated_probabilities", None)
    if not isinstance(calibrated, dict):
        return None
    block = calibrated.get("ga_rgca")
    if not isinstance(block, dict):
        return None
    version = block.get("model_version") or block.get("prediction_source")
    return str(version) if version else None


def _input_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def active_model(db: Session) -> ModelVersion:
    row = db.scalar(select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE).limit(1))
    if row:
        return row
    row = db.scalar(select(ModelVersion).where(ModelVersion.is_demo.is_(True)).limit(1))
    if row:
        return row
    raise HTTPException(status_code=503, detail="No model version is registered")


def current_visit_payload(visit: Visit, child: Child) -> dict:
    quality = visit.data_quality if isinstance(visit.data_quality, dict) else {}
    context = quality.get("ga_rgca_context") if isinstance(quality.get("ga_rgca_context"), dict) else {}
    return {
        "child_pseudonymous_id": child.pseudonymous_id,
        "visit_number": visit.visit_number,
        "visit_date": visit.visit_date.isoformat(),
        "anthropometric": {
            "age_months": visit.anthropometry.age_months if visit.anthropometry else None,
            "sex": visit.anthropometry.sex.value if visit.anthropometry else None,
            "height_cm": visit.anthropometry.height_cm if visit.anthropometry else None,
            "weight_kg": visit.anthropometry.weight_kg if visit.anthropometry else None,
            "muac_cm": visit.anthropometry.muac_cm if visit.anthropometry else None,
            "birth_weight_kg": visit.anthropometry.birth_weight_kg if visit.anthropometry else None,
            "head_circumference_cm": visit.anthropometry.head_circumference_cm if visit.anthropometry else None,
        },
        "socioeconomic": _to_dict(visit.socioeconomic),
        "dietary": _to_dict(visit.dietary),
        "maternal_child_health": _to_dict(visit.maternal_child_health),
        "ga_rgca_context": context,
    }


def _add_months(moment: datetime, months: int) -> datetime:
    year = moment.year + (moment.month - 1 + months) // 12
    month = (moment.month - 1 + months) % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def _verified_clinical(context: dict | None) -> dict:
    """Clinician-entered history only. Missing stays unknown, not confirmed absent."""
    context = context or {}

    def flag(value):
        if value in (0, 1):
            return int(value)
        return None

    def grade(value):
        if value in {"Normal", "Moderate", "Severe"}:
            return value
        return None

    return {
        "mam": flag(context.get("historical_mam")),
        "sam": flag(context.get("historical_sam")),
        "underweight": grade(context.get("historical_underweight")),
        "stunting": grade(context.get("historical_stunting")),
    }


def assemble_historical_baseline(*, current: dict, earlier: list[dict], context: dict | None) -> dict:
    """Choose the Hist_2025 baseline without copying a later visit over an earlier one.

    A follow-up uses the earliest stored visit that has height and weight.
    The first stored assessment is the baseline itself, labeled with its own date
    and a 12-month horizon. Clinical flags come only from the verified context.
    """
    clinical = _verified_clinical(context)
    birth = current.get("birth_weight_kg")
    chosen = None
    for visit in earlier:
        if visit.get("height_cm") is not None and visit.get("weight_kg") is not None:
            chosen = visit
            break
    if chosen is not None:
        source = "earlier_visit"
        growth = chosen
    else:
        source = "baseline_assessment"
        growth = current
    assessment = growth.get("visit_date")
    horizon_end = _add_months(assessment, 12).isoformat() if isinstance(assessment, datetime) else None
    return {
        "source": source,
        "visit_number": growth.get("visit_number"),
        "assessment_date": assessment.isoformat() if isinstance(assessment, datetime) else None,
        "horizon_months": 12,
        "horizon_end_date": horizon_end,
        "age_months": growth.get("age_months"),
        "height_cm": growth.get("height_cm"),
        "weight_kg": growth.get("weight_kg"),
        "birth_weight_kg": birth if birth is not None else growth.get("birth_weight_kg"),
        **clinical,
    }


def _visit_growth(visit: Visit) -> dict:
    anthro = visit.anthropometry
    return {
        "visit_number": visit.visit_number,
        "visit_date": visit.visit_date,
        "age_months": anthro.age_months if anthro else None,
        "height_cm": anthro.height_cm if anthro else None,
        "weight_kg": anthro.weight_kg if anthro else None,
        "birth_weight_kg": anthro.birth_weight_kg if anthro else None,
    }


def build_inference_payload(db: Session, visit: Visit, child: Child) -> dict:
    """Send the verified baseline separately from the visit being saved.

    Prior model output is not sent and is never used as a clinical label.
    """
    payload = current_visit_payload(visit, child)
    earlier_rows = db.scalars(
        select(Visit)
        .where(Visit.child_id == child.id, Visit.visit_number < visit.visit_number)
        .order_by(Visit.visit_number.asc())
        .options(joinedload(Visit.anthropometry))
    ).all()
    payload["historical_baseline"] = assemble_historical_baseline(
        current=_visit_growth(visit),
        earlier=[_visit_growth(row) for row in earlier_rows],
        context=payload.get("ga_rgca_context"),
    )
    return payload


def _to_dict(obj) -> dict:
    if obj is None:
        return {}
    data = {}
    for col in obj.__table__.columns:
        if col.name in {"id", "visit_id", "created_at", "updated_at"}:
            continue
        val = getattr(obj, col.name)
        data[col.name] = val.value if hasattr(val, "value") else val
    return data


def _recorded_text(value) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _recorded_bool(value) -> str | None:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return None


def _prior_visit_features(db: Session, visit: Visit, child: Child) -> dict | None:
    previous = db.scalar(
        select(Visit)
        .where(Visit.child_id == child.id, Visit.visit_number < visit.visit_number)
        .order_by(Visit.visit_number.desc())
        .options(
            joinedload(Visit.anthropometry),
            joinedload(Visit.socioeconomic),
            joinedload(Visit.dietary),
            joinedload(Visit.maternal_child_health),
        )
        .limit(1)
    )
    anthro = previous.anthropometry if previous else None
    if anthro is None or anthro.weight_kg is None or anthro.height_cm is None:
        return None
    socio = _to_dict(previous.socioeconomic) or _to_dict(visit.socioeconomic)
    diet = _to_dict(previous.dietary) or _to_dict(visit.dietary)
    mch = _to_dict(previous.maternal_child_health) or _to_dict(visit.maternal_child_health)
    prev_pred = db.scalar(select(Prediction).where(Prediction.visit_id == previous.id, Prediction.is_active.is_(True)))
    previous_ga = None
    if prev_pred and isinstance(prev_pred.calibrated_probabilities, dict):
        block = prev_pred.calibrated_probabilities.get("ga_rgca")
        if isinstance(block, dict):
            previous_ga = block
    sex = child.sex.value if child.sex else None
    return {
        "age_months": anthro.age_months,
        "sex": sex,
        "height_cm": anthro.height_cm,
        "weight_kg": anthro.weight_kg,
        "birth_weight_kg": anthro.birth_weight_kg if anthro.birth_weight_kg is not None else (
            visit.anthropometry.birth_weight_kg if visit.anthropometry else None
        ),
        "household_size": socio.get("household_size"),
        "maternal_education": _recorded_text(socio.get("maternal_education")),
        "maternal_employment": _recorded_text(socio.get("maternal_employment")),
        "breastfeeding_duration": _recorded_text(diet.get("breastfeeding_duration_months")),
        "exclusive_breastfeeding": _recorded_text(diet.get("breastfeeding_status")),
        "complementary_feeding_timing": _recorded_bool(diet.get("complementary_feeding")),
        "meal_frequency": _recorded_text(diet.get("meal_frequency")),
        "dietary_diversity": _recorded_text(diet.get("dietary_diversity_score")),
        "vitamin_supplementation": _recorded_bool(
            mch.get("vitamin_a") if mch.get("vitamin_a") is not None else diet.get("micronutrient_supplementation")
        ),
        "previous_ga_rgca": previous_ga,
    }


def run_inference(db: Session, visit: Visit, child: Child, user_id, ip: str | None) -> Prediction:
    settings = get_settings()
    model = active_model(db)
    payload = build_inference_payload(db, visit, child)
    started = datetime.now(UTC)
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{settings.inference_url}/predict", json=payload)
            response.raise_for_status()
            result = apply_new_prediction_interpretation(response.json())
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_NOT_AVAILABLE",
                "message": "Prediction service is temporarily unavailable. No demo score was substituted.",
            },
        ) from exc

    existing_runs = db.scalars(select(Prediction).where(Prediction.visit_id == visit.id)).all()
    for pred in existing_runs:
        pred.is_active = False
    run_number = len(existing_runs) + 1

    prediction = Prediction(
        visit_id=visit.id,
        model_version_id=model.id,
        run_number=run_number,
        is_active=True,
        mode=result.get("mode", "DEMO"),
        status_prediction=result["status"],
        severity_prediction=result["severity"],
        raw_probabilities=result["raw_probabilities"],
        calibrated_probabilities=result["calibrated_probabilities"],
        primary_risk_score=float(result["risk_score"]),
        confidence=result.get("confidence", "moderate"),
        inference_ms=float(result.get("inference_ms") or (datetime.now(UTC) - started).total_seconds() * 1000),
        input_hash=_input_hash(payload),
        feature_schema_version=result.get("feature_schema_version", "fs-2026-001"),
        calibration_version=result.get("calibration_version", "demo-temp-v1"),
    )
    db.add(prediction)
    db.flush()

    embedding = result.get("latent_embedding") or []
    x, y = _project(embedding)
    v4_embedding = result.get("model_version") == "GA-RGCA-v4-Rolling-RSL"
    db.add(
        LatentEmbedding(
            visit_id=visit.id,
            prediction_id=prediction.id,
            model_version_id=model.id,
            embedding_space_id="ga-rgca-v4-rolling-rsl-fused-latent" if v4_embedding else model.embedding_space_id,
            embedding_dimension=len(embedding) or model.embedding_dimension,
            embedding=embedding,
            projection_x=x,
            projection_y=y,
            projection_version="ga-rgca-v4-fused-latent-v1" if v4_embedding else DEMO_PROJECTION_VERSION,
        )
    )

    visit.status = VisitStatus.PREDICTED
    visit.model_version_id = model.id

    _update_trajectory(db, child, visit, prediction, model)
    from app.integrations.common.enqueue import enqueue_c4_prediction_observation

    enqueue_c4_prediction_observation(db, child=child, visit=visit, prediction=prediction, model=model)
    write_audit(
        db,
        action=AuditAction.PREDICTION_GENERATED,
        resource_type="prediction",
        resource_id=str(prediction.id),
        user_id=user_id,
        facility_id=child.facility_id,
        metadata={"visit_id": str(visit.id), "mode": prediction.mode},
        ip=ip,
    )
    return prediction


def _project(embedding: list[float]) -> tuple[float | None, float | None]:
    if not embedding:
        return None, None
    # Deterministic 2D reference projection for demo/PCA-like display.
    n = len(embedding)
    x = sum(embedding[i] * (1 if i % 2 == 0 else -1) for i in range(n)) / n
    y = sum(embedding[i] * (1 if i % 3 == 0 else -0.5) for i in range(n)) / n
    return float(x), float(y)


def _update_trajectory(db: Session, child: Child, visit: Visit, prediction: Prediction, model: ModelVersion) -> TrajectoryMetric:
    policy = load_clinical_policy()
    visits = db.scalars(
        select(Visit)
        .where(Visit.child_id == child.id, Visit.status == VisitStatus.PREDICTED)
        .order_by(Visit.visit_number)
        .options(joinedload(Visit.predictions))
    ).unique().all()
    predicted = [v for v in visits if v.id != visit.id] + [visit]
    predicted.sort(key=lambda v: v.visit_number)

    is_baseline = visit.visit_number == 1 or len(predicted) == 1
    previous = predicted[-2] if len(predicted) >= 2 else None
    baseline = predicted[0]
    prev_active = _active_prediction(previous) if previous else None
    base_active = _active_prediction(baseline)

    previous_model = previous.model_version_id if previous else None
    compatible = previous_model is None or previous_model == model.id or _compatible(db, previous_model, model)
    if prev_active is not None:
        prev_mode = prev_active.mode.value if hasattr(prev_active.mode, "value") else prev_active.mode
        new_mode = prediction.mode.value if hasattr(prediction.mode, "value") else prediction.mode
        if str(prev_mode) != str(new_mode):
            compatible = False
        previous_version = _stored_model_version(prev_active)
        current_version = _stored_model_version(prediction)
        if previous_version and current_version and previous_version != current_version:
            compatible = False

    months = None
    months_from_baseline = None
    warning = None
    try:
        if previous:
            months = elapsed_months(previous.visit_date, visit.visit_date)
        if baseline.id != visit.id:
            months_from_baseline = elapsed_months(baseline.visit_date, visit.visit_date)
    except LongitudinalError as exc:
        warning = str(exc)
        months = None

    consecutive = _consecutive_stagnation_count(db, child.id) if previous else 0
    evaluation = classify_progress(
        is_baseline=is_baseline,
        previous_risk=prev_active.primary_risk_score if prev_active else None,
        current_risk=prediction.primary_risk_score,
        baseline_risk=base_active.primary_risk_score if base_active else None,
        months=months,
        months_from_baseline=months_from_baseline,
        stagnation_threshold=policy.stagnation_threshold,
        deterioration_delta=policy.deterioration_delta,
        consecutive_near_zero=consecutive + 1,
        consecutive_required=policy.consecutive_followups,
        model_compatible=compatible,
    )
    if warning:
        evaluation.warning = warning

    metric = TrajectoryMetric(
        child_id=child.id,
        from_visit_id=previous.id if previous else None,
        to_visit_id=visit.id,
        baseline_visit_id=baseline.id,
        risk_velocity=evaluation.risk_velocity,
        baseline_recovery_rate=evaluation.baseline_recovery_rate,
        elapsed_days=int((months or 0) * 30.4375) if months else None,
        elapsed_months=evaluation.elapsed_months,
        previous_risk=prev_active.primary_risk_score if prev_active else None,
        current_risk=prediction.primary_risk_score,
        progress_state=evaluation.progress_state,
        model_compatible=compatible,
        warning=evaluation.warning,
    )
    db.add(metric)
    db.flush()

    _maybe_create_alerts(db, child, visit, prediction, prev_active, base_active, evaluation, policy, consecutive)
    _schedule_follow_up(db, child, visit, policy)
    _emit_event(
        db,
        IntegrationEventType.TRAJECTORY_UPDATED,
        {
            "child_id": child.pseudonymous_id,
            "visit_id": str(visit.id),
            "progress_state": evaluation.progress_state.value,
            "risk_velocity": evaluation.risk_velocity,
        },
    )
    return metric


def _active_prediction(visit: Visit | None) -> Prediction | None:
    if visit is None:
        return None
    for pred in visit.predictions:
        if pred.is_active:
            return pred
    return visit.predictions[-1] if visit.predictions else None


def _compatible(db: Session, previous_id, current: ModelVersion) -> bool:
    previous = db.get(ModelVersion, previous_id)
    if previous is None:
        return False
    if previous.embedding_space_id == current.embedding_space_id:
        return True
    compat = current.compatible_with or []
    return previous.version in compat or str(previous.id) in compat


def _consecutive_stagnation_count(db: Session, child_id) -> int:
    rows = db.scalars(
        select(TrajectoryMetric).where(TrajectoryMetric.child_id == child_id).order_by(TrajectoryMetric.created_at.desc())
    ).all()
    count = 0
    for row in rows:
        if row.progress_state in {ProgressState.STAGNATING, ProgressState.STABLE}:
            count += 1
        else:
            break
    return count


def _maybe_create_alerts(db, child, visit, prediction, prev_active, base_active, evaluation, policy, consecutive) -> None:
    created: list[AlertType] = []
    if stagnation_alert(
        progress_state=evaluation.progress_state,
        consecutive_stagnating=consecutive + 1,
        policy=policy,
    ):
        created.append(AlertType.STAGNATION)
        _emit_event(db, IntegrationEventType.PROGRESS_STAGNATING, {"child_id": child.pseudonymous_id})
    if evaluation.progress_state != ProgressState.INCOMPATIBLE_MODEL and deterioration_alert(
        previous_risk=prev_active.primary_risk_score if prev_active else None,
        current_risk=prediction.primary_risk_score,
        policy=policy,
    ):
        created.append(AlertType.DETERIORATION)
        _emit_event(db, IntegrationEventType.PROGRESS_DETERIORATING, {"child_id": child.pseudonymous_id})
    improved = False
    if base_active:
        improved = (base_active.primary_risk_score - prediction.primary_risk_score) >= policy.relapse_prior_improvement
    if evaluation.progress_state != ProgressState.INCOMPATIBLE_MODEL and relapse_alert(
        improved_from_baseline=improved,
        previous_risk=prev_active.primary_risk_score if prev_active else None,
        current_risk=prediction.primary_risk_score,
        policy=policy,
    ):
        created.append(AlertType.RELAPSE)

    for alert_type in created:
        key = event_window_key(str(child.id), alert_type, str(visit.id))
        existing = db.scalar(select(Alert).where(Alert.event_window_key == key))
        if existing:
            continue
        prev = prev_active.primary_risk_score if prev_active else None
        calibrated = prediction.calibrated_probabilities if isinstance(prediction.calibrated_probabilities, dict) else {}
        ga_block = calibrated.get("ga_rgca") if isinstance(calibrated, dict) else None
        predicted_risk = isinstance(ga_block, dict) and ga_block.get("prediction_source") in {
            "GA-RGCA-v3",
            "GA-RGCA-v4-Rolling-RSL",
        }
        message = {
            AlertType.STAGNATION: "Progress stagnation detected",
            AlertType.DETERIORATION: (
                "Predicted 12-month risk increased. This alert does not use a change in weight or height."
                if predicted_risk
                else "Deterioration detected"
            ),
            AlertType.RELAPSE: "Possible relapse / regression",
        }[alert_type]
        trigger_value = {
            "previous_risk": prev,
            "current_risk": prediction.primary_risk_score,
            "risk_velocity": evaluation.risk_velocity,
            "policy_id": policy.policy_id,
        }
        if predicted_risk and alert_type == AlertType.DETERIORATION:
            trigger_value["basis"] = "predicted_risk_change"
            trigger_value["observed_growth"] = "not_used"
        alert = Alert(
            child_id=child.id,
            visit_id=visit.id,
            facility_id=child.facility_id,
            type=alert_type,
            severity=severity_for(alert_type, policy),
            status=AlertStatus.OPEN,
            message=message,
            trigger_value=trigger_value,
            threshold_version=policy.policy_id,
            event_window_key=key,
        )
        db.add(alert)
        db.flush()
        _notify_facility(db, child, alert)
        _emit_event(
            db,
            IntegrationEventType.ALERT_CREATED,
            {"child_id": child.pseudonymous_id, "type": alert_type.value, "alert_id": str(alert.id)},
        )


def _schedule_follow_up(db: Session, child: Child, visit: Visit, policy) -> None:
    expected = (visit.visit_date + timedelta(days=policy.default_followup_days)).date()
    existing_open = db.scalars(
        select(FollowUpSchedule).where(
            FollowUpSchedule.child_id == child.id,
            FollowUpSchedule.status.in_(
                [
                    FollowUpStatus.SUGGESTED,
                    FollowUpStatus.SCHEDULED,
                    FollowUpStatus.OVERDUE,
                    FollowUpStatus.RESCHEDULED,
                ]
            ),
        )
    ).all()
    for row in existing_open:
        row.status = FollowUpStatus.COMPLETED
    db.add(
        FollowUpSchedule(
            child_id=child.id,
            facility_id=child.facility_id,
            expected_date=expected,
            interval_days=policy.default_followup_days,
            responsible_user_id=child.assigned_doctor_id,
            status=FollowUpStatus.SUGGESTED,
            notes="System-suggested after assessment — confirm or change in clinic workflow.",
        )
    )


def _notify_facility(db: Session, child: Child, alert: Alert) -> None:
    """Route clinical alerts to assigned clinician first; fall back to facility clinical inbox.

    Fallback recipients: facility doctors + facility admins with alert access.
    Does not notify caregivers. Does not broadcast to every facility user.
    """
    from app.models.identity import User
    from app.models.enums import UserRole, UserStatus

    recipients: list[User] = []
    if child.assigned_doctor_id:
        assigned = db.get(User, child.assigned_doctor_id)
        if assigned and assigned.status == UserStatus.ACTIVE:
            recipients = [assigned]
            alert.assigned_to = assigned.id

    if not recipients:
        recipients = list(
            db.scalars(
                select(User).where(
                    User.facility_id == child.facility_id,
                    User.status == UserStatus.ACTIVE,
                    User.role.in_([UserRole.DOCTOR, UserRole.FACILITY_ADMIN]),
                )
            ).all()
        )
        if recipients and alert.assigned_to is None:
            # Facility clinical inbox fallback — assign to first doctor if present.
            doctor = next((u for u in recipients if u.role == UserRole.DOCTOR), recipients[0])
            alert.assigned_to = doctor.id

    for user in recipients:
        db.add(
            Notification(
                user_id=user.id,
                channel=NotificationChannel.IN_APP,
                title=alert.message,
                body=f"{child.pseudonymous_id}: {alert.message}",
                severity=alert.severity.value,
                resource_type="alert",
                resource_id=str(alert.id),
            )
        )


def _emit_event(db: Session, event_type: IntegrationEventType, payload: dict) -> None:
    db.add(IntegrationEvent(event_type=event_type, payload=payload, target="internal"))


def evaluate_missed_followups(db: Session) -> int:
    """Idempotent missed follow-up evaluation used by the worker."""
    from datetime import date

    policy = load_clinical_policy()
    today = date.today()
    due = db.scalars(
        select(FollowUpSchedule).where(
            FollowUpSchedule.status.in_([FollowUpStatus.SCHEDULED, FollowUpStatus.RESCHEDULED]),
            FollowUpSchedule.expected_date < today,
        )
    ).all()
    created = 0
    for sched in due:
        grace_end = sched.expected_date.toordinal() + policy.overdue_grace_days
        if today.toordinal() < grace_end:
            continue
        sched.status = FollowUpStatus.OVERDUE
        child = db.get(Child, sched.child_id)
        if child is None:
            continue
        key = event_window_key(str(child.id), AlertType.MISSED_FOLLOW_UP, None, extra=str(sched.id))
        existing = db.scalar(select(Alert).where(Alert.event_window_key == key))
        if existing:
            continue
        alert = Alert(
            child_id=child.id,
            facility_id=child.facility_id,
            type=AlertType.MISSED_FOLLOW_UP,
            severity=severity_for(AlertType.MISSED_FOLLOW_UP, policy),
            status=AlertStatus.OPEN,
            message="Follow-up overdue",
            trigger_value={
                "expected_date": sched.expected_date.isoformat(),
                "grace_period_days": policy.overdue_grace_days,
                "disclaimer": policy.disclaimer,
            },
            threshold_version=policy.policy_id,
            event_window_key=key,
        )
        db.add(alert)
        _notify_facility(db, child, alert)
        _emit_event(db, IntegrationEventType.FOLLOWUP_OVERDUE, {"child_id": child.pseudonymous_id})
        created += 1
    db.commit()
    return created
