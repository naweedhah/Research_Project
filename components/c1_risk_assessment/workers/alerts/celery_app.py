from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

REDIS = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("cnip_alerts", broker=REDIS, backend=REDIS)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "missed-followups-hourly": {
        "task": "workers.alerts.tasks.evaluate_missed_followups_task",
        "schedule": crontab(minute=15),
    },
    "integration-outbox-drain": {
        "task": "workers.alerts.tasks.drain_integration_outbox_task",
        "schedule": 60.0,  # every minute
    },
}

import workers.alerts.tasks  # noqa: E402, F401
