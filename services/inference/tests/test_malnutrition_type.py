"""Decision tests for the doctor-facing GA-RGCA malnutrition type."""

import pytest

from app.malnutrition_type import derive_predicted_malnutrition_type, load_binary_thresholds

THRESHOLD = 0.09


def derive(underweight, stunting, acute, underweight_threshold=THRESHOLD, stunting_threshold=THRESHOLD):
    return derive_predicted_malnutrition_type(
        underweight_probability=underweight,
        stunting_probability=stunting,
        underweight_threshold=underweight_threshold,
        stunting_threshold=stunting_threshold,
        acute_status=acute,
    )


def test_normal_only_when_both_binary_heads_and_acute_are_negative():
    result = derive(0.01, 0.02, "Normal")
    assert result["underweight_positive"] is False
    assert result["stunting_positive"] is False
    assert result["predicted_malnutrition_type"] == "Normal"
    assert result["detected_conditions"] == []


def test_underweight_only():
    result = derive(0.20, 0.01, "Normal")
    assert result["underweight_positive"] is True
    assert result["stunting_positive"] is False
    assert result["predicted_malnutrition_type"] == "Underweight"
    assert result["detected_conditions"] == ["Underweight"]


def test_stunting_only():
    result = derive(0.01, 0.20, "Normal")
    assert result["predicted_malnutrition_type"] == "Stunting"
    assert result["detected_conditions"] == ["Stunting"]


def test_both_positive_stunting_stronger():
    result = derive(0.20, 0.80, "Normal")
    assert result["st_decision_strength"] > result["uw_decision_strength"]
    assert result["predicted_malnutrition_type"] == "Stunting"
    assert result["detected_conditions"] == ["Underweight", "Stunting"]


def test_both_positive_underweight_stronger():
    result = derive(0.80, 0.20, "Normal")
    assert result["uw_decision_strength"] > result["st_decision_strength"]
    assert result["predicted_malnutrition_type"] == "Underweight"
    assert result["detected_conditions"] == ["Underweight", "Stunting"]


def test_equal_decision_strength_prefers_stunting():
    result = derive(0.50, 0.50, "Normal")
    assert result["uw_decision_strength"] == result["st_decision_strength"]
    assert result["predicted_malnutrition_type"] == "Stunting"
    assert result["detected_conditions"] == ["Underweight", "Stunting"]


def test_threshold_is_inclusive_and_not_one_half():
    assert derive(0.09, 0.089, "Normal")["predicted_malnutrition_type"] == "Underweight"
    assert derive(0.20, 0.01, "Normal")["underweight_positive"] is True


def test_mam_and_sam_outrank_positive_binary_heads():
    mam = derive(0.80, 0.80, "MAM")
    assert mam["predicted_malnutrition_type"] == "MAM"
    assert mam["detected_conditions"] == ["Underweight", "Stunting", "MAM"]
    sam = derive(0.80, 0.80, "SAM")
    assert sam["predicted_malnutrition_type"] == "SAM"
    assert sam["detected_conditions"] == ["Underweight", "Stunting", "SAM"]


def test_screenshot_stunting_case_is_not_normal():
    result = derive(0.00, 0.66, "Normal", stunting_threshold=0.09)
    assert result["underweight_positive"] is False
    assert result["stunting_positive"] is True
    assert result["predicted_malnutrition_type"] == "Stunting"
    assert result["detected_conditions"] == ["Stunting"]
    assert result["predicted_malnutrition_type"] != "Normal"


def test_normal_invariant():
    cases = [
        (0.50, 0.01, "Normal"),
        (0.01, 0.50, "Normal"),
        (0.50, 0.50, "Normal"),
        (0.01, 0.01, "MAM"),
        (0.01, 0.01, "SAM"),
        (0.50, 0.50, "SAM"),
    ]
    for underweight, stunting, acute in cases:
        result = derive(underweight, stunting, acute)
        if result["predicted_malnutrition_type"] == "Normal":
            assert result["underweight_positive"] is False
            assert result["stunting_positive"] is False
            assert acute == "Normal"
        assert result["predicted_malnutrition_type"] != "Normal"


def test_output_consistency_flags_impossible_normal():
    from app.malnutrition_type import check_output_consistency

    assert (
        check_output_consistency(
            predicted_malnutrition_type="Normal",
            underweight_positive=True,
            stunting_positive=False,
            acute_status="Normal",
        )
        == "REVIEW_REQUIRED"
    )
    assert derive(0.00, 0.66, "Normal")["output_consistency"] == "OK"


def test_metadata_thresholds_are_loaded_not_hardcoded():
    loaded = load_binary_thresholds()
    assert loaded is not None
    underweight_threshold, stunting_threshold = loaded
    assert underweight_threshold == pytest.approx(0.32)
    assert stunting_threshold == pytest.approx(0.26)
