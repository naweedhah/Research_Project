from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import UserRole, UserStatus
from app.models.identity import RefreshToken, User

ACCESS_COOKIE = "cnip_access"
REFRESH_COOKIE = "cnip_refresh"
CSRF_COOKIE = "cnip_csrf"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(payload: dict, secret: str, ttl: timedelta) -> str:
    body = {**payload, "exp": datetime.now(UTC) + ttl, "iat": datetime.now(UTC), "jti": secrets.token_hex(8)}
    return jwt.encode(body, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_refresh_raw() -> str:
    return secrets.token_urlsafe(48)


def new_csrf() -> str:
    return secrets.token_urlsafe(24)


class FieldEncryptor:
    def __init__(self, key: str):
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        import base64

        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return None


PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SYSTEM_ADMIN: {
        "org:manage",
        "facility:manage",
        "user:manage",
        "user:manage_any",
        "child:read",
        "child:write",
        "child:read_any",
        "visit:read",
        "visit:write",
        "predict:run",
        "alert:read",
        "alert:write",
        "note:write",
        "report:export",
        "research:read",
        "admin:system",
        "admin:security",
        "admin:settings",
        "model:activate",
        "audit:read",
        "integration:request",
    },
    UserRole.FACILITY_ADMIN: {
        "user:manage",
        "child:read",
        "child:write",
        "visit:read",
        "visit:write",
        "predict:run",
        "alert:read",
        "alert:write",
        "note:write",
        "report:export",
        "admin:settings",
        "audit:read",
        "integration:request",
    },
    UserRole.DOCTOR: {
        "child:read",
        "child:write",
        "visit:read",
        "visit:write",
        "predict:run",
        "alert:read",
        "alert:write",
        "note:write",
        "report:export",
        "integration:request",
    },
    UserRole.HEALTH_WORKER: {
        "child:read",
        "child:write",
        "visit:read",
        "visit:write",
        "predict:run",
        "alert:read",
        "alert:write",
        "note:write",
        "integration:request",
    },
    UserRole.NUTRITIONIST: {
        "child:read",
        "visit:read",
        "alert:read",
        "note:write",
        "report:export",
    },
    UserRole.RESEARCHER: {
        "research:read",
        "report:export",
        "child:read_deidentified",
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def persist_refresh_token(db: Session, user: User, raw: str, ttl: timedelta, ip: str | None, ua: str | None) -> RefreshToken:
    row = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(UTC) + ttl,
        ip_address=ip,
        user_agent=(ua or "")[:300],
    )
    db.add(row)
    db.flush()
    return row


def rotate_refresh_token(db: Session, existing: RefreshToken, raw: str, ttl: timedelta) -> RefreshToken:
    existing.revoked_at = datetime.now(UTC)
    new_row = RefreshToken(
        user_id=existing.user_id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(UTC) + ttl,
        ip_address=existing.ip_address,
        user_agent=existing.user_agent,
    )
    db.add(new_row)
    db.flush()
    existing.replaced_by = new_row.id
    return new_row


def cookie_kwargs(settings: Settings) -> dict:
    kwargs = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    return kwargs
