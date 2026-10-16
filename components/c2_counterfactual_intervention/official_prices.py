"""Auditable official retail reference prices; never local Kalmunai quotations."""
import argparse
import csv
import io
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .food_resources import Evidence, FoodResource, Price


DCS_REPORT = "https://www.statistics.gov.lk/Resource/en/InflationAndPrices/retail/DCSB-WRP-2026-10-W1.pdf"
DCS_COVERAGE = "Main markets in Colombo District"


class OfficialPriceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    food_id: str = Field(min_length=1)
    food_name: str = Field(min_length=1)
    food_group: str = Field(min_length=1)
    published_commodity: str = Field(min_length=1)
    amount_lkr: Decimal = Field(gt=0, allow_inf_nan=False)
    quantity: Decimal = Field(gt=0, allow_inf_nan=False)
    unit: Literal["g", "kg", "ml", "l", "piece", "bunch", "serving"]
    source_institution: Literal["Department of Census and Statistics", "HARTI"]
    report_url: str = Field(pattern=r"^https://")
    publication_date: date | None = None
    observation_start: date
    observation_end: date
    period_date_basis: Literal["explicit_report_dates", "calendar_week_interpretation"]
    market_coverage: str = Field(min_length=1)
    price_class: Literal["retail", "wholesale"]
    evidence_status: Literal["source_checked", "transcribed_unverified"]
    source_locator: str = Field(min_length=1)
    imported_at: datetime

    @model_validator(mode="after")
    def valid_dates(self):
        if self.observation_end < self.observation_start:
            raise ValueError("observation period reversed")
        if self.observation_end > date.today() or (self.publication_date and self.publication_date > date.today()):
            raise ValueError("future source date")
        host = urlparse(self.report_url).hostname
        allowed = {"Department of Census and Statistics": "statistics.gov.lk", "HARTI": "harti.gov.lk"}
        if host not in (allowed[self.source_institution], "www." + allowed[self.source_institution]):
            raise ValueError("report URL does not match source institution")
        return self

    @property
    def identity(self) -> tuple:
        return (self.report_url, self.source_locator, self.published_commodity,
                self.observation_start, self.observation_end, self.market_coverage, self.price_class)


class FoodDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    food_id: str
    name: str
    group: str
    exact_commodity: str


FOODS = (
    FoodDefinition(food_id="rice_raw_red_average", name="Raw Red - ( Average )", group="rice and cereals", exact_commodity="Raw Red - ( Average )"),
    FoodDefinition(food_id="rice_nadu_white_local", name="Nadu - White local", group="rice and cereals", exact_commodity="Nadu - White local"),
    FoodDefinition(food_id="wheat_flour", name="Wheat Flour", group="rice and cereals", exact_commodity="Wheat Flour"),
    FoodDefinition(food_id="mysore_dhall_average", name="Mysore Dhall - ( Average )", group="pulses", exact_commodity="Mysore Dhall - ( Average )"),
    FoodDefinition(food_id="green_gram_average", name="Green Gram - Average", group="pulses", exact_commodity="Green Gram - Average"),
    FoodDefinition(food_id="egg_average", name="Egg - ( Average )", group="eggs", exact_commodity="Egg - ( Average )"),
    FoodDefinition(food_id="fish_salaya_fresh", name="Fresh Fish - Salaya", group="fish", exact_commodity="Fresh Fish - Salaya"),
    FoodDefinition(food_id="chicken_fresh", name="Chicken - Fresh", group="chicken", exact_commodity="Chicken - Fresh"),
    FoodDefinition(food_id="milk_powder_pelwatta_400g", name="Pelwatta 400g milk powder", group="milk and dairy", exact_commodity="Pelwatta 400g."),
    FoodDefinition(food_id="carrot", name="Carrot", group="vegetables", exact_commodity="Carrot"),
    FoodDefinition(food_id="gotukola_bunch", name="Gotukola Bunch", group="green leafy vegetables", exact_commodity="Gotukola Bunch"),
    FoodDefinition(food_id="papaw", name="Papaw", group="fruits", exact_commodity="Papaw"),
    FoodDefinition(food_id="banana_sour_plantain", name="Sour Plantain", group="fruits", exact_commodity="Sour Plantain"),
    FoodDefinition(food_id="curd", name="Curd", group="milk and dairy", exact_commodity="Curd"),
)
FOOD_BY_ID = {food.food_id: food for food in FOODS}


