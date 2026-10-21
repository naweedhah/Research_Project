from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FORBIDDEN = {
    "child_name",
    "caregiver_name",
    "phone",
    "national_id",
    "address",
    "external_patient_id",
    "clinical_notes",
}


def load_feature_sets(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def assert_no_forbidden_columns(frame: pd.DataFrame) -> None:
    overlap = FORBIDDEN.intersection(set(frame.columns))
    if overlap:
        raise ValueError(f"Identity / leakage columns present: {sorted(overlap)}")


def assert_early_risk_no_label_leak(frame: pd.DataFrame, feature_set: dict) -> None:
    forbidden = set(feature_set["early_risk"]["forbidden_features"])
    overlap = forbidden.intersection(set(frame.columns))
    if overlap:
        raise ValueError(f"Early-risk leakage features present: {sorted(overlap)}")


def group_split(frame: pd.DataFrame, group_col: str, label_col: str, test_size: float, seed: int):
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(frame, frame[label_col], groups=frame[group_col]))
    train, test = frame.iloc[train_idx], frame.iloc[test_idx]
    assert set(train[group_col]).isdisjoint(set(test[group_col])), "Child-level leakage across split"
    return train, test


def fit_preprocessor(train: pd.DataFrame, numeric: list[str], categorical: list[str]) -> Pipeline:
    numeric_pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical_pipe = Pipeline(
        [("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]
    )
    pre = ColumnTransformer([("num", numeric_pipe, numeric), ("cat", categorical_pipe, categorical)])
    pre.fit(train)
    return pre
