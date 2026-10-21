"""Versioned food-scenario contract and hard-gate regression tests."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from components.c2_counterfactual_intervention.nutrition_scenarios_v2 import (
    ScenarioRequest, generate_scenarios,
)
from components.c2_counterfactual_intervention.tests.test_manual_c1_validation import ContractStub, example_request


def request_data(**changes):
    data = {
        "age_months": 24,
        "original_c1": {
            "model_version": "GA-RGCA-v3", "prediction_source": "GA-RGCA-v3",
            "predicted_malnutrition_type": "Stunting", "severity": "Moderate",
            "uncertainty_flag": False, "clinical_use": False,
            "input_fingerprint": "invented-baseline-fingerprint",
            "provenance": "supplied_research_assessment",
        },
        "feeding": {
            "meal_frequency": "3 meals/day", "dietary_diversity": "2 to 5 varieties",
            "food_groups": ["rice and cereals"], "provenance": "unverified",
        },
        "household": {
            "budget_lkr": "1500", "budget_period": "weekly",
            "budget_provenance": "user_reported", "allergy_status": "unknown",
            "preparation": "unknown", "local_availability": {},
        },
    }
    for key, value in changes.items():
        data[key] = value
    return data


def run(data):
    return generate_scenarios(ScenarioRequest.model_validate(data))


def test_original_c1_is_unchanged_and_no_candidate_is_repredicted():
    data = request_data()
    original = deepcopy(data["original_c1"])
    result = run(data)
    assert data["original_c1"] == original == result["original_c1"]
    assert result["c1_candidate_calls"] == 0
    assert result["candidate_count"] == 4
    assert len({item["candidate_id"] for item in result["unresolved_or_rejected"]}) == 4
    assert result["ranked_cards"] == []
    assert result["referral_notice"]
    assert all(item["rank"] is None for item in result["unresolved_or_rejected"])


def test_unverified_feeding_allergies_local_stock_and_nutrition_remain_unknown():
    result = run(request_data())
    for item in result["unresolved_or_rejected"]:
        checks = {check["criterion"]: check["state"] for check in item["checks"]}
        assert checks["baseline_provenance"] == "unknown"
        assert checks["allergy_restriction"] == "unknown"
        assert checks["local_availability"] == "unknown"
        assert checks["nutrition_adequacy"] == "unknown"
        assert checks["budget_reference"] == "unknown"


def test_reported_exclusion_and_unavailable_food_are_avoided_when_alternatives_exist():
    data = request_data()
    data["household"].update(allergy_status="reported", excluded_food_ids=["egg_average"],
                             local_availability={"egg_average": False})
    result = run(data)
    assert result["candidate_count"] == 4
    assert all("egg_average" not in {food["food_id"] for food in item["items"]}
               for item in result["unresolved_or_rejected"])


def test_reported_groups_and_budget_change_selected_foods_without_changing_c1():
    base = request_data(method="compare_all", research_algorithm_demo=True)
    different_groups = deepcopy(base)
    different_groups["feeding"]["food_groups"] = ["rice and cereals", "eggs", "fruits"]
    smaller_budget = deepcopy(base)
    smaller_budget["household"]["budget_lkr"] = "400"
    results = [run(data) for data in (base, different_groups, smaller_budget)]
    titles = [{card["title"] for card in result["unresolved_or_rejected"]} for result in results]
    assert titles[0] != titles[1]
    assert titles[0] != titles[2]
    assert all(result["original_c1"] == results[0]["original_c1"] for result in results)
    assert all(result["c1_candidate_calls"] == 0 for result in results)
    assert all(result["ranked_cards"] == [] for result in results)


def test_age_scope_and_no_complementary_plan_below_six_months():
    under_six = run(request_data(age_months=5))
    assert under_six["candidate_count"] == 0
    assert under_six["ranked_cards"] == under_six["unresolved_or_rejected"] == []
    older = run(request_data(age_months=36))
    assert all(next(check for check in item["checks"] if check["criterion"] == "age_scope")["state"] == "unknown"
               for item in older["unresolved_or_rejected"])


def test_budget_changes_reference_fit_but_not_original_c1_or_approval():
    low = request_data()
    high = request_data()
    low["household"]["budget_lkr"] = "100"
    high["household"]["budget_lkr"] = "3000"
    left, right = run(low), run(high)
    assert left["original_c1"] == right["original_c1"]
    assert left["ranked_cards"] == right["ranked_cards"] == []
    assert {row["title"] for row in left["unresolved_or_rejected"]} != {
        row["title"] for row in right["unresolved_or_rejected"]}
    assert left["c1_candidate_calls"] == right["c1_candidate_calls"] == 0


def test_contract_rejects_incoherent_budget_and_unknown_fields_and_is_repeatable():
    data = request_data()
    left, right = run(data), run(deepcopy(data))
    left["method_results"]["bounded_search"].pop("runtime_ms")
    right["method_results"]["bounded_search"].pop("runtime_ms")
    assert left == right
    bad = deepcopy(data)
    bad["household"]["budget_provenance"] = "unknown"
    with pytest.raises(ValidationError):
        ScenarioRequest.model_validate(bad)
    bad = deepcopy(data)
    bad["household"]["household_income_as_treatment"] = True
    with pytest.raises(ValidationError):
        ScenarioRequest.model_validate(bad)


def test_versioned_api_is_local_only_and_has_no_predictor_dependency():
    data = request_data()
    assert TestClient(app).post("/interventions/diet-scenarios-v2", json=data).status_code == 403
    client = TestClient(app, client=("127.0.0.1", 12345))
    response = client.post("/interventions/diet-scenarios-v2", json=data)
    assert response.status_code == 200
    assert response.json()["c1_candidate_calls"] == 0
    assert response.json()["ranked_cards"] == []


def test_baseline_api_calls_c1_once_without_hypothetical_change(monkeypatch):
    from app.routers import interventions

    stub = ContractStub()
    monkeypatch.setattr(interventions, "RealC1HttpPredictor", lambda: stub)
    client = TestClient(app, client=("127.0.0.1", 12345))
    response = client.post("/interventions/baseline-c1-v2",
                           json=example_request().model_dump(mode="json"))
    assert response.status_code == 200
    assert response.json()["c1_calls"] == 1
    assert len(stub.calls) == 1
    assert stub.calls[0]["allow_demo"] is False
    assert response.json()["feeding_provenance"] == "unverified"
