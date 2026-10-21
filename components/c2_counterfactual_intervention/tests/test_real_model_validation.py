"""C2 validation is distinct from recommendations and fails closed without C1."""
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from components.c2_counterfactual_intervention.c1_compat import next_categories
from components.c2_counterfactual_intervention.c1_predictors import SimulatedC1Predictor
from components.c2_counterfactual_intervention.real_model_validation import _standalone_policy_reasons, run_validation, run_standalone_validation, standalone_input_fingerprint, standalone_snapshot, validation_snapshot
from components.c2_counterfactual_intervention.standalone_demo import StandaloneRequest, run_standalone


def test_fixed_fixture_changes_only_feeding_categories():
    snapshot = validation_snapshot()
    assert snapshot.child_pseudonymous_id.startswith("SYNTHETIC-")
    assert snapshot.historical_baseline["height_cm"] == 80
    options = next_categories(snapshot)
    assert len(options) == 3
    for change in options:
        payload = snapshot.predict_payload(change)
        assert payload["allow_demo"] is False
        assert payload["historical_baseline"] == snapshot.historical_baseline
        assert set(change) <= {"meal_frequency", "dietary_diversity"}


def test_simulator_cannot_supply_real_validation_output():
    class MislabelledPredictor(SimulatedC1Predictor):
        source = "GA-RGCA-v3"

    with pytest.raises(ValueError, match="genuine, nonclinical"):
        run_validation(MislabelledPredictor())


def test_validation_api_fails_closed_when_c1_unavailable(monkeypatch):
    monkeypatch.delenv("C1_INFERENCE_URL", raising=False)
    response = TestClient(app).get("/interventions/c1-validation")
    assert response.status_code == 503
    assert response.json() == {"detail": "C1 inference URL is unconfigured or insecure"}


def test_optional_standalone_validation_uses_exact_fixture_and_only_feeding_changes():
    standalone = run_standalone(StandaloneRequest())
    assert standalone["input_fingerprint"] == standalone_input_fingerprint("synthetic_24m")
    assert run_standalone(StandaloneRequest(budget_lkr=500))["input_fingerprint"] == standalone["input_fingerprint"]
    snapshot = standalone_snapshot("synthetic_24m")
    assert snapshot.child_pseudonymous_id == standalone["profile"]["test_id"]
    assert snapshot.historical_baseline["height_cm"] == standalone["profile"]["historical_height_cm"]
    assert {key: snapshot.ga_rgca_context[key] for key in standalone["original_feeding"]} == standalone["original_feeding"]
    baseline = snapshot.predict_payload()
    assert len(next_categories(snapshot)) == len(standalone["cards"]) == 3
    for changes in next_categories(snapshot):
        candidate = snapshot.predict_payload(changes)
        assert candidate["allow_demo"] is False
        assert candidate["historical_baseline"] == baseline["historical_baseline"]
        assert candidate["anthropometric"] == baseline["anthropometric"]
        assert candidate["socioeconomic"] == baseline["socioeconomic"]
        assert {key: value for key, value in candidate["ga_rgca_context"].items() if key not in changes} == {
            key: value for key, value in baseline["ga_rgca_context"].items() if key not in changes}


def test_optional_validation_offline_does_not_block_standalone(monkeypatch):
    monkeypatch.delenv("C1_INFERENCE_URL", raising=False)
    client = TestClient(app)
    assert client.get("/interventions/standalone-validation?case_id=synthetic_24m").status_code == 503
    result = client.post("/interventions/standalone-analysis", json={"case_id": "synthetic_24m"})
    assert result.status_code == 200 and len(result.json()["cards"]) == 3
    young = client.get("/interventions/standalone-validation?case_id=synthetic_5m")
    assert young.status_code == 200 and young.json()["candidates"] == []


def test_real_comparison_rules_reject_worsening_without_authorization():
    snapshot = standalone_snapshot("synthetic_24m")
    baseline = SimulatedC1Predictor().predict(snapshot)
    candidate = baseline.model_copy(update={"stunting_probability": baseline.stunting_probability + 0.05})
    rejected, unresolved = _standalone_policy_reasons(baseline, candidate)
    assert "stunting_probability increases" in rejected
    assert "no approved categorical improvement" in rejected
    assert "real-mode research authorization has not been supplied" in unresolved
