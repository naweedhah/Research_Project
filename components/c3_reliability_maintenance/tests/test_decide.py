from component3.assess.assess import ReliabilityReport
from component3.config import Thresholds
from component3.decide.policy import MaintenanceAction, decide
from component3.monitor.monitor import FeatureShiftResult, MonitoringReport

THRESHOLDS = Thresholds(min_labeled_for_retrain=200)


def _monitoring(any_flagged: bool) -> MonitoringReport:
    return MonitoringReport(feature_results=(), prediction_psi=None, prediction_flagged=False, any_flagged=any_flagged)


def _reliability(status="evaluated", discrimination_ok=True, calibration_ok=True, minority_ok=True) -> ReliabilityReport:
    return ReliabilityReport(
        status=status,
        metrics={} if status == "evaluated" else None,
        discrimination_ok=discrimination_ok,
        calibration_ok=calibration_ok,
        minority_ok=minority_ok,
    )


def test_no_action_when_no_shift_and_no_labels():
    decision = decide(_monitoring(False), _reliability(status="pending_labels", discrimination_ok=None, calibration_ok=None, minority_ok=None), THRESHOLDS)
    assert decision.action == MaintenanceAction.NO_ACTION


def test_hold_when_shift_flagged_but_labels_pending():
    decision = decide(_monitoring(True), _reliability(status="pending_labels", discrimination_ok=None, calibration_ok=None, minority_ok=None), THRESHOLDS)
    assert decision.action == MaintenanceAction.HOLD


def test_no_action_when_reliable_despite_shift():
    decision = decide(_monitoring(True), _reliability(discrimination_ok=True, calibration_ok=True, minority_ok=True), THRESHOLDS)
    assert decision.action == MaintenanceAction.NO_ACTION


def test_recalibrate_when_only_calibration_degraded():
    decision = decide(_monitoring(True), _reliability(discrimination_ok=True, calibration_ok=False, minority_ok=True), THRESHOLDS)
    assert decision.action == MaintenanceAction.RECALIBRATE


def test_retrain_when_discrimination_degraded_and_enough_labels():
    decision = decide(
        _monitoring(True),
        _reliability(discrimination_ok=False, calibration_ok=True, minority_ok=True),
        THRESHOLDS,
        n_labeled=500,
    )
    assert decision.action == MaintenanceAction.RETRAIN


def test_hold_when_discrimination_degraded_but_insufficient_labels():
    decision = decide(
        _monitoring(True),
        _reliability(discrimination_ok=False, calibration_ok=True, minority_ok=True),
        THRESHOLDS,
        n_labeled=10,
    )
    assert decision.action == MaintenanceAction.HOLD


def test_retrain_when_only_minority_class_degraded_and_enough_labels():
    decision = decide(
        _monitoring(True),
        _reliability(discrimination_ok=True, calibration_ok=True, minority_ok=False),
        THRESHOLDS,
        n_labeled=500,
    )
    assert decision.action == MaintenanceAction.RETRAIN


def test_hold_for_data_quality_when_missingness_spikes_and_performance_drops():
    missing = FeatureShiftResult("weight", "numeric", 0.05, 0.1, 0.5, 0.4, True, ("missingness_delta=0.400>=0.1",))
    monitoring = MonitoringReport(feature_results=(missing,), prediction_psi=None, prediction_flagged=False, any_flagged=True)
    decision = decide(monitoring, _reliability(discrimination_ok=False, calibration_ok=True, minority_ok=True), THRESHOLDS, n_labeled=500)
    assert decision.action == MaintenanceAction.HOLD
    assert "data collection" in decision.reason
    assert decision.evidence["data_quality_features"] == ["weight"]
