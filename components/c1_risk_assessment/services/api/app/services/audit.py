from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import AuditAction
from app.models.operations import AuditLog


def write_audit(
    db: Session,
    *,
    action: AuditAction | str,
    resource_type: str,
    resource_id: str | None = None,
    user_id=None,
    role: str | None = None,
    facility_id=None,
    metadata: dict | None = None,
    ip: str | None = None,
) -> AuditLog:
    row = AuditLog(
        timestamp=datetime.now(UTC),
        user_id=user_id,
        role=role,
        facility_id=facility_id,
        action=action.value if isinstance(action, AuditAction) else action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        metadata_json=metadata,
        ip_address=ip,
    )
    db.add(row)
    db.flush()
    return row
