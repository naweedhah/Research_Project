"""Command-line check of external context for a monitoring window.

  python -m component3.context.check --start 2025-11-01 --end 2025-12-31          # live sources
  python -m component3.context.check --start 2025-11-01 --end 2025-12-31 --offline  # bundled sample data only
  python -m component3.context.check --background                                  # + World Bank yearly inflation
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from component3.context import sources
from component3.context.signals import build_context_report

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def main() -> None:
    ap = argparse.ArgumentParser(description="Show external context signals (disasters, food prices, inflation).")
    ap.add_argument("--start", type=date.fromisoformat, default=date.today().replace(day=1))
    ap.add_argument("--end", type=date.fromisoformat, default=date.today())
    ap.add_argument("--offline", action="store_true", help="use the bundled sample GDACS/WFP files, no internet")
    ap.add_argument("--background", action="store_true", help="also print World Bank yearly inflation")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    kwargs = {}
    if a.offline:
        kwargs["events"] = sources.parse_gdacs(json.loads((FIXTURES / "gdacs_sri_lanka_2025.json").read_text()))
        kwargs["prices"] = sources.parse_wfp_prices(FIXTURES / "wfp_food_prices_lka_east_sample.csv")
        kwargs["fetch"] = False
    report = build_context_report(a.start, a.end, **kwargs)

    if a.json:
        print(json.dumps(report.as_evidence(), indent=2))
    else:
        print(report.explanation())
        for s in report.signals:
            print(f"  - {s.kind:10s} {s.level:5s} {s.summary}")
    if a.background and not a.offline:
        try:
            print("\nWorld Bank yearly inflation (background only):")
            print(sources.fetch_worldbank_indicator().to_string(index=False))
        except Exception as exc:
            print(f"World Bank API unavailable: {exc}")


if __name__ == "__main__":
    main()
