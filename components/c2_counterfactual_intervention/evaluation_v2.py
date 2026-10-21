"""Reproducible, invented-input software evaluation for C2 diet scenarios v2."""
from copy import deepcopy
import json
from decimal import Decimal
from time import perf_counter

from .nutrition_scenarios_v2 import ScenarioRequest, generate_scenarios


def fixture() -> ScenarioRequest:
    return ScenarioRequest.model_validate({
        "age_months": 24,
        "original_c1": {"model_version": "GA-RGCA-v3", "prediction_source": "GA-RGCA-v3",
                        "predicted_malnutrition_type": "Stunting", "severity": "Moderate",
                        "uncertainty_flag": False, "clinical_use": False,
                        "input_fingerprint": "INVENTED-EVALUATION-ONLY",
                        "provenance": "supplied_research_assessment"},
        "feeding": {"meal_frequency": "3 meals/day", "dietary_diversity": "2 to 5 varieties",
                    "food_groups": ["rice and cereals"], "provenance": "unverified"},
        "household": {"budget_lkr": "1500", "budget_period": "weekly",
                      "budget_provenance": "user_reported", "allergy_status": "unknown",
                      "preparation": "unknown", "local_availability": {}},
    })


def evaluate() -> dict:
    request = fixture()
    start = perf_counter()
    result = generate_scenarios(request)
    duration_ms = round((perf_counter() - start) * 1000, 3)
    repeated = generate_scenarios(deepcopy(request))
    candidates = result["ranked_cards"] + result["unresolved_or_rejected"]
    changed = request.model_copy(deep=True)
    changed.household.budget_lkr = Decimal("100")
    low_budget = generate_scenarios(changed)
    restriction = request.model_copy(deep=True)
    restriction.household.allergy_status = "reported"
    restriction.household.excluded_food_ids = ["egg_average"]
    excluded = generate_scenarios(restriction)
    def decisions_only(value):
        copy = deepcopy(value)
        for method in copy["method_results"].values():
            method.pop("runtime_ms", None)
        return copy

    comparison = request.model_copy(update={"method": "compare_all"})
    all_methods = generate_scenarios(comparison)
    return {
        "contract_version": result["contract_version"], "fixture_provenance": "invented software evaluation",
        "candidate_count": result["candidate_count"],
        "candidate_diversity": len({tuple(sorted(x["proposed_food_groups"])) for x in candidates}),
        "verified_ranked": len(result["ranked_cards"]),
        "unresolved_or_rejected": len(result["unresolved_or_rejected"]),
        "hard_rule_compliance": all(x["rank"] is None or x["status"] == "verified_feasible" for x in candidates),
        "evidence_check_count": sum(len(x["checks"]) for x in candidates),
        "unknown_check_count": sum(check["state"] == "unknown" for x in candidates for check in x["checks"]),
        "priced_candidate_count": sum(x["reference_cost_lkr"] is not None for x in candidates),
        "local_cost_verified_count": 0,
        "allergy_exclusion_rejected_count": sum(x["status"] == "rejected" for x in excluded["unresolved_or_rejected"]),
        "budget_changes_original_c1": low_budget["original_c1"] != result["original_c1"],
        "budget_changes_reference_fit": any(
            a["reference_budget_fit"] != b["reference_budget_fit"]
            for a, b in zip(result["unresolved_or_rejected"], low_budget["unresolved_or_rejected"])),
        "same_input_deterministic": decisions_only(result) == decisions_only(repeated),
        "c1_candidate_calls": result["c1_candidate_calls"],
        "method_results": all_methods["method_results"],
        "deduplicated_compare_all_count": all_methods["candidate_count"],
        "response_time_ms_one_run": duration_ms,
        "rank_order_sensitivity": "not measurable: zero fully verified eligible candidates",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
