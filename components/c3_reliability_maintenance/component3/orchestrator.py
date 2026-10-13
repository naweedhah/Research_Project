"""The closed loop (spec §8-15): Monitor -> Assess -> Decide -> Adapt -> Verify -> Promote/Reject.

`C3Orchestrator.run_cycle` is the single entry point experiments and any future
dashboard call — it bundles every intermediate report into one `CycleReport`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from component3.adapt.candidate import CandidateModel, bump_version
from component3.adapt.recalibrate import generate_recalibrated_candidate
from component3.adapt.retrain import generate_retrained_candidate
from component3.assess.assess import ReliabilityReport, assess_reliability
from component3.config import PromotionCriteria, Thresholds
from component3.context.signals import ContextReport
from component3.decide.policy import Decision, MaintenanceAction, decide
from component3.interfaces import FeatureSchema
from component3.monitor.monitor import MonitoringReport, run_monitoring
from component3.registry.registry import ModelRegistry
from component3.verify.verify import VerificationResult, verify_candidate

DecisionFn = Callable[[MonitoringReport, ReliabilityReport, Thresholds, "int | None"], Decision]


@dataclass(frozen=True)
class CycleReport:
    monitoring: MonitoringReport
    reliability: ReliabilityReport
    decision: Decision
    candidate: CandidateModel | None
    verification: VerificationResult | None
    promoted: bool
    context: ContextReport | None = None


class C3Orchestrator:
    def __init__(
        self,
        registry: ModelRegistry,
        schema: FeatureSchema,
        thresholds: Thresholds | None = None,
        criteria: PromotionCriteria | None = None,
        decision_fn: DecisionFn = decide,
    ):
        self.registry = registry
        self.schema = schema
        self.thresholds = thresholds or Thresholds()
        self.criteria = criteria or PromotionCriteria()
        self.decision_fn = decision_fn

    def run_cycle(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        current_labels: np.ndarray | None = None,
        adapt_data: pd.DataFrame | None = None,
        adapt_labels: np.ndarray | None = None,
        verify_data: pd.DataFrame | None = None,
        verify_labels: np.ndarray | None = None,
        model_factory: Callable[[], object] | None = None,
        retrain_history: tuple[pd.DataFrame, np.ndarray] | None = None,
        context: ContextReport | None = None,
    ) -> CycleReport:
        """`retrain_history` (optional): earlier labelled data to train on together with the new adaptation data
        when retraining, as a rolling window would. Recalibration always uses the new adaptation data only.

        `context` (optional): external signals (disasters, food prices, inflation). While an alert is active, drift
        thresholds are tightened for this cycle and the signals are recorded as possible causes. Context never changes
        the decision rules or triggers maintenance by itself."""
        active = self.registry.active_model

        reference_predictions = active.predict(reference_data) if len(reference_data) else None
        current_predictions = active.predict(current_data) if len(current_data) else None

        monitor_thresholds = context.adjust(self.thresholds) if context is not None else self.thresholds
        monitoring = run_monitoring(
            reference_data, current_data, self.schema, monitor_thresholds, reference_predictions, current_predictions
        )
        reliability = assess_reliability(active, current_data, current_labels, self.thresholds)
        n_labeled = None if current_labels is None else len(current_labels)
        decision = self.decision_fn(monitoring, reliability, self.thresholds, n_labeled)
        if context is not None:
            decision.evidence["context"] = context.as_evidence()
            if monitoring.any_flagged and context.signals:
                decision.evidence["possible_causes"] = context.possible_causes()

        candidate: CandidateModel | None = None
        verification: VerificationResult | None = None
        promoted = False

        if decision.action == MaintenanceAction.RECALIBRATE:
            if adapt_data is None or adapt_labels is None:
                raise ValueError("RECALIBRATE decision requires adapt_data and adapt_labels")
            next_version = bump_version(active.version, "recalibrate")
            candidate = generate_recalibrated_candidate(
                active, adapt_data, adapt_labels, next_version, self.thresholds.operating_sensitivity
            )

        elif decision.action == MaintenanceAction.RETRAIN:
            if adapt_data is None or adapt_labels is None or model_factory is None:
                raise ValueError("RETRAIN decision requires adapt_data, adapt_labels and model_factory")
            next_version = bump_version(active.version, "retrain")
            X_train, y_train = adapt_data, adapt_labels
            if retrain_history is not None:
                X_train = pd.concat([retrain_history[0], adapt_data], ignore_index=True)
                y_train = np.concatenate([np.asarray(retrain_history[1]), np.asarray(adapt_labels)])
            candidate = generate_retrained_candidate(
                model_factory, X_train, y_train, next_version, active.version, self.schema,
                self.thresholds.operating_sensitivity,
            )

        if candidate is not None:
            if verify_data is None or verify_labels is None:
                raise ValueError("a candidate was generated but no verify_data/verify_labels were supplied")
            verification = verify_candidate(candidate, verify_data, verify_labels, self.criteria, active_model=active)
            if verification.passed:
                self.registry.promote(candidate, verification)
                promoted = True
            else:
                self.registry.reject(candidate, verification, reason="failed verification gate")

        return CycleReport(
            monitoring=monitoring,
            reliability=reliability,
            decision=decision,
            candidate=candidate,
            verification=verification,
            promoted=promoted,
            context=context,
        )
