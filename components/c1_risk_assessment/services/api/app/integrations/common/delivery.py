"""Background delivery of pending C3/C4 integration events."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.c3 import client as c3_client
from app.integrations.c4 import client as c4_client
from app.integrations.common.outbox import (
    claim_pending_events,
    mark_delivered,
    mark_delivering,
    mark_retryable_failure,
)
from app.models.enums import IntegrationDeliveryStatus, IntegrationEventType
from app.models.operations import C3ReassessmentRequest, IntegrationEvent
from app.models.enums import C3RequestStatus

logger = logging.getLogger(__name__)


def deliver_one(db: Session, event: IntegrationEvent) -> str:
    settings = get_settings()
    max_attempts = settings.integration_max_retries
    mark_delivering(event)
    db.flush()

    if event.target == "c3":
        if not c3_client.is_configured():
            # Keep queued — do not invent a fake C3 result.
            event.delivery_status = IntegrationDeliveryStatus.PENDING
            event.delivery_error = "C3_NOT_CONFIGURED"
            return "not_configured"
        try:
            response = c3_client.submit_reassessment(event.payload, event=event)
            mark_delivered(event, external_ref=response)
            _sync_c3_request(db, event, response)
            return "delivered"
        except Exception as exc:  # noqa: BLE001
            mark_retryable_failure(event, f"{type(exc).__name__}: {exc}", max_attempts=max_attempts)
            logger.warning(
                "integration_delivery_failed",
                extra={
                    "event_id": str(event.id),
                    "destination": "c3",
                    "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                    "attempt": event.attempt_count,
                    "error_type": type(exc).__name__,
                },
            )
            return "failed"

    if event.target == "c4":
        if not c4_client.is_configured():
            event.delivery_status = IntegrationDeliveryStatus.PENDING
            event.delivery_error = "C4_NOT_CONFIGURED"
            return "not_configured"
        try:
            response = c4_client.deliver_observation(event.payload, event=event)
            mark_delivered(event, external_ref=response if isinstance(response, dict) else {"ack": True})
            return "delivered"
        except Exception as exc:  # noqa: BLE001
            mark_retryable_failure(event, f"{type(exc).__name__}: {exc}", max_attempts=max_attempts)
            logger.warning(
                "integration_delivery_failed",
                extra={
                    "event_id": str(event.id),
                    "destination": "c4",
                    "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                    "attempt": event.attempt_count,
                    "error_type": type(exc).__name__,
                },
            )
            return "failed"

    # Internal / unknown targets — mark delivered without HTTP.
    mark_delivered(event, external_ref={"note": "internal_no_http"})
    return "skipped"


def deliver_event_by_id(db: Session, event_id: str | UUID) -> str:
    event = db.get(IntegrationEvent, event_id)
    if event is None:
        return "missing"
    if event.delivery_status == IntegrationDeliveryStatus.DELIVERED:
        return "already_delivered"
    return deliver_one(db, event)


def drain_pending(db: Session, *, limit: int = 25) -> dict[str, int]:
    counts = {"delivered": 0, "failed": 0, "not_configured": 0, "skipped": 0}
    for event in claim_pending_events(db, limit=limit):
        result = deliver_one(db, event)
        counts[result] = counts.get(result, 0) + 1
        db.commit()
    return counts


def _sync_c3_request(db: Session, event: IntegrationEvent, response: dict[str, Any]) -> None:
    if event.event_type != IntegrationEventType.COUNTERFACTUAL_REQUESTED:
        return
    row = db.get(C3ReassessmentRequest, event.payload.get("c3_request_row_id")) if event.payload.get("c3_request_row_id") else None
    if row is None:
        from sqlalchemy import select

        row = db.scalar(select(C3ReassessmentRequest).where(C3ReassessmentRequest.integration_event_id == event.id))
    if row is None:
        return
    status = str(response.get("status") or "QUEUED").upper()
    try:
        row.status = C3RequestStatus(status)
    except ValueError:
        row.status = C3RequestStatus.PROCESSING
    row.external_request_id = str(response.get("request_id") or response.get("result_id") or row.external_request_id or "")
    row.result_ref = response.get("result_id")
    row.result_url = response.get("result_url")
    if row.status == C3RequestStatus.COMPLETED:
        from datetime import UTC, datetime

        row.completed_at = datetime.now(UTC)
    row.last_error = None
