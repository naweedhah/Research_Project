"""Phase 3 safety and scientific-regression tests; all data are synthetic fixtures."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention.contracts import (
    FeatureContract, PredictorCompatibilityError, PredictorContract, SYNTHETIC_FEATURES, TargetContract,
)
from components.c2_counterfactual_intervention.dice_method import generate_dice_candidates
from components.c2_counterfactual_intervention.engine import MissingRealPredictorError, recommend, resolve_predictor
from components.c2_counterfactual_intervention.evaluation import METHODS, SYNTHETIC_CASES, evaluate, synthetic_request
from components.c2_counterfactual_intervention.face_graph import bounded_reachable_paths, generate_face_paths
from components.c2_counterfactual_intervention.predictor import SyntheticSklearnPredictor, SyntheticTestPredictor
from components.c2_counterfactual_intervention.registry import register_real_predictor
from components.c2_counterfactual_intervention.schemas import RecommendationRequest


class MockC1Predictor:
    """Contract fixture for tests; never a registered or clinically validated C1 model."""
    contract = PredictorContract(
        model_id="mock-c1-contract-test", model_version="fixture-1", mode="real",
        features=SYNTHETIC_FEATURES,
        targets=(TargetContract(code="fixture_a", definition="test category A"),
                 TargetContract(code="fixture_b", definition="test category B")),
        desired_category="fixture_b", artifact_id="test-artifact",
        artifact_sha256="a" * 64, reference_data_id="test-grid")

    def predict_category(self, child):
        return "fixture_b" if child.meals_per_day + child.dietary_diversity >= 7 else "fixture_a"

    def reference_points(self):
        from components.c2_counterfactual_intervention.synthetic_data import synthetic_reference_points
        return synthetic_reference_points()


def real_request(method="bounded_search"):
    raw = synthetic_request(3, 3, method).model_dump()
    raw.update(mode="real", predictor="mock-c1-contract-test", predictor_version="fixture-1")
    return RecommendationRequest.model_validate(raw)


def test_real_mode_requires_explicit_compatible_predictor():
    request = real_request()
    with pytest.raises(MissingRealPredictorError):
        recommend(request)
    with pytest.raises(PredictorCompatibilityError, match="mode"):
        recommend(request, SyntheticTestPredictor())
    response = recommend(request, MockC1Predictor())
    assert response.condition_category == "fixture_a"
    assert response.cards
    assert response.mode == "real"
    assert all("treatment effect" in card.explanation for card in response.cards)


def test_contract_id_version_features_and_targets():
    request = real_request()
    raw = request.model_dump()
    raw["predictor_version"] = "wrong"
    with pytest.raises(PredictorCompatibilityError, match="version"):
        recommend(RecommendationRequest.model_validate(raw), MockC1Predictor())
    raw = request.model_dump()
    raw["predictor"] = "wrong-model"
    with pytest.raises(PredictorCompatibilityError, match="ID"):
        recommend(RecommendationRequest.model_validate(raw), MockC1Predictor())
    with pytest.raises(ValueError, match="artifact"):
        PredictorContract(model_id="incomplete", model_version="1", mode="real",
                          features=SYNTHETIC_FEATURES, targets=MockC1Predictor.contract.targets,
                          desired_category="fixture_b")
    with pytest.raises(ValueError, match="desired_category"):
        PredictorContract(model_id="bad-target", model_version="1", mode="test",
                          features=SYNTHETIC_FEATURES, targets=MockC1Predictor.contract.targets,
                          desired_category="nonexistent")
    with pytest.raises(ValueError, match="64 hexadecimal"):
        PredictorContract(model_id="bad-hash", model_version="1", mode="real",
                          features=SYNTHETIC_FEATURES, targets=MockC1Predictor.contract.targets,
                          desired_category="fixture_b", artifact_id="artifact", artifact_sha256="not-a-hash")


def test_contract_requires_mappable_feature_names():
    class UnmappedPredictor(MockC1Predictor):
        contract = PredictorContract(
            model_id="mock-c1-contract-test", model_version="fixture-1", mode="real",
            features=(FeatureContract(name="unknown", source_field="nonexistent_field",
                                      dtype="integer", preprocessing="identity",
                                      missing_value_policy="reject"),),
            targets=MockC1Predictor.contract.targets, desired_category="fixture_b",
            artifact_id="test-artifact", artifact_sha256="a" * 64)
    with pytest.raises(PredictorCompatibilityError, match="unmapped"):
        recommend(real_request(), UnmappedPredictor())


def test_real_mode_rejects_synthetic_id_and_test_mode_rejects_real_id():
    raw = synthetic_request(3, 3, "bounded_search").model_dump()
    raw.update(mode="real", predictor="synthetic_test_v1", predictor_version="1")
    with pytest.raises(ValueError, match="synthetic"):
        RecommendationRequest.model_validate(raw)
    raw.update(mode="test", predictor="mock-c1-contract-test")
    with pytest.raises(ValueError, match="registered synthetic"):
        RecommendationRequest.model_validate(raw)
    with pytest.raises(PredictorCompatibilityError, match="mode"):
        resolve_predictor(synthetic_request(3, 3, "bounded_search"), MockC1Predictor())
    with pytest.raises(PredictorCompatibilityError, match="only a contracted real"):
        register_real_predictor(SyntheticTestPredictor())


def test_registration_does_not_imply_verified_c1_integration(monkeypatch):
    from components.c2_counterfactual_intervention import registry
    monkeypatch.setattr(registry, "_real_predictor", None)
    monkeypatch.setattr(registry, "_c1_integration_verified", False)
    registry.register_real_predictor(MockC1Predictor())
    assert registry.get_real_predictor() is not None
    assert registry.c1_integration_verified() is False
    registry.register_real_predictor(MockC1Predictor(), integration_verified=True)
    assert registry.c1_integration_verified() is True


def test_dice_generation_and_validation_model_must_agree():
    class InconsistentAdapter(SyntheticSklearnPredictor):
        def predict_category(self, child):
            return "lower_concern"  # disagrees with its own sklearn model at baseline
    request = synthetic_request(3, 3, "dice")
    with pytest.raises(PredictorCompatibilityError, match="disagree"):
        generate_dice_candidates(request.child, InconsistentAdapter(), 2)
    class BadReferenceLabels(SyntheticSklearnPredictor):
        def dice_reference_data(self):
            frame = super().dice_reference_data()
            frame.loc[0, "outcome"] = 1 - frame.loc[0, "outcome"]
            return frame
    with pytest.raises(PredictorCompatibilityError, match="reference labels"):
        generate_dice_candidates(request.child, BadReferenceLabels(), 2)
    adapter = SyntheticSklearnPredictor()
    candidates = generate_dice_candidates(request.child, adapter, 2)
    for changes in candidates:
        child = request.child.model_validate({**request.child.model_dump(),
                                              **{c.feature: c.to_value for c in changes}})
        assert adapter.predict_category(child) == adapter.contract.desired_category
        for name in ("age_months", "sex", "household_income_band", "supplement_use"):
            assert getattr(child, name) == getattr(request.child, name)


def test_bounded_dijkstra_retains_remaining_step_budget():
    start, via, joint, target = (0, 0), (1, 0), (2, 0), (3, 0)
    graph = {start: ((via, 1.0), (joint, 5.0)), via: ((joint, 1.0),),
             joint: ((target, 1.0),), target: ()}
    paths = bounded_reachable_paths(graph, start, 2, lambda path, neighbor: True)
    assert any(path == (start, joint, target) for _, path in paths)
    assert not any(path == (start, via, joint, target) for _, path in paths)


def test_graph_checks_cumulative_budget_and_unknowns():
    predictor = SyntheticSklearnPredictor()
    request = synthetic_request(2, 3, "face_graph", "two_feature_needed")
    assert generate_face_paths(request.child, request.context, predictor, 2)
    request.context.budget_units = 3  # each step fits, combined cost 5 does not
    assert generate_face_paths(request.child, request.context, predictor, 2) == []
    request.context.budget_units = 10
    request.context.eligible["meals_per_day"] = None
    assert generate_face_paths(request.child, request.context, predictor, 2) == []


def test_evaluation_denominators_and_reproducibility():
    first, second = evaluate(), evaluate()
    assert first["case_count"] == len(SYNTHETIC_CASES) > 4
    for left, right in zip(first["cases"], second["cases"]):
        assert {k: v for k, v in left.items() if k != "runtime_ms"} == {
            k: v for k, v in right.items() if k != "runtime_ms"}
    for summary in first["summary"]:
        rows = [row for row in first["cases"] if row["method"] == summary["method"]]
        assert summary["generated"] == sum(row["generated"] for row in rows)
        assert summary["valid_target"] == sum(row["valid_target"] for row in rows)
        assert summary["feasible_target"] == sum(row["feasible_target"] for row in rows)
        assert summary["coverage"] == summary["solved_cases"] / summary["eligible_cases"]
        if summary["generated"]:
            assert summary["candidate_validity"] == summary["valid_target"] / summary["generated"]
        assert summary["rejected"] == sum(row["rejected"] for row in rows)
        assert summary["unresolved"] == sum(row["unresolved"] for row in rows)
    assert {row["method"] for row in first["cases"]} == set(METHODS)


def test_safe_api_errors_and_public_card_contract(monkeypatch):
    client = TestClient(app)
    test_request = synthetic_request(3, 3, "bounded_search").model_dump()
    missing_mode = dict(test_request)
    del missing_mode["mode"]
    assert client.post("/interventions/recommendations", json=missing_mode).status_code == 422
    real = real_request().model_dump()
    missing = client.post("/interventions/recommendations", json=real)
    assert missing.status_code == 503 and "no registered C1 predictor" in missing.json()["detail"]
    from app.routers import interventions
    monkeypatch.setattr(interventions, "get_real_predictor", lambda: MockC1Predictor())
    response = client.post("/interventions/recommendations", json=real)
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "real" and body["cards"]
    assert body["condition_category"] == "fixture_a"
    assert all("%" not in json.dumps(card) and "risk" not in json.dumps(card).lower()
               for card in body["cards"])
    assert all("predicted_category" not in card for card in body["cards"])
    status = client.get("/interventions/status").json()
    assert status["real_model_registered"] is True
    assert status["c1_integrated"] is False
    assert status["clinical_ready"] is False
