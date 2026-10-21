# Live C1 case library and C2 scenario check

The ten `TEST-####` profiles in `live_case_library_v2.py` are invented software-test inputs. Their names describe input variation; no profile has a preset nutritional-risk label. Select a profile on the existing **Intervention Analysis** screen, review or edit its fields, and select **Generate dietary scenarios**. C2 requests the original assessment from the genuine GA-RGCA-v3 service with `allow_demo=false`, then passes that read-only assessment to the C2 food-scenario engine. Budget and reported food groups can change C2 ordering without changing the C1 assessment. This workflow makes **zero C1 candidate prediction calls** and cannot establish a minimum change that improves predicted health.

## Reproduce all cases in PowerShell

Start C1 in terminal 1 from `D:\Research_Project_C1`:

```powershell
$env:GA_RGCA_DIR = 'D:\Research_Project_C1\ml\artifacts\ga_rgca_v3'
$env:MODEL_MODE = 'ga-rgca'
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir services/inference --host 127.0.0.1 --port 8001
```

Run the batch from `D:\Research_Project` in terminal 2:

```powershell
$env:PYTHONPATH = 'D:\Research_Project;D:\Research_Project\backend'
$env:C1_INFERENCE_URL = 'http://127.0.0.1:8001'
py -m components.c2_counterfactual_intervention.live_case_validation_v2
```

The command exits with an error if C1 is unavailable or its genuine model cannot be verified. The JSON output reports the observed C1 category, severity, uncertainty, model provenance, C2 candidate count, and category coverage for every case. No output is substituted from a test predictor.

On `http://127.0.0.1:5173/analysis`, select **Verify all cases with live C1** to see the same categories in the dashboard, then select a case ID to load its editable input and generate its C2 food scenarios. This action calls C1 again; the table is not a stored prediction. The case library is served by the C2 backend on port 8000. After adding or changing cases, restart that backend and refresh the browser. If it remains on an old process, `/interventions/live-case-library-v2` may still return an older list. A case-library error is now shown with a retry control instead of silently hiding the new cases.

## Live run on 21 October 2026

The local service reported `GA-RGCA-v3` with trained artifacts loaded. Ten requests used `allow_demo=false`. The table gives one actual response per requested demonstration path; **SAM was not observed** in this finite invented case set.

| Demonstration path | Select case | Actual C1 output | C2 check |
| --- | --- | --- | --- |
| Normal | `TEST-0021` | Normal; severity Normal; uncertainty not flagged | Food examples generated without implying treatment is needed. |
| Underweight | `TEST-0019` | Underweight; severity Moderate; uncertainty flagged | Four candidates checked against the invented budget and reported groups. |
| Stunting | `TEST-0022` | Stunting; severity Moderate; uncertainty not flagged | Four candidates generated and ordered for software comparison. |
| MAM | `TEST-0020` | MAM; severity Moderate; uncertainty flagged | Food examples remain separate from any clinical management decision. |
| Severe safety path | `TEST-0023` | MAM; severity Severe; uncertainty not flagged | Assessment review is shown; food examples are not presented as sufficient care. A live SAM output was not found. |

The historical MAM/SAM and underweight/stunting flags in these cases are **invented prior-status inputs** supported by C1's model contract. For example, `TEST-0020` deliberately supplies an invented historical SAM flag, but C1's actual future-risk output was **MAM**. The prior flag must never be described as an observed diagnosis or as C1's current output.

Each case produced four C2 candidate food scenarios. Research-test ordering included four candidates for nine cases and one candidate for the limited-budget case; all ten cases had **zero verified-feasible cards** because individual suitability, local availability, and other mandatory evidence remain unresolved. The C1 results are model outputs on invented inputs, not clinical findings or validated treatment outcomes.

Changing the manually entered values can alter the C1 category or produce no C2 option. The system reports actual outputs and an empty result; it does not force an improvement or guarantee coverage of every risk category. The test suite checks the input contract and local catalogue API with software fixtures; those tests are distinct from the live model run above.
