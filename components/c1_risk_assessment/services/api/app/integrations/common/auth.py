"""Service-to-service auth for C3/C4. Never use clinician cookies for outbound calls."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def outbound_headers(*, component: str, correlation_id: str, contract_version: str, idempotency_key: str) -> dict[str, str]:
    settings = get_settings()
    token = ""
    if component == "c3":
        token = settings.c3_integration_token
    elif component == "c4":
        token = settings.c4_integration_token
    elif component == "c2":
        token = settings.c2_integration_token
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
        "X-Contract-Version": contract_version,
        "Idempotency-Key": idempotency_key,
        "X-Source-Component": "C1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def require_component_token(expected: str, authorization: str | None) -> None:
    settings = get_settings()
    expected_token = {
        "c3": settings.c3_integration_token,
        "c4": settings.c4_integration_token,
        "c2": settings.c2_integration_token,
    }.get(expected, "")
    if not expected_token:
        # Prototype: reject inbound component calls when token not configured.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Component {expected.upper()} inbound authentication is not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    presented = authorization.removeprefix("Bearer ").strip()
    if presented != expected_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid component token")


def require_c4_token(authorization: str | None = Header(default=None, alias="Authorization")) -> None:
    require_component_token("c4", authorization)
