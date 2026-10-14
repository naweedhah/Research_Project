from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.models.enums import AuditAction
from app.models.intelligence import Prediction
from app.models.paediatric import Child, Visit
from app.services.audit import write_audit

router = APIRouter(tags=["export"])


@router.post("/research/export")
def export_deidentified(request: Request, db: Session = Depends(get_db), current=Depends(require_permission("report:export"))):
    """De-identified research export. Direct identity fields are excluded and the action is audited."""
    visits = db.scalars(select(Visit).limit(5000)).all()
    rows = []
    for visit in visits:
        child = db.get(Child, visit.child_id)
        pred = db.scalar(select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True)))
        rows.append(
            {
                "pseudonymous_id": child.pseudonymous_id if child else None,
                "visit_number": visit.visit_number,
                "visit_date": visit.visit_date.date().isoformat(),
                "status_prediction": pred.status_prediction if pred else None,
                "severity_prediction": pred.severity_prediction if pred else None,
                "risk": pred.primary_risk_score if pred else None,
            }
        )
    write_audit(
        db,
        action=AuditAction.REPORT_EXPORTED,
        resource_type="research_export",
        user_id=current.id,
        role=current.role.value,
        facility_id=current.user.facility_id,
        ip=request.client.host if request.client else None,
        metadata={"rows": len(rows), "identity_fields_excluded": True, "synthetic": True},
    )
    from app.services.model_display import get_model_output_display_metadata

    semantics = get_model_output_display_metadata()
    return {
        "confirmation": "Export includes only pseudonymous identifiers. Direct identity fields were excluded.",
        "disclaimer": semantics["report_disclaimer"],
        "rows": rows,
        "synthetic": True,
        "clinical_use": False,
        "display_semantics": semantics,
    }
