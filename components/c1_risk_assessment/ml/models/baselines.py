from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier


def build_random_forest(**params):
    return RandomForestClassifier(random_state=params.pop("random_state", 42), **params)


def build_xgboost(**params):
    from xgboost import XGBClassifier

    return XGBClassifier(random_state=params.pop("random_state", 42), eval_metric="mlogloss", **params)


def build_lightgbm(**params):
    from lightgbm import LGBMClassifier

    return LGBMClassifier(random_state=params.pop("random_state", 42), verbose=-1, **params)
