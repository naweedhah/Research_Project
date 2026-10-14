"""P0 scientific integrity — model display semantics and projection naming."""

from app.services.model_display import DEMO_PROJECTION_VERSION, get_model_output_display_metadata
from app.services.demo_outcomes import get_demo_outcome


def test_demo_display_semantics():
    meta = get_model_output_display_metadata(model_mode="demo", is_demo=True)
    assert meta["is_demo"] is True
    assert meta["score_label"] == "Model-assessed probability"
    assert meta["score_is_probability"] is True
    assert meta["velocity_label"] == "Risk velocity"
    assert meta["prediction_task_label"] == "Current nutritional assessment"
    assert meta["banner_subtitle"] == "AI-assisted assessment. Clinical review required."
    assert meta["projection_version"] is None
    assert meta["clinical_use"] is False
    assert meta["report_disclaimer"] == "AI-assisted assessment. Clinical review required."


def test_research_mode_not_clinically_validated():
    meta = get_model_output_display_metadata(model_mode="pytorch", is_demo=False)
    assert meta["clinical_use"] is False
    assert meta["banner_title"] == "RESEARCH MODEL"
    assert meta["prediction_task_label"] == "Current-status classification"
    assert meta["score_label"] != "Demo Progression Score"


def test_demo_outcomes_one_based_c1042():
    assert get_demo_outcome("C-1042", 1) == ("wasting", "severe", 0.82)
    assert get_demo_outcome("C-1042", 2) == ("wasting", "moderate", 0.61)
    assert get_demo_outcome("C-1042", 3) == ("wasting", "moderate", 0.59)
    assert get_demo_outcome("C-1042", 0) is None


def test_projection_constant_not_pca():
    assert DEMO_PROJECTION_VERSION == "demo-latent-projection-v1"
    assert "pca" not in DEMO_PROJECTION_VERSION.lower()
