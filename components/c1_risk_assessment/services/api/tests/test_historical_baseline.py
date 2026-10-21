"""Baseline selection for GA-RGCA history. No database and no model scores."""

from datetime import datetime

from app.services.prediction import assemble_historical_baseline


def test_follow_up_uses_earlier_visit_and_keeps_unknown_distinct_from_absent():
    baseline = assemble_historical_baseline(
        current={
            "visit_number": 2,
            "visit_date": datetime(2026, 6, 1),
            "age_months": 30,
            "height_cm": 90,
            "weight_kg": 12,
            "birth_weight_kg": 2.9,
        },
        earlier=[
            {
                "visit_number": 1,
                "visit_date": datetime(2025, 6, 1),
                "age_months": 18,
                "height_cm": 76,
                "weight_kg": 9,
                "birth_weight_kg": 2.9,
            }
        ],
        context={"historical_stunting": "Moderate"},
    )
    assert baseline["source"] == "earlier_visit"
    assert baseline["height_cm"] == 76
    assert baseline["weight_kg"] == 9
    assert baseline["age_months"] == 18
    assert baseline["assessment_date"].startswith("2025-06-01")
    assert baseline["horizon_end_date"].startswith("2026-06-01")
    assert baseline["mam"] is None
    assert baseline["sam"] is None
    assert baseline["underweight"] is None
    assert baseline["stunting"] == "Moderate"


def test_first_assessment_is_labeled_as_the_baseline():
    baseline = assemble_historical_baseline(
        current={
            "visit_number": 1,
            "visit_date": datetime(2025, 1, 31),
            "age_months": 12,
            "height_cm": 72,
            "weight_kg": 8,
            "birth_weight_kg": 2.5,
        },
        earlier=[],
        context={"historical_mam": 0, "historical_sam": 1, "historical_underweight": "Normal", "historical_stunting": "Severe"},
    )
    assert baseline["source"] == "baseline_assessment"
    assert baseline["height_cm"] == 72
    assert baseline["mam"] == 0
    assert baseline["sam"] == 1
    assert baseline["underweight"] == "Normal"
    assert baseline["stunting"] == "Severe"
    assert baseline["horizon_end_date"].startswith("2026-01-31")


def test_invalid_clinical_values_stay_unknown():
    baseline = assemble_historical_baseline(
        current={"visit_number": 1, "visit_date": datetime(2025, 3, 1), "height_cm": 70, "weight_kg": 8},
        earlier=[],
        context={"historical_mam": 2, "historical_underweight": "Positive"},
    )
    assert baseline["mam"] is None
    assert baseline["underweight"] is None
