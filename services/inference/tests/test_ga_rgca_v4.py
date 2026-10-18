"""GA-RGCA v4 Rolling SuperLearner deployment checks."""

from pathlib import Path

import numpy as np
import pytest
from fastapi import HTTPException

from app.ga_rgca_v4 import (
    EXPERT_NAMES,
    FORBIDDEN_ROLLING_INPUTS,
    TASK_NAMES,
    V4_MODEL_VERSION,
    _derive_primary_type_v4,
    _predict_neural_core_v4,
    _predict_tree_expert_v4,
    load_ga_rgca_v4,
    predict_v4_deployment_bundle,
)
from app.main import GaRgcaV4Adapter, PredictRequest, V4_LOAD_ERROR, V4_MODEL

requires_v4 = pytest.mark.skipif(V4_MODEL is None, reason=V4_LOAD_ERROR or "v4 artifacts did not load")


def _payload(height, weight, age, **context):
    return {
        "child_pseudonymous_id": "C-V4",
        "visit_number": 1,
        "anthropometric": {
            "age_months": age,
            "sex": "female",
            "height_cm": height,
            "weight_kg": weight,
            "birth_weight_kg": 2.8,
        },
        "socioeconomic": {"household_size": 4, "maternal_education": "O/L passed"},
        "ga_rgca_context": {
            "maternal_age_years": 28,
            "maternal_education": "O/L passed",
            "household_income_range": "Rs.20,000 to Rs. 50,000",
            "exclusive_breastfeeding": "Yes",
            "vitamin_supplementation": "No",
            **context,
        },
        "historical_baseline": {"height_cm": 70, "weight_kg": 8, "age_months": 12},
    }


def test_unloaded_model_returns_503(monkeypatch):
    monkeypatch.setattr("app.main.V4_MODEL", None)
    monkeypatch.setattr("app.main.V4_LOAD_ERROR", "missing artifact")
    request = PredictRequest(child_pseudonymous_id="C-V4", anthropometric={"age_months": 24, "sex": "female", "height_cm": 80, "weight_kg": 10})
    with pytest.raises(HTTPException) as exc:
        GaRgcaV4Adapter().predict(request)
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "MODEL_NOT_AVAILABLE"


def test_missing_artifact_directory_fails_closed():
    model, error = load_ga_rgca_v4(Path("C:/missing/ga-rgca-v4"))
    assert model is None
    assert error


@requires_v4
def test_artifacts_version_experts_and_thresholds():
    assert V4_MODEL.name == V4_MODEL_VERSION
    assert V4_MODEL.metadata["model_version"] == V4_MODEL_VERSION
    assert len(V4_MODEL.models) >= 1
    assert list(V4_MODEL.policy["candidate_names"]) == list(EXPERT_NAMES)
    for task in TASK_NAMES:
        assert set(V4_MODEL.policy["stack_weights"][task]) == set(EXPERT_NAMES)
    thresholds = V4_MODEL.bundle["binary_thresholds"]
    assert list(thresholds) == list(V4_MODEL.metadata["binary_thresholds_final_superlearner"])
    assert thresholds[0] != 0.5 and thresholds[1] != 0.5
    assert V4_MODEL.bundle["uncertainty_binary_variance_q95"] == pytest.approx(
        V4_MODEL.metadata["uncertainty_binary_variance_q95"]
    )
    assert float(V4_MODEL.policy["latent_q99"]) == pytest.approx(V4_MODEL.metadata["latent_q99"])
    assert float(V4_MODEL.policy["acute_conformal_alpha"]) == pytest.approx(0.10)


def test_primary_type_rule_and_overlap():
    thresholds = np.array([0.32, 0.26])
    primary, detected, uw, st, acute = _derive_primary_type_v4(
        np.array([0.50, 0.40]), thresholds, np.array([0.2, 0.3, 0.5])
    )
    assert acute == 2 and primary == "SAM" and "Underweight" in detected and "Stunting" in detected
    primary, detected, uw, st, _ = _derive_primary_type_v4(
        np.array([0.90, 0.40]), thresholds, np.array([0.8, 0.1, 0.1])
    )
    assert uw and st and primary == "Underweight"
    primary, _, _, _, _ = _derive_primary_type_v4(
        np.array([0.50, 0.50]), thresholds, np.array([0.8, 0.1, 0.1])
    )
    assert primary == "Stunting"


