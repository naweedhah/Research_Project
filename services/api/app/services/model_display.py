"""Display labels for the only active model, GA-RGCA-v4-Rolling-RSL."""

from __future__ import annotations

V4_MODEL_VERSION = "GA-RGCA-v4-Rolling-RSL"
V4_PROJECTION_VERSION = "ga-rgca-v4-fused-latent-v1"


def is_demo_mode(*, model_mode: str | None = None, is_demo: bool | None = None) -> bool:
    """The clinical application no longer has a demonstration scoring mode."""
    return False


def semantics_for_prediction(pred, *, is_demo: bool | None = None) -> dict:
    """Label a stored prediction only when it is the active v4 result."""
    block = None
    if pred is not None and isinstance(getattr(pred, "calibrated_probabilities", None), dict):
        block = pred.calibrated_probabilities.get("ga_rgca")
    if isinstance(block, dict) and block.get("prediction_source") == V4_MODEL_VERSION:
        return get_model_output_display_metadata()
    return _unsupported_metadata()


def get_model_output_display_metadata(
    *,
    model_mode: str | None = None,
    is_demo: bool | None = None,
) -> dict:
    """Return UI-facing semantics for GA-RGCA v4 Rolling SuperLearner."""
    if model_mode not in (None, "", "ga_rgca_v4_rsl"):
        return _unsupported_metadata()
    return {
        "model_mode": "ga_rgca_v4_rsl",
        "clinical_use": False,
        "is_demo": False,
        "score_kind": "highest_condition_probability",
        "score_label": "Highest Predicted Condition Risk",
        "score_description": (
            "Highest of the Underweight, Stunting, MAM, and SAM probabilities from the "
            "GA-RGCA v4 Rolling SuperLearner. The Normal acute probability is not included. "
            "This is a 12-month nutritional-risk research output from the current visit. "
            "It is not a diagnosis and it is not an overall malnutrition probability."
        ),
        "score_is_probability": True,
        "score_is_calibrated": True,
        "velocity_label": "Risk Velocity",
        "velocity_description": (
            "Visit-to-visit change is shown only when both visits used GA-RGCA-v4-Rolling-RSL."
        ),
        "prediction_task": "twelve_month_nutritional_risk",
        "prediction_task_label": "12-Month Nutritional Risk Prediction",
        "projection_version": V4_PROJECTION_VERSION,
        "projection_label": "Fused latent representation",
        "projection_description": (
            "Coordinates from the GA-RGCA v4 fused latent vector. This is not anatomical imaging."
        ),
        "confidence_label": "Ensemble uncertainty",
        "confidence_is_calibrated": False,
        "banner_title": "RESEARCH MODEL",
        "banner_subtitle": "GA-RGCA-v4-Rolling-RSL · Research decision-support prototype — clinician confirmation required.",
        "report_disclaimer": (
            "Research decision-support prototype. Clinician confirmation required. "
            "Repeated rolling-origin and external prospective validation are still required."
        ),
        "alert_rule_note": "Generated from GA-RGCA v4 Rolling SuperLearner condition probabilities",
    }


def _unsupported_metadata() -> dict:
    return {
        "model_mode": "unsupported",
        "clinical_use": False,
        "is_demo": False,
        "score_kind": "unavailable",
        "score_label": "Prediction unavailable",
        "score_description": "This record is not a GA-RGCA-v4-Rolling-RSL prediction.",
        "score_is_probability": False,
        "score_is_calibrated": False,
        "velocity_label": "Risk Velocity",
        "velocity_description": "Visit-to-visit change requires two GA-RGCA-v4-Rolling-RSL predictions.",
        "prediction_task": "twelve_month_nutritional_risk",
        "prediction_task_label": "12-Month Nutritional Risk Prediction",
        "projection_version": None,
        "projection_label": "Fused latent representation",
        "projection_description": "No GA-RGCA v4 latent representation is available for this record.",
        "confidence_label": "Ensemble uncertainty",
        "confidence_is_calibrated": False,
        "banner_title": "RESEARCH MODEL",
        "banner_subtitle": "GA-RGCA-v4-Rolling-RSL is the only active model.",
        "report_disclaimer": "Research decision-support prototype. Clinician confirmation required.",
        "alert_rule_note": "No active model prediction is available for this record.",
    }
