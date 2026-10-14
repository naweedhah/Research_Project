from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import FieldEncryptor
from app.core.deps import require_permission
from app.core.policy import load_clinical_policy
from app.integrations.common.outbox import kick_delivery_best_effort, pop_scheduled_delivery_ids
from app.models.enums import AuditAction, Sex, VisitStatus, VisitType
from app.models.paediatric import (
    AnthropometricRecord,
    Child,
    DietaryRecord,
    MaternalChildHealthRecord,
    SocioeconomicRecord,
    Visit,
)
from app.schemas.common import VisitCorrection, VisitCreate, VisitOut
from app.security.rbac import assert_child_access
from app.services.audit import write_audit
from app.services.malnutrition_type import prediction_api_fields
from app.services.prediction import run_inference
from app.services.quality import validate_visit_payload

router = APIRouter(tags=["visits"])


def _context_dict(body: VisitCreate, previous: Visit | None) -> dict:
    """Keep only answers entered for this visit. A blank field stays unrecorded."""
    del previous
    incoming = body.ga_rgca_context.model_dump() if body.ga_rgca_context else {}
    return {key: value for key, value in incoming.items() if value not in (None, "")}


def _quality_with_context(quality: dict, body: VisitCreate, previous: Visit | None) -> dict:
    context = _context_dict(body, previous)
    if not context:
        return quality
    stored = dict(quality)
    stored["ga_rgca_context"] = context
    return stored


def _visit_number(db: Session, child_id) -> int:
    last = db.scalar(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number.desc()).limit(1))
    return 1 if last is None else last.visit_number + 1


@router.get("/children/{child_id}/visits/prefill")
def visit_prefill(child_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("visit:read"))):
    """Return child context and last visit modality data for follow-up entry."""
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    last = db.scalar(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number.desc()).limit(1))
    age_months = (last.visit_date.year - child.date_of_birth.year) * 12 + (last.visit_date.month - child.date_of_birth.month) if last else None
    if last is None:
        age_months = (date.today().year - child.date_of_birth.year) * 12 + (date.today().month - child.date_of_birth.month)
    payload = {
        "child": {
            "id": str(child.id),
            "pseudonymous_id": child.pseudonymous_id,
            "full_name": FieldEncryptor(get_settings().encryption_key).decrypt(child.full_name_encrypted)
            if child.full_name_encrypted
            else None,
            "sex": child.sex.value,
            "date_of_birth": child.date_of_birth.isoformat(),
            "age_months": age_months,
            "visit_count": 0 if last is None else last.visit_number,
            "is_baseline": last is None,
            "visit_label": "V1" if last is None else f"V{last.visit_number + 1}",
        },
        "last_visit_id": str(last.id) if last else None,
        "anthropometric": _row(last.anthropometry) if last else None,
        "socioeconomic": _row(last.socioeconomic) if last else None,
        "dietary": _row(last.dietary) if last else None,
        "maternal_child_health": _row(last.maternal_child_health) if last else None,
        "ga_rgca_context": last.data_quality.get("ga_rgca_context")
        if last and isinstance(last.data_quality, dict)
        else None,
    }
    return payload


