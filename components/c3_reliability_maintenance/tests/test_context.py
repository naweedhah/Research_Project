import json
from datetime import date
from pathlib import Path

import pandas as pd

from component3.config import Thresholds
from component3.context import sources
from component3.context.signals import (
    DEFAULT_AREA,
    ContextReport,
    ContextSignal,
    build_context_report,
    disaster_signals,
    food_price_signals,
    inflation_signals,
)
from component3.decide.policy import MaintenanceAction
from component3.orchestrator import C3Orchestrator
from tests.test_orchestrator import _setup

FIXTURES = Path(__file__).parent / "fixtures"


def _events():
    return sources.parse_gdacs(json.loads((FIXTURES / "gdacs_sri_lanka_2025.json").read_text()))


def test_parse_real_gdacs_sample():
    events = _events()
    assert {e.event_type for e in events} == {"FL", "TC"}
    assert all(e.alert_level == "Orange" for e in events)
    assert any("DITWAH" in e.name for e in events)


def test_disaster_alert_inside_window_and_lookback_only():
    events = _events()
    during = disaster_signals(events, date(2025, 12, 1), date(2025, 12, 31))
    assert during and all(s.level == "alert" for s in during)
    months_later = disaster_signals(events, date(2026, 8, 1), date(2026, 8, 31))
    assert months_later == []


def test_parse_real_wfp_sample_skips_hxl_row():
    prices = sources.parse_wfp_prices(FIXTURES / "wfp_food_prices_lka_east_sample.csv")
    assert set(prices["admin2"]) <= {"Ampara", "Batticaloa"}
    assert prices["price"].gt(0).all()
    assert pd.api.types.is_datetime64_any_dtype(prices["date"])


def _prices(change: float) -> pd.DataFrame:
    rows = []
    for district in ("Ampara", "Batticaloa"):
        for commodity in ("Rice (white)", "Eggs", "Coconut"):
            rows.append({"date": pd.Timestamp("2026-07-15"), "admin2": district, "commodity": commodity, "price": 100.0})
            rows.append({"date": pd.Timestamp("2026-08-15"), "admin2": district, "commodity": commodity,
                         "price": 100.0 * (1 + change)})
    return pd.DataFrame(rows)


def test_food_price_jump_raises_alert_and_stable_prices_do_not():
    alert = food_price_signals(_prices(0.15), date(2026, 8, 31))
    assert alert and alert[0].level == "alert" and alert[0].details["months_behind"] == 0
    assert food_price_signals(_prices(0.01), date(2026, 8, 31)) == []


def test_inflation_signal_levels():
    ccpi = pd.DataFrame({"month": pd.PeriodIndex(["2026-05", "2026-08"], freq="M"),
                         "headline_yoy": [5.5, 8.0], "food_yoy": [0.9, 12.0]})
    signals = inflation_signals(ccpi, date(2026, 8, 31))
    assert any(s.level == "alert" and "food" in s.summary.lower() for s in signals)


def test_bundled_ccpi_file_loads():
    ccpi = sources.load_ccpi()
    assert str(ccpi["month"].iloc[-1]) >= "2026-08"


def test_unreachable_sources_are_reported_not_fatal():
    def offline(url, params=None):
        raise OSError("no network")

    report = build_context_report(date(2026, 9, 1), date(2026, 9, 30), getter=offline)
    assert "GDACS disasters" in report.sources_unavailable
    assert "WFP food prices" in report.sources_unavailable


def test_alert_tightens_drift_thresholds_only():
    alert = ContextReport(DEFAULT_AREA, date(2025, 12, 1), date(2025, 12, 31),
                          (ContextSignal("disaster", "alert", "Flood"),))
    base = Thresholds()
    tightened = alert.adjust(base)
    assert tightened.psi_flag < base.psi_flag
    assert tightened.missingness_delta_flag < base.missingness_delta_flag
    assert tightened.reliability_tau == base.reliability_tau  # reliability limits unchanged
    watch = ContextReport(DEFAULT_AREA, date(2025, 12, 1), date(2025, 12, 31),
                          (ContextSignal("inflation", "watch", "CCPI"),))
    assert watch.adjust(base) == base


def test_context_never_triggers_maintenance_by_itself():
    schema, X, y, initial, registry = _setup()
    alert = ContextReport(DEFAULT_AREA, date(2025, 12, 1), date(2025, 12, 31),
                          (ContextSignal("disaster", "alert", "Flood (Orange)"),))
    cycle = C3Orchestrator(registry, schema).run_cycle(reference_data=X, current_data=X, current_labels=None,
                                                       context=alert)
    assert cycle.decision.action == MaintenanceAction.NO_ACTION
    assert cycle.decision.evidence["context"]["heightened"] is True
    assert cycle.context is alert
