"""Backfill synthetic demonstration fields on existing child records (idempotent)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import FieldEncryptor
from app.models.enums import FollowUpStatus, Sex, UserRole, UserStatus
from app.models.identity import RefreshToken, User
from app.models.intelligence import Prediction
from app.models.operations import ClinicalNote, FollowUpSchedule
from app.models.paediatric import AnthropometricRecord, Caregiver, Child, DietaryRecord, MaternalChildHealthRecord, Visit


def _disable_non_doctor_users(db) -> int:
    now = datetime.now(UTC)
    disabled = 0
    for user in db.scalars(select(User).where(User.role != UserRole.DOCTOR)).all():
        user.status = UserStatus.DISABLED
        user.locked_until = None
        for token in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))).all():
            token.revoked_at = now
        disabled += 1
    return disabled


def _confidence_for_risk(risk: float) -> str:
    if risk < 0.35:
        return "high"
    if risk < 0.65:
        return "moderate"
    return "low"


def _age_months_at_visit(dob, visit_date) -> float:
    months = (visit_date.year - dob.year) * 12 + visit_date.month - dob.month
    return float(max(0, months))


def _measurements(sex: str, age: float, risk: float) -> dict:
    base_w = 9.5 if sex == "female" else 10.0
    weight = round(base_w + age * 0.12 - risk * 3.2, 2)
    height = round(70 + age * 0.7 - risk * 4, 1)
    muac = round(14.5 - risk * 4.5, 1)
    head = round(43.5 + age * 0.18 - risk * 0.8, 1)
    return {
        "weight_kg": max(4.0, weight),
        "height_cm": max(55.0, height),
        "muac_cm": max(9.0, muac),
        "head_circumference_cm": max(34.0, head),
        "age_months": age,
    }


def enrich() -> None:
    db = SessionLocal()
    try:
        disabled_users = _disable_non_doctor_users(db)

        recorder = db.scalar(select(User).where(User.email == "doctor@demo.local", User.status == UserStatus.ACTIVE))
        if recorder is None:
            recorder = db.scalar(select(User).where(User.role == UserRole.DOCTOR, User.status == UserStatus.ACTIVE))
        if not recorder:
            print("Enrich skipped — no active doctor account found (run seed first)")
            return

        enc = FieldEncryptor(get_settings().encryption_key)
        children = db.scalars(select(Child).where(Child.deleted_at.is_(None))).all()
        notes_added = 0
        visits_enriched = 0
        anthro_created = 0

        for child in children:
            if not child.external_patient_id_encrypted:
                child.external_patient_id_encrypted = enc.encrypt(f"EXT-{child.pseudonymous_id}")

            if not child.assigned_doctor_id:
                child.assigned_doctor_id = recorder.id

            if not child.responsible_team:
                child.responsible_team = "Synthetic demonstration team"

            caregiver = db.scalar(select(Caregiver).where(Caregiver.child_id == child.id))
            if caregiver is None:
                caregiver = Caregiver(
                    child_id=child.id,
                    kinship="mother",
                    display_name=f"Synthetic caregiver ({child.pseudonymous_id})",
                    phone_encrypted=enc.encrypt("+250780000001"),
                )
                db.add(caregiver)
            else:
                if not caregiver.display_name:
                    caregiver.display_name = f"Synthetic caregiver ({child.pseudonymous_id})"
                if not caregiver.phone_encrypted:
                    caregiver.phone_encrypted = enc.encrypt("+250780000001")

            visits = db.scalars(select(Visit).where(Visit.child_id == child.id).order_by(Visit.visit_number)).all()
            prev_anthro: AnthropometricRecord | None = None

            for visit in visits:
                pred = db.scalar(select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True)))
                risk = pred.primary_risk_score if pred else 0.4
                age = _age_months_at_visit(child.date_of_birth, visit.visit_date)
                sex = child.sex.value

                anthro = visit.anthropometry
                if anthro is None:
                    meas = _measurements(sex, age, risk)
                    anthro = AnthropometricRecord(
                        visit_id=visit.id,
                        age_months=meas["age_months"],
                        sex=Sex(sex),
                        height_cm=meas["height_cm"],
                        weight_kg=meas["weight_kg"],
                        muac_cm=meas["muac_cm"],
                        head_circumference_cm=meas["head_circumference_cm"],
                        birth_weight_kg=2.7 if sex == "female" else 2.9,
                        previous_weight_kg=prev_anthro.weight_kg if prev_anthro else None,
                        previous_height_cm=prev_anthro.height_cm if prev_anthro else None,
                    )
                    db.add(anthro)
                    anthro_created += 1
                else:
                    if anthro.weight_kg is None or anthro.height_cm is None or anthro.muac_cm is None:
                        meas = _measurements(sex, anthro.age_months or age, risk)
                        anthro.weight_kg = anthro.weight_kg or meas["weight_kg"]
                        anthro.height_cm = anthro.height_cm or meas["height_cm"]
                        anthro.muac_cm = anthro.muac_cm or meas["muac_cm"]
                    if anthro.head_circumference_cm is None:
                        anthro.head_circumference_cm = round(43.5 + (anthro.age_months or age) * 0.18, 1)
                    if prev_anthro:
                        anthro.previous_weight_kg = anthro.previous_weight_kg or prev_anthro.weight_kg
                        anthro.previous_height_cm = anthro.previous_height_cm or prev_anthro.height_cm
                    visits_enriched += 1

                prev_anthro = anthro

                dietary = visit.dietary
                if dietary and dietary.breastfeeding_duration_months is None and anthro:
                    dietary.breastfeeding_duration_months = round(min(max(anthro.age_months, 0), 24), 1)

                mch = visit.maternal_child_health
                if mch and not mch.birth_characteristics:
                    mch.birth_characteristics = (
                        "Synthetic demonstration data: term birth, facility delivery, "
                        "no neonatal complications recorded in demo record."
                    )

                if pred and not pred.confidence:
                    pred.confidence = _confidence_for_risk(pred.primary_risk_score)

            follow = db.scalar(
                select(FollowUpSchedule).where(FollowUpSchedule.child_id == child.id).order_by(FollowUpSchedule.expected_date.desc())
            )
            if follow is None and visits:
                db.add(
                    FollowUpSchedule(
                        child_id=child.id,
                        facility_id=child.facility_id,
                        expected_date=visits[-1].visit_date.date() + timedelta(days=42),
                        interval_days=42,
                        responsible_user_id=recorder.id,
                        status=FollowUpStatus.SCHEDULED,
                        notes="Synthetic demonstration follow-up",
                    )
                )

            predicted = [v for v in visits if db.scalar(select(Prediction).where(Prediction.visit_id == v.id, Prediction.is_active.is_(True)))]
            for visit in predicted[:-1]:
                existing_review = db.scalar(
                    select(ClinicalNote).where(
                        ClinicalNote.visit_id == visit.id,
                        ClinicalNote.body.like("[Clinician review]%"),
                    )
                )
                if existing_review:
                    continue
                db.add(
                    ClinicalNote(
                        child_id=child.id,
                        visit_id=visit.id,
                        author_id=recorder.id,
                        body=(
                            "[Clinician review] Assessment: agree. Workflow: monitor. "
                            "Synthetic demonstration review recorded after this visit."
                        ),
                        created_at=visit.visit_date + timedelta(hours=4),
                    )
                )
                notes_added += 1

            note_count = db.scalar(
                select(func.count()).select_from(ClinicalNote).where(ClinicalNote.child_id == child.id)
            ) or 0
            if note_count == 0 and visits:
                db.add(
                    ClinicalNote(
                        child_id=child.id,
                        visit_id=visits[-1].id,
                        author_id=recorder.id,
                        body=(
                            f"[Synthetic demonstration note] Initial clinical review for {child.pseudonymous_id}. "
                            "Caregiver counselled on complementary feeding; follow-up scheduled per clinic protocol."
                        ),
                    )
                )
                notes_added += 1

        db.commit()
        print(
            f"Enrich complete: {len(children)} children, {visits_enriched} visits updated, "
            f"{anthro_created} anthropometry records created, {notes_added} notes added, "
            f"{disabled_users} non-doctor accounts disabled."
        )
    finally:
        db.close()


if __name__ == "__main__":
    enrich()
