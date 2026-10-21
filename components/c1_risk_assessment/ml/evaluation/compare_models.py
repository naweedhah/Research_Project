from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    report = ROOT / "ml/artifacts/evaluation_report.json"
    if not report.exists():
        print("No experimental result available. Run: python -m ml.training.train_baselines")
        return
    data = json.loads(report.read_text())
    print(json.dumps({k: v.get("f1_macro") for k, v in data.get("models", {}).items()}, indent=2))


if __name__ == "__main__":
    main()
