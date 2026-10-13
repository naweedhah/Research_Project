"""Subgroup (fairness) reliability: does the model work for every group of children, not only on average?

A model can keep its overall accuracy while failing one group (e.g. infants, or one PHM area). C3 reports
per-group balanced accuracy and sensitivity, and the verification gate refuses a candidate that makes the
worst-off group clearly worse than the current model does.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import recall_score

GroupFn = Callable[[pd.DataFrame], pd.Series]
MIN_GROUP_SIZE = 20


def subgroup_metrics(y_true, y_pred, groups: pd.Series, classes, min_size: int = MIN_GROUP_SIZE) -> dict:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    groups = pd.Series(np.asarray(groups)).astype(str)
    per_group = {}
    for g in sorted(groups.unique()):
        m = (groups == g).to_numpy()
        if m.sum() < min_size or len(np.unique(y_true[m])) < 2:
            continue  # too small or one class only: not reliably measurable
        entry = {"n": int(m.sum()),
                 "bal_acc": float(recall_score(y_true[m], y_pred[m], labels=classes, average="macro", zero_division=0))}
        if len(classes) == 2:
            entry["sensitivity"] = float(recall_score(y_true[m], y_pred[m], pos_label=classes[1], zero_division=0))
        per_group[g] = entry
    if not per_group:
        return {"groups": {}, "worst_group": None, "worst_bal_acc": float("nan")}
    worst = min(per_group, key=lambda g: per_group[g]["bal_acc"])
    return {"groups": per_group, "worst_group": worst, "worst_bal_acc": per_group[worst]["bal_acc"]}


def sex_age_groups(sex_column: str = "Sex", age_column: str = "Age_months_2025") -> GroupFn:
    """Groups children by sex and age band (0-11, 12-23, 24-59 months)."""
    def _fn(frame: pd.DataFrame) -> pd.Series:
        band = pd.cut(pd.to_numeric(frame[age_column], errors="coerce"), [-1, 11, 23, 60],
                      labels=["0-11m", "12-23m", "24-59m"]).astype(str)
        return frame[sex_column].astype(str) + "/" + band
    return _fn
