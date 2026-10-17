from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import ModelStatus, PredictionMode, ProgressState
from app.models.paediatric import Visit


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"

    model_key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    architecture: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    label_schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    training_dataset_version: Mapped[str | None] = mapped_column(String(40))
    calibration_version: Mapped[str | None] = mapped_column(String(40))
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=128)
    embedding_space_id: Mapped[str] = mapped_column(String(80), nullable=False)
    evaluation_metrics: Mapped[dict | None] = mapped_column(JSON)
    artifact_checksum: Mapped[str | None] = mapped_column(String(128))
    artifact_path: Mapped[str | None] = mapped_column(String(400))
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ModelStatus] = mapped_column(str_enum(ModelStatus, "model_status"), default=ModelStatus.EXPERIMENTAL)
    compatible_with: Mapped[list | None] = mapped_column(JSON)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("model_key", "version", name="uq_model_key_version"),)


class CalibrationVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calibration_versions"

    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    brier_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="active")


class ProjectionVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projection_versions"

    embedding_space_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    artifact_path: Mapped[str | None] = mapped_column(String(400))
    notes: Mapped[str | None] = mapped_column(Text)


class ClinicalPolicyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clinical_policy_versions"

    policy_key: Mapped[str] = mapped_column(String(80), nullable=False)
    stagnation_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    consecutive_visits: Mapped[int] = mapped_column(Integer, nullable=False)
    deterioration_delta: Mapped[float] = mapped_column(Float, nullable=False)
    overdue_grace_days: Mapped[int] = mapped_column(Integer, nullable=False)
    relapse_prior_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    relapse_increase: Mapped[float] = mapped_column(Float, nullable=False)
    default_followup_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(40), default="active")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="Research / Demo Configuration")
    payload: Mapped[dict | None] = mapped_column(JSON)


class Prediction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "predictions"

    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mode: Mapped[PredictionMode] = mapped_column(str_enum(PredictionMode, "prediction_mode"), default=PredictionMode.DEMO)
    status_prediction: Mapped[str] = mapped_column(String(40), nullable=False)
    severity_prediction: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)
    calibrated_probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)
    primary_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    inference_ms: Mapped[float] = mapped_column(Float, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    calibration_version: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    visit: Mapped[Visit] = relationship(back_populates="predictions")
    model_version: Mapped[ModelVersion] = relationship()

    __table_args__ = (UniqueConstraint("visit_id", "run_number", name="uq_prediction_run"),)


class LatentEmbedding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "latent_embeddings"

    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    prediction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("predictions.id"), nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    embedding_space_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False)
    projection_x: Mapped[float | None] = mapped_column(Float)
    projection_y: Mapped[float | None] = mapped_column(Float)
    projection_version: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TrajectoryMetric(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "trajectory_metrics"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    from_visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visits.id"))
    to_visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), nullable=False)
    baseline_visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visits.id"))
    risk_velocity: Mapped[float | None] = mapped_column(Float)
    baseline_recovery_rate: Mapped[float | None] = mapped_column(Float)
    elapsed_days: Mapped[int | None] = mapped_column(Integer)
    elapsed_months: Mapped[float | None] = mapped_column(Float)
    previous_risk: Mapped[float | None] = mapped_column(Float)
    current_risk: Mapped[float] = mapped_column(Float, nullable=False)
    progress_state: Mapped[ProgressState] = mapped_column(str_enum(ProgressState, "progress_state"), nullable=False)
    model_compatible: Mapped[bool] = mapped_column(Boolean, default=True)
    warning: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExperimentRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "experiment_runs"

    experiment_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    git_commit: Mapped[str | None] = mapped_column(String(64))
    dataset_version: Mapped[str | None] = mapped_column(String(40))
    model_config: Mapped[dict | None] = mapped_column(JSON)
    seed: Mapped[int | None] = mapped_column(Integer)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    artifact_path: Mapped[str | None] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
