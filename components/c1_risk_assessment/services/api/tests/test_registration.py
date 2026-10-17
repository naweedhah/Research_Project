from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.common import ChildCreate


def test_child_create_rejects_future_dob():
    with pytest.raises(ValidationError):
        ChildCreate(
            full_name="Test Child",
            date_of_birth=date.today() + timedelta(days=1),
            sex="female",
            external_patient_id="HOSP-001",
            responsible_team="Nutrition Clinic",
            caregiver_relationship="Mother",
        )


def test_child_create_requires_core_fields():
    with pytest.raises(ValidationError):
        ChildCreate(
            full_name="A",
            date_of_birth=date(2024, 1, 1),
            sex="female",
            external_patient_id="",
            responsible_team="Clinic",
            caregiver_relationship="Mother",
        )


def test_child_create_valid_payload():
    body = ChildCreate(
        full_name="Anuki Perera",
        date_of_birth=date(2024, 6, 1),
        sex="female",
        external_patient_id="LRH-2026-001",
        responsible_team="Paediatric Clinic",
        caregiver_relationship="Mother",
        caregiver_phone="0771234567",
    )
    assert body.full_name == "Anuki Perera"
    assert body.reminder_consent is False
