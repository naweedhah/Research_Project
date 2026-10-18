"""Age-specific weight and height limits for children 0–60 months.

Bounds follow WHO Child Growth Standards biologically implausible flags:
weight-for-age z < -6 or > +5, length/height-for-age z < -6 or > +6.
Combined-sex ranges so SAM and large-for-age children can still be recorded.
"""

from __future__ import annotations

KNOTS: list[tuple[float, float, float, float, float]] = [
    # age_months, min_kg, max_kg, min_cm, max_cm
    (0, 1.4, 6.2, 38, 62),
    (1, 2.0, 7.8, 43, 68),
    (2, 2.5, 9.0, 47, 72),
    (3, 2.9, 10.0, 50, 76),
    (4, 3.2, 10.8, 52, 78),
    (5, 3.5, 11.5, 54, 80),
    (6, 3.7, 12.2, 55, 83),
    (9, 4.3, 14.0, 59, 88),
    (12, 4.9, 15.6, 62, 93),
    (15, 5.3, 16.9, 65, 97),
    (18, 5.7, 18.2, 67, 101),
    (21, 6.1, 19.4, 69, 104),
    (24, 6.5, 20.6, 71, 107),
    (30, 7.2, 23.2, 74, 113),
    (36, 7.8, 25.8, 77, 118),
    (42, 8.4, 28.2, 80, 123),
    (48, 9.0, 30.6, 82, 127),
    (54, 9.5, 33.0, 84, 131),
    (60, 10.0, 35.0, 86, 135),
]

BMI_MIN = 8.5
BMI_MAX = 26.0


def bounds_for_age_months(age_months: float) -> dict[str, float]:
    age = min(60.0, max(0.0, age_months))
    for left, right in zip(KNOTS, KNOTS[1:]):
        if left[0] <= age <= right[0]:
            span = right[0] - left[0]
            t = 0.0 if span == 0 else (age - left[0]) / span
            return {
                "min_kg": round(left[1] + (right[1] - left[1]) * t, 1),
                "max_kg": round(left[2] + (right[2] - left[2]) * t, 1),
                "min_cm": round(left[3] + (right[3] - left[3]) * t),
                "max_cm": round(left[4] + (right[4] - left[4]) * t),
            }
    last = KNOTS[-1]
    return {"min_kg": last[1], "max_kg": last[2], "min_cm": last[3], "max_cm": last[4]}


def unusual_measurement_messages(age_months: float, weight_kg: float, height_cm: float) -> list[str]:
    bounds = bounds_for_age_months(age_months)
    age_label = str(int(age_months)) if float(age_months).is_integer() else f"{age_months:.1f}"
    issues: list[str] = []
    if weight_kg < bounds["min_kg"] or weight_kg > bounds["max_kg"]:
        issues.append(
            f"Weight {weight_kg} kg is not realistic for a child aged {age_label} months. "
            f"Expected about {bounds['min_kg']}–{bounds['max_kg']} kg at this age. "
            "Please verify this measurement before prediction."
        )
    if height_cm < bounds["min_cm"] or height_cm > bounds["max_cm"]:
        issues.append(
            f"Height {height_cm} cm is not realistic for a child aged {age_label} months. "
            f"Expected about {bounds['min_cm']}–{bounds['max_cm']} cm at this age. "
            "Please verify this measurement before prediction."
        )
    if height_cm >= 40:
        bmi = weight_kg / (height_cm / 100) ** 2
        if bmi < BMI_MIN or bmi > BMI_MAX:
            issues.append(
                f"Weight {weight_kg} kg with height {height_cm} cm does not match a realistic body size "
                "for this age. Check that weight is in kilograms and height is in centimetres. "
                "Please verify this measurement before prediction."
            )
    return issues
