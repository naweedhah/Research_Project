import pytest

from component3.config import PromotionCriteria, Thresholds
from component3.decide.policy import MaintenanceAction
from component3.experiments.run_comparison import fit_initial_model
from component3.orchestrator import C3Orchestrator
from component3.registry.registry import ModelRegistry
from tests.helpers import make_toy_data, model_factory, toy_schema

LENIENT = PromotionCriteria(min_recall_macro=0.0, min_minority_recall=0.0, max_ece=1.0, max_brier=3.0, max_regression=1.0)
STRICT = PromotionCriteria(min_recall_macro=0.999, min_minority_recall=0.999, max_ece=0.0, max_brier=0.0, max_regression=0.0)


def _setup(seed=0):
    schema = toy_schema()
    X, y = make_toy_data(seed=seed)
    initial = fit_initial_model(model_factory, X, y, schema)
    registry = ModelRegistry(initial)
    return schema, X, y, initial, registry


def test_run_cycle_no_action_when_stable_and_no_labels():
    schema, X, y, initial, registry = _setup()
    orchestrator = C3Orchestrator(registry, schema)

    cycle = orchestrator.run_cycle(reference_data=X, current_data=X, current_labels=None)

    assert cycle.decision.action == MaintenanceAction.NO_ACTION
    assert cycle.candidate is None
    assert registry.active_model is initial


def test_run_cycle_recalibrates_and_promotes_with_lenient_criteria():
    schema, X, y, initial, registry = _setup(seed=1)
    thresholds = Thresholds(reliability_tau=0.0, calibration_tau=-1.0)
    orchestrator = C3Orchestrator(registry, schema, thresholds=thresholds, criteria=LENIENT)

    cycle = orchestrator.run_cycle(
        reference_data=X, current_data=X, current_labels=y,
        adapt_data=X, adapt_labels=y, verify_data=X, verify_labels=y,
    )

    assert cycle.decision.action == MaintenanceAction.RECALIBRATE
    assert cycle.candidate is not None
    assert cycle.promoted
    assert registry.active_model is cycle.candidate


def test_run_cycle_rejects_candidate_that_fails_verification():
    schema, X, y, initial, registry = _setup(seed=1)
    thresholds = Thresholds(reliability_tau=0.0, calibration_tau=-1.0)
    orchestrator = C3Orchestrator(registry, schema, thresholds=thresholds, criteria=STRICT)

    cycle = orchestrator.run_cycle(
        reference_data=X, current_data=X, current_labels=y,
        adapt_data=X, adapt_labels=y, verify_data=X, verify_labels=y,
    )

    assert cycle.candidate is not None
    assert not cycle.promoted
    assert registry.active_model is initial


def test_run_cycle_retrains_and_promotes():
    schema, X, y, initial, registry = _setup(seed=2)
    thresholds = Thresholds(reliability_tau=1.1, calibration_tau=1.1, min_labeled_for_retrain=10)
    orchestrator = C3Orchestrator(registry, schema, thresholds=thresholds, criteria=LENIENT)

    cycle = orchestrator.run_cycle(
        reference_data=X, current_data=X, current_labels=y,
        adapt_data=X, adapt_labels=y, verify_data=X, verify_labels=y,
        model_factory=model_factory,
    )

    assert cycle.decision.action == MaintenanceAction.RETRAIN
    assert cycle.promoted
    assert registry.active_model.metadata.action == "retrain"


def test_run_cycle_raises_when_recalibrate_missing_adapt_data():
    schema, X, y, initial, registry = _setup(seed=1)
    thresholds = Thresholds(reliability_tau=0.0, calibration_tau=-1.0)
    orchestrator = C3Orchestrator(registry, schema, thresholds=thresholds, criteria=LENIENT)

    with pytest.raises(ValueError):
        orchestrator.run_cycle(reference_data=X, current_data=X, current_labels=y)
