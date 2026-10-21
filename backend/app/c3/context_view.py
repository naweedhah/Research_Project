"""External-context dashboard for C3: what each source returned, as time series, so the monitoring can be seen.

For one monitoring window it fetches every source (live, or the bundled real samples when offline), records how each
fetch went (time, records, latest data date), shapes the data for charts and adds the signals C3 derives from them.
Live fetches are cached for a few minutes; `refresh=True` fetches again.
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.c3.service import FIXTURES, jsonable
from component3.config import Thresholds
from component3.context import sources
from component3.context.signals import DEFAULT_AREA, STAPLE_KEYWORDS, STAPLE_PATTERN, ContextRules, _distance_km, build_context_report

CACHE_SECONDS = 600
TIMELINE_DAYS = 730          # disaster timeline shown: two years up to the window end
EVENT_NAMES = {"FL": "Flood", "TC": "Tropical cyclone", "DR": "Drought", "EQ": "Earthquake"}

_cache: dict = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fetch(name: str, mode: str, url: str, loader, key, refresh: bool):
    """Runs one source loader and reports how it went; live results are cached by `key`."""
    if mode == "live" and not refresh:
        with _lock:
            hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_SECONDS:
            data, status = hit[1], dict(hit[2], cached=True)
            return data, status
    started = time.perf_counter()
    try:
        data, ok, error = loader(), True, None
    except Exception as exc:  # a source that cannot be reached is reported, never fatal
        data, ok, error = None, False, f"{type(exc).__name__}: {exc}"[:200]
    status = {"name": name, "mode": mode, "url": url, "ok": ok, "error": error, "cached": False,
              "seconds": round(time.perf_counter() - started, 2), "fetched_at": _now()}
    if mode == "live" and ok:
        with _lock:
            _cache[key] = (time.time(), data, status)
    return data, status


def _disasters(events, start: date, end: date, rules: ContextRules) -> list[dict]:
    lookback = start - timedelta(days=rules.disaster_lookback_days)
    out = []
    for e in sorted(events or [], key=lambda e: e.start):
        km = _distance_km(DEFAULT_AREA.latitude, DEFAULT_AREA.longitude, e.latitude, e.longitude)
        near = math.isnan(km) or km <= rules.disaster_radius_km
        severe = e.alert_level in ("Orange", "Red")
        in_window = not (e.end < lookback or e.start > end)
        counts = in_window and (severe or near)          # same rule as signals.disaster_signals
        out.append({"type": EVENT_NAMES.get(e.event_type, e.event_type), "alert_level": e.alert_level,
                    "start": e.start.isoformat(), "end": e.end.isoformat(), "name": e.name,
                    "distance_km": None if math.isnan(km) else round(km), "near_area": near,
                    "counts_for_window": counts,
                    "signal": ("alert" if severe else "watch") if counts else None})
    return out


def _food(prices: pd.DataFrame | None, end: date) -> dict:
    if prices is None or prices.empty:
        return {"commodities": [], "mom_median": [], "latest_month": None, "months_behind": None}
    d = prices[prices["admin2"].isin(DEFAULT_AREA.districts)]
    d = d[d["commodity"].str.lower().str.contains(STAPLE_PATTERN, regex=True)]
    d = d[d["date"] <= pd.Timestamp(end)]
    if d.empty:
        return {"commodities": [], "mom_median": [], "latest_month": None, "months_behind": None}
    d = d.assign(month=d["date"].dt.to_period("M"))
    latest = d["month"].max()
    d = d[d["month"] > latest - 24]                                   # last two years of data
    monthly = d.groupby(["commodity", "month"])["price"].median().unstack()
    units = d.groupby("commodity")["unit"].agg(lambda u: u.mode().iat[0])
    counts = monthly.notna().sum(axis=1).sort_values(ascending=False)
    chosen = []                                   # one item per staple (the best-covered), in the staples' order
    for keyword in STAPLE_KEYWORDS:
        match = [n for n in counts.index if counts[n] >= 6 and n not in chosen
                 and re.search(rf"\b{re.escape(keyword)}s?\b", n.lower())]
        if match:
            chosen.append(match[0])
    commodities = []
    for name in chosen[:6]:
        row = monthly.loc[name].dropna()
        commodities.append({"commodity": name, "unit": units.get(name, ""),
                            "points": [{"month": str(m), "price": round(float(v), 1)} for m, v in row.items()]})
    change = monthly.pct_change(axis=1, fill_method=None)
    mom = [{"month": str(m), "value": round(float(np.nanmedian(change[m])), 4), "commodities": int(change[m].notna().sum())}
           for m in change.columns if change[m].notna().any()]
    return {"commodities": commodities, "mom_median": mom, "latest_month": str(latest),
            "months_behind": (pd.Period(end, freq="M") - latest).n, "districts": list(DEFAULT_AREA.districts)}


def context_dashboard(start: date, end: date, offline: bool = False, refresh: bool = False) -> dict:
    rules = ContextRules()
    mode = "offline" if offline else "live"
    timeline_start = end - timedelta(days=TIMELINE_DAYS)

    if offline:
        events, gdacs = _fetch("GDACS disasters", "offline", "tests/fixtures/gdacs_sri_lanka_2025.json",
                               lambda: sources.parse_gdacs(json.loads((FIXTURES / "gdacs_sri_lanka_2025.json").read_text())),
                               None, refresh)
        prices, wfp = _fetch("WFP food prices", "offline", "tests/fixtures/wfp_food_prices_lka_east_sample.csv",
                             lambda: sources.parse_wfp_prices(FIXTURES / "wfp_food_prices_lka_east_sample.csv"), None, refresh)
        world, wb = _fetch("World Bank inflation", "offline", "tests/fixtures/worldbank_lka_inflation.json",
                           lambda: _worldbank(json.loads((FIXTURES / "worldbank_lka_inflation.json").read_text())),
                           None, refresh)
    else:
        events, gdacs = _fetch("GDACS disasters", "live", sources.GDACS_URL,
                               lambda: sources.fetch_gdacs(DEFAULT_AREA.country, timeline_start, end),
                               ("gdacs", timeline_start, end), refresh)
        prices, wfp = _fetch("WFP food prices", "live", sources.WFP_LKA_URL, sources.fetch_wfp_prices, ("wfp",), refresh)
        world, wb = _fetch("World Bank inflation", "live", sources.WORLD_BANK_URL.format(country="LKA",
                           indicator="FP.CPI.TOTL.ZG"),
                           lambda: _worldbank(json.loads(sources.http_get(
                               sources.WORLD_BANK_URL.format(country="LKA", indicator="FP.CPI.TOTL.ZG"),
                               {"format": "json", "mrv": 12}))), ("worldbank",), refresh)
    ccpi, ccpi_status = _fetch("CCPI inflation", "file", "component3/context/data/ccpi_monthly.csv", sources.load_ccpi,
                               None, True)

    report = build_context_report(start, end, events=events or [], prices=prices, ccpi=ccpi, fetch=False)
    base = Thresholds()
    tightened = report.adjust(base)
    food = _food(prices, end)

    gdacs.update(records=len(events or []), latest=max((e.end for e in events or []), default=None))
    wfp.update(records=0 if prices is None else len(prices),
               latest=None if prices is None or prices.empty else prices["date"].max().date())
    ccpi_status.update(records=0 if ccpi is None else len(ccpi), latest=None if ccpi is None else str(ccpi["month"].max()))
    wb.update(records=len(world or []), latest=max((r["year"] for r in world or []), default=None))

    return jsonable({
        "mode": mode, "window": {"start": start.isoformat(), "end": end.isoformat()},
        "area": {"name": DEFAULT_AREA.name, "districts": list(DEFAULT_AREA.districts),
                 "latitude": DEFAULT_AREA.latitude, "longitude": DEFAULT_AREA.longitude},
        "sources": [{**s, "latest": None if s.get("latest") is None else str(s["latest"])}
                    for s in (gdacs, wfp, ccpi_status, wb)],
        "level": "alert" if report.heightened else ("watch" if report.signals else "none"),
        "explanation": report.explanation(),
        "signals": [{"source": s.kind, "level": s.level, "summary": s.summary} for s in report.signals],
        "effect": {"tighten_factor": rules.tighten_factor, "active": report.heightened,
                   "limits": [{"name": "PSI (each input)", "normal": base.psi_flag, "now": tightened.psi_flag},
                              {"name": "Missing-data change", "normal": base.missingness_delta_flag,
                               "now": tightened.missingness_delta_flag},
                              {"name": "KS p-value", "normal": base.ks_alpha, "now": tightened.ks_alpha}]},
        "rules": {"disaster_lookback_days": rules.disaster_lookback_days, "disaster_radius_km": rules.disaster_radius_km,
                  "food_mom_watch": rules.food_mom_watch, "food_mom_alert": rules.food_mom_alert,
                  "food_inflation_watch": rules.food_inflation_watch, "food_inflation_alert": rules.food_inflation_alert},
        "disasters": _disasters(events, start, end, rules),
        "food": food,
        "ccpi": _ccpi_series(ccpi),
        "worldbank": sorted(world or [], key=lambda r: r["year"]),
    })


def _worldbank(payload) -> list[dict]:
    rows = payload[1] if len(payload) > 1 and payload[1] else []
    return [{"year": int(r["date"]), "value": round(float(r["value"]), 2)} for r in rows if r.get("value") is not None]


def _ccpi_series(ccpi: pd.DataFrame | None) -> list[dict]:
    """Every month from the first to the last entry; months without a release stay empty so charts show the gap."""
    if ccpi is None or ccpi.empty:
        return []
    by_month = {r["month"]: r for _, r in ccpi.iterrows()}
    months = pd.period_range(ccpi["month"].min(), ccpi["month"].max(), freq="M")
    return [{"month": str(m), "headline": by_month[m]["headline_yoy"] if m in by_month else None,
             "food": by_month[m]["food_yoy"] if m in by_month else None} for m in months]
