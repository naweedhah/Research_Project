"""One-time replacement of stored v3/demo scores with GA-RGCA v4.

Does not retrain, invent probabilities, or fall back to the demo adapter.
Safe to re-run: visits already stored as GA-RGCA-v4-Rolling-RSL are skipped.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.db import SessionLocal, apply_rls_context
from app.models.enums import UserRole
from app.models.identity import User
from app.models.intelligence import Prediction
from app.models.paediatric import Child, Visit
from app.services.prediction import run_inference

V4_SOURCE = "GA-RGCA-v4-Rolling-RSL"


def _stored_source(prediction: Prediction | None) -> str | None:
    if prediction is None or not isinstance(prediction.calibrated_probabilities, dict):
        return None
    block = prediction.calibrated_probabilities.get("ga_rgca")
    if not isinstance(block, dict):
        return None
    source = block.get("prediction_source") or block.get("model_version")
    return str(source) if source else None


def _visits_in_order(db) -> list[Visit]:
    return (
        db.scalars(
            select(Visit)
            .options(
                joinedload(Visit.anthropometry),
                joinedload(Visit.socioeconomic),
                joinedload(Visit.dietary),
                joinedload(Visit.maternal_child_health),
                joinedload(Visit.child),
            )
            .order_by(Visit.child_id, Visit.visit_number)
        )
        .unique()
        .all()
    )


def rescore_all(*, log=print) -> dict:
    db = SessionLocal()
    stats = {"scored": 0, "skipped_v4": 0, "skipped_incomplete": 0, "failed": 0}
    try:
        apply_rls_context(db, None, None, bypass=True)
        doctor = db.scalar(select(User).where(User.role == UserRole.DOCTOR).limit(1))
        if doctor is None:
            raise RuntimeError("No doctor account is available to record the rescore audit.")
        visits = _visits_in_order(db)
        log(f"visits={len(visits)}")
        for visit in visits:
            apply_rls_context(db, None, None, bypass=True)
            anthro = visit.anthropometry
            if (
                anthro is None
                or anthro.age_months is None
                or anthro.sex is None
                or anthro.height_cm is None
                or anthro.weight_kg is None
                or float(anthro.height_cm) <= 0
                or float(anthro.weight_kg) <= 0
            ):
                stats["skipped_incomplete"] += 1
                log(f"SKIP incomplete {visit.id}")
                continue
            active = db.scalar(select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True)))
            if _stored_source(active) == V4_SOURCE:
                stats["skipped_v4"] += 1
                continue
            child = visit.child or db.get(Child, visit.child_id)
            if child is None:
                stats["failed"] += 1
                log(f"FAIL missing child {visit.id}")
                continue
            try:
                prediction = run_inference(db, visit, child, doctor.id, None)
                source = _stored_source(prediction)
                if source != V4_SOURCE:
                    db.rollback()
                    apply_rls_context(db, None, None, bypass=True)
                    stats["failed"] += 1
                    log(f"FAIL not v4 {visit.id} source={source}")
                    continue
                db.commit()
                stats["scored"] += 1
                log(f"OK visit={visit.id} type={prediction.status_prediction}")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                apply_rls_context(db, None, None, bypass=True)
                stats["failed"] += 1
                log(f"FAIL {visit.id} {exc}")
        log(f"done {stats}")
        return stats
    finally:
        db.close()


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "rescore.log"
    with log_path.open("a", encoding="utf-8") as handle:

        def log(message: str) -> None:
            handle.write(message + "\n")
            handle.flush()
            print(message)

        stats = rescore_all(log=log)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
