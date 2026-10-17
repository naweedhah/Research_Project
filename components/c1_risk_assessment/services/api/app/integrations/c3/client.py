"""Component 3 HTTP client — reassessment request/status only. No counterfactual logic."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.common.auth import outbound_headers
from app.integrations.common.contracts import C3InterventionResponseV1, assert_supported_contract_version
from app.models.operations import IntegrationEvent

MESSAGE_NOT_CONNECTED = "Component 3 is not connected. The reassessment request remains queued."


def is_configured() -> bool:
    settings = get_settings()
    if settings.integration_mode.lower() == "mock":
        return False
    return bool(settings.c3_counterfactual_url)


def connection_status() -> str:
    if not get_settings().c3_counterfactual_url:
        return "NOT_CONFIGURED"
    if get_settings().integration_mode.lower() == "mock":
        return "NOT_CONFIGURED"
    return "CONNECTED"  # refined by recent delivery outcomes in status API


def submit_reassessment(payload: dict[str, Any], *, event: IntegrationEvent) -> dict[str, Any]:
    settings = get_settings()
    base = settings.c3_counterfactual_url.rstrip("/")
    assert_supported_contract_version(str(payload.get("contract_version", "1.0")))
    headers = outbound_headers(
        component="c3",
        correlation_id=str(event.correlation_id or event.id),
        contract_version=event.contract_version or "1.0",
        idempotency_key=event.idempotency_key or str(event.id),
    )
    with httpx.Client(timeout=settings.integration_timeout_seconds) as client:
        response = client.post(f"{base}/v1/intervention-reassessments", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    parsed = C3InterventionResponseV1.model_validate(data)
    return parsed.model_dump(mode="json")


def fetch_status(external_request_id: str, *, event: IntegrationEvent | None = None) -> dict[str, Any]:
    settings = get_settings()
    base = settings.c3_counterfactual_url.rstrip("/")
    headers = outbound_headers(
        component="c3",
        correlation_id=str(event.correlation_id if event else external_request_id),
        contract_version="1.0",
        idempotency_key=f"c3-status:{external_request_id}",
    )
    with httpx.Client(timeout=settings.integration_timeout_seconds) as client:
        response = client.get(f"{base}/v1/intervention-reassessments/{external_request_id}", headers=headers)
        response.raise_for_status()
        return response.json()
