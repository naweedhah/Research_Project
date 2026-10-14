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
