"""Maintenance-effectiveness metrics (spec §20): recovery and intervention accounting."""

from __future__ import annotations

from component3.config import ACTION_COST
from component3.decide.policy import MaintenanceAction
from component3.orchestrator import CycleReport

_ACTED = (MaintenanceAction.RECALIBRATE, MaintenanceAction.RETRAIN)


def recovery(original: float, degraded: float, after: float, higher_is_better: bool = True) -> float:
    """(after - degraded) / (original - degraded), flipped for lower-is-better metrics
    such as calibration error, per spec §20."""
    denom = (original - degraded) if higher_is_better else (degraded - original)
    if denom == 0:
        return float("nan")
    numer = (after - degraded) if higher_is_better else (degraded - after)
    return numer / denom


def intervention_rate(cycles: list[CycleReport]) -> float:
    """Fraction of cycles where a maintenance action (recalibrate/retrain) was attempted."""
    if not cycles:
        return float("nan")
    acted = sum(1 for c in cycles if c.decision.action in _ACTED)
    return acted / len(cycles)


def unnecessary_intervention_rate(cycles: list[CycleReport]) -> float:
    """Among attempted interventions, the fraction taken while reliability was
    already acceptable at decision time (spec §11: unnecessary updates are a risk)."""
    acted = [c for c in cycles if c.decision.action in _ACTED]
    if not acted:
        return 0.0
    unnecessary = sum(1 for c in acted if c.reliability.status == "evaluated" and c.reliability.reliable)
    return unnecessary / len(acted)


def failed_adaptation_rate(cycles: list[CycleReport]) -> float:
    """Among cycles that generated a candidate, the fraction rejected at verification."""
    generated = [c for c in cycles if c.candidate is not None]
    if not generated:
        return float("nan")
    failed = sum(1 for c in generated if not c.promoted)
    return failed / len(generated)


def rollback_success_rate(reassessments: list[bool]) -> float:
    """Given one bool per rollback event — whether a later delayed-label reassessment
    confirmed reliability was restored — returns the fraction that succeeded."""
    if not reassessments:
        return float("nan")
    return sum(reassessments) / len(reassessments)


def mean_action_cost(cycles: list[CycleReport], costs: dict | None = None) -> float:
    """Average maintenance cost per cycle (ACTION_COST: no action 0 < hold < recalibrate < retrain)."""
    costs = costs or ACTION_COST
    if not cycles:
        return float("nan")
    return sum(costs[c.decision.action.value] for c in cycles) / len(cycles)
