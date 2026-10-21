import pandas as pd
import pytest

from ml.preprocessing.pipeline import assert_early_risk_no_label_leak, assert_no_forbidden_columns, group_split, load_feature_sets
from pathlib import Path


def test_forbidden_identity_columns():
    frame = pd.DataFrame({"weight_kg": [8.1], "child_name": ["x"]})
    with pytest.raises(ValueError, match="Identity"):
        assert_no_forbidden_columns(frame)


def test_early_risk_rejects_status_label_leak():
    feature_sets = {
        "early_risk": {"forbidden_features": ["current_status_label", "current_whz"]},
        "current_status": {"forbidden_features": []},
    }
    frame = pd.DataFrame({"wealth_proxy": ["low"], "current_whz": [-2.1]})
    with pytest.raises(ValueError, match="leakage"):
        assert_early_risk_no_label_leak(frame, feature_sets)


def test_group_split_keeps_children_together():
    rows = []
    for child in ("A", "B", "C", "D"):
        for v in range(3):
            rows.append({"child_id": child, "status": "normal" if child != "A" else "wasting", "x": v})
    frame = pd.DataFrame(rows)
    train, test = group_split(frame, "child_id", "status", 0.25, 42)
    assert set(train["child_id"]).isdisjoint(set(test["child_id"]))
