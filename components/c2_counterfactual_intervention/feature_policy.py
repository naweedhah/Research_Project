"""Research-only feature policy. These values are test fixtures, not clinical rules."""
from .schemas import ChildFeatures, Change, Feature

ACTIONABLE: tuple[Feature, ...] = ("meals_per_day", "dietary_diversity")
CONTEXTUAL = frozenset({"household_income_band", "supplement_access", "supplement_programme_eligible", "supplement_clinically_suitable", "available", "practical", "age_suitable", "eligible", "clinically_suitable", "transition_justified", "budget_units"})
HISTORICAL = frozenset({"birth_weight_kg", "historical_exclusive_breastfeeding"})
IMMUTABLE = frozenset({"age_months", "sex"})
OBSERVED_NON_ACTIONABLE = frozenset({"supplement_use"})
TEST_COST_UNITS = {"meals_per_day": 2, "dietary_diversity": 3}


def next_values(child: ChildFeatures, feature: Feature) -> tuple[int | bool, ...]:
    value = getattr(child, feature)
    return (value + 1,) if value < 5 else ()


def validate_changes(child: ChildFeatures, changes: tuple[Change, ...]) -> list[str]:
    reasons: list[str] = []
    seen: set[str] = set()
    for change in changes:
        if change.feature not in ACTIONABLE:
            reasons.append(f"{change.feature}: protected feature")
            continue
        if change.feature in seen:
            reasons.append(f"{change.feature}: duplicate change")
        seen.add(change.feature)
        current = getattr(child, change.feature, None)
        if (type(change.from_value) is not int or type(change.to_value) is not int
                or change.from_value != current or change.to_value not in next_values(child, change.feature)):
            reasons.append(f"{change.feature}: invalid transition")
    if not 1 <= len(changes) <= 2:
        reasons.append("candidate must change one or two features")
    return reasons
