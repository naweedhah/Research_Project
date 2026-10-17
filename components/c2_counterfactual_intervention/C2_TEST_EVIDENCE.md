# Phase 6 executed software evidence (16 October 2026)

All tests and examples below are **software verification with synthetic fixtures**. They are not clinical validation and do not establish an intervention effect.

## Commands and observed results

From `D:\Research_Project`, with `$env:PYTHONPATH='.;backend'`:

| Command | Observed result |
| --- | --- |
| `py -m pytest components/c2_counterfactual_intervention/tests -q` | **90 passed**, 1 Starlette `httpx` TestClient deprecation warning, 0 failures; final rerun 94.56 s. |
| `py -m pytest components/c2_counterfactual_intervention/tests/test_phase6.py -q` | **13 passed**, same warning, 0 failures; 24.49 s. |
| `py -m components.c2_counterfactual_intervention.evaluation --summary` | Completed on 45 synthetic cases per method; 26 cards and 18 solved cases each for bounded search, DiCE and FACE-inspired graph. These figures describe the legacy synthetic design grid only. |
| `git diff --check` | No whitespace errors. Git emitted only Windows LF/CRLF conversion notices. |
| `py -m ruff --version` | Ruff is not installed in the active Python 3.14 environment; no Ruff pass is claimed. |

## Phase 6 observed demo scenarios

The C1-shaped favorable profile produced **one card through each of the three methods**, with a **synthetic LKR 60** fixture cost. The synthetic reference food and LKR 100/day budget do not represent a local price or an actual household. `no_solution` and `too_young` yielded zero cards without inventing a candidate. `unknown_availability`, `unaffordable`, `unchanged`, `worsening`, and `uncertain` each yielded zero cards and a specific unresolved or rejected reason. The API test exercised `POST /interventions/c1-research` in simulated mode and confirmed that real mode returns 503 without configuration; the response contains no condition probabilities or risk-reduction claim.

Tests cover exact categorical vocabulary, 59/60-month boundary, missing historical measurements, full request-payload immutability except approved feeding fields, repeated outputs, acute and severity distributions, invalid output semantics, individual-condition worsening, severity worsening, uncertainty, approval policy, unknown availability, absent food price, clinical suitability, all three methods, real/simulated separation, and mocked HTTP `allow_demo=false` plus historical equality. The mocked HTTP test does **not** demonstrate connectivity to an actual C1 service.

## Evidence still absent

C1 GA-RGCA weights, fitted preprocessor, calibrators, metadata, live `/health`, `/model-info` and `/predict` checks; de-identified approved real fixtures; model applicability and clinical review; locally verified Kalmunai prices and availability; approved age-specific feeding transitions; real DiCE classifier/reference data and real FACE reference points. Therefore `c1_integrated=false` and `clinical_use=false` remain correct.

## Phase 6.1 rerun (16 October 2026)

`py -m pytest components/c2_counterfactual_intervention/tests -q` completed with **92 passed, 0 failed, 1 Starlette/httpx TestClient deprecation warning** in 76.18 seconds. This includes official import, conversion, freshness, affordability, availability, real-mode fail-closed and API tests. The new real-mode test uses a hash-approved policy and verifies that a predictor is not called when food planning is absent. The new price-workflow test checks the 100 g Mysore Dhall arithmetic, October 22 historical status, unknown local affordability, supplied budget comparison, incompatible units and missing availability provenance.

The CLI produced one synthetic card each for bounded search, DiCE and FACE-inspired graph, and zero cards for the no-solution scenario. The official-price CLI printed LKR 334.52/kg and LKR 33.452 for illustrative 100 g Mysore Dhall; the supplied scenario printed LKR 37.77/egg with a comparison against an illustrative LKR 50/day budget while verified local affordability remained unknown. API behavior is covered by the full suite's `test_api_response_and_real_failure`; it was not retested against a live server. `git diff --check` completed without whitespace errors, with only Git LF/CRLF notices. The DCS index was checked on 16 October and listed the first week of October as its newest weekly retail report. No newer values were imported.
