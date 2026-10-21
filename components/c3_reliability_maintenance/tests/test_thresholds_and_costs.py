import numpy as np
import pandas as pd

from component3.adapt.candidate import CandidateModel
from component3.adapt.thresholds import tune_threshold
from component3.assess.metrics import ece
from component3.config import ACTION_COST
from component3.experiments.strategies import STRATEGY_DECISION_FNS, periodic_retrain_decision
from component3.interfaces import ModelMetadata
from tests.test_decide import _monitoring, _reliability, THRESHOLDS


def test_tuned_threshold_reaches_target_sensitivity():
    rng = np.random.default_rng(0)
    y = (rng.random(2000) < 0.1).astype(int)
    p = np.clip(0.1 + 0.3 * y + rng.normal(0, 0.15, 2000), 0, 1)
    t = tune_threshold(y, p, min_sensitivity=0.8)
    assert ((p >= t) & (y == 1)).sum() / y.sum() >= 0.8


class _ConstantProba:
    def __init__(self, p):
        self.p = p

    def predict_proba(self, X):
        return np.column_stack([1 - self.p, self.p])

    def predict(self, X):
        return (self.p >= 0.5).astype(int)


def test_candidate_uses_decision_threshold_not_argmax():
    p = np.array([0.1, 0.2, 0.3, 0.6])
    meta = ModelMetadata(version="v1.0", classes=(0, 1), decision_threshold=0.25)
    model = CandidateModel(_ConstantProba(p), "v1.0", meta)
    assert model.predict(pd.DataFrame(index=range(4))).tolist() == [0, 0, 1, 1]


def test_binary_ece_detects_overconfident_risk_scores():
    y = np.array([0] * 90 + [1] * 10)
    overconfident = np.column_stack([np.full(100, 0.6), np.full(100, 0.4)])  # says 40% risk, true rate 10%
    assert ece(y, overconfident) > 0.25


def test_periodic_strategy_always_retrains_and_costs_most():
    decision = periodic_retrain_decision(_monitoring(False), _reliability(), THRESHOLDS)
    assert decision.action.value == "retrain"
    assert "periodic_retrain" in STRATEGY_DECISION_FNS
    assert ACTION_COST["retrain"] == max(ACTION_COST.values())
