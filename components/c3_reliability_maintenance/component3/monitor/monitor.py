"""Monitor stage: observe reference vs. current data and flag possible shift (spec §8-9).

This stage only detects distributional change. It makes no claim about whether that
change harms model reliability — that judgment belongs to the Assess stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from component3.config import Thresholds
from component3.interfaces import FeatureSchema
from component3.monitor.detectors import ks_test, missingness_delta, psi, psi_categorical


@dataclass(frozen=True)
class FeatureShiftResult:
    feature: str
    kind: str
    psi_value: float
    ks_statistic: float | None
    ks_pvalue: float | None
    missingness_delta: float
    flagged: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class MonitoringReport:
    feature_results: tuple[FeatureShiftResult, ...]
    prediction_psi: float | None
    prediction_flagged: bool
    any_flagged: bool

    def flagged_features(self) -> list[str]:
        return [r.feature for r in self.feature_results if r.flagged]


def _assess_feature(name: str, kind: str, reference: pd.Series, current: pd.Series, thresholds: Thresholds) -> FeatureShiftResult:
    miss_delta = missingness_delta(reference, current)
    reasons: list[str] = []

    if kind == "numeric":
        psi_value = psi(reference, current)
        ks_stat, ks_p = ks_test(reference, current)
        if not np.isnan(psi_value) and psi_value >= thresholds.psi_flag:
            reasons.append(f"psi={psi_value:.3f}>={thresholds.psi_flag:.3g}")
        if thresholds.ks_statistic_flag is not None:
            if ks_stat is not None and not np.isnan(ks_stat) and ks_stat >= thresholds.ks_statistic_flag:
                reasons.append(f"ks={ks_stat:.3f}>={thresholds.ks_statistic_flag:.3g}")
        elif ks_p is not None and not np.isnan(ks_p) and ks_p < thresholds.ks_alpha:
            reasons.append(f"ks_p={ks_p:.4f}<{thresholds.ks_alpha:.3g}")
    else:
        psi_value = psi_categorical(reference, current)
        ks_stat, ks_p = None, None
        if not np.isnan(psi_value) and psi_value >= thresholds.psi_flag:
            reasons.append(f"psi={psi_value:.3f}>={thresholds.psi_flag:.3g}")

    if miss_delta >= thresholds.missingness_delta_flag:
        reasons.append(f"missingness_delta={miss_delta:.3f}>={thresholds.missingness_delta_flag:.3g}")

    return FeatureShiftResult(
        feature=name,
        kind=kind,
        psi_value=psi_value,
        ks_statistic=ks_stat,
        ks_pvalue=ks_p,
        missingness_delta=miss_delta,
        flagged=len(reasons) > 0,
        reasons=tuple(reasons),
    )


def run_monitoring(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    schema: FeatureSchema,
    thresholds: Thresholds,
    reference_predictions: np.ndarray | None = None,
    current_predictions: np.ndarray | None = None,
) -> MonitoringReport:
    """Compare `current_df` against `reference_df` for every feature in `schema`.

    Optionally also compares predicted-class distributions when both prediction
    arrays are supplied (spec §8: "prediction-distribution changes").
    """
    results = []
    for spec in schema.features:
        if spec.name not in reference_df.columns or spec.name not in current_df.columns:
            continue
        results.append(
            _assess_feature(spec.name, spec.kind, reference_df[spec.name], current_df[spec.name], thresholds)
        )

    prediction_psi = None
    prediction_flagged = False
    if reference_predictions is not None and current_predictions is not None:
        prediction_psi = psi_categorical(pd.Series(reference_predictions), pd.Series(current_predictions))
        limit = thresholds.prediction_psi_flag if thresholds.prediction_psi_flag is not None else thresholds.psi_flag
        prediction_flagged = not np.isnan(prediction_psi) and prediction_psi >= limit

    any_flagged = any(r.flagged for r in results) or prediction_flagged

    return MonitoringReport(
        feature_results=tuple(results),
        prediction_psi=prediction_psi,
        prediction_flagged=prediction_flagged,
        any_flagged=any_flagged,
    )
