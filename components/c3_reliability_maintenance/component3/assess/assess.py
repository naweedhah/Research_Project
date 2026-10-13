"""Assess stage: does a detected shift actually threaten model reliability? (spec §10)

Distinguishes the delayed-label reality explicitly: with no labels yet, this module
never claims degradation, only that outcome-based verification is pending.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from component3.assess.metrics import classification_metrics
from component3.config import Thresholds
from component3.interfaces import ModelArtifact

ReliabilityStatus = str  # "evaluated" | "pending_labels"


@dataclass(frozen=True)
class ReliabilityReport:
    status: ReliabilityStatus
    metrics: dict | None
    discrimination_ok: bool | None
    calibration_ok: bool | None
    minority_ok: bool | None

    @property
    def reliable(self) -> bool | None:
        if self.status == "pending_labels":
            return None
        return bool(self.discrimination_ok and self.calibration_ok and self.minority_ok)


def assess_reliability(
    model: ModelArtifact,
    X: pd.DataFrame,
    y: np.ndarray | None,
    thresholds: Thresholds,
) -> ReliabilityReport:
    if y is None:
        return ReliabilityReport(status="pending_labels", metrics=None, discrimination_ok=None, calibration_ok=None, minority_ok=None)

    y_proba = model.predict_proba(X)
    y_pred = model.predict(X)
    classes = np.array(model.metadata.classes) if model.metadata.classes else np.unique(y)

    metrics = classification_metrics(np.asarray(y), np.asarray(y_pred), np.asarray(y_proba), classes)

    discrimination_ok = metrics["recall_macro"] >= thresholds.reliability_tau
    calibration_ok = metrics["ece"] <= thresholds.calibration_tau

    minority_ok = True
    if thresholds.minority_classes:
        minority_recalls = [
            metrics["recall_per_class"].get(c, 0.0) for c in thresholds.minority_classes if c in metrics["recall_per_class"]
        ]
        if minority_recalls:
            minority_ok = min(minority_recalls) >= thresholds.min_minority_recall

    return ReliabilityReport(
        status="evaluated",
        metrics=metrics,
        discrimination_ok=discrimination_ok,
        calibration_ok=calibration_ok,
        minority_ok=minority_ok,
    )
