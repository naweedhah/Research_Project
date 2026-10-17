"""Operating-threshold selection for binary models.

A threshold is chosen to reach a target sensitivity (catching enough true cases), then to maximise balanced accuracy
among the thresholds that do. Used for the initial model and re-applied after every recalibration and retraining,
because recalibrating probabilities to the true prevalence would otherwise silently change which children are flagged.
"""

from __future__ import annotations

import numpy as np


def tune_threshold(y_true: np.ndarray, p_positive: np.ndarray, min_sensitivity: float = 0.80) -> float:
    y = np.asarray(y_true).astype(int)
    p = np.asarray(p_positive, dtype=float)
    if y.min() == y.max():
        return 0.5
    best, best_any = None, None
    for t in np.unique(np.round(p, 4)):
        pred = p >= t
        tp = np.sum(pred & (y == 1))
        fn = np.sum(~pred & (y == 1))
        tn = np.sum(~pred & (y == 0))
        fp = np.sum(pred & (y == 0))
        sens = tp / (tp + fn)
        spec = tn / (tn + fp) if (tn + fp) else 0.0
        bal = (sens + spec) / 2
        if best_any is None or bal > best_any[0]:
            best_any = (bal, t)
        if sens >= min_sensitivity and (best is None or bal > best[0]):
            best = (bal, t)
    return float((best or best_any)[1])
