"""Invented case catalogue must never preassign model outcomes."""

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from components.c2_counterfactual_intervention.live_case_library_v2 import live_case_library
from components.c2_counterfactual_intervention.manual_c1_validation import ManualC1Request, manual_snapshot
from components.c2_counterfactual_intervention.live_case_validation_v2 import run_live_cases
from components.c2_counterfactual_intervention.c1_predictors import C1PredictionUnavailable
from pydantic import ValidationError


def test_case_library_has_valid_distinct_model_inputs_without_risk_labels():
    catalogue = live_case_library()
    assert catalogue["contract_version"] == "c2-live-case-library-v2"
    cases = catalogue["cases"]
    assert len(cases) >= 5
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert len({case["input"]["age_months"] for case in cases}) > 1
    for case in cases:
        assert "prediction" not in case and "risk" not in case
        request = ManualC1Request.model_validate(case["input"])
        payload = manual_snapshot(request).predict_payload()
        assert payload["allow_demo"] is False
        assert payload["child_pseudonymous_id"] == case["case_id"]
        assert case["food_groups"]


def test_invented_historical_status_is_explicit_and_immutable_in_c1_payload():
    cases = {case["case_id"]: case for case in live_case_library()["cases"]}
    underweight = ManualC1Request.model_validate(cases["TEST-0019"]["input"])
    payload = manual_snapshot(underweight).predict_payload()
    assert payload["historical_baseline"]["underweight"] == "Severe"
    assert payload["historical_baseline"]["stunting"] == "Normal"
    assert payload["allow_demo"] is False
    changed = manual_snapshot(underweight).predict_payload({"meal_frequency": "3 meals/day"})
    assert changed["historical_baseline"] == payload["historical_baseline"]
    invalid = {**cases["TEST-0020"]["input"], "historical_mam": True}
    with pytest.raises(ValidationError, match="cannot both be true"):
        ManualC1Request.model_validate(invalid)


def test_local_case_catalogue_api_returns_inputs_without_predictions():
    response = TestClient(app, client=("127.0.0.1", 50000)).get("/interventions/live-case-library-v2")
    assert response.status_code == 200
    assert response.json() == live_case_library()


def test_batch_refuses_non_genuine_predictor():
    class ResearchTestPredictor:
        source = "research-test"

    with pytest.raises(C1PredictionUnavailable, match="genuine"):
        run_live_cases(ResearchTestPredictor())


def test_batch_api_is_local_and_calls_the_live_runner(monkeypatch):
    from app.routers import interventions

    monkeypatch.setattr(interventions, "run_live_cases", lambda: {"mode": "checked"})
    local = TestClient(app, client=("127.0.0.1", 50000))
    assert local.get("/interventions/live-case-validation-v2").json() == {"mode": "checked"}
    remote = TestClient(app, client=("192.0.2.1", 50000))
    assert remote.get("/interventions/live-case-validation-v2").status_code == 403
