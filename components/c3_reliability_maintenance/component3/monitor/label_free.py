"""Label-free warning: an early estimate of risk while outcome labels are still pending.

Labels for a 12-month prediction arrive a year later, so a shift often has to be judged without them. The model's own
outputs still move: if the average predicted risk or the share of children flagged changes sharply, the population
(or the data) has changed in a way the model reacts to. This ranks how urgently a Hold needs human review; it never
replaces outcome-based assessment.
"""

from __future__ import annotations

import numpy as np

HIGH_RATE_CHANGE = 0.10    # absolute change in the share of children flagged
MEDIUM_RATE_CHANGE = 0.05


def label_free_warning(ref_proba: np.ndarray, cur_proba: np.ndarray, ref_pred: np.ndarray, cur_pred: np.ndarray,
                       positive_class, prediction_flagged: bool, context_heightened: bool = False) -> dict:
    ref_rate = float(np.mean(np.asarray(ref_pred) == positive_class))
    cur_rate = float(np.mean(np.asarray(cur_pred) == positive_class))
    change = cur_rate - ref_rate
    ref_risk = float(np.mean(np.asarray(ref_proba)[:, -1]))
    cur_risk = float(np.mean(np.asarray(cur_proba)[:, -1]))
    if abs(change) >= HIGH_RATE_CHANGE or (prediction_flagged and context_heightened):
        urgency = "high"
    elif abs(change) >= MEDIUM_RATE_CHANGE or prediction_flagged:
        urgency = "medium"
    else:
        urgency = "low"
    return {"flagged_rate_reference": round(ref_rate, 3), "flagged_rate_current": round(cur_rate, 3),
            "flagged_rate_change": round(change, 3), "mean_risk_reference": round(ref_risk, 3),
            "mean_risk_current": round(cur_risk, 3), "urgency": urgency}
