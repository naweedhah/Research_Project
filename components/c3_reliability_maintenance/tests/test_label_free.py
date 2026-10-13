import numpy as np

from component3.decide.policy import MaintenanceAction
from component3.monitor.label_free import label_free_warning
from component3.orchestrator import C3Orchestrator
from tests.test_orchestrator import _setup


def test_urgency_levels():
    ref_p = np.column_stack([np.full(100, 0.9), np.full(100, 0.1)])
    ref = np.zeros(100)
    cur_high = np.r_[np.ones(20), np.zeros(80)]
    assert label_free_warning(ref_p, ref_p, ref, cur_high, 1, prediction_flagged=False)["urgency"] == "high"
    cur_med = np.r_[np.ones(6), np.zeros(94)]
    assert label_free_warning(ref_p, ref_p, ref, cur_med, 1, prediction_flagged=False)["urgency"] == "medium"
    assert label_free_warning(ref_p, ref_p, ref, ref, 1, prediction_flagged=False)["urgency"] == "low"
    assert label_free_warning(ref_p, ref_p, ref, ref, 1, prediction_flagged=True, context_heightened=True)["urgency"] == "high"


def test_hold_without_labels_reports_urgency():
    schema, X, y, initial, registry = _setup()
    shifted = X.copy()
    shifted["f0"] = shifted["f0"] + 3 * shifted["f0"].std()
    cycle = C3Orchestrator(registry, schema).run_cycle(reference_data=X, current_data=shifted, current_labels=None)
    assert cycle.decision.action == MaintenanceAction.HOLD
    assert "label-free urgency" in cycle.decision.reason
    assert cycle.decision.evidence["label_free_warning"]["urgency"] in {"high", "medium", "low"}
