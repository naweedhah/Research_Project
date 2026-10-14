from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.models.enums import ModelStatus, UserStatus
from app.models.identity import LoginAttempt, User
from app.models.intelligence import ModelVersion, Prediction
from app.models.operations import AuditLog

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system")
def system_health(db: Session = Depends(get_db), current=Depends(require_permission("admin:system"))):
    import httpx

    settings = get_settings()
    inference = {"status": "unknown"}
    try:
        r = httpx.get(f"{settings.inference_url}/health", timeout=3.0)
        inference = r.json()
        inference["http"] = r.status_code
    except Exception:  # noqa: BLE001
        inference = {"status": "unavailable"}

    redis_ok = False
    try:
        import redis

        redis_ok = redis.Redis.from_url(settings.redis_url).ping()
    except Exception:  # noqa: BLE001
        redis_ok = False

    db_ok = True
    try:
        db.execute(select(1))
    except Exception:  # noqa: BLE001
        db_ok = False

    active = db.scalar(select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE).limit(1))
    last_pred = db.scalar(select(Prediction).order_by(Prediction.created_at.desc()).limit(1))
    return {
        "api": "ok",
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "inference": inference,
        "worker": "configured",
        "active_model": None
        if not active
        else {
            "id": str(active.id),
            "key": f"{active.model_key}-{active.version}",
            "demo": active.is_demo,
        },
        "last_successful_prediction": last_pred.created_at.isoformat() if last_pred else None,
        "model_mode": settings.model_mode,
    }


@router.get("/security")
def security(db: Session = Depends(get_db), current=Depends(require_permission("admin:security"))):
    active_users = db.scalar(select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)) or 0
    failed = db.scalars(select(LoginAttempt).where(LoginAttempt.success.is_(False)).order_by(LoginAttempt.created_at.desc()).limit(20)).all()
    audits = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(30)).all()
    return {
        "active_users": active_users,
        "failed_logins": [
            {"email": f.email, "at": f.created_at.isoformat(), "ip": f.ip_address} for f in failed
        ],
        "recent_audit": [
            {"action": a.action, "resource_type": a.resource_type, "timestamp": a.timestamp.isoformat(), "role": a.role}
            for a in audits
        ],
    }


@router.get("/audit")
def audit_logs(db: Session = Depends(get_db), current=Depends(require_permission("audit:read"))):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200)).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "timestamp": r.timestamp.isoformat(),
                "user_id": str(r.user_id) if r.user_id else None,
                "role": r.role,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "metadata": r.metadata_json,
            }
            for r in rows
        ]
    }


@router.get("/settings")
def settings_view(current=Depends(require_permission("admin:settings"))):
    from app.core.policy import load_clinical_policy

    policy = load_clinical_policy()
    return {
        "sections": ["Organization", "Facilities", "Users", "Model", "Follow-Up", "Notifications", "Integrations", "Security"],
        "clinical_policy": {
            "policy_id": policy.policy_id,
            "status": policy.status,
            "disclaimer": policy.disclaimer,
            "stagnation_threshold": policy.stagnation_threshold,
            "consecutive_followups": policy.consecutive_followups,
            "deterioration_delta": policy.deterioration_delta,
            "overdue_grace_days": policy.overdue_grace_days,
            "notes": "Research / Demo Configuration",
        },
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db), current=Depends(require_permission("user:manage", "user:manage_any"))):
    stmt = select(User).where(User.deleted_at.is_(None))
    if not current.can("user:manage_any"):
        stmt = stmt.where(User.facility_id == current.user.facility_id)
    rows = db.scalars(stmt.order_by(User.email)).all()
    return {
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value,
                "status": u.status.value,
                "facility_id": str(u.facility_id),
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in rows
        ]
    }
