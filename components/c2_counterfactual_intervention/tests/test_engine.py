"""Synthetic software tests; no fixture represents a clinical recommendation."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention.candidate_generation import generate_candidates
from components.c2_counterfactual_intervention.contracts import synthetic_contract
from components.c2_counterfactual_intervention.engine import recommend
from components.c2_counterfactual_intervention.feature_policy import ACTIONABLE, validate_changes
from components.c2_counterfactual_intervention.feasibility import check_feasibility
from components.c2_counterfactual_intervention.predictor import SyntheticTestPredictor
from components.c2_counterfactual_intervention.schemas import Change, ChildFeatures, FeasibilityContext, RecommendationRequest


FIELDS = ("meals_per_day", "dietary_diversity")
CHECKS = ("available", "practical", "age_suitable", "eligible", "clinically_suitable", "transition_justified")


def payload():
    return {
        "child_id": "SYNTHETIC-001",
        "mode": "test",
        "child": {"age_months": 24, "sex": "female", "birth_weight_kg": 2.8,
                  "historical_exclusive_breastfeeding": True, "household_income_band": "low",
                  "meals_per_day": 3, "dietary_diversity": 3, "supplement_use": False},
        "context": {"budget_units": 10, "supplement_access": False,
                    "supplement_programme_eligible": None, "supplement_clinically_suitable": None,
                    **{name: {feature: True for feature in FIELDS} for name in CHECKS}},
    }


def test_generation_deduplication_and_protected_preservation():
    child = ChildFeatures.model_validate(payload()["child"])
    candidates = generate_candidates(child)
    assert len(candidates) == 3
    assert len({tuple((c.feature, c.to_value) for c in group) for group in candidates}) == 3
    for group in candidates:
        assert not validate_changes(child, group)
        assert all(c.feature in ACTIONABLE for c in group)
        changed = child.model_validate({**child.model_dump(), **{c.feature: c.to_value for c in group}})
        for name in ("age_months", "sex", "birth_weight_kg", "historical_exclusive_breastfeeding", "household_income_band", "supplement_use"):
            assert getattr(changed, name) == getattr(child, name)


@pytest.mark.parametrize("feature", ["supplement_access", "supplement_use", "household_income_band", "age_months", "birth_weight_kg"])
def test_protected_features_rejected(feature):
    child = ChildFeatures.model_validate(payload()["child"])
    assert "protected feature" in str(validate_changes(child, (Change(feature=feature, from_value=0, to_value=1),)))
    assert all(feature != c.feature for group in generate_candidates(child) for c in group)


@pytest.mark.parametrize("change", [
    Change(feature="meals_per_day", from_value=3, to_value=5),
    Change(feature="dietary_diversity", from_value=2, to_value=4),
    Change(feature="meals_per_day", from_value=3, to_value=2),
    Change(feature="meals_per_day", from_value=True, to_value=4),
])
def test_invalid_feeding_transitions(change):
    child = ChildFeatures.model_validate(payload()["child"])
    assert "invalid transition" in str(validate_changes(child, (change,)))


def test_duplicate_change_rejected():
    child = ChildFeatures.model_validate(payload()["child"])
    change = Change(feature="meals_per_day", from_value=3, to_value=4)
    assert "duplicate change" in str(validate_changes(child, (change, change)))


def test_predictor_adapter_and_repeatability():
    class RecordingPredictor:
        model_id = "recording-test"
        contract = synthetic_contract(model_id)
        def __init__(self):
            self.calls = []
        def predict_category(self, child):
            self.calls.append(child.model_dump())
            return SyntheticTestPredictor().predict_category(child)

    request = RecommendationRequest.model_validate(payload())
    predictor = RecordingPredictor()
    result = recommend(request, predictor)
    assert len(predictor.calls) == 4  # baseline plus each of three candidates
    assert result.cards
    assert result.model_dump() == recommend(request, RecordingPredictor()).model_dump()
    assert all(card.rank == i for i, card in enumerate(result.cards, 1))


def test_no_fabricated_improvement():
    class ConstantPredictor:
        model_id = "constant-test"
        contract = synthetic_contract(model_id)
        def predict_category(self, child):
            return "higher_concern"
    result = recommend(RecommendationRequest.model_validate(payload()), ConstantPredictor())
    assert result.cards == []
    assert any("no favorable category change" in reason for c in result.rejected_or_unresolved for reason in c.reasons)


def test_unknown_mandatory_checks_and_supplement_context():
    context = FeasibilityContext.model_validate(payload()["context"])
    change = (Change(feature="meals_per_day", from_value=3, to_value=4),)
    assert check_feasibility(change, context)[0] == "feasible"
    context.clinically_suitable["meals_per_day"] = None
    assert check_feasibility(change, context)[0] == "unresolved"
    context.clinically_suitable["meals_per_day"] = True
    context.transition_justified["meals_per_day"] = None
    assert check_feasibility(change, context)[0] == "unresolved"
    context.transition_justified["meals_per_day"] = True
    context.supplement_access = None
    context.supplement_programme_eligible = None
    context.supplement_clinically_suitable = None
    assert check_feasibility(change, context)[0] == "feasible"  # supplement is unrelated to feeding change


@pytest.mark.parametrize("eligibility", [None, False, True])
def test_programme_eligibility_never_creates_supplement_candidate(eligibility):
    value = payload()
    value["context"]["supplement_access"] = True
    value["context"]["supplement_programme_eligible"] = eligibility
    value["context"]["supplement_clinically_suitable"] = None
    result = recommend(RecommendationRequest.model_validate(value))
    assert all(change.feature != "supplement_use" for card in result.cards for change in card.changes)
    assert all(change.feature != "supplement_access" for card in result.cards for change in card.changes)


def test_conflicting_feasibility_constraints():
    context = FeasibilityContext.model_validate(payload()["context"])
    context.available["meals_per_day"] = False
    context.eligible["meals_per_day"] = None
    status, reasons = check_feasibility((Change(feature="meals_per_day", from_value=3, to_value=4),), context)
    assert status == "rejected"
    assert any("available is false" in r for r in reasons)
    assert any("eligible unknown" in r for r in reasons)


def test_no_valid_counterfactual():
    value = payload()
    value["context"]["budget_units"] = 0
    result = recommend(RecommendationRequest.model_validate(value))
    assert not result.cards
    assert result.rejected_or_unresolved
    assert "No feasible" in result.message


def test_no_candidate_when_features_at_bounds():
    value = payload()
    value["child"]["meals_per_day"] = 5
    value["child"]["dietary_diversity"] = 5
    assert generate_candidates(ChildFeatures.model_validate(value["child"])) == []
    result = recommend(RecommendationRequest.model_validate(value))
    assert result.cards == []


client = TestClient(app)


def test_api_smoke_and_public_contract():
    response = client.post("/interventions/recommendations", json=payload())
    assert response.status_code == 200
    body = response.json()
    assert body["child_id"] == "SYNTHETIC-001"
    assert body["cards"]
    assert all(card["professional_review_required"] for card in body["cards"])
    assert all("predicted_category" not in card for card in body["cards"])
    assert all(change["feature"] in FIELDS for card in body["cards"] for change in card["changes"])
    assert "risk" not in json.dumps(body).lower()
    assert "%" not in json.dumps(body)
    assert client.get("/interventions/status").json()["c1_integrated"] is False


def test_api_unresolved_and_empty_smoke():
    value = payload()
    value["context"]["clinically_suitable"]["meals_per_day"] = None
    value["context"]["clinically_suitable"]["dietary_diversity"] = None
    body = client.post("/interventions/recommendations", json=value).json()
    assert body["cards"] == []
    assert any(c["status"] == "unresolved" for c in body["rejected_or_unresolved"])


@pytest.mark.parametrize("mutation", [
    lambda p: p["child"].update(age_months=-1),
    lambda p: p["child"].update(household_income_band="invalid"),
    lambda p: p["child"].update(supplement_access=True),
    lambda p: p["context"]["available"].update(supplement_access=True),
    lambda p: p.update(max_changes=3),
    lambda p: p["child"].update(meals_per_day=True),
    lambda p: p.pop("mode"),
])
def test_api_validation_errors(mutation):
    value = payload()
    mutation(value)
    assert client.post("/interventions/recommendations", json=value).status_code == 422
