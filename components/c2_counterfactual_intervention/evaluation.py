"""Reproducible software-method comparison on synthetic design cases only."""
import argparse
import json
from statistics import mean
from time import perf_counter

from .engine import run_pipeline
from .feature_policy import validate_changes
from .feasibility import check_feasibility
from .predictor import SyntheticSklearnPredictor
from .schemas import RecommendationRequest

# Fixed scenario cases plus a complete, deterministic 30-point feature grid.
SCENARIO_CASES = (
    (3, 3, "all"), (2, 4, "availability_constraint"), (4, 2, "unknown_suitability"),
    (1, 1, "no_target"), (2, 3, "two_feature_needed"), (3, 2, "one_feature_cap"),
    (4, 1, "limited_budget"), (3, 3, "unknown_eligibility"),
    (3, 3, "programme_eligibility_unknown"), (3, 3, "conflicting_checks"),
    (3, 3, "no_permitted_changes"), (2, 4, "tight_budget"),
    (4, 2, "practicality_constraint"), (1, 5, "ceiling_one_feature"),
    (5, 1, "ceiling_other_feature"), (3, 3, "unknown_availability"),
)
GRID_CASES = tuple((meals, diversity, "all") for meals in range(1, 6)
                   for diversity in range(0, 6)
                   if (meals, diversity, "all") not in SCENARIO_CASES)
SYNTHETIC_CASES = SCENARIO_CASES + GRID_CASES
METHODS = ("bounded_search", "dice", "face_graph")
CHECKS = ("available", "practical", "age_suitable", "eligible", "clinically_suitable", "transition_justified")


