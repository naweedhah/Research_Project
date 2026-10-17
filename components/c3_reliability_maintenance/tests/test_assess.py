import numpy as np

from component3.assess.assess import assess_reliability
from component3.assess.metrics import brier_score_multiclass, classification_metrics, ece
from component3.config import Thresholds
from component3.interfaces import ModelMetadata
from tests.helpers import make_toy_data, model_factory


def test_ece_is_low_for_well_calibrated_predictions():
    rng = np.random.default_rng(0)
    n = 2000
    y_proba_pos = rng.uniform(0, 1, size=n)
    y_true = (rng.uniform(0, 1, size=n) < y_proba_pos).astype(int)
    y_proba = np.column_stack([1 - y_proba_pos, y_proba_pos])
    assert ece(y_true, y_proba, n_bins=10) < 0.05


def test_ece_is_high_for_overconfident_predictions():
    n = 500
    y_true = np.zeros(n, dtype=int)
    y_true[: n // 2] = 1
    # Always confidently predicts class 1 regardless of truth.
    y_proba = np.tile(np.array([0.02, 0.98]), (n, 1))
    assert ece(y_true, y_proba, n_bins=10) > 0.3


def test_brier_score_perfect_predictions_is_zero():
    y_true = np.array([0, 1, 2])
    y_proba = np.eye(3)[y_true]
    assert brier_score_multiclass(y_true, y_proba, n_classes=3) == 0.0


def test_brier_score_uniform_guess_matches_hand_computation():
    y_true = np.array([0])
    y_proba = np.array([[1 / 3, 1 / 3, 1 / 3]])
    expected = (2 / 3) ** 2 + (1 / 3) ** 2 + (1 / 3) ** 2
    assert np.isclose(brier_score_multiclass(y_true, y_proba, n_classes=3), expected)


def test_classification_metrics_has_expected_keys():
    X, y = make_toy_data()
    model = model_factory().fit(X, y)
    classes = model.classes_
    metrics = classification_metrics(y, model.predict(X), model.predict_proba(X), classes)
    for key in ("f1_macro", "recall_macro", "recall_per_class", "auroc", "auprc", "ece", "brier"):
        assert key in metrics


class _Wrapped:
    def __init__(self, estimator, classes):
        self.version = "v1.0"
        self.metadata = ModelMetadata(version="v1.0", classes=tuple(classes.tolist()))
        self._estimator = estimator

    def predict(self, X):
        return self._estimator.predict(X)

    def predict_proba(self, X):
        return self._estimator.predict_proba(X)


def test_assess_reliability_pending_when_no_labels():
    X, y = make_toy_data()
    estimator = model_factory().fit(X, y)
    model = _Wrapped(estimator, estimator.classes_)
    report = assess_reliability(model, X, None, Thresholds())
    assert report.status == "pending_labels"
    assert report.reliable is None


def test_assess_reliability_evaluated_with_labels():
    X, y = make_toy_data()
    estimator = model_factory().fit(X, y)
    model = _Wrapped(estimator, estimator.classes_)
    report = assess_reliability(model, X, y, Thresholds())
    assert report.status == "evaluated"
    assert report.metrics is not None
    assert report.reliable in (True, False)
