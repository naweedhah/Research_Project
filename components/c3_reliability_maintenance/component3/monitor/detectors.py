"""Shift detectors: PSI, KS, missingness. Deliberately a small, justified set (spec §8)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


def psi(reference: pd.Series, current: pd.Series, bins: int = 10, epsilon: float = 1e-4) -> float:
    """Population Stability Index between two numeric samples.

    Buckets are quantile edges of the reference sample; PSI = sum((cur% - ref%) * ln(cur%/ref%)).
    """
    ref = reference.dropna().to_numpy(dtype=float)
    cur = current.dropna().to_numpy(dtype=float)
    if ref.size == 0 or cur.size == 0:
        return float("nan")

    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if edges.size < 3:
        # Reference has too little variation to bucket meaningfully.
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf

    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)

    ref_pct = ref_counts / ref_counts.sum()
    cur_pct = cur_counts / cur_counts.sum()

    ref_pct = np.clip(ref_pct, epsilon, None)
    cur_pct = np.clip(cur_pct, epsilon, None)

    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def psi_categorical(reference: pd.Series, current: pd.Series, epsilon: float = 1e-4) -> float:
    """PSI for categorical features, bucketed by observed category rather than quantile."""
    ref = reference.dropna()
    cur = current.dropna()
    if ref.empty or cur.empty:
        return float("nan")

    categories = pd.Index(ref.unique()).union(cur.unique())
    ref_pct = ref.value_counts(normalize=True).reindex(categories, fill_value=0.0)
    cur_pct = cur.value_counts(normalize=True).reindex(categories, fill_value=0.0)

    ref_pct = ref_pct.clip(lower=epsilon)
    cur_pct = cur_pct.clip(lower=epsilon)

    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def ks_test(reference: pd.Series, current: pd.Series) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov test. Returns (statistic, p_value)."""
    ref = reference.dropna().to_numpy(dtype=float)
    cur = current.dropna().to_numpy(dtype=float)
    if ref.size == 0 or cur.size == 0:
        return float("nan"), float("nan")
    result = ks_2samp(ref, cur)
    return float(result.statistic), float(result.pvalue)


def missingness_rate(series: pd.Series) -> float:
    if len(series) == 0:
        return float("nan")
    return float(series.isna().mean())


def missingness_delta(reference: pd.Series, current: pd.Series) -> float:
    """Absolute change in missingness rate between reference and current."""
    return abs(missingness_rate(current) - missingness_rate(reference))