@router.get("/children/{child_id}/visits")
def list_visits(child_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("visit:read"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    visits = db.scalars(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number)).all()
    return [
        VisitOut(
            id=v.id,
            child_id=v.child_id,
            visit_number=v.visit_number,
            visit_date=v.visit_date,
            visit_type=v.visit_type.value,
            status=v.status.value,
            scheduled=v.scheduled,
            data_quality=v.data_quality,
        )
        for v in visits
    ]


@router.post("/children/{child_id}/visits", status_code=201)
def create_visit(
    child_id: UUID,
    body: VisitCreate,
    request: Request,
    db: Session = Depends(get_db),
    current=Depends(require_permission("visit:write")),
):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    policy = load_clinical_policy()
    payload = body.model_dump()
    previous = db.scalar(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number.desc()).limit(1))
    stale = False
    if body.socioeconomic and not body.socioeconomic.household_changed and previous and previous.socioeconomic:
        payload["socioeconomic"] = {
            "wealth_proxy": previous.socioeconomic.wealth_proxy,
            "maternal_education": previous.socioeconomic.maternal_education,
            "paternal_education": previous.socioeconomic.paternal_education,
            "maternal_employment": previous.socioeconomic.maternal_employment,
            "household_size": previous.socioeconomic.household_size,
            "geographical_area": previous.socioeconomic.geographical_area,
            "drinking_water": previous.socioeconomic.drinking_water,
            "sanitation": previous.socioeconomic.sanitation,
        }
        stale = True
    report = validate_visit_payload(payload, policy, socioeconomic_stale=stale)
    if not body.save_as_draft and not report.complete:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "This visit contains values outside the configured validation range. Review the highlighted fields before continuing."
                if any(i.flag.value == "OUTLIER_REVIEW_REQUIRED" for i in report.blocking_errors)
                else "A prediction cannot be generated from the available information. Complete the required fields or request clinical review.",
                "quality": report.as_dict(),
            },
        )
    if not body.save_as_draft and not body.confirmation_attested:
        raise HTTPException(status_code=422, detail="Confirmation is required before prediction: entered information must match the clinic record.")

    visit = Visit(
        child_id=child.id,
        facility_id=child.facility_id,
        visit_number=_visit_number(db, child.id),
        visit_date=body.visit_date,
        visit_type=VisitType(body.visit_type),
        scheduled=body.scheduled,
        recorded_by=current.id,
        status=VisitStatus.DRAFT if body.save_as_draft else VisitStatus.SUBMITTED,
        confirmation_attested=body.confirmation_attested,
        data_quality=_quality_with_context(report.as_dict(), body, previous),
    )
    db.add(visit)
    db.flush()
    anthro = body.anthropometric
    db.add(
        AnthropometricRecord(
            visit_id=visit.id,
            age_months=anthro.age_months,
            sex=Sex(anthro.sex),
            height_cm=anthro.height_cm,
            weight_kg=anthro.weight_kg,
            muac_cm=anthro.muac_cm,
            birth_weight_kg=anthro.birth_weight_kg,
            head_circumference_cm=anthro.head_circumference_cm,
            previous_weight_kg=anthro.previous_weight_kg,
            previous_height_cm=anthro.previous_height_cm,
        )
    )
    socio = payload.get("socioeconomic") or {}
    context = _context_dict(body, previous)
    if context.get("maternal_education"):
        socio["maternal_education"] = context["maternal_education"]
    if context.get("mother_occupation"):
        socio["maternal_employment"] = context["mother_occupation"]
    db.add(SocioeconomicRecord(visit_id=visit.id, carried_forward=stale, **{k: socio.get(k) for k in [
        "wealth_proxy", "maternal_education", "paternal_education", "maternal_employment",
        "household_size", "geographical_area", "drinking_water", "sanitation"
    ]}))
    diet = (body.dietary.model_dump() if body.dietary else {})
    db.add(DietaryRecord(visit_id=visit.id, **diet))
    mch = (body.maternal_child_health.model_dump() if body.maternal_child_health else {})
    db.add(MaternalChildHealthRecord(visit_id=visit.id, **mch))
    write_audit(
        db,
        action=AuditAction.VISIT_CREATED,
        resource_type="visit",
        resource_id=str(visit.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"draft": body.save_as_draft, "visit_number": visit.visit_number},
    )
    db.flush()
    result = {
        "visit": VisitOut(
            id=visit.id,
            child_id=visit.child_id,
            visit_number=visit.visit_number,
            visit_date=visit.visit_date,
            visit_type=visit.visit_type.value,
            status=visit.status.value,
            scheduled=visit.scheduled,
            data_quality=visit.data_quality,
        ),
        "quality": report.as_dict(),
        "prediction": None,
    }
    if body.save_as_draft:
        return result
    db.refresh(visit)
    visit.anthropometry  # load
    prediction = run_inference(db, visit, child, current.id, request.client.host if request.client else None)
    kick_delivery_best_effort(pop_scheduled_delivery_ids(db))
    result["prediction"] = {
        "id": str(prediction.id),
        "risk": prediction.primary_risk_score,
        "confidence": prediction.confidence,
        "mode": prediction.mode.value if hasattr(prediction.mode, "value") else prediction.mode,
        "run_number": prediction.run_number,
        "inference_ms": prediction.inference_ms,
        **prediction_api_fields(prediction),
    }
    result["visit"].status = visit.status.value
    return result


