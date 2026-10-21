from __future__ import annotations

import sys
from pathlib import Path

from workers.alerts.celery_app import celery_app

API_ROOT = Path("/app") if Path("/app/app").exists() else Path(__file__).resolve().parents[2] / "services" / "api"
sys.path.insert(0, str(API_ROOT))


@celery_app.task(name="workers.alerts.tasks.evaluate_missed_followups_task")
def evaluate_missed_followups_task() -> int:
    from app.core.db import SessionLocal
    from app.services.prediction import evaluate_missed_followups

    db = SessionLocal()
    try:
        return evaluate_missed_followups(db)
    finally:
        db.close()


@celery_app.task(name="workers.alerts.tasks.deliver_integration_event_task")
def deliver_integration_event_task(event_id: str) -> str:
    from app.core.db import SessionLocal
    from app.integrations.common.delivery import deliver_event_by_id

    db = SessionLocal()
    try:
        result = deliver_event_by_id(db, event_id)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="workers.alerts.tasks.drain_integration_outbox_task")
def drain_integration_outbox_task() -> dict:
    from app.core.db import SessionLocal
    from app.integrations.common.delivery import drain_pending

    db = SessionLocal()
    try:
        return drain_pending(db, limit=25)
    finally:
        db.close()
