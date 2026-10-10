"""Phase 4 uses invented test fixtures, never observed prices or clinical guidance."""
from copy import deepcopy

from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention.engine import recommend
from components.c2_counterfactual_intervention.evaluation import synthetic_request
from components.c2_counterfactual_intervention.schemas import RecommendationRequest


EVIDENCE = {"kind": "synthetic_test", "source": "automated test fixture", "observed_on": "2026-01-01"}


def planning_request():
    raw = synthetic_request(3, 3, "bounded_search").model_dump(mode="json")
    raw["max_cards"] = 5
    raw["food_planning"] = {
        "catalog": [{"food_id": "fixture-food", "name": "Fixture food", "food_group": "fixture group",
                     "price": {"amount_lkr": "60", "quantity": "2", "unit": "piece", "evidence": EVIDENCE},
                     "locally_available": True, "availability_evidence": EVIDENCE}],
        "budget": {"amount_lkr": "100", "period": "day", "evidence": EVIDENCE},
        "alternatives": [{"alternative_id": "option-b", "title": "Test feeding practice",
                          "reason": "Supplied test practice linked to the validated change",
                          "changes": [{"feature": "meals_per_day", "from_value": 3, "to_value": 4}],
                          "foods": [{"food_id": "fixture-food", "quantity": "2", "unit": "piece",
                                     "serving_assumption": "test-only incremental quantity for one day"}],
                          "period": "day", "practice_evidence": EVIDENCE, "practice_reviewed": True,
                          "suitability_evidence": EVIDENCE, "age_suitable": True,
                          "clinically_suitable": True, "caregiver_practical": True}]}
    return raw


def result(raw):
    return recommend(RecommendationRequest.model_validate(raw))


def test_affordable_card_and_api_contract():
    raw = planning_request()
    response = result(raw)
    assert len(response.cards) == 1
    card = response.cards[0]
    assert card.incremental_cost_lkr == "60"
    assert card.affordability == "affordable" and card.availability == "available"
    assert card.food_options == ["Fixture food"]
    assert card.professional_review_required
    api = TestClient(app).post("/interventions/recommendations", json=raw)
    assert api.status_code == 200
    assert api.json()["cards"][0]["alternative_id"] == "option-b"
    assert "risk" not in str(api.json()["cards"]).lower()
    assert "%" not in str(api.json()["cards"])


def test_unaffordable_and_missing_price():
    raw = planning_request()
    raw["food_planning"]["budget"]["amount_lkr"] = "50"
    response = result(raw)
    assert response.cards == []
    assert any("exceeds" in reason for item in response.rejected_or_unresolved for reason in item.reasons)
    raw = planning_request()
    raw["food_planning"]["catalog"][0]["price"] = None
    response = result(raw)
    assert response.cards == []
    assert any("price unknown" in reason for item in response.rejected_or_unresolved for reason in item.reasons)


def test_unknown_availability_period_units_and_safety():
    cases = [
        ("catalog", "locally_available", None, "availability unknown"),
        ("budget", "period", "week", "periods differ"),
        ("quantity", "unit", "g", "units differ"),
        ("alternative", "clinically_suitable", None, "clinically_suitable: unknown"),
        ("alternative", "programme_required", True, "programme_eligible: unknown"),
    ]
    for owner, field, value, expected in cases:
        raw = planning_request()
        data = raw["food_planning"]
        obj = {"catalog": data["catalog"][0], "budget": data["budget"],
               "quantity": data["alternatives"][0]["foods"][0],
               "alternative": data["alternatives"][0]}[owner]
        obj[field] = value
        response = result(raw)
        assert not response.cards
        assert any(expected in reason for item in response.rejected_or_unresolved for reason in item.reasons)


def test_synthetic_evidence_cannot_verify_real_planning():
    from components.c2_counterfactual_intervention.tests.test_phase3 import MockC1Predictor, real_request
    raw = real_request().model_dump(mode="json")
    raw["food_planning"] = planning_request()["food_planning"]
    response = recommend(RecommendationRequest.model_validate(raw), MockC1Predictor())
    assert not response.cards
    assert any("synthetic test evidence" in reason for item in response.rejected_or_unresolved for reason in item.reasons)


def test_exact_match_empty_and_repeatability():
    raw = planning_request()
    raw["food_planning"]["alternatives"][0]["changes"][0]["to_value"] = 5
    response = result(raw)
    assert not response.cards
    assert any("no model-supported" in reason for item in response.rejected_or_unresolved for reason in item.reasons)
    raw = planning_request()
    second = deepcopy(raw["food_planning"]["alternatives"][0])
    second["alternative_id"] = "option-a"
    second["foods"][0]["quantity"] = "1"
    raw["food_planning"]["alternatives"].append(second)
    first = result(raw).model_dump(mode="json")
    assert first == result(raw).model_dump(mode="json")
    assert [card["alternative_id"] for card in first["cards"]] == ["option-a", "option-b"]
    assert [card["incremental_cost_lkr"] for card in first["cards"]] == ["30", "60"]


def test_unreviewed_practice_and_missing_budget_evidence():
    raw = planning_request()
    raw["food_planning"]["alternatives"][0]["practice_reviewed"] = False
    response = result(raw)
    assert not response.cards
    assert any("not approved" in reason for item in response.rejected_or_unresolved for reason in item.reasons)
    raw = planning_request()
    raw["food_planning"]["budget"]["evidence"] = None
    response = result(raw)
    assert not response.cards
    assert any("food budget: evidence missing" in reason for item in response.rejected_or_unresolved for reason in item.reasons)


def test_referral_requires_configured_category():
    raw = planning_request()
    raw["food_planning"]["referral_policy"] = {
        "trigger_categories": ["higher_concern"], "evidence": EVIDENCE,
        "message": "Test-only referral pathway for professional assessment"}
    response = result(raw)
    assert response.professional_referral_recommended
    assert "professional assessment" in response.referral_message
