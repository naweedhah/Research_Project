"""C1-shaped software-contract tests. All predictions here are simulated."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention.c1_compat import C1Snapshot, DIVERSITY, MEALS
from components.c2_counterfactual_intervention.c1_engine import run_c1
from components.c2_counterfactual_intervention.c1_predictors import (
    C1PredictionUnavailable, RealC1HttpPredictor, SimulatedC1Predictor, parse_c1_output,
)
from components.c2_counterfactual_intervention.supervisor_demo import demo_request, official_price_demo


def test_exact_vocabulary_and_immutable_wire_snapshot():
    snapshot = demo_request().snapshot
    baseline = snapshot.predict_payload()
    changed = snapshot.predict_payload({"meal_frequency": MEALS[2], "dietary_diversity": DIVERSITY[1]})
    expected = deepcopy(baseline)
    expected["ga_rgca_context"]["meal_frequency"] = MEALS[2]
    expected["ga_rgca_context"]["dietary_diversity"] = DIVERSITY[1]
    assert changed == expected
    assert baseline["historical_baseline"] == changed["historical_baseline"]
    assert changed["allow_demo"] is False
    for field in ("meal_frequency", "dietary_diversity"):
        with pytest.raises(ValueError):
            snapshot.predict_payload({field: "invented score"})


def test_missing_history_and_cohort_boundary():
    data = demo_request().snapshot.model_dump()
    data["historical_baseline"].pop("height_cm")
    with pytest.raises(ValueError, match="historical height"):
        C1Snapshot.model_validate(data)
    data = demo_request().snapshot.model_dump()
    data["historical_baseline"]["age_months"] = 60
    with pytest.raises(ValueError, match="cohort"):
        C1Snapshot.model_validate(data)
    data["historical_baseline"]["age_months"] = 59
    assert C1Snapshot.model_validate(data).historical_baseline["age_months"] == 59
    assert run_c1(demo_request(scenario="too_young")).cards == []


def test_four_condition_outputs_and_distribution_guards():
    output = SimulatedC1Predictor().predict(demo_request().snapshot)
    assert all(0 <= getattr(output, f) <= 1 for f in ("underweight_probability", "stunting_probability"))
    assert set(output.acute_probabilities) == {"Normal", "MAM", "SAM"}
    assert sum(output.acute_probabilities.values()) == pytest.approx(1)
    assert sum(output.severity_probabilities.values()) == pytest.approx(1)
    broken = output.model_dump()
    broken["acute_probabilities"].pop("SAM")
    with pytest.raises(ValueError, match="incomplete"):
        type(output).model_validate(broken)
    broken = output.model_dump()
    broken["severity_probabilities"]["severe"] = 2
    with pytest.raises(ValueError):
        type(output).model_validate(broken)


def test_simulator_varied_outcomes_repeatability_and_no_benefit_claim():
    request = demo_request()
    first = run_c1(request)
    assert first == run_c1(request)
    assert first.cards and first.baseline["predicted_malnutrition_type"] == "Underweight"
    assert first.cards[0]["professional_review_required"] is True
    assert "SIMULATED" in first.banner
    assert "benefit is established" in first.cards[0]["explanation"]
    assert first.c1_integrated is False
    assert run_c1(demo_request(scenario="no_solution")).cards == []
    data = request.snapshot.model_dump()
    data["ga_rgca_context"].update(meal_frequency=MEALS[0], dietary_diversity=DIVERSITY[0])
    assert SimulatedC1Predictor().predict(C1Snapshot.model_validate(data)).predicted_malnutrition_type == "Stunting"


def test_policy_and_feasibility_fail_closed():
    request = demo_request()
    request.policy.approved_for_research = False
    result = run_c1(request)
    assert not result.cards and result.rejected_or_unresolved[0]["status"] == "unresolved"
    request = demo_request(scenario="unknown_availability")
    result = run_c1(request)
    assert not result.cards and result.rejected_or_unresolved[0]["status"] == "unresolved"
    assert not run_c1(demo_request(scenario="unaffordable")).cards
    request = demo_request()
    request.policy.allowed_type_transitions = []
    assert not run_c1(request).cards
    assert not run_c1(demo_request(scenario="uncertain")).cards
    assert not run_c1(demo_request(scenario="unchanged")).cards
    assert not run_c1(demo_request(scenario="worsening")).cards


def test_severity_and_individual_condition_nonworsening():
    class SeverityWorse(SimulatedC1Predictor):
        def predict(self, snapshot, changes=None):
            output = super().predict(snapshot, changes)
            return output.model_copy(update={"severity": "Severe"}) if changes else output

    class StuntingWorse(SimulatedC1Predictor):
        def predict(self, snapshot, changes=None):
            output = super().predict(snapshot, changes)
            return output.model_copy(update={"stunting_probability": .99}) if changes else output

    for predictor, reason in ((SeverityWorse(), "severity worsens"),
                              (StuntingWorse(), "stunting_probability worsens")):
        result = run_c1(demo_request(), predictor)
        assert not result.cards
        assert reason in result.rejected_or_unresolved[0]["reasons"][0]


def test_food_price_and_suitability_remain_unresolved():
    request = demo_request()
    request.food_planning.catalog[0].price = None
    result = run_c1(request)
    assert not result.cards
    assert any("price unknown" in reason for item in result.rejected_or_unresolved for reason in item["reasons"])
    request = demo_request()
    request.food_planning.alternatives[0].clinically_suitable = None
    result = run_c1(request)
    assert not result.cards
    assert any("clinically_suitable" in reason for item in result.rejected_or_unresolved for reason in item["reasons"])


def test_real_mode_unavailable_and_demo_response_rejected():
    request = demo_request().model_copy(update={"mode": "real"})
    with pytest.raises(C1PredictionUnavailable):
        run_c1(request, SimulatedC1Predictor())
    with pytest.raises(C1PredictionUnavailable):
        RealC1HttpPredictor(base_url="")
    raw = {"calibrated_probabilities": {"ga_rgca": {}}}
    with pytest.raises(C1PredictionUnavailable):
        parse_c1_output(raw, real=True, expected_version="GA-RGCA-v3")
    simulated = SimulatedC1Predictor().predict(demo_request().snapshot)
    demo = {"status": simulated.predicted_malnutrition_type, "severity": simulated.severity,
            "model_version": "GA-RGCA-v3", "calibration_version": "ga-rgca-v3-binary-calibrators",
            "feature_schema_version": "ga-rgca-v3-current-visit-baseline", "prediction_source": "DEMO",
            "prediction_task": "twelve_month_nutritional_risk", "score_kind": "highest_condition_probability",
            "score_is_probability": True, "score_is_calibrated": False, "clinical_use": False,
            "data_limitations": [], "mode": "DEMO", "calibrated_probabilities": {"ga_rgca": {
                "underweight_probability": simulated.underweight_probability,
                "stunting_probability": simulated.stunting_probability,
                "normal_acute_probability": simulated.acute_probabilities["Normal"],
                "mam_probability": simulated.acute_probabilities["MAM"],
                "sam_probability": simulated.acute_probabilities["SAM"],
                "predicted_malnutrition_type": simulated.predicted_malnutrition_type,
                "acute_status": simulated.acute_status, "severity": simulated.severity,
                "severity_probabilities": simulated.severity_probabilities,
                "uncertainty_flag": False}}}
    with pytest.raises(C1PredictionUnavailable, match="demo"):
        parse_c1_output(demo, real=True, expected_version="GA-RGCA-v3")


def test_real_mode_requires_food_planning_before_predictor(monkeypatch):
    request = demo_request().model_copy(update={"mode": "real", "food_planning": None})
    canonical = json.dumps(request.policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    monkeypatch.setenv("C1_REAL_POLICY_SHA256", hashlib.sha256(canonical.encode()).hexdigest())

    class UnexpectedPredictor:
        source = "GA-RGCA-v3"
        def predict(self, *args):
            pytest.fail("real predictor must not be called without food evidence")

    with pytest.raises(C1PredictionUnavailable, match="food and LKR affordability evidence"):
        run_c1(request, UnexpectedPredictor())


def test_official_reference_scenario_keeps_local_status_unknown():
    base = dict(food_id="mysore_dhall_average", quantity=Decimal("100"), unit="g", as_of=date(2026, 10, 22))
    result = official_price_demo(**base)
    assert result["official_reference"]["published_price_lkr"] == "334.52"
    assert result["official_reference"]["indicative_reference_cost_lkr"] == "33.452"
    assert result["official_reference"]["freshness_status"] == "HISTORICAL_REFERENCE"
    assert result["scenario"]["reference_cost_budget_comparison"] == "unresolved"
    assert result["scenario"]["local_availability"] == "unknown"
    with_budget = official_price_demo(**base, budget_lkr=Decimal("30"), budget_period="day",
        quantity_period="day", budget_source="illustrative user input",
        local_availability="available", availability_source="illustrative user report")
    assert with_budget["scenario"]["reference_cost_budget_comparison"] == "above illustrative budget"
    assert with_budget["scenario"]["verified_local_affordability"] == "UNKNOWN"
    with pytest.raises(ValueError, match="provenance"):
        official_price_demo(**base, local_availability="available")
    with pytest.raises(ValueError, match="compatible"):
        official_price_demo(**{**base, "unit": "piece"})


def test_http_adapter_validates_service_response_and_never_requests_demo(monkeypatch):
    from components.c2_counterfactual_intervention import c1_predictors
    calls = []
    snapshot = demo_request().snapshot

    class Reply:
        status_code = 200
        def __init__(self, body):
            self.body = body
        def json(self):
            return self.body

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] <= 10
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, url):
            return Reply({"ga_rgca_loaded": True, "prediction_source": "GA-RGCA-v3",
                          "model_version": "GA-RGCA-v3"})
        def post(self, url, json):
            calls.append(deepcopy(json))
            assert json["allow_demo"] is False
            values = {"Meal_Frequency_per_Day": json["ga_rgca_context"]["meal_frequency"],
                      "Dietary_Diversity": json["ga_rgca_context"]["dietary_diversity"],
                      "Hist_2025_Height_cm": json["historical_baseline"]["height_cm"],
                      "Hist_2025_Weight_kg": json["historical_baseline"]["weight_kg"],
                      "Hist_2025_Age_months": json["historical_baseline"]["age_months"]}
            body = {"status": "Underweight", "severity": "Moderate", "model_version": "GA-RGCA-v3",
                    "calibration_version": "ga-rgca-v3-binary-calibrators",
                    "feature_schema_version": "ga-rgca-v3-current-visit-baseline",
                    "prediction_source": "GA-RGCA-v3", "prediction_task": "twelve_month_nutritional_risk",
                    "score_kind": "highest_condition_probability", "score_is_probability": True,
                    "score_is_calibrated": False, "clinical_use": False, "data_limitations": [], "mode": "PYTORCH",
                    "calibrated_probabilities": {"ga_rgca": {
                        "underweight_probability": .6, "stunting_probability": .4,
                        "normal_acute_probability": .8, "mam_probability": .15, "sam_probability": .05,
                        "predicted_malnutrition_type": "Underweight", "acute_status": "Normal",
                        "severity": "Moderate", "severity_probabilities": {"normal": .2, "moderate": .7, "severe": .1},
                        "uncertainty_flag": False, "input_snapshot": {"values": values}}}}
            return Reply(body)

    monkeypatch.setattr(c1_predictors.httpx, "Client", Client)
    adapter = RealC1HttpPredictor(base_url="https://c1.example", token="test-only")
    assert adapter.predict(snapshot).prediction_source == "GA-RGCA-v3"
    assert adapter.predict(snapshot, {"meal_frequency": MEALS[2]}).prediction_source == "GA-RGCA-v3"
    assert calls[0]["historical_baseline"] == calls[1]["historical_baseline"]
    assert calls[0]["ga_rgca_context"]["meal_frequency"] != calls[1]["ga_rgca_context"]["meal_frequency"]


@pytest.mark.parametrize("method", ["bounded_search", "dice", "face_graph"])
def test_all_three_methods_have_simulated_path(method):
    result = run_c1(demo_request(method=method))
    assert result.mode == "simulated" and result.method == method
    assert all(set(card["changes"]).issubset({"meal_frequency", "dietary_diversity"}) for card in result.cards)


def test_api_response_and_real_failure(monkeypatch):
    client = TestClient(app)
    payload = demo_request().model_dump(mode="json")
    response = client.post("/interventions/c1-research", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["cards"] and body["clinical_use"] is False and body["c1_integrated"] is False
    assert "risk_reduction" not in str(body)
    assert "underweight_probability" not in str(body)
    payload["mode"] = "real"
    response = client.post("/interventions/c1-research", json=payload)
    assert response.status_code == 503
    monkeypatch.setenv("C2_REAL_API_TOKEN", "test-only-token")
    response = client.post("/interventions/c1-research", json=payload)
    assert response.status_code == 401
