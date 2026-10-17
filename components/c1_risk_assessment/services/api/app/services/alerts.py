"""Adaptive alert evaluation with event-window de-duplication."""

from __future__ import annotations

from app.core.policy import ClinicalPolicy
from app.models.enums import AlertSeverity, AlertType, ProgressState


def event_window_key(child_id: str, alert_type: AlertType, visit_id: str | None, extra: str = "") -> str:
    return f"{child_id}:{alert_type.value}:{visit_id or 'na'}:{extra}"


def stagnation_alert(
    *,
    progress_state: ProgressState,
    consecutive_stagnating: int,
    policy: ClinicalPolicy,
) -> bool:
    return progress_state == ProgressState.STAGNATING and consecutive_stagnating >= policy.consecutive_followups


def deterioration_alert(*, previous_risk: float | None, current_risk: float, policy: ClinicalPolicy) -> bool:
    if previous_risk is None:
        return False
    return (current_risk - previous_risk) >= policy.deterioration_delta


def relapse_alert(
    *,
    improved_from_baseline: bool,
    previous_risk: float | None,
    current_risk: float,
    policy: ClinicalPolicy,
) -> bool:
    if not improved_from_baseline or previous_risk is None:
        return False
    return (current_risk - previous_risk) >= policy.relapse_increase


def severity_for(alert_type: AlertType, policy: ClinicalPolicy) -> AlertSeverity:
    raw = policy.alert_severity_map.get(alert_type.value, "MODERATE")
    return AlertSeverity(raw)
