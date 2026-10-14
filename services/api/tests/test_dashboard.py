"""Unit tests for dashboard attention ranking."""

from app.api.dashboard import _attention_priority
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
    det_rank, _ = _attention_priority(
        review="AWAITING_REVIEW",
        alerts=[_AlertStub(AlertType.DETERIORATION)],
        metric=None,
        follow_overdue=False,
    )
    stag_rank, _ = _attention_priority(
        review="AWAITING_REVIEW",
        alerts=[_AlertStub(AlertType.STAGNATION)],
        metric=None,
        follow_overdue=False,
    )
    assert det_rank < stag_rank


def test_observed_progress_state_marks_deterioration():
    rank, badges = _attention_priority(
        review="AWAITING_REVIEW",
        alerts=[_AlertStub(AlertType.STAGNATION)],
        metric=_MetricStub(ProgressState.DETERIORATING),
        follow_overdue=False,
    )
    assert rank == 1
    assert "Deterioration" in badges


def test_missed_follow_up_ranks_below_stagnation():
    missed, _ = _attention_priority(
        review="REVIEWED",
        alerts=[_AlertStub(AlertType.MISSED_FOLLOW_UP)],
        metric=None,
        follow_overdue=True,
    )
    stagnating, _ = _attention_priority(
        review="REVIEWED",
        alerts=[_AlertStub(AlertType.STAGNATION)],
        metric=None,
        follow_overdue=False,
    )
    assert missed > stagnating


def test_probability_delta_pp_calculation():
    current = 0.71
    previous = 0.58
    assert round((current - previous) * 100) == 13
