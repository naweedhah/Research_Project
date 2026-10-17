"""Component 1 model adapter: column mapping (always) and loading/predicting (only when the bundle is present)."""

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from component3.models.c1_ga_rgca import C1GaRgcaModel, model_dir, to_c1_frame  # noqa: E402


def _child(**overrides):
    row = {"Age_months_2025": 30, "Height_cm_2025": 85.0, "Weight_kg_2025": 9.0, "WHZ_2025": -2.5, "WAZ_2025": -3.2,
           "HAZ_2025": -1.0, "Birth_Weight_g": 2500.0, "Sex": "Female", "Father_Occupation": "Working abroad",
           "Maternal_Age_years_2025": 27.0, "Family_Size_2025": 4.0, "Breastfeeding_Duration_2025": "More than 6 months"}
    return {**row, **overrides}


def test_columns_are_mapped_to_c1_names_with_who_statuses():
    out = to_c1_frame(pd.DataFrame([_child(), _child(WHZ_2025=np.nan, WAZ_2025=-1.0, Father_Occupation="Unemployed")]))
    first, second = out.iloc[0], out.iloc[1]
    assert first["Hist_2025_Underweight"] == "Severe" and first["Hist_2025_Stunting"] == "Normal"
    assert (first["Hist_2025_MAM"], first["Hist_2025_SAM"]) == (1.0, 0.0)
    assert first["Hist_Age_Band"] == "24-35" and round(first["Hist_2025_BMI"], 2) == 12.46
    assert first["Father_Occupation"] == "Abroad" and second["Father_Occupation"] == "No job"
    assert np.isnan(second["Hist_2025_MAM"]) and second["Hist_2025_Underweight"] == "Normal"
    assert pd.isna(first["Household_Income_Range"])  # absent -> treated as Unknown by C1's preprocessor


@pytest.mark.skipif(not (model_dir() / "ga_rgca_v3_states.pt").exists(), reason="C1 model bundle not present")
def test_c1_bundle_loads_strictly_and_predicts_probabilities():
    model = C1GaRgcaModel(target="underweight")
    assert len(model.networks) == 3 and model.version == "v1.0" and model.metadata.decision_threshold == 0.09
    X = pd.DataFrame([_child(), _child(WAZ_2025=0.5, WHZ_2025=0.2, Weight_kg_2025=12.5)])
    proba = model.predict_proba(X)
    assert proba.shape == (2, 2) and np.allclose(proba.sum(axis=1), 1)
    assert proba[0, 1] > proba[1, 1]  # the severely underweight child gets the higher risk
    heads = model.predict_heads(X)
    assert heads["acute"].shape == (2, 3) and np.allclose(heads["acute"].sum(axis=1), 1)
