from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.core.policy import load_registration_config
from app.core.security import FieldEncryptor
from app.models.enums import AuditAction, EntityStatus, FollowUpStatus, ModelStatus, Sex, UserRole, UserStatus
from app.models.identity import Facility, User
from app.models.intelligence import Prediction, TrajectoryMetric
from app.models.operations import Alert, FollowUpSchedule
from app.models.paediatric import Child, Caregiver, Visit
from app.schemas.common import ChildCreate, ChildListItem, ChildUpdate, ChildrenListPage
from app.security.rbac import assert_child_access, facility_scope_ids
from app.services.audit import write_audit
from app.services.child_list import active_model_is_demo, build_list_item, child_is_synthetic, list_summary
from app.services.malnutrition_type import prediction_api_fields
from app.services.model_display import get_model_output_display_metadata
from app.services.child_profile import (
    ALERT_HEADLINES,
    ANTHRO_FIELDS,
    DIETARY_FIELDS,
    MCH_FIELDS,
    SOCIO_FIELDS,
    calibrated_status_probabilities,
    count_fields,
    data_quality_label,
    follow_up_overdue_days,
    probability_delta_pp,
    progress_display,
    record_as_inputs,
    risk_velocity_pp_month,
    since_baseline_pp,
)

router = APIRouter(prefix="/children", tags=["children"])


def _next_pseudo(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(Child)) or 0
    return f"C-{1100 + count}"


def _age_months(dob: date, on: date | None = None) -> int:
    ref = on or date.today()
    return max(0, (ref.year - dob.year) * 12 + (ref.month - dob.month))


def _external_id_hash(facility_id: UUID, external_patient_id: str) -> str:
    raw = f"{facility_id}:{external_patient_id.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.get("/registration-options")
def registration_options(db: Session = Depends(get_db), current=Depends(require_permission("child:write"))):
    cfg = load_registration_config()
    facility = db.get(Facility, current.user.facility_id)
    doctors = db.scalars(
        select(User).where(
            User.facility_id == current.user.facility_id,
            User.role == UserRole.DOCTOR,
            User.status == UserStatus.ACTIVE,
            User.deleted_at.is_(None),
        )
    ).all()
    district = facility.district if facility else None
    moh_map = cfg.get("moh_areas", {})
    moh_areas = moh_map.get(district, moh_map.get("default", [])) if district else moh_map.get("default", [])
    return {
        "facility": {
            "id": str(current.user.facility_id),
            "name": facility.name if facility else None,
            "code": facility.code if facility else None,
            "district": district,
        },
        "care_teams": cfg.get("care_teams", []),
        "caregiver_relationships": cfg.get("caregiver_relationships", []),
        "districts": cfg.get("districts", []),
        "moh_areas": moh_areas,
        "doctors": [{"id": str(d.id), "full_name": d.full_name, "email": d.email} for d in doctors],
        "current_user_id": str(current.user.id),
    }


def _displayed_status(item: dict) -> str:
    status = (item.get("current_status") or "").strip().lower().replace(" ", "_")
    severity = (item.get("severity") or "").strip().lower()
    if status == "severe_wasting" or (status == "wasting" and severity == "severe"):
        return "sam"
    if status in {"wasting", "mild_wasting", "moderate_wasting"}:
        return "mam"
    return status


