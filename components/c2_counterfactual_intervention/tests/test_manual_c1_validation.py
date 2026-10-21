"""Manual C1 UI contract checks use a stub, never fake clinical evidence."""

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from backend.app.main import app
from components.c2_counterfactual_intervention.c1_predictors import C1PredictionUnavailable, SimulatedC1Predictor
from components.c2_counterfactual_intervention.manual_c1_validation import ManualC1Request, run_manual_c1


def example_request(**changes):
    values = {
        "test_id": "TEST-0014", "age_months": 24, "sex": "Female",
        "height_cm": 80, "weight_kg": 10, "birth_weight_kg": 2.8,
        "household_size": 4, "maternal_age_years": 28,
        "maternal_education": "O/L passed",
        "household_income_range": "Rs.20,000 to Rs. 50,000",
        "father_occupation": "Manual worker", "mother_occupation": "Housewife",
        "exclusive_breastfeeding": "Yes", "breastfeeding_duration": "More than 6 months",
        "complementary_feeding_timing": "After 6 months",
        "meal_frequency": "3 meals/day", "dietary_diversity": "2 to 5 varieties",
        "triposha_supplementation": "No", "vitamin_supplementation": "Yes",
    }
    return ManualC1Request.model_validate({**values, **changes})


class ContractStub:
    """Deterministic test double with C1-shaped output; no real model claims."""

    source = "GA-RGCA-v3"

    def __init__(self, fail_candidate=False, scenario="unchanged"):
        self.calls = []
        self.fail_candidate = fail_candidate
        self.scenario = scenario

    def predict(self, snapshot, changes=None):
        self.calls.append(snapshot.predict_payload(changes))
        if self.fail_candidate and changes:
            raise C1PredictionUnavailable("candidate inference unavailable")
        output = SimulatedC1Predictor(self.scenario).predict(snapshot, changes)
        return output.model_copy(update={"prediction_source": "GA-RGCA-v3",
                                         "model_version": "GA-RGCA-v3", "mode": "PYTORCH"})


def test_manual_input_reaches_predictor_and_changes_only_feeding_fields():
    stub = ContractStub()
    result = run_manual_c1(example_request(weight_kg=11.5), stub)
    assert result["submitted_input"]["weight_kg"] == 11.5
    assert result["baseline"]["prediction_source"] == "GA-RGCA-v3"
    assert len(result["candidates"]) == 3
    assert result["approved_intervention_cards"] == []
    assert result["clinical_use"] is False
    assert all(item["model_policy_result"] in ("rejected", "unresolved") for item in result["candidates"])
    baseline = stub.calls[0]
    assert all(payload["allow_demo"] is False for payload in stub.calls)
    for candidate in stub.calls[1:]:
        assert candidate["historical_baseline"] == baseline["historical_baseline"]
        assert candidate["anthropometric"] == baseline["anthropometric"]
        assert candidate["socioeconomic"] == baseline["socioeconomic"]
        assert {key: value for key, value in candidate["ga_rgca_context"].items()
                if key not in ("meal_frequency", "dietary_diversity")} == {
                    key: value for key, value in baseline["ga_rgca_context"].items()
                    if key not in ("meal_frequency", "dietary_diversity")}


def test_failed_candidate_has_no_fabricated_prediction():
    result = run_manual_c1(example_request(), ContractStub(fail_candidate=True))
    assert result["baseline"] is not None
    assert all(item["prediction"] is None and item["probability_delta"] is None
               and item["model_policy_result"] == "unresolved" for item in result["candidates"])


def test_model_passing_fixture_ranks_candidates_and_budget_changes_only_food_examples():
    # A test double exercises the ranking branch; it is not clinical or real C1 evidence.
    low = run_manual_c1(example_request(budget_lkr="100"), ContractStub(scenario="favorable"))
    high = run_manual_c1(example_request(budget_lkr="3000"), ContractStub(scenario="favorable"))
    assert len(low["ranked_model_comparisons"]) == 3
    assert [item["rank"] for item in low["ranked_model_comparisons"]] == [1, 2, 3]
    assert low["approved_intervention_cards"] == []
    assert low["budget"]["affordability"] == "unresolved"
    assert low["baseline"] == high["baseline"]
    assert low["candidates"] == high["candidates"]
    assert low["food_plans"] and high["food_plans"]
    assert [plan["budget_fit"] for plan in low["food_plans"]] != [
        plan["budget_fit"] for plan in high["food_plans"]]


def test_manual_api_rejects_nonlocal_and_patient_identifiers():
    client = TestClient(app)
    assert client.post("/interventions/manual-c1-validation", json=example_request().model_dump()).status_code == 403
    with pytest.raises(ValidationError):
        example_request(test_id="REAL-CHILD-001")
    with pytest.raises(ValidationError):
        example_request(test_id="SYNTHETIC-PANEL-001")
    assert example_request(test_id="TEST-0024").test_id == "TEST-0024"
    with pytest.raises(ValidationError):
        example_request(age_months=5)