def synthetic_request(meals: int, diversity: int, method: str,
                      scenario: str = "all") -> RecommendationRequest:
    raw = {
        "child_id": f"SYNTHETIC-{meals}-{diversity}-{scenario}", "mode": "test",
        "method": method, "predictor": "synthetic_sklearn_grid_v1", "predictor_version": "1",
        "max_cards": 20,
        "child": {"age_months": 24, "sex": "female", "household_income_band": "unknown",
                  "meals_per_day": meals, "dietary_diversity": diversity},
        "context": {"budget_units": 10, "supplement_access": None,
                    "supplement_programme_eligible": None, "supplement_clinically_suitable": None,
                    **{name: {"meals_per_day": True, "dietary_diversity": True}
                       for name in CHECKS}},
    }
    context = raw["context"]
    if scenario == "availability_constraint":
        context["available"]["meals_per_day"] = False
    elif scenario == "unknown_suitability":
        context["clinically_suitable"]["dietary_diversity"] = None
    elif scenario == "one_feature_cap":
        raw["max_changes"] = 1
    elif scenario == "limited_budget":
        context["budget_units"] = 2
    elif scenario == "unknown_eligibility":
        context["eligible"] = {feature: None for feature in context["eligible"]}
    elif scenario == "programme_eligibility_unknown":
        context["supplement_access"] = True
        context["supplement_programme_eligible"] = None
    elif scenario == "conflicting_checks":
        context["available"]["meals_per_day"] = False
        context["eligible"]["meals_per_day"] = None
    elif scenario == "no_permitted_changes":
        context["transition_justified"] = {feature: False for feature in context["transition_justified"]}
    elif scenario == "tight_budget":
        context["budget_units"] = 2
    elif scenario == "practicality_constraint":
        context["practical"]["meals_per_day"] = False
    elif scenario == "unknown_availability":
        context["available"] = {feature: None for feature in context["available"]}
    elif scenario not in ("all", "no_target", "two_feature_needed", "ceiling_one_feature", "ceiling_other_feature"):
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


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate() -> dict:
    predictor = SyntheticSklearnPredictor()  # same frozen model object for all methods
    cases = []
    for meals, diversity, scenario in SYNTHETIC_CASES:
        for method in METHODS:
            request = synthetic_request(meals, diversity, method, scenario)
            start = perf_counter()
            response, generated = run_pipeline(request, predictor)
            runtime_ms = (perf_counter() - start) * 1000
            baseline = predictor.predict_category(request.child)
            target = predictor.contract.desired_category
            valid_target = 0
            feasible_target = 0
            for changes in generated:
                if validate_changes(request.child, changes):
                    continue
                child = request.child.model_validate({**request.child.model_dump(),
                                                      **{c.feature: c.to_value for c in changes}})
                if baseline == target or predictor.predict_category(child) != target:
                    continue
                valid_target += 1
                feasible_target += check_feasibility(changes, request.context)[0] == "feasible"
            cards = response.cards
            cases.append({
                "case": request.child_id, "scenario": scenario, "method": method,
                "eligible_baseline": baseline != target,
                "generated": len(generated), "valid_target": valid_target,
                "feasible_target": feasible_target, "cards": len(cards),
                "candidate_validity": _ratio(valid_target, len(generated)),
                "feasibility_pass_rate": _ratio(feasible_target, valid_target),
                "proximity": mean(_proximity(c.changes) for c in cards) if cards else None,
                "sparsity": mean(len(c.changes) for c in cards) if cards else None,
                "diversity": _diversity(cards, request),
                "rejected": sum(c.status == "rejected" for c in response.rejected_or_unresolved),
                "unresolved": sum(c.status == "unresolved" for c in response.rejected_or_unresolved),
                "no_solution": baseline != target and not cards,
                "runtime_ms": round(runtime_ms, 3),
            })
    summaries = []
    for method in METHODS:
        rows = [case for case in cases if case["method"] == method]
        generated = sum(case["generated"] for case in rows)
        valid = sum(case["valid_target"] for case in rows)
        feasible = sum(case["feasible_target"] for case in rows)
        card_count = sum(case["cards"] for case in rows)
        eligible = sum(case["eligible_baseline"] for case in rows)
        solved = sum(case["eligible_baseline"] and case["cards"] > 0 for case in rows)
        diversities = [case["diversity"] for case in rows if case["diversity"] is not None]
        summaries.append({
            "method": method, "cases": len(rows), "eligible_cases": eligible,
            "generated": generated, "valid_target": valid, "feasible_target": feasible,
            "cards": card_count, "candidate_validity": _ratio(valid, generated),
            "feasibility_pass_rate": _ratio(feasible, valid),
            "proximity": _ratio(sum(case["proximity"] * case["cards"] for case in rows if case["cards"]), card_count),
            "sparsity": _ratio(sum(case["sparsity"] * case["cards"] for case in rows if case["cards"]), card_count),
            "diversity": mean(diversities) if diversities else None,
            "diversity_case_count": len(diversities), "solved_cases": solved,
            "coverage": _ratio(solved, eligible), "no_solution_cases": eligible - solved,
            "no_solution_rate": _ratio(eligible - solved, eligible),
            "rejected": sum(case["rejected"] for case in rows),
            "unresolved": sum(case["unresolved"] for case in rows),
            "runtime_mean_ms": mean(case["runtime_ms"] for case in rows),
        })
    bounded_solved = {case["case"] for case in cases
                      if case["method"] == "bounded_search" and case["cards"]}
    for summary in summaries:
        summary["missed_bounded_solution_cases"] = sum(
            case["case"] in bounded_solved and not case["cards"] for case in cases
            if case["method"] == summary["method"])
    return {"synthetic_only": True, "predictor": predictor.contract.model_id,
            "predictor_version": predictor.contract.model_version,
            "dice_seed": 17, "grid_points": 30,
            "scenario_case_count": len(SCENARIO_CASES), "grid_case_count": len(GRID_CASES),
            "case_count": len(SYNTHETIC_CASES), "cases": cases, "summary": summaries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic-only C2 method comparison")
    parser.add_argument("--summary", action="store_true", help="omit per-case rows")
    args = parser.parse_args()
    report = evaluate()
    if args.summary:
        report.pop("cases")
    print(json.dumps(report, indent=2))
