"""P1 alert routing and lifecycle helpers."""

from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import AlertStatus, UserRole, UserStatus


def test_alert_status_lifecycle_values():
    assert AlertStatus.OPEN.value == "OPEN"
    assert AlertStatus.ACKNOWLEDGED.value == "ACKNOWLEDGED"
    assert AlertStatus.IN_REVIEW.value == "IN_REVIEW"
    assert AlertStatus.RESOLVED.value == "RESOLVED"
    assert AlertStatus.DISMISSED_WITH_REASON.value == "DISMISSED_WITH_REASON"


def test_notify_recipient_prefers_assigned_doctor(monkeypatch):
    from app.services import prediction as pred_mod

    assigned_id = uuid4()
    other_id = uuid4()
    assigned = SimpleNamespace(id=assigned_id, role=UserRole.DOCTOR, status=UserStatus.ACTIVE, facility_id=uuid4())
    other = SimpleNamespace(id=other_id, role=UserRole.DOCTOR, status=UserStatus.ACTIVE, facility_id=assigned.facility_id)

    child = SimpleNamespace(id=uuid4(), facility_id=assigned.facility_id, assigned_doctor_id=assigned_id, pseudonymous_id="C-1005")
    alert = SimpleNamespace(
        id=uuid4(),
        message="Deterioration detected",
        severity=SimpleNamespace(value="HIGH"),
        assigned_to=None,
    )

    added = []

    class FakeDB:
        def get(self, model, key):
            if key == assigned_id:
                return assigned
            return None

        def scalars(self, stmt):
            return SimpleNamespace(all=lambda: [assigned, other])

        def add(self, obj):
            added.append(obj)

    pred_mod._notify_facility(FakeDB(), child, alert)
    assert alert.assigned_to == assigned_id
    assert len(added) == 1
    assert added[0].user_id == assigned_id


def test_notify_fallback_facility_clinical_inbox():
    from app.services import prediction as pred_mod

    facility_id = uuid4()
    doctor = SimpleNamespace(id=uuid4(), role=UserRole.DOCTOR, status=UserStatus.ACTIVE, facility_id=facility_id)
    admin = SimpleNamespace(id=uuid4(), role=UserRole.FACILITY_ADMIN, status=UserStatus.ACTIVE, facility_id=facility_id)

    child = SimpleNamespace(id=uuid4(), facility_id=facility_id, assigned_doctor_id=None, pseudonymous_id="C-1004")
    alert = SimpleNamespace(
        id=uuid4(),
        message="Limited improvement",
        severity=SimpleNamespace(value="MODERATE"),
        assigned_to=None,
    )
    added = []

    class FakeDB:
        def get(self, model, key):
            return None

        def scalars(self, stmt):
            return SimpleNamespace(all=lambda: [doctor, admin])

        def add(self, obj):
            added.append(obj)

    pred_mod._notify_facility(FakeDB(), child, alert)
    assert alert.assigned_to == doctor.id
    assert {n.user_id for n in added} == {doctor.id, admin.id}
