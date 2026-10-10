"""Conservative food feasibility: unknown mandatory evidence remains unresolved."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .food_resources import Evidence, FoodAlternative, FoodPlanningContext


@dataclass(frozen=True)
class FoodAssessment:
    status: str
    reasons: tuple[str, ...]
    cost_lkr: Decimal | None
    affordability: str
    availability: str


def _evidence_ok(evidence: Evidence | None, mode: str, label: str, unresolved: list[str]) -> bool:
    if evidence is None:
        unresolved.append(f"{label}: evidence missing")
        return False
    if evidence.observed_on > date.today():
        unresolved.append(f"{label}: observation date is in the future")
        return False
    if mode == "real" and evidence.kind == "synthetic_test":
        unresolved.append(f"{label}: synthetic test evidence cannot verify real planning")
        return False
    return True


def assess_food_alternative(alternative: FoodAlternative, planning: FoodPlanningContext,
                            mode: str) -> FoodAssessment:
    rejected: list[str] = []
    unresolved: list[str] = []
    _evidence_ok(alternative.practice_evidence, mode, "feeding practice", unresolved)
    if alternative.practice_reviewed is False:
        rejected.append("feeding practice not approved")
    elif alternative.practice_reviewed is None:
        unresolved.append("feeding practice approval unknown")
    _evidence_ok(alternative.suitability_evidence, mode, "suitability", unresolved)
    for name in ("age_suitable", "clinically_suitable", "caregiver_practical"):
        value = getattr(alternative, name)
        if value is False:
            rejected.append(f"{name}: false")
        elif value is None:
            unresolved.append(f"{name}: unknown")
    if alternative.programme_required:
        _evidence_ok(alternative.programme_evidence, mode, "programme eligibility", unresolved)
        if alternative.programme_eligible is False:
            rejected.append("programme_eligible: false")
        elif alternative.programme_eligible is None:
            unresolved.append("programme_eligible: unknown")
    catalog = {food.food_id: food for food in planning.catalog}
    total = Decimal("0")
    cost_known = True
    availability = "available"
    for proposal in alternative.foods:
        food = catalog.get(proposal.food_id)
        if food is None:
            unresolved.append(f"{proposal.food_id}: food resource missing")
            cost_known = False
            availability = "unknown"
            continue
        if food.locally_available is False:
            rejected.append(f"{food.food_id}: locally unavailable")
            availability = "unavailable"
        elif food.locally_available is None:
            unresolved.append(f"{food.food_id}: local availability unknown")
            if availability != "unavailable":
                availability = "unknown"
        if not _evidence_ok(food.availability_evidence, mode, f"{food.food_id} availability", unresolved):
            if availability != "unavailable":
                availability = "unknown"
        if food.price is None:
            unresolved.append(f"{food.food_id}: price unknown")
            cost_known = False
            continue
        if not _evidence_ok(food.price.evidence, mode, f"{food.food_id} price", unresolved):
            cost_known = False
        if proposal.unit != food.price.unit:
            rejected.append(f"{food.food_id}: quantity and price units differ; conversion not supplied")
            cost_known = False
            continue
        total += proposal.quantity * food.price.amount_lkr / food.price.quantity
    budget = planning.budget
    affordability = "unknown"
    if budget.period != alternative.period:
        unresolved.append("budget and proposal periods differ")
    elif budget.amount_lkr is None:
        unresolved.append("food budget unknown")
    elif not _evidence_ok(budget.evidence, mode, "food budget", unresolved):
        pass
    elif cost_known:
        if total > budget.amount_lkr:
            rejected.append("incremental cost exceeds supplied food budget")
            affordability = "unaffordable"
        else:
            affordability = "affordable"
    cost = total if cost_known else None
    status = "rejected" if rejected else "unresolved" if unresolved else "feasible"
    return FoodAssessment(status, tuple(rejected + unresolved), cost, affordability, availability)
