"""Phase 2 tests use only explicit synthetic design points and test predictors."""
from importlib.metadata import version

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention.dice_method import generate_dice_candidates
from components.c2_counterfactual_intervention.engine import generate_method_candidates, recommend
from components.c2_counterfactual_intervention.evaluation import METHODS, SYNTHETIC_CASES, evaluate, synthetic_request
from components.c2_counterfactual_intervention.face_graph import build_reference_graph, generate_face_paths
from components.c2_counterfactual_intervention.feature_policy import ACTIONABLE, validate_changes
from components.c2_counterfactual_intervention.predictor import SyntheticSklearnPredictor
from components.c2_counterfactual_intervention.schemas import RecommendationRequest
from components.c2_counterfactual_intervention.synthetic_data import synthetic_reference_points


@pytest.fixture(scope="module")
def predictor():
    return SyntheticSklearnPredictor()


def test_official_dice_dependency_and_execution(predictor):
    assert version("dice-ml") == "0.12"
    request = synthetic_request(3, 3, "dice")
    candidates = generate_dice_candidates(request.child, predictor, 2)
    assert candidates
    assert len(candidates) >= 2  # diverse valid endpoints
    assert all(not validate_changes(request.child, group) for group in candidates)
    assert all(change.feature in ACTIONABLE for group in candidates for change in group)
    assert candidates == generate_dice_candidates(request.child, predictor, 2)


def test_method_dispatch_is_distinct(monkeypatch, predictor):
    from components.c2_counterfactual_intervention import engine
    called = []
    original_dice = engine.generate_dice_candidates
    original_face = engine.generate_face_candidates
    def dice(*args, **kwargs):
        called.append("dice")
        return original_dice(*args, **kwargs)
    def face(*args, **kwargs):
        called.append("face_graph")
        return original_face(*args, **kwargs)
    monkeypatch.setattr(engine, "generate_dice_candidates", dice)
    monkeypatch.setattr(engine, "generate_face_candidates", face)
    assert generate_method_candidates(synthetic_request(3, 3, "bounded_search"), predictor)
    assert called == []
    assert generate_method_candidates(synthetic_request(3, 3, "dice"), predictor)
    assert generate_method_candidates(synthetic_request(3, 3, "face_graph"), predictor)
    assert called == ["dice", "face_graph"]


def test_dice_failure_does_not_fall_back(monkeypatch, predictor):
    from components.c2_counterfactual_intervention import engine
    def fail(*args, **kwargs):
        raise RuntimeError("DiCE execution failed")
    monkeypatch.setattr(engine, "generate_dice_candidates", fail)
    with pytest.raises(RuntimeError, match="DiCE execution failed"):
        recommend(synthetic_request(3, 3, "dice"), predictor)


def test_graph_construction_and_paths(predictor):
    reference = synthetic_reference_points()
    graph = build_reference_graph(reference)
    assert len(graph) == 30
    assert all(v[0] >= u[0] and v[1] >= u[1] and sum(b - a for a, b in zip(u, v)) == 1
               for u, edges in graph.items() for v, weight in edges)
    assert all(weight > 0 for edges in graph.values() for _, weight in edges)
    request = synthetic_request(3, 3, "face_graph")
    paths = generate_face_paths(request.child, request.context, predictor, 2)
    assert paths
    for item in paths:
        assert len(item.path) - 1 <= 2
        assert all(next_node in [v for v, _ in graph[node]]
                   for node, next_node in zip(item.path, item.path[1:]))
        assert not validate_changes(request.child, item.changes)


def test_no_feasible_graph_path_and_unknown_safety(predictor):
    request = synthetic_request(3, 3, "face_graph")
    assert generate_face_paths(request.child, request.context, predictor, 2,
                               reference=((3, 3), (5, 5))) == []
    request.context.clinically_suitable["meals_per_day"] = None
    request.context.clinically_suitable["dietary_diversity"] = None
    assert generate_face_paths(request.child, request.context, predictor, 2) == []
    assert not recommend(request, predictor).cards


def test_immutable_context_and_dedup_across_methods(predictor):
    for method in METHODS:
        request = synthetic_request(3, 3, method)
        candidates = generate_method_candidates(request, predictor)
        keys = [tuple((c.feature, c.to_value) for c in group) for group in candidates]
        assert len(keys) == len(set(keys))
        for group in candidates:
            assert all(c.feature in ACTIONABLE for c in group)
            changed = request.child.model_validate({**request.child.model_dump(),
                                                    **{c.feature: c.to_value for c in group}})
            for field in ("age_months", "sex", "household_income_band", "birth_weight_kg",
                          "historical_exclusive_breastfeeding", "supplement_use"):
                assert getattr(changed, field) == getattr(request.child, field)


def test_no_predictor_supported_improvement(predictor):
    for method in METHODS:
        result = recommend(synthetic_request(1, 1, method), predictor)
        assert result.cards == []


def test_equal_evaluation_conditions_and_actual_metrics():
    for meals, diversity, scenario in SYNTHETIC_CASES:
        requests = [synthetic_request(meals, diversity, m, scenario) for m in METHODS]
        assert all(r.child == requests[0].child and r.context == requests[0].context for r in requests)
        assert all(r.predictor == "synthetic_sklearn_grid_v1" for r in requests)
    report = evaluate()
    assert len(report["cases"]) == len(SYNTHETIC_CASES) * 3
    assert all(c["runtime_ms"] >= 0 for c in report["cases"])
    assert any(c["no_solution"] for c in report["cases"])


def test_api_method_smoke_and_backward_compatibility():
    client = TestClient(app)
    for method in METHODS:
        request = synthetic_request(3, 3, method).model_dump()
        response = client.post("/interventions/recommendations", json=request)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == method
        assert body["cards"]
        assert all("predicted_category" not in card for card in body["cards"])
        assert all("%" not in str(card) and "risk" not in str(card).lower() for card in body["cards"])
    old_request = synthetic_request(3, 3, "bounded_search").model_dump(exclude={"method", "predictor"})
    assert client.post("/interventions/recommendations", json=old_request).json()["method"] == "bounded_search"
    invalid = synthetic_request(3, 3, "dice").model_dump()
    invalid["predictor"] = "synthetic_test_v1"
    assert client.post("/interventions/recommendations", json=invalid).status_code == 422
