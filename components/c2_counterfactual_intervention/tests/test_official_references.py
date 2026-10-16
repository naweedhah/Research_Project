"""Synthetic importer fixtures; bundled observations are checked against a cited DCS PDF."""
import csv
import io
import json
import sys
from datetime import date
from decimal import Decimal

import pytest

from components.c2_counterfactual_intervention.engine import MissingRealPredictorError, recommend
from components.c2_counterfactual_intervention.food_feasibility import assess_food_alternative
from components.c2_counterfactual_intervention.food_resources import FoodPlanningContext
from components.c2_counterfactual_intervention.guideline_references import applicable_references, REFERENCES
from components.c2_counterfactual_intervention.official_prices import (
    DCS_COVERAGE, DCS_REPORT, FOODS, bundled_history, catalog_from_history, import_csv,
    main, price_state, read_history, refresh,
)
from components.c2_counterfactual_intervention.schemas import RecommendationRequest
from components.c2_counterfactual_intervention.tests.test_food_planning import planning_request


def fixture_csv(**changes):
    """Synthetic row derived from a bundled row; never treated as a published observation."""
    row = bundled_history()[0].model_dump(mode="json")
    for field in ("food_name", "food_group", "imported_at"):
        row.pop(field)
    row.update(changes)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()


def test_bundled_dcs_attribution_catalog_and_missing_product():
    rows = bundled_history()
    assert len(rows) == 13
    assert all(row.report_url == DCS_REPORT and row.market_coverage == DCS_COVERAGE
               and row.price_class == "retail" and row.source_locator for row in rows)
    assert all(row.period_date_basis == "calendar_week_interpretation" for row in rows)
    assert len({row.imported_at for row in rows}) == 1
    catalog = catalog_from_history(rows)
    assert len(catalog) == len(FOODS) == 14
    assert sum(food.price is None for food in catalog) == 1
    assert next(food for food in catalog if food.food_id == "curd").price is None
    assert all(food.locally_available is None for food in catalog)
    egg = next(food for food in catalog if food.food_id == "egg_average")
    assert egg.price.amount_lkr == Decimal("37.77")
    assert egg.price.unit == "piece" and egg.price.market_coverage == DCS_COVERAGE


def test_import_rejects_duplicate_bad_values_wrong_commodity_source_and_dates():
    sample = fixture_csv()
    with pytest.raises(ValueError, match="duplicate"):
        import_csv(sample + sample.splitlines(True)[1])
    for change, message in [({"amount_lkr": "0"}, "greater than 0"),
                            ({"unit": "basket"}, "unit"),
                            ({"published_commodity": "Rice"}, "commodity"),
                            ({"report_url": "https://example.org/fake.pdf"}, "source institution"),
                            ({"observation_end": "2999-01-01"}, "future")]:
        with pytest.raises(ValueError, match=message):
            import_csv(fixture_csv(**change))


def test_refresh_history_idempotency_failure_and_conflict(tmp_path):
    history = tmp_path / "history.json"
    sample = fixture_csv()
    assert refresh(history, lambda: sample) == 1
    before = history.read_bytes()
    assert refresh(history, lambda: sample) == 0
    assert history.read_bytes() == before
    with pytest.raises(OSError):
        refresh(history, lambda: (_ for _ in ()).throw(OSError("download failed")))
    with pytest.raises(ValueError, match="conflicting"):
        refresh(history, lambda: fixture_csv(amount_lkr="999.00"))
    with pytest.raises(ValueError, match="checked"):
        refresh(history, lambda: fixture_csv(price_class="wholesale"))
    assert history.read_bytes() == before and len(read_history(history)) == 1
    assert refresh(history, lambda: fixture_csv(observation_start="2026-09-01",
                                                observation_end="2026-09-07")) == 1
    assert len(read_history(history)) == 2


def test_on_demand_refresh_cli(tmp_path, monkeypatch, capsys):
    source = tmp_path / "reviewed.csv"
    source.write_text(fixture_csv(), encoding="utf-8")
    history = tmp_path / "history.json"
    monkeypatch.setattr(sys, "argv", ["official_prices", "--reviewed-csv", str(source),
                                  "--history", str(history)])
    main()
    assert json.loads(capsys.readouterr().out)["added"] == 1
    main()
    assert json.loads(capsys.readouterr().out)["added"] == 0


