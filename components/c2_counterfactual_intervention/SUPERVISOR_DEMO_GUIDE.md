# Component 2 live supervisor demonstration

**Primary standalone C2 demonstration:** follow [STANDALONE_DEMO.md](STANDALONE_DEMO.md). It starts only the C2 API and dashboard, runs all three synthetic research-test methods automatically, and shows the research-test eligible card with budget-aware food options and an illustrative seven-day schedule. C1 is not required. The steps below remain the separate, optional genuine C1 validation workflow.

Run from three PowerShell windows. Keep C1 and C2 on separate ports. These commands use the already installed C1 Python 3.12 environment for C1 and the existing C2 Python environment for C2.

## 1. Start genuine C1 inference

```powershell
cd D:\Research_Project_C1
$env:GA_RGCA_DIR = 'D:\Research_Project_C1\ml\artifacts\ga_rgca_v3'
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir services/inference --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/health` and `/model-info`. Both must say `ga_rgca_loaded: true`, with `model_version: GA-RGCA-v3`. The four artifact files stay in C1's ignored artifact directory.

## 2. Start C2 API

```powershell
cd D:\Research_Project
$env:PYTHONPATH = '.;backend'
$env:C1_INFERENCE_URL = 'http://127.0.0.1:8001'
py -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

C2's C1 validation route is `GET http://127.0.0.1:8000/interventions/c1-validation`. It sends a fixed **synthetic** historical-baseline fixture to C1 with `allow_demo=false`, then three adjacent feeding variants. It displays actual GA-RGCA-v3 labels, probabilities, uncertainty and changes. All variants are **unresolved for intervention** and it returns **zero intervention cards**. This route cannot take user or patient input.

## 3. Start dashboard

```powershell
cd D:\Research_Project\components\c2_counterfactual_intervention\dashboard
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. The primary **Intervention Analysis** screen automatically loads a genuine C1 baseline for the fully synthetic 24- or 59-month case; the 5-month safety case is deliberately not sent to C1 because required meal categories are age-inapplicable. Enter only a family food budget in LKR and its daily, weekly, or monthly period, or leave the amount unknown. Click **Generate Intervention Analysis**. Bounded search scores permitted feeding variants with genuine C1; DiCE and FACE-inspired graph run separately with `SIMULATED_TEST_ONLY` predictors. Their outputs are never mixed into C1 rankings. The 5-month case returns no complementary-feeding candidates. The 24- and 59-month cases display actual C1 comparisons and fail-closed evidence status, with zero approved intervention cards.

Then show **C1 Model Validation** for the separate fixed sensitivity check, **Algorithm Comparison** or **Advanced Testing** for research-test methods and no-solution scenarios, and **Food Price References** for 13 checked DCS Colombo retail records. The automatic workflow now shows four independently ranked **illustrative household shopping baskets**. Each uses checked DCS Colombo reference prices, explicit purchase quantities and a period-matched cost. Try weekly budgets of LKR 500, 1,500 and 3,000: basket fit and ordering change while all C1 predictions and intervention approvals remain unchanged. These quantities are pricing scenarios, never child servings or complete dietary plans. Individual suitability, local availability and approved treatment affordability remain unresolved. The dashboard never activates real recommendations.

For API checks, `GET /interventions/automatic-baseline?case_id=synthetic_24m` returns only the actual C1 baseline and fixed synthetic input provenance. `POST /interventions/automatic-analysis` accepts `{"case_id":"synthetic_24m","budget_lkr":"500","budget_period":"weekly"}`. Both require genuine C1 service output and fail with HTTP 503 when it is unavailable. These endpoints are non-prescriptive model-comparison workflows and do not replace the protected `/interventions/c1-research` real mode.

## 4. Run automated live checks

In a fourth PowerShell window:

```powershell
cd D:\Research_Project
$env:PYTHONPATH = '.;backend'
py -m components.c2_counterfactual_intervention.supervisor_live_demo --compact
```

The script fails if C1 is not loaded, if genuine C1 provenance is missing, if a test method claims a real predictor, if the no-solution case creates a card, or if the official price conversion changes. It also checks that the C2 real recommendation endpoint remains protected. For readable output, omit `--compact`.

## Price example and limitations

```powershell
py -m components.c2_counterfactual_intervention.supervisor_demo --workflow official_price --food-id mysore_dhall_average --quantity 100 --unit g --as-of 2026-10-18
```

The checked [Department of Census and Statistics weekly retail report](https://www.statistics.gov.lk/Resource/en/InflationAndPrices/retail/DCSB-WRP-2026-10-W1.pdf) gives Mysore Dhall average **LKR 334.52/kg** for the first week of October 2026 in **main Colombo District markets**. The arithmetic for 100 g is **indicative LKR 33.452**. The 1–7 October dates are a calendar-week interpretation; the report gives no separate publication date. This is not a verified Kalmunai price, serving recommendation, or household affordability finding.

Real C2 recommendations remain blocked: no server-approved real-mode acceptance policy, authorization token, reviewed food practice, verified local availability, clinical suitability or household budget has been supplied. C1 states `clinical_use: false` and external validation is incomplete. Do not represent model differences as treatment effects.

## Test commands

```powershell
cd D:\Research_Project
$env:PYTHONPATH = '.;backend'
py -m pytest components/c2_counterfactual_intervention/tests -q
cd components/c2_counterfactual_intervention/dashboard
npm.cmd run test
npm.cmd run build
```