@router.get("", response_model=ChildrenListPage)
def list_children(
    q: str | None = None,
    facility: str | None = None,
    age_band: str | None = None,
    nutritional_status: str | None = None,
    risk: str | None = None,
    progress: str | None = None,
    alert_type: str | None = None,
    has_open_alert: bool | None = None,
    attention: str | None = None,
    review_status: str | None = Query(None, alias="review_status"),
    requires_my_attention: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("priority", pattern="^(priority|latest_assessment|probability|progress|follow_up|pseudonymous_id)$"),
    db: Session = Depends(get_db),
    current=Depends(require_permission("child:read")),
):
    stmt = select(Child).where(Child.deleted_at.is_(None))
    scope = facility_scope_ids(current)
    if scope:
        stmt = stmt.where(Child.facility_id.in_(scope))
    if facility:
        fac = db.scalar(select(Facility).where(Facility.code == facility))
        if fac:
            stmt = stmt.where(Child.facility_id == fac.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Child.pseudonymous_id.ilike(like)))

    rows = [c for c in db.scalars(stmt.order_by(Child.pseudonymous_id)).all() if not child_is_synthetic(c)]
    demo = active_model_is_demo(db)
    items = [build_list_item(db, c, model_is_demo=demo) for c in rows]

    if nutritional_status:
        want = nutritional_status.lower()
        items = [i for i in items if _displayed_status(i) == want]
    if progress:
        if progress == "insufficient_history":
            items = [i for i in items if i.get("progress_display") == "insufficient_history"]
        else:
            items = [i for i in items if (i.get("progress") or "").lower() == progress.lower()]
    if alert_type:
        items = [i for i in items if any(a["type"] == alert_type for a in i.get("clinical_attention") or [])]
    if has_open_alert:
        items = [i for i in items if i.get("clinical_attention")]
    if attention == "requires_attention":
        items = [i for i in items if i.get("requires_attention")]
    elif attention == "no_alert":
        items = [i for i in items if not i.get("clinical_attention")]
    elif attention == "follow_up_overdue":
        items = [i for i in items if i.get("follow_up_display_status") == "overdue"]
    if review_status:
        items = [i for i in items if i.get("clinician_review_status") == review_status]
    if requires_my_attention:
        items = [i for i in items if i.get("requires_attention")]
    if risk == "high":
        items = [i for i in items if (i.get("current_risk") or 0) >= 0.6]
    if age_band:
        items = [i for i in items if _band(i["age_months"]) == age_band]

    summary_data = list_summary(items)
    summary_data["model_is_demo"] = demo

    if sort == "priority":
        items.sort(key=lambda i: (-i.get("priority_score", 0), i.get("pseudonymous_id", "")))
    elif sort == "latest_assessment":
        items.sort(key=lambda i: (i.get("last_visit") is None, i.get("last_visit") or ""), reverse=True)
    elif sort == "probability":
        items.sort(key=lambda i: i.get("current_risk") if i.get("current_risk") is not None else -1, reverse=True)
    elif sort == "progress":
        items.sort(key=lambda i: -i.get("priority_score", 0))
    elif sort == "follow_up":
        items.sort(
            key=lambda i: (
                i.get("follow_up_display_status") != "overdue",
                i.get("next_follow_up") is None,
                i.get("next_follow_up") or "",
            )
        )
    else:
        items.sort(key=lambda i: i.get("pseudonymous_id", ""))

    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]

    return ChildrenListPage(
        items=[ChildListItem.model_validate(i) for i in page_items],
        total=total,
        page=page,
        page_size=page_size,
        summary=summary_data,
    )


def _band(age: int) -> str:
    if age < 6:
        return "0-5"
    if age < 12:
        return "6-11"
    if age < 24:
        return "12-23"
    return "24-59"


