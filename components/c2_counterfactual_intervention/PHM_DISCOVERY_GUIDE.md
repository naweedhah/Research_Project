# Local PHM / GA-RGCA-v3 validation

This is **model sensitivity research**, not an intervention authorization or clinical recommendation. The unchanged trained C1 model is called through its local `/predict` API with `allow_demo=false`. The C2 comparison changes only ordered meal-frequency and dietary-diversity categories. Historical growth, age, sex, socioeconomic context and every other C1 input stay fixed.

## Data boundary

The local source is `C:\Users\wazee\Downloads\PHM_prediction_2025_to_2026.xlsx`. It contains linked, pseudonymous 2025 and 2026 research records. The source SHA-256 and scan counts appear in `PHM_C1_VALIDATION_REPORT.md`. All 1,542 linked rows cross-match the age, height, weight and feeding values in both named PHM final workbooks by their internal child IDs. The C1 request uses **only 2025 baseline values**; future 2026 measurements and outcomes are never supplied as predictors.

The PHM workbooks do not contain per-field proof that meal frequency and dietary diversity were directly observed. Those fields are therefore **provenance-unverified**. The separate counterfactual training workbooks contain 2,993 rows and explicitly mark all meal-frequency fields synthetic/derived; they are not used for this scan. `C1_C2_Feature_Compatibility_Audit.xlsx` was not found in Downloads.

The private discovery file contains de-identified model inputs and predictions. Keep it outside the repository; the commands below place it under `%TEMP%`. No names, original source identifiers or raw workbook rows are written to the public report or bundled with the dashboard. Do not commit or share the private JSON.

## Start C1 and scan

PowerShell terminal 1:

```powershell
cd D:\Research_Project_C1
$env:GA_RGCA_DIR = 'D:\Research_Project_C1\ml\artifacts\ga_rgca_v3'
$env:MODEL_MODE = 'ga-rgca'
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir services/inference --host 127.0.0.1 --port 8001
```

Check `http://127.0.0.1:8001/health` and `/model-info`. Both must report `ga_rgca_loaded: true`; model-info must identify `GA-RGCA-v3`.

PowerShell terminal 2, from `D:\Research_Project`:

```powershell
$env:PYTHONPATH = '.;backend'
$env:C1_INFERENCE_URL = 'http://127.0.0.1:8001'
py -m components.c2_counterfactual_intervention.phm_discovery --source 'C:\Users\wazee\Downloads\PHM_prediction_2025_to_2026.xlsx' --at-risk-first --resume --workers 2 --private-output "$env:TEMP\c2_phm_discovery_private.json" --public-report 'components\c2_counterfactual_intervention\PHM_C1_VALIDATION_REPORT.md'
```

The scan is resumable after interruption. It checks good links, ages 6–59 months, positive historical height/weight, non-implausible baseline growth, exact C1 feeding categories and at least one upward transition. It evaluates all upward category combinations with genuine C1; non-adjacent transitions are **exploratory** and cannot pass the existing adjacent-transition policy. The report gives the examined denominator and leaves the whole-cohort rate empty until every technically eligible profile finishes.

## Local dashboard review

After the private file exists, start C2 in another PowerShell terminal:

```powershell
cd D:\Research_Project
$env:PYTHONPATH = '.;backend'
$env:C1_INFERENCE_URL = 'http://127.0.0.1:8001'
$env:C2_PHM_VALIDATION_PATH = Join-Path $env:TEMP 'c2_phm_discovery_private.json'
py -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8003
```

Start the dashboard in another terminal:

```powershell
cd D:\Research_Project\components\c2_counterfactual_intervention\dashboard
$env:C2_API_TARGET = 'http://127.0.0.1:8003'
npm.cmd run dev -- --host 127.0.0.1 --port 5175
```

Open `http://127.0.0.1:5175/analysis` and choose **Local C1 validation profiles**. The selector shows a small, de-identified, source-labelled set. Selecting a case makes **fresh C1 predictions** and compares them with the private stored evidence; a mismatch fails closed. A model-rule-passing comparison appears with an illustrative seven-day household food option and budget comparison in the same card. It remains explicitly unresolved for research authorization, clinical suitability and local availability. Budget changes reorder affordable shopping examples but never change C1 model inputs or predictions. The **Standalone research test** option remains independent and continues to work if C1 is offline or no private file is configured.

The local PHM endpoints are restricted to loopback clients and are unavailable unless `C2_PHM_VALIDATION_PATH` points to a private file. Do not expose the backend on a public interface while reviewing research records.
