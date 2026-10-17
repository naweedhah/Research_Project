"""Component 4 HTTP client — observations and model-activation notices only. No drift logic."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.common.auth import outbound_headers
from app.integrations.common.contracts import assert_supported_contract_version
from app.models.operations import IntegrationEvent


def is_configured() -> bool:
    settings = get_settings()
    if settings.integration_mode.lower() == "mock":
        return False
    return bool(settings.c4_drift_url)


def deliver_observation(payload: dict[str, Any], *, event: IntegrationEvent) -> dict[str, Any]:
    settings = get_settings()
    base = settings.c4_drift_url.rstrip("/")
    assert_supported_contract_version(str(payload.get("contract_version", "1.0")))
    event_type = str(payload.get("event_type") or event.event_type.value)
    path = {
        "c1.prediction.completed": "/v1/observations/predictions",
        "c1.clinician_review.completed": "/v1/observations/clinician-reviews",
        "c1.model.activated": "/v1/observations/model-activations",
        "prediction.completed": "/v1/observations/predictions",
        "clinician_review.completed": "/v1/observations/clinician-reviews",
        "model.activated": "/v1/observations/model-activations",
    }.get(event_type, "/v1/observations")
    headers = outbound_headers(
        component="c4",
        correlation_id=str(event.correlation_id or event.id),
        contract_version=event.contract_version or "1.0",
        idempotency_key=event.idempotency_key or str(event.id),
    )
    with httpx.Client(timeout=settings.integration_timeout_seconds) as client:
        response = client.post(f"{base}{path}", json=payload, headers=headers)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {"status": "accepted"}
