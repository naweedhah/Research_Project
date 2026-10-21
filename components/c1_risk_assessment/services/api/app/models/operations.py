from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    C3RequestStatus,
    ClinicianAssessment,
    ClinicianReviewState,
    ClinicianWorkflowAction,
    FollowUpStatus,
    IntegrationDeliveryStatus,
    IntegrationEventType,
    NotificationChannel,
)


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visits.id"))
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    type: Mapped[AlertType] = mapped_column(str_enum(AlertType, "alert_type"), nullable=False, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(str_enum(AlertSeverity, "alert_severity"), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(str_enum(AlertStatus, "alert_status"), default=AlertStatus.OPEN, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_value: Mapped[dict | None] = mapped_column(JSON)
    threshold_version: Mapped[str | None] = mapped_column(String(80))
    event_window_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolution_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("event_window_key", name="uq_alert_event_window"),)


class FollowUpSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "follow_up_schedules"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), nullable=False)
    expected_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=30)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[FollowUpStatus] = mapped_column(
        str_enum(FollowUpStatus, "follow_up_status"), default=FollowUpStatus.SCHEDULED, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)


class ClinicalNote(UUIDPrimaryKeyMixin, Base):
    """Free-text notes are operational only and are never fed into the model."""

    __tablename__ = "clinical_notes"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visits.id"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ClinicianReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Structured clinician review — never overwrites AI prediction fields."""

    __tablename__ = "clinician_reviews"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    prediction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("predictions.id"), nullable=False, index=True)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    review_state: Mapped[ClinicianReviewState] = mapped_column(
        str_enum(ClinicianReviewState, "clinician_review_state"),
        default=ClinicianReviewState.PENDING,
        index=True,
    )
    clinician_assessment: Mapped[ClinicianAssessment | None] = mapped_column(
        str_enum(ClinicianAssessment, "clinician_assessment")
    )
    clinician_status: Mapped[str | None] = mapped_column(String(40))
    clinician_severity: Mapped[str | None] = mapped_column(String(40))
    clinical_note: Mapped[str | None] = mapped_column(Text)
    workflow_action: Mapped[ClinicianWorkflowAction | None] = mapped_column(
        str_enum(ClinicianWorkflowAction, "clinician_workflow_action")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("prediction_id", name="uq_clinician_review_prediction"),)


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str | None] = mapped_column(String(40))
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facilities.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        str_enum(NotificationChannel, "notification_channel"), default=NotificationChannel.IN_APP
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class IntegrationEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_events"

    event_type: Mapped[IntegrationEventType] = mapped_column(
        str_enum(IntegrationEventType, "integration_event_type"), nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    target: Mapped[str] = mapped_column(String(40), default="internal", index=True)
    contract_version: Mapped[str] = mapped_column(String(20), default="1.0")
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True, index=True)
    delivery_status: Mapped[IntegrationDeliveryStatus] = mapped_column(
        str_enum(IntegrationDeliveryStatus, "integration_delivery_status"),
        default=IntegrationDeliveryStatus.PENDING,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_error: Mapped[str | None] = mapped_column(Text)
    external_ref: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class C3ReassessmentRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """C1-owned tracking for Component 3 intervention reassessment requests (references only)."""

    __tablename__ = "c3_reassessment_requests"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id"), nullable=False, index=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    prediction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("predictions.id"), nullable=False, index=True)
    clinician_review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinician_reviews.id"), nullable=False, index=True)
    integration_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("integration_events.id"), index=True)
    status: Mapped[C3RequestStatus] = mapped_column(
        str_enum(C3RequestStatus, "c3_request_status"), default=C3RequestStatus.QUEUED, index=True
    )
    external_request_id: Mapped[str | None] = mapped_column(String(120))
    result_ref: Mapped[str | None] = mapped_column(String(200))
    result_url: Mapped[str | None] = mapped_column(String(500))
    last_error: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("clinician_review_id", name="uq_c3_request_clinician_review"),)
