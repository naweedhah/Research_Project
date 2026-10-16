# October 22 supervisor demonstration

Run from `D:\Research_Project` in PowerShell:

```powershell
$env:PYTHONPATH = '.;backend'
py -m components.c2_counterfactual_intervention.supervisor_demo --method bounded_search --scenario favorable
py -m components.c2_counterfactual_intervention.supervisor_demo --method dice --scenario favorable
py -m components.c2_counterfactual_intervention.supervisor_demo --method face_graph --scenario favorable
py -m components.c2_counterfactual_intervention.supervisor_demo --scenario no_solution
py -m components.c2_counterfactual_intervention.supervisor_demo --scenario unknown_availability
py -m components.c2_counterfactual_intervention.supervisor_demo --scenario unaffordable
py -m components.c2_counterfactual_intervention.supervisor_demo --scenario too_young
py -m components.c2_counterfactual_intervention.supervisor_demo --scenario unchanged
py -m components.c2_counterfactual_intervention.supervisor_demo --scenario worsening
py -m components.c2_counterfactual_intervention.supervisor_demo --scenario uncertain
```

The CLI prints original categories, baseline and candidate **labels**, ranked cards, LKR 60 **synthetic fixture** cost with a synthetic LKR 100/day budget, feasibility/rejection reasons, and `SIMULATED MODEL - NOT FOR CLINICAL USE`. All profiles use a synthetic pseudonym and arbitrary outcome rules. The presence of a simulated card does not show a treatment effect or clinical suitability. The no-solution and constraint scenarios show empty cards. The current C1 integration status is unverified.

For Swagger, run `py -m uvicorn app.main:app --app-dir backend --reload` and open `http://127.0.0.1:8000/docs`. The endpoint is `POST /interventions/c1-research`. To obtain a complete simulated JSON request without writing a file:

```powershell
py -c "import json; from components.c2_counterfactual_intervention.supervisor_demo import demo_request; print(json.dumps(demo_request().model_dump(mode='json'), indent=2))"
```

The legacy `POST /interventions/recommendations` remains available for prior synthetic v1/v2 demonstrations. `GET /interventions/status` still reports that genuine C1 integration is false. The Phase 6 real request returns 503 until server authorization, a reviewed acceptance-policy hash, and a genuine loaded C1 service are configured and verified. Do not use real child identifiers for this demo.

## Phase 6.1 official price reference

These commands use the 13 checked DCS retail observations from the first week of October 2026. The quantities are arithmetic illustrations, not approved child serving sizes. The 14-day rule labels this bulletin `HISTORICAL_REFERENCE` on 22 October. The JSON shows the original DCS source URL, Colombo District coverage, interpreted observation dates and unknown publication date.

```powershell
py -m components.c2_counterfactual_intervention.supervisor_demo --workflow official_price --food-id mysore_dhall_average --quantity 100 --unit g
py -m components.c2_counterfactual_intervention.supervisor_demo --workflow official_price --food-id egg_average --quantity 1 --unit piece --budget-lkr 50 --budget-period day --quantity-period day --budget-source 'Illustrative supervisor scenario' --local-availability available --availability-source 'Illustrative user report' --caregiver-practical yes --practicality-source 'Illustrative user report'
```

The first command leaves household budget and local availability unresolved. The second compares a hypothetical daily quantity with a user-supplied daily budget. Its availability and practicality are user assertions, not independently verified Kalmunai evidence. Verified local affordability and clinical suitability remain `UNKNOWN`. A budget comparison requires matching `--budget-period` and `--quantity-period`; otherwise it stays unresolved. Reported availability and practicality require a provenance string. Use `--as-of YYYY-MM-DD` to rerun freshness. Neither command produces an intervention card.

Four short demo starting points are `--method bounded_search --scenario favorable`, the first `official_price` command, the second `official_price` command, and `--scenario no_solution`. DiCE and FACE remain available as software method demonstrations. The engine still uses its LKR 60 synthetic fixture. All workflows display `RESEARCH TEST MODE — C1 TRAINED MODEL NOT CONNECTED`; predictor and published-price provenance remain separate.
