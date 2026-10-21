"""Offline C2 supervisor workflow using only the existing synthetic research fixture.

The method results prove software-path behavior under synthetic assertions. Shopping
examples and schedules are educational pricing scenarios, not feasibility evidence.
"""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Literal
from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field

from .c1_engine import C1Request, run_c1
from .educational_baskets import shopping_examples
from .guideline_references import research_guidance_for_age
from .real_model_validation import standalone_input_fingerprint, standalone_snapshot
from .supervisor_demo import demo_request


class StandaloneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: Literal["synthetic_5m", "synthetic_24m", "synthetic_59m"] = "synthetic_24m"
    budget_lkr: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_period: Literal["daily", "weekly", "monthly"] = "weekly"


AGES = {"synthetic_5m": 5, "synthetic_24m": 24, "synthetic_59m": 59}
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@lru_cache(maxsize=12)
def _synthetic_method_results(age: int, simulator_case: str):
    """Fixed fixture predictions are budget-independent and repeatable."""
    results = []
    original = None
    profile = None
    for method in ("bounded_search", "dice", "face_graph"):
        raw = demo_request(method=method, scenario=simulator_case).model_dump(mode="json")
        # Exact snapshot is also used by optional genuine C1 validation.
        raw["snapshot"] = standalone_snapshot(f"synthetic_{age}m").model_dump(mode="json")
        template = raw["food_planning"]["alternatives"][0]
        transitions = (
            ("meal-frequency-test", [{"feature": "meals_per_day", "from_value": 3, "to_value": 4}]),
            ("dietary-diversity-test", [{"feature": "dietary_diversity", "from_value": 1, "to_value": 2}]),
            ("combined-feeding-test", [{"feature": "meals_per_day", "from_value": 3, "to_value": 4},
                                       {"feature": "dietary_diversity", "from_value": 1, "to_value": 2}]),
        )
        raw["food_planning"]["alternatives"] = []
        for identifier, changes in transitions:
            alternative = deepcopy(template)
            alternative["alternative_id"] = identifier
            alternative["title"] = "Software-test feeding transition"
            alternative["changes"] = changes
            raw["food_planning"]["alternatives"].append(alternative)
        fixture = C1Request.model_validate(raw)
        original = {key: fixture.snapshot.ga_rgca_context[key]
                    for key in ("meal_frequency", "dietary_diversity")}
        profile = {"test_id": fixture.snapshot.child_pseudonymous_id,
                   "age_months": age,
                   "historical_height_cm": fixture.snapshot.historical_baseline["height_cm"],
                   "historical_weight_kg": fixture.snapshot.historical_baseline["weight_kg"],
                   "provenance": "fully synthetic C2 demonstration profile; anthropometrics are fixed software fixture values"}
        results.append(run_c1(fixture))
    return tuple(results), original, profile


def _schedule(option: dict) -> list[dict]:
    """Rotate listed food pairings; never allocate servings or infer adequacy."""
    groups: dict[str, list[dict]] = {}
    for item in option["items"]:
        groups.setdefault(item["food_group"], []).append(item)
    cereals = groups.get("rice and cereals", [])
    proteins = [*groups.get("pulses", []), *groups.get("eggs", []), *groups.get("fish", [])]
    vegetables = [*groups.get("vegetables", []), *groups.get("green leafy vegetables", [])]
    fruits = groups.get("fruits", [])
    if not cereals or not proteins or not vegetables:
        return []

    def foods(*rows: dict) -> list[dict]:
        unique = {row["food_id"]: row for row in rows}
        return [{"name": row["name"], "food_group": row["food_group"],
                 "source_url": row["source_url"]} for row in unique.values()]

    schedule = []
    for index, day in enumerate(DAYS):
        cereal = cereals[index % len(cereals)]
        protein = proteins[index % len(proteins)]
        vegetable = vegetables[index % len(vegetables)]
        later = fruits[index % len(fruits)] if fruits else vegetable
        slots = [
            {"label": "Morning pairing idea", "foods": foods(cereal, protein)},
            {"label": "Midday pairing idea", "foods": foods(cereal, protein, vegetable)},
            {"label": "Later pairing idea", "foods": foods(cereal, later)},
        ]
        schedule.append({"day": day, "slots": slots,
                         "variety_explanation": f"Illustrates {len(option['food_groups'])} listed food groups across this shopping example; repeated ingredients do not establish dietary adequacy."})
    return schedule


