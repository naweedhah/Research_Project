"""GA-RGCA architecture smoke test. Does not require the Colab weight files."""

import numpy as np
import torch

from app.ga_rgca import GrowthAnchoredRGCA, build_feature_row


class _Prep:
    def __init__(self):
        self.view_specs = {
            "history": {"num": ["Hist_2025_Age_months", "Hist_2025_Weight_kg"], "cat": ["Sex"]},
            "feeding": {"num": [], "cat": ["Dietary_Diversity"]},
        }
        self.num_dims = {"history": 2, "feeding": 0}
        self.cardinalities = {"history": [4], "feeding": [3]}


def test_forward_returns_binary_acute_and_severity():
    model = GrowthAnchoredRGCA(_Prep(), _Prep().view_specs)
    model.eval()
    views = {
        "history": {
            "num": torch.zeros(2, 2),
            "num_missing": torch.zeros(2, 2),
            "cat": torch.zeros(2, 1, dtype=torch.long),
            "quality": torch.ones(2, 3),
        },
        "feeding": {
            "num": torch.zeros(2, 0),
            "num_missing": torch.zeros(2, 0),
            "cat": torch.zeros(2, 1, dtype=torch.long),
            "quality": torch.ones(2, 3),
        },
    }
    binary, acute_logits, severity, gates = model(views)
    acute = torch.softmax(acute_logits, dim=1)
    assert binary.shape == (2, 2)
    assert acute.shape == (2, 3)
    assert severity.shape == (2, 3)
    assert "history" in gates
    assert torch.allclose(acute.sum(dim=1), torch.ones(2), atol=1e-5)


def test_missing_prior_diagnosis_is_not_coded_as_absent():
    row, limitations = build_feature_row(
        {
            "anthropometric": {"age_months": 24, "sex": "female", "height_cm": 80, "weight_kg": 10, "birth_weight_kg": 2.5},
            "socioeconomic": {"household_size": 4, "maternal_education": "primary"},
            "ga_rgca_context": {"exclusive_breastfeeding": "continued"},
        }
    )
    assert row["Sex"] == "Female"
    assert row["Birth_Weight_g"] == 2500
    assert row["Hist_2025_MAM"] is None
    assert row["Hist_2025_SAM"] is None
    assert row["Hist_2025_Underweight"] is None
    assert row["Maternal_Education"] is None
    assert row["Exclusive_Breastfeeding"] is None
    assert "baseline_clinical_status_not_recorded" in limitations
    assert np.isfinite(row["Hist_2025_BMI"])
