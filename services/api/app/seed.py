"""Seed synthetic demonstration data. Never use these passwords in production."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.policy import load_clinical_policy
from app.core.security import FieldEncryptor, hash_password
from app.models.enums import (
    ClinicianAssessment,
    ClinicianReviewState,
    ClinicianWorkflowAction,
    EntityStatus,
    FacilityType,
    FollowUpStatus,
    ModelStatus,
    OrganizationType,
    ProgressState,
    Sex,
    UserRole,
    UserStatus,
    VisitStatus,
    VisitType,
)
from app.models.identity import Facility, Organization, User
from app.models.intelligence import ClinicalPolicyVersion, ModelVersion, Prediction, TrajectoryMetric
from app.models.operations import ClinicianReview, FollowUpSchedule, ClinicalNote
from app.models.paediatric import (
    AnthropometricRecord,
    Caregiver,
    Child,
    DietaryRecord,
    MaternalChildHealthRecord,
    SocioeconomicRecord,
    Visit,
)
from app.services.longitudinal import elapsed_months
from app.services.demo_outcomes import get_demo_outcome
DEMO_PASSWORD = "doctor123"
CONTRACTS = Path("/contracts") if Path("/contracts").exists() else Path(__file__).resolve().parents[3] / "packages" / "contracts"


CASES = [
    {
        "pid": "C-1042",
        "sex": "female",
        "dob": "2025-02-19",
        "facility": "CCHC-04",
        "team": "Clinic 04",
        "scenario": "stagnation",
        "follow_up": "2026-09-15",
        "visits": [
            {"date": "2026-01-15", "risk": 0.82, "status": "wasting", "severity": "severe", "progress": "baseline"},
            {"date": "2026-02-18", "risk": 0.61, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-03-18", "risk": 0.59, "status": "wasting", "severity": "moderate", "progress": "stagnating"},
        ],
    },
    {
        "pid": "C-1001",
        "sex": "male",
        "dob": "2024-11-02",
        "facility": "CCHC-04",
        "scenario": "improving",
        "follow_up": "2026-09-01",
        "visits": [
            {"date": "2026-03-01", "risk": 0.74, "status": "underweight", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-04-04", "risk": 0.58, "status": "underweight", "severity": "mild", "progress": "improving"},
            {"date": "2026-05-06", "risk": 0.41, "status": "normal", "severity": "none", "progress": "improving"},
            {"date": "2026-06-08", "risk": 0.28, "status": "normal", "severity": "none", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1002",
        "sex": "female",
        "dob": "2025-01-10",
        "facility": "CCHC-04",
        "scenario": "deteriorating",
        "follow_up": "2026-08-25",
        "visits": [
            {"date": "2026-04-10", "risk": 0.38, "status": "stunting", "severity": "mild", "progress": "baseline"},
            {"date": "2026-05-12", "risk": 0.47, "status": "stunting", "severity": "moderate", "progress": "deteriorating"},
            {"date": "2026-06-14", "risk": 0.62, "status": "stunting", "severity": "moderate", "progress": "deteriorating"},
            {"date": "2026-07-16", "risk": 0.71, "status": "wasting", "severity": "moderate", "progress": "deteriorating"},
        ],
    },
    {
        "pid": "C-1003",
        "sex": "male",
        "dob": "2024-06-20",
        "facility": "CCHC-04",
        "scenario": "stable",
        "follow_up": "2026-09-10",
        "visits": [
            {"date": "2026-04-01", "risk": 0.22, "status": "normal", "severity": "none", "progress": "baseline"},
            {"date": "2026-05-02", "risk": 0.21, "status": "normal", "severity": "none", "progress": "stable"},
            {"date": "2026-06-03", "risk": 0.23, "status": "normal", "severity": "none", "progress": "stable"},
        ],
    },
    {
        "pid": "C-1004",
        "sex": "female",
        "dob": "2024-12-01",
        "facility": "CCHC-04",
        "scenario": "missed",
        "follow_up": "2026-07-01",
        "overdue": True,
        "visits": [
            {"date": "2026-03-20", "risk": 0.55, "status": "underweight", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-04-22", "risk": 0.52, "status": "underweight", "severity": "moderate", "progress": "stable"},
            {"date": "2026-05-24", "risk": 0.50, "status": "underweight", "severity": "moderate", "progress": "stagnating"},
        ],
    },
    {
        "pid": "C-1005",
        "sex": "male",
        "dob": "2025-03-08",
        "facility": "CCHC-04",
        "scenario": "relapse",
        "follow_up": "2026-09-05",
        "visits": [
            {"date": "2026-02-01", "risk": 0.78, "status": "wasting", "severity": "severe", "progress": "baseline"},
            {"date": "2026-03-05", "risk": 0.49, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-04-08", "risk": 0.33, "status": "underweight", "severity": "mild", "progress": "improving"},
            {"date": "2026-06-12", "risk": 0.58, "status": "wasting", "severity": "moderate", "progress": "deteriorating"},
        ],
    },
    {
        "pid": "C-1006",
        "sex": "female",
        "dob": "2024-08-14",
        "facility": "KMCC-01",
        "scenario": "improving",
        "follow_up": "2026-09-12",
        "visits": [
            {"date": "2026-02-10", "risk": 0.66, "status": "stunting", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-03-12", "risk": 0.51, "status": "stunting", "severity": "mild", "progress": "improving"},
            {"date": "2026-04-14", "risk": 0.39, "status": "stunting", "severity": "mild", "progress": "improving"},
            {"date": "2026-05-16", "risk": 0.30, "status": "normal", "severity": "none", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1007",
        "sex": "male",
        "dob": "2025-04-22",
        "facility": "KMCC-01",
        "scenario": "improving",
        "follow_up": "2026-09-08",
        "visits": [
            {"date": "2026-05-01", "risk": 0.88, "status": "wasting", "severity": "severe", "progress": "baseline"},
            {"date": "2026-06-02", "risk": 0.70, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-07-04", "risk": 0.54, "status": "wasting", "severity": "moderate", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1008",
        "sex": "female",
        "dob": "2024-09-30",
        "facility": "KMCC-01",
        "scenario": "stagnation",
        "follow_up": "2026-09-02",
        "visits": [
            {"date": "2026-03-08", "risk": 0.57, "status": "underweight", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-04-10", "risk": 0.56, "status": "underweight", "severity": "moderate", "progress": "stable"},
            {"date": "2026-05-12", "risk": 0.55, "status": "underweight", "severity": "moderate", "progress": "stagnating"},
            {"date": "2026-06-14", "risk": 0.54, "status": "underweight", "severity": "moderate", "progress": "stagnating"},
        ],
    },
    {
        "pid": "C-1009",
        "sex": "male",
        "dob": "2025-05-05",
        "facility": "GCNU-02",
        "scenario": "stable",
        "follow_up": "2026-09-20",
        "visits": [
            {"date": "2026-04-20", "risk": 0.18, "status": "normal", "severity": "none", "progress": "baseline"},
            {"date": "2026-05-22", "risk": 0.17, "status": "normal", "severity": "none", "progress": "stable"},
            {"date": "2026-06-24", "risk": 0.19, "status": "normal", "severity": "none", "progress": "stable"},
            {"date": "2026-07-26", "risk": 0.16, "status": "normal", "severity": "none", "progress": "stable"},
        ],
    },
    {
        "pid": "C-1010",
        "sex": "female",
        "dob": "2024-10-11",
        "facility": "GCNU-02",
        "scenario": "deteriorating",
        "follow_up": "2026-08-28",
        "visits": [
            {"date": "2026-03-03", "risk": 0.44, "status": "wasting", "severity": "mild", "progress": "baseline"},
            {"date": "2026-04-05", "risk": 0.53, "status": "wasting", "severity": "moderate", "progress": "deteriorating"},
            {"date": "2026-05-07", "risk": 0.67, "status": "wasting", "severity": "moderate", "progress": "deteriorating"},
        ],
    },
    {
        "pid": "C-1011",
        "sex": "male",
        "dob": "2025-06-18",
        "facility": "CCHC-04",
        "scenario": "stagnation",
        "follow_up": "2026-09-18",
        "visits": [
            {"date": "2026-04-18", "risk": 0.69, "status": "wasting", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-05-20", "risk": 0.48, "status": "underweight", "severity": "mild", "progress": "improving"},
            {"date": "2026-06-22", "risk": 0.47, "status": "underweight", "severity": "mild", "progress": "stagnating"},
            {"date": "2026-07-24", "risk": 0.46, "status": "underweight", "severity": "mild", "progress": "stagnating"},
        ],
    },
    {
        "pid": "C-1012",
        "sex": "female",
        "dob": "2024-07-07",
        "facility": "KMCC-01",
        "scenario": "missed",
        "follow_up": "2026-06-30",
        "overdue": True,
        "visits": [
            {"date": "2026-02-28", "risk": 0.81, "status": "wasting", "severity": "severe", "progress": "baseline"},
            {"date": "2026-04-01", "risk": 0.76, "status": "wasting", "severity": "severe", "progress": "stable"},
            {"date": "2026-05-03", "risk": 0.73, "status": "wasting", "severity": "moderate", "progress": "stable"},
        ],
    },
    {
        "pid": "C-1013",
        "sex": "male",
        "dob": "2025-02-02",
        "facility": "GCNU-02",
        "scenario": "improving",
        "follow_up": "2026-09-14",
        "visits": [
            {"date": "2026-03-14", "risk": 0.60, "status": "underweight", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-04-16", "risk": 0.49, "status": "underweight", "severity": "mild", "progress": "improving"},
            {"date": "2026-05-18", "risk": 0.37, "status": "normal", "severity": "none", "progress": "improving"},
            {"date": "2026-06-20", "risk": 0.29, "status": "normal", "severity": "none", "progress": "improving"},
            {"date": "2026-07-22", "risk": 0.24, "status": "normal", "severity": "none", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1014",
        "sex": "female",
        "dob": "2025-07-01",
        "facility": "CCHC-04",
        "scenario": "baseline",
        "follow_up": "2026-09-19",
        "visits": [
            {"date": "2026-06-01", "risk": 0.64, "status": "wasting", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-07-04", "risk": 0.58, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-08-06", "risk": 0.57, "status": "wasting", "severity": "moderate", "progress": "stagnating"},
        ],
    },
    {
        "pid": "C-1015",
        "sex": "male",
        "dob": "2024-05-15",
        "facility": "CCHC-04",
        "scenario": "improving",
        "follow_up": "2026-09-22",
        "visits": [
            {"date": "2026-02-15", "risk": 0.72, "status": "wasting", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-03-18", "risk": 0.55, "status": "underweight", "severity": "moderate", "progress": "improving"},
            {"date": "2026-04-20", "risk": 0.42, "status": "underweight", "severity": "mild", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1016",
        "sex": "female",
        "dob": "2025-01-28",
        "facility": "CCHC-04",
        "scenario": "deteriorating",
        "follow_up": "2026-09-16",
        "visits": [
            {"date": "2026-03-22", "risk": 0.35, "status": "normal", "severity": "none", "progress": "baseline"},
            {"date": "2026-04-24", "risk": 0.48, "status": "underweight", "severity": "mild", "progress": "deteriorating"},
            {"date": "2026-05-26", "risk": 0.63, "status": "wasting", "severity": "moderate", "progress": "deteriorating"},
        ],
    },
    {
        "pid": "C-1017",
        "sex": "male",
        "dob": "2024-11-18",
        "facility": "CCHC-04",
        "scenario": "stable",
        "follow_up": "2026-09-11",
        "visits": [
            {"date": "2026-04-05", "risk": 0.26, "status": "normal", "severity": "none", "progress": "baseline"},
            {"date": "2026-05-07", "risk": 0.25, "status": "normal", "severity": "none", "progress": "stable"},
            {"date": "2026-06-09", "risk": 0.27, "status": "normal", "severity": "none", "progress": "stable"},
        ],
    },
    {
        "pid": "C-1018",
        "sex": "female",
        "dob": "2025-03-12",
        "facility": "KMCC-01",
        "scenario": "improving",
        "follow_up": "2026-09-17",
        "visits": [
            {"date": "2026-04-12", "risk": 0.79, "status": "wasting", "severity": "severe", "progress": "baseline"},
            {"date": "2026-05-14", "risk": 0.61, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-06-16", "risk": 0.45, "status": "underweight", "severity": "mild", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1019",
        "sex": "male",
        "dob": "2024-08-03",
        "facility": "KMCC-01",
        "scenario": "stagnation",
        "follow_up": "2026-09-09",
        "visits": [
            {"date": "2026-02-20", "risk": 0.68, "status": "stunting", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-03-24", "risk": 0.66, "status": "stunting", "severity": "moderate", "progress": "stable"},
            {"date": "2026-04-26", "risk": 0.65, "status": "stunting", "severity": "moderate", "progress": "stagnating"},
            {"date": "2026-05-28", "risk": 0.64, "status": "stunting", "severity": "moderate", "progress": "stagnating"},
        ],
    },
    {
        "pid": "C-1020",
        "sex": "female",
        "dob": "2025-06-07",
        "facility": "KMCC-01",
        "scenario": "baseline",
        "follow_up": "2026-09-21",
        "visits": [
            {"date": "2026-05-30", "risk": 0.51, "status": "underweight", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-07-02", "risk": 0.46, "status": "underweight", "severity": "mild", "progress": "improving"},
            {"date": "2026-08-04", "risk": 0.41, "status": "underweight", "severity": "mild", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1021",
        "sex": "male",
        "dob": "2024-12-22",
        "facility": "GCNU-02",
        "scenario": "improving",
        "follow_up": "2026-09-13",
        "visits": [
            {"date": "2026-03-10", "risk": 0.83, "status": "wasting", "severity": "severe", "progress": "baseline"},
            {"date": "2026-04-12", "risk": 0.67, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-05-14", "risk": 0.52, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-06-16", "risk": 0.38, "status": "underweight", "severity": "mild", "progress": "improving"},
        ],
    },
    {
        "pid": "C-1022",
        "sex": "female",
        "dob": "2025-04-09",
        "facility": "GCNU-02",
        "scenario": "missed",
        "follow_up": "2026-07-15",
        "overdue": True,
        "visits": [
            {"date": "2026-04-01", "risk": 0.59, "status": "underweight", "severity": "moderate", "progress": "baseline"},
            {"date": "2026-05-03", "risk": 0.57, "status": "underweight", "severity": "moderate", "progress": "stable"},
            {"date": "2026-06-05", "risk": 0.56, "status": "underweight", "severity": "moderate", "progress": "stagnating"},
        ],
    },
    {
        "pid": "C-1023",
        "sex": "male",
        "dob": "2024-07-25",
        "facility": "CCHC-04",
        "scenario": "relapse",
        "follow_up": "2026-09-07",
        "visits": [
            {"date": "2026-01-20", "risk": 0.75, "status": "wasting", "severity": "severe", "progress": "baseline"},
            {"date": "2026-02-22", "risk": 0.52, "status": "wasting", "severity": "moderate", "progress": "improving"},
            {"date": "2026-04-26", "risk": 0.34, "status": "underweight", "severity": "mild", "progress": "improving"},
            {"date": "2026-06-30", "risk": 0.61, "status": "wasting", "severity": "moderate", "progress": "deteriorating"},
        ],
    },
    {
        "pid": "C-1024",
        "sex": "female",
        "dob": "2025-08-14",
        "facility": "KMCC-01",
        "scenario": "stable",
        "follow_up": "2026-09-25",
        "visits": [
            {"date": "2026-06-10", "risk": 0.19, "status": "normal", "severity": "none", "progress": "baseline"},
            {"date": "2026-07-12", "risk": 0.18, "status": "normal", "severity": "none", "progress": "stable"},
            {"date": "2026-08-14", "risk": 0.20, "status": "normal", "severity": "none", "progress": "stable"},
        ],
    },
]


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _measurements(sex: str, age: float, risk: float) -> dict:
    base_w = 9.5 if sex == "female" else 10.0
    weight = round(base_w + age * 0.12 - risk * 3.2, 2)
    height = round(70 + age * 0.7 - risk * 4, 1)
    muac = round(14.5 - risk * 4.5, 1)
    head = round(43.5 + age * 0.18 - risk * 0.8, 1)
    return {
        "weight_kg": max(4.0, weight),
        "height_cm": max(55.0, height),
        "muac_cm": max(9.0, muac),
        "head_circumference_cm": max(34.0, head),
        "age_months": age,
    }


def _resolve_visit_outcome(pid: str, visit_number: int, spec: dict) -> dict:
    """Read the stored demonstration case outcome used only to build sample measurements."""
    canonical = get_demo_outcome(pid, visit_number)
    if canonical is None:
        return {
            "status": spec["status"],
            "severity": spec["severity"],
            "risk": spec["risk"],
            "progress": spec["progress"],
            "date": spec["date"],
        }
    status, severity, score = canonical
    return {
        "status": status,
        "severity": severity,
        "risk": score,
        "progress": spec["progress"],
        "date": spec["date"],
    }


def _caregiver_label(pid: str) -> str:
    return f"Synthetic caregiver ({pid})"


def _validate_cases() -> None:
    """Ensure seed cases satisfy minimum visit history and chronological ordering."""
    errors: list[str] = []
    for case in CASES:
        pid = case["pid"]
        visits = case["visits"]
        if len(visits) < 3:
            errors.append(f"{pid}: requires at least 3 visits, found {len(visits)}")
            continue
        if visits[0]["progress"] != "baseline":
            errors.append(f"{pid}: first visit must have progress=baseline")
        prev_date = None
        for spec in visits:
            visit_date = _dt(spec["date"]).date()
            if prev_date is not None and visit_date <= prev_date:
                errors.append(f"{pid}: visit dates must be strictly increasing")
                break
            prev_date = visit_date
    if errors:
        raise ValueError("Invalid CASES seed data:\n" + "\n".join(errors))


def _renumber_child_visits(db, child_id) -> bool:
    visits = db.scalars(
        select(Visit).where(Visit.child_id == child_id).order_by(Visit.visit_date, Visit.visit_number)
    ).all()
    if not visits:
        return False
    expected = list(range(1, len(visits) + 1))
    current = [v.visit_number for v in visits]
    if current == expected:
        return False
    for i, visit in enumerate(visits):
        visit.visit_number = 10_000 + i
    db.flush()
    for i, visit in enumerate(visits):
        visit.visit_number = i + 1
    return True


def _add_case_visit(
    db,
    *,
    child: Child,
    case: dict,
    idx: int,
    spec: dict,
    fac,
    recorder,
    model,
    policy_cfg,
    predicted_visits: list[Visit],
    previous_pred: Prediction | None,
    baseline_pred: Prediction | None,
    consecutive: int,
    prev_meas: dict | None,
    lookup: dict | None,
) -> tuple[Visit, Prediction, Prediction | None, Prediction | None, int, dict, list[Visit]]:
    dob = child.date_of_birth
    visit_number = idx + 1
    outcome = _resolve_visit_outcome(case["pid"], visit_number, spec)
    visit_date = _dt(outcome["date"])
    age = (visit_date.date().year - dob.year) * 12 + visit_date.date().month - dob.month
    meas = _measurements(case["sex"], float(age), outcome["risk"])
    visit = Visit(
        child_id=child.id,
        facility_id=fac.id,
        visit_number=visit_number,
        visit_date=visit_date,
        visit_type=VisitType.ROUTINE if idx == 0 else VisitType.FOLLOW_UP,
        scheduled=True,
        recorded_by=recorder.id,
        model_version_id=None,
        status=VisitStatus.SUBMITTED,
        confirmation_attested=True,
        data_quality={"complete": True, "optional_missing": 1, "synthetic": True},
    )
    db.add(visit)
    db.flush()
    db.add(
        AnthropometricRecord(
            visit_id=visit.id,
            age_months=meas["age_months"],
            sex=Sex(case["sex"]),
            height_cm=meas["height_cm"],
            weight_kg=meas["weight_kg"],
            muac_cm=meas["muac_cm"],
            head_circumference_cm=meas["head_circumference_cm"],
            birth_weight_kg=2.7 if case["sex"] == "female" else 2.9,
            previous_weight_kg=prev_meas["weight_kg"] if prev_meas else None,
            previous_height_cm=prev_meas["height_cm"] if prev_meas else None,
        )
    )
    prev_meas = meas
    db.add(
        SocioeconomicRecord(
            visit_id=visit.id,
            wealth_proxy="second",
            maternal_education="secondary",
            paternal_education="primary",
            maternal_employment="home",
            household_size=5,
            geographical_area=fac.district.lower(),
            drinking_water="piped",
            sanitation="improved",
        )
    )
    db.add(
        DietaryRecord(
            visit_id=visit.id,
            breastfeeding_status="continued" if age < 18 else "stopped",
            breastfeeding_duration_months=round(min(max(float(age), 0), 24), 1),
            complementary_feeding=age >= 6,
            dietary_diversity_score=3 if outcome["risk"] > 0.5 else 5,
            meal_frequency=3,
            food_groups=["grains", "dairy"] if outcome["risk"] > 0.5 else ["grains", "dairy", "legumes", "flesh"],
            micronutrient_supplementation=True,
        )
    )
    db.add(
        MaternalChildHealthRecord(
            visit_id=visit.id,
            maternal_bmi=20.5,
            gestational_age_weeks=38,
            immunization_uptodate=True,
            vitamin_a=True,
            recent_diarrhoea=outcome["risk"] > 0.7,
            recent_respiratory_illness=False,
            recent_hospitalization=outcome["risk"] > 0.8,
            birth_characteristics=(
                "Synthetic demonstration data: term birth, facility delivery, "
                "no neonatal complications recorded in the demonstration record."
            ),
        )
    )
    db.flush()
    return visit, None, baseline_pred, previous_pred, consecutive, prev_meas, predicted_visits + [visit]


def _seed_demo_case(
    db,
    case: dict,
    facs: dict,
    recorder,
    model,
    policy_cfg,
    enc: FieldEncryptor,
    lookup: dict,
) -> None:
    fac = facs[case["facility"]]
    dob = date.fromisoformat(case["dob"])
    child = Child(
        facility_id=fac.id,
        pseudonymous_id=case["pid"],
        external_patient_id_encrypted=enc.encrypt(f"EXT-{case['pid']}"),
        date_of_birth=dob,
        sex=Sex(case["sex"]),
        status=EntityStatus.ACTIVE,
        responsible_team=case.get("team", fac.name),
        registered_by=recorder.id,
        assigned_doctor_id=recorder.id,
    )
    db.add(child)
    db.flush()
    db.add(
        Caregiver(
            child_id=child.id,
            kinship="mother",
            display_name=_caregiver_label(case["pid"]),
            phone_encrypted=enc.encrypt(f"+250780{case['pid'][-4:]}01"),
        )
    )
    previous_pred = None
    baseline_pred = None
    consecutive = 0
    predicted_visits = []
    prev_meas: dict | None = None
    for idx, spec in enumerate(case["visits"]):
        _, pred, baseline_pred, previous_pred, consecutive, prev_meas, predicted_visits = _add_case_visit(
            db,
            child=child,
            case=case,
            idx=idx,
            spec=spec,
            fac=fac,
            recorder=recorder,
            model=model,
            policy_cfg=policy_cfg,
            predicted_visits=predicted_visits,
            previous_pred=previous_pred,
            baseline_pred=baseline_pred,
            consecutive=consecutive,
            prev_meas=prev_meas,
            lookup=lookup,
        )

    if predicted_visits:
        # Structured reviews for all but the latest visit (latest remains awaiting review).
        for visit in predicted_visits[:-1]:
            pred = db.scalar(
                select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True))
            )
            if not pred:
                continue
            db.add(
                ClinicianReview(
                    facility_id=fac.id,
                    child_id=child.id,
                    visit_id=visit.id,
                    prediction_id=pred.id,
                    reviewer_user_id=recorder.id,
                    review_state=ClinicianReviewState.COMPLETED,
                    clinician_assessment=ClinicianAssessment.AGREE,
                    clinical_note="Synthetic demonstration review recorded after this visit.",
                    workflow_action=ClinicianWorkflowAction.CONTINUE_MONITORING,
                    reviewed_at=visit.visit_date + timedelta(hours=4),
                )
            )
            # Preserve legacy free-text note for historical audit (not used for status).
            db.add(
                ClinicalNote(
                    child_id=child.id,
                    visit_id=visit.id,
                    author_id=recorder.id,
                    body=(
                        "[Clinician review] Assessment: agree. Workflow: monitor. "
                        "Synthetic demonstration review recorded after this visit. "
                        "(Legacy note preserved; structured clinician_reviews is authoritative.)"
                    ),
                    created_at=visit.visit_date + timedelta(hours=4),
                )
            )
        db.add(
            ClinicalNote(
                child_id=child.id,
                visit_id=predicted_visits[-1].id,
                author_id=recorder.id,
                body=(
                    f"[Synthetic demonstration note] Clinical review for {case['pid']} ({case['scenario']} scenario). "
                    "Anthropometry recorded; AI-assisted assessment pending structured clinician review."
                ),
            )
        )

    follow_date = date.fromisoformat(case["follow_up"])
    status = FollowUpStatus.OVERDUE if case.get("overdue") else FollowUpStatus.SUGGESTED
    db.add(
        FollowUpSchedule(
            child_id=child.id,
            facility_id=fac.id,
            expected_date=follow_date,
            interval_days=30,
            responsible_user_id=recorder.id,
            status=status,
            notes=None if case.get("overdue") else "Suggested by demo seed — confirm in clinic workflow.",
        )
    )
    if case.get("overdue") or case["pid"] == "C-1042":
        from app.models.enums import AlertStatus, AlertType
        from app.models.operations import Alert
        from app.services.alerts import event_window_key, severity_for

        if case.get("overdue"):
            key = event_window_key(str(child.id), AlertType.MISSED_FOLLOW_UP, None, extra="seed")
            db.add(
                Alert(
                    child_id=child.id,
                    facility_id=fac.id,
                    type=AlertType.MISSED_FOLLOW_UP,
                    severity=severity_for(AlertType.MISSED_FOLLOW_UP, policy_cfg),
                    status=AlertStatus.OPEN,
                    message="Follow-up overdue",
                    trigger_value={"disclaimer": policy_cfg.disclaimer, "expected_date": case["follow_up"]},
                    threshold_version=policy_cfg.policy_id,
                    event_window_key=key,
                )
            )
        if case["pid"] == "C-1042":
            key = event_window_key(str(child.id), AlertType.STAGNATION, str(predicted_visits[-1].id), extra="seed")
            db.add(
                Alert(
                    child_id=child.id,
                    facility_id=fac.id,
                    type=AlertType.STAGNATION,
                    severity=severity_for(AlertType.STAGNATION, policy_cfg),
                    status=AlertStatus.OPEN,
                    message="Progress stagnation detected",
                    trigger_value={
                        "previous_risk": 0.61,
                        "current_risk": 0.59,
                        "risk_velocity": 0.02,
                        "disclaimer": "Research / Demo Configuration",
                    },
                    threshold_version=policy_cfg.policy_id,
                    event_window_key=key,
                )
            )


def seed() -> None:
    _validate_cases()
    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)):
            print("Seed skipped — data already present")
            return
        directory = json.loads((CONTRACTS / "demo_directory.json").read_text())
        orgs = {}
        for item in directory["organizations"]:
            org = Organization(name=item["name"], code=item["code"], type=OrganizationType(item["type"]), status=EntityStatus.ACTIVE)
            db.add(org)
            db.flush()
            orgs[item["code"]] = org
        facs = {}
        for item in directory["facilities"]:
            fac = Facility(
                organization_id=orgs[item["organization_code"]].id,
                name=item["name"],
                code=item["code"],
                district=item["district"],
                type=FacilityType(item["type"]),
                status=EntityStatus.ACTIVE,
            )
            db.add(fac)
            db.flush()
            facs[item["code"]] = fac
        for item in directory["users"]:
            if item["role"] != "doctor":
                continue
            user = User(
                facility_id=facs[item["facility_code"]].id,
                email=item["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=item["full_name"],
                qualifications=item.get("qualifications"),
                experience=item.get("experience"),
                role=UserRole(item["role"]),
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()

        model = ModelVersion(
            model_key="GA-RGCA",
            version="GA-RGCA-v4-Rolling-RSL",
            architecture="GA-RGCA v4 Rolling SuperLearner",
            feature_schema_version="ga-rgca-v4-rolling-current-visit",
            label_schema_version="ga-rgca-v4-types",
            training_dataset_version="rolling-2025-2026",
            calibration_version="ga-rgca-v4-superlearner",
            embedding_dimension=96,
            embedding_space_id="ga-rgca-v4-rolling-rsl-fused-latent",
            status=ModelStatus.ACTIVE,
            is_demo=False,
            activated_at=datetime.now(UTC),
            notes="Research decision-support prototype. Clinician confirmation required.",
        )
        db.add(model)
        db.flush()
        policy_cfg = load_clinical_policy()
        policy_row = ClinicalPolicyVersion(
            policy_key=policy_cfg.policy_id,
            stagnation_threshold=policy_cfg.stagnation_threshold,
            consecutive_visits=policy_cfg.consecutive_followups,
            deterioration_delta=policy_cfg.deterioration_delta,
            overdue_grace_days=policy_cfg.overdue_grace_days,
            relapse_prior_improvement=policy_cfg.relapse_prior_improvement,
            relapse_increase=policy_cfg.relapse_increase,
            default_followup_days=policy_cfg.default_followup_days,
            status="active",
            notes="Clinic follow-up policy",
            payload={"disclaimer": policy_cfg.disclaimer},
        )
        db.add(policy_row)

        db.commit()
        print("Seed complete: clinic accounts only. Children are added through registration.")
    finally:
        db.close()


def seed_missing_cases() -> None:
    """Sample children are not loaded. Register children in the clinic workflow."""
    print("Sample children are not loaded. Register children in the clinic workflow.")


def repair_visit_integrity() -> None:
    """Renumber visits to V1..Vn and backfill missing visits from CASES definitions."""
    _validate_cases()
    db = SessionLocal()
    try:
        cases_by_pid = {case["pid"]: case for case in CASES}
        recorder = db.scalar(select(User).where(User.email == "doctor@demo.local"))
        model = db.scalar(select(ModelVersion).where(ModelVersion.status == ModelStatus.ACTIVE).limit(1))
        if not recorder or not model:
            print("Repair skipped — seed data not present")
            return

        policy_cfg = load_clinical_policy()
        facs = {facility.code: facility for facility in db.scalars(select(Facility)).all()}
        renumbered = 0
        appended = 0

        children = db.scalars(select(Child).where(Child.deleted_at.is_(None))).all()
        for child in children:
            if _renumber_child_visits(db, child.id):
                renumbered += 1

            case = cases_by_pid.get(child.pseudonymous_id)
            if not case:
                continue

            visits = db.scalars(
                select(Visit).where(Visit.child_id == child.id).order_by(Visit.visit_number)
            ).all()
            if len(visits) >= len(case["visits"]):
                continue

            predicted_visits = list(visits)
            baseline_pred = None
            previous_pred = None
            consecutive = 0
            prev_meas = None
            fac = facs.get(case["facility"]) or db.get(Facility, child.facility_id)

            for visit in visits:
                pred = db.scalar(
                    select(Prediction).where(Prediction.visit_id == visit.id, Prediction.is_active.is_(True))
                )
                if pred:
                    if baseline_pred is None:
                        baseline_pred = pred
                    previous_pred = pred
                anthro = visit.anthropometry
                if anthro:
                    prev_meas = {"weight_kg": anthro.weight_kg, "height_cm": anthro.height_cm}
                if visit.id and pred:
                    metric = db.scalar(
                        select(TrajectoryMetric)
                        .where(TrajectoryMetric.to_visit_id == visit.id)
                        .order_by(TrajectoryMetric.created_at.desc())
                        .limit(1)
                    )
                    if metric and metric.progress_state in {ProgressState.STAGNATING, ProgressState.STABLE}:
                        consecutive += 1

            for idx in range(len(visits), len(case["visits"])):
                spec = case["visits"][idx]
                _, _, baseline_pred, previous_pred, consecutive, prev_meas, predicted_visits = _add_case_visit(
                    db,
                    child=child,
                    case=case,
                    idx=idx,
                    spec=spec,
                    fac=fac,
                    recorder=recorder,
                    model=model,
                    policy_cfg=policy_cfg,
                    predicted_visits=predicted_visits,
                    previous_pred=previous_pred,
                    baseline_pred=baseline_pred,
                    consecutive=consecutive,
                    prev_meas=prev_meas,
                    lookup=None,
                )
                appended += 1

        db.commit()

        issues: list[str] = []
        for child in db.scalars(select(Child).where(Child.deleted_at.is_(None))).all():
            visit_rows = db.scalars(
                select(Visit).where(Visit.child_id == child.id).order_by(Visit.visit_number)
            ).all()
            numbers = [row.visit_number for row in visit_rows]
            expected = list(range(1, len(numbers) + 1))
            if len(visit_rows) < 3:
                issues.append(f"{child.pseudonymous_id}: only {len(visit_rows)} visit(s)")
            elif numbers != expected:
                issues.append(f"{child.pseudonymous_id}: non-sequential numbering {numbers}")

        print(f"Repair complete: {renumbered} children renumbered, {appended} visit(s) appended.")
        if issues:
            print("Remaining issues:\n" + "\n".join(issues))
        else:
            print(f"Verified {len(children)} children each have >=3 sequential visits (V1..Vn).")
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "missing":
        seed_missing_cases()
    elif len(sys.argv) > 1 and sys.argv[1] == "repair":
        repair_visit_integrity()
    else:
        seed()
