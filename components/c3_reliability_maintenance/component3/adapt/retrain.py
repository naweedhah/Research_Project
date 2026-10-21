"""Retraining action (spec §11, Action 3): the more consequential maintenance option.

`model_factory` returns an unfitted sklearn-compatible estimator so C3 stays
model-family-agnostic (logistic regression, Random Forest, XGBoost, CatBoost per
spec §4.4 are all valid factories).
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from component3.adapt.candidate import CandidateModel
from component3.adapt.thresholds import tune_threshold
from component3.interfaces import FeatureSchema, ModelMetadata


def fit_with_threshold(
    model_factory: Callable[[], object],
    X: pd.DataFrame,
    y: np.ndarray,
    operating_sensitivity: float = 0.80,
    seed: int = 0,
) -> tuple[object, float | None]:
    """Fits a model; for binary targets, tunes the operating threshold on a held-out 25% of the data and then refits
    on all of it, so the threshold is never chosen on the rows the final model was fitted to."""
    y = np.asarray(y)
    classes = np.unique(y)
    threshold = None
    if len(classes) == 2 and min(np.sum(y == c) for c in classes) >= 8:
        X_fit, X_tune, y_fit, y_tune = train_test_split(X, y, test_size=0.25, stratify=y, random_state=seed)
        probe = model_factory()
        probe.fit(X_fit, y_fit)
        threshold = tune_threshold((y_tune == classes[1]).astype(int), probe.predict_proba(X_tune)[:, 1],
                                   operating_sensitivity)
    estimator = model_factory()
    estimator.fit(X, y)
    return estimator, threshold


def generate_retrained_candidate(
    model_factory: Callable[[], object],
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    next_version: str,
    parent_version: str,
    schema: FeatureSchema | None = None,
    operating_sensitivity: float = 0.80,
) -> CandidateModel:
    estimator, threshold = fit_with_threshold(model_factory, X_train, y_train, operating_sensitivity)
    classes = getattr(estimator, "classes_", np.unique(y_train))

    metadata = ModelMetadata(
        version=next_version,
        classes=tuple(np.asarray(classes).tolist()),
        parent_version=parent_version,
        action="retrain",
        schema=schema,
        decision_threshold=threshold,
    )
    return CandidateModel(estimator=estimator, version=next_version, metadata=metadata)
