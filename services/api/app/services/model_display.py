"""Authoritative model-output display semantics for clinical UI.

Display labels must follow active inference semantics — never hard-code demo
terminology into domain tables. Future calibrated models switch labels here.
"""

from __future__ import annotations

from app.core.config import get_settings

DEMO_PROJECTION_VERSION = "demo-latent-projection-v1"


def is_demo_mode(*, model_mode: str | None = None, is_demo: bool | None = None) -> bool:
    mode = (model_mode if model_mode is not None else get_settings().model_mode).lower()
    if is_demo is True:
        return True
    if is_demo is False and mode != "demo":
        return False
    return mode == "demo" or is_demo is True


def semantics_for_prediction(pred, *, is_demo: bool | None = None) -> dict:
    """Label a stored prediction from its own source, not from MODEL_MODE."""
    block = None
    if pred is not None and isinstance(getattr(pred, "calibrated_probabilities", None), dict):
        block = pred.calibrated_probabilities.get("ga_rgca")
    if isinstance(block, dict) and block.get("prediction_source") == "GA-RGCA-v4-Rolling-RSL":
        return get_model_output_display_metadata(model_mode="ga_rgca_v4_rsl", is_demo=False)
    if isinstance(block, dict) and block.get("prediction_source") == "GA-RGCA-v3":
        return get_model_output_display_metadata(model_mode="ga_rgca", is_demo=False)
    return get_model_output_display_metadata(is_demo=True if is_demo is None else is_demo)


def get_model_output_display_metadata(
    *,
    model_mode: str | None = None,
    is_demo: bool | None = None,
) -> dict:
    """Return UI-facing semantics for the active model output.

    Absence of DEMO must never imply clinical validation.
    """
    settings = get_settings()
    mode = (model_mode if model_mode is not None else settings.model_mode).lower()
    demo = is_demo_mode(model_mode=mode, is_demo=is_demo)

    if mode == "ga_rgca_v4_rsl":
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
                "Visit-to-visit change is shown only when both visits used the same model version. "
                "A change from v3 or the demo score to v4 is not compared."
            ),
            "prediction_task": "twelve_month_nutritional_risk",
            "prediction_task_label": "12-Month Nutritional Risk Prediction",
            "projection_version": "ga-rgca-v4-fused-latent-v1",
            "projection_label": "Fused latent representation",
            "projection_description": (
                "Coordinates from the GA-RGCA v4 fused latent vector. This is not anatomical imaging "
                "and it is not in the same space as a GA-RGCA v3 embedding."
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

    if mode == "ga_rgca":
        return {
            "model_mode": "ga_rgca",
            "clinical_use": False,
            "is_demo": False,
            "score_kind": "highest_condition_probability",
            "score_label": "Highest Predicted Condition Risk",
            "score_description": (
                "Highest of the Underweight, Stunting, MAM, and SAM probabilities from GA-RGCA v3. "
                "The Normal acute probability is not included. This is a 12-month nutritional-risk "
                "research output. It is not a diagnosis and it is not an overall malnutrition probability."
            ),
            "score_is_probability": True,
            "score_is_calibrated": False,
            "velocity_label": "Risk Velocity",
            "velocity_description": (
                "Visit-to-visit change is shown only when both visits used the same model output. "
                "A change from the demo score to GA-RGCA is not compared."
            ),
            "prediction_task": "twelve_month_nutritional_risk",
            "prediction_task_label": "12-Month Nutritional Risk Prediction",
            "projection_version": None,
            "projection_label": "Model output coordinates",
            "projection_description": (
                "Coordinates from the GA-RGCA output heads. This is not the demo latent projection "
                "and is not anatomical imaging."
            ),
            "confidence_label": "Ensemble uncertainty",
            "confidence_is_calibrated": False,
            "banner_title": "RESEARCH MODEL",
            "banner_subtitle": "GA-RGCA v3 · Research decision-support model — clinical confirmation required.",
            "report_disclaimer": "Research decision-support model — clinical confirmation required.",
            "alert_rule_note": "Generated from GA-RGCA v3 acute-status probability",
        }

    if demo:
        return {
            "model_mode": "demo",
            "clinical_use": False,
            "is_demo": True,
            "score_kind": "model_assessed_probability",
            "score_label": "Model-assessed probability",
            "score_description": (
                "Model-assessed probability from the measurements recorded at this visit. "
                "Clinical review required."
            ),
            "score_is_probability": True,
            "score_is_calibrated": False,
            "velocity_label": "Risk velocity",
            "velocity_description": (
                "Visit-to-visit change in model-assessed probability, adjusted for elapsed time. "
                "Clinical review required."
            ),
            "prediction_task": "current_status",
            "prediction_task_label": "Current nutritional assessment",
            "projection_version": None,
            "projection_label": "Model trajectory",
            "projection_description": (
                "Visit-to-visit model trajectory from recorded assessments. It is not anatomical imaging."
            ),
            "confidence_label": "Model confidence",
            "confidence_is_calibrated": False,
            "banner_title": "Clinical review required",
            "banner_subtitle": "AI-assisted assessment. Clinical review required.",
            "report_disclaimer": "AI-assisted assessment. Clinical review required.",
            "alert_rule_note": "Generated from the model-assessed probability",
        }

    # Research / non-demo adapters — still not clinically validated unless separately attested.
    return {
        "model_mode": mode,
        "clinical_use": False,
        "is_demo": False,
        "score_kind": "research_model_score",
        "score_label": "Model-Assessed Probability",
        "score_description": (
            "Research model output. Clinical review required. Not clinically validated for care decisions."
        ),
        "score_is_probability": True,
        "score_is_calibrated": False,
        "velocity_label": "Risk Velocity",
        "velocity_description": (
            "Visit-to-visit change in model-assessed probability adjusted for elapsed time. "
            "Clinical review required."
        ),
        "prediction_task": "current_status",
        "prediction_task_label": "Current-status classification",
        "projection_version": None,
        "projection_label": "Model latent projection",
        "projection_description": (
            "2D projection of the model latent representation. Research visualization only."
        ),
        "confidence_label": "Model confidence",
        "confidence_is_calibrated": False,
        "banner_title": "RESEARCH MODEL",
        "banner_subtitle": "Clinical review required",
        "report_disclaimer": "RESEARCH MODEL — Clinical review required · Not clinically validated",
        "alert_rule_note": "Research model alert rule",
    }
