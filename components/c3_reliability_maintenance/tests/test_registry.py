import pytest

from component3.experiments.run_comparison import fit_initial_model
from component3.registry.registry import ModelRegistry
from tests.helpers import make_toy_data, model_factory, toy_schema


def _fresh_model(version="v1.0"):
    schema = toy_schema()
    X, y = make_toy_data()
    return fit_initial_model(model_factory, X, y, schema, version=version)


def test_registry_starts_with_initial_model():
    model = _fresh_model()
    registry = ModelRegistry(model)
    assert registry.active_model is model
    assert len(registry.history) == 1
    assert registry.history[0].action == "initial"


def test_promote_replaces_active_model_and_logs_history():
    initial = _fresh_model("v1.0")
    registry = ModelRegistry(initial)
    candidate = _fresh_model("v1.1")

    registry.promote(candidate)

    assert registry.active_model is candidate
    assert registry.history[-1].action == "promoted"
    assert registry.history[-1].version == "v1.1"


def test_reject_retains_active_model():
    initial = _fresh_model("v1.0")
    registry = ModelRegistry(initial)
    candidate = _fresh_model("v1.1")

    registry.reject(candidate, reason="failed verification gate")

    assert registry.active_model is initial
    assert registry.history[-1].action == "rejected"
    assert registry.history[-1].reason == "failed verification gate"


def test_rollback_restores_previous_promoted_model():
    initial = _fresh_model("v1.0")
    registry = ModelRegistry(initial)
    candidate = _fresh_model("v1.1")
    registry.promote(candidate)

    restored = registry.rollback()

    assert restored is initial
    assert registry.active_model is initial
    assert registry.history[-1].action == "rollback"


def test_rollback_raises_when_nothing_to_roll_back_to():
    initial = _fresh_model("v1.0")
    registry = ModelRegistry(initial)

    with pytest.raises(ValueError):
        registry.rollback()


def test_staging_a_new_candidate_records_the_superseded_one():
    registry = ModelRegistry(_fresh_model("v1.0"))
    registry.stage(_fresh_model("v2.0"))
    registry.stage(_fresh_model("v3.0"))
    assert registry.pending.version == "v3.0"
    assert (registry.history[-2].version, registry.history[-2].action) == ("v2.0", "rejected")
    assert registry.history[-2].reason == "superseded by v3.0"


def test_registry_survives_save_and_load(tmp_path):
    from component3.registry import load_state, save_state

    registry = ModelRegistry(_fresh_model("v1.0"))
    registry.promote(_fresh_model("v2.0"))
    registry.stage(_fresh_model("v3.0"))
    save_state({"registry": registry}, tmp_path / "state.joblib")

    restored = load_state(tmp_path / "state.joblib")["registry"]
    assert restored.active_model.version == "v2.0" and restored.pending.version == "v3.0"
    assert [h.action for h in restored.history] == [h.action for h in registry.history]
    X, _ = make_toy_data()
    assert (restored.active_model.predict(X) == registry.active_model.predict(X)).all()
    assert restored.rollback().version == "v1.0"
    assert not list(tmp_path.glob("*.tmp"))