@router.post("", status_code=201)
def create_child(body: ChildCreate, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("child:write"))):
    facility_id = body.facility_id or current.user.facility_id
    if str(facility_id) != current.facility_id and not current.can("child:read_any"):
        raise HTTPException(status_code=403, detail="Cannot register a child in another facility")
    if body.sex not in {s.value for s in Sex}:
        raise HTTPException(status_code=422, detail="Invalid sex value")
    enc = FieldEncryptor(get_settings().encryption_key)
    ext_hash = _external_id_hash(facility_id, body.external_patient_id)
    existing = db.scalar(
        select(Child).where(
            Child.facility_id == facility_id,
            Child.external_patient_id_hash == ext_hash,
            Child.deleted_at.is_(None),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Hospital / Patient ID already registered at this facility")

    assigned_doctor_id = body.assigned_doctor_id or current.user.id
    if assigned_doctor_id:
        doctor = db.get(User, assigned_doctor_id)
        if doctor is None or doctor.facility_id != facility_id or doctor.role != UserRole.DOCTOR:
            raise HTTPException(status_code=422, detail="Assigned doctor must be an active doctor at this facility")

    child = Child(
        facility_id=facility_id,
        pseudonymous_id=_next_pseudo(db),
        external_patient_id_encrypted=enc.encrypt(body.external_patient_id),
        external_patient_id_hash=ext_hash,
        full_name_encrypted=enc.encrypt(body.full_name),
        date_of_birth=body.date_of_birth,
        sex=Sex(body.sex),
        status=EntityStatus.ACTIVE,
        responsible_team=body.responsible_team,
        district=body.district,
        moh_area=body.moh_area,
        phm_area=body.phm_area,
        assigned_doctor_id=assigned_doctor_id,
        registered_by=current.id,
    )
    db.add(child)
    db.flush()
    db.add(
        Caregiver(
            child_id=child.id,
            kinship=body.caregiver_relationship,
            display_name=body.caregiver_display_name,
            phone_encrypted=enc.encrypt(body.caregiver_phone) if body.caregiver_phone else None,
            reminder_consent=body.reminder_consent,
        )
    )
    write_audit(
        db,
        action=AuditAction.CHILD_CREATED,
        resource_type="child",
        resource_id=child.pseudonymous_id,
        user_id=current.id,
        role=current.role.value,
        facility_id=facility_id,
        ip=request.client.host if request.client else None,
    )
    return {
        "id": str(child.id),
        "pseudonymous_id": child.pseudonymous_id,
        "has_baseline": False,
        "message": "Child registered successfully. No nutritional assessment has been recorded yet.",
    }


@router.get("/{child_id}")
def get_child(child_id: UUID, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    child = db.get(Child, child_id)
    if child is None or child.deleted_at or child_is_synthetic(child):
        raise HTTPException(status_code=404, detail="Child not found")
    assert_child_access(current, child)
    write_audit(
        db,
        action=AuditAction.CHILD_VIEWED,
        resource_type="child",
        resource_id=child.pseudonymous_id,
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
    )
    return _child_profile(db, child)


@router.patch("/{child_id}")
def patch_child(child_id: UUID, body: ChildUpdate, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("child:write"))):
    child = db.get(Child, child_id)
    if child is None or child.deleted_at:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_child_access(current, child)
    data = body.model_dump(exclude_unset=True)
    enc = FieldEncryptor(get_settings().encryption_key)
    if "full_name" in data and data["full_name"]:
        child.full_name_encrypted = enc.encrypt(data["full_name"])
    if "date_of_birth" in data and data["date_of_birth"] is not None:
        child.date_of_birth = data["date_of_birth"]
    if "sex" in data and data["sex"] is not None:
        if data["sex"] not in {item.value for item in Sex}:
            raise HTTPException(status_code=422, detail="Invalid sex value")
        child.sex = Sex(data["sex"])
    if "responsible_team" in data and data["responsible_team"] is not None:
        child.responsible_team = data["responsible_team"]
    if "status" in data and data["status"] is not None:
        try:
            child.status = EntityStatus(data["status"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid status") from exc
    if "external_patient_id" in data and data["external_patient_id"]:
        ext_hash = _external_id_hash(child.facility_id, data["external_patient_id"])
        clash = db.scalar(
            select(Child).where(
                Child.facility_id == child.facility_id,
                Child.external_patient_id_hash == ext_hash,
                Child.deleted_at.is_(None),
                Child.id != child.id,
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Hospital / Patient ID already registered at this facility")
        child.external_patient_id_encrypted = enc.encrypt(data["external_patient_id"])
        child.external_patient_id_hash = ext_hash
    if "district" in data:
        child.district = data["district"] or None
    if "moh_area" in data:
        child.moh_area = data["moh_area"] or None
    if "phm_area" in data:
        child.phm_area = data["phm_area"] or None
    if "assigned_doctor_id" in data and data["assigned_doctor_id"] is not None:
        doctor = db.get(User, data["assigned_doctor_id"])
        if doctor is None or doctor.facility_id != child.facility_id or doctor.role != UserRole.DOCTOR:
            raise HTTPException(status_code=422, detail="Assigned doctor must be an active doctor at this facility")
        child.assigned_doctor_id = data["assigned_doctor_id"]
    caregiver_fields = {"caregiver_relationship", "caregiver_display_name", "caregiver_phone", "reminder_consent"}
    if caregiver_fields & data.keys():
        caregiver = db.scalar(select(Caregiver).where(Caregiver.child_id == child.id))
        if caregiver is None:
            caregiver = Caregiver(child_id=child.id, kinship=data.get("caregiver_relationship") or "Mother")
            db.add(caregiver)
        if data.get("caregiver_relationship"):
            caregiver.kinship = data["caregiver_relationship"]
        if "caregiver_display_name" in data:
            caregiver.display_name = data["caregiver_display_name"] or None
        if "caregiver_phone" in data:
            caregiver.phone_encrypted = enc.encrypt(data["caregiver_phone"]) if data["caregiver_phone"] else None
        if "reminder_consent" in data and data["reminder_consent"] is not None:
            caregiver.reminder_consent = data["reminder_consent"]
    write_audit(
        db,
        action=AuditAction.CHILD_CHANGED,
        resource_type="child",
        resource_id=child.pseudonymous_id,
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "pseudonymous_id": child.pseudonymous_id}


@router.delete("/{child_id}")
def delete_child(child_id: UUID, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("child:write"))):
    child = db.get(Child, child_id)
    if child is None or child.deleted_at:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_child_access(current, child)
    child.deleted_at = datetime.now(UTC)
    open_follow_ups = db.scalars(
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
    for follow_up in open_follow_ups:
        follow_up.status = FollowUpStatus.CANCELLED
    write_audit(
        db,
        action=AuditAction.CHILD_REMOVED,
        resource_type="child",
        resource_id=child.pseudonymous_id,
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "pseudonymous_id": child.pseudonymous_id}


def _child_profile(db: Session, child: Child) -> dict:
    from app.models.identity import User
    from app.models.intelligence import LatentEmbedding, ModelVersion
    from app.models.operations import ClinicalNote

    enc = FieldEncryptor(get_settings().encryption_key)
    facility = db.get(Facility, child.facility_id)
    caregiver = db.scalar(select(Caregiver).where(Caregiver.child_id == child.id))
    assigned = db.get(User, child.assigned_doctor_id) if child.assigned_doctor_id else None
    visits = db.scalars(
        select(Visit)
        .where(Visit.child_id == child.id)
        .options(
            joinedload(Visit.anthropometry),
            joinedload(Visit.socioeconomic),
            joinedload(Visit.dietary),
            joinedload(Visit.maternal_child_health),
        )
        .order_by(Visit.visit_number)
    ).unique().all()
    notes = db.scalars(select(ClinicalNote).where(ClinicalNote.child_id == child.id).order_by(ClinicalNote.created_at.desc())).all()
    authors = {}
    for note in notes:
        if note.author_id and note.author_id not in authors:
            authors[note.author_id] = db.get(User, note.author_id)

    def _review_for_visit(visit: Visit, next_visit: Visit | None):
        from app.services.clinician_review import get_review_for_visit, serialize_review

        review = get_review_for_visit(db, visit.id)
        if review is None:
            return None
        author = db.get(User, review.reviewer_user_id)
        return serialize_review(review, author, has_prediction=True)

    history = []
    for index, visit in enumerate(visits):
        pred = db.scalar(select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True)))
        metric = db.scalar(select(TrajectoryMetric).where(TrajectoryMetric.to_visit_id == visit.id))
        emb = db.scalar(select(LatentEmbedding).where(LatentEmbedding.visit_id == visit.id))
        model = db.get(ModelVersion, visit.model_version_id) if visit.model_version_id else None
        anthro = visit.anthropometry
        next_visit = visits[index + 1] if index + 1 < len(visits) else None
        review = _review_for_visit(visit, next_visit)
        history.append(
            {
                "id": str(visit.id),
                "visit_number": visit.visit_number,
                "visit_date": visit.visit_date.isoformat(),
                "status": visit.status.value,
                "data_quality": visit.data_quality,
                "measurements": None
                if not anthro
                else {
                    "weight_kg": anthro.weight_kg,
                    "height_cm": anthro.height_cm,
                    "muac_cm": anthro.muac_cm,
                },
                "prediction": None
                if not pred
                else {
                    "risk": pred.primary_risk_score,
                    "confidence": pred.confidence,
                    "mode": pred.mode.value if hasattr(pred.mode, "value") else pred.mode,
                    "model": f"{model.model_key}-{model.version}" if model else None,
                    "run_number": pred.run_number,
                    "calibration_version": pred.calibration_version,
                    "feature_schema_version": pred.feature_schema_version,
                    "calibrated_status_probabilities": calibrated_status_probabilities(pred.calibrated_probabilities),
                    **prediction_api_fields(pred),
                },
                "progress": metric.progress_state.value if metric else None,
                "risk_velocity": metric.risk_velocity if metric else None,
                "baseline_recovery_rate": metric.baseline_recovery_rate if metric else None,
                "model_compatible": metric.model_compatible if metric else None,
                "warning": metric.warning if metric else None,
                "embedding_space_id": emb.embedding_space_id if emb else None,
                "projection_version": emb.projection_version if emb else None,
                "projection": {"x": emb.projection_x, "y": emb.projection_y} if emb else None,
                "review_status": review["status"] if review else ("AWAITING_REVIEW" if pred else "NOT_REQUIRED"),
                "clinician_review": review,
            }
        )
    latest = history[-1] if history else None
    previous = history[-2] if len(history) >= 2 else None
    has_baseline = len(history) > 0
    follow = db.scalar(
        select(FollowUpSchedule)
        .where(
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
        .order_by(FollowUpSchedule.expected_date.desc())
        .limit(1)
    )
    alerts = db.scalars(select(Alert).where(Alert.child_id == child.id).order_by(Alert.created_at.desc())).all()
    baseline_risk = history[0]["prediction"]["risk"] if history and history[0]["prediction"] else None
    current_risk = latest["prediction"]["risk"] if latest and latest["prediction"] else None
    previous_risk = previous["prediction"]["risk"] if previous and previous["prediction"] else None
    spaces = {h["embedding_space_id"] for h in history if h["embedding_space_id"]}
    latest_metric_compatible = latest.get("model_compatible") if latest else None
    comparable = True
    if len(spaces) > 1 or latest_metric_compatible is False:
        comparable = False
    model_warning = None
    if len(spaces) > 1:
        model_warning = "Longitudinal comparison unavailable. The active model changed between these assessments."
    elif latest and latest.get("warning"):
        model_warning = latest["warning"]

    predicted_count = sum(1 for h in history if h.get("prediction"))
    progress_state = latest["progress"] if latest else None
    latest_visit = visits[-1] if visits else None
    latest_model = db.get(ModelVersion, latest_visit.model_version_id) if latest_visit and latest_visit.model_version_id else None
    if latest_model is None:
        latest_model = db.scalar(select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE).limit(1))

    quality = latest_visit.data_quality if latest_visit else None
    modalities = None
    latest_inputs = None
    if latest_visit:
        modalities = {
            "anthropometric": count_fields(latest_visit.anthropometry, ANTHRO_FIELDS),
            "socioeconomic": count_fields(latest_visit.socioeconomic, SOCIO_FIELDS),
            "dietary": count_fields(latest_visit.dietary, DIETARY_FIELDS),
            "maternal_child_health": count_fields(latest_visit.maternal_child_health, MCH_FIELDS),
        }
        latest_inputs = {
            "anthropometric": record_as_inputs(latest_visit.anthropometry, ANTHRO_FIELDS),
            "socioeconomic": record_as_inputs(latest_visit.socioeconomic, SOCIO_FIELDS),
            "dietary": record_as_inputs(latest_visit.dietary, DIETARY_FIELDS),
            "maternal_child_health": record_as_inputs(latest_visit.maternal_child_health, MCH_FIELDS),
        }

    latest_review = _review_for_visit(latest_visit, None) if latest_visit else None
    if latest and latest.get("prediction") and latest_review is None:
        clinician_review = {"status": "AWAITING_REVIEW"}
    elif latest_review:
        clinician_review = latest_review
    else:
        clinician_review = {"status": "NOT_REQUIRED"}

    today = date.today()
    overdue = follow_up_overdue_days(follow.expected_date if follow else None, follow.status.value if follow else None, today)
    synthetic = bool(quality.get("synthetic")) if isinstance(quality, dict) else False

    return {
        "id": str(child.id),
        "pseudonymous_id": child.pseudonymous_id,
        "full_name": enc.decrypt(child.full_name_encrypted) if child.full_name_encrypted else None,
        "external_patient_id": enc.decrypt(child.external_patient_id_encrypted) if child.external_patient_id_encrypted else None,
        "age_months": _age_months(child.date_of_birth),
        "sex": child.sex.value,
        "date_of_birth": child.date_of_birth.isoformat(),
        "facility": {"name": facility.name, "code": facility.code, "district": facility.district} if facility else None,
        "responsible_team": child.responsible_team,
        "district": child.district,
        "moh_area": child.moh_area,
        "phm_area": child.phm_area,
        "assigned_doctor": {"id": str(assigned.id), "full_name": assigned.full_name} if assigned else None,
        "caregiver": None
        if not caregiver
        else {
            "relationship": caregiver.kinship,
            "display_name": caregiver.display_name,
            "phone": enc.decrypt(caregiver.phone_encrypted) if caregiver.phone_encrypted else None,
            "reminder_consent": caregiver.reminder_consent,
        },
        "has_baseline": has_baseline,
        "visit_count": len(history),
        "assessment_count": predicted_count,
        "current": latest,
        "previous": previous,
        "risk_change_pp": probability_delta_pp(current_risk, previous_risk) if comparable else None,
        "risk_velocity_pp_month": risk_velocity_pp_month(latest["risk_velocity"] if latest else None) if comparable else None,
        "since_baseline_pp": since_baseline_pp(current_risk, baseline_risk, predicted_count) if comparable else None,
        "progress_display": progress_display(progress_state, predicted_count, comparable),
        "longitudinal_comparable": comparable,
        "next_follow_up": follow.expected_date.isoformat() if follow else None,
        "follow_up_status": follow.status.value if follow else None,
        "follow_up_id": str(follow.id) if follow else None,
        "follow_up_overdue_days": overdue,
        "visits": history,
        "model_warning": model_warning,
        "model_is_demo": False
        if isinstance((latest or {}).get("prediction"), dict) and (latest or {}).get("prediction", {}).get("ga_rgca")
        else (bool(latest_model.is_demo) if latest_model else active_model_is_demo(db)),
        "display_semantics": get_model_output_display_metadata(
            model_mode="ga_rgca" if isinstance((latest or {}).get("prediction"), dict) and (latest or {}).get("prediction", {}).get("ga_rgca") else None,
            is_demo=False
            if isinstance((latest or {}).get("prediction"), dict) and (latest or {}).get("prediction", {}).get("ga_rgca")
            else True,
        ),
        "synthetic_data": synthetic,
        "data_quality": quality,
        "data_quality_label": data_quality_label(quality),
        "modalities": modalities,
        "latest_inputs": latest_inputs,
        "clinician_review": clinician_review,
        "model": None
        if not latest_model
        else {
            "key": latest_model.model_key,
            "version": latest_model.version,
            "label": f"{latest_model.model_key}-{latest_model.version}",
            "architecture": latest_model.architecture,
            "embedding_dimension": latest_model.embedding_dimension,
            "embedding_space_id": latest_model.embedding_space_id,
            "calibration_version": latest_model.calibration_version,
            "feature_schema_version": latest_model.feature_schema_version,
            "is_demo": latest_model.is_demo,
            "status": latest_model.status.value if hasattr(latest_model.status, "value") else latest_model.status,
        },
        "alerts": [
            {
                "id": str(a.id),
                "type": a.type.value,
                "severity": a.severity.value,
                "status": a.status.value,
                "message": a.message,
                "headline": ALERT_HEADLINES.get(a.type.value, a.message),
                "created_at": a.created_at.isoformat(),
                "trigger_value": a.trigger_value,
            }
            for a in alerts
        ],
        "notes": [
            {"id": str(n.id), "body": n.body, "created_at": n.created_at.isoformat(), "author_id": str(n.author_id)}
            for n in notes
        ],
    }

