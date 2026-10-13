# Component 3 — Adaptive Model Reliability Monitoring and Safe Maintenance Framework

Monitors the deployed C1 prediction model, decides whether a detected data shift actually harms reliability, and
applies the least-invasive validated maintenance action. Core idea: **data changed ≠ model broken.**

**Loop:** Monitor → Assess → Decide → Adapt → Verify → Promote / Reject / Rollback

## Layout

```
component3/
├── interfaces.py     # contract any C1 model must satisfy (predict, predict_proba, version, metadata, decision threshold)
├── config.py         # thresholds, promotion criteria, action costs
├── monitor/          # PSI, KS, missingness, prediction drift; label-free warning while labels are pending
├── assess/           # balanced accuracy, per-class recall, AUROC/AUPRC, calibration error (ECE), Brier, subgroups
├── decide/           # No Action / Recalibrate / Retrain / Hold (incl. data-quality hold)
├── adapt/            # recalibration and retraining candidates, operating-threshold tuning
├── verify/           # verification gate on untouched data; must not regress vs the active model
├── registry/         # promote, reject, stage for approval, approve, rollback, full version history
├── orchestrator.py   # one full maintenance cycle
├── validate/         # validation gate: impossible values, missing essentials, age-inappropriate answers
├── context/          # external signals: disasters (GDACS), food prices (WFP/HDX), inflation (CCPI), World Bank background
├── data/             # loader for the real linked 2025 -> 2026 register data (not stored in the repo)
├── models/           # stand-in C1 model (calibrated gradient-boosted trees) until C1's final model is plugged in
└── experiments/      # stress scenarios, strategies, comparison harness, real-data experiment runner
tests/                # 67 unit tests (offline; real GDACS/WFP samples in tests/fixtures)
results/c3_underweight/             # experiment results, conventional drift limits (aggregate numbers, graphs)
results/c3_underweight_calibrated/  # same with data-driven drift limits
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

## Safety features

| Feature | What it does |
|---|---|
| Data-quality hold | Performance drop + missing-data spike → Hold with "fix data collection" (retraining would learn the defect) |
| Validation gate (`validate/`) | Invalid records (impossible z-scores/measurements, missing age/sex, diet recorded for infants < 6 months) are excluded from repair and verification; a batch with > 20% invalid records is held for review |
| Subgroup reliability | Per-group balanced accuracy/sensitivity (sex × age band, or any grouping); a candidate may not make the worst-off group > 5 points worse |
| Label-free warning | While labels are pending, the change in the share of children flagged and in mean risk gives the Hold an urgency (high/medium/low) |
| Operating threshold | Binary models run at a tuned threshold (≥ 80% sensitivity), re-tuned after every recalibration/retraining |
| Shadow comparison | Candidate and active model run on the same new children before any deployment (agreement, flagged share) |
| Human approval (optional) | `require_approval=True`: verified candidates wait for approval instead of deploying automatically |
| Post-deployment check | First labelled batch after deployment; automatic rollback if the new model is worse than the previous one |
| Data-driven drift limits | `config.calibrated_thresholds()`: PSI 0.6, KS statistic 0.27, prediction PSI 0.04 (from the experiments) |

## Backend and dashboard

`backend/app/routers/maintenance.py` + `backend/app/c3/` expose C3 through the integrated API; open
`http://localhost:8000/maintenance/dashboard` for the model-health page (run cycles under any shift, see drift,
reliability, context, validation, shadow comparison and subgroups; approve, reject or roll back models).

## External context monitoring

Disasters, food prices and inflation can change the child population before any new labels arrive. C3 reads them as
**leading indicators**: an alert tightens drift detection for that cycle and the signals are attached to the cycle's
evidence as possible causes. Context **never triggers maintenance by itself** (data changed ≠ model broken).

| Source | What | Frequency | Signal |
|---|---|---|---|
| GDACS API | Floods, cyclones, droughts, earthquakes (Sri Lanka) | Near real-time | Orange/Red event → alert; Green within 250 km → watch (90-day lookback) |
| WFP market prices (HDX) | Staple prices (rice, eggs, coconut, lentils…) in Ampara and Batticaloa | Monthly, published with delay | Month-on-month ≥ 10% or year-on-year ≥ 20% → alert; ≥ 5% → watch |
| CCPI (`component3/context/data/ccpi_monthly.csv`) | National food and headline inflation | Monthly; update from the CBSL/DCS release | Food ≥ 10% → alert, ≥ 5% → watch; headline +3 points in 3 months → watch |
| World Bank Indicators API | Yearly national inflation | Yearly | Background only |

```bash
python -m component3.context.check --start 2025-12-01 --end 2025-12-31 --offline   # Cyclone Ditwah / flood: ALERT
python -m component3.context.check --background                                    # live sources, current month
```

Pass the report to a cycle with `orchestrator.run_cycle(..., context=build_context_report(start, end))`.

## Results (underweight, stand-in model) — see `results/*/REPORT.md`

160 shift runs (120 stress tests incl. impossible values, 40 real unseen-PHM-area shifts), 800 maintenance cycles,
all safety features active.

- **Drift does not mean harm:** the drift monitors explain only a small part of the actual performance drop
  (R² ≈ 0.17); conventional limits (PSI ≥ 0.2, KS p < 0.05) raise alarms on 90% of harmless shifts, the data-driven
  limits on 56%. Unseen area PHM04 drifted strongly (PSI 1.5) with no harm; PHM07 drifted less (PSI 0.49) and was harmed.
- **Adaptive maintenance:** 41% intervention rate (vs 64–97% for fixed strategies), 37% unnecessary interventions on
  harmless shifts (vs 53–96%), mean cost 0.98 (vs 1.93–2.92 for retraining strategies), same final test performance.
  On harmful shifts it corrected 48%, escalated 37% to human review and left 15% without response.
- **Records vs statistics:** weights recorded 5× too high barely move the drift statistics (the calibrated limits miss
  them all) but the validation gate catches every invalid record.
- **Honest limits:** with small batches of new labels, no strategy recovers much lost accuracy (gains ≤ 0.01); the
  verification gate therefore rejects most candidates, which protects against deploying worse models.

## Data note

Growth measurements and WHO labels come from real 2025/2026 PHM registers. Maternal, household and dietary fields
are **synthetic** (statistically generated from a real survey) for prototyping; real collection is planned.
