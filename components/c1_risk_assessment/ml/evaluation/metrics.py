from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)


def classification_metrics(y_true, y_pred, y_proba=None, labels=None) -> dict:
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "report": classification_report(y_true, y_pred, zero_division=0, output_dict=True),
    }
    if y_proba is not None:
        try:
            out["roc_auc_ovr"] = float(roc_auc_score(y_true, y_proba, multi_class="ovr"))
        except ValueError:
            out["roc_auc_ovr"] = None
        try:
            out["pr_auc"] = float(average_precision_score(y_true, y_proba, average="macro"))
        except Exception:  # noqa: BLE001
            out["pr_auc"] = None
    return out


def write_reports(metrics: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation_report.json").write_text(json.dumps(metrics, indent=2))
    rows = []
    for name, values in metrics.get("models", {}).items():
        rows.append(
            {
                "model": name,
                "macro_f1": values.get("f1_macro"),
                "recall_macro": values.get("recall_macro"),
                "balanced_accuracy": values.get("balanced_accuracy"),
                "brier": values.get("brier"),
                "latency_ms": values.get("latency_ms"),
            }
        )
    if rows:
        import csv

        with (output_dir / "evaluation_metrics.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
