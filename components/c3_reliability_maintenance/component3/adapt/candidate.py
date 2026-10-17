"""CandidateModel: a maintenance-generated model that has not yet been promoted (spec §13).

C3 never mutates the active model in place — every adaptation produces a new
candidate with explicit lineage back to its parent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from component3.interfaces import ModelMetadata


@dataclass(frozen=True)
class CandidateModel:
    """Wraps a fitted sklearn-compatible estimator to satisfy the ModelArtifact contract."""

    estimator: Any
    version: str
    metadata: ModelMetadata

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        threshold = self.metadata.decision_threshold
        classes = self.metadata.classes
        if threshold is not None and len(classes) == 2:
            positive = np.asarray(self.predict_proba(X))[:, 1] >= threshold
            return np.where(positive, classes[1], classes[0])
        return self.estimator.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.estimator.predict_proba(X)


def bump_version(version: str, action: str) -> str:
    """v1.0 -> v1.1 on recalibration, v1.x -> v2.0 on retraining (spec §13)."""
    major_str, _, minor_str = version.lstrip("v").partition(".")
    major, minor = int(major_str), int(minor_str or 0)
    if action == "retrain":
        return f"v{major + 1}.0"
    if action == "recalibrate":
        return f"v{major}.{minor + 1}"
    raise ValueError(f"unknown action for version bump: {action}")
