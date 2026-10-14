"""Load canonical demo outcomes (1-based visit_number).

Shared by seed and DemoModelAdapter so seeded predictions match re-inference.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONTRACTS = Path("/contracts") if Path("/contracts").exists() else Path(__file__).resolve().parents[3] / "packages" / "contracts"


@lru_cache(maxsize=1)
def load_demo_outcomes() -> dict:
    path = CONTRACTS / "demo_outcomes.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_demo_outcome(pid: str, visit_number: int) -> tuple[str, str, float] | None:
    """Return (status, severity, score) for a 1-based visit_number, or None."""
    data = load_demo_outcomes()
    child = data.get("outcomes", {}).get(pid)
    if not child:
        return None
    row = child.get(str(visit_number))
    if not row:
        return None
    return row["status"], row["severity"], float(row["score"])


def demo_projection_version() -> str:
    return load_demo_outcomes().get("projection_version", "demo-latent-projection-v1")


def demo_confidence() -> str:
    """Non-calibrated demo confidence band required by schema."""
    return load_demo_outcomes().get("confidence", "moderate")
