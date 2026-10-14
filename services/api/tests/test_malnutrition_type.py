"""Persistence and display mapping for the GA-RGCA overall type."""

from types import SimpleNamespace

from app.services.malnutrition_type import (
    apply_new_prediction_interpretation,
    integration_prediction_fields,
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
