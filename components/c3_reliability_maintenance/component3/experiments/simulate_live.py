"""Simulate a screening round against the live C3 API, using real children the live model was never trained on.

Sends a batch of held-out children (optionally under one of the experiment shifts), then, unless --no-outcomes, sends
their observed outcomes as if they had arrived a year later. Only the running backend sees the records.

    python -m component3.experiments.simulate_live --records 300
    python -m component3.experiments.simulate_live --shift prevalence:0.4 --from 2025-12-01 --to 2025-12-31 --context offline
    python -m component3.experiments.simulate_live --shift missing_weight:0.75 --no-outcomes
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

import numpy as np
from sklearn.model_selection import train_test_split

from component3.data import load_prediction_data
from component3.experiments.run_real import shift_grid


def held_out(target: str, seed: int = 0):
    """Children outside the live model's training split (the live service trains v1.0 on the same 45% split)."""
    data = load_prediction_data(target)
    _, X_rest, _, y_rest = train_test_split(data.X, data.y, train_size=0.45, stratify=data.y, random_state=seed)
    return X_rest.reset_index(drop=True), np.asarray(y_rest)


def post(api: str, path: str, body: dict) -> dict:
    request = urllib.request.Request(api.rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"content-type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(request, timeout=600))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{path}: HTTP {exc.code} {exc.read().decode()}") from None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--target", default="underweight")
    ap.add_argument("--records", type=int, default=300)
    ap.add_argument("--shift", default="none:0", help="family:strength from the experiment grid, e.g. prevalence:0.4")
    ap.add_argument("--seed", type=int, default=1, help="which children are sampled")
    ap.add_argument("--batch-id")
    ap.add_argument("--area")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--context", choices=["live", "offline", "none"], default="live")
    ap.add_argument("--no-outcomes", action="store_true", help="only submit the batch (outcomes still pending)")
    ap.add_argument("--auto-deploy", action="store_true", help="deploy a verified candidate without approval")
    args = ap.parse_args()

    family, _, strength = args.shift.partition(":")
    shift = next((s for s in shift_grid() if s.family == family and s.strength == float(strength or 0)), None)
    if shift is None:
        raise SystemExit("unknown shift; choose one of: " + ", ".join(f"{s.family}:{s.strength:g}" for s in shift_grid()))

    X, y = held_out(args.target)
    rng = np.random.default_rng(args.seed)
    take = rng.choice(len(X), size=min(args.records, len(X)), replace=False)
    X, y = shift.apply(X.iloc[take].reset_index(drop=True), y[take], rng)
    ids = [f"S{args.seed}-{i}" for i in range(len(X))]
    rows = [{"record_id": rid, **{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in row.items()}}
            for rid, row in zip(ids, X.to_dict("records"))]

    batch = post(args.api, "/maintenance/live/batches", {
        "records": rows, "batch_id": args.batch_id, "area": args.area, "collected_from": args.start,
        "collected_to": args.end, "context": args.context})
    c = batch["cycle"]
    print(f"batch {batch['batch_id']}: {batch['records']} children ({shift.label}) -> {c['decision'].upper()}: {c['reason']}")
    if c.get("possible_causes"):
        print("  possible causes:", "; ".join(c["possible_causes"]))
    if args.no_outcomes:
        return

    result = post(args.api, f"/maintenance/live/batches/{batch['batch_id']}/outcomes",
                  {"labels": {rid: int(v) for rid, v in zip(ids, y)}, "require_approval": not args.auto_deploy})
    if "post_deployment_check" in result:
        print("post-deployment check:", result["post_deployment_check"])
    c = result["cycle"]
    m = c["reliability"]["metrics"]
    print(f"outcomes ({result['outcomes']}): balanced accuracy {m.get('recall_macro')}, calibration error {m.get('ece')}"
          f" -> {c['decision'].upper()}: {c['reason']}")
    if c["candidate"]:
        v = c["verification"]
        state = "waiting for approval" if c["pending_approval"] else "deployed" if c["promoted"] else "rejected"
        print(f"  candidate {c['candidate']}: gate {'passed' if v['passed'] else 'failed ' + '; '.join(v['failures'])}"
              f" -> {state}; active model {c['model_after']}")


if __name__ == "__main__":
    main()
