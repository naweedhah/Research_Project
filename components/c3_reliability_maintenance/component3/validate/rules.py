"""Validation gate: checks new records before C3 uses them to recalibrate, retrain or verify a model.

Retraining on defective records teaches the model the defect. The rules come from problems found in the real
register data: impossible z-scores and measurements, missing essentials, and age-inappropriate answers (e.g. diet
recorded for infants under 6 months). Column names are configurable so the gate works for any C1 feature set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

NOT_APPLICABLE = {"not applicable", "not yet started", "ongoing (child under 6 months)", "missing", "na", "nan", ""}


@dataclass(frozen=True)
class ValidationReport:
    n_rows: int
    invalid: np.ndarray          # boolean mask, True = record failed at least one rule
    rule_counts: dict = field(default_factory=dict)

    @property
    def invalid_fraction(self) -> float:
        return float(self.invalid.mean()) if self.n_rows else 0.0

    def summary(self) -> dict:
        return {"rows": self.n_rows, "invalid_rows": int(self.invalid.sum()),
                "invalid_fraction": round(self.invalid_fraction, 3),
                "failed_rules": {k: v for k, v in self.rule_counts.items() if v}}


@dataclass(frozen=True)
class Validator:
    ranges: dict = field(default_factory=dict)                  # column -> (low, high), inclusive
    required: tuple[str, ...] = ()                              # must not be missing
    age_column: str | None = None
    infant_not_applicable: tuple[str, ...] = ()                 # must be blank/"not applicable" below 6 months
    max_invalid_fraction: float = 0.20                          # above this, do not adapt on the batch

    def validate(self, frame: pd.DataFrame) -> ValidationReport:
        invalid = np.zeros(len(frame), dtype=bool)
        counts = {}
        for col, (lo, hi) in self.ranges.items():
            if col not in frame.columns:
                continue
            v = pd.to_numeric(frame[col], errors="coerce")
            bad = (v.notna() & ((v < lo) | (v > hi))).to_numpy()
            counts[f"{col} outside [{lo}, {hi}]"] = int(bad.sum())
            invalid |= bad
        for col in self.required:
            if col in frame.columns:
                bad = frame[col].isna().to_numpy()
                counts[f"{col} missing"] = int(bad.sum())
                invalid |= bad
        if self.age_column and self.age_column in frame.columns:
            infant = (pd.to_numeric(frame[self.age_column], errors="coerce") < 6).to_numpy()
            for col in self.infant_not_applicable:
                if col not in frame.columns:
                    continue
                answered = ~frame[col].astype(str).str.strip().str.lower().isin(NOT_APPLICABLE).to_numpy()
                bad = infant & answered & frame[col].notna().to_numpy()
                counts[f"{col} answered for infant < 6 months"] = int(bad.sum())
                invalid |= bad
        return ValidationReport(len(frame), invalid, counts)


def default_validator(suffix: str = "_2025", max_invalid_fraction: float = 0.20) -> Validator:
    """Rules for the PHM register features (2025 predictors by default)."""
    return Validator(
        ranges={f"Age_months{suffix}": (0, 60), f"Height_cm{suffix}": (40, 125), f"Weight_kg{suffix}": (1, 40),
                f"HAZ{suffix}": (-6, 6), f"WAZ{suffix}": (-6, 5), f"WHZ{suffix}": (-5, 5),
                "Birth_Weight_g": (500, 6000), f"Maternal_Age_years{suffix}": (14, 60), f"Family_Size{suffix}": (2, 20)},
        required=(f"Age_months{suffix}", "Sex"),
        age_column=f"Age_months{suffix}",
        infant_not_applicable=(f"Meal_Frequency_per_Day{suffix}", f"Dietary_Diversity{suffix}",
                               f"Triposha_Supplementation{suffix}"),
        max_invalid_fraction=max_invalid_fraction,
    )
