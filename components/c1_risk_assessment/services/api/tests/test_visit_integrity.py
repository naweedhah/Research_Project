"""Seed case visit integrity checks."""

from app.seed import CASES, _validate_cases


def test_all_cases_have_at_least_three_visits():
    _validate_cases()
    for case in CASES:
        assert len(case["visits"]) >= 3, case["pid"]


def test_first_visit_is_baseline_and_dates_increase():
    _validate_cases()
    for case in CASES:
        visits = case["visits"]
        assert visits[0]["progress"] == "baseline"
        dates = [v["date"] for v in visits]
        assert dates == sorted(dates)
        assert len(set(dates)) == len(dates)
