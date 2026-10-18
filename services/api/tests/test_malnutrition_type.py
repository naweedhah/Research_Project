"""Persistence and display mapping for the GA-RGCA overall type."""

from types import SimpleNamespace

from app.services.malnutrition_type import (
    apply_new_prediction_interpretation,
    component1_output,
    display_probability_fields,
    highest_risk_condition,
    integration_prediction_fields,
    normal_category_probability,
    predicted_type_probability,
    prediction_api_fields,
    resolve_display,
)

STUNTING_BLOCK = {
    "prediction_source": "GA-RGCA-v3",
    "model_version": "GA-RGCA-v3",
    "underweight_probability": 0.00,
    "stunting_probability": 0.66,
    "mam_probability": 0.01,
    "sam_probability": 0.00,
    "acute_status": "Normal",
    "severity": "Moderate",
    "severity_probabilities": {"normal": 0.2, "moderate": 0.7, "severe": 0.1},
    "uncertainty_flag": False,
    "triage": "Priority clinical assessment",
    "binary_thresholds": {"Underweight": 0.09, "Stunting": 0.09},
}


def test_new_prediction_stores_overall_type_and_keeps_acute_status():
    result = {
        "status": "Normal",
        "severity": "Moderate",
        "raw_probabilities": {"ga_rgca": dict(STUNTING_BLOCK)},
        "calibrated_probabilities": {"acute": {"Normal": 0.99}, "risk": 0.66, "ga_rgca": dict(STUNTING_BLOCK)},
    }
    stored = apply_new_prediction_interpretation(result)
    ga = stored["calibrated_probabilities"]["ga_rgca"]
    assert stored["status"] == "Stunting"
    assert ga["predicted_malnutrition_type"] == "Stunting"
    assert ga["acute_status"] == "Normal"
    assert ga["detected_conditions"] == ["Stunting"]
    assert ga["underweight_positive"] is False
    assert ga["stunting_positive"] is True
    assert stored["raw_probabilities"]["ga_rgca"]["predicted_malnutrition_type"] == "Stunting"
    assert stored["status"] == ga["predicted_malnutrition_type"]


def test_historical_ga_record_is_derived_for_display_without_mutation():
    calibrated = {"ga_rgca": dict(STUNTING_BLOCK)}
    row = SimpleNamespace(status_prediction="Normal", calibrated_probabilities=calibrated, severity_prediction="Moderate")
    status, block = resolve_display(row.status_prediction, row.calibrated_probabilities)
    assert status == "Stunting"
    assert block["predicted_malnutrition_type"] == "Stunting"
    assert block["detected_conditions"] == ["Stunting"]
    assert row.status_prediction == "Normal"
    assert "predicted_malnutrition_type" not in row.calibrated_probabilities["ga_rgca"]


def test_demo_records_keep_their_labelled_status():
    row = SimpleNamespace(
        status_prediction="wasting",
        severity_prediction="moderate",
        calibrated_probabilities={"status": {"wasting": 0.7}, "risk": 0.7},
    )
    status, block = resolve_display(row.status_prediction, row.calibrated_probabilities)
    assert status == "wasting"
    assert block is None
    fields = integration_prediction_fields(row)
    assert fields["status"] == "wasting"
    assert "predicted_malnutrition_type" not in fields


def test_integration_payload_uses_overall_type_for_the_stunting_case():
    calibrated = {"ga_rgca": dict(STUNTING_BLOCK)}
    row = SimpleNamespace(status_prediction="Normal", calibrated_probabilities=calibrated, severity_prediction="Moderate")
    fields = integration_prediction_fields(row)
    assert fields["predicted_malnutrition_type"] == "Stunting"
    assert fields["detected_conditions"] == ["Stunting"]
    assert fields["underweight_probability"] == 0.00
    assert fields["stunting_probability"] == 0.66
    assert fields["mam_probability"] == 0.01
    assert fields["sam_probability"] == 0.00
    assert fields["underweight_positive"] is False
    assert fields["stunting_positive"] is True
    assert fields["acute_status"] == "Normal"
    assert fields["severity"] == "Moderate"
    assert fields["status"] == "Stunting"
    assert row.status_prediction == "Normal"


def test_component1_contract_uses_overall_type_and_hides_identity():
    calibrated = {"ga_rgca": dict(STUNTING_BLOCK)}
    row = SimpleNamespace(
        visit_id="visit-1",
        created_at=None,
        feature_schema_version="ga-rgca-v3-current-visit-baseline",
        calibration_version="ga-rgca-v3-binary-calibrators",
        status_prediction="Normal",
        calibrated_probabilities=calibrated,
        severity_prediction="Moderate",
    )
    body = component1_output(row)
    assert body["schema_version"] == "component1-ga-rgca-v3-1"
    assert body["prediction"]["predicted_malnutrition_type"] == "Stunting"
    assert body["prediction"]["detected_conditions"] == ["Stunting"]
    assert body["observed_outcome"] is None
    assert "full_name" not in str(body)
    assert "phone" not in str(body)


