import numpy as np

from component3.config import Thresholds
from component3.orchestrator import C3Orchestrator
from tests.test_orchestrator import LENIENT, _setup


def _cycle(require_approval):
    schema, X, y, initial, registry = _setup(seed=1)
    orch = C3Orchestrator(registry, schema, thresholds=Thresholds(reliability_tau=0.0, calibration_tau=-1.0),
                          criteria=LENIENT, require_approval=require_approval)
    cycle = orch.run_cycle(reference_data=X, current_data=X, current_labels=y, adapt_data=X, adapt_labels=y,
                           verify_data=X, verify_labels=y)
    return orch, registry, initial, cycle, X, y


def test_shadow_comparison_recorded():
    _, _, _, cycle, _, _ = _cycle(False)
    assert cycle.shadow is not None and 0 <= cycle.shadow["agreement"] <= 1
    assert "shadow" in cycle.decision.evidence


def test_approval_required_stages_instead_of_deploying():
    orch, registry, initial, cycle, _, _ = _cycle(True)
    assert cycle.pending_approval and not cycle.promoted
    assert registry.active_model is initial and registry.pending is cycle.candidate
    registry.approve("MOH officer")
    assert registry.active_model is cycle.candidate
    assert registry.history[-1].reason == "approved by MOH officer"


def test_post_deployment_check_rolls_back_a_worse_model():
    orch, registry, initial, cycle, X, y = _cycle(False)
    assert cycle.promoted

    class Broken:
        version, metadata = cycle.candidate.version, cycle.candidate.metadata

        def predict(self, X):
            return np.zeros(len(X), dtype=int)

        def predict_proba(self, X):
            p = np.zeros((len(X), len(self.metadata.classes)))
            p[:, 0] = 1.0
            return p

    registry._active = Broken()  # simulate a deployed model that turns out worse on new data
    registry._promoted_stack[-1] = registry._active
    report = orch.post_deployment_check(X, y)
    assert report["rolled_back"] and registry.active_model is initial


def test_new_candidate_never_reuses_a_rejected_version_name():
    orch, registry, _, first, X, y = _cycle(True)
    registry.reject_pending()
    second = orch.run_cycle(reference_data=X, current_data=X, current_labels=y, adapt_data=X, adapt_labels=y,
                            verify_data=X, verify_labels=y)
    assert second.candidate.version != first.candidate.version
    versions = [h.version for h in registry.history if h.action != "rejected"]
    assert len(versions) == len(set(versions))
