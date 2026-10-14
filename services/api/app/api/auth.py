from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import get_current_user, CurrentUser
from app.core.policy import load_product
from app.core.security import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    PERMISSIONS,
    cookie_kwargs,
    create_token,
    decode_token,
    hash_token,
    hash_password,
    new_csrf,
    new_refresh_raw,
    persist_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from app.models.enums import AuditAction, UserRole, UserStatus
from app.models.identity import LoginAttempt, RefreshToken, User
from app.schemas.common import LoginRequest, TokenUserResponse, UserOut
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["authentication"])


def _user_out(user: User) -> UserOut:
    role = UserRole(user.role.value if hasattr(user.role, "value") else user.role)
    perms = sorted(PERMISSIONS.get(role, set()))
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        qualifications=user.qualifications,
        experience=user.experience,
        role=user.role.value,
        status=user.status.value,
        facility_id=user.facility_id,
        facility_name=user.facility.name if user.facility else None,
        facility_code=user.facility.code if user.facility else None,
        permissions=perms,
    )


def _set_auth_cookies(response: Response, settings: Settings, access: str, refresh: str, csrf: str, remember: bool) -> None:
    kwargs = cookie_kwargs(settings)
    max_refresh = int(settings.refresh_ttl.total_seconds()) if remember else int(settings.refresh_ttl.total_seconds())
    response.set_cookie(ACCESS_COOKIE, access, max_age=int(settings.access_ttl.total_seconds()), **kwargs)
    response.set_cookie(REFRESH_COOKIE, refresh, max_age=max_refresh, **kwargs)
    csrf_kwargs = {**kwargs, "httponly": False}
    response.set_cookie(CSRF_COOKIE, csrf, max_age=max_refresh, **csrf_kwargs)


@router.post("/login", response_model=TokenUserResponse)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    ip = request.client.host if request.client else None
    user = db.scalar(select(User).options(joinedload(User.facility)).where(User.email == body.email.lower()))
    now = datetime.now(UTC)
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail="Account temporarily locked")
    valid = user is not None and user.status == UserStatus.ACTIVE and verify_password(body.password, user.password_hash)
    db.add(LoginAttempt(email=body.email.lower(), success=valid, ip_address=ip))
    if not valid:
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.failed_login_limit:
                user.status = UserStatus.LOCKED
                user.locked_until = now + timedelta_minutes(settings.lockout_minutes)
        write_audit(db, action=AuditAction.LOGIN_FAILED, resource_type="session", metadata={"email": body.email.lower()}, ip=ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if user.role != UserRole.DOCTOR:
        write_audit(db, action=AuditAction.LOGIN_FAILED, resource_type="session", metadata={"email": body.email.lower(), "reason": "non_doctor_role"}, ip=ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This application is restricted to clinician accounts")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    access = create_token({"sub": str(user.id), "role": user.role.value}, settings.jwt_secret, settings.access_ttl)
    raw_refresh = new_refresh_raw()
    persist_refresh_token(db, user, raw_refresh, settings.refresh_ttl, ip, request.headers.get("user-agent"))
    csrf = new_csrf()
    _set_auth_cookies(response, settings, access, raw_refresh, csrf, body.remember_me)
    write_audit(
        db,
        action=AuditAction.LOGIN,
        resource_type="session",
        user_id=user.id,
        role=user.role.value,
        facility_id=user.facility_id,
        ip=ip,
    )
    product = load_product()
    return TokenUserResponse(user=_user_out(user), csrf_token=csrf, disclaimer=product["disclaimer"])


def timedelta_minutes(minutes: int):
    from datetime import timedelta

    return timedelta(minutes=minutes)


@router.post("/refresh", response_model=TokenUserResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    now = datetime.now(UTC)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        raise HTTPException(status_code=401, detail="Refresh token invalid")
    user = db.get(User, row.user_id)
    if user is None or user.status != UserStatus.ACTIVE or user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=401, detail="Account unavailable")
    new_raw = new_refresh_raw()
    rotate_refresh_token(db, row, new_raw, settings.refresh_ttl)
    access = create_token({"sub": str(user.id), "role": user.role.value}, settings.jwt_secret, settings.access_ttl)
    csrf = new_csrf()
    _set_auth_cookies(response, settings, access, new_raw, csrf, True)
    db.refresh(user)
    user = db.scalar(select(User).options(joinedload(User.facility)).where(User.id == user.id))
    return TokenUserResponse(user=_user_out(user), csrf_token=csrf, disclaimer=load_product()["disclaimer"])


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        if row:
            row.revoked_at = datetime.now(UTC)
            write_audit(db, action=AuditAction.LOGOUT, resource_type="session", user_id=row.user_id, ip=request.client.host if request.client else None)
    kwargs = cookie_kwargs(settings)
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(current: CurrentUser = Depends(get_current_user)):
    return _user_out(current.user)
