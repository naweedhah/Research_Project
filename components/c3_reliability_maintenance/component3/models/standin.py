"""Stand-in for the C1 model while the final C1 model is being retrained on the real linked data.

Gradient-boosted trees, like the best model in C1's own benchmark (LightGBM), with class-balanced weights and
sigmoid (Platt) calibration. Missing
values are handled natively, so missing-data stress tests exercise the model rather than an imputer. Any model with
fit / predict_proba can replace it through the same factory interface.
"""

from __future__ import annotations

from typing import Callable

from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def standin_factory(numeric: list[str], categorical: list[str], seed: int = 0) -> Callable[[], Pipeline]:
    def make() -> Pipeline:
        pre = ColumnTransformer([
            ("num", "passthrough", numeric),
            ("cat", Pipeline([
                ("fill", SimpleImputer(strategy="constant", fill_value="Missing")),
                ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=10, sparse_output=False)),
            ]), categorical),
        ])
        trees = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150,
                                               class_weight="balanced", random_state=seed)
        # Class weighting inflates probabilities; a deployed clinical model is calibrated (as C1's is), so the
        # stand-in is too. Otherwise C3 would flag miscalibration that existed from day one.
        model = CalibratedClassifierCV(trees, method="sigmoid", cv=3)
        return Pipeline([("pre", pre), ("model", model)])

    return make
