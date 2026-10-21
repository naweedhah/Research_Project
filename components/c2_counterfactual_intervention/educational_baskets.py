"""Illustrative, period-matched shopping scenarios; never child feeding prescriptions."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from .official_prices import OfficialPriceObservation, bundled_history, indicative_reference_cost, price_state


# Quantities describe a hypothetical household purchase in one week, not child servings.
SCENARIOS = (
    ("Essentials example", (("rice_raw_red_average", "0.5", "kg"), ("mysore_dhall_average", "0.25", "kg"), ("gotukola_bunch", "1", "bunch"))),
    ("Egg and greens example", (("rice_nadu_white_local", "1", "kg"), ("egg_average", "6", "piece"), ("carrot", "0.5", "kg"), ("gotukola_bunch", "1", "bunch"))),
    ("Fish and fruit example", (("rice_raw_red_average", "1", "kg"), ("fish_salaya_fresh", "0.5", "kg"), ("papaw", "0.5", "kg"), ("carrot", "0.5", "kg"))),
    ("Varied groups example", (("rice_nadu_white_local", "1", "kg"), ("green_gram_average", "0.5", "kg"), ("egg_average", "8", "piece"), ("fish_salaya_fresh", "0.5", "kg"), ("gotukola_bunch", "2", "bunch"), ("banana_sour_plantain", "1", "kg"))),
)
# Additional illustrative combinations use the same source-checked commodities
# and purchase units as the original four examples. They are not child portions.
SCENARIO_VARIANTS = (
    ("Pulse and vegetable example", (("rice_nadu_white_local", "0.5", "kg"), ("green_gram_average", "0.25", "kg"), ("carrot", "0.5", "kg"))),
    ("Egg and fruit example", (("rice_raw_red_average", "0.5", "kg"), ("egg_average", "6", "piece"), ("papaw", "0.5", "kg"), ("gotukola_bunch", "1", "bunch"))),
    ("Fish and greens example", (("rice_nadu_white_local", "1", "kg"), ("fish_salaya_fresh", "0.5", "kg"), ("gotukola_bunch", "1", "bunch"), ("carrot", "0.5", "kg"))),
    ("Pulse and banana example", (("rice_raw_red_average", "0.5", "kg"), ("mysore_dhall_average", "0.25", "kg"), ("banana_sour_plantain", "1", "kg"), ("carrot", "0.5", "kg"))),
)
PERIOD_MULTIPLIER = {"daily": Decimal("1") / Decimal("7"), "weekly": Decimal("1"), "monthly": Decimal("4")}
CENT = Decimal("0.01")


def shopping_examples(age_months: int, guidance: dict, budget_lkr: Decimal | None,
                      period: str, *, history: list[OfficialPriceObservation] | None = None,
                      as_of: date | None = None, scenarios=SCENARIOS) -> list[dict]:
    """Compare identical-period indicative costs; unknown evidence never becomes affordable."""
    if age_months < 6 or not guidance.get("reference") or not guidance.get("food_groups"):
        return []
    if period not in PERIOD_MULTIPLIER:
        raise ValueError("unsupported budget period")
    records = {row.food_id: row for row in (bundled_history() if history is None else history)
               if row.evidence_status == "source_checked" and row.price_class == "retail"}
    groups = set(guidance["food_groups"])
    examples = []
    for title, purchases in scenarios:
        items, missing, total = [], [], Decimal("0")
        for food_id, weekly_amount, unit in purchases:
            row = records.get(food_id)
            if row is None or row.food_group not in groups:
                missing.append(food_id + ": checked price or reviewed group unavailable")
                continue
            quantity = Decimal(weekly_amount) * PERIOD_MULTIPLIER[period]
            if period == "daily" and unit in {"piece", "bunch"}:
                quantity = quantity.to_integral_value(rounding=ROUND_CEILING)
            try:
                cost = indicative_reference_cost(row, quantity, unit)
            except ValueError:
                missing.append(food_id + ": incompatible price unit")
                continue
            total += cost
            items.append({"food_id": food_id, "name": row.food_name, "food_group": row.food_group,
                          "quantity": str(quantity.quantize(Decimal("0.0001"))), "unit": unit,
                          "published_unit_price_lkr": str(row.amount_lkr),
                          "published_quantity": str(row.quantity), "published_unit": row.unit,
                          "indicative_cost_lkr": str(cost.quantize(CENT, rounding=ROUND_HALF_UP)),
                          "source_title": row.source_institution, "source_url": row.report_url,
                          "source_locator": row.source_locator, "market_coverage": row.market_coverage,
                          "observation_end": row.observation_end.isoformat(),
                          "price_status": price_state(row, as_of=as_of)})
        known = bool(items) and not missing
        amount = total.quantize(CENT, rounding=ROUND_HALF_UP) if known else None
        fit = ("unknown" if amount is None or budget_lkr is None else
               "within_budget" if amount <= budget_lkr else "above_budget")
        represented = sorted({item["food_group"] for item in items})
        freshness = "fresh_reference" if known and all(item["price_status"] == "fresh_reference" for item in items) else "historical_or_missing"
        examples.append({"title": title, "kind": "educational_shopping_example", "items": items,
                         "food_groups": represented, "group_count": len(represented),
                         "cost_period": period, "budget_period": period,
                         "estimated_total_lkr": str(amount) if amount is not None else None,
                         "budget_lkr": str(budget_lkr) if budget_lkr is not None else None,
                         "budget_fit": fit, "price_evidence": freshness,
                         "missing_evidence": missing, "guideline_reference": guidance["reference"],
                         "quantity_note": "Illustrative household shopping quantities for pricing only; not child servings, a complete diet, or a treatment plan.",
                         "period_note": "Daily scales weekly mass to one seventh and rounds pieces and bunches up to whole purchases; monthly uses four weekly purchases. This is a price scenario, not feeding frequency.",
                         "coverage_note": "DCS Colombo District retail reference; local price and availability are unverified."})
    # Budget fit only orders shopping examples; it has no path to model policy or cards.
    fit_order = {"within_budget": 0, "above_budget": 1, "unknown": 2}
    examples.sort(key=lambda row: (fit_order[row["budget_fit"]], -row["group_count"],
                                   0 if row["price_evidence"] == "fresh_reference" else 1,
                                   -len(row["items"]), Decimal(row["estimated_total_lkr"]) if row["estimated_total_lkr"] else Decimal("Infinity"), row["title"]))
    for rank, row in enumerate(examples, 1):
        row["rank"] = rank
        row["ranking_reason"] = (f"{row['budget_fit'].replace('_', ' ')}; {row['group_count']} reviewed food groups; "
                                 f"{len(row['items'])} priced items; {row['price_evidence'].replace('_', ' ')}; "
                                 "then indicative cost and fixed title tie-breaker. No clinical ranking.")
    return examples
