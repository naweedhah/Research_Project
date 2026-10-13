"""Loads the real linked 2025 -> 2026 register data used to build and test C3 against a C1-style model.

The files hold child-level data and are never stored in this repository. Their folder is read from the environment
variable C3_DATA_DIR (default: ~/Downloads/clean_malnutrition_data). Inputs are 2025 measurements and background
fields; the target is the child's 2026 WHO status, so the model predicts a year ahead (no same-year "calculator").
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from component3.interfaces import FeatureSchema, FeatureSpec

PREDICTION_FILE = "PHM_prediction_2025_to_2026.csv"

NUMERIC = [
    "Age_months_2025", "HAZ_2025", "WAZ_2025", "WHZ_2025", "Height_cm_2025", "Weight_kg_2025",
    "Birth_Weight_g", "Maternal_Age_years_2025", "Real_Food_Income_LKR_Jun2025_2025", "Family_Size_2025",
]
CATEGORICAL = [
    "Sex", "Maternal_Education", "Father_Education", "Father_Occupation", "Mother_Occupation",
    "Exclusive_Breastfeeding", "Breastfeeding_Duration_2025", "Complementary_Feeding_Timing_2025",
    "Meal_Frequency_per_Day_2025", "Dietary_Diversity_2025", "Triposha_Supplementation_2025",
    "Vitamin_Supplementation_2025",
]
TARGETS = {"underweight": "Underweight_2026", "stunting": "Stunting_2026", "wasting": "Wasting_2026"}


def data_dir() -> Path:
    return Path(os.environ.get("C3_DATA_DIR", Path.home() / "Downloads" / "clean_malnutrition_data"))


@dataclass(frozen=True)
class RealData:
    X: pd.DataFrame
    y: np.ndarray
    phm: np.ndarray
    person_id: np.ndarray
    schema: FeatureSchema
    target: str


def load_prediction_data(target: str = "underweight", path: Path | None = None) -> RealData:
    path = path or data_dir() / PREDICTION_FILE
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; set C3_DATA_DIR to the folder holding {PREDICTION_FILE}")
    d = pd.read_csv(path)
    keep = (d["Implausible_Z_Flag_2025"] == 0) & (d["Implausible_Z_Flag_2026"] == 0)
    d = d[keep & d[TARGETS[target]].notna() & d[["HAZ_2025", "WAZ_2025", "WHZ_2025"]].notna().all(axis=1)]
    d = d.reset_index(drop=True)

    X = d[NUMERIC + CATEGORICAL].copy()
    for c in CATEGORICAL:
        X[c] = X[c].astype(object).where(X[c].notna(), np.nan)
    y = d[TARGETS[target]].isin(["Moderate", "Severe"]).astype(int).to_numpy()
    schema = FeatureSchema(tuple([FeatureSpec(c, "numeric") for c in NUMERIC] +
                                 [FeatureSpec(c, "categorical", "object") for c in CATEGORICAL]))
    return RealData(X=X, y=y, phm=d["PHM"].to_numpy(), person_id=d["Person_ID"].to_numpy(), schema=schema, target=target)
