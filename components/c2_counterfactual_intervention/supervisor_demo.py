"""October 22 local supervisor CLI. Every profile and model output is simulated."""
import argparse
import json
from datetime import date
from decimal import Decimal

from .c1_compat import C1Snapshot
from .c1_engine import C1Request, run_c1
from .demonstrations import _request as synthetic_food_request
from .evaluation import CHECKS
from .official_prices import bundled_history, indicative_reference_cost, price_state


TEST_BANNER = "RESEARCH TEST MODE — C1 TRAINED MODEL NOT CONNECTED"


def official_price_demo(*, food_id: str, quantity: Decimal, unit: str,
                        as_of: date, budget_lkr: Decimal | None = None,
                        budget_period: str | None = None, quantity_period: str | None = None,
                        budget_source: str | None = None,
                        local_availability: str = "unknown", availability_source: str | None = None,
                        caregiver_practical: str = "unknown", practicality_source: str | None = None) -> dict:
    """Published Colombo price arithmetic and separate illustrative household assertions."""
    record = next((row for row in bundled_history() if row.food_id == food_id and row.evidence_status == "source_checked"), None)
    if record is None:
        raise ValueError("food ID has no checked DCS price record")
    if budget_lkr is not None and (budget_lkr < 0 or budget_period is None):
        raise ValueError("nonnegative budget and budget period must be supplied together")
    if budget_lkr is None and (budget_period or budget_source):
        raise ValueError("budget source or period requires a budget amount")
    if local_availability != "unknown" and not availability_source:
        raise ValueError("reported local availability requires its user-supplied provenance")
    if caregiver_practical != "unknown" and not practicality_source:
        raise ValueError("reported caregiver practicality requires its user-supplied provenance")
    cost = indicative_reference_cost(record, quantity, unit)
    comparison = "unresolved"
    if budget_lkr is not None and quantity_period == budget_period:
        comparison = "within illustrative budget" if cost <= budget_lkr else "above illustrative budget"
    return {
        "banner": TEST_BANNER,
        "workflow": "OFFICIAL REFERENCE PRICE; no intervention recommendation",
        "official_reference": {
            "food_id": record.food_id, "published_commodity": record.published_commodity,
            "published_price_lkr": str(record.amount_lkr), "published_quantity": str(record.quantity),
            "published_unit": record.unit, "illustrative_quantity": str(quantity),
            "illustrative_unit": unit, "indicative_reference_cost_lkr": str(cost),
            "source_institution": record.source_institution, "publication_url": record.report_url,
            "publication_date": record.publication_date.isoformat() if record.publication_date else None,
            "market_coverage": record.market_coverage,
            "observation_start": record.observation_start.isoformat(),
            "observation_end": record.observation_end.isoformat(),
            "period_date_basis": record.period_date_basis,
            "freshness_as_of": as_of.isoformat(), "freshness_status": price_state(record, as_of=as_of).upper(),
        },
        "scenario": {
            "budget_lkr": str(budget_lkr) if budget_lkr is not None else None,
            "budget_period": budget_period, "quantity_period": quantity_period,
            "budget_provenance": budget_source or ("user-supplied illustration; unverified" if budget_lkr is not None else None),
            "reference_cost_budget_comparison": comparison,
            "local_availability": local_availability, "availability_provenance": availability_source,
            "caregiver_practical": caregiver_practical, "practicality_provenance": practicality_source,
            "verified_local_affordability": "UNKNOWN",
            "clinical_suitability": "UNKNOWN",
        },
        "limitations": "Colombo District reference only; no verified Kalmunai price, household budget, serving size, or treatment effect.",
    }


def demo_request(method: str = "bounded_search", scenario: str = "favorable") -> C1Request:
    context = {name: {"meals_per_day": True, "dietary_diversity": True} for name in CHECKS}
    context["budget_units"] = 10
    meal, diversity, age = "3 meals/day", "More than 5 varieties", 24
    if scenario == "no_solution":
        meal, diversity = "4+ meals/day", "More than 5 varieties"
    elif scenario == "unknown_availability":
        context["available"]["meals_per_day"] = None
        context["available"]["dietary_diversity"] = None
    elif scenario == "unaffordable":
        context["budget_units"] = 0
    elif scenario == "too_young":
        age = 5
    snapshot = C1Snapshot(child_pseudonymous_id="SYNTHETIC-SUPERVISOR-001", visit_number=1,
        visit_date="2026-10-22", historical_baseline={"source": "baseline_assessment",
        "age_months": age, "height_cm": 80, "weight_kg": 10},
        ga_rgca_context={"meal_frequency": meal, "dietary_diversity": diversity},
        provenance="fully synthetic October 22 software fixture")
    simulator_case = scenario if scenario in {"unchanged", "worsening", "uncertain"} else "favorable"
    food = synthetic_food_request(3, 2)["food_planning"]
    if scenario == "unaffordable":
        food["budget"]["amount_lkr"] = "50"
    return C1Request(mode="simulated", method=method, simulator_case=simulator_case, snapshot=snapshot, context=context,
        food_planning=food,
        policy={"policy_id": "SUPERVISOR-FIXTURE-ONLY", "approved_for_research": True,
                "allowed_type_transitions": [["Underweight", "Normal"], ["MAM", "Underweight"],
                                             ["MAM", "Normal"], ["SAM", "MAM"], ["Stunting", "MAM"]]})


def main():
    parser = argparse.ArgumentParser(description=TEST_BANNER)
    parser.add_argument("--workflow", choices=["engine", "official_price"], default="engine")
    parser.add_argument("--food-id", choices=[r.food_id for r in bundled_history()])
    parser.add_argument("--quantity", type=Decimal)
    parser.add_argument("--unit", choices=["g", "kg", "ml", "l", "piece", "bunch", "serving"])
    parser.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 10, 22))
    parser.add_argument("--budget-lkr", type=Decimal)
    parser.add_argument("--budget-period", choices=["day", "week", "month"])
    parser.add_argument("--quantity-period", choices=["day", "week", "month"])
    parser.add_argument("--budget-source")
    parser.add_argument("--local-availability", choices=["available", "unavailable", "unknown"], default="unknown")
    parser.add_argument("--availability-source")
    parser.add_argument("--caregiver-practical", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--practicality-source")
    parser.add_argument("--method", choices=["bounded_search", "dice", "face_graph"], default="bounded_search")
    parser.add_argument("--scenario", choices=["favorable", "unchanged", "worsening", "uncertain",
                                                "no_solution", "unknown_availability", "unaffordable", "too_young"],
                        default="favorable")
    args = parser.parse_args()
    if args.workflow == "official_price":
        if args.food_id is None or args.quantity is None or args.unit is None:
            parser.error("official_price requires --food-id, --quantity and --unit")
        try:
            result = official_price_demo(food_id=args.food_id, quantity=args.quantity, unit=args.unit,
                as_of=args.as_of, budget_lkr=args.budget_lkr, budget_period=args.budget_period,
                quantity_period=args.quantity_period, budget_source=args.budget_source,
                local_availability=args.local_availability, availability_source=args.availability_source,
                caregiver_practical=args.caregiver_practical, practicality_source=args.practicality_source)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(result, indent=2))
        return
    request = demo_request(args.method, args.scenario)
    response = run_c1(request)
    print(TEST_BANNER)
    print("C1 integration: UNVERIFIED; real model artifacts unavailable")
    print("Original feeding:", request.snapshot.ga_rgca_context["meal_frequency"], "/",
          request.snapshot.ga_rgca_context["dietary_diversity"])
    print(json.dumps(response.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
