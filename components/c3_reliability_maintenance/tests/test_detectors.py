import numpy as np
import pandas as pd

from component3.monitor.detectors import ks_test, missingness_delta, psi, psi_categorical


def test_psi_near_zero_for_identical_distributions():
    rng = np.random.default_rng(0)
    ref = pd.Series(rng.normal(size=1000))
    cur = pd.Series(rng.normal(size=1000))
    assert psi(ref, cur) < 0.05


def test_psi_large_for_shifted_distribution():
    rng = np.random.default_rng(0)
    ref = pd.Series(rng.normal(loc=0, size=1000))
    cur = pd.Series(rng.normal(loc=5, size=1000))
    assert psi(ref, cur) > 0.5


def test_psi_handles_empty_series():
    assert np.isnan(psi(pd.Series([], dtype=float), pd.Series([1.0, 2.0])))


def test_ks_test_detects_shift():
    rng = np.random.default_rng(0)
    ref = pd.Series(rng.normal(size=500))
    cur = pd.Series(rng.normal(loc=3, size=500))
    stat, pvalue = ks_test(ref, cur)
    assert stat > 0.5
    assert pvalue < 0.01


def test_ks_test_no_shift():
    rng = np.random.default_rng(0)
    ref = pd.Series(rng.normal(size=500))
    cur = pd.Series(rng.normal(size=500))
    stat, pvalue = ks_test(ref, cur)
    assert pvalue > 0.05


def test_missingness_delta():
    ref = pd.Series([1.0, np.nan, 3.0, 4.0])  # 25% missing
    cur = pd.Series([np.nan, np.nan, np.nan, 4.0])  # 75% missing
    assert missingness_delta(ref, cur) == 0.5


def test_psi_categorical_flags_distribution_change():
    ref = pd.Series(["a"] * 80 + ["b"] * 20)
    cur = pd.Series(["a"] * 20 + ["b"] * 80)
    assert psi_categorical(ref, cur) > 0.2


def test_psi_categorical_near_zero_when_unchanged():
    ref = pd.Series(["a"] * 50 + ["b"] * 50)
    cur = pd.Series(["a"] * 48 + ["b"] * 52)
    assert psi_categorical(ref, cur) < 0.05


def test_calibrated_thresholds_use_ks_statistic_and_prediction_limit():
    import numpy as np
    import pandas as pd

    from component3.config import calibrated_thresholds
    from component3.interfaces import FeatureSchema
    from component3.monitor.monitor import run_monitoring

    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 5000)})
    cur = pd.DataFrame({"x": rng.normal(0.08, 1, 5000)})  # tiny shift: significant p-value, small KS statistic
    schema = FeatureSchema.from_dicts([{"name": "x", "kind": "numeric"}])
    thr = calibrated_thresholds()
    assert thr.psi_flag == 0.6 and thr.ks_statistic_flag == 0.27 and thr.prediction_psi_flag == 0.04
    assert not run_monitoring(ref, cur, schema, thr).any_flagged
