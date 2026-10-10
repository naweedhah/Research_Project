"""Exhaustive artificial design grid; never derived from child records."""
from .schemas import ChildFeatures


def synthetic_reference_points() -> tuple[tuple[int, int], ...]:
    return tuple((meals, diversity) for meals in range(1, 6) for diversity in range(0, 6))


def synthetic_child(meals: int, diversity: int) -> ChildFeatures:
    return ChildFeatures(age_months=24, sex="female", household_income_band="unknown",
                         meals_per_day=meals, dietary_diversity=diversity)
