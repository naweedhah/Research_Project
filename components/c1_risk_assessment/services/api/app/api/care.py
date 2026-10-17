from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.models.enums import AuditAction, FollowUpStatus
from app.models.identity import User
from app.models.operations import ClinicalNote, ClinicianReview, FollowUpSchedule
from app.models.paediatric import Child, Visit
from app.schemas.common import ClinicianReviewCreate, ClinicianReviewPatch, FollowUpCreate, FollowUpPatch, NoteCreate, NoteUpdate
from app.security.rbac import assert_child_access, facility_scope_ids
from app.services.audit import write_audit
from app.services.clinician_review import (
    active_prediction_for_visit,
    get_review_for_visit,
    normalize_assessment,
    normalize_workflow,
    serialize_review,
    upsert_completed_review,
)

router = APIRouter(tags=["care"])


@router.post("/children/{child_id}/notes")
def add_note(child_id: UUID, body: NoteCreate, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("note:write"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    if body.body.strip().lower().startswith("[clinician review]"):
        raise HTTPException(
            422,
            "Structured clinician reviews must be submitted via the clinician-review endpoint, not free-text notes.",
        )
    note = ClinicalNote(child_id=child.id, visit_id=body.visit_id, author_id=current.id, body=body.body)
    db.add(note)
    write_audit(
        db,
        action=AuditAction.CLINICAL_NOTE_CREATED,
        resource_type="clinical_note",
        resource_id=str(child.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"not_used_for_ml": True},
    )
    db.flush()
    return {"id": str(note.id), "created_at": note.created_at.isoformat()}


@router.patch("/notes/{note_id}")
def update_note(note_id: UUID, body: NoteUpdate, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("note:write"))):
    note = db.get(ClinicalNote, note_id)
    if note is None:
        raise HTTPException(404, "Clinical note not found")
    child = db.get(Child, note.child_id)
    if child is None or child.deleted_at:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    if body.body.strip().lower().startswith("[clinician review]"):
        raise HTTPException(422, "Structured clinician reviews are stored separately from clinical notes.")
    note.body = body.body.strip()
    write_audit(
        db,
        action=AuditAction.CLINICAL_NOTE_UPDATED,
        resource_type="clinical_note",
        resource_id=str(note.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"not_used_for_ml": True},
    )
    return {"id": str(note.id)}


@router.delete("/notes/{note_id}")
def delete_note(note_id: UUID, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("note:write"))):
    note = db.get(ClinicalNote, note_id)
    if note is None:
        raise HTTPException(404, "Clinical note not found")
    child = db.get(Child, note.child_id)
    if child is None or child.deleted_at:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    db.delete(note)
    write_audit(
        db,
        action=AuditAction.CLINICAL_NOTE_DELETED,
        resource_type="clinical_note",
        resource_id=str(note_id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"not_used_for_ml": True},
    )
    return {"ok": True}