def _food_plans(age: int, guidance: dict, budget_lkr: Decimal | None, period: str, *, scenarios=None) -> list[dict]:
    plans = shopping_examples(age, guidance, budget_lkr, period, **({"scenarios": scenarios} if scenarios is not None else {}))
    for plan in plans:
        cost = Decimal(plan["estimated_total_lkr"]) if plan["estimated_total_lkr"] is not None else None
        plan["budget_remaining_lkr"] = (str((budget_lkr - cost).quantize(Decimal("0.01")))
                                         if budget_lkr is not None and cost is not None and budget_lkr >= cost else None)
        plan["shortfall_lkr"] = (str((cost - budget_lkr).quantize(Decimal("0.01")))
                                 if budget_lkr is not None and cost is not None and cost > budget_lkr else None)
        plan["schedule"] = _schedule(plan) if not plan["missing_evidence"] else []
        plan["schedule_status"] = "illustrative_food_pairings" if plan["schedule"] else "evidence_incomplete"
        plan["guideline_scope_note"] = "Broad published food groups only. Individual food suitability, child serving sizes, feeding frequency and nutritional adequacy have not been reviewed."
    return plans


def run_standalone(request: StandaloneRequest, *, simulator_case: str = "favorable") -> dict:
    age = AGES[request.case_id]
    guidance = research_guidance_for_age(age)
    budget = {"amount_lkr": str(request.budget_lkr) if request.budget_lkr is not None else None,
              "period": request.budget_period, "provenance": "user-entered demonstration amount; not verified household evidence"}
    if age < 6:
        return {"mode": "standalone_research_test", "case_id": request.case_id,
                "input_fingerprint": standalone_input_fingerprint(request.case_id),
                "profile": {"test_id": f"SYNTHETIC-C2-{age}M", "age_months": age,
                            "historical_height_cm": None, "historical_weight_kg": None,
                            "provenance": "synthetic safety fixture; anthropometrics are not scored"},
                "original_feeding": None, "baseline": None, "methods": [], "cards": [],
                "rejected_or_unresolved": [], "food_plans": [], "guidance": guidance,
                "budget": budget, "clinical_use": False, "c1_required": False,
                "message": "No complementary-food or feeding-category plan is generated below six months."}

    method_results, original, profile = _synthetic_method_results(age, simulator_case)
    baseline = method_results[0].baseline
    if baseline["prediction_source"] != "SIMULATED_TEST_ONLY":
        raise ValueError("standalone fixture must retain simulated prediction provenance")
    if any(result.baseline != baseline or result.c1_integrated or result.clinical_use
           for result in method_results):
        raise ValueError("standalone method output provenance mismatch")

    accepted: dict[tuple, dict] = {}
    rejected = []
    methods = []
    for result in method_results:
        methods.append({"name": result.method, "mode": "SIMULATED_TEST_ONLY",
                        "eligible_count": len(result.cards), "rejected_count": len(result.rejected_or_unresolved)})
        for card in result.cards:
            key = tuple(sorted(card["changes"].items()))
            if key not in accepted:
                accepted[key] = {"changes": card["changes"], "supporting_methods": [],
                                 "prediction": None, "research_test_feasibility": card["feasibility_status"],
                                 "fixture_affordability": card.get("affordability"),
                                 "fixture_price_scope": card.get("affordability_scope"),
                                 "fixture_availability": card.get("availability"),
                                 "status": "Eligible in Research Test", "professional_review_required": True,
                                 "explanation": card["explanation"],
                                 "real_world_suitability": "unknown", "real_world_availability": "unknown"}
            accepted[key]["supporting_methods"].append(result.method)
            matching = next((item["candidate"] for item in result.candidates if item["changes"] == card["changes"]), None)
            if matching is None or matching["prediction_source"] != "SIMULATED_TEST_ONLY":
                raise ValueError("accepted test card lacks a matching simulated prediction")
            if accepted[key]["prediction"] is not None and accepted[key]["prediction"] != matching:
                raise ValueError("test methods disagree on candidate prediction")
            accepted[key]["prediction"] = matching
        for item in result.rejected_or_unresolved:
            rejected.append({"method": result.method, "changes": item["changes"],
                             "status": item["status"], "reasons": item["reasons"]})
    plans = _food_plans(age, guidance, request.budget_lkr, request.budget_period)
    cards = sorted(accepted.values(), key=lambda card: (len(card["changes"]), tuple(sorted(card["changes"].items()))))
    for rank, card in enumerate(cards, 1):
        card["rank"] = rank
        card["food_plans"] = plans
        card["food_plan_relationship"] = "Educational pairing examples only; basket fit does not validate the modeled feeding change or synthetic fixture assertions."
    return {"mode": "standalone_research_test", "case_id": request.case_id,
            "input_fingerprint": standalone_input_fingerprint(request.case_id),
            "profile": profile,
            "original_feeding": original, "baseline": baseline,
            "methods": methods, "cards": cards, "rejected_or_unresolved": rejected,
            "food_plans": plans, "guidance": guidance, "budget": budget,
            "clinical_use": False, "c1_required": False,
            "message": "Research-test eligibility reflects existing synthetic fixture assertions only; professional review and real-world evidence remain required."}
