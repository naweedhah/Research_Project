"""Experiment runner on the real linked 2025 -> 2026 data (spec §16-20, Tiers A-C).

For every shift (type x strength x seed) it records:
  * drift: what C3's monitors see (max PSI, max KS statistic, missingness change, prediction PSI);
  * harm: how much the deployed model actually got worse, measured on a large pool of unseen children;
  * maintenance: what each strategy decided, what it cost, and how the resulting model performs on a held-out test
    set that the verification gate never saw.

Then it analyses whether drift predicts harm (regression and per-monitor ROC-AUC, idea 1), suggests data-driven
monitor thresholds (smallest drift that coincides with harm), and compares strategies including action cost and
periodic retraining (idea 5).

Usage:  python -m component3.experiments.run_real [--target underweight] [--seeds 5] [--out results/c3_underweight]
Data is read from C3_DATA_DIR (see component3.data.real_data); results contain aggregates only, no child records.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from component3.assess.metrics import classification_metrics
from component3.assess.subgroups import sex_age_groups
from component3.config import ACTION_COST, PromotionCriteria, Thresholds, calibrated_thresholds
from component3.data import CATEGORICAL, NUMERIC, load_prediction_data
from component3.experiments import stress_scenarios as ss
from component3.experiments.run_comparison import fit_initial_model
from component3.experiments.strategies import STRATEGY_DECISION_FNS, build_orchestrator
from component3.models import standin_factory
from component3.monitor.monitor import run_monitoring
from component3.registry.registry import ModelRegistry
from component3.validate import default_validator

HARM_TOLERANCE = 0.05       # drop in balanced accuracy that counts as harm
MIN_SENSITIVITY = 0.65      # floor for sensitivity (detecting true cases)
CLASSES = np.array([0, 1])
DRIFT_COLUMNS = ["max_psi", "max_ks", "max_missing_delta", "prediction_psi"]
DRIFT_MODE = {"mode": "conventional"}  # "calibrated" uses config.calibrated_thresholds() drift limits


# ---------------------------------------------------------------- shifts

def measurement_error(height_sd_cm: float, weight_sd_kg: float) -> ss.ScenarioFn:
    """Random measurement error in height and weight, propagated to the z-scores computed from them
    (first-order: ~3.5 cm per HAZ unit, ~1.4 kg per WAZ unit, ~1.2 kg per WHZ unit at these ages)."""
    def _apply(X, y, rng):
        X = X.copy()
        e_h = rng.normal(0, height_sd_cm, len(X))
        e_w = rng.normal(0, weight_sd_kg, len(X))
        X["Height_cm_2025"] += e_h
        X["Weight_kg_2025"] += e_w
        X["HAZ_2025"] += e_h / 3.5
        X["WAZ_2025"] += e_w / 1.4
        X["WHZ_2025"] += e_w / 1.2 - 0.25 * e_h / 3.5
        return X, y
    return _apply


def scale_bias(offset_kg: float) -> ss.ScenarioFn:
    """Systematic weighing error (e.g. an uncalibrated scale reading low), propagated to WAZ and WHZ."""
    def _apply(X, y, rng):
        X = X.copy()
        X["Weight_kg_2025"] += offset_kg
        X["WAZ_2025"] += offset_kg / 1.4
        X["WHZ_2025"] += offset_kg / 1.2
        return X, y
    return _apply


@dataclass(frozen=True)
class Shift:
    family: str
    category: str
    strength: float
    label: str
    apply: ss.ScenarioFn


def shift_grid() -> list[Shift]:
    g = [Shift("none", "-", 0.0, "no shift", lambda X, y, rng: (X, y))]
    for r in (0.1, 0.25, 0.5, 0.75):
        g.append(Shift("missing_weight", "A", r, f"{r:.0%} weights missing",
                       ss.inject_missingness(["Weight_kg_2025", "WAZ_2025", "WHZ_2025"], r)))
    for h, w in ((1.0, 0.3), (2.0, 0.6), (4.0, 1.2)):
        g.append(Shift("measurement_error", "A", h, f"height SD {h} cm, weight SD {w} kg", measurement_error(h, w)))
    for r in (0.05, 0.2):
        g.append(Shift("impossible_values", "A", r, f"{r:.0%} weights recorded 5x too high",
                       ss.inject_out_of_range_values(["Weight_kg_2025", "WAZ_2025"], factor=5.0, rate=r)))
    for kg in (-0.25, -0.5, -1.0):
        g.append(Shift("scale_bias", "A", abs(kg), f"scale reads {abs(kg)} kg low", scale_bias(kg)))
    for s in (0.5, 1.0, 1.5):
        g.append(Shift("younger_population", "B", s, f"age tilt {s}", ss.shift_population("Age_months_2025", -s)))
        g.append(Shift("poorer_growth_population", "B", s, f"WAZ tilt {s}", ss.shift_population("WAZ_2025", -s)))
    for p in (0.05, 0.25, 0.40):
        g.append(Shift("prevalence", "C", p, f"prevalence {p:.0%}", ss.shift_label_prevalence({0: 1 - p, 1: p})))
    g.append(Shift("field_dropped", "D", 1.0, "birth weight not collected", ss.make_feature_unavailable(["Birth_Weight_g"])))
    g.append(Shift("field_dropped", "D", 2.0, "WHZ not computed", ss.make_feature_unavailable(["WHZ_2025"])))
    return g


# ---------------------------------------------------------------- helpers

def evaluate(model, X: pd.DataFrame, y: np.ndarray) -> dict:
    m = classification_metrics(np.asarray(y), model.predict(X), model.predict_proba(X), CLASSES)
    return {"bal_acc": m["recall_macro"], "sensitivity": m["recall_per_class"][1], "auroc": m["auroc"], "ece": m["ece"]}


def drift_summary(ref: pd.DataFrame, cur: pd.DataFrame, model, schema, thresholds) -> dict:
    rep = run_monitoring(ref, cur, schema, thresholds, model.predict(ref), model.predict(cur))
    psi = [r.psi_value for r in rep.feature_results if np.isfinite(r.psi_value)]
    ks = [r.ks_statistic for r in rep.feature_results if r.ks_statistic is not None and np.isfinite(r.ks_statistic)]
    return {"max_psi": max(psi) if psi else 0.0, "max_ks": max(ks) if ks else 0.0,
            "max_missing_delta": max(r.missingness_delta for r in rep.feature_results),
            "prediction_psi": rep.prediction_psi or 0.0, "n_flagged": len(rep.flagged_features()),
            "any_flagged": rep.any_flagged}


def thresholds_from_baseline(baseline: dict) -> tuple[Thresholds, PromotionCriteria]:
    """Acceptance limits anchored to the model's validated performance at deployment (cf. Augur: thresholds set at
    development time), replacing the generic placeholders in config.py."""
    tau = baseline["bal_acc"] - HARM_TOLERANCE
    cal = max(baseline["ece"] + 0.05, 0.08)
    limits = dict(reliability_tau=tau, calibration_tau=cal, min_minority_recall=MIN_SENSITIVITY,
                  minority_classes=(1,), min_labeled_for_retrain=100, operating_sensitivity=0.80)
    thr = calibrated_thresholds(**limits) if DRIFT_MODE["mode"] == "calibrated" else Thresholds(**limits)
    crit = PromotionCriteria(min_recall_macro=tau, min_minority_recall=MIN_SENSITIVITY, max_ece=cal, max_brier=0.35,
                             max_regression=0.02, minority_classes=(1,))
    return thr, crit


def is_harmful(baseline: dict, shifted: dict, thr: Thresholds) -> bool:
    return (baseline["bal_acc"] - shifted["bal_acc"] > HARM_TOLERANCE or shifted["ece"] > thr.calibration_tau
            or shifted["sensitivity"] < MIN_SENSITIVITY)


@dataclass
class Setting:
    """One deployment: an initial model, its reference data and four disjoint post-deployment sets."""
    name: str
    model: object
    X_ref: pd.DataFrame
    y_ref: np.ndarray
    parts: dict  # name -> (X, y) for current, adapt, verify, test
    baseline_pool: tuple[pd.DataFrame, np.ndarray]  # in-distribution data for the harm baseline


def split_parts(X, y, seed, sizes=(0.27, 0.27, 0.23, 0.23)):
    names = ["current", "adapt", "verify", "test"]
    parts, rest_X, rest_y, remaining = {}, X, y, 1.0
    for name, size in zip(names[:-1], sizes[:-1]):
        a_X, rest_X, a_y, rest_y = train_test_split(rest_X, rest_y, train_size=size / remaining, stratify=rest_y,
                                                    random_state=seed)
        parts[name] = (a_X.reset_index(drop=True), np.asarray(a_y))
        remaining -= size
    parts["test"] = (rest_X.reset_index(drop=True), np.asarray(rest_y))
    return parts


def synthetic_setting(data, factory, seed) -> Setting:
    X_ref, X_rest, y_ref, y_rest = train_test_split(data.X, data.y, train_size=0.45, stratify=data.y, random_state=seed)
    model = fit_initial_model(factory, X_ref.reset_index(drop=True), np.asarray(y_ref), data.schema)
    parts = split_parts(X_rest, y_rest, seed)
    pool = (pd.concat([parts[k][0] for k in parts], ignore_index=True), np.concatenate([parts[k][1] for k in parts]))
    return Setting(f"seed{seed}", model, X_ref.reset_index(drop=True), np.asarray(y_ref), parts, pool)


def phm_setting(data, factory, phm, seed) -> Setting:
    inside = data.phm != phm
    X_in, y_in = data.X[inside].reset_index(drop=True), data.y[inside]
    X_tr, X_val, y_tr, y_val = train_test_split(X_in, y_in, test_size=0.2, stratify=y_in, random_state=seed)
    model = fit_initial_model(factory, X_tr.reset_index(drop=True), np.asarray(y_tr), data.schema)
    parts = split_parts(data.X[~inside].reset_index(drop=True), data.y[~inside], seed, sizes=(0.25, 0.25, 0.25, 0.25))
    return Setting(f"{phm}_seed{seed}", model, X_tr.reset_index(drop=True), np.asarray(y_tr), parts,
                   (X_val.reset_index(drop=True), np.asarray(y_val)))


def run_strategies(setting: Setting, shifted: dict, data, factory, thr, crit, harmful: bool, meta: dict) -> list[dict]:
    rows = []
    X_test, y_test = shifted["test"]
    before = evaluate(setting.model, X_test, y_test)
    for strategy in STRATEGY_DECISION_FNS:
        registry = ModelRegistry(setting.model)
        orch = build_orchestrator(strategy, registry, data.schema, thr, crit,
                                  validator=default_validator(), group_fn=sex_age_groups())
        cycle = orch.run_cycle(
            reference_data=setting.X_ref, current_data=shifted["current"][0], current_labels=shifted["current"][1],
            adapt_data=shifted["adapt"][0], adapt_labels=shifted["adapt"][1],
            verify_data=shifted["verify"][0], verify_labels=shifted["verify"][1],
            model_factory=factory, retrain_history=(setting.X_ref, setting.y_ref))
        after = evaluate(registry.active_model, X_test, y_test)
        action = cycle.decision.action.value
        corrective = action in ("recalibrate", "retrain")
        rows.append({**meta, "strategy": strategy, "harmful": harmful, "action": action,
                     "candidate": cycle.candidate is not None, "promoted": cycle.promoted,
                     "cost": ACTION_COST[action],
                     "unnecessary": corrective and not harmful, "missed": harmful and action == "no_action",
                     "escalated": action == "hold",
                     **{f"before_{k}": v for k, v in before.items()}, **{f"after_{k}": v for k, v in after.items()}})
    return rows


# ---------------------------------------------------------------- analyses

def drift_vs_harm(shifts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    d = shifts[shifts["family"] != "none"].copy()
    reg_rows = []
    y = d["harm_bal_acc"].to_numpy()
    for cols in [[c] for c in DRIFT_COLUMNS] + [DRIFT_COLUMNS]:
        Xd = d[cols].to_numpy()
        r2 = LinearRegression().fit(Xd, y).score(Xd, y)
        reg_rows.append({"predictors": " + ".join(cols), "r2_balanced_accuracy_drop": round(r2, 3)})
    det_rows = []
    harmful = d["harmful"].astype(int)
    for c in DRIFT_COLUMNS:
        auc = roc_auc_score(harmful, d[c]) if harmful.nunique() == 2 else np.nan
        det_rows.append({"monitor": c, "auroc_for_harm": round(auc, 3),
                         "corr_with_drop": round(np.corrcoef(d[c], y)[0, 1], 3)})
    flagged = d["any_flagged"].astype(bool)
    false_alarm = float((flagged & ~d["harmful"]).sum() / max(1, (~d["harmful"]).sum()))
    suggested = {}
    for c in ["max_psi", "max_ks", "prediction_psi"]:
        best = None
        for t in np.unique(d[c].round(3)):
            pred = d[c] >= t
            tpr = (pred & d["harmful"]).sum() / max(1, d["harmful"].sum())
            fpr = (pred & ~d["harmful"]).sum() / max(1, (~d["harmful"]).sum())
            if best is None or tpr - fpr > best[0]:
                best = (tpr - fpr, float(t), float(tpr), float(fpr))
        suggested[c] = {"threshold": best[1], "detects_harm": round(best[2], 2), "false_alarm": round(best[3], 2)}
    suggested["current_rules_false_alarm_rate"] = round(false_alarm, 2)
    return pd.DataFrame(reg_rows), pd.DataFrame(det_rows), suggested


def strategy_summary(runs: pd.DataFrame) -> pd.DataFrame:
    out = []
    for s, g in runs.groupby("strategy", sort=False):
        h, ok = g[g["harmful"]], g[~g["harmful"]]
        out.append({
            "strategy": s,
            "cycles": len(g),
            "intervention_rate": round(g["action"].isin(["recalibrate", "retrain"]).mean(), 3),
            "unnecessary_interventions_when_harmless": round(ok["unnecessary"].mean(), 3) if len(ok) else np.nan,
            "corrected_when_harmful": round(h["action"].isin(["recalibrate", "retrain"]).mean(), 3) if len(h) else np.nan,
            "escalated_when_harmful": round((h["action"] == "hold").mean(), 3) if len(h) else np.nan,
            "no_response_when_harmful": round((h["action"] == "no_action").mean(), 3) if len(h) else np.nan,
            "candidates_rejected": round((g["candidate"] & ~g["promoted"]).sum() / max(1, g["candidate"].sum()), 3),
            "mean_cost": round(g["cost"].mean(), 3),
            "test_bal_acc_after_harmful": round(h["after_bal_acc"].mean(), 3) if len(h) else np.nan,
            "gain_on_harmful": round((h["after_bal_acc"] - h["before_bal_acc"]).mean(), 3) if len(h) else np.nan,
            "test_ece_after_harmful": round(h["after_ece"].mean(), 3) if len(h) else np.nan,
            "test_sensitivity_after_harmful": round(h["after_sensitivity"].mean(), 3) if len(h) else np.nan,
            "change_on_harmless": round((ok["after_bal_acc"] - ok["before_bal_acc"]).mean(), 3) if len(ok) else np.nan,
        })
    return pd.DataFrame(out)


def figures(shifts: pd.DataFrame, runs: pd.DataFrame, summary: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = shifts[shifts["family"] != "none"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for fam, g in d.groupby("family"):
        ax.scatter(g["max_psi"], g["harm_bal_acc"], label=fam, s=22, alpha=0.75)
    ax.axhline(HARM_TOLERANCE, ls="--", c="grey", lw=1)
    ax.axvline(0.2, ls=":", c="grey", lw=1)
    ax.set_xlabel("Max PSI across features (what the monitor sees)")
    ax.set_ylabel("Drop in balanced accuracy (actual harm)")
    ax.set_title("Data changed vs model harmed")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "drift_vs_harm.png", dpi=150)
    plt.close(fig)

    fams = [f for f in d["family"].unique() if d[d["family"] == f]["strength"].nunique() > 1]
    fig, axes = plt.subplots(1, len(fams), figsize=(3 * len(fams), 3.2), sharey=True)
    for ax, fam in zip(np.atleast_1d(axes), fams):
        g = d[d["family"] == fam].groupby("strength")["harm_bal_acc"].agg(["mean", "std"]).reset_index()
        ax.errorbar(g["strength"], g["mean"], yerr=g["std"], marker="o", capsize=3)
        ax.axhline(HARM_TOLERANCE, ls="--", c="grey", lw=1)
        ax.set_title(fam.replace("_", " "), fontsize=9)
        ax.set_xlabel("shift strength")
    np.atleast_1d(axes)[0].set_ylabel("Drop in balanced accuracy")
    fig.tight_layout()
    fig.savefig(out / "harm_by_strength.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    s = summary.set_index("strategy")
    for ax, col, title in [(axes[0], "gain_on_harmful", "Balanced-accuracy gain when shift was harmful"),
                           (axes[1], "unnecessary_interventions_when_harmless", "Unnecessary interventions (harmless shifts)"),
                           (axes[2], "mean_cost", "Mean maintenance cost per cycle")]:
        ax.bar(s.index, s[col], color=["#888" if i != "adaptive" else "#2a7" for i in s.index])
        ax.set_title(title, fontsize=9)
        ax.tick_params(axis="x", rotation=30, labelsize=8)
    fig.tight_layout()
    fig.savefig(out / "strategy_comparison.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main

def _record(setting: Setting, shift: Shift, seed: int, kind: str, shifted: dict, data, factory) -> tuple[dict, list]:
    baseline = evaluate(setting.model, *setting.baseline_pool)
    thr, crit = thresholds_from_baseline(baseline)
    pool_X = pd.concat([shifted[k][0] for k in shifted], ignore_index=True)
    pool_y = np.concatenate([shifted[k][1] for k in shifted])
    after_shift = evaluate(setting.model, pool_X, pool_y)
    harmful = is_harmful(baseline, after_shift, thr)
    drift = drift_summary(setting.X_ref, shifted["current"][0], setting.model, data.schema, thr)
    meta = {"kind": kind, "setting": setting.name, "family": shift.family, "category": shift.category,
            "strength": shift.strength, "shift": shift.label, "seed": seed}
    shift_row = {**meta, **drift, "harmful": harmful, "harm_bal_acc": baseline["bal_acc"] - after_shift["bal_acc"],
                 "baseline_bal_acc": baseline["bal_acc"], "shifted_bal_acc": after_shift["bal_acc"],
                 "shifted_sensitivity": after_shift["sensitivity"], "shifted_auroc": after_shift["auroc"],
                 "baseline_ece": baseline["ece"], "shifted_ece": after_shift["ece"]}
    return shift_row, run_strategies(setting, shifted, data, factory, thr, crit, harmful, meta)


def _stress_task(target: str, seed: int, mode: str = "conventional") -> tuple[list, list]:
    from threadpoolctl import threadpool_limits
    DRIFT_MODE["mode"] = mode
    with threadpool_limits(1):
        data = load_prediction_data(target)
        factory = standin_factory(NUMERIC, CATEGORICAL)
        setting = synthetic_setting(data, factory, seed)
        shift_rows, run_rows = [], []
        for i, shift in enumerate(shift_grid()):
            rng = np.random.default_rng(1000 * seed + i)
            shifted = {k: shift.apply(X, y, rng) for k, (X, y) in setting.parts.items()}
            row, runs = _record(setting, shift, seed, "stress_test", shifted, data, factory)
            shift_rows.append(row)
            run_rows.extend(runs)
        return shift_rows, run_rows


def _area_task(target: str, phm: str, seed: int, mode: str = "conventional") -> tuple[list, list]:
    from threadpoolctl import threadpool_limits
    DRIFT_MODE["mode"] = mode
    with threadpool_limits(1):
        data = load_prediction_data(target)
        factory = standin_factory(NUMERIC, CATEGORICAL)
        setting = phm_setting(data, factory, phm, seed)
        shift = Shift("new_phm_area", "real", 0.0, f"unseen area {phm}", lambda X, y, rng: (X, y))
        row, runs = _record(setting, shift, seed, "real_area_shift", setting.parts, data, factory)
        return [row], runs


def run(target: str, seeds: int, out: Path, include_phm: bool = True, workers: int | None = None,
        mode: str = "conventional") -> None:
    import os
    from concurrent.futures import ProcessPoolExecutor, as_completed

    start = time.time()
    out.mkdir(parents=True, exist_ok=True)
    data = load_prediction_data(target)
    tasks = [(_stress_task, (target, s, mode)) for s in range(seeds)]
    if include_phm:
        tasks += [(_area_task, (target, phm, s, mode)) for phm in sorted(np.unique(data.phm)) for s in range(seeds)]
    shift_rows, run_rows = [], []
    with ProcessPoolExecutor(max_workers=workers or max(1, (os.cpu_count() or 2) - 1)) as pool:
        futures = [pool.submit(fn, *args) for fn, args in tasks]
        for n, fut in enumerate(as_completed(futures), start=1):
            rows, runs = fut.result()
            shift_rows.extend(rows)
            run_rows.extend(runs)
            print(f"{n}/{len(tasks)} tasks done ({time.time() - start:.0f}s)", flush=True)

    shifts = pd.DataFrame(shift_rows)
    runs = pd.DataFrame(run_rows)
    shifts.to_csv(out / "shifts.csv", index=False)
    runs.to_csv(out / "strategy_runs.csv", index=False)
    write_report(target, seeds, out, runtime=time.time() - start)


def write_report(target: str, seeds: int, out: Path, runtime: float | None = None) -> None:
    shifts = pd.read_csv(out / "shifts.csv")
    runs = pd.read_csv(out / "strategy_runs.csv")
    runs["missed"] = runs["harmful"] & (runs["action"] == "no_action")
    include_phm = (runs["kind"] == "real_area_shift").any()

    regression, detection, suggested = drift_vs_harm(shifts)
    summary = strategy_summary(runs)
    summary_stress = strategy_summary(runs[runs["kind"] == "stress_test"])
    summary_real = strategy_summary(runs[runs["kind"] == "real_area_shift"]) if include_phm else None
    by_family = shifts.groupby(["family", "shift"]).agg(
        runs=("harmful", "size"), harmful_share=("harmful", "mean"), mean_drop=("harm_bal_acc", "mean"),
        max_psi=("max_psi", "mean"), flagged_share=("any_flagged", "mean")).round(3).reset_index()
    summary.to_csv(out / "strategy_summary.csv", index=False)
    by_family.to_csv(out / "shift_summary.csv", index=False)
    regression.to_csv(out / "drift_harm_regression.csv", index=False)
    detection.to_csv(out / "monitor_harm_detection.csv", index=False)
    (out / "suggested_thresholds.json").write_text(json.dumps(suggested, indent=2))
    figures(shifts, runs, summary, out)

    lines = [f"# C3 experiment results: {target} (stand-in C1 model, real linked data)", "",
             f"Seeds: {seeds}. Shift runs: {len(shifts)} ({(shifts['kind'] == 'stress_test').sum()} stress tests, "
             f"{(shifts['kind'] == 'real_area_shift').sum()} real area shifts). Strategy cycles: {len(runs)}.",
             f"Harm = balanced-accuracy drop > {HARM_TOLERANCE}, calibration error above limit, or sensitivity < "
             f"{MIN_SENSITIVITY}. " + (f"Runtime {runtime:.0f}s." if runtime else ""), "",
             "## Strategy comparison (all shifts)", "", summary.to_markdown(index=False), "",
             "## Strategy comparison (stress tests only)", "", summary_stress.to_markdown(index=False), ""]
    if summary_real is not None:
        lines += ["## Strategy comparison (real unseen-PHM shifts only)", "", summary_real.to_markdown(index=False), ""]
    lines += ["## Shift types", "", by_family.to_markdown(index=False), "",
              "## Does drift predict harm? (idea 1)", "", regression.to_markdown(index=False), "",
              detection.to_markdown(index=False), "", "Suggested monitor thresholds (maximise detection minus false alarms):",
              "", "```", json.dumps(suggested, indent=2), "```", ""]
    (out / "REPORT.md").write_text("\n".join(lines))
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--target", default="underweight", choices=["underweight", "stunting", "wasting"])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-phm", action="store_true", help="skip the real unseen-PHM-area shifts")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--report-only", action="store_true", help="rebuild REPORT.md and figures from saved CSVs")
    ap.add_argument("--thresholds", choices=["conventional", "calibrated"], default="conventional",
                    help="drift limits: conventional (PSI 0.2, KS p<0.05) or calibrated from earlier experiments")
    a = ap.parse_args()
    default_out = Path("results") / (f"c3_{a.target}" + ("_calibrated" if a.thresholds == "calibrated" else ""))
    if a.report_only:
        write_report(a.target, a.seeds, a.out or default_out)
        return
    run(a.target, a.seeds, a.out or default_out, include_phm=not a.no_phm, workers=a.workers, mode=a.thresholds)


if __name__ == "__main__":
    main()
