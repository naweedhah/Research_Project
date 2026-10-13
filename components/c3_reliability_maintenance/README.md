# Component 3 — Adaptive Model Reliability Monitoring and Safe Maintenance Framework

Monitors the deployed C1 prediction model, decides whether a detected data shift actually harms reliability, and
applies the least-invasive validated maintenance action. Core idea: **data changed ≠ model broken.**

**Loop:** Monitor → Assess → Decide → Adapt → Verify → Promote / Reject / Rollback

## Layout

```
component3/
├── interfaces.py     # contract any C1 model must satisfy (predict, predict_proba, version, metadata, decision threshold)
├── config.py         # thresholds, promotion criteria, action costs
├── monitor/          # PSI (numeric + categorical), KS test, missingness change, prediction-distribution drift
├── assess/           # balanced accuracy, per-class recall, AUROC/AUPRC, calibration error (ECE), Brier; pending labels
├── decide/           # No Action / Recalibrate / Retrain / Hold (incl. data-quality hold)
├── adapt/            # recalibration and retraining candidates, operating-threshold tuning
├── verify/           # verification gate on untouched data; must not regress vs the active model
├── registry/         # promote, reject, rollback, full version history
├── orchestrator.py   # one full maintenance cycle
├── data/             # loader for the real linked 2025 -> 2026 register data (not stored in the repo)
├── models/           # stand-in C1 model (calibrated gradient-boosted trees) until C1's final model is plugged in
└── experiments/      # stress scenarios, strategies, comparison harness, real-data experiment runner
tests/                # 46 unit tests
results/c3_underweight/  # first experiment results (aggregate numbers and graphs only)
```

## Setup

```bash
cd components/c3_reliability_maintenance
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,experiments]"
pytest
```

## Running the experiments

The real data (`PHM_prediction_2025_to_2026.csv`) contains child-level records and is **not** in this repository.
Point C3 to the folder that holds it:

```bash
export C3_DATA_DIR=/path/to/clean_malnutrition_data
python -m component3.experiments.run_real --target underweight --seeds 5 --workers 7
python -m component3.experiments.run_real --report-only        # rebuild REPORT.md and graphs from saved CSVs
```

It runs 22 controlled shifts (missing data, measurement error, scale bias, population shifts, prevalence change,
dropped fields) plus real unseen-PHM-area shifts, measures drift and actual harm, and compares five strategies:
static, periodic retraining, always recalibrate, always retrain and C3's adaptive policy.

## First results (underweight, stand-in model) — see `results/c3_underweight/REPORT.md`

- **Drift does not mean harm:** all drift monitors together explain only 17% of the actual performance drop; the
  standard PSI ≥ 0.2 rule raises alarms on 92% of harmless shifts. Example: unseen area PHM04 drifted strongly
  (PSI 1.5) with no harm, while PHM07 drifted less (PSI 0.49) and was harmed.
- **Adaptive maintenance:** 43% intervention rate (vs 92–100%), 39% unnecessary interventions on harmless shifts
  (vs 89–100%), mean cost 1.0 (vs 2.76–3.0 for retraining strategies), with the same final test performance.
- **Safety:** the verification gate rejected most candidate models that would not have been better; data-quality
  problems are escalated to a human instead of retraining on defective data.

## Data note

Growth measurements and WHO labels come from real 2025/2026 PHM registers. Maternal, household and dietary fields
are **synthetic** (statistically generated from a real survey) for prototyping; real collection is planned.
