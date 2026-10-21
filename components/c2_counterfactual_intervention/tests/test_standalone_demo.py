"""Standalone synthetic workflow never inherits real C1 authorization or claims."""
from decimal import Decimal

from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention import educational_baskets
from components.c2_counterfactual_intervention.standalone_demo import StandaloneRequest, run_standalone


def test_offline_api_uses_only_synthetic_predictor(monkeypatch):
    monkeypatch.delenv("C1_INFERENCE_URL", raising=False)
    client = TestClient(app)
    response = client.post("/interventions/standalone-analysis", json={"case_id": "synthetic_24m", "budget_lkr": "500", "budget_period": "weekly"})
    assert response.status_code == 200
    result = response.json()
    assert result["c1_required"] is False and result["clinical_use"] is False
    assert result["baseline"]["prediction_source"] == "SIMULATED_TEST_ONLY"
    assert result["profile"]["test_id"] == "SYNTHETIC-C2-24M"
    assert result["profile"]["historical_height_cm"] == 80
    assert result["profile"]["historical_weight_kg"] == 10
    assert {method["name"] for method in result["methods"]} == {"bounded_search", "dice", "face_graph"}
    assert len(result["cards"]) == 3
    assert [card["changes"] for card in result["cards"]] == [
        {"dietary_diversity": "More than 5 varieties"},
        {"meal_frequency": "4+ meals/day"},
        {"meal_frequency": "4+ meals/day", "dietary_diversity": "More than 5 varieties"},
    ]
    card = result["cards"][0]
    assert card["status"] == "Eligible in Research Test"
    assert card["prediction"]["prediction_source"] == "SIMULATED_TEST_ONLY"
    assert card["real_world_suitability"] == card["real_world_availability"] == "unknown"
    assert card["professional_review_required"] is True
    assert all(candidate["prediction"]["prediction_source"] == "SIMULATED_TEST_ONLY" for candidate in result["cards"])
    assert all(len(candidate["food_plans"][0]["schedule"]) == 7 for candidate in result["cards"])
    assert len(card["food_plans"][0]["schedule"]) == 7
    assert [day["day"] for day in card["food_plans"][0]["schedule"]] == [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert all(slot["foods"] for day in card["food_plans"][0]["schedule"] for slot in day["slots"])


def test_budget_changes_only_plan_rank_and_fit():
    results = [run_standalone(StandaloneRequest(budget_lkr=Decimal(amount)))
               for amount in ("500", "1500", "3000")]
    assert [sum(plan["budget_fit"] == "within_budget" for plan in result["food_plans"]) for result in results] == [1, 3, 4]
    assert results[0]["baseline"] == results[1]["baseline"] == results[2]["baseline"]
    assert [[card["changes"] for card in result["cards"]] for result in results] == [[card["changes"] for card in results[0]["cards"]]] * 3
    assert all(result["cards"][0]["status"] == "Eligible in Research Test" for result in results)
    assert results[0]["food_plans"][0]["budget_remaining_lkr"] == "261.52"
    assert any(plan["shortfall_lkr"] for plan in results[0]["food_plans"])


def test_ages_and_missing_budget():
    young = run_standalone(StandaloneRequest(case_id="synthetic_5m"))
    assert young["baseline"] is None and young["cards"] == [] and young["food_plans"] == []
    assert young["profile"]["historical_height_cm"] is None
    assert young["methods"] == []
    older = run_standalone(StandaloneRequest(case_id="synthetic_59m"))
    assert older["guidance"]["age_band"] == "24-59 months (older-child category)"
    assert len(older["cards"]) == 3 and len(older["food_plans"]) == 4
    assert all(plan["budget_fit"] == "unknown" for plan in older["food_plans"])


def test_rejected_synthetic_fixture_stays_rejected_at_high_budget():
    result = run_standalone(StandaloneRequest(budget_lkr=Decimal("3000")), simulator_case="worsening")
    assert result["cards"] == []
    assert result["rejected_or_unresolved"]
    assert all(item["status"] == "rejected" for item in result["rejected_or_unresolved"])
    assert all(plan["budget_fit"] == "within_budget" for plan in result["food_plans"])


def test_missing_price_withholds_schedule_and_age_group_evidence(monkeypatch):
    original = educational_baskets.bundled_history
    monkeypatch.setattr(educational_baskets, "bundled_history", lambda: [row for row in original() if row.food_id != "egg_average"])
    result = run_standalone(StandaloneRequest(budget_lkr=Decimal("3000")))
    egg = next(plan for plan in result["food_plans"] if plan["title"] == "Egg and greens example")
    assert egg["budget_fit"] == "unknown" and egg["schedule"] == []
    assert egg["schedule_status"] == "evidence_incomplete"
    assert result["cards"][0]["status"] == "Eligible in Research Test"


def test_periods_match_shopping_costs():
    for period in ("daily", "weekly", "monthly"):
        result = run_standalone(StandaloneRequest(budget_lkr=Decimal("1500"), budget_period=period))
        assert all(plan["cost_period"] == plan["budget_period"] == period for plan in result["food_plans"])
        assert all(plan["items"] and plan["guideline_scope_note"] for plan in result["food_plans"])
    assert run_standalone(StandaloneRequest(budget_lkr=Decimal("1500"))) == run_standalone(StandaloneRequest(budget_lkr=Decimal("1500")))
