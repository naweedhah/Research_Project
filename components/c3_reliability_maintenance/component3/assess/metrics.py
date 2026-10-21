"""Reliability metrics: predictive performance and calibration (spec §10)."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score, recall_score, roc_auc_score, average_precision_score


def ece(y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error per equal-width bin.

    Binary models: calibration of P(positive), the standard for risk scores. Top-label ECE is not used for them
    because, with a rare outcome, it hides overconfident risk estimates (most children fall in confident 'negative'
    bins). Multiclass models: top-label ECE, |accuracy - confidence|.
    """
    if y_proba.shape[1] == 2:
        p = y_proba[:, 1]
        y = (np.asarray(y_true) == 1).astype(float) if set(np.unique(y_true)) <= {0, 1} else None
        if y is not None:
            edges = np.linspace(0.0, 1.0, n_bins + 1)
            which = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
            total = 0.0
            for b in range(n_bins):
                in_bin = which == b
                if np.any(in_bin):
                    total += in_bin.mean() * abs(y[in_bin].mean() - p[in_bin].mean())
            return float(total)
    confidences = y_proba.max(axis=1)
    predictions = y_proba.argmax(axis=1)
    correct = (predictions == y_true).astype(float)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(y_true)
    total = 0.0
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        in_bin = (confidences > lo) & (confidences <= hi) if lo > 0 else (confidences >= lo) & (confidences <= hi)
        if not np.any(in_bin):
            continue
        bin_acc = correct[in_bin].mean()
        bin_conf = confidences[in_bin].mean()
        total += (in_bin.sum() / n) * abs(bin_acc - bin_conf)
    return float(total)


def brier_score_multiclass(y_true: np.ndarray, y_proba: np.ndarray, n_classes: int) -> float:
    """Multiclass Brier score: mean over samples of sum_c (p_c - one_hot_c)^2."""
    one_hot = np.zeros((len(y_true), n_classes))
    one_hot[np.arange(len(y_true)), y_true] = 1.0
    return float(np.mean(np.sum((y_proba - one_hot) ** 2, axis=1)))


def per_class_recall(y_true: np.ndarray, y_pred: np.ndarray, classes: np.ndarray) -> dict:
    scores = recall_score(y_true, y_pred, labels=classes, average=None, zero_division=0)
    return dict(zip(classes.tolist(), scores.tolist()))


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray, classes: np.ndarray) -> dict:
    metrics = {
        "f1_macro": float(f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, labels=classes, average="macro", zero_division=0)),
        "recall_per_class": per_class_recall(y_true, y_pred, classes),
    }
    try:
        if len(classes) == 2:
            metrics["auroc"] = float(roc_auc_score(y_true, y_proba[:, 1]))
            metrics["auprc"] = float(average_precision_score(y_true, y_proba[:, 1]))
        else:
            metrics["auroc"] = float(roc_auc_score(y_true, y_proba, labels=classes, multi_class="ovr", average="macro"))
            metrics["auprc"] = float(
                np.mean(
                    [
                        average_precision_score((y_true == c).astype(int), y_proba[:, i])
                        for i, c in enumerate(classes)
                    ]
                )
            )
    except ValueError:
        # e.g. a class absent from y_true in a small/synthetic sample
        metrics["auroc"] = float("nan")
        metrics["auprc"] = float("nan")

    metrics["ece"] = ece(y_true, y_proba)
    metrics["brier"] = brier_score_multiclass(y_true, y_proba, n_classes=len(classes))
    return metrics
