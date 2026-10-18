"""The clinic display contract is GA-RGCA-v4-Rolling-RSL only."""

from types import SimpleNamespace

from app.services.model_display import V4_PROJECTION_VERSION, get_model_output_display_metadata, semantics_for_prediction


def test_active_display_is_v4():
    meta = get_model_output_display_metadata()
    assert meta["model_mode"] == "ga_rgca_v4_rsl"
    assert meta["is_demo"] is False
    assert meta["clinical_use"] is False
    assert meta["prediction_task_label"] == "12-Month Nutritional Risk Prediction"
    assert meta["projection_version"] == V4_PROJECTION_VERSION


def test_old_mode_names_are_not_treated_as_a_model():
    meta = get_model_output_display_metadata(model_mode="demo", is_demo=True)
    assert meta["model_mode"] == "unsupported"
    assert meta["is_demo"] is False


def test_stored_v4_prediction_uses_v4_labels():
    pred = SimpleNamespace(
        calibrated_probabilities={"ga_rgca": {"prediction_source": "GA-RGCA-v4-Rolling-RSL"}}
    )
    meta = semantics_for_prediction(pred, is_demo=True)
    assert meta["model_mode"] == "ga_rgca_v4_rsl"
    assert meta["is_demo"] is False