def _latest_visit(db: Session, child_id: UUID) -> Visit | None:
    return db.scalar(select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_number.desc()).limit(1))


def _clear_latest_score(db: Session, visit: Visit) -> None:
    """Drop the score artifacts for this visit so a corrected assessment replaces them."""
    from app.models.intelligence import LatentEmbedding, TrajectoryMetric

    embeddings = db.scalars(select(LatentEmbedding).where(LatentEmbedding.visit_id == visit.id)).all()
    for row in embeddings:
        db.delete(row)
    metrics = db.scalars(select(TrajectoryMetric).where(TrajectoryMetric.to_visit_id == visit.id)).all()
    for row in metrics:
        db.delete(row)
    db.flush()


@router.patch("/visits/{visit_id}")
def correct_visit(
    visit_id: UUID,
    body: VisitCorrection,
    request: Request,
    db: Session = Depends(get_db),
    current=Depends(require_permission("visit:write")),
):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    if child is None or child.deleted_at:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    latest = _latest_visit(db, child.id)
    if latest is None or latest.id != visit.id:
        raise HTTPException(status_code=409, detail="Only the latest visit can be edited, so earlier assessments stay comparable.")
    anthro = visit.anthropometry
    if anthro is None:
        raise HTTPException(status_code=422, detail="This visit has no measurements to correct.")
    age_months = (body.visit_date.year - child.date_of_birth.year) * 12 + (body.visit_date.month - child.date_of_birth.month)
    anthro.age_months = max(0, age_months)
    anthro.weight_kg = body.weight_kg
    anthro.height_cm = body.height_cm
    visit.visit_date = body.visit_date
    policy = load_clinical_policy()
    payload = {
        "anthropometric": _row(anthro),
        "socioeconomic": _row(visit.socioeconomic),
        "dietary": _row(visit.dietary),
        "maternal_child_health": _row(visit.maternal_child_health),
    }
    report = validate_visit_payload(payload, policy)
    if not report.complete:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "This visit contains values outside the configured validation range. Review the highlighted fields before continuing.",
                "quality": report.as_dict(),
            },
        )
    stored = report.as_dict()
    if isinstance(visit.data_quality, dict) and visit.data_quality.get("ga_rgca_context"):
        stored["ga_rgca_context"] = visit.data_quality["ga_rgca_context"]
    visit.data_quality = stored
    _clear_latest_score(db, visit)
    db.flush()
    prediction = run_inference(db, visit, child, current.id, request.client.host if request.client else None)
    write_audit(
        db,
        action=AuditAction.VISIT_CHANGED,
        resource_type="visit",
        resource_id=str(visit.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"visit_number": visit.visit_number},
    )
    return {
        "id": str(visit.id),
        "visit_number": visit.visit_number,
        "prediction": {
            "risk": prediction.primary_risk_score,
            **prediction_api_fields(prediction),
        },
    }