NORMAL_BLOCK = {
    **STUNTING_BLOCK,
    "underweight_probability": 0.02,
    "stunting_probability": 0.05,
    "mam_probability": 0.01,
    "sam_probability": 0.00,
    "severity": "Normal",
}


def test_normal_prediction_pairs_type_with_residual_and_names_leading_condition():
    assert highest_risk_condition(NORMAL_BLOCK) == ("Stunting", 0.05)
    assert normal_category_probability(NORMAL_BLOCK) == 0.95
    assert predicted_type_probability("Normal", NORMAL_BLOCK) == 0.95
    fields = display_probability_fields("Normal", NORMAL_BLOCK, 0.05)
    assert fields == {
        "predicted_type_probability": 0.95,
        "highest_risk_condition": "Stunting",
        "highest_risk_probability": 0.05,
    }
    # The two numbers are complementary: the 5% risk and the 95% Normal probability describe the same output.
    assert fields["predicted_type_probability"] + fields["highest_risk_probability"] == 1.0


def test_condition_prediction_keeps_its_own_probability_separate_from_highest_risk():
    block = {**STUNTING_BLOCK, "underweight_probability": 0.70}
    assert predicted_type_probability("Stunting", block) == 0.66
    assert highest_risk_condition(block) == ("Underweight", 0.70)


def test_demo_prediction_falls_back_to_the_stored_score():
    fields = display_probability_fields("wasting", None, 0.42)
    assert fields == {
        "predicted_type_probability": 0.42,
        "highest_risk_condition": None,
        "highest_risk_probability": 0.42,
    }


def test_prediction_api_fields_include_display_probabilities():
    row = SimpleNamespace(
        status_prediction="Normal",
        calibrated_probabilities={"ga_rgca": dict(NORMAL_BLOCK)},
        severity_prediction="Normal",
        primary_risk_score=0.05,
    )
    fields = prediction_api_fields(row)
    assert fields["predicted_malnutrition_type"] == "Normal"
    assert fields["predicted_type_probability"] == 0.95
    assert fields["highest_risk_condition"] == "Stunting"
    assert fields["highest_risk_probability"] == 0.05
    # Integration contracts are unchanged.
    assert "predicted_type_probability" not in integration_prediction_fields(row)


def test_v4_prediction_is_returned_without_reapplying_v3_thresholds():
    block = {
        "prediction_source": "GA-RGCA-v4-Rolling-RSL",
        "model_version": "GA-RGCA-v4-Rolling-RSL",
        "predicted_malnutrition_type": "SAM",
        "detected_conditions": ["SAM", "Underweight"],
        "underweight_probability": 0.40,
        "stunting_probability": 0.10,
        "mam_probability": 0.20,
        "sam_probability": 0.70,
        "underweight_positive": True,
        "stunting_positive": False,
        "acute_status": "SAM",
        "severity": "Severe",
        "severity_probabilities": {"Normal": 0.05, "Moderate": 0.15, "Severe": 0.80},
        "uncertainty_flag": False,
        "ensemble_variance": 0.001,
        "binary_variance": 0.001,
        "triage": "Priority clinical assessment — SAM risk",
        "binary_thresholds": {"Underweight": 0.32, "Stunting": 0.26},
        "prediction_horizon_months": 12,
    }
    result = apply_new_prediction_interpretation(
        {
            "status": "SAM",
            "severity": "Severe",
            "raw_probabilities": {"ga_rgca": dict(block)},
            "calibrated_probabilities": {"ga_rgca": dict(block), "risk": 0.70},
        }
    )
    assert result["status"] == "SAM"
    assert result["calibrated_probabilities"]["ga_rgca"]["binary_thresholds"]["Underweight"] == 0.32
    row = SimpleNamespace(
        visit_id="visit-1",
        created_at=None,
        status_prediction="SAM",
        severity_prediction="Severe",
        calibrated_probabilities=result["calibrated_probabilities"],
        feature_schema_version="ga-rgca-v4-rolling-current-visit",
        calibration_version="ga-rgca-v4-superlearner",
        primary_risk_score=0.70,
    )
    contract = component1_output(row)
    assert contract["model_version"] == "GA-RGCA-v4-Rolling-RSL"
    assert contract["prediction"]["predicted_malnutrition_type"] == "SAM"
    assert contract["prediction"]["sam_probability"] == 0.70
    assert contract["prediction"]["ensemble_variance"] == 0.001
    assert "child_pseudonymous_id" not in contract
