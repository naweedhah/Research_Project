"""Decide stage: the adaptive maintenance decision mechanism (spec §11-12).

Actions are predefined and few by design: unnecessary intervention is itself a risk
the spec calls out explicitly, so this module is conservative about escalating.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from component3.assess.assess import ReliabilityReport
from component3.config import Thresholds
from component3.monitor.monitor import MonitoringReport


class MaintenanceAction(str, Enum):
    NO_ACTION = "no_action"
    RECALIBRATE = "recalibrate"
    RETRAIN = "retrain"
    HOLD = "hold"


@dataclass(frozen=True)
class Decision:
    action: MaintenanceAction
    reason: str
    evidence: dict


def decide(
    monitoring: MonitoringReport,
    reliability: ReliabilityReport,
    thresholds: Thresholds,
    n_labeled: int | None = None,
) -> Decision:
    evidence = {
        "any_shift_flagged": monitoring.any_flagged,
        "flagged_features": monitoring.flagged_features(),
        "reliability_status": reliability.status,
    }

    if reliability.status == "pending_labels":
        if not monitoring.any_flagged:
            return Decision(MaintenanceAction.NO_ACTION, "no shift detected; nothing to evaluate", evidence)
        return Decision(
            MaintenanceAction.HOLD,
            "shift detected but no outcome labels available yet; potential reliability risk, verification pending",
            evidence,
        )

    evidence.update(
        {
            "metrics": reliability.metrics,
            "discrimination_ok": reliability.discrimination_ok,
            "calibration_ok": reliability.calibration_ok,
            "minority_ok": reliability.minority_ok,
            "n_labeled": n_labeled,
        }
    )

    if reliability.reliable:
        return Decision(
            MaintenanceAction.NO_ACTION,
            "reliability within acceptable limits; unnecessary updates avoided",
            evidence,
        )

    if reliability.discrimination_ok and not reliability.calibration_ok:
        return Decision(
            MaintenanceAction.RECALIBRATE,
            "discrimination acceptable but calibration degraded",
            evidence,
        )

    # Discrimination (and/or minority-class performance) has substantially degraded.
    # If the inputs themselves have degraded (missing values spiked), the cause is data collection, not the model:
    # retraining would learn the defect. Escalate to a human with a data-quality reason instead.
    data_quality_features = [
        r.feature for r in monitoring.feature_results if r.missingness_delta >= thresholds.missingness_delta_flag
    ]
    evidence["data_quality_features"] = data_quality_features
    if data_quality_features and (not reliability.discrimination_ok or not reliability.minority_ok):
        return Decision(
            MaintenanceAction.HOLD,
            "performance degraded while input completeness dropped ("
            + ", ".join(data_quality_features)
            + "); fix data collection before maintaining the model, since retraining would learn the defect",
            evidence,
        )

    has_enough_data = n_labeled is not None and n_labeled >= thresholds.min_labeled_for_retrain
    if not reliability.discrimination_ok or not reliability.minority_ok:
        if has_enough_data:
            return Decision(
                MaintenanceAction.RETRAIN,
                "predictive performance substantially degraded and sufficient labeled data available",
                evidence,
            )
        return Decision(
            MaintenanceAction.HOLD,
            "predictive performance degraded but insufficient labeled data for retraining",
            evidence,
        )

    return Decision(MaintenanceAction.HOLD, "ambiguous reliability evidence", evidence)
