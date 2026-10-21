# Component 2 live supervisor demonstration

**Primary v2 dietary scenario demonstration:** start C1, C2 and the dashboard with the commands below, then open `/analysis`. Enter an invented profile. C1 provides the original risk assessment once; C2 compares alternative foods with the labelled current feeding pattern, checks evidence and shows unresolved alternatives or verified ranks. No scenario is re-scored by C1. The old model-comparison routes remain legacy research evidence. The independent three-method software test remains at `/research-test` and is documented in [STANDALONE_DEMO.md](STANDALONE_DEMO.md).

**Four-method supervisor example:** On `/analysis`, keep the invented 24-month profile, set weekly budget to LKR 1,500, choose **compare all**, and generate. The explicit research algorithm demonstration runs bounded enumeration, DiCE on a labelled engineering fixture, FACE-inspired path search, and bounded Wachter-style optimization. It produces three **research-test** ranks among four unique food examples; the Essentials example is first under the test-only smaller-shopping-list and reference-cost tie-break rule. Change the budget to LKR 100 and regenerate: no option meets even that engineering target. These are software behavior demonstrations, not proof that a child's growth or nutrition improves. Genuine `ranked_cards` stay empty until the missing individual suitability and local evidence is resolved. The legacy research routes remain accessible by direct URL but are removed from the primary navigation.

Run from three PowerShell windows. Keep C1 and C2 on separate ports. These commands use the already installed C1 Python 3.12 environment for C1 and the existing C2 Python environment for C2.

## 1. Start genuine C1 inference

```powershell
cd D:\Research_Project_C1
$env:GA_RGCA_DIR = 'D:\Research_Project_C1\ml\artifacts\ga_rgca_v3'
$env:MODEL_MODE = 'ga-rgca'
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir services/inference --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/health` and `/model-info`. Both must say `ga_rgca_loaded: true`, with `model_version: GA-RGCA-v3`. The four artifact files stay in C1's ignored artifact directory.

## 2. Start C2 API

```powershell
cd D:\Research_Project
$env:PYTHONPATH = 'D:\Research_Project;D:\Research_Project\backend'
$env:C1_INFERENCE_URL = 'http://127.0.0.1:8001'
py -m uvicorn app.main:app --app-dir D:\Research_Project\backend --host 127.0.0.1 --port 8000
```

For the primary v2 workflow, the dashboard calls `POST /interventions/baseline-c1-v2` once for the original invented input, then `POST /interventions/diet-scenarios-v2` for food comparisons. The second route makes no C1 calls. The older `GET /interventions/c1-validation` route is retained only as historical model-sensitivity research: it sends a fixed invented fixture and three feeding variants to C1. Its results do not authorize intervention cards or feed the v2 ranking.

## 3. Start dashboard

Open `http://127.0.0.1:5173/analysis` after starting all three services. Enter only an invented profile, review the original C1 context, select any reported food groups, enter an illustrative food budget, and select **Generate dietary scenarios**. The feeding baseline remains unverified in this demonstration. The first endpoint obtains one genuine C1 risk assessment; the second generates food-based comparisons without a C1 call. The screen shows the original risk, comparison foods, indicative DCS Colombo costs and research-test ordering. Detailed evidence checks remain in the API response; no card is verified feasible with the current evidence. The separate research-test workflow remains at `/research-test`.

```powershell
cd D:\Research_Project\components\c2_counterfactual_intervention\dashboard
Remove-Item Env:C2_API_TARGET -ErrorAction SilentlyContinue
npm.cmd run dev
```

The primary `/analysis` workflow uses C1 only for original context. The older automatic per-candidate C1 comparison and DiCE/FACE research-test methods remain available as archived sensitivity research; they do not feed v2 rankings. Under-six-month complementary-food scenarios are excluded by the v2 API.

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
