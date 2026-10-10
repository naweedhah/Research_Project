"""Reproducible software-method comparison on synthetic design cases only."""
import json
from statistics import mean
from time import perf_counter

from .engine import run_pipeline
from .feature_policy import validate_changes
from .feasibility import check_feasibility
from .predictor import SyntheticSklearnPredictor
from .schemas import RecommendationRequest

SYNTHETIC_CASES = ((3, 3, "all"), (2, 4, "availability_constraint"),
                   (4, 2, "unknown_suitability"), (1, 1, "no_target"))
METHODS = ("bounded_search", "dice", "face_graph")
CHECKS = ("available", "practical", "age_suitable", "eligible", "clinically_suitable", "transition_justified")


def synthetic_request(meals: int, diversity: int, method: str,
                      scenario: str = "all") -> RecommendationRequest:
    raw = {
        "child_id": f"SYNTHETIC-{meals}-{diversity}", "method": method,
        "predictor": "synthetic_sklearn_grid_v1", "max_cards": 20,
        "child": {"age_months": 24, "sex": "female", "household_income_band": "unknown",
                  "meals_per_day": meals, "dietary_diversity": diversity},
        "context": {"budget_units": 10, **{name: {"meals_per_day": True, "dietary_diversity": True}
                                         for name in CHECKS}},
    }
    if scenario == "availability_constraint":
        raw["context"]["available"]["meals_per_day"] = False
    elif scenario == "unknown_suitability":
        raw["context"]["clinically_suitable"]["dietary_diversity"] = None
    elif scenario not in ("all", "no_target"):
        raise ValueError(f"unknown synthetic scenario: {scenario}")
    return RecommendationRequest.model_validate(raw)


def _proximity(changes) -> float:
    return sum(abs(c.to_value - c.from_value) / (4 if c.feature == "meals_per_day" else 5)
               for c in changes) / 2


def _diversity(cards, request) -> float | None:
    if not cards:
        return None
    if len(cards) == 1:
        return 0.0
    endpoints = [{**{"meals_per_day": request.child.meals_per_day,
                     "dietary_diversity": request.child.dietary_diversity},
                  **{c.feature: c.to_value for c in card.changes}} for card in cards]
    distances = []
    for i, left in enumerate(endpoints):
        for right in endpoints[i + 1:]:
            distances.append((abs(left["meals_per_day"] - right["meals_per_day"]) / 4 +
                              abs(left["dietary_diversity"] - right["dietary_diversity"]) / 5) / 2)
    return mean(distances)


def evaluate() -> dict:
    predictor = SyntheticSklearnPredictor()  # one frozen compatible model for all methods
    cases = []
    for meals, diversity, scenario in SYNTHETIC_CASES:
        for method in METHODS:
            request = synthetic_request(meals, diversity, method, scenario)
            start = perf_counter()
            response, generated = run_pipeline(request, predictor)
            runtime_ms = (perf_counter() - start) * 1000
            baseline = predictor.predict_category(request.child)
            valid_target = 0
            feasible_target = 0
            for changes in generated:
                if validate_changes(request.child, changes):
                    continue
                child = request.child.model_validate({**request.child.model_dump(),
                                                      **{c.feature: c.to_value for c in changes}})
                if baseline != "higher_concern" or predictor.predict_category(child) != "lower_concern":
                    continue
                valid_target += 1
                feasible_target += check_feasibility(changes, request.context)[0] == "feasible"
            cards = response.cards
            cases.append({
                "case": request.child_id, "scenario": scenario, "method": method,
                "generated": len(generated),
                "cards": len(cards), "candidate_validity": valid_target / len(generated) if generated else None,
                "feasibility_pass_rate": feasible_target / valid_target if valid_target else None,
                "proximity": mean(_proximity(c.changes) for c in cards) if cards else None,
                "sparsity": mean(len(c.changes) for c in cards) if cards else None,
                "diversity": _diversity(cards, request),
                "rejected": sum(c.status == "rejected" for c in response.rejected_or_unresolved),
                "unresolved": sum(c.status == "unresolved" for c in response.rejected_or_unresolved),
                "no_solution": not cards, "runtime_ms": round(runtime_ms, 3),
            })
    return {"synthetic_only": True, "predictor": predictor.model_id, "cases": cases}


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
