"""Software-boundary tests; the stub below is never presented as genuine inference."""
from copy import deepcopy
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from components.c2_counterfactual_intervention.automatic_analysis import (
    AutomaticRequest, demonstration_snapshot, load_automatic_baseline, run_automatic_analysis,
)
from components.c2_counterfactual_intervention.c1_predictors import C1PredictionUnavailable, SimulatedC1Predictor


class StubC1:
    """Test double for genuine-output contract shape, never a real model result."""
    source = "GA-RGCA-v3"

    def __init__(self):
        self.payloads = []

    def predict(self, snapshot, changes=None):
        self.payloads.append(snapshot.predict_payload(changes))
        output = SimulatedC1Predictor().predict(snapshot, changes)
        return output.model_copy(update={"prediction_source": "GA-RGCA-v3", "model_version": "GA-RGCA-v3", "mode": "PYTORCH"})


@pytest.mark.parametrize("case_id,age,band", [
    ("synthetic_5m", 5, "under 6 months"),
    ("synthetic_24m", 24, "24-59 months (older-child category)"),
    ("synthetic_59m", 59, "24-59 months (older-child category)"),
])
def test_age_boundaries_and_immutable_history(case_id, age, band):
    stub = StubC1()
    result = run_automatic_analysis(AutomaticRequest(case_id=case_id), stub)
    assert result["age_months"] == age
    assert result["guidance"]["age_band"] == band
    assert result["approved_intervention_cards"] == []
    assert len(result["candidates"]) == (0 if age == 5 else 3)
    assert all(payload["allow_demo"] is False for payload in stub.payloads)
    if age == 5:
        assert stub.payloads == []
        assert result["baseline"] is None
        assert result["original_feeding"] == {}
    else:
        assert all(payload["historical_baseline"] == stub.payloads[0]["historical_baseline"] for payload in stub.payloads)
    assert all(result["guidance"]["quantity"] is None for _ in [0])
    assert {row["method"] for row in result["research_test_runs"]} == (set() if age == 5 else {"dice", "face_graph"})
    assert all(row["prediction_source"] == "SIMULATED_TEST_ONLY" and row["approved_cards"] == 0
               for row in result["research_test_runs"])


@pytest.mark.parametrize("budget", [None, Decimal("0"), Decimal("50"), Decimal("5000")])
def test_budget_never_approves_unknown_food_cost(budget):
    result = run_automatic_analysis(AutomaticRequest(budget_lkr=budget, budget_period="weekly"), StubC1())
    assert result["budget"]["affordability"] == "unresolved"
    assert result["approved_intervention_cards"] == []
    assert all(item["affordability"] == "unresolved" and item["indicative_incremental_cost_lkr"] is None
               for item in result["candidates"])
    assert result == run_automatic_analysis(AutomaticRequest(budget_lkr=budget, budget_period="weekly"), StubC1())


def test_research_ranking_deduplicates_and_never_promotes_worsening(monkeypatch):
    from components.c2_counterfactual_intervention import automatic_analysis as module
    original = module.next_categories
    monkeypatch.setattr(module, "next_categories", lambda snapshot: original(snapshot) + deepcopy(original(snapshot)))
    result = run_automatic_analysis(AutomaticRequest(), StubC1())
    assert len(result["candidates"]) == 3
    ranks = [item["rank"] for item in result["candidates"] if item["rank"] is not None]
    assert ranks
    assert ranks == list(range(1, len(ranks) + 1))
    assert all(item["rank"] is None for item in result["candidates"] if item["disposition"] == "rejected_model_worsening")


def test_simulated_predictor_cannot_supply_automatic_results():
    with pytest.raises(C1PredictionUnavailable, match="genuine C1"):
        run_automatic_analysis(AutomaticRequest(), SimulatedC1Predictor())
    with pytest.raises(C1PredictionUnavailable, match="genuine C1"):
        load_automatic_baseline("synthetic_24m", SimulatedC1Predictor())


def test_candidate_response_mismatch_fails_entire_analysis():
    class MismatchedStub(StubC1):
        def predict(self, snapshot, changes=None):
            output = super().predict(snapshot, changes)
            return output.model_copy(update={"prediction_source": "SIMULATED_TEST_ONLY"}) if changes else output

    with pytest.raises(C1PredictionUnavailable, match="genuine, nonclinical C1 candidate"):
        run_automatic_analysis(AutomaticRequest(), MismatchedStub())


def test_offline_api_and_invalid_case_fail_closed(monkeypatch):
    monkeypatch.delenv("C1_INFERENCE_URL", raising=False)
    client = TestClient(app)
    assert client.get("/interventions/automatic-baseline", params={"case_id": "unknown"}).status_code == 422
    assert client.get("/interventions/automatic-baseline").status_code == 503
    assert client.post("/interventions/automatic-analysis", json={"case_id": "synthetic_24m"}).status_code == 503
    young = client.post("/interventions/automatic-analysis", json={"case_id": "synthetic_5m"})
    assert young.status_code == 200
    assert young.json()["mode"] == "unsupported_age_no_prediction"
    assert young.json()["baseline"] is None


def test_snapshot_rejects_non_demonstration_input():
    with pytest.raises(ValueError):
        demonstration_snapshot("patient-001")
