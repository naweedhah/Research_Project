from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import EntityStatus, Sex, VisitStatus, VisitType


class Child(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "children"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    pseudonymous_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    external_patient_id_encrypted: Mapped[str | None] = mapped_column(String(512))
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[Sex] = mapped_column(str_enum(Sex, "sex"), nullable=False)
    status: Mapped[EntityStatus] = mapped_column(str_enum(EntityStatus, "child_status"), default=EntityStatus.ACTIVE)
    responsible_team: Mapped[str | None] = mapped_column(String(120))
    registered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    full_name_encrypted: Mapped[str | None] = mapped_column(String(512))
    district: Mapped[str | None] = mapped_column(String(120))
    moh_area: Mapped[str | None] = mapped_column(String(120))
    phm_area: Mapped[str | None] = mapped_column(String(120))
    assigned_doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    external_patient_id_hash: Mapped[str | None] = mapped_column(String(64), index=True)

    visits: Mapped[list[Visit]] = relationship(back_populates="child", order_by="Visit.visit_number")
    caregiver: Mapped[Caregiver | None] = relationship(back_populates="child", uselist=False)


class Caregiver(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Operational identity only. Never used as an ML feature."""

    __tablename__ = "caregivers"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), unique=True, nullable=False)
    kinship: Mapped[str] = mapped_column(String(40), default="mother")
    display_name: Mapped[str | None] = mapped_column(String(200))
    phone_encrypted: Mapped[str | None] = mapped_column(String(512))
    reminder_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    child: Mapped[Child] = relationship(back_populates="caregiver")


class Visit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visits"
    __table_args__ = (UniqueConstraint("child_id", "visit_number", name="uq_visit_child_number"),)

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    visit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    visit_type: Mapped[VisitType] = mapped_column(str_enum(VisitType, "visit_type"), default=VisitType.ROUTINE)
    scheduled: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_versions.id"))
    status: Mapped[VisitStatus] = mapped_column(str_enum(VisitStatus, "visit_status"), default=VisitStatus.DRAFT)
    confirmation_attested: Mapped[bool] = mapped_column(Boolean, default=False)
    data_quality: Mapped[dict | None] = mapped_column(JSON)

    child: Mapped[Child] = relationship(back_populates="visits")
    anthropometry: Mapped[AnthropometricRecord | None] = relationship(back_populates="visit", uselist=False)
    socioeconomic: Mapped[SocioeconomicRecord | None] = relationship(back_populates="visit", uselist=False)
    dietary: Mapped[DietaryRecord | None] = relationship(back_populates="visit", uselist=False)
    maternal_child_health: Mapped[MaternalChildHealthRecord | None] = relationship(back_populates="visit", uselist=False)
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="visit")


class AnthropometricRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "anthropometric_records"

    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), unique=True, nullable=False)
    age_months: Mapped[float] = mapped_column(Float, nullable=False)
    sex: Mapped[Sex] = mapped_column(str_enum(Sex, "anthro_sex"), nullable=False)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    muac_cm: Mapped[float | None] = mapped_column(Float)
    birth_weight_kg: Mapped[float | None] = mapped_column(Float)
    head_circumference_cm: Mapped[float | None] = mapped_column(Float)
    previous_weight_kg: Mapped[float | None] = mapped_column(Float)
    previous_height_cm: Mapped[float | None] = mapped_column(Float)

    visit: Mapped[Visit] = relationship(back_populates="anthropometry")


class SocioeconomicRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "socioeconomic_records"

    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), unique=True, nullable=False)
    wealth_proxy: Mapped[str | None] = mapped_column(String(40))
    maternal_education: Mapped[str | None] = mapped_column(String(80))
    paternal_education: Mapped[str | None] = mapped_column(String(80))
    maternal_employment: Mapped[str | None] = mapped_column(String(80))
    household_size: Mapped[int | None] = mapped_column(Integer)
    geographical_area: Mapped[str | None] = mapped_column(String(80))
    drinking_water: Mapped[str | None] = mapped_column(String(80))
    sanitation: Mapped[str | None] = mapped_column(String(80))
    carried_forward: Mapped[bool] = mapped_column(Boolean, default=False)

    visit: Mapped[Visit] = relationship(back_populates="socioeconomic")


class DietaryRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dietary_records"

    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), unique=True, nullable=False)
    breastfeeding_status: Mapped[str | None] = mapped_column(String(80))
    breastfeeding_duration_months: Mapped[float | None] = mapped_column(Float)
    complementary_feeding: Mapped[bool | None] = mapped_column(Boolean)
    dietary_diversity_score: Mapped[int | None] = mapped_column(Integer)
    meal_frequency: Mapped[int | None] = mapped_column(Integer)
    food_groups: Mapped[list | None] = mapped_column(JSON)
    micronutrient_supplementation: Mapped[bool | None] = mapped_column(Boolean)

    visit: Mapped[Visit] = relationship(back_populates="dietary")


class MaternalChildHealthRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maternal_child_health_records"

    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), unique=True, nullable=False)
    maternal_bmi: Mapped[float | None] = mapped_column(Float)
    gestational_age_weeks: Mapped[int | None] = mapped_column(Integer)
    immunization_uptodate: Mapped[bool | None] = mapped_column(Boolean)
    vitamin_a: Mapped[bool | None] = mapped_column(Boolean)
    recent_diarrhoea: Mapped[bool | None] = mapped_column(Boolean)
    recent_respiratory_illness: Mapped[bool | None] = mapped_column(Boolean)
    recent_hospitalization: Mapped[bool | None] = mapped_column(Boolean)
    birth_characteristics: Mapped[str | None] = mapped_column(Text)

    visit: Mapped[Visit] = relationship(back_populates="maternal_child_health")
