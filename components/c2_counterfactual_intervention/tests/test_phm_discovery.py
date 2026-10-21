"""No private PHM records are bundled with these software regression tests."""

import pytest

from components.c2_counterfactual_intervention.phm_discovery import (
    compare_with_retry, eligibility_reasons, public_report, snapshot_from_row, upward_candidates,
)
from components.c2_counterfactual_intervention.c1_predictors import C1PredictionUnavailable


def _row():
    return {
        "Link_Quality": "Good", "Age_months_2025": "24",
        "Height_cm_2025": "80", "Weight_kg_2025": "10",
        "Implausible_Z_Flag_2025": "0", "Sex": "Female",
        "Meal_Frequency_per_Day_2025": "2 meals/day",
        "Dietary_Diversity_2025": "Less than 2 varieties",
        "Acute_Malnutrition_2025": "MAM", "Underweight_2025": "Moderate",
        "Stunting_2025": "Normal", "Birth_Weight_g": None,
        "Maternal_Age_years_2025": None,
    }


def test_technical_eligibility_rejects_missing_history_and_bad_categories():
    row = _row()
    assert eligibility_reasons(row) == []
    row["Height_cm_2025"] = None
    row["Meal_Frequency_per_Day_2025"] = "five"
    assert "historical_growth_missing" in eligibility_reasons(row)
    assert "feeding_category_incompatible" in eligibility_reasons(row)
    with pytest.raises(ValueError):
        snapshot_from_row(row, "TEST-ONLY")


def test_source_mapping_keeps_missing_values_missing_and_context_immutable():
    snapshot = snapshot_from_row(_row(), "TEST-ONLY")
    assert snapshot.provenance.endswith("feeding field observation provenance unverified")
    assert snapshot.historical_baseline["birth_weight_kg"] is None
    assert snapshot.ga_rgca_context["maternal_age_years"] is None
    original = snapshot.predict_payload()
    assert original["allow_demo"] is False
    options = upward_candidates(snapshot)
    assert len(options) == 8
    assert sum(adjacent for _, adjacent in options) == 3
    for change, _ in options:
        modified = snapshot.predict_payload(change)
        expected = {**original, "ga_rgca_context": {**original["ga_rgca_context"], **change}}
        assert modified == expected


def test_no_feeding_candidate_below_six_months_or_at_upper_bound():
    row = _row()
    row["Age_months_2025"] = "5"
    assert "age_outside_6_59_or_missing" in eligibility_reasons(row)
    row["Age_months_2025"] = "24"
    row["Meal_Frequency_per_Day_2025"] = "4+ meals/day"
    row["Dietary_Diversity_2025"] = "More than 5 varieties"
    assert "no_upward_feeding_category" in eligibility_reasons(row)


def test_public_report_never_serializes_private_snapshot():
    result = {
        "source_name": "research.xlsx", "source_sha256": "abc", "scan_order": "source row order",
        "complete_cohort_scan": False, "exclusions": {}, "scanned_candidate_pass_rate": 0.0,
        "whole_cohort_pass_rate": None,
        "counts": {"total_linked_profiles": 1, "technically_eligible_profiles": 1,
                   "genuine_c1_baselines": 1, "candidates_evaluated": 0,
                   "improvement_signals": 0, "model_rule_passing": 0,
                   "profiles_with_model_rule_pass": 0,
                   "mixed_tradeoffs": 0, "worsening_signals": 0,
                   "uncertainty_exclusions": 0, "unresolved_feasibility": 0},
        "cases": [{"case_id": "PHM-LOCAL-0001", "snapshot": {"secret_name": "PRIVATE-NAME"},
                   "baseline": {}, "candidates": []}],
    }
    report = public_report(result)
    assert "PRIVATE-NAME" not in report
    assert "secret_name" not in report
    assert "No matching case" in report


def test_transient_c1_failure_retries_the_whole_comparison(monkeypatch):
    calls = []

    def compare(_snapshot, _predictor):
        calls.append(1)
        if len(calls) == 1:
            raise C1PredictionUnavailable("transient timeout")
        return {"verified": True}

    monkeypatch.setattr("components.c2_counterfactual_intervention.phm_discovery.compare", compare)
    monkeypatch.setattr("components.c2_counterfactual_intervention.phm_discovery.time.sleep", lambda _: None)
    assert compare_with_retry(None, None) == {"verified": True}
    assert len(calls) == 2
