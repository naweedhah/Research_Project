"""Versioned, non-predictive C2 dietary counterfactual comparison.

The original C1 assessment is immutable context. This module never imports or
calls a predictor. Published food prices are indicative Colombo references.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .guideline_references import research_guidance_for_age
from .standalone_demo import _food_plans
from .educational_baskets import SCENARIOS, SCENARIO_VARIANTS
from .evidence_registry_v2 import registry
from .face_graph import food_transition_paths
from .algorithm_demo_v2 import eligible_ids, dice_test_candidates, wachter_test_candidates
from time import perf_counter


class OriginalAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_version: str = Field(min_length=1)
    prediction_source: str = Field(min_length=1)
    predicted_malnutrition_type: Literal["Normal", "Underweight", "Stunting", "MAM", "SAM"]
    severity: Literal["Normal", "Moderate", "Severe"]
    uncertainty_flag: bool
    clinical_use: Literal[False] = False
    input_fingerprint: str = Field(min_length=1)
    provenance: Literal["live_c1_baseline", "supplied_research_assessment"]


class FeedingBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meal_frequency: Literal["2 meals/day", "3 meals/day", "4+ meals/day"]
    dietary_diversity: Literal["Less than 2 varieties", "2 to 5 varieties", "More than 5 varieties"]
    food_groups: list[str] = Field(default_factory=list, max_length=20)
    provenance: Literal["confirmed_caregiver_report", "direct_observation", "unverified"]


class HouseholdEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_lkr: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_period: Literal["daily", "weekly", "monthly"] = "weekly"
    budget_provenance: Literal["user_reported", "unknown"] = "unknown"
    allergy_status: Literal["confirmed_none", "reported", "unknown"] = "unknown"
    excluded_food_ids: list[str] = Field(default_factory=list)
    preparation: Literal["adequate_reported", "limited", "unknown"] = "unknown"
    local_availability: dict[str, bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def coherent_budget_and_allergies(self):
        if (self.budget_lkr is None) != (self.budget_provenance == "unknown"):
            raise ValueError("budget value and provenance must agree")
        if self.allergy_status == "confirmed_none" and self.excluded_food_ids:
            raise ValueError("confirmed no allergies conflicts with excluded foods")
        if self.allergy_status == "reported" and not self.excluded_food_ids:
            raise ValueError("reported restrictions require at least one excluded food ID")
        if self.allergy_status == "unknown" and self.excluded_food_ids:
            raise ValueError("unknown restrictions cannot include a confirmed exclusion")
        return self


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["c2-diet-scenarios-v2"] = "c2-diet-scenarios-v2"
    age_months: int = Field(ge=0, le=59)
    original_c1: OriginalAssessment
    feeding: FeedingBaseline
    household: HouseholdEvidence
    max_candidates: int = Field(default=5, ge=1, le=5)
    method: Literal["dice", "face_graph", "wachter", "bounded_search", "compare_all"] = "bounded_search"
    research_algorithm_demo: bool = False


def _checks(request: ScenarioRequest, plan: dict, guidance: dict) -> tuple[str, list[dict]]:
    checks = []

    def add(name: str, state: str, reason: str, evidence: str | None = None):
        checks.append({"criterion": name, "state": state, "reason": reason, "evidence_source": evidence})

    if request.age_months < 6:
        add("age_scope", "fail", "No complementary-food scenario below six months")
    else:
        add("age_scope", "pass" if request.age_months <= 23 else "unknown",
            "WHO complementary feeding guideline covers 6-23 months" if request.age_months <= 23
            else "An applicable older-child feeding practice has not been reviewed",
            "WHO-CF-2023" if request.age_months <= 23 else None)
    add("baseline_provenance", "pass" if request.feeding.provenance != "unverified" else "unknown",
        "Caregiver-confirmed or directly observed baseline" if request.feeding.provenance != "unverified"
        else "Feeding pattern has not been confirmed")
    ids = {item["food_id"] for item in plan["items"]}
    conflicting = sorted(ids & set(request.household.excluded_food_ids))
    add("allergy_restriction", "fail" if conflicting else "unknown" if request.household.allergy_status == "unknown" else "pass",
        "Excluded foods: " + ", ".join(conflicting) if conflicting else
        "Allergy and restriction status unknown" if request.household.allergy_status == "unknown" else
        "No reported conflict with listed foods")
    availability = [request.household.local_availability.get(item) for item in ids]
    add("local_availability", "fail" if False in availability else "pass" if ids and all(x is True for x in availability) else "unknown",
        "A listed food is reported unavailable" if False in availability else
        "All listed foods are reported locally available" if ids and all(x is True for x in availability) else
        "Local stock has not been confirmed")
    add("preparation", "pass" if request.household.preparation == "adequate_reported" else "unknown",
        "Household reports preparation capacity" if request.household.preparation == "adequate_reported" else
        "Preparation practicality requires review")
    fit = plan["budget_fit"]
    add("budget_reference", "unknown", "Colombo prices are indicative, not verified household purchase costs"
        + (f"; reference comparison: {fit.replace('_', ' ')}" if fit != "unknown" else ""))
    add("nutrition_adequacy", "unknown", "Food-group presence does not establish portions or nutrient adequacy",
        guidance["reference"]["url"] if guidance["reference"] else None)
    add("individual_suitability", "unknown", "No professional assessment of this food scenario")
    status = "rejected" if any(row["state"] == "fail" for row in checks) else (
        "evidence_incomplete" if any(row["state"] == "unknown" for row in checks) else "verified_feasible")
    return status, checks


def generate_scenarios(request: ScenarioRequest) -> dict:
    """Select bounded source-priced examples using reported groups and budget."""
    guidance = research_guidance_for_age(request.age_months)
    original = request.original_c1.model_dump(mode="json")
    referral = ("Seek professional nutritional assessment for the original C1 concern; "
                "this model output is not a diagnosis." if original["severity"] == "Severe"
                or original["uncertainty_flag"] or original["predicted_malnutrition_type"] != "Normal" else None)
    plans = _food_plans(request.age_months, guidance, request.household.budget_lkr,
                        request.household.budget_period, scenarios=SCENARIOS + SCENARIO_VARIANTS) if request.age_months >= 6 else []
    baseline_groups = set(request.feeding.food_groups)
    excluded = set(request.household.excluded_food_ids) | {
        food for food, available in request.household.local_availability.items() if available is False}
    # These are shopping-comparison criteria only; none estimates a health benefit.
    plans.sort(key=lambda plan: (
        bool({item["food_id"] for item in plan["items"]} & excluded),
        plan["budget_fit"] != "within_budget",
        Decimal(plan["estimated_total_lkr"]) if plan["budget_fit"] == "above_budget" and plan["estimated_total_lkr"] else Decimal("0"),
        -len(set(plan["food_groups"]) - baseline_groups),
        Decimal(plan["estimated_total_lkr"]) if plan["estimated_total_lkr"] else Decimal("Infinity"),
        plan["title"],
    ))
    plans = plans[:4]
    candidates = []
    seen = set()
    for plan in plans:
        groups = set(plan["food_groups"])
        identity = tuple(sorted(item["food_id"] for item in plan["items"]))
        if identity in seen:
            continue
        seen.add(identity)
        status, checks = _checks(request, plan, guidance)
        additions = sorted(groups - baseline_groups)
        candidates.append({"candidate_id": f"food-option-{len(candidates)+1}",
                           "title": plan["title"], "status": status,
                           "current_food_groups": sorted(baseline_groups),
                           "proposed_food_groups": sorted(groups), "additional_groups": additions,
                           "meal_frequency_change": None,
                           "dietary_diversity_change": None,
                           "reference_cost_lkr": plan["estimated_total_lkr"],
                           "cost_period": plan["cost_period"], "reference_budget_fit": plan["budget_fit"],
                           "items": plan["items"], "schedule": plan["schedule"],
                           "checks": checks, "rank": None,
                           "limitations": [plan["quantity_note"], plan["coverage_note"],
                                           "Food-group additions are not a validated nutrient or clinical benefit estimate."]})
    # Methods propose candidate IDs only. They do not assign evidence states.
    # Every proposal is checked above by the same independent validator.
    methods = [request.method] if request.method != "compare_all" else [
        "bounded_search", "dice", "face_graph", "wachter"]
    candidate_by_id = {item["candidate_id"]: item for item in candidates}
    targets = {item["candidate_id"]: frozenset(food["food_id"] for food in item["items"])
               for item in candidates}
    method_results = {}
    proposed = set()
    test_allowed = eligible_ids(candidates, request.household) if request.research_algorithm_demo else []
    for method in methods:
        begin = perf_counter()
        diagnostics = {}
        if method == "bounded_search":
            ids = list(candidate_by_id)
            status = "executed"
            diagnostics = {"enumerated": len(ids), "bound": "up to four selected source-priced examples"}
        elif method == "face_graph":
            paths = {}
            graphs = {}
            for identifier, target in targets.items():
                blocked_foods = set(request.household.excluded_food_ids) | {
                    food for food, available in request.household.local_availability.items() if available is False}
                found, detail = food_transition_paths(
                    frozenset(), {identifier: target}, frozenset(blocked_foods))
                paths.update(found)
                graphs[identifier] = detail
            ids = list(paths)
            status = "executed" if any(row["status"] == "executed" for row in graphs.values()) else "unavailable"
            diagnostics = {"paths": paths, "graphs": graphs}
        elif method == "dice":
            if request.research_algorithm_demo:
                ids, diagnostics = dice_test_candidates(candidates, test_allowed)
                status = "synthetic_software_test_only"
            else:
                ids = []
                status = "unavailable_real_nutrition_target"
                diagnostics = {"reason": "No independently validated nutrition-feasibility classifier or suitable reference dataset."}
        else:
            if request.research_algorithm_demo:
                ids, diagnostics = wachter_test_candidates(candidates, test_allowed)
                status = "synthetic_software_test_only"
            else:
                ids = []
                status = "unavailable_real_nutrition_target"
                diagnostics = {"reason": "No validated differentiable nutrition-feasibility target."}
        valid_ids = [identifier for identifier in ids if identifier in candidate_by_id]
        proposed.update(valid_ids)
        method_results[method] = {"status": status, "generated_count": len(valid_ids),
            "independently_validated_count": len(valid_ids),
            "verified_ranked_count": sum(candidate_by_id[identifier]["status"] == "verified_feasible" for identifier in valid_ids),
            "rejected_or_unresolved_count": sum(candidate_by_id[identifier]["status"] != "verified_feasible" for identifier in valid_ids),
            "runtime_ms": round((perf_counter() - begin) * 1000, 3), "diagnostics": diagnostics}
        for identifier in valid_ids:
            candidate_by_id[identifier].setdefault("generator_methods", []).append(method)
    candidates = [candidate_by_id[identifier] for identifier in candidate_by_id if identifier in proposed]
    # No source currently verifies individual portions, local costs and clinical
    # suitability. Only wholly verified candidates may enter primary ranking.
    eligible = [item for item in candidates if item["status"] == "verified_feasible"]
    eligible.sort(key=lambda item: (-len(item["additional_groups"]),
                                    Decimal(item["reference_cost_lkr"]) if item["reference_cost_lkr"] else Decimal("Infinity"),
                                    item["candidate_id"]))
    for rank, item in enumerate(eligible[:request.max_candidates], 1):
        item["rank"] = rank
    test_ranked = [item for item in candidates if item["candidate_id"] in test_allowed
                   and item["status"] != "rejected"] if request.research_algorithm_demo else []
    test_ranked.sort(key=lambda item: (len(item["items"]), Decimal(item["reference_cost_lkr"]), item["candidate_id"]))
    for rank, item in enumerate(test_ranked, 1):
        item["software_test_rank"] = rank
    return {"contract_version": request.contract_version, "original_c1": original,
            "original_c1_unchanged": True, "c1_candidate_calls": 0,
            "feeding_baseline": request.feeding.model_dump(mode="json"),
            "household": request.household.model_dump(mode="json"),
            "age_months": request.age_months, "guideline_scope": guidance,
            "evidence_registry": registry(),
            "method": request.method, "method_results": method_results,
            "software_test_ranked": [{"candidate_id": item["candidate_id"],
                "rank": item["software_test_rank"], "title": item["title"],
                "generator_methods": item.get("generator_methods", []),
                "reference_cost_lkr": item["reference_cost_lkr"],
                "scope": "engineering budget and exclusion test only; not nutritional or clinical suitability"}
                for item in test_ranked[:request.max_candidates]],
            "ranked_cards": eligible[:request.max_candidates],
            "unresolved_or_rejected": [item for item in candidates if item["rank"] is None],
            "candidate_count": len(candidates), "referral_notice": referral,
            "ranking_trace": {"status": "engineering_design_not_official_ranking_rule",
                              "order": ["verified safety and nutrition", "budget feasibility",
                                        "availability and practicality", "smaller confirmed-diet departure",
                                        "stable candidate ID"],
                              "note": "No unresolved candidate is promoted to a verified rank."},
            "clinical_use": False,
            "limitations": ["C1 is original context only; no scenario was sent to C1.",
                            "PHM feeding columns are not confirmed direct observations.",
                            "DCS prices describe Colombo markets, not verified Kalmunai prices.",
                            "Food combinations are educational examples, not prescribed child portions or guaranteed outcomes."]}
