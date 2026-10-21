"""Invented profiles for repeatable, live C1 baseline and C2 scenario checks.

Names describe inputs only. Risk labels must come from genuine C1 responses.
No entry is an observed child record or a validated feeding recommendation.
"""

from .manual_c1_validation import ManualC1Request


_BASE = {
    "test_id": "TEST-0014", "age_months": 24, "sex": "Female",
    "height_cm": 80, "weight_kg": 10, "birth_weight_kg": 2.8,
    "household_size": 4, "maternal_age_years": 28,
    "maternal_education": "O/L passed",
    "household_income_range": "Rs.20,000 to Rs. 50,000",
    "father_occupation": "Manual worker", "mother_occupation": "Housewife",
    "exclusive_breastfeeding": "Yes",
    "breastfeeding_duration": "More than 6 months",
    "complementary_feeding_timing": "After 6 months",
    "meal_frequency": "3 meals/day", "dietary_diversity": "2 to 5 varieties",
    "triposha_supplementation": "No", "vitamin_supplementation": "Yes",
    "budget_lkr": "1500", "budget_period": "weekly",
}

# Input variation explores model behavior. It does not assign or guarantee an
# output category; C1 may return the same category for several profiles.
_CASES = (
    ("TEST-0014", "24-month reference", {}, ["rice and cereals"]),
    ("TEST-0015", "16-month lower measurements", {
        "age_months": 16, "height_cm": 74, "weight_kg": 7.7,
        "meal_frequency": "2 meals/day", "dietary_diversity": "Less than 2 varieties",
    }, ["rice and cereals"]),
    ("TEST-0016", "30-month varied feeding", {
        "age_months": 30, "sex": "Male", "height_cm": 87, "weight_kg": 12,
        "meal_frequency": "4+ meals/day", "dietary_diversity": "More than 5 varieties",
        "budget_lkr": "2200",
    }, ["rice and cereals", "pulses", "vegetables"]),
    ("TEST-0017", "10-month limited budget", {
        "age_months": 10, "height_cm": 69, "weight_kg": 7.5,
        "meal_frequency": "2 meals/day", "dietary_diversity": "Less than 2 varieties",
        "budget_lkr": "300",
    }, ["rice and cereals"]),
    ("TEST-0018", "42-month higher measurements", {
        "age_months": 42, "sex": "Male", "height_cm": 97, "weight_kg": 15,
        "meal_frequency": "4+ meals/day", "dietary_diversity": "More than 5 varieties",
    }, ["rice and cereals", "vegetables", "pulses"]),
    ("TEST-0019", "24-month recorded weight-history flag", {
        "historical_mam": False, "historical_sam": False,
        "historical_underweight": "Severe", "historical_stunting": "Normal",
        "meal_frequency": "2 meals/day", "dietary_diversity": "Less than 2 varieties",
    }, ["rice and cereals"]),
    ("TEST-0020", "24-month recorded acute-history flag", {
        "historical_mam": False, "historical_sam": True,
        "historical_underweight": "Normal", "historical_stunting": "Normal",
        "meal_frequency": "2 meals/day", "dietary_diversity": "Less than 2 varieties",
    }, ["rice and cereals"]),
    ("TEST-0021", "36-month higher measurements", {
        "age_months": 36, "sex": "Male", "height_cm": 100, "weight_kg": 17,
        "meal_frequency": "4+ meals/day", "dietary_diversity": "More than 5 varieties",
    }, ["rice and cereals", "vegetables", "pulses"]),
    ("TEST-0022", "24-month recorded height-history flag", {
        "historical_mam": False, "historical_sam": False,
        "historical_underweight": "Normal", "historical_stunting": "Severe",
    }, ["rice and cereals"]),
    ("TEST-0023", "8-month combined prior-status flags", {
        "age_months": 8, "height_cm": 66, "weight_kg": 6,
        "historical_mam": False, "historical_sam": True,
        "historical_underweight": "Severe", "historical_stunting": "Severe",
        "meal_frequency": "2 meals/day", "dietary_diversity": "Less than 2 varieties",
    }, ["rice and cereals"]),
)


def live_case_library() -> dict:
    cases = []
    for case_id, name, overrides, groups in _CASES:
        request = ManualC1Request.model_validate({**_BASE, **overrides, "test_id": case_id})
        cases.append({"case_id": case_id, "name": name,
                      "input": request.model_dump(mode="json"), "food_groups": groups})
    return {"contract_version": "c2-live-case-library-v2", "cases": cases,
            "provenance": "invented research test inputs; risk categories are not preassigned"}
