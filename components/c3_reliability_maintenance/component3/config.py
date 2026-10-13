"""Predefined, human-set configuration for C3.

All values here are placeholders. Per the project spec (§25, Weeks 3-4), the real
thresholds must be established empirically once real shift/reliability data exists —
nothing in this file should be read as a validated clinical or statistical threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Thresholds:
    """Predefined limits used by the Monitor and Decide stages."""

    # Monitor: shift detectors
    psi_flag: float = 0.2  # conventional "moderate shift" cutoff
    ks_alpha: float = 0.05
    missingness_delta_flag: float = 0.1  # absolute change in NaN rate

    # Assess: reliability floors/ceilings
    min_recall_macro: float = 0.6
    min_minority_recall: float = 0.5
    max_ece: float = 0.1
    max_brier: float = 0.25

    # Decide: how much degradation is "substantial" vs tolerable, and data sufficiency
    reliability_tau: float = 0.6  # recall_macro floor below which reliability is compromised
    calibration_tau: float = 0.1  # ece ceiling below which calibration is acceptable
    min_labeled_for_retrain: int = 200

    minority_classes: tuple = ()  # e.g. ("SAM",) once C1's label set is finalized

    # Adapt: operating point re-tuned for every recalibrated/retrained binary candidate
    operating_sensitivity: float = 0.80


# Relative cost of each maintenance action, used to quantify "least invasive" (spec §12) when comparing
# strategies. Hold means a human review, which costs staff time but changes nothing automatically.
ACTION_COST = {"no_action": 0.0, "hold": 0.5, "recalibrate": 1.0, "retrain": 3.0}


@dataclass(frozen=True)
class PromotionCriteria:
    """Predefined pass/fail criteria a candidate must clear on the untouched verify split."""

    min_recall_macro: float = 0.6
    min_minority_recall: float = 0.5
    max_ece: float = 0.1
    max_brier: float = 0.25
    max_regression: float = 0.02  # allowed drop vs active model on recall_macro, same verify split
    minority_classes: tuple = ()
