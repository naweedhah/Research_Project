"""Generic, non-malnutrition test fixtures — pure plumbing checks for C3 mechanics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from component3.interfaces import FeatureSchema

TOY_COLUMNS = [f"f{i}" for i in range(6)]


def toy_schema() -> FeatureSchema:
    return FeatureSchema.from_dicts([{"name": c, "kind": "numeric"} for c in TOY_COLUMNS])


def make_toy_data(n_samples: int = 600, seed: int = 0) -> tuple[pd.DataFrame, np.ndarray]:
    X, y = make_classification(
        n_samples=n_samples,
        n_features=len(TOY_COLUMNS),
        n_informative=4,
        n_redundant=0,
        n_classes=3,
        n_clusters_per_class=1,
        weights=[0.6, 0.3, 0.1],
        random_state=seed,
    )
    return pd.DataFrame(X, columns=TOY_COLUMNS), y


def model_factory() -> Pipeline:
    """NaN-tolerant so it survives the missingness/feature-unavailable stress scenarios.

    Imputation is a modeling choice made by whoever supplies `model_factory` to C3 —
    C3 itself stays agnostic to it.
    """
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
