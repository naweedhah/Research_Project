from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.models.enums import AlertSeverity, AlertStatus, AlertType
from app.models.operations import Alert
from app.services.alerts import event_window_key
import uuid


def test_duplicate_event_window_is_unique():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _disable_fk(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    Base.metadata.create_all(engine)
    db: Session = sessionmaker(bind=engine)()
    child_id = uuid.uuid4()
    facility_id = uuid.uuid4()
    key = event_window_key(str(child_id), AlertType.STAGNATION, "visit-1")
    db.add(
        Alert(
            child_id=child_id,
            facility_id=facility_id,
            type=AlertType.STAGNATION,
            severity=AlertSeverity.MODERATE,
            status=AlertStatus.OPEN,
            message="Progress stagnation detected",
            event_window_key=key,
        )
    )
    db.commit()
    db.add(
        Alert(
            child_id=child_id,
            facility_id=facility_id,
            type=AlertType.STAGNATION,
            severity=AlertSeverity.MODERATE,
            status=AlertStatus.OPEN,
            message="Progress stagnation detected",
            event_window_key=key,
        )
    )
    with pytest.raises(Exception):  # integrity error on unique event window
        db.commit()
