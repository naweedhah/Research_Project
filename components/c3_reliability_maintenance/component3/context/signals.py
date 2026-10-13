"""Turns external context (disasters, food prices, inflation) into signals for a monitoring window.

Context is a *leading indicator*: it tells C3 that the population may be about to change and suggests why drift was
seen. It never triggers maintenance by itself (data changed != model broken). When an alert-level signal is active,
C3 watches more closely: drift thresholds are tightened for that cycle and the signals are attached to the cycle's
evidence as possible causes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

import numpy as np
import pandas as pd

from component3.config import Thresholds
from component3.context import sources


@dataclass(frozen=True)
class AreaConfig:
    name: str
    districts: tuple[str, ...]
    latitude: float
    longitude: float
    country: str = "Sri Lanka"


# Approximate centre of the Kalmunai / Addalaichenai PHM areas (Ampara district, next to Batticaloa).
DEFAULT_AREA = AreaConfig("Kalmunai / Addalaichenai PHM areas", ("Ampara", "Batticaloa"), 7.42, 81.82)

STAPLE_KEYWORDS = ("rice", "egg", "coconut", "lentil", "dhal", "wheat flour", "fish", "milk")


@dataclass(frozen=True)
class ContextRules:
    disaster_lookback_days: int = 90      # nutrition effects of a disaster appear over the following months
    disaster_radius_km: float = 250.0     # GDACS often places national events at a central point
    food_mom_watch: float = 0.05
    food_mom_alert: float = 0.10
    food_yoy_alert: float = 0.20
    food_inflation_watch: float = 5.0     # CCPI food, year-on-year %
    food_inflation_alert: float = 10.0
    headline_jump_watch: float = 3.0      # percentage-point rise over 3 months
    tighten_factor: float = 0.75          # drift thresholds multiplied by this while an alert is active


@dataclass(frozen=True)
class ContextSignal:
    kind: str          # disaster | food_price | inflation
    level: str         # watch | alert
    summary: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContextReport:
    area: AreaConfig
    window_start: date
    window_end: date
    signals: tuple[ContextSignal, ...]
    sources_unavailable: tuple[str, ...] = ()
    rules: ContextRules = ContextRules()

    @property
    def heightened(self) -> bool:
        return any(s.level == "alert" for s in self.signals)

    def adjust(self, thresholds: Thresholds) -> Thresholds:
        """Tighter drift detection while an alert is active. Reliability and promotion limits are not changed."""
        if not self.heightened:
            return thresholds
        f = self.rules.tighten_factor
        return replace(thresholds, psi_flag=thresholds.psi_flag * f,
                       missingness_delta_flag=thresholds.missingness_delta_flag * f,
                       ks_alpha=min(0.10, thresholds.ks_alpha / f))

    def possible_causes(self) -> list[str]:
        return [s.summary for s in self.signals]

    def as_evidence(self) -> dict:
        return {"window": f"{self.window_start} to {self.window_end}", "heightened": self.heightened,
                "signals": [{"kind": s.kind, "level": s.level, "summary": s.summary} for s in self.signals],
                "sources_unavailable": list(self.sources_unavailable)}

    def explanation(self) -> str:
        if not self.signals:
            text = f"No external context signals for {self.area.name} ({self.window_start} to {self.window_end})."
        else:
            state = "ALERT: monitoring tightened" if self.heightened else "watch only"
            text = f"{state}. " + " | ".join(f"[{s.level}] {s.summary}" for s in self.signals)
        if self.sources_unavailable:
            text += f" (unavailable: {', '.join(self.sources_unavailable)})"
        return text


def _distance_km(lat1, lon1, lat2, lon2) -> float:
    if any(math.isnan(v) for v in (lat1, lon1, lat2, lon2)):
        return float("nan")
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def disaster_signals(events: list[sources.DisasterEvent], start: date, end: date, area: AreaConfig = DEFAULT_AREA,
                     rules: ContextRules = ContextRules()) -> list[ContextSignal]:
    out = []
    lookback = start - timedelta(days=rules.disaster_lookback_days)
    names = {"FL": "Flood", "TC": "Tropical cyclone", "DR": "Drought", "EQ": "Earthquake"}
    for e in events:
        if e.end < lookback or e.start > end:
            continue
        km = _distance_km(area.latitude, area.longitude, e.latitude, e.longitude)
        severe = e.alert_level in ("Orange", "Red")
        near = math.isnan(km) or km <= rules.disaster_radius_km
        if not severe and not near:
            continue
        level = "alert" if severe else "watch"
        out.append(ContextSignal("disaster", level,
                                 f"{names.get(e.event_type, e.event_type)} ({e.alert_level}) {e.start} to {e.end}: {e.name}",
                                 {"distance_km": None if math.isnan(km) else round(km), "url": e.url}))
    return out


def food_price_signals(prices: pd.DataFrame, as_of: date, area: AreaConfig = DEFAULT_AREA,
                       rules: ContextRules = ContextRules()) -> list[ContextSignal]:
    """Median month-on-month and year-on-year change of staple-food prices in the area's districts."""
    d = prices[prices["admin2"].isin(area.districts)]
    d = d[d["commodity"].str.lower().str.contains("|".join(STAPLE_KEYWORDS))]
    d = d[d["date"] <= pd.Timestamp(as_of)]
    if d.empty:
        return []
    monthly = d.assign(month=d["date"].dt.to_period("M")).groupby(["commodity", "month"])["price"].median().unstack()
    latest = monthly.columns.max()
    prev, last_year = latest - 1, latest - 12
    mom = (monthly[latest] / monthly[prev] - 1).dropna() if prev in monthly.columns else pd.Series(dtype=float)
    yoy = (monthly[latest] / monthly[last_year] - 1).dropna() if last_year in monthly.columns else pd.Series(dtype=float)
    mom_med = float(np.median(mom)) if len(mom) else float("nan")
    yoy_med = float(np.median(yoy)) if len(yoy) else float("nan")
    lag = (pd.Period(as_of, freq="M") - latest).n
    details = {"latest_month": str(latest), "months_behind": lag, "mom_median": round(mom_med, 3),
               "yoy_median": None if math.isnan(yoy_med) else round(yoy_med, 3), "commodities": len(mom)}
    level = None
    if mom_med >= rules.food_mom_alert or (not math.isnan(yoy_med) and yoy_med >= rules.food_yoy_alert):
        level = "alert"
    elif mom_med >= rules.food_mom_watch:
        level = "watch"
    if level is None:
        return []
    yoy_text = "" if math.isnan(yoy_med) else f", {yoy_med:+.0%} on a year earlier"
    return [ContextSignal("food_price", level,
                          f"Staple food prices in {'/'.join(area.districts)} {mom_med:+.0%} month-on-month{yoy_text} "
                          f"(latest available month {latest}, {lag} months behind)", details)]


