# Standalone Component 2 supervisor demonstration

This is a **software research test**. It uses the existing favorable synthetic C2 fixture and `SIMULATED_TEST_ONLY` predictor. C1 is optional and is never called by `POST /interventions/standalone-analysis`. “Eligible in Research Test” means the synthetic fixture passed the existing prediction, policy and feasibility checks. It is not clinical approval or evidence of local availability.

## Start without Component 1

In PowerShell terminal 1, switch from the C1 checkout to the C2 repository before starting its backend:

```powershell
cd D:\Research_Project
$env:PYTHONPATH = 'D:\Research_Project;D:\Research_Project\backend'
Remove-Item Env:C1_INFERENCE_URL -ErrorAction SilentlyContinue
py -m uvicorn app.main:app --app-dir D:\Research_Project\backend --host 127.0.0.1 --port 8000
```

In PowerShell terminal 2:

```powershell
cd D:\Research_Project\components\c2_counterfactual_intervention\dashboard
Remove-Item Env:C2_API_TARGET -ErrorAction SilentlyContinue
npm.cmd run dev
```

If the backend reports `ModuleNotFoundError: No module named 'app'`, check that the terminal is in `D:\Research_Project`, not `D:\Research_Project_C1`, and rerun the full terminal 1 block. The C1 API uses its own checkout and port 8001.

If port 8000 is already occupied by an older server, stop that server in its own terminal with Ctrl+C before using the commands above. For a separate preview without disturbing it, use `--port 8002` in the backend command, then in terminal 2 set `$env:C2_API_TARGET = 'http://127.0.0.1:8002'` and run `npm.cmd run dev -- --port 5174`. Open `http://127.0.0.1:5174/research-test`. The proxy target setting is local to that terminal.

Open `http://127.0.0.1:5173/research-test`, choose the 24-month demonstration profile and click **Generate intervention plans**. The full-width results page is `/analysis/results`. The revised test-only fixture starts at 3 meals/day and 2 to 5 varieties. The existing engine accepts three distinct candidates: diversity, meal frequency, and both together. These are ranked by the existing fewest-changes rule, with a stable feature-name tie-break; the ranking is not a treatment-effect estimate. Compare weekly LKR 500, 1,500 and 3,000. The three candidate changes and test predictions stay the same; illustrative shopping fit changes from 1 to 3 to 4 of 4 examples. Expand **View 7-Day Plan**, move to Tuesday with **Continue Plan**, mark a demo day, reset, and print. The completion marker is browser memory only and proves no health outcome. Select the 59-month profile, then 5 months to show no complementary-food schedule. Genuine C1 comparison remains available at `/c1-comparison` when C1 is running, but is hidden from the supervisor navigation.

API example:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/interventions/standalone-analysis -Method Post -ContentType 'application/json' -Body '{"case_id":"synthetic_24m","budget_lkr":"1500","budget_period":"weekly"}'
```

The response exposes baseline and candidate synthetic labels, supporting methods, research-test eligibility, rejected or unresolved model cases, four separately ranked shopping examples, source-linked DCS prices, budget remaining or shortfall, and seven day-by-day food pairing examples within the eligible card. Actual DCS records refer to main Colombo District markets. Family budget is an unverified demo input. Shopping purchase quantities are explicitly hypothetical and are **not child servings**. The schedule is not a complete diet, feeding-frequency instruction or malnutrition treatment plan; it does not allocate purchased amounts to child portions. Local availability and individual clinical suitability remain unknown.

The [Ministry of Health handbook](https://nutrition.health.gov.lk/english/resources/) and [FAO's profile of the Ministry-endorsed food groups](https://www.fao.org/nutrition/education/dietary-guidelines/regions/sri-lanka/en/) support broad group examples. The user-supplied 2020 handbook PDF URL currently returns 404; the Nutrition Division's resources page links a 2026-hosted copy. The FHB complementary-feeding booklet is listed, but its detailed feeding instructions have not been encoded. No age-specific portions, calories, protein targets or therapeutic diet are claimed. Children younger than six months receive no complementary-food proposals.

## Verification

The fixed test ID, historical height and weight, and original feeding categories displayed by the analysis are software-fixture inputs. They are not editable patient measurements; the five-month safety fixture is not anthropometrically scored.

## Optional genuine C1 cross-validation

For a **manual model check**, use the legacy comparison page at `http://127.0.0.1:5173/legacy-c1-comparison` after starting C1 and restarting C2 with `C1_INFERENCE_URL` configured as below. Enter an invented test profile, review the expandable C1 context, and select **Analyze with C1 and C2**. The result shows the submitted baseline, C1's actual baseline probabilities and classification, and C1's actual output for each permitted adjacent feeding change. It also shows the existing C2 comparison-rule result and reasons. The historical assessment and horizon dates are fixed invented test dates (1 June 2025 and 1 June 2026). This is a model behavior check; it never issues an approved intervention card. The three standalone research-test cards remain a separate demonstration, and C1 can be offline for that workflow.

The standalone analysis and its cards work while C1 is offline. To show genuine model evidence, start the existing C1 checkout in a third PowerShell terminal:

```powershell
cd D:\Research_Project_C1
$env:GA_RGCA_DIR = 'D:\Research_Project_C1\ml\artifacts\ga_rgca_v3'
$env:MODEL_MODE = 'ga-rgca'
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir services/inference --host 127.0.0.1 --port 8001
```

Check `http://127.0.0.1:8001/health` and `http://127.0.0.1:8001/model-info`; both must report `ga_rgca_loaded: true`, and model-info must report `prediction_source: GA-RGCA-v3`. Restart C2 with `$env:C1_INFERENCE_URL = 'http://127.0.0.1:8001'` set in its terminal. On `/analysis/results`, expand **Real GA-RGCA Validation Evidence**. It scores the exact standalone child profile and three permitted feeding variants with `allow_demo=false`. This panel is optional: a missing C1 service shows an inline unavailable state and does not affect standalone cards, plans, or ranking. The genuine model comparison does not authorize interventions.

Generate the reproducible evidence report after both services are available:

```powershell
cd D:\Research_Project
$env:PYTHONPATH = '.;backend'
$env:C1_INFERENCE_URL = 'http://127.0.0.1:8001'
py -m components.c2_counterfactual_intervention.supervisor_validation_report --output components/c2_counterfactual_intervention/SUPERVISOR_VALIDATION_REPORT.md
```

The working-tree report records the actual 24-month fixture run: three research-test cards, three genuine C1 comparisons, and three model-rule rejections. Those genuine probabilities are observations from this specific trained artifact and invented input. Re-run the command to verify the live model; do not use the report as a clinical outcome claim.

```powershell
cd D:\Research_Project
$env:PYTHONPATH = '.;backend'
py -m pytest components/c2_counterfactual_intervention/tests -q
cd components/c2_counterfactual_intervention/dashboard
npm.cmd test -- --run
npm.cmd run build
```
