"""The maintenance strategies compared in spec §16, plus scheduled (periodic) retraining as a common baseline.

Strategies A-C and periodic retraining are fixed policies that bypass reliability-based gating; Strategy D
("adaptive") is simply the real decision policy from `component3.decide`. All four
share the same Monitor/Adapt/Verify/Promote machinery via `C3Orchestrator`'s
pluggable `decision_fn`, so the comparison isolates the effect of the decision logic.
"""

from __future__ import annotations

from component3.assess.assess import ReliabilityReport
from component3.config import Thresholds
from component3.decide.policy import Decision, MaintenanceAction, decide
from component3.interfaces import FeatureSchema
from component3.monitor.monitor import MonitoringReport
from component3.orchestrator import C3Orchestrator
from component3.registry.registry import ModelRegistry


def static_decision(monitoring: MonitoringReport, reliability: ReliabilityReport, thresholds: Thresholds, n_labeled=None) -> Decision:
    return Decision(
        MaintenanceAction.NO_ACTION,
        "static strategy: model is never updated",
        {"any_shift_flagged": monitoring.any_flagged},
    )


def always_recalibrate_decision(monitoring: MonitoringReport, reliability: ReliabilityReport, thresholds: Thresholds, n_labeled=None) -> Decision:
    if monitoring.any_flagged:
        return Decision(MaintenanceAction.RECALIBRATE, "always-recalibrate strategy: shift flagged", {"any_shift_flagged": True})
    return Decision(MaintenanceAction.NO_ACTION, "always-recalibrate strategy: no shift flagged", {"any_shift_flagged": False})


def always_retrain_decision(monitoring: MonitoringReport, reliability: ReliabilityReport, thresholds: Thresholds, n_labeled=None) -> Decision:
    if monitoring.any_flagged:
        return Decision(MaintenanceAction.RETRAIN, "always-retrain strategy: shift flagged", {"any_shift_flagged": True})
    return Decision(MaintenanceAction.NO_ACTION, "always-retrain strategy: no shift flagged", {"any_shift_flagged": False})


def periodic_retrain_decision(monitoring: MonitoringReport, reliability: ReliabilityReport, thresholds: Thresholds, n_labeled=None) -> Decision:
    """Scheduled maintenance: retrains every cycle regardless of drift or reliability (common industry baseline)."""
    return Decision(MaintenanceAction.RETRAIN, "periodic strategy: scheduled retraining", {"any_shift_flagged": monitoring.any_flagged})


STRATEGY_DECISION_FNS = {
    "static": static_decision,
    "periodic_retrain": periodic_retrain_decision,
    "always_recalibrate": always_recalibrate_decision,
    "always_retrain": always_retrain_decision,
    "adaptive": decide,
}


def build_orchestrator(
    strategy: str,
    registry: ModelRegistry,
    schema: FeatureSchema,
    thresholds: Thresholds | None = None,
    criteria=None,
    **orchestrator_options,
) -> C3Orchestrator:
    if strategy not in STRATEGY_DECISION_FNS:
        raise ValueError(f"unknown strategy '{strategy}', expected one of {list(STRATEGY_DECISION_FNS)}")
    return C3Orchestrator(
        registry=registry,
        schema=schema,
        thresholds=thresholds,
        criteria=criteria,
        decision_fn=STRATEGY_DECISION_FNS[strategy],
        **orchestrator_options,
    )