@router.get("/children/{child_id}/clinician-reviews")
def list_clinician_reviews(child_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    rows = db.scalars(
        select(ClinicianReview).where(ClinicianReview.child_id == child_id).order_by(ClinicianReview.created_at.desc())
    ).all()
    items = []
    for row in rows:
        reviewer = db.get(User, row.reviewer_user_id)
        items.append(serialize_review(row, reviewer, has_prediction=True))
    return {"items": items}


@router.get("/visits/{visit_id}/clinician-review")
def get_visit_clinician_review(visit_id: UUID, db: Session = Depends(get_db), current=Depends(require_permission("child:read"))):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    pred = active_prediction_for_visit(db, visit.id)
    review = get_review_for_visit(db, visit.id)
    reviewer = db.get(User, review.reviewer_user_id) if review else None
    return serialize_review(review, reviewer, has_prediction=pred is not None)


@router.post("/visits/{visit_id}/clinician-review")
def create_visit_clinician_review(
    visit_id: UUID,
    body: ClinicianReviewCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current=Depends(require_permission("note:write")),
):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    child = db.get(Child, visit.child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    prediction = active_prediction_for_visit(db, visit.id)
    if prediction is None:
        raise HTTPException(422, "No active AI prediction exists for this visit")
    ai_status = prediction.status_prediction
    ai_severity = prediction.severity_prediction
    ai_score = prediction.primary_risk_score
    try:
        assessment = normalize_assessment(body.assessment)
    except ValueError as exc:
        raise HTTPException(422, "Invalid clinician assessment") from exc
    workflow = normalize_workflow(body.workflow_action)
    row = upsert_completed_review(
        db,
        child=child,
        visit=visit,
        prediction=prediction,
        reviewer=current.user,
        assessment=assessment,
        workflow=workflow,
        clinical_note=body.clinical_note,
        clinician_status=body.clinician_status,
        clinician_severity=body.clinician_severity,
    )
    db.refresh(prediction)
    if (
        prediction.status_prediction != ai_status
        or prediction.severity_prediction != ai_severity
        or float(prediction.primary_risk_score) != float(ai_score)
    ):
        raise HTTPException(500, "AI prediction was unexpectedly modified")
    write_audit(
        db,
        action=AuditAction.CLINICIAN_REVIEW_CREATED,
        resource_type="clinician_review",
        resource_id=str(row.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={
            "visit_id": str(visit.id),
            "prediction_id": str(prediction.id),
            "assessment": assessment.value,
            "workflow_action": workflow.value,
            "ai_status": ai_status,
            "ai_severity": ai_severity,
            "ai_score": ai_score,
        },
    )
    from app.models.intelligence import ModelVersion
    from app.integrations.common.enqueue import (
        enqueue_c3_reassessment_for_review,
        enqueue_c4_clinician_review_observation,
    )
    from app.integrations.common.outbox import kick_delivery_best_effort, pop_scheduled_delivery_ids

    model = db.get(ModelVersion, prediction.model_version_id)
    if model is not None:
        enqueue_c4_clinician_review_observation(
            db, child=child, visit=visit, prediction=prediction, model=model, review=row
        )
        enqueue_c3_reassessment_for_review(
            db, child=child, visit=visit, prediction=prediction, model=model, review=row, user_id=current.id
        )
    deliver_ids = pop_scheduled_delivery_ids(db)
    if deliver_ids:
        background_tasks.add_task(kick_delivery_best_effort, deliver_ids)
    return serialize_review(row, current.user, has_prediction=True)


@router.patch("/clinician-reviews/{review_id}")
def patch_clinician_review(
    review_id: UUID,
    body: ClinicianReviewPatch,
    request: Request,
    db: Session = Depends(get_db),
    current=Depends(require_permission("note:write")),
):
    row = db.get(ClinicianReview, review_id)
    if not row:
        raise HTTPException(404, "Review not found")
    child = db.get(Child, row.child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    if body.assessment is not None:
        try:
            row.clinician_assessment = normalize_assessment(body.assessment)
        except ValueError as exc:
            raise HTTPException(422, "Invalid clinician assessment") from exc
    if body.workflow_action is not None:
        row.workflow_action = normalize_workflow(body.workflow_action)
    if body.clinical_note is not None:
        row.clinical_note = body.clinical_note
    if body.clinician_status is not None:
        row.clinician_status = body.clinician_status
    if body.clinician_severity is not None:
        row.clinician_severity = body.clinician_severity
    row.reviewer_user_id = current.id
    row.reviewed_at = datetime.now(UTC)
    write_audit(
        db,
        action=AuditAction.CLINICIAN_REVIEW_UPDATED,
        resource_type="clinician_review",
        resource_id=str(row.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
    )
    return serialize_review(row, current.user, has_prediction=True)


def _supersede_open_follow_ups(db: Session, child_id: UUID) -> None:
    open_rows = db.scalars(
        select(FollowUpSchedule).where(
            FollowUpSchedule.child_id == child_id,
            FollowUpSchedule.status.in_(
                [
                    FollowUpStatus.SUGGESTED,
                    FollowUpStatus.SCHEDULED,
                    FollowUpStatus.OVERDUE,
                    FollowUpStatus.RESCHEDULED,
                ]
            ),
        )
    ).all()
    for item in open_rows:
        item.status = FollowUpStatus.COMPLETED


@router.post("/children/{child_id}/follow-ups")
def create_follow_up(child_id: UUID, body: FollowUpCreate, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("visit:write"))):
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    _supersede_open_follow_ups(db, child.id)
    status = FollowUpStatus.SCHEDULED if body.confirm else FollowUpStatus.SUGGESTED
    row = FollowUpSchedule(
        child_id=child.id,
        facility_id=child.facility_id,
        expected_date=body.expected_date,
        interval_days=body.interval_days,
        responsible_user_id=body.responsible_user_id or current.id,
        status=status,
        notes=body.notes,
    )
    db.add(row)
    write_audit(
        db,
        action=AuditAction.FOLLOW_UP_CHANGED,
        resource_type="follow_up",
        resource_id=str(child.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"status": status.value, "confirmed": body.confirm},
    )
    db.flush()
    return {"id": str(row.id), "expected_date": row.expected_date.isoformat(), "status": row.status.value}


@router.post("/follow-ups/{follow_up_id}/confirm")
def confirm_follow_up(follow_up_id: UUID, request: Request, db: Session = Depends(get_db), current=Depends(require_permission("visit:write"))):
    row = db.get(FollowUpSchedule, follow_up_id)
    if not row:
        raise HTTPException(404, "Follow-up not found")
    child = db.get(Child, row.child_id)
    if not child:
        raise HTTPException(404, "Child not found")
    assert_child_access(current, child)
    if row.status == FollowUpStatus.SCHEDULED:
        return {"ok": True, "status": row.status.value, "already_confirmed": True}
    if row.status not in {FollowUpStatus.SUGGESTED, FollowUpStatus.RESCHEDULED}:
        raise HTTPException(422, f"Follow-up in status {row.status.value} cannot be confirmed")
    row.status = FollowUpStatus.SCHEDULED
    row.responsible_user_id = row.responsible_user_id or current.id
    write_audit(
        db,
        action=AuditAction.FOLLOW_UP_CHANGED,
        resource_type="follow_up",
        resource_id=str(row.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=child.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"action": "confirm"},
    )
    return {"ok": True, "status": row.status.value}


@router.get("/follow-ups")
def list_follow_ups(db: Session = Depends(get_db), current=Depends(require_permission("visit:read"))):
    stmt = select(FollowUpSchedule)
    scope = facility_scope_ids(current)
    if scope:
        stmt = stmt.where(FollowUpSchedule.facility_id.in_(scope))
    rows = db.scalars(stmt.order_by(FollowUpSchedule.expected_date).limit(200)).all()
    out = []
    for r in rows:
        child = db.get(Child, r.child_id)
        out.append(
            {
                "id": str(r.id),
                "child": child.pseudonymous_id if child else None,
                "child_id": str(r.child_id),
                "expected_date": r.expected_date.isoformat(),
                "status": r.status.value,
                "interval_days": r.interval_days,
            }
        )
    return {"items": out}


@router.patch("/follow-ups/{follow_up_id}")
def patch_follow_up(
    follow_up_id: UUID,
    body: FollowUpPatch,
    request: Request,
    db: Session = Depends(get_db),
    current=Depends(require_permission("visit:write")),
):
    row = db.get(FollowUpSchedule, follow_up_id)
    if not row:
        raise HTTPException(404, "Follow-up not found")
    child = db.get(Child, row.child_id)
    if child:
        assert_child_access(current, child)
    if body.expected_date:
        row.expected_date = body.expected_date
        if body.status is None:
            row.status = FollowUpStatus.SCHEDULED
    if body.status:
        row.status = FollowUpStatus(body.status)
    if body.notes is not None:
        row.notes = body.notes
    write_audit(
        db,
        action=AuditAction.FOLLOW_UP_CHANGED,
        resource_type="follow_up",
        resource_id=str(row.id),
        user_id=current.id,
        role=current.role.value,
        facility_id=row.facility_id,
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "status": row.status.value}
