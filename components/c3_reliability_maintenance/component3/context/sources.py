"""External context sources for C3: disasters, food prices, inflation and yearly background indicators.

All sources are free and need no API key. Network access goes through `http_get`, which callers (and tests) can
replace, so nothing here needs the internet to be tested.

  * GDACS (Global Disaster Alert and Coordination System): near real-time floods, cyclones, droughts, earthquakes.
  * WFP market prices via HDX: monthly retail prices by district and market (Sri Lanka incl. Ampara, Batticaloa).
    Note: published with a delay (latest month was September 2025 when checked in October 2026).
  * CCPI (Colombo Consumer Price Index): monthly inflation from CBSL/DCS press releases. There is no official API, so
    values are kept in data/ccpi_monthly.csv and updated once a month from the release.
  * World Bank Indicators API (v2): yearly, national indicators. Background context only; too slow for alerts.
"""

from __future__ import annotations

import io
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

import pandas as pd

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
WFP_LKA_URL = ("https://data.humdata.org/dataset/0298c598-d312-4771-b564-f4ac4d831f05/resource/"
               "3638f0d6-9969-48cf-a919-1d879d037ec6/download/wfp_food_prices_lka.csv")
WORLD_BANK_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
CCPI_FILE = Path(__file__).parent / "data" / "ccpi_monthly.csv"

Getter = Callable[[str, dict | None], bytes]


def http_get(url: str, params: dict | None = None, timeout: int = 30) -> bytes:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, safe=';')}"
    request = urllib.request.Request(url, headers={"User-Agent": "C3-reliability-monitor/0.1 (research)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


# ---------------------------------------------------------------- disasters (GDACS)

@dataclass(frozen=True)
class DisasterEvent:
    source: str
    event_type: str      # FL flood, TC tropical cyclone, DR drought, EQ earthquake
    alert_level: str     # Green / Orange / Red
    start: date
    end: date
    latitude: float
    longitude: float
    name: str
    url: str


def _day(value: str) -> date:
    return datetime.fromisoformat(value[:19]).date()


def parse_gdacs(payload: dict) -> list[DisasterEvent]:
    events = []
    for feature in payload.get("features", []):
        p = feature.get("properties", {})
        lon, lat = feature.get("geometry", {}).get("coordinates", [None, None])[:2]
        url = p.get("url", {})
        events.append(DisasterEvent(
            source="GDACS", event_type=p.get("eventtype", ""), alert_level=p.get("alertlevel", ""),
            start=_day(p["fromdate"]), end=_day(p.get("todate") or p["fromdate"]),
            latitude=float(lat) if lat is not None else float("nan"),
            longitude=float(lon) if lon is not None else float("nan"),
            name=p.get("name", ""), url=url.get("report", "") if isinstance(url, dict) else str(url)))
    return events


def fetch_gdacs(country: str, start: date, end: date, event_types: tuple[str, ...] = ("FL", "TC", "DR", "EQ"),
                getter: Getter = http_get) -> list[DisasterEvent]:
    raw = getter(GDACS_URL, {"eventlist": ";".join(event_types), "country": country,
                             "fromdate": start.isoformat(), "todate": end.isoformat()})
    return parse_gdacs(json.loads(raw)) if raw.strip() else []


# ---------------------------------------------------------------- food prices (WFP via HDX)

def parse_wfp_prices(source: str | Path | bytes) -> pd.DataFrame:
    """Reads a WFP/HDX price CSV. The second line is an HXL tag row (#date, #adm1 ...) and is skipped."""
    if isinstance(source, bytes):
        source = io.StringIO(source.decode("utf-8"))
    d = pd.read_csv(source, skiprows=[1])
    d["date"] = pd.to_datetime(d["date"])
    d["price"] = pd.to_numeric(d["price"], errors="coerce")
    return d.dropna(subset=["price"])


def fetch_wfp_prices(url: str = WFP_LKA_URL, getter: Getter = http_get) -> pd.DataFrame:
    return parse_wfp_prices(getter(url, None))


# ---------------------------------------------------------------- inflation (CCPI monthly file)

def load_ccpi(path: Path = CCPI_FILE) -> pd.DataFrame:
    d = pd.read_csv(path, comment="#")
    d["month"] = pd.PeriodIndex(d["month"], freq="M")
    return d.sort_values("month").reset_index(drop=True)


# ---------------------------------------------------------------- yearly background (World Bank)

def fetch_worldbank_indicator(country: str = "LKA", indicator: str = "FP.CPI.TOTL.ZG", most_recent: int = 5,
                              getter: Getter = http_get) -> pd.DataFrame:
    """Yearly national values, e.g. FP.CPI.TOTL.ZG = consumer-price inflation (%). Background context only."""
    raw = getter(WORLD_BANK_URL.format(country=country, indicator=indicator), {"format": "json", "mrv": most_recent})
    payload = json.loads(raw)
    rows = payload[1] if len(payload) > 1 and payload[1] else []
    return pd.DataFrame([{"year": int(r["date"]), "value": r["value"]} for r in rows if r.get("value") is not None])
