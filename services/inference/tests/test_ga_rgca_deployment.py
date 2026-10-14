"""Load the deployed GA-RGCA v3 artifacts and score one complete visit."""

from fastapi import HTTPException

from app.ga_rgca import load_ga_rgca
from app.main import GaRgcaAdapter, PredictRequest


def test_deployment_artifacts_and_one_prediction():
    model, error = load_ga_rgca()
    assert error is None, error
    assert model is not None
    assert len(model.models) == 3
    assert len(model.calibrators) == 2
    meta = model.metadata
    assert "Underweight" in meta["binary_thresholds"]
    assert "Stunting" in meta["binary_thresholds"]
    assert meta["acute_temperature"] > 0
    assert meta["severity_temperature"] > 0
    assert meta["uncertainty_binary_variance_q95"] > 0
    assert meta["triage"]["evaluation_order"][0] == "SAM"
    payload = {
        "anthropometric": {
            "age_months": 24,
            "sex": "Female",
            "height_cm": 80,
            "weight_kg": 10,
            "birth_weight_kg": 2.8,
        },
        "socioeconomic": {"household_size": 4},
        "ga_rgca_context": {
            "maternal_age_years": 28,
            "maternal_education": "O/L passed",
            "household_income_range": "Rs.20,000 to Rs. 50,000",
            "father_occupation": "Manual worker",
            "mother_occupation": "Housewife",
            "exclusive_breastfeeding": "Yes",
            "breastfeeding_duration": "More than 6 months",
            "complementary_feeding_timing": "After 6 months",
            "meal_frequency": "3 meals/day",
            "dietary_diversity": "2 to 5 varieties",
            "triposha_supplementation": "No",
            "vitamin_supplementation": "Yes",
        },
    }
    result = model.predict_prior(payload)
    for key in (
        "underweight_probability",
        "stunting_probability",
        "mam_probability",
        "sam_probability",
    ):
        value = result[key]
        assert value == value and 0 <= value <= 1
    acute_total = (
        result["normal_acute_probability"]
        + result["mam_probability"]
        + result["sam_probability"]
    )
    severity = result["severity_probabilities"]
    assert abs(acute_total - 1) < 0.02
    assert abs(severity["normal"] + severity["moderate"] + severity["severe"] - 1) < 0.02
    assert set(result["modality_reliability"]) >= {"history", "socioeconomic", "feeding", "supplementation"}
    assert result["model_version"] == "GA-RGCA-v3"
    assert result["prediction_source"] == "GA-RGCA-v3"
    assert result["acute_status"] in {"Normal", "MAM", "SAM"}
    assert result["predicted_malnutrition_type"] in {"Normal", "Underweight", "Stunting", "MAM", "SAM"}
    assert result["severity"] in {"Normal", "Moderate", "Severe"}
    if result["predicted_malnutrition_type"] == "Normal":
        assert result["underweight_positive"] is False
        assert result["stunting_positive"] is False
        assert result["acute_status"] == "Normal"
    assert isinstance(result["uncertainty_flag"], bool)
    assert result["triage"]


def test_incomplete_input_does_not_use_demo():
    request = PredictRequest(
        child_pseudonymous_id="synthetic-check",
        anthropometric={"age_months": 24, "sex": "Female"},
        allow_demo=False,
    )
    try:
        GaRgcaAdapter().predict(request)
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["code"] == "REAL_MODEL_INPUT_INCOMPLETE"
        return
    raise AssertionError("incomplete GA-RGCA input returned a prediction")
