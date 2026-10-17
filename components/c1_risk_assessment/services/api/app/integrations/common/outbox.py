"""Transactional outbox helpers for durable C3/C4 delivery."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import IntegrationDeliveryStatus, IntegrationEventType
from app.models.operations import IntegrationEvent

logger = logging.getLogger(__name__)


def enqueue_integration_event(
    db: Session,
    *,
    event_type: IntegrationEventType,
    target: str,
    payload: dict[str, Any],
    idempotency_key: str,
    contract_version: str = "1.0",
    correlation_id: UUID | None = None,
) -> IntegrationEvent:
    """Insert outbox row in the current transaction. Idempotent on idempotency_key."""
    existing = db.scalar(select(IntegrationEvent).where(IntegrationEvent.idempotency_key == idempotency_key))
    if existing is not None:
        return existing

    event = IntegrationEvent(
        event_type=event_type,
        payload=payload,
        target=target,
        contract_version=contract_version,
        correlation_id=correlation_id or uuid4(),
        idempotency_key=idempotency_key,
        delivery_status=IntegrationDeliveryStatus.PENDING,
        attempt_count=0,
    )
    db.add(event)
    db.flush()
    pending = db.info.setdefault("integration_deliver_ids", [])
    pending.append(str(event.id))
    return event


def kick_delivery_best_effort(event_ids: list[str]) -> None:
    """After DB commit, ask Celery to deliver. Safe if worker is offline (beat will drain)."""
    for eid in event_ids:
        try:
            from workers.alerts.tasks import deliver_integration_event_task

            deliver_integration_event_task.delay(eid)
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "integration_schedule_deferred",
                extra={"event_id": eid, "error_type": type(exc).__name__},
            )


def pop_scheduled_delivery_ids(db: Session) -> list[str]:
    return list(db.info.pop("integration_deliver_ids", []) or [])


def mark_delivering(event: IntegrationEvent) -> None:
    event.delivery_status = IntegrationDeliveryStatus.DELIVERING
    event.last_attempt_at = datetime.now(UTC)


def mark_delivered(event: IntegrationEvent, *, external_ref: dict[str, Any] | None = None) -> None:
    event.delivery_status = IntegrationDeliveryStatus.DELIVERED
    event.delivered_at = datetime.now(UTC)
    event.delivery_error = None
    if external_ref is not None:
        event.external_ref = external_ref


def mark_retryable_failure(event: IntegrationEvent, error: str, *, max_attempts: int) -> None:
    event.attempt_count = int(event.attempt_count or 0) + 1
    event.delivery_error = error[:2000]
    event.last_attempt_at = datetime.now(UTC)
    if event.attempt_count >= max_attempts:
        event.delivery_status = IntegrationDeliveryStatus.FAILED_FINAL
        event.next_attempt_at = None
    else:
        event.delivery_status = IntegrationDeliveryStatus.FAILED_RETRYABLE
        backoff = min(3600, 30 * (2 ** (event.attempt_count - 1)))
        event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=backoff)


def claim_pending_events(db: Session, *, limit: int = 25) -> list[IntegrationEvent]:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(IntegrationEvent)
        .where(
            IntegrationEvent.target.in_(["c3", "c4"]),
            IntegrationEvent.delivery_status.in_(
                [IntegrationDeliveryStatus.PENDING, IntegrationDeliveryStatus.FAILED_RETRYABLE]
            ),
        )
        .order_by(IntegrationEvent.created_at.asc())
        .limit(limit)
    ).all()
    ready: list[IntegrationEvent] = []
    for row in rows:
        if row.delivery_status == IntegrationDeliveryStatus.FAILED_RETRYABLE and row.next_attempt_at and row.next_attempt_at > now:
            continue
        ready.append(row)
    return ready
