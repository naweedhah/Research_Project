# Component 2 code map for the panel

Open this file first. Keep the existing module locations: Python imports, API routes and tests use them. The **current dashboard workflow** is `/analysis`; earlier research pipelines are still present and should be described separately.

## Show the current workflow in five minutes

| What to show | File and entry point | What it does |
| --- | --- | --- |
| Screen and browser requests | `dashboard/src/pages/ScenarioV2.tsx` — `ScenarioV2`, `ScenarioResults` | Collects an invented profile, obtains the original C1 assessment, sends reported food groups and budget to C2, renders cards and method counts. It caches the C1 baseline when only budget/food context changes. |
| API boundary | `backend/app/routers/interventions.py` — `baseline_c1_v2`, `diet_scenarios_v2` | Local research endpoints. The first calls C1 once. The second calls only C2 scenario generation. |
| Current input schemas | `nutrition_scenarios_v2.py` — `OriginalAssessment`, `FeedingBaseline`, `HouseholdEvidence`, `ScenarioRequest` | Strict Pydantic contract. Original C1 context is read only; unknown evidence remains unknown. |
| C1 connection | `manual_c1_validation.py` — `ManualC1Request`, `manual_snapshot`; `c1_predictors.py` — `RealC1HttpPredictor` | Maps invented fields to C1's exact categories, verifies loaded GA-RGCA version/artifacts and sends `/predict`. No demo fallback is accepted as real. |
| Candidate generation and evaluation | `nutrition_scenarios_v2.py` — `generate_scenarios`, `_checks` | Chooses up to four source-priced shopping examples based on reported food groups, budget and exclusions, runs selected methods, deduplicates IDs, checks evidence, and separates test ranking from verified ranking. |
| Food source and calculations | `educational_baskets.py` — `SCENARIOS`, `SCENARIO_VARIANTS`, `shopping_examples`; `official_prices.py` | Eight bounded example baskets; purchase quantities are illustrative. Official records supply reference prices, units, geography and dates. Four examples are selected per analysis. |
| Tests | `tests/test_nutrition_scenarios_v2.py`, `tests/test_scenario_methods_v2.py`, `dashboard/src/test/scenario-v2.test.tsx` | Contract, safety, method, input sensitivity, C1 call-count and screen checks. |

**Call path:** `ScenarioV2.tsx` → `/baseline-c1-v2` → `RealC1HttpPredictor` → genuine C1 `/predict` for the original input; then `ScenarioV2.tsx` → `/diet-scenarios-v2` → `generate_scenarios` → food examples → four search methods → common checks → research-test card order. The second path does **zero** C1 candidate prediction calls. It cannot claim that a food option changes C1 risk or the child's outcome.

## Where each algorithm lives

| Method | Current `/analysis` implementation | Earlier research implementation | What to say |
| --- | --- | --- | --- |
| Bounded Search | `nutrition_scenarios_v2.py`, `method == "bounded_search"` | `candidate_generation.py`, `engine.py` | Enumerates the selected bounded food examples. The earlier engine enumerates one- or two-feature feeding transitions under `feature_policy.py`. |
| FACE Graph | `face_graph.py`, `food_transition_paths`; called in `nutrition_scenarios_v2.py` | `face_graph.py`, `generate_face_paths` | A directed subset graph adds one non-excluded food per edge. Shortest path cost is number of additions. These states are constructed; they are not empirical density evidence or an observed feeding history. |
| DiCE | `algorithm_demo_v2.py`, `dice_test_candidates`; called in `nutrition_scenarios_v2.py` | `dice_method.py`, `generate_dice_candidates` | Official `dice-ml` runs against a labelled one-hot **software-test** target: one affordable, non-excluded basket. It is not trained to predict nutrition improvement. The earlier DiCE adapter is for the separate test-predictor pipeline. |
| Wachter | `algorithm_demo_v2.py`, `wachter_test_candidates`; called in `nutrition_scenarios_v2.py` | `wachter_method.py`, `optimize_test_pattern` | Bounded SciPy optimization relaxes selection to continuous values, then checks the chosen discrete basket against the independent test target. Its objective is not a C1 or nutrition score. |

All four current methods propose **candidate IDs**. In `generate_scenarios`, `candidate_by_id` and `proposed` deduplicate shared options. `_checks` applies the same age, provenance, restriction, availability, preparation, reference-budget, nutrition and suitability checks to every proposal. `software_test_ranked` orders only examples meeting the engineering budget/exclusion target; `ranked_cards` requires every mandatory evidence check to pass. One candidate can appear in several methods' generated/selected counts but is rendered once.