def inflation_signals(ccpi: pd.DataFrame, as_of: date, rules: ContextRules = ContextRules()) -> list[ContextSignal]:
    d = ccpi[ccpi["month"] <= pd.Period(as_of, freq="M")]
    if d.empty:
        return []
    latest = d.iloc[-1]
    out = []
    food = latest.get("food_yoy")
    if pd.notna(food) and food >= rules.food_inflation_watch:
        level = "alert" if food >= rules.food_inflation_alert else "watch"
        out.append(ContextSignal("inflation", level, f"CCPI food inflation {food:.1f}% year-on-year ({latest['month']})",
                                 {"month": str(latest["month"]), "food_yoy": float(food)}))
    earlier = d[d["month"] <= latest["month"] - 3]
    if not earlier.empty and pd.notna(latest["headline_yoy"]):
        jump = float(latest["headline_yoy"] - earlier.iloc[-1]["headline_yoy"])
        if jump >= rules.headline_jump_watch:
            out.append(ContextSignal("inflation", "watch",
                                     f"CCPI headline inflation up {jump:.1f} points in 3 months to {latest['headline_yoy']:.1f}%",
                                     {"jump_points": round(jump, 1)}))
    return out


def build_context_report(start: date, end: date, area: AreaConfig = DEFAULT_AREA, rules: ContextRules = ContextRules(),
                         events: list | None = None, prices: pd.DataFrame | None = None,
                         ccpi: pd.DataFrame | None = None, fetch: bool = True,
                         getter: sources.Getter = sources.http_get) -> ContextReport:
    """Collects all signals for a monitoring window. Sources that cannot be reached are listed, never fatal."""
    unavailable = []
    if events is None and fetch:
        try:
            events = sources.fetch_gdacs(area.country, start - timedelta(days=rules.disaster_lookback_days), end,
                                         getter=getter)
        except Exception:
            unavailable.append("GDACS disasters")
    if prices is None and fetch:
        try:
            prices = sources.fetch_wfp_prices(getter=getter)
        except Exception:
            unavailable.append("WFP food prices")
    if ccpi is None:
        try:
            ccpi = sources.load_ccpi()
        except Exception:
            unavailable.append("CCPI file")
    signals = []
    if events:
        signals += disaster_signals(events, start, end, area, rules)
    if prices is not None and not prices.empty:
        signals += food_price_signals(prices, end, area, rules)
    if ccpi is not None and not ccpi.empty:
        signals += inflation_signals(ccpi, end, rules)
    return ContextReport(area, start, end, tuple(signals), tuple(unavailable), rules)
