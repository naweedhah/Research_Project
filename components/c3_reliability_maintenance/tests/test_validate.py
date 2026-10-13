import numpy as np
import pandas as pd

from component3.config import Thresholds
from component3.decide.policy import MaintenanceAction
from component3.orchestrator import C3Orchestrator
from component3.validate import Validator, default_validator
from tests.test_orchestrator import LENIENT, _setup


def _records():
    return pd.DataFrame({
        "Age_months_2025": [3, 30, 40, 12, np.nan],
        "Sex": ["Female", "Male", None, "Male", "Female"],
        "HAZ_2025": [0.1, -7.5, 0.0, -1.0, 0.2],            # -7.5 is biologically implausible
        "Weight_kg_2025": [5.0, 12.0, 14.0, 9.0, 11.0],
        "Meal_Frequency_per_Day_2025": ["3 meals/day", "3 meals/day", "4+ meals/day", "Not applicable", "3 meals/day"],
    })


def test_default_rules_catch_real_data_problems():
    report = default_validator().validate(_records())
    # row 0: infant with meals recorded; row 1: implausible HAZ; row 2: sex missing; row 4: age missing
    assert report.invalid.tolist() == [True, True, True, False, True]
    failed = report.summary()["failed_rules"]
    assert any("infant" in k for k in failed) and any("HAZ" in k for k in failed)


def test_orchestrator_drops_invalid_rows_before_adapting():
    schema, X, y, initial, registry = _setup(seed=1)
    bad = X.copy()
    bad.loc[:9, "f0"] = 999.0  # ten impossible values
    validator = Validator(ranges={"f0": (-50, 50)}, max_invalid_fraction=0.5)
    orch = C3Orchestrator(registry, schema, thresholds=Thresholds(reliability_tau=0.0, calibration_tau=-1.0),
                          criteria=LENIENT, validator=validator)
    cycle = orch.run_cycle(reference_data=X, current_data=X, current_labels=y, adapt_data=bad, adapt_labels=y,
                           verify_data=X, verify_labels=y)
    assert cycle.decision.action == MaintenanceAction.RECALIBRATE
    assert cycle.validation["adapt"].invalid.sum() == 10
    assert cycle.decision.evidence["validation"]["adapt"]["invalid_rows"] == 10


def test_mostly_invalid_batch_is_held_not_used():
    schema, X, y, initial, registry = _setup(seed=1)
    bad = X.copy()
    bad["f0"] = 999.0
    orch = C3Orchestrator(registry, schema, thresholds=Thresholds(reliability_tau=0.0, calibration_tau=-1.0),
                          criteria=LENIENT, validator=Validator(ranges={"f0": (-50, 50)}))
    cycle = orch.run_cycle(reference_data=X, current_data=X, current_labels=y, adapt_data=bad, adapt_labels=y,
                           verify_data=X, verify_labels=y)
    assert cycle.decision.action == MaintenanceAction.HOLD
    assert "failed validation" in cycle.decision.reason
    assert cycle.candidate is None and registry.active_model is initial
