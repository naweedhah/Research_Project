"""Recalibration action (spec §11, Action 2): fix probability calibration without retraining.

Implemented as per-class isotonic regression on the active model's predicted
probabilities. Only needs `predict_proba`, so it works against any ModelArtifact —
including a future real C1 model — without assuming its internal library.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from component3.adapt.candidate import CandidateModel
from component3.adapt.thresholds import tune_threshold
from component3.interfaces import ModelArtifact, ModelMetadata


class RecalibratedEstimator:
    def __init__(self, base_model: ModelArtifact, classes: np.ndarray, calibrators: dict[int, IsotonicRegression]):
        self.base_model = base_model
        self.classes_ = classes
        self._calibrators = calibrators

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raw = np.asarray(self.base_model.predict_proba(X))
        calibrated = np.column_stack(
            [self._calibrators[i].predict(raw[:, i]) for i in range(len(self.classes_))]
        )
        row_sums = calibrated.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return calibrated / row_sums

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]


def generate_recalibrated_candidate(
    active_model: ModelArtifact,
    X_adapt: pd.DataFrame,
    y_adapt: np.ndarray,
    next_version: str,
    operating_sensitivity: float = 0.80,
) -> CandidateModel:
    classes = np.array(active_model.metadata.classes) if active_model.metadata.classes else np.unique(y_adapt)
    raw_proba = np.asarray(active_model.predict_proba(X_adapt))
    y_arr = np.asarray(y_adapt)

    calibrators: dict[int, IsotonicRegression] = {}
    for i, c in enumerate(classes):
        binary_targets = (y_arr == c).astype(float)
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(raw_proba[:, i], binary_targets)
        calibrators[i] = iso

    estimator = RecalibratedEstimator(active_model, classes, calibrators)
    # Recalibration moves probabilities toward the observed prevalence, so the operating threshold is re-tuned on the
    # same adaptation data; otherwise a fixed (or argmax) threshold would silently stop flagging true cases.
    threshold = None
    if len(classes) == 2:
        threshold = tune_threshold((y_arr == classes[1]).astype(int), estimator.predict_proba(X_adapt)[:, 1],
                                   operating_sensitivity)
    metadata = ModelMetadata(
        version=next_version,
        classes=tuple(classes.tolist()),
        parent_version=active_model.version,
        action="recalibrate",
        schema=active_model.metadata.schema,
        decision_threshold=threshold,
    )
    return CandidateModel(estimator=estimator, version=next_version, metadata=metadata)
