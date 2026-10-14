from app.core.policy import ClinicalPolicy
from app.models.enums import AlertType, ProgressState
from app.services.alerts import deterioration_alert, event_window_key, relapse_alert, stagnation_alert


def _policy(**overrides) -> ClinicalPolicy:
    base = dict(
        policy_id="test",
        status="RESEARCH_DEMO",
        disclaimer="demo",
        stagnation_threshold=0.03,
        consecutive_followups=2,
        deterioration_delta=0.08,
        relapse_prior_improvement=0.10,
        relapse_increase=0.08,
        overdue_grace_days=7,
        default_followup_days=30,
        measurement_ranges={},
        alert_severity_map={},
        notes="test",
    )
    base.update(overrides)
    return ClinicalPolicy(**base)


def test_stagnation_requires_consecutive_followups():
    policy = _policy()
    assert not stagnation_alert(progress_state=ProgressState.STAGNATING, consecutive_stagnating=1, policy=policy)
    assert stagnation_alert(progress_state=ProgressState.STAGNATING, consecutive_stagnating=2, policy=policy)


def test_deterioration_delta():
    policy = _policy()
    assert not deterioration_alert(previous_risk=0.50, current_risk=0.55, policy=policy)
    assert deterioration_alert(previous_risk=0.50, current_risk=0.60, policy=policy)


def test_relapse_after_improvement():
    policy = _policy()
    assert relapse_alert(improved_from_baseline=True, previous_risk=0.30, current_risk=0.45, policy=policy)
    assert not relapse_alert(improved_from_baseline=False, previous_risk=0.30, current_risk=0.45, policy=policy)


def test_event_window_key_dedupes():
    a = event_window_key("child-1", AlertType.STAGNATION, "visit-9")
    b = event_window_key("child-1", AlertType.STAGNATION, "visit-9")
    assert a == b
