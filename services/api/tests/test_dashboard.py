"""Unit tests for dashboard aggregation helpers."""

from app.api.dashboard import _ALERT_PRIORITY, _PROGRESS_PRIORITY, _priority_score
from app.models.enums import AlertSeverity, AlertStatus, AlertType, ProgressState


class _AlertStub:
    def __init__(self, alert_type: AlertType):
        self.type = alert_type
        self.severity = AlertSeverity.HIGH
        self.status = AlertStatus.OPEN


class _MetricStub:
    def __init__(self, progress_state: ProgressState):
        self.progress_state = progress_state


def test_deterioration_outranks_stagnation():
    det = [_AlertStub(AlertType.DETERIORATION)]
    stag = [_AlertStub(AlertType.STAGNATION)]
    assert _priority_score(det, None, 0.5) > _priority_score(stag, None, 0.5)


def test_progress_state_adds_to_alert_score():
    metric = _MetricStub(ProgressState.DETERIORATING)
    base = _priority_score([_AlertStub(AlertType.STAGNATION)], metric, 0.5)
    assert base == _ALERT_PRIORITY[AlertType.STAGNATION] + _PROGRESS_PRIORITY[ProgressState.DETERIORATING]


def test_high_risk_boost():
    low = _priority_score([_AlertStub(AlertType.STAGNATION)], None, 0.4)
    high = _priority_score([_AlertStub(AlertType.STAGNATION)], None, 0.75)
    assert high > low


def test_missed_follow_up_has_lowest_alert_priority():
    assert _ALERT_PRIORITY[AlertType.MISSED_FOLLOW_UP] < _ALERT_PRIORITY[AlertType.STAGNATION]


def test_probability_delta_pp_calculation():
    current = 0.71
    previous = 0.58
    assert round((current - previous) * 100) == 13
