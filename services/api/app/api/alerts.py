from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.models.enums import AlertStatus, AuditAction
from app.models.operations import Alert
from app.models.paediatric import Child
from app.services.child_list import child_is_synthetic
from app.schemas.common import AlertPatch
from app.security.rbac import facility_scope_ids
from app.services.audit import write_audit

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    severity: str | None = None,
    type: str | None = None,
    status: str | None = None,
    assigned_to_me: bool = False,
    db: Session = Depends(get_db),
    current=Depends(require_permission("alert:read")),
):
    stmt = select(Alert)
    scope = facility_scope_ids(current)
    if scope:
        stmt = stmt.where(Alert.facility_id.in_(scope))
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if type:
        stmt = stmt.where(Alert.type == type)
    if status:
        stmt = stmt.where(Alert.status == status)
    if assigned_to_me:
        stmt = stmt.where(Alert.assigned_to == current.id)
    rows = db.scalars(stmt.order_by(Alert.created_at.desc()).limit(200)).all()
    out = []
    for a in rows:
        child = db.get(Child, a.child_id)
        if child is None or child.deleted_at or child_is_synthetic(child):
            continue
        out.append(
            {
                "id": str(a.id),
                "child_id": str(a.child_id),
                "pseudonymous_id": child.pseudonymous_id if child else None,
                "type": a.type.value,
                "severity": a.severity.value,
                "status": a.status.value,
                "message": a.message,
                "trigger_value": a.trigger_value,
                "created_at": a.created_at.isoformat(),
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            }
        )
    return {"items": out, "synthetic": False}


@router.get("/{alert_id}")
def get_alert(alert_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("alert:read"))):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    child = db.get(Child, alert.child_id)
    return {
        "id": str(alert.id),
        "pseudonymous_id": child.pseudonymous_id if child else None,
        "type": alert.type.value,
        "severity": alert.severity.value,
        "status": alert.status.value,
        "message": alert.message,
        "trigger_value": alert.trigger_value,
        "child_id": str(alert.child_id),
    }


@router.patch("/{alert_id}/acknowledge")
def acknowledge(alert_id: UUID, body: AlertPatch, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("alert:write"))):
    from datetime import UTC, datetime

    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(UTC)
    alert.acknowledged_by = current.id
    if body.notes:
        alert.resolution_notes = body.notes
    write_audit(
        db,
        action=AuditAction.ALERT_ACKNOWLEDGED,
        resource_type="alert",
        resource_id=str(alert.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=alert.facility_id,
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "status": alert.status.value}


@router.patch("/{alert_id}/resolve")
def resolve(alert_id: UUID, body: AlertPatch, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("alert:write"))):
    from datetime import UTC, datetime

    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(UTC)
    alert.resolved_by = current.id
    alert.resolution_notes = body.notes or body.reason
    write_audit(
        db,
        action=AuditAction.ALERT_RESOLVED,
        resource_type="alert",
        resource_id=str(alert.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=alert.facility_id,
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "status": alert.status.value}


@router.patch("/{alert_id}/dismiss")
def dismiss(alert_id: UUID, body: AlertPatch, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("alert:write"))):
    from datetime import UTC, datetime

    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    if not body.reason:
        raise HTTPException(422, "A reason is required to dismiss an alert")
    alert.status = AlertStatus.DISMISSED_WITH_REASON
    alert.resolution_notes = body.reason
    alert.resolved_at = datetime.now(UTC)
    alert.resolved_by = current.id
    write_audit(
        db,
        action=AuditAction.ALERT_DISMISSED,
        resource_type="alert",
        resource_id=str(alert.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=alert.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"reason": body.reason},
    )
    return {"ok": True, "status": alert.status.value}


@router.patch("/{alert_id}/review")
def mark_in_review(alert_id: UUID, body: AlertPatch, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("alert:write"))):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    if alert.status not in {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_REVIEW}:
        raise HTTPException(422, f"Cannot move alert from {alert.status.value} to IN_REVIEW")
    alert.status = AlertStatus.IN_REVIEW
    if body.notes:
        alert.resolution_notes = body.notes
    write_audit(
        db,
        action=AuditAction.ALERT_IN_REVIEW,
        resource_type="alert",
        resource_id=str(alert.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=alert.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"status": "IN_REVIEW"},
    )
    return {"ok": True, "status": alert.status.value}
