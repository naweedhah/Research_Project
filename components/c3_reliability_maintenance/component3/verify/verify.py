"""Verification gate (spec §14): a candidate is scored only on data adaptation never touched.

A candidate is promoted only if it clears every predefined criterion. This is what
keeps C3 from becoming an uncontrolled automatic retraining system.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from component3.assess.metrics import classification_metrics
from component3.config import PromotionCriteria
from component3.interfaces import ModelArtifact


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    candidate_metrics: dict
    active_metrics: dict | None
    failures: tuple[str, ...]


def verify_candidate(
    candidate: ModelArtifact,
    X_verify: pd.DataFrame,
    y_verify: np.ndarray,
    criteria: PromotionCriteria,
    active_model: ModelArtifact | None = None,
) -> VerificationResult:
    classes = np.array(candidate.metadata.classes) if candidate.metadata.classes else np.unique(y_verify)
    y_arr = np.asarray(y_verify)

    cand_pred = np.asarray(candidate.predict(X_verify))
    cand_proba = np.asarray(candidate.predict_proba(X_verify))
    cand_metrics = classification_metrics(y_arr, cand_pred, cand_proba, classes)

    failures: list[str] = []

    if cand_metrics["recall_macro"] < criteria.min_recall_macro:
        failures.append(f"recall_macro={cand_metrics['recall_macro']:.3f}<{criteria.min_recall_macro}")
    if cand_metrics["ece"] > criteria.max_ece:
        failures.append(f"ece={cand_metrics['ece']:.3f}>{criteria.max_ece}")
    if cand_metrics["brier"] > criteria.max_brier:
        failures.append(f"brier={cand_metrics['brier']:.3f}>{criteria.max_brier}")

    if criteria.minority_classes:
        minority_recalls = [
            cand_metrics["recall_per_class"][c]
            for c in criteria.minority_classes
            if c in cand_metrics["recall_per_class"]
        ]
        if minority_recalls and min(minority_recalls) < criteria.min_minority_recall:
            failures.append(f"minority_recall={min(minority_recalls):.3f}<{criteria.min_minority_recall}")

    active_metrics = None
    if active_model is not None:
        active_pred = np.asarray(active_model.predict(X_verify))
        active_proba = np.asarray(active_model.predict_proba(X_verify))
        active_metrics = classification_metrics(y_arr, active_pred, active_proba, classes)
        regression = active_metrics["recall_macro"] - cand_metrics["recall_macro"]
        if regression > criteria.max_regression:
            failures.append(f"regression_vs_active={regression:.3f}>{criteria.max_regression}")

    return VerificationResult(
        passed=len(failures) == 0,
        candidate_metrics=cand_metrics,
        active_metrics=active_metrics,
        failures=tuple(failures),
    )