@requires_v4
def test_invalid_anthropometry_is_422():
    request = PredictRequest(child_pseudonymous_id="C-V4", anthropometric={"age_months": 24, "sex": "female"})
    with pytest.raises(HTTPException) as exc:
        GaRgcaV4Adapter().predict(request)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "REAL_MODEL_INPUT_INCOMPLETE"


@requires_v4
def test_allow_demo_does_not_replace_v4():
    request = PredictRequest(
        child_pseudonymous_id="C-V4",
        allow_demo=True,
        anthropometric={"age_months": 24, "sex": "female", "height_cm": 80, "weight_kg": 10},
    )
    result = GaRgcaV4Adapter().predict(request)
    assert result.prediction_source == V4_MODEL_VERSION
    assert result.model_version == V4_MODEL_VERSION
    assert result.mode != "DEMO"


@requires_v4
def test_rolling_visit_uses_the_current_measurements():
    first = V4_MODEL.predict_payload(_payload(80, 10, 24))
    second = V4_MODEL.predict_payload(_payload(86, 11.4, 30))
    assert first["input_snapshot"]["Baseline_Height_cm"] == 80
    assert first["input_snapshot"]["Baseline_Weight_kg"] == 10
    assert second["input_snapshot"]["Baseline_Height_cm"] == 86
    assert second["input_snapshot"]["Baseline_Weight_kg"] == 11.4
    assert second["input_snapshot"]["Baseline_Height_cm"] != first["input_snapshot"]["Baseline_Height_cm"]
    assert "historical_baseline_growth_ignored_for_rolling_origin" in second["data_limitations"]
    leaked = set(second["input_snapshot"]).intersection(FORBIDDEN_ROLLING_INPUTS)
    assert not leaked


@requires_v4
def test_prediction_contract_and_notebook_fusion_parity():
    payload = _payload(82, 10.5, 26)
    frame, _, _ = V4_MODEL.snapshot_frame(payload)
    bundled = predict_v4_deployment_bundle(V4_MODEL.bundle, frame)[0]
    served = V4_MODEL.predict_payload(payload)
    for key in (
        "underweight_probability",
        "stunting_probability",
        "mam_probability",
        "sam_probability",
        "ensemble_variance",
        "latent_distance",
        "predicted_malnutrition_type",
        "detected_conditions",
        "triage",
        "uncertainty_flag",
        "out_of_distribution_flag",
        "acute_conformal_prediction_set",
        "modality_reliability",
    ):
        assert served[key] == bundled[key]

    neural = _predict_neural_core_v4(V4_MODEL.bundle["neural"], frame)
    experts = {"GA_RGCA_v4": neural}
    for name, tree in V4_MODEL.bundle["trees"].items():
        experts[name] = _predict_tree_expert_v4(tree, frame)
    names = V4_MODEL.bundle["candidate_names"]
    weights = np.array([V4_MODEL.bundle["stack_weights"]["Underweight"][name] for name in names])
    manual_uw = float(np.sum([experts[name]["binary"][0, 0] * weight for name, weight in zip(names, weights)]))
    assert served["underweight_probability"] == pytest.approx(manual_uw, abs=1e-5)

    for key in ("underweight_probability", "stunting_probability", "mam_probability", "sam_probability"):
        value = served[key]
        assert np.isfinite(value)
        assert 0.0 <= value <= 1.0
    acute_total = sum(served["acute_probabilities"].values())
    severity_total = sum(served["severity_probabilities"].values())
    assert acute_total == pytest.approx(1.0, abs=1e-5)
    assert severity_total == pytest.approx(1.0, abs=1e-5)
    assert served["acute_status"] in served["acute_conformal_prediction_set"]
    assert set(served["modality_reliability"]) == {"history", "socioeconomic", "feeding", "supplementation"}
    assert all(0.0 <= value <= 1.0 for value in served["modality_reliability"].values())
    assert served["uncertainty_flag"] == (served["ensemble_variance"] > V4_MODEL.bundle["uncertainty_binary_variance_q95"])
    assert served["out_of_distribution_flag"] == (served["latent_distance"] > float(V4_MODEL.policy["latent_q99"]))
    assert served["latent"] and len(served["latent"]) == 96
    assert served["model_version"] == V4_MODEL_VERSION
    assert served["prediction_horizon_months"] == 12
