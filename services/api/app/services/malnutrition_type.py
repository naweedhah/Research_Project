"""Persist and display the GA-RGCA overall type.

The decision rule lives in services/inference/app/malnutrition_type.py.
This module loads that function and maps it onto API responses. It does not
rewrite historical database rows.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DERIVED_KEYS = (
    "predicted_malnutrition_type",
    "underweight_positive",
    "stunting_positive",
    "detected_conditions",
    "uw_decision_strength",
    "st_decision_strength",
    "output_consistency",
)

_PUBLIC_KEYS = (
    "predicted_malnutrition_type",
    "detected_conditions",
    "underweight_probability",
    "stunting_probability",
    "mam_probability",
    "sam_probability",
    "underweight_positive",
    "stunting_positive",
    "acute_status",
    "severity",
    "severity_probabilities",
    "uncertainty_flag",
    "binary_variance",
    "triage",
    "modality_reliability",
    "model_version",
    "prediction_source",
    "output_consistency",
    "binary_thresholds",
    "input_snapshot",
    "missing_features",
    "applicability",
)


def _load_decision_module():
    candidates: list[Path] = [Path("/opt/ga_rgca/malnutrition_type.py")]
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / "services" / "inference" / "app" / "malnutrition_type.py")
    for path in candidates:
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("ga_rgca_malnutrition_type", path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    raise ImportError("GA-RGCA malnutrition type helper was not found")


_decision = _load_decision_module()
derive_predicted_malnutrition_type = _decision.derive_predicted_malnutrition_type
load_binary_thresholds = _decision.load_binary_thresholds
check_output_consistency = _decision.check_output_consistency


def _ga_block(calibrated) -> dict | None:
    if isinstance(calibrated, dict):
        block = calibrated.get("ga_rgca")
        if isinstance(block, dict):
            return block
    return None


def _thresholds_for(block: dict) -> tuple[float, float] | None:
    stored = block.get("binary_thresholds")
    if isinstance(stored, dict) and "Underweight" in stored and "Stunting" in stored:
        return float(stored["Underweight"]), float(stored["Stunting"])
    return load_binary_thresholds()


def derive_from_ga_block(block: dict) -> dict | None:
    """Derive a missing overall type from stored GA-RGCA probabilities."""
    if block.get("prediction_source") != "GA-RGCA-v3":
        return None
    required = ("underweight_probability", "stunting_probability", "acute_status")
    if any(block.get(key) is None for key in required):
        return None
    thresholds = _thresholds_for(block)
    if thresholds is None:
        return None
    underweight_threshold, stunting_threshold = thresholds
    return derive_predicted_malnutrition_type(
        underweight_probability=block["underweight_probability"],
        stunting_probability=block["stunting_probability"],
        underweight_threshold=underweight_threshold,
        stunting_threshold=stunting_threshold,
        acute_status=block["acute_status"],
    )


def _with_derivation(block: dict) -> dict:
    """Shallow copy. Does not mutate the stored JSON object."""
    copied = dict(block)
    if copied.get("prediction_source") != "GA-RGCA-v3":
        return copied
    if not copied.get("predicted_malnutrition_type"):
        derived = derive_from_ga_block(copied)
        if derived is not None:
            for key in _DERIVED_KEYS:
                copied[key] = derived[key]
    if copied.get("predicted_malnutrition_type") and "output_consistency" not in copied:
        copied["output_consistency"] = check_output_consistency(
            predicted_malnutrition_type=copied["predicted_malnutrition_type"],
            underweight_positive=bool(copied.get("underweight_positive")),
            stunting_positive=bool(copied.get("stunting_positive")),
            acute_status=copied.get("acute_status") or "Normal",
        )
    return copied


def resolve_display(status_prediction: str | None, calibrated) -> tuple[str | None, dict | None]:
    """Doctor-facing status and GA-RGCA JSON for API responses.

    Real GA-RGCA rows missing predicted_malnutrition_type are derived here.
    The database row is left unchanged. Demo rows keep their stored status.
    """
    raw = _ga_block(calibrated)
    if raw is None:
        return status_prediction, None
    block = _with_derivation(raw)
    if block.get("prediction_source") == "GA-RGCA-v3" and block.get("predicted_malnutrition_type"):
        return str(block["predicted_malnutrition_type"]), block
    return status_prediction, block


def apply_new_prediction_interpretation(result: dict) -> dict:
    """Set status to the overall type before a new prediction is stored."""
    calibrated = result.get("calibrated_probabilities")
    raw_block = _ga_block(calibrated)
    if not isinstance(raw_block, dict) or raw_block.get("prediction_source") != "GA-RGCA-v3":
        return result
    block = _with_derivation(raw_block)
    predicted = block.get("predicted_malnutrition_type")
    if not predicted:
        return result
    if block.get("output_consistency") != "OK":
        logger.error("GA-RGCA output_consistency=%s predicted=%s acute=%s", block.get("output_consistency"), predicted, block.get("acute_status"))
    calibrated = dict(calibrated)
    calibrated["ga_rgca"] = block
    result["calibrated_probabilities"] = calibrated
    raw = result.get("raw_probabilities")
    if isinstance(raw, dict) and isinstance(raw.get("ga_rgca"), dict):
        raw = dict(raw)
        raw_ga = dict(raw["ga_rgca"])
        for key in _DERIVED_KEYS:
            if key in block:
                raw_ga[key] = block[key]
        raw["ga_rgca"] = raw_ga
        result["raw_probabilities"] = raw
    result["status"] = predicted
    return result


def prediction_api_fields(prediction) -> dict:
    """Fields shared by visit, profile, and integration responses."""
    status, block = resolve_display(prediction.status_prediction, prediction.calibrated_probabilities)
    fields = {
        "status": status,
        "severity": prediction.severity_prediction,
        "ga_rgca": block,
    }
    if isinstance(block, dict) and block.get("prediction_source") == "GA-RGCA-v3":
        for key in _PUBLIC_KEYS:
            if key == "severity":
                fields["severity"] = block.get("severity") or prediction.severity_prediction
                continue
            if key in block:
                fields[key] = block[key]
        fields["predicted_malnutrition_type"] = status
    return fields


def outbound_probabilities(prediction, attr: str):
    """Copy stored probability JSON and attach a display-only GA-RGCA interpretation."""
    stored = getattr(prediction, attr, None)
    if not isinstance(stored, dict) or not isinstance(stored.get("ga_rgca"), dict):
        return stored
    _, block = resolve_display(prediction.status_prediction, prediction.calibrated_probabilities)
    if not isinstance(block, dict) or block.get("prediction_source") != "GA-RGCA-v3":
        return stored
    copied = dict(stored)
    merged = dict(stored["ga_rgca"])
    for key in _DERIVED_KEYS:
        if key in block:
            merged[key] = block[key]
    copied["ga_rgca"] = merged
    return copied


def component1_output(prediction) -> dict:
    """Clean Component 1 contract for C2/C3. No identifiers or model weights."""
    fields = prediction_api_fields(prediction)
    block = fields.get("ga_rgca") if isinstance(fields.get("ga_rgca"), dict) else {}
    snapshot = block.get("input_snapshot") if isinstance(block.get("input_snapshot"), dict) else {}
    thresholds = block.get("binary_thresholds") if isinstance(block.get("binary_thresholds"), dict) else {}
    created = getattr(prediction, "created_at", None)
    prediction_body = {
        "predicted_malnutrition_type": fields.get("predicted_malnutrition_type") or fields.get("status"),
        "detected_conditions": fields.get("detected_conditions") or [],
        "underweight_probability": fields.get("underweight_probability"),
        "stunting_probability": fields.get("stunting_probability"),
        "mam_probability": fields.get("mam_probability"),
        "sam_probability": fields.get("sam_probability"),
        "underweight_positive": fields.get("underweight_positive"),
        "stunting_positive": fields.get("stunting_positive"),
        "acute_status": fields.get("acute_status"),
        "severity": fields.get("severity"),
        "severity_probabilities": fields.get("severity_probabilities") or block.get("severity_probabilities"),
        "uncertainty_flag": fields.get("uncertainty_flag"),
        "binary_variance": fields.get("binary_variance") or block.get("binary_variance"),
        "triage": fields.get("triage"),
        "modality_reliability": fields.get("modality_reliability") or block.get("modality_reliability"),
    }
    return {
        "schema_version": "component1-ga-rgca-v3-1",
        "visit_id": str(prediction.visit_id),
        "prediction_timestamp": created.isoformat() if created is not None else None,
        "prediction_source": fields.get("prediction_source"),
        "model_version": fields.get("model_version"),
        "feature_schema_version": getattr(prediction, "feature_schema_version", None),
        "calibration_version": getattr(prediction, "calibration_version", None),
        "prediction": prediction_body,
        "baseline_context": snapshot,
        "missing_features": block.get("missing_features") or snapshot.get("missing_features") or [],
        "decision_policy": {
            "underweight_threshold": thresholds.get("Underweight"),
            "stunting_threshold": thresholds.get("Stunting"),
            "acute_temperature": snapshot.get("acute_temperature"),
            "severity_temperature": snapshot.get("severity_temperature"),
            "uncertainty_threshold": snapshot.get("uncertainty_threshold") or block.get("uncertainty_threshold"),
        },
        "observed_outcome": None,
    }


def integration_prediction_fields(prediction) -> dict:
    """Component 1 fields returned to Shamiq (C3) and Naweedh (C4)."""
    fields = prediction_api_fields(prediction)
    body = {
        "status": fields["status"],
        "severity": prediction.severity_prediction,
    }
    if fields.get("prediction_source") == "GA-RGCA-v3":
        for key in _PUBLIC_KEYS:
            if key in fields:
                body[key] = fields[key]
        body["severity"] = fields.get("severity") or prediction.severity_prediction
    return body