def test_fresh_stale_wholesale_and_unverified_states():
    row = bundled_history()[0]
    assert price_state(row, as_of=date(2026, 10, 15), fresh_days=14) == "fresh_reference"
    assert price_state(row, as_of=date(2026, 11, 1), fresh_days=14) == "historical_reference"
    assert price_state(None) == "missing"
    assert price_state(row.model_copy(update={"price_class": "wholesale"})) == "unverified_or_unusable"
    assert price_state(row.model_copy(update={"evidence_status": "transcribed_unverified"})) == "unverified_or_unusable"
    assert catalog_from_history([row.model_copy(update={"price_class": "wholesale"})])[0].price is None
    stale = catalog_from_history([row], as_of=date(2026, 11, 1))[0]
    assert stale.price.reference_status == "historical_reference"


def test_indicative_cost_conversion_and_unknown_local_availability():
    raw = planning_request()
    raw["food_planning"]["catalog"] = [food.model_dump(mode="json") for food in catalog_from_history(bundled_history())]
    quantity = raw["food_planning"]["alternatives"][0]["foods"][0]
    quantity.update(food_id="mysore_dhall_average", quantity="100", unit="g")
    planning = FoodPlanningContext.model_validate(raw["food_planning"])
    assessment = assess_food_alternative(planning.alternatives[0], planning, "test")
    assert assessment.cost_lkr == Decimal("33.452")
    assert assessment.status == "unresolved" and assessment.affordability_scope == "indicative_official_reference"
    assert any("local availability unknown" in reason for reason in assessment.reasons)
    food = next(item for item in raw["food_planning"]["catalog"] if item["food_id"] == "mysore_dhall_average")
    food["locally_available"] = True
    food["availability_evidence"] = {"kind": "authorized_input", "source": "synthetic caregiver fixture",
                                     "observed_on": "2026-10-15"}
    response = recommend(RecommendationRequest.model_validate(raw))
    assert response.cards and response.cards[0].affordability_scope == "indicative_official_reference"
    assert response.cards[0].incremental_cost_lkr == "33.452"
    quantity["unit"] = "piece"
    response = recommend(RecommendationRequest.model_validate(raw))
    assert not response.cards
    assert any("units differ" in reason for item in response.rejected_or_unresolved for reason in item.reasons)


def test_historical_reference_requires_review_and_local_price_has_distinct_scope():
    raw = planning_request()
    catalog = catalog_from_history(bundled_history(), as_of=date(2026, 11, 1))
    raw["food_planning"]["catalog"] = [food.model_dump(mode="json") for food in catalog]
    quantity = raw["food_planning"]["alternatives"][0]["foods"][0]
    quantity.update(food_id="egg_average", quantity="1", unit="piece")
    egg = next(item for item in raw["food_planning"]["catalog"] if item["food_id"] == "egg_average")
    egg["locally_available"] = True
    egg["availability_evidence"] = {"kind": "authorized_input", "source": "synthetic local fixture",
                                    "observed_on": "2026-10-15"}
    response = recommend(RecommendationRequest.model_validate(raw))
    assert not response.cards
    assert any("historical official reference" in reason for item in response.rejected_or_unresolved
               for reason in item.reasons)
    egg["price"]["reference_kind"] = "local_verified"
    egg["price"]["reference_status"] = None
    egg["price"]["market_coverage"] = "Synthetic Kalmunai local-price fixture"
    egg["price"]["evidence"] = {"kind": "verified_source", "source": "synthetic local price fixture",
                                 "observed_on": "2026-10-15"}
    response = recommend(RecommendationRequest.model_validate(raw))
    assert response.cards and response.cards[0].affordability_scope == "locally_verified"


def test_guideline_age_scope_and_real_predictor_separation():
    assert len(REFERENCES) == 3
    assert not applicable_references(5) and not applicable_references(24)
    assert [item.institution for item in applicable_references(6)] == ["World Health Organization"]
    assert all(item.review_status != "expert_approved" for item in REFERENCES)
    raw = planning_request()
    raw.update(mode="real", predictor="unregistered-c1", predictor_version="1")
    with pytest.raises(MissingRealPredictorError):
        recommend(RecommendationRequest.model_validate(raw))
