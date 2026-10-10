"""Final contract and safety regressions; labels and observations are test fixtures."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention.contracts import (
    LabelTransition, ModelPrediction, PredictorCompatibilityError, PredictorContract,
    SYNTHETIC_FEATURES, TargetContract,
)
from components.c2_counterfactual_intervention.engine import (
    generate_method_candidates, recommend,
)
from components.c2_counterfactual_intervention.schemas import Change
from components.c2_counterfactual_intervention.demonstrations import demonstrate
from components.c2_counterfactual_intervention.evaluation import evaluate, synthetic_request
from components.c2_counterfactual_intervention.face_graph import generate_face_paths
from components.c2_counterfactual_intervention.predictor import SyntheticSklearnPredictor
from components.c2_counterfactual_intervention.schemas import RecommendationRequest
from components.c2_counterfactual_intervention.tests.test_food_planning import planning_request


TYPES = (TargetContract(code="type_a", definition="fixture type A"),
         TargetContract(code="type_b", definition="fixture type B"))
SEVERITIES = (TargetContract(code="level_0", definition="fixture lower severity"),
              TargetContract(code="level_1", definition="fixture middle severity"),
              TargetContract(code="level_2", definition="fixture higher severity"))


def dual_contract(*, transitions=(LabelTransition(from_label="type_a", to_label="type_b"),)):
    return PredictorContract(interface_version="c2-predictor-v2", output_mode="type_severity",
                             model_id="two-output-fixture", model_version="1", mode="real",
                             features=SYNTHETIC_FEATURES, type_targets=TYPES,
                             severity_targets=SEVERITIES,
                             accepted_type_transitions=transitions,
                             severity_order=("level_0", "level_1", "level_2"),
                             artifact_id="fixture-artifact", artifact_sha256="a" * 64,
                             reference_data_id="fixture-grid")


class DualPredictor:
    contract = dual_contract()

    def predict_outcomes(self, child):
        if child.meals_per_day >= 4 and child.dietary_diversity >= 4:
            return ModelPrediction(type_label="type_b", severity_label="level_0")
        if child.meals_per_day >= 4:
            return ModelPrediction(type_label="type_b", severity_label="level_2")
        if child.dietary_diversity >= 4:
            return ModelPrediction(type_label="type_b", severity_label="level_1")
        return ModelPrediction(type_label="type_a", severity_label="level_1")

    def reference_points(self):
        from components.c2_counterfactual_intervention.synthetic_data import synthetic_reference_points
        return synthetic_reference_points()


def dual_request(method="bounded_search"):
    raw = synthetic_request(3, 3, method).model_dump(mode="json")
    raw.update(mode="real", predictor="two-output-fixture", predictor_version="1")
    return RecommendationRequest.model_validate(raw)


@pytest.mark.parametrize("method", ["bounded_search", "face_graph"])
def test_two_output_rejects_severity_worsening_and_accepts_safe_progress(method):
    response = recommend(dual_request(method), DualPredictor())
    assert response.condition_category == "type_a"
    assert response.condition_severity == "level_1"
    assert response.cards
    assert all(not (len(card.changes) == 1 and card.changes[0].feature == "meals_per_day")
               for card in response.cards)
    if method == "bounded_search":
        assert any("severity worsens" in reason for item in response.rejected_or_unresolved
                   for reason in item.reasons)
    assert all(card.professional_review_required for card in response.cards)


def test_unapproved_type_change_and_no_progress_are_rejected():
    class NoTypeChange(DualPredictor):
        contract = dual_contract(transitions=())
    response = recommend(dual_request(), NoTypeChange())
    assert not response.cards
    assert any("not approved" in reason for item in response.rejected_or_unresolved for reason in item.reasons)

    class Constant(DualPredictor):
        def predict_outcomes(self, child):
            return ModelPrediction(type_label="type_a", severity_label="level_1")
    response = recommend(dual_request(), Constant())
    assert not response.cards
    assert any("no approved" in reason for item in response.rejected_or_unresolved for reason in item.reasons)


def test_severity_only_progress_and_internal_probabilities():
    class SeverityOnly(DualPredictor):
        contract = dual_contract(transitions=())

        def predict_outcomes(self, child):
            severity = "level_0" if child.meals_per_day >= 4 else "level_1"
            return ModelPrediction(type_label="type_a", severity_label=severity,
                                   type_probabilities={"type_a": 0.8, "type_b": 0.2},
                                   severity_probabilities={"level_0": 0.2,
                                                           "level_1": 0.7, "level_2": 0.1})

    response = recommend(dual_request(), SeverityOnly())
    assert response.cards
    assert all("category change" not in card.explanation for card in response.cards)
    assert all("probabilit" not in str(card.model_dump()).lower() for card in response.cards)


def test_missing_and_undeclared_outputs_fail_safely():
    class MissingCandidate(DualPredictor):
        def predict_outcomes(self, child):
            if child.meals_per_day == 3 and child.dietary_diversity == 3:
                return super().predict_outcomes(child)
            return {"type_label": "type_b"}
    response = recommend(dual_request(), MissingCandidate())
    assert not response.cards
    assert all(item.status == "unresolved" for item in response.rejected_or_unresolved)

    class BadBaseline(DualPredictor):
        def predict_outcomes(self, child):
            return {"type_label": "unknown", "severity_label": "level_1"}
    with pytest.raises(PredictorCompatibilityError, match="undeclared type"):
        recommend(dual_request(), BadBaseline())
    invalid = dual_contract().model_dump()
    invalid["severity_order"] = ("level_0",)
    with pytest.raises(ValueError, match="severity order"):
        PredictorContract.model_validate(invalid)


def test_two_output_dice_uses_existing_synthetic_test_model_only():
    class JointDiceAdapter(DualPredictor):
        def __init__(self):
            self.synthetic = SyntheticSklearnPredictor()
            self.dice_model = self.synthetic.dice_model
            self.dice_outcome_name = self.synthetic.dice_outcome_name
            self.dice_target_label = 1

        def dice_reference_data(self):
            return self.synthetic.dice_reference_data()

        def dice_query(self, child):
            return self.synthetic.dice_query(child)

        def dice_prediction(self, label):
            return ModelPrediction(type_label="type_b", severity_label="level_0") if int(label) == 1 else ModelPrediction(type_label="type_a", severity_label="level_1")

        def predict_outcomes(self, child):
            import pandas as pd
            label = self.dice_model.predict(pd.DataFrame([self.dice_query(child)]))[0]
            return self.dice_prediction(label)

    response = recommend(dual_request("dice"), JointDiceAdapter())
    assert response.cards
    assert all(card.professional_review_required for card in response.cards)


def test_food_evidence_conflicts_and_units_remain_nonfeasible():
    raw = planning_request()
    raw["food_planning"]["catalog"][0]["locally_available"] = False
    response = recommend(RecommendationRequest.model_validate(raw))
    assert not response.cards
    assert any("locally unavailable" in reason for item in response.rejected_or_unresolved for reason in item.reasons)
    raw = planning_request()
    raw["food_planning"]["catalog"][0]["availability_evidence"] = None
    response = recommend(RecommendationRequest.model_validate(raw))
    assert not response.cards
    assert any("availability: evidence missing" in reason for item in response.rejected_or_unresolved for reason in item.reasons)
    raw = planning_request()
    raw["food_planning"]["alternatives"][0]["programme_required"] = True
    raw["food_planning"]["alternatives"][0]["programme_eligible"] = True
    response = recommend(RecommendationRequest.model_validate(raw))
    assert not response.cards
    assert any("programme eligibility: evidence missing" in reason
               for item in response.rejected_or_unresolved for reason in item.reasons)


def test_real_api_missing_predictor_and_no_probability_claims():
    client = TestClient(app)
    response = client.post("/interventions/recommendations", json=dual_request().model_dump(mode="json"))
    assert response.status_code == 503
    test_response = client.post("/interventions/recommendations", json=planning_request())
    assert test_response.status_code == 200
    cards = test_response.json()["cards"]
    assert cards and all("probabilit" not in str(card).lower() and "risk" not in str(card).lower()
                         for card in cards)


def test_six_reproducible_demonstrations():
    first = demonstrate()
    assert first == demonstrate()
    assert first["synthetic_test_only"] and not first["clinical_validation"]
    scenarios = first["scenarios"]
    assert len(scenarios["A_success"]["cards"]) == 1
    assert scenarios["B_unaffordable"]["other"][0]["status"] == "rejected"
    assert scenarios["C_unavailable"]["other"][0]["status"] == "rejected"
    assert scenarios["D_unknown_clinical"]["other"][0]["status"] == "unresolved"
    assert scenarios["E_no_model_supported"]["cards"] == []
    assert "no registered C1 predictor" in scenarios["F_real_model_missing"]["error"]


def test_real_graph_cannot_fall_back_to_synthetic_reference():
    class MissingReference(DualPredictor):
        def reference_points(self):
            return None
    with pytest.raises(PredictorCompatibilityError, match="reference data unavailable"):
        recommend(dual_request("face_graph"), MissingReference())
    request = dual_request("face_graph")
    with pytest.raises(PredictorCompatibilityError, match="reference data unavailable"):
        generate_face_paths(request.child, request.context, MissingReference(), 2)


def test_duplicate_candidates_removed_without_masking_invalid_transition(monkeypatch):
    from components.c2_counterfactual_intervention import engine
    request = synthetic_request(3, 3, "bounded_search")
    bad = (Change(feature="meals_per_day", from_value=2, to_value=4),)
    good = (Change(feature="meals_per_day", from_value=3, to_value=4),)
    monkeypatch.setattr(engine, "generate_candidates", lambda child, limit: [bad, good, good])
    candidates = generate_method_candidates(request, SyntheticSklearnPredictor())
    assert candidates == [bad, good]
    response = recommend(request)
    assert any(card.changes == list(good) for card in response.cards)
    assert any("invalid transition" in reason for item in response.rejected_or_unresolved
               for reason in item.reasons)


def test_invalid_food_values_and_future_evidence_fail_closed():
    raw = planning_request()
    raw["food_planning"]["alternatives"][0]["foods"][0]["quantity"] = "0"
    with pytest.raises(ValueError, match="greater than 0"):
        RecommendationRequest.model_validate(raw)
    raw = planning_request()
    raw["food_planning"]["catalog"][0]["price"]["evidence"]["observed_on"] = "2999-01-01"
    response = recommend(RecommendationRequest.model_validate(raw))
    assert not response.cards
    assert any("future" in reason for item in response.rejected_or_unresolved for reason in item.reasons)


def test_dice_returns_no_candidate_when_already_in_target_class():
    request = synthetic_request(5, 5, "dice")
    response = recommend(request)
    assert response.cards == []


def test_expanded_method_comparison_has_consistent_denominators():
    report = evaluate()
    assert report["synthetic_only"] and report["dice_seed"] == 17
    assert report["case_count"] == report["scenario_case_count"] + report["grid_case_count"] == 45
    assert len(report["cases"]) == 45 * 3
    summaries = {row["method"]: row for row in report["summary"]}
    assert set(summaries) == {"bounded_search", "dice", "face_graph"}
    for summary in summaries.values():
        assert summary["cases"] == 45
        assert summary["valid_target"] <= summary["generated"]
        assert summary["feasible_target"] <= summary["valid_target"]
        assert summary["solved_cases"] + summary["no_solution_cases"] == summary["eligible_cases"]
        assert summary["runtime_mean_ms"] >= 0
    assert summaries["face_graph"]["generated"] <= summaries["bounded_search"]["generated"]
