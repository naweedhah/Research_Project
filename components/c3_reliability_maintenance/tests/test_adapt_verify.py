import numpy as np
import pytest

from component3.adapt.candidate import bump_version
from component3.adapt.recalibrate import generate_recalibrated_candidate
from component3.adapt.retrain import generate_retrained_candidate
from component3.config import PromotionCriteria
from component3.experiments.run_comparison import fit_initial_model
from component3.verify.verify import verify_candidate
from tests.helpers import make_toy_data, model_factory, toy_schema


def test_bump_version_recalibrate():
    assert bump_version("v1.0", "recalibrate") == "v1.1"


def test_bump_version_retrain():
    assert bump_version("v1.3", "retrain") == "v2.0"


def test_bump_version_unknown_action_raises():
    with pytest.raises(ValueError):
        bump_version("v1.0", "unknown")


def test_generate_recalibrated_candidate_produces_valid_probabilities():
    schema = toy_schema()
    X, y = make_toy_data()
    active = fit_initial_model(model_factory, X, y, schema)

    candidate = generate_recalibrated_candidate(active, X, y, "v1.1")
    proba = candidate.predict_proba(X)

    assert proba.shape == (len(X), 3)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-6)
    assert candidate.metadata.parent_version == active.version
    assert candidate.metadata.action == "recalibrate"


def test_generate_retrained_candidate_fits_fresh_model():
    schema = toy_schema()
    X, y = make_toy_data()

    candidate = generate_retrained_candidate(model_factory, X, y, "v2.0", "v1.0", schema)

    assert candidate.version == "v2.0"
    assert candidate.metadata.parent_version == "v1.0"
    assert candidate.metadata.action == "retrain"
    assert len(candidate.predict(X)) == len(X)


def test_verify_candidate_passes_with_lenient_criteria():
    schema = toy_schema()
    X, y = make_toy_data()
    active = fit_initial_model(model_factory, X, y, schema)
    lenient = PromotionCriteria(min_recall_macro=0.0, min_minority_recall=0.0, max_ece=1.0, max_brier=3.0, max_regression=1.0)

    result = verify_candidate(active, X, y, lenient, active_model=active)

    assert result.passed


def test_verify_candidate_fails_with_strict_criteria():
    schema = toy_schema()
    X, y = make_toy_data()
    active = fit_initial_model(model_factory, X, y, schema)
    strict = PromotionCriteria(min_recall_macro=0.999, min_minority_recall=0.999, max_ece=0.0, max_brier=0.0, max_regression=0.0)

    result = verify_candidate(active, X, y, strict, active_model=active)

    assert not result.passed
    assert len(result.failures) > 0
