import numpy as np
import pandas as pd

from component3.assess.subgroups import sex_age_groups, subgroup_metrics
from component3.config import PromotionCriteria
from component3.verify.verify import verify_candidate


def test_worst_group_is_identified():
    y = np.array([0, 1] * 40)
    pred = y.copy()
    groups = pd.Series(["A"] * 40 + ["B"] * 40)
    pred[40:] = 0  # model misses every positive in group B
    out = subgroup_metrics(y, pred, groups, np.array([0, 1]))
    assert out["worst_group"] == "B" and out["groups"]["B"]["sensitivity"] == 0.0


def test_sex_age_groups():
    frame = pd.DataFrame({"Sex": ["Male", "Female"], "Age_months_2025": [5, 40]})
    assert sex_age_groups()(frame).tolist() == ["Male/0-11m", "Female/24-59m"]


class _Fixed:
    def __init__(self, pred, version, classes=(0, 1)):
        from component3.interfaces import ModelMetadata
        self.pred, self.version = np.asarray(pred), version
        self.metadata = ModelMetadata(version=version, classes=classes)

    def predict(self, X):
        return self.pred

    def predict_proba(self, X):
        return np.column_stack([1 - self.pred, self.pred]).astype(float)


def test_candidate_that_fails_one_group_is_rejected():
    y = np.array([0, 1] * 40)
    groups = pd.Series(["A"] * 40 + ["B"] * 40)
    active = _Fixed(y, "v1.0")
    worse_for_b = y.copy()
    worse_for_b[40:] = 0
    criteria = PromotionCriteria(min_recall_macro=0.0, min_minority_recall=0.0, max_ece=1.0, max_brier=3.0,
                                 max_regression=1.0, max_worst_group_regression=0.05)
    result = verify_candidate(_Fixed(worse_for_b, "v1.1"), pd.DataFrame(index=range(80)), y, criteria,
                              active_model=active, groups=groups)
    assert not result.passed
    assert any("worst_group_regression" in f for f in result.failures)
