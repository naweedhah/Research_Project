"""Historical baseline mapping, feature order, and missing-value behavior."""

from pathlib import Path

import numpy as np

from app.ga_rgca import build_feature_row, transform_record


PRIMARY_HISTORY_NUM = [
    "Hist_2025_Age_months",
    "Hist_2025_Height_cm",
    "Hist_2025_Weight_kg",
    "Hist_2025_BMI",
    "Birth_Weight_g",
    "Hist_2025_MAM",
    "Hist_2025_SAM",
]
PRIMARY_HISTORY_CAT = ["Sex", "Hist_Age_Band", "Hist_2025_Underweight", "Hist_2025_Stunting"]


def test_follow_up_does_not_copy_current_measurements_into_history():
    row, limitations = build_feature_row(
        {
            "anthropometric": {
                "age_months": 40,
                "sex": "Male",
                "height_cm": 100,
                "weight_kg": 20,
                "birth_weight_kg": 3.3,
            },
            "historical_baseline": {
                "source": "earlier_visit",
                "assessment_date": "2025-06-01T00:00:00",
                "horizon_end_date": "2026-06-01T00:00:00",
                "age_months": 18,
                "height_cm": 75,
                "weight_kg": 9,
                "birth_weight_kg": 2.8,
                "mam": 1,
                "sam": 0,
                "underweight": "Moderate",
                "stunting": "Severe",
            },
        }
    )
    assert row["Hist_2025_Age_months"] == 18
    assert row["Hist_2025_Height_cm"] == 75
    assert row["Hist_2025_Weight_kg"] == 9
    assert row["Hist_2025_BMI"] == 9 / ((75 / 100) ** 2)
    assert row["Birth_Weight_g"] == 2800
    assert row["Hist_2025_MAM"] == 1
    assert row["Hist_2025_SAM"] == 0
    assert row["Hist_2025_Underweight"] == "Moderate"
    assert row["Hist_2025_Stunting"] == "Severe"
    assert row["Sex"] == "Male"
    assert "baseline_growth_is_from_an_earlier_visit_not_today" in limitations
    assert "Hist_2025_MAM_not_recorded" not in limitations
    assert "Hist_2025_Underweight_not_recorded" not in limitations


def test_unknown_history_is_not_confirmed_negative_and_conditions_can_coexist():
    missing, missing_limits = build_feature_row(
        {
            "anthropometric": {"sex": "Female", "height_cm": 90, "weight_kg": 14},
            "historical_baseline": {"source": "earlier_visit", "age_months": 20, "height_cm": 78, "weight_kg": 9.5},
        }
    )
    assert missing["Hist_2025_MAM"] is None
    assert missing["Hist_2025_SAM"] is None
    assert missing["Hist_2025_Underweight"] is None
    assert missing["Hist_2025_Stunting"] is None
    assert "Hist_2025_MAM_not_recorded" in missing_limits

    both, _ = build_feature_row(
        {
            "anthropometric": {"sex": "Female"},
            "historical_baseline": {
                "source": "verified_record",
                "height_cm": 80,
                "weight_kg": 10,
                "age_months": 24,
                "mam": 0,
                "sam": 0,
                "underweight": "Severe",
                "stunting": "Moderate",
            },
        }
    )
    assert both["Hist_2025_Underweight"] == "Severe"
    assert both["Hist_2025_Stunting"] == "Moderate"
    assert both["Hist_2025_MAM"] == 0
    assert both["Hist_2025_SAM"] == 0


def test_saved_preprocessor_order_and_missing_flag_match_training():
    directory = Path(__file__).resolve().parents[3] / "ml" / "artifacts" / "ga_rgca_v3"
    prep_path = directory / "multimodal_preprocessor.joblib"
    if not prep_path.is_file():
        return
    import joblib
    import __main__
    from app.ga_rgca import MultimodalPreprocessor

    __main__.MultimodalPreprocessor = MultimodalPreprocessor
    prep = joblib.load(prep_path)
    assert list(prep.view_specs) == ["history", "socioeconomic", "feeding", "supplementation"]
    assert list(prep.view_specs["history"]["num"]) == PRIMARY_HISTORY_NUM
    assert list(prep.view_specs["history"]["cat"]) == PRIMARY_HISTORY_CAT

    row, _ = build_feature_row(
        {
            "anthropometric": {"sex": "Female"},
            "historical_baseline": {
                "source": "earlier_visit",
                "age_months": 24,
                "height_cm": 80,
                "weight_kg": 10,
                "birth_weight_kg": 2.9,
            },
        }
    )
    views = transform_record(prep, row)
    history = views["history"]
    mam_index = PRIMARY_HISTORY_NUM.index("Hist_2025_MAM")
    assert history["num_missing"][0, mam_index] == 1
    stats = prep.num_stats["history"]["Hist_2025_MAM"]
    expected = (float(stats["median"]) - float(stats["mean"])) / float(stats["std"])
    assert np.isclose(history["num"][0, mam_index], expected)
    assert row["Hist_2025_MAM"] is None
    underweight_index = PRIMARY_HISTORY_CAT.index("Hist_2025_Underweight")
    assert history["cat"][0, underweight_index] == prep.cat_vocab["history"]["Hist_2025_Underweight"]["Unknown"]