def import_csv(content: str, *, imported_at: datetime | None = None) -> list[OfficialPriceObservation]:
    """Import a reviewed transcription; each row retains an exact report locator."""
    reader = csv.DictReader(io.StringIO(content))
    required = {"food_id", "published_commodity", "amount_lkr", "quantity", "unit",
                "source_institution", "report_url", "observation_start", "observation_end",
                "market_coverage", "price_class", "evidence_status", "source_locator", "period_date_basis"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("missing required official price columns")
    records = []
    seen = set()
    stamp = imported_at or datetime.now(timezone.utc)
    for row in reader:
        food = FOOD_BY_ID.get(row["food_id"])
        if food is None or row["published_commodity"] != food.exact_commodity:
            raise ValueError("unmatched or changed commodity definition")
        record = OfficialPriceObservation.model_validate({
            **row, "food_name": food.name, "food_group": food.group,
            "publication_date": row.get("publication_date") or None,
            "imported_at": row.get("imported_at") or stamp,
        })
        if record.identity in seen:
            raise ValueError("duplicate observation in import")
        seen.add(record.identity)
        records.append(record)
    return records


def read_history(path: Path) -> list[OfficialPriceObservation]:
    if not path.exists():
        return []
    return [OfficialPriceObservation.model_validate(row) for row in json.loads(path.read_text(encoding="utf-8"))]


def refresh(path: Path, fetch: Callable[[], str]) -> int:
    """On-demand, schedule-ready refresh. Fetch/parse failures leave history intact."""
    content = fetch()
    incoming = import_csv(content)
    if not incoming or any(row.evidence_status != "source_checked" or row.price_class != "retail"
                           for row in incoming):
        raise ValueError("refresh requires checked, nonempty retail observations")
    existing = read_history(path)
    known = {row.identity: row for row in existing}
    for row in incoming:
        prior = known.get(row.identity)
        if prior and (prior.amount_lkr != row.amount_lkr or prior.quantity != row.quantity or
                      prior.unit != row.unit):
            raise ValueError("conflicting value for existing source observation")
    added = [row for row in incoming if row.identity not in known]
    if not added:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps([row.model_dump(mode="json") for row in existing + added], indent=2), encoding="utf-8")
    pending.replace(path)
    return len(added)


def price_state(record: OfficialPriceObservation | None, *, as_of: date | None = None,
                fresh_days: int = 14) -> str:
    if record is None:
        return "missing"
    if record.evidence_status != "source_checked" or record.price_class != "retail":
        return "unverified_or_unusable"
    age = ((as_of or date.today()) - record.observation_end).days
    return "fresh_reference" if 0 <= age <= fresh_days else "historical_reference"


def indicative_reference_cost(record: OfficialPriceObservation, quantity: Decimal, unit: str) -> Decimal:
    """Scale a published commodity price; this is not a serving recommendation."""
    scales = {"g": ("mass", Decimal("1")), "kg": ("mass", Decimal("1000")),
              "ml": ("volume", Decimal("1")), "l": ("volume", Decimal("1000")),
              "piece": ("count", Decimal("1")), "bunch": ("bunch", Decimal("1")),
              "serving": ("serving", Decimal("1"))}
    if quantity <= 0 or unit not in scales or scales[unit][0] != scales[record.unit][0]:
        raise ValueError("quantity must be positive and unit compatible with published price")
    return record.amount_lkr * quantity * scales[unit][1] / (record.quantity * scales[record.unit][1])


def catalog_from_history(history: list[OfficialPriceObservation], *, as_of: date | None = None,
                         fresh_days: int = 14) -> list[FoodResource]:
    """Price-bearing catalog with local availability deliberately unknown."""
    usable = {}
    for record in history:
        if price_state(record, as_of=as_of, fresh_days=fresh_days) in ("fresh_reference", "historical_reference"):
            previous = usable.get(record.food_id)
            if previous is None or (record.observation_end, record.imported_at) > (previous.observation_end, previous.imported_at):
                usable[record.food_id] = record
    catalog = []
    for food in FOODS:
        record = usable.get(food.food_id)
        price = None
        if record:
            price = Price(amount_lkr=record.amount_lkr, quantity=record.quantity, unit=record.unit,
                          evidence=Evidence(kind="verified_source", source=record.report_url,
                                            observed_on=record.observation_end),
                          reference_kind="official_indicative", market_coverage=record.market_coverage,
                          source_locator=record.source_locator,
                          reference_status=price_state(record, as_of=as_of, fresh_days=fresh_days))
        catalog.append(FoodResource(food_id=food.food_id, name=food.name, food_group=food.group,
                                    price=price, locally_available=None, availability_evidence=None))
    return catalog


def bundled_history() -> list[OfficialPriceObservation]:
    return import_csv((Path(__file__).parent / "data" / "dcs_2026_10_w1.csv.txt").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh C2 price history from a reviewed official-report CSV")
    parser.add_argument("--reviewed-csv", type=Path, required=True,
                        help="CSV transcription checked against the official PDF/spreadsheet")
    parser.add_argument("--history", type=Path, required=True,
                        help="append-only JSON history outside the repository")
    args = parser.parse_args()
    added = refresh(args.history, lambda: args.reviewed_csv.read_text(encoding="utf-8"))
    print(json.dumps({"added": added, "history_records": len(read_history(args.history)),
                      "history_path": str(args.history)}))


if __name__ == "__main__":
    main()