@router.delete("/visits/{visit_id}")
def delete_visit(visit_id: UUID, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("visit:write"))):
    from app.models.enums import FollowUpStatus
    from app.models.intelligence import LatentEmbedding, Prediction, TrajectoryMetric
    from app.models.operations import Alert, C3ReassessmentRequest, ClinicalNote, ClinicianReview, FollowUpSchedule

    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    if child is None or child.deleted_at:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    latest = _latest_visit(db, child.id)
    if latest is None or latest.id != visit.id:
        raise HTTPException(status_code=409, detail="Only the latest visit can be removed, so earlier assessments stay comparable.")
    for row in db.scalars(select(C3ReassessmentRequest).where(C3ReassessmentRequest.visit_id == visit.id)).all():
        db.delete(row)
    db.flush()
    for row in db.scalars(select(ClinicianReview).where(ClinicianReview.visit_id == visit.id)).all():
        db.delete(row)
    for row in db.scalars(select(ClinicalNote).where(ClinicalNote.visit_id == visit.id)).all():
        row.visit_id = None
    for row in db.scalars(select(Alert).where(Alert.visit_id == visit.id)).all():
        db.delete(row)
    for row in db.scalars(select(LatentEmbedding).where(LatentEmbedding.visit_id == visit.id)).all():
        db.delete(row)
    for row in db.scalars(
        select(TrajectoryMetric).where(
            (TrajectoryMetric.to_visit_id == visit.id)
            | (TrajectoryMetric.from_visit_id == visit.id)
            | (TrajectoryMetric.baseline_visit_id == visit.id)
        )
    ).all():
        db.delete(row)
    db.flush()
    for row in db.scalars(select(Prediction).where(Prediction.visit_id == visit.id)).all():
        db.delete(row)
    if visit.anthropometry:
        db.delete(visit.anthropometry)
    if visit.socioeconomic:
        db.delete(visit.socioeconomic)
    if visit.dietary:
        db.delete(visit.dietary)
    if visit.maternal_child_health:
        db.delete(visit.maternal_child_health)
    for follow_up in db.scalars(
        select(FollowUpSchedule).where(
            FollowUpSchedule.child_id == child.id,
            FollowUpSchedule.status == FollowUpStatus.SUGGESTED,
        )
    ).all():
        db.delete(follow_up)
    db.delete(visit)
    write_audit(
        db,
        action=AuditAction.VISIT_REMOVED,
        resource_type="visit",
        resource_id=str(visit_id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"visit_number": visit.visit_number},
    )
    return {"ok": True}


@router.get("/visits/{visit_id}")
def get_visit(visit_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("visit:read"))):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    assert_child_access(current, child)
    return {
        "id": str(visit.id),
        "child_id": str(visit.child_id),
        "visit_number": visit.visit_number,
        "visit_date": visit.visit_date.isoformat(),
        "status": visit.status.value,
        "anthropometric": _row(visit.anthropometry),
        "socioeconomic": _row(visit.socioeconomic),
        "dietary": _row(visit.dietary),
        "maternal_child_health": _row(visit.maternal_child_health),
        "data_quality": visit.data_quality,
    }


@router.post("/visits/{visit_id}/predict")
def predict_visit(visit_id: UUID, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("predict:run"))):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    assert_child_access(current, child)
    if visit.status == VisitStatus.DRAFT:
        raise HTTPException(422, "Submit the visit before running prediction")
    prediction = run_inference(db, visit, child, current.id, request.client.host if request.client else None)
    kick_delivery_best_effort(pop_scheduled_delivery_ids(db))
    return {
        "id": str(prediction.id),
        "run_number": prediction.run_number,
        "risk": prediction.primary_risk_score,
        "mode": prediction.mode.value if hasattr(prediction.mode, "value") else prediction.mode,
        "inference_ms": prediction.inference_ms,
        **prediction_api_fields(prediction),
    }


@router.get("/visits/{visit_id}/prediction")
def get_prediction(visit_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("visit:read"))):
    from app.models.intelligence import Prediction

    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    assert_child_access(current, db.get(Child, visit.child_id))
    preds = db.scalars(select(Prediction).where(Prediction.visit_id == visit_id).order_by(Prediction.run_number)).all()
    return [
        {
            "id": str(p.id),
            "run_number": p.run_number,
            "is_active": p.is_active,
            "risk": p.primary_risk_score,
            **prediction_api_fields(p),
            "mode": p.mode.value if hasattr(p.mode, "value") else p.mode,
            "raw_probabilities": p.raw_probabilities,
            "calibrated_probabilities": p.calibrated_probabilities,
            "confidence": p.confidence,
            "created_at": p.created_at.isoformat(),
        }
        for p in preds
    ]


def _row(obj):
    if obj is None:
        return None
    data = {}
    for col in obj.__table__.columns:
        if col.name in {"id", "visit_id", "created_at", "updated_at"}:
            continue
        val = getattr(obj, col.name)
        data[col.name] = val.value if hasattr(val, "value") else val
    return data
