"""Train baseline classifiers. Fitted transformers never see test data."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ml.evaluation.metrics import classification_metrics, write_reports
from ml.models.baselines import build_lightgbm, build_random_forest, build_xgboost
from ml.preprocessing.pipeline import assert_no_forbidden_columns, fit_preprocessor, group_split

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "ml/configs/baseline.yaml"))
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    rng = np.random.default_rng(cfg["seed"])
    data_path = ROOT / cfg["data"]["path"]
    if not data_path.exists():
        from ml.data.make_synthetic import write_synthetic

        write_synthetic(data_path)
    frame = pd.read_csv(data_path)
    assert_no_forbidden_columns(frame)
    label = cfg["label_column"]
    group = cfg["data"]["group_column"]
    trainval, test = group_split(frame, group, label, cfg["split"]["test_size"], cfg["seed"])
    train, val = group_split(trainval, group, label, cfg["split"]["val_size"], cfg["seed"] + 1)
    numeric = [c for c in train.columns if train[c].dtype != object and c not in {label, group, "visit_date"}]
    categorical = [c for c in train.columns if train[c].dtype == object and c not in {label, group, "visit_date"}]
    pre = fit_preprocessor(train, numeric, categorical)
    x_train, y_train = pre.transform(train), train[label]
    x_test, y_test = pre.transform(test), test[label]
    builders = {
        "random_forest": lambda: build_random_forest(**cfg["models"]["random_forest"], random_state=cfg["seed"]),
        "xgboost": lambda: build_xgboost(**cfg["models"]["xgboost"], random_state=cfg["seed"]),
        "lightgbm": lambda: build_lightgbm(**cfg["models"]["lightgbm"], random_state=cfg["seed"]),
    }
    report = {"models": {}, "seed": cfg["seed"], "split": "group_aware", "n_train": len(train), "n_test": len(test)}
    out_dir = ROOT / cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, builder in builders.items():
        model = builder()
        t0 = time.perf_counter()
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        latency = (time.perf_counter() - t0) * 1000 / max(len(test), 1)
        proba = model.predict_proba(x_test) if hasattr(model, "predict_proba") else None
        metrics = classification_metrics(y_test, pred, proba)
        metrics["latency_ms"] = latency
        report["models"][name] = metrics
        import joblib

        joblib.dump({"model": model, "preprocessor": pre}, out_dir / f"{name}.joblib")
    write_reports(report, ROOT / "ml/artifacts")
    (out_dir / "last_run.json").write_text(json.dumps({"ok": True, "models": list(report["models"])}, indent=2))
    print(json.dumps({k: v.get("f1_macro") for k, v in report["models"].items()}, indent=2))


if __name__ == "__main__":
    main()
