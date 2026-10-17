"""Component 3 experiment results (aggregate numbers, reports and figures from components/.../results/)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.c3.service import C3_ROOT, jsonable

RESULTS = C3_ROOT / "results"


def _run_dir(run: str) -> Path:
    runs = {p.name: p for p in RESULTS.iterdir() if p.is_dir()} if RESULTS.exists() else {}
    if run not in runs:  # only listed folders, so a request can never reach other paths
        raise LookupError(f"no results run {run}")
    return runs[run]


def runs() -> list[dict]:
    out = []
    for path in sorted(p for p in RESULTS.iterdir() if p.is_dir()) if RESULTS.exists() else []:
        summary = path / "strategy_summary.csv"
        thresholds = path / "suggested_thresholds.json"
        out.append(jsonable({
            "run": path.name,
            "drift_limits": "calibrated" if path.name.endswith("_calibrated") else "conventional",
            "suggested_thresholds": json.loads(thresholds.read_text()) if thresholds.exists() else None,
            "strategy_summary": pd.read_csv(summary).to_dict("records") if summary.exists() else [],
            "report": f"/maintenance/results/{path.name}/report",
            "figures": [f"/maintenance/results/{path.name}/figures/{p.name}" for p in sorted(path.glob("*.png"))],
        }))
    return out


def report(run: str) -> str:
    path = _run_dir(run) / "REPORT.md"
    if not path.exists():
        raise LookupError(f"no report for {run}")
    return path.read_text()


def figure(run: str, name: str) -> Path:
    figures = {p.name: p for p in _run_dir(run).glob("*.png")}
    if name not in figures:
        raise LookupError(f"no figure {name} in {run}")
    return figures[name]
