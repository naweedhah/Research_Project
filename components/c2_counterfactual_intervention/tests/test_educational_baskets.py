"""Shopping examples are independent from C1 and from clinical feasibility."""
from datetime import date
from decimal import Decimal

from components.c2_counterfactual_intervention.automatic_analysis import AutomaticRequest, run_automatic_analysis
from components.c2_counterfactual_intervention.educational_baskets import shopping_examples
from components.c2_counterfactual_intervention.guideline_references import research_guidance_for_age
from components.c2_counterfactual_intervention.official_prices import bundled_history
from components.c2_counterfactual_intervention.tests.test_automatic_analysis import StubC1


def options(amount=None, period="weekly", age=24, **kwargs):
    return shopping_examples(age, research_guidance_for_age(age), amount, period, **kwargs)


def test_weekly_budget_changes_fit_and_order_without_approval():
    outputs = [run_automatic_analysis(AutomaticRequest(budget_lkr=Decimal(value)), StubC1())
               for value in ("500", "1500", "3000")]
    fits = [{item["title"]: item["budget_fit"] for item in output["shopping_examples"]} for output in outputs]
    assert fits[0] != fits[1]
    assert fits[1] != fits[2]
    assert all(output["approved_intervention_cards"] == [] for output in outputs)
    assert outputs[0]["baseline"] == outputs[1]["baseline"] == outputs[2]["baseline"]
    assert [(item["changes"], item["prediction"], item["disposition"]) for item in outputs[0]["candidates"]] == [
        (item["changes"], item["prediction"], item["disposition"]) for item in outputs[2]["candidates"]]


def test_age_and_missing_budget():
    assert options(Decimal("500"), age=5) == []
    assert len(options(Decimal("500"), age=59)) >= 3
    assert all(item["budget_fit"] == "unknown" for item in options())
    assert any(item["budget_fit"] == "above_budget" for item in options(Decimal("500")))


def test_missing_guidance_and_price_do_not_create_false_budget_fit():
    assert shopping_examples(24, {"food_groups": [], "reference": None}, Decimal("3000"), "weekly") == []
    rows = [row for row in bundled_history() if row.food_id != "egg_average"]
    examples = options(Decimal("3000"), history=rows)
    egg = next(item for item in examples if item["title"] == "Egg and greens example")
    assert egg["budget_fit"] == "unknown" and egg["estimated_total_lkr"] is None
    old = options(Decimal("3000"), as_of=date(2026, 12, 1))
    assert all(item["price_evidence"] == "historical_or_missing" for item in old)


def test_period_units_and_repeatability():
    weekly = options(Decimal("1500"))
    daily = options(Decimal("1500"), "daily")
    monthly = options(Decimal("1500"), "monthly")
    by_title = lambda rows: {row["title"]: row for row in rows}
    assert Decimal(by_title(monthly)["Essentials example"]["estimated_total_lkr"]) == 4 * Decimal(by_title(weekly)["Essentials example"]["estimated_total_lkr"])
    assert all(row["cost_period"] == row["budget_period"] == "daily" for row in daily)
    assert all(item["unit"] in ("kg", "piece", "bunch") for row in weekly for item in row["items"])
    assert weekly == options(Decimal("1500"))
