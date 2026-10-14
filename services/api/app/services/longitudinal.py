"""Longitudinal risk metrics.

Risk Velocity:
    RV_t = (R_(t-1) - R_t) / elapsed_months

Positive RV indicates decreasing risk (improvement).
These functions never invent a clinically meaningful zero-tolerance;
callers supply stagnation_threshold from the active policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models.enums import ProgressState

DAYS_PER_MONTH = 30.4375


class LongitudinalError(ValueError):
    pass


def elapsed_months(start: datetime, end: datetime) -> float:
    delta_days = (end - start).total_seconds() / 86400.0
    if delta_days <= 0:
        raise LongitudinalError("Elapsed interval must be greater than zero days")
    return delta_days / DAYS_PER_MONTH


def risk_velocity(previous_risk: float, current_risk: float, months: float) -> float:
    if previous_risk is None or current_risk is None:
        raise LongitudinalError("Missing risk — velocity cannot be calculated")
    if months <= 0:
        raise LongitudinalError("Zero-day or negative interval is not a valid velocity denominator")
    return (previous_risk - current_risk) / months


def baseline_recovery_rate(baseline_risk: float, current_risk: float, months_from_baseline: float) -> float:
    if months_from_baseline <= 0:
        raise LongitudinalError("Zero-day or negative interval from baseline is not valid")
    return (baseline_risk - current_risk) / months_from_baseline


@dataclass
class ProgressEvaluation:
    progress_state: ProgressState
    risk_velocity: float | None
    baseline_recovery_rate: float | None
    elapsed_months: float | None
    warning: str | None = None


def classify_progress(
    *,
    is_baseline: bool,
    previous_risk: float | None,
    current_risk: float,
    baseline_risk: float | None,
    months: float | None,
    months_from_baseline: float | None,
    stagnation_threshold: float,
    deterioration_delta: float,
    consecutive_near_zero: int,
    consecutive_required: int,
    model_compatible: bool,
) -> ProgressEvaluation:
    if is_baseline:
        return ProgressEvaluation(ProgressState.BASELINE, None, None, None)
    if not model_compatible:
        return ProgressEvaluation(
            ProgressState.INCOMPATIBLE_MODEL,
            None,
            None,
            months,
            warning="Model version changed — latent trajectory restarted/re-aligned",
        )
    if previous_risk is None or months is None:
        return ProgressEvaluation(ProgressState.UNKNOWN, None, None, months, warning="Missing risk — velocity not calculated")

    rv = risk_velocity(previous_risk, current_risk, months)
    brr = None
    if baseline_risk is not None and months_from_baseline and months_from_baseline > 0:
        brr = baseline_recovery_rate(baseline_risk, current_risk, months_from_baseline)

    delta = current_risk - previous_risk
    if delta >= deterioration_delta:
        state = ProgressState.DETERIORATING
    elif consecutive_near_zero >= consecutive_required and abs(rv) <= stagnation_threshold:
        state = ProgressState.STAGNATING
    elif rv > stagnation_threshold:
        state = ProgressState.IMPROVING
    elif abs(rv) <= stagnation_threshold:
        state = ProgressState.STABLE
    else:
        state = ProgressState.DETERIORATING
    return ProgressEvaluation(state, rv, brr, months)
