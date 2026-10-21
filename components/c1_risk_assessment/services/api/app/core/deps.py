from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.db import apply_rls_context, get_db
from app.core.security import ACCESS_COOKIE, CSRF_COOKIE, decode_token, has_permission
from app.models.enums import UserRole, UserStatus
from app.models.identity import User

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class CurrentUser:
    user: User
    role: UserRole
    facility_id: str
    organization_id: str | None

    @property
    def id(self):
        return self.user.id

    def can(self, permission: str) -> bool:
        return has_permission(self.role, permission)


def require_csrf(request: Request, csrf_cookie: str | None, csrf_header: str | None) -> None:
    if request.method not in UNSAFE_METHODS:
        return
    settings = get_settings()
    if settings.app_env == "test":
        return
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    access: str | None = Cookie(default=None, alias=ACCESS_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> CurrentUser:
    require_csrf(request, csrf_cookie, csrf_header)
    if not access:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(access, settings.jwt_secret)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from exc
    user = db.scalar(select(User).options(joinedload(User.facility)).where(User.id == payload.get("sub")))
    if user is None or user.status != UserStatus.ACTIVE or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable")
    bypass = user.role == UserRole.SYSTEM_ADMIN
    apply_rls_context(db, str(user.facility_id), user.role.value, bypass=bypass)
    return CurrentUser(
        user=user,
        role=user.role,
        facility_id=str(user.facility_id),
        organization_id=str(user.facility.organization_id) if user.facility else None,
    )


def require_permission(*permissions: str):
    def _dep(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(current.can(p) for p in permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current

    return _dep


AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
