from datetime import datetime
from math import isfinite

from app.services.longitudinal import (
    LongitudinalError,
    baseline_recovery_rate,
    classify_progress,
    elapsed_months,
    monthly_velocity_available,
    risk_velocity,
)
from app.models.enums import ProgressState
import pytest


def test_improving_velocity():
    rv = risk_velocity(previous_risk=0.80, current_risk=0.60, months=1)
    assert rv == pytest.approx(0.20)


def test_deteriorating_velocity():
    rv = risk_velocity(previous_risk=0.60, current_risk=0.72, months=1)
    assert rv == pytest.approx(-0.12)


def test_zero_day_interval_rejected():
    with pytest.raises(LongitudinalError):
        risk_velocity(0.5, 0.4, months=0)


def test_same_calendar_date_does_not_calculate_monthly_velocity():
    start = datetime(2026, 10, 14, 9, 0, 0)
    end = datetime(2026, 10, 14, 16, 30, 0)
    with pytest.raises(LongitudinalError):
        elapsed_months(start, end)
    assert monthly_velocity_available(
        previous_date=start,
        current_date=end,
        stored_elapsed_days=0,
        risk_velocity_value=-4.517,
    ) is False


def test_positive_elapsed_interval_calculates_finite_monthly_velocity():
    months = elapsed_months(datetime(2026, 9, 14, 9, 0, 0), datetime(2026, 10, 14, 9, 0, 0))
    rv = risk_velocity(previous_risk=0.83, current_risk=0.88, months=months)
    assert months > 0
    assert isfinite(rv)
    assert rv == pytest.approx((0.83 - 0.88) / months)
    assert monthly_velocity_available(
        previous_date=datetime(2026, 9, 14, 9, 0, 0),
        current_date=datetime(2026, 10, 14, 9, 0, 0),
        stored_elapsed_days=30,
        risk_velocity_value=rv,
    ) is True


def test_non_finite_velocity_is_not_available():
    assert monthly_velocity_available(risk_velocity_value=float("inf"), stored_elapsed_days=30) is False
    assert monthly_velocity_available(risk_velocity_value=float("nan"), stored_elapsed_days=30) is False


def test_missing_risk_rejected():
    with pytest.raises(LongitudinalError):
        risk_velocity(None, 0.4, months=1)  # type: ignore[arg-type]


def test_baseline_recovery_rate():
    assert baseline_recovery_rate(0.82, 0.59, months_from_baseline=2) == pytest.approx((0.82 - 0.59) / 2)


def test_baseline_classification():
    result = classify_progress(
        is_baseline=True,
        previous_risk=None,
        current_risk=0.82,
        baseline_risk=0.82,
        months=None,
        months_from_baseline=None,
        stagnation_threshold=0.03,
        deterioration_delta=0.08,
        consecutive_near_zero=0,
        consecutive_required=2,
        model_compatible=True,
    )
    assert result.progress_state == ProgressState.BASELINE


def test_incompatible_model_does_not_draw_silent_trajectory():
    result = classify_progress(
        is_baseline=False,
        previous_risk=0.8,
        current_risk=0.6,
        baseline_risk=0.8,
        months=1,
        months_from_baseline=1,
        stagnation_threshold=0.03,
        deterioration_delta=0.08,
        consecutive_near_zero=0,
        consecutive_required=2,
        model_compatible=False,
    )
    assert result.progress_state == ProgressState.INCOMPATIBLE_MODEL
    assert "latent trajectory" in (result.warning or "").lower()
