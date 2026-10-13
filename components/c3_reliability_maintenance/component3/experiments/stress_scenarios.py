"""Controlled shift-injection framework (spec §18-19): systematic, not arbitrary, perturbations.

Every function is a pure DataFrame(+labels) transform, generic over column names, so
these scenarios work identically against toy test fixtures and a real dataset later.
Concept shift (a genuine change in P(Y|X)) is deliberately not modeled here — the
spec treats it as a stretch experiment, not a core claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

ScenarioFn = Callable[[pd.DataFrame, np.ndarray, np.random.Generator], tuple[pd.DataFrame, np.ndarray]]


@dataclass(frozen=True)
class Scenario:
    name: str
    category: str  # "A" data-quality | "B" covariate | "C" label/prevalence | "D" operational
    apply: ScenarioFn


# --- Category A: data-quality degradation ---------------------------------------------------


def inject_missingness(columns: list[str], rate: float = 0.3) -> ScenarioFn:
    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        X = X.copy()
        mask = rng.random(len(X)) < rate
        for col in columns:
            if col in X.columns:
                X.loc[mask, col] = np.nan
        return X, y

    return _apply


def inject_measurement_noise(columns: list[str], scale: float = 1.0) -> ScenarioFn:
    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        X = X.copy()
        for col in columns:
            if col in X.columns:
                std = X[col].std()
                X[col] = X[col] + rng.normal(0, std * scale, size=len(X))
        return X, y

    return _apply


def inject_out_of_range_values(columns: list[str], factor: float = 5.0, rate: float = 0.05) -> ScenarioFn:
    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        X = X.copy()
        mask = rng.random(len(X)) < rate
        for col in columns:
            if col in X.columns:
                X.loc[mask, col] = X[col].max() * factor
        return X, y

    return _apply


# --- Category B: covariate shift -------------------------------------------------------------


def shift_covariate(columns: list[str], loc_shift_in_std: float = 1.5, scale_factor: float = 1.0) -> ScenarioFn:
    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        X = X.copy()
        for col in columns:
            if col in X.columns:
                std = X[col].std()
                X[col] = X[col] * scale_factor + loc_shift_in_std * std
        return X, y

    return _apply


def shift_population(column: str, strength: float = 1.0) -> ScenarioFn:
    """Genuine covariate shift: resamples children toward high (strength > 0) or low (< 0) values of `column`.

    Unlike shift_covariate, every row keeps its own features and label, so P(Y|X) is unchanged. This is the case
    the spec singles out: the data changes but the model may still be fine.
    """

    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        v = pd.to_numeric(X[column], errors="coerce")
        z = ((v - v.mean()) / v.std()).fillna(0.0).to_numpy()
        w = np.exp(strength * z)
        idx = rng.choice(len(X), size=len(X), replace=True, p=w / w.sum())
        return X.iloc[idx].reset_index(drop=True), np.asarray(y)[idx]

    return _apply


# --- Category C: label / prevalence shift -----------------------------------------------------


def shift_label_prevalence(target_props: dict) -> ScenarioFn:
    """Resamples rows (with replacement) so class proportions match `target_props`."""

    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        y = np.asarray(y)
        n = len(y)
        idx_by_class = {c: np.where(y == c)[0] for c in np.unique(y)}
        chosen_idx = []
        for cls, prop in target_props.items():
            pool = idx_by_class.get(cls, np.array([], dtype=int))
            if pool.size == 0:
                continue
            chosen_idx.append(rng.choice(pool, size=int(round(prop * n)), replace=True))
        if not chosen_idx:
            return X, y
        idx = np.concatenate(chosen_idx)
        rng.shuffle(idx)
        return X.iloc[idx].reset_index(drop=True), y[idx]

    return _apply


# --- Category D: operational shift -------------------------------------------------------------


def make_feature_unavailable(columns: list[str]) -> ScenarioFn:
    """Simulates a field that stops being collected: becomes entirely missing."""

    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        X = X.copy()
        for col in columns:
            if col in X.columns:
                X[col] = np.nan
        return X, y

    return _apply


def shift_field_missingness(column: str, rate: float) -> ScenarioFn:
    """Simulates a collection-procedure change causing one field to be missing more often."""

    def _apply(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator):
        X = X.copy()
        if column in X.columns:
            mask = rng.random(len(X)) < rate
            X.loc[mask, column] = np.nan
        return X, y

    return _apply


def default_scenarios(numeric_columns: list[str], target_prevalence: dict | None = None) -> list[Scenario]:
    """A small, representative set covering all four categories (spec §19: one or two per category)."""
    if not numeric_columns:
        raise ValueError("default_scenarios requires at least one numeric column")

    primary = numeric_columns[0]
    scenarios = [
        Scenario("missingness_spike", "A", inject_missingness(numeric_columns[:2], rate=0.3)),
        Scenario("measurement_noise", "A", inject_measurement_noise(numeric_columns[:2], scale=1.0)),
        Scenario("covariate_shift", "B", shift_covariate([primary], loc_shift_in_std=1.5)),
        Scenario("feature_unavailable", "D", make_feature_unavailable([primary])),
    ]
    if target_prevalence is not None:
        scenarios.append(Scenario("label_prevalence_shift", "C", shift_label_prevalence(target_prevalence)))
    return scenarios
