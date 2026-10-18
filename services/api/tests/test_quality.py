from app.core.policy import load_clinical_policy
from app.services.quality import validate_visit_payload


def test_missing_required_blocks_prediction():
    policy = load_clinical_policy()
    report = validate_visit_payload({"anthropometric": {"age_months": 18, "sex": "female"}}, policy)
    assert report.complete is False
    assert report.blocking_errors


def test_outlier_weight_blocks():
    policy = load_clinical_policy()
    report = validate_visit_payload(
        {"anthropometric": {"age_months": 18, "sex": "female", "height_cm": 80, "weight_kg": 99}},
        policy,
    )
    assert report.complete is False


def test_missing_height_and_weight_block():
    policy = load_clinical_policy()
    missing_height = validate_visit_payload(
        {"anthropometric": {"age_months": 18, "sex": "female", "weight_kg": 9.2}},
        policy,
    )
    missing_weight = validate_visit_payload(
        {"anthropometric": {"age_months": 18, "sex": "female", "height_cm": 80}},
        policy,
    )
    assert missing_height.complete is False
    assert any(issue.field == "height_cm" for issue in missing_height.blocking_errors)
    assert missing_weight.complete is False
    assert any(issue.field == "weight_kg" for issue in missing_weight.blocking_errors)


def test_negative_height_and_zero_weight_block():
    policy = load_clinical_policy()
    negative = validate_visit_payload(
        {"anthropometric": {"age_months": 18, "sex": "female", "height_cm": -80, "weight_kg": 9.2}},
        policy,
    )
    zero = validate_visit_payload(
        {"anthropometric": {"age_months": 18, "sex": "female", "height_cm": 80, "weight_kg": 0}},
        policy,
    )
    assert negative.complete is False
    assert "Please verify this measurement before prediction." in negative.blocking_errors[0].message
    assert zero.complete is False


def test_height_in_metres_and_invalid_numeric_block():
    policy = load_clinical_policy()
    metres = validate_visit_payload(
        {"anthropometric": {"age_months": 24, "sex": "female", "height_cm": 0.8, "weight_kg": 10}},
        policy,
    )
    invalid = validate_visit_payload(
        {"anthropometric": {"age_months": 24, "sex": "female", "height_cm": "abc", "weight_kg": 10}},
        policy,
    )
    assert metres.complete is False
    assert "Please verify this measurement before prediction." in metres.blocking_errors[0].message
    assert invalid.complete is False


def test_age_specific_implausible_weight_blocks():
    policy = load_clinical_policy()
    report = validate_visit_payload(
        {"anthropometric": {"age_months": 17, "sex": "female", "height_cm": 78, "weight_kg": 20}},
        policy,
    )
    assert report.complete is False
    assert any("not realistic" in issue.message for issue in report.blocking_errors)


def test_complete_visit_passes():
    policy = load_clinical_policy()
    report = validate_visit_payload(
        {
            "anthropometric": {
                "age_months": 18,
                "sex": "female",
                "height_cm": 78,
                "weight_kg": 9.2,
                "muac_cm": 12.5,
            },
            "dietary": {"dietary_diversity_score": 4},
            "maternal_child_health": {"maternal_bmi": 21},
        },
        policy,
    )
    assert report.complete is True