## If the panel asks “Where are the schemas?”

There are **two generations**, so open the contract matching the demonstrated endpoint:

1. **Current `/analysis`:** `nutrition_scenarios_v2.py` defines `ScenarioRequest` and its nested C1, feeding and household models. `manual_c1_validation.py` defines the original C1 form request. The frontend checks responses in `dashboard/src/lib/contracts.ts`; calls are in `dashboard/src/lib/api.ts`.
2. **Earlier `/recommendations` engine:** `schemas.py` defines `ChildFeatures`, `FeasibilityContext`, `RecommendationRequest`, `Change`, `InterventionCard` and `RecommendationResponse`. `feature_policy.py` partitions actionable, contextual, historical and immutable features. `contracts.py` and `c1_compat.py` provide predictor and C1 compatibility contracts.

Never present the earlier integer-scale test fields as C1's actual categorical encodings. C1 uses exact strings such as `3 meals/day` and `2 to 5 varieties` in the current workflow.

## Likely technical questions and honest answers

**Is the current food output a counterfactual of C1's prediction?** No. C1 is called once for the original risk context. The present food scenarios are counterfactual *shopping/group scenarios*, not demonstrated model-risk reductions. The older `c1_engine.py` and `real_model_validation.py` contain separate feeding-input sensitivity comparisons; they do not authorize the current food cards.

**Why can two children see the same foods?** The current search is bounded to eight source-priced example baskets and selects up to four. Reported food groups, budget, explicit exclusions and reported unavailability can alter the selected options. Two inputs can still select the same examples. Age, height, weight and C1 risk do not have validated rules that prescribe particular foods; changing only those fields need not change the food list. Under six months, no complementary-food candidate is generated.

**What does “ranked” mean?** `software_test_ranked` is an engineering order among candidates that fit the submitted budget reference and explicit exclusions. It sorts by shorter shopping list, reference cost and stable ID. It is **not** a clinical suitability rank, a nutrient adequacy score or a predicted risk improvement. The independent evidence-gated `ranked_cards` is normally empty with current unknown evidence. Open `C2_RANKING_METHODOLOGY.md` for the rule.

**Why do DiCE and Wachter run yet not establish health benefit?** A valid optimizer only optimizes its defined target. Their current target is the test condition in `algorithm_demo_v2.py`, not a validated nutritional outcome. The result is checked against that condition and still passes through `_checks`; no health benefit is fabricated.

**Is this original FACE?** No. The current food graph is FACE-inspired connectivity with deterministic edge cost. It has no empirical reference-density or manifold-plausibility estimate. `face_graph.py` contains the route and node bound; the dashboard displays the path in plain language.

**Are meal frequency and dietary diversity directly actionable here?** The earlier feature-policy engine permits bounded +1 test transitions. In the current `/analysis` food route, they are recorded as original C1/feeding context, but food baskets do not change their values or re-score C1. A food-group addition does not prove a transition to a higher dietary-diversity category.

**How do you prevent fake C1 predictions?** `RealC1HttpPredictor.verify` checks `/health`, `/model-info`, loaded artifacts, source and version. `predict` validates the returned schema, calibration version and echoed historical/feeding inputs. The current scenario endpoint receives only the original assessment and reports `c1_candidate_calls: 0`.

**How are prices used?** `official_prices.py` retains published unit, period, market and source. `educational_baskets.py` converts the example household quantities to period-matched reference costs. These are Colombo references, not measured household purchases, local Kalmunai prices or child serving sizes.

**What happens if evidence is unknown or a method returns nothing?** Unknown mandatory checks remain evidence-incomplete; explicit conflicts reject. A method with no supported target/candidate reports zero rather than substituting another method. The API keeps method diagnostics and check reasons even though the presentation screen is concise.

**Why is there older code?** The module preserves staged research work: `engine.py`, `dice_method.py`, `candidate_generation.py`, `ranking.py` and `schemas.py` support the earlier test-predictor intervention API; `c1_engine.py` and `real_model_validation.py` support earlier C1 sensitivity studies; `standalone_demo.py` is the independent demonstration. The current panel path begins with `nutrition_scenarios_v2.py`.

## Verification commands

From `D:\Research_Project` in PowerShell:

```powershell
$env:PYTHONPATH = '.;backend'
py -m pytest components/c2_counterfactual_intervention/tests -q
cd components/c2_counterfactual_intervention/dashboard
npm.cmd test
npm.cmd run build
```

See `SUPERVISOR_DEMO_GUIDE.md` for the separate C1, C2 and dashboard startup terminals. Tests and a build verify software behavior; they do not establish clinical validity or missing individual evidence.
