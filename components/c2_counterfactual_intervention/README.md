# Component 2: counterfactual intervention engine

This research prototype compares bounded search, official DiCE, and a FACE-inspired graph method using synthetic inputs and test-only predictors. No output is clinically validated. Predicted category changes do not establish treatment effects.

## Architecture

`schemas.py` validates request and response data. `feature_policy.py` lists candidate features and transitions. `candidate_generation.py` enumerates unique one- and two-feature changes. `engine.py` validates each change, calls the replaceable `Predictor` adapter, checks feasibility, and creates cards. `ranking.py` uses predicted category improvement, then fewer changes, lower abstract cost and stable feature order, while preferring different first features when possible. The public card omits its candidate prediction; internal comparisons determine acceptance.

## Input contract and future C1 mapping

The request contains `child_id`, `child`, `context`, `max_changes` (1 or 2), `max_cards` (1–20), and an optional predictor ID (`synthetic_test_v1` or `synthetic_sklearn_grid_v1`). Extra fields are rejected. The following are **test encodings**, not clinical cutoffs or recommendations:

| Field | Type and accepted values | Policy |
|---|---|---|
| `age_months` | strict integer 0–59 | Immutable |
| `sex` | `female` or `male` | Immutable |
| `birth_weight_kg` | positive number or null | Historical |
| `historical_exclusive_breastfeeding` | boolean or null | Historical |
| `household_income_band` | `low`, `middle`, `high`, `unknown` | Contextual, never mutated |
| `meals_per_day` | strict integer 1–5 | Synthetic actionable test feature; only +1 within bound |
| `dietary_diversity` | strict integer 0–5 | Synthetic actionable test feature; only +1 within bound |
| `supplement_use` | boolean or null | Observed, never mutated in Phase 1 |

The context holds `budget_units` (nonnegative integer or null), `supplement_access`, `supplement_programme_eligible`, and `supplement_clinically_suitable` (each boolean or null), plus per-feature `available`, `practical`, `age_suitable`, `eligible`, `clinically_suitable`, and `transition_justified` maps (booleans or null). Map keys are only `meals_per_day` and `dietary_diversity`. The separate supplement fields are contextual information only; they are not changed, used to boost the predictor, or used to generate supplement cards. A referral for assessment would need a separate, reviewed workflow. No treatment or guaranteed access is implied.

Every mandatory check for each changed feature must explicitly be true. False rejects; missing or null stays unresolved. Budget is an abstract test cost (2 units for meal frequency, 3 for diversity), not a real price. Conflicting checks reject if any explicit false is present, while retaining unknown reasons. The API returns an empty card list and reasons when no valid, favorable, feasible change exists. Professional review is always required.

The synthetic predictor reads only `meals_per_day` and `dietary_diversity`: their sum at least 7 yields `lower_concern`, otherwise `higher_concern`. This threshold is arbitrary. C1 integration must explicitly map each available source column, type, categorical encoding, units, missing-value rule, and target label to a frozen model contract. The current test encoding must not be assumed to match C1.

## Install, run, and test

From the repository root (Python 3.10+):

```powershell
python -m pip install -r backend/requirements.txt pytest httpx
$env:PYTHONPATH = ".;backend"
python -m pytest components/c2_counterfactual_intervention/tests -q
python -m uvicorn app.main:app --app-dir backend --reload
```

Open `http://127.0.0.1:8000/docs`. `GET /interventions/status` reports a functioning test engine while C1 and clinical integration remain false.

## Synthetic API example

`POST /interventions/recommendations`:

```json
{
  "child_id": "SYNTHETIC-001",
  "child": {"age_months": 24, "sex": "female", "birth_weight_kg": 2.8, "historical_exclusive_breastfeeding": true, "household_income_band": "low", "meals_per_day": 3, "dietary_diversity": 3, "supplement_use": false},
  "context": {
    "budget_units": 10,
    "supplement_access": false,
    "supplement_programme_eligible": null,
    "supplement_clinically_suitable": null,
    "available": {"meals_per_day": true, "dietary_diversity": true},
    "practical": {"meals_per_day": true, "dietary_diversity": true},
    "age_suitable": {"meals_per_day": true, "dietary_diversity": true},
    "eligible": {"meals_per_day": true, "dietary_diversity": true},
    "clinically_suitable": {"meals_per_day": true, "dietary_diversity": true},
    "transition_justified": {"meals_per_day": true, "dietary_diversity": true}
  },
  "max_cards": 1
}
```

The supplied true values are synthetic test assertions, not verified facts about a child. The response contains a baseline test category, ranked cards, rejected or unresolved candidates with reasons, professional-review flags, and test-only provenance. It contains no risk percentage, predicted risk reduction, or per-card predicted category.

## Limitations and next steps

The +1 feeding transitions, abstract cost scale, and predictor threshold are test fixtures. Real transitions and eligibility conditions need domain review. The FACE-inspired graph is not an exact FACE reproduction, and the three methods still need evaluation on suitable real reference data. A real C1 adapter requires frozen labels and target semantics, feature schema, preprocessing and encodings, model artifact and version, missing-data behavior, and a callable prediction interface. Validate candidate plausibility and feasibility rules with qualified professionals before any real-world use.

## Phase 2 method support

The request accepts `method: "bounded_search"` (default), `"dice"`, or `"face_graph"`. The public response identifies the method. All three feed candidate changes through the same post-generation transition validation, predictor comparison, feasibility check, ranking, and card formatting. DiCE never delegates to bounded search; unavailable dependencies return an API error. Research metrics stay in `evaluation.py` and are not added to cards.

### DiCE

`dice_method.py` uses the official `dice-ml` 0.12 `Dice(..., method="random")` model-agnostic explainer with a deterministic seed of 17 and 20 requested counterfactuals. It restricts `features_to_vary` to meal frequency and dietary diversity and `permitted_range` to the current value through at most one increment. Nonintegral outputs are discarded; candidates are deduplicated and then independently revalidated by the shared pipeline. A no-counterfactual response returns no candidates, never a fabricated fallback. Its classifier is a separate `SyntheticSklearnPredictor` trained with `DecisionTreeClassifier(random_state=17)` on the complete **artificial design grid** of 30 feature pairs. Training labels use the same arbitrary threshold as the Phase 1 test predictor; the adapter verifies exact agreement on that grid. No real child records or model artifacts are used. When selecting DiCE, the sklearn adapter is required. Other methods can also use this adapter through `predictor: "synthetic_sklearn_grid_v1"` for equal comparison.

### FACE-inspired graph method

`face_graph.py` implements an adaptation of the graph and shortest-path ideas in Poyiadzi et al. Its explicit reference dataset is the same 30-point synthetic design grid (`meals_per_day` in 1–5, `dietary_diversity` in 0–5). Each point is a graph node, and a directed edge exists only for a +1 change in exactly one permitted feature (L1 distance 1). The graph has no access, income, age, sex, birth, or historical variables to alter. Edge cost is `1 + 1/(1 + min(degree(u), degree(v)))`, where degree is the number of adjacent reference points. This penalizes sparsely supported grid edges but **is not an empirical density estimate**. Dijkstra search finds minimum-cost paths of at most `max_changes` edges. Each step is checked against the feature policy and feasibility conditions; cumulative changes and budget are also checked. The endpoint must be supported by the selected predictor, and the shared pipeline checks it again. An absent source, disconnected graph, infeasible route, or unreachable target yields no path and no card.

This is **FACE-inspired**, not an exact reproduction: it uses a tiny categorical/integer design grid, directed one-step edges, a simple degree proxy instead of KDE or the paper's continuous density-weighted metric, and no calibrated prediction-confidence or learned density threshold. Its output cannot establish real-world path feasibility.

References: [DiCE library and documentation](https://interpret.ml/DiCE/), [DiCE repository](https://github.com/interpretml/DiCE), and [Poyiadzi et al., FACE, AIES 2020](https://doi.org/10.1145/3375627.3375850) ([author manuscript](https://arxiv.org/pdf/1909.09369)).

### Reproducible evaluation

Run from the repository root:

```powershell
$env:PYTHONPATH = ".;backend"
python -m components.c2_counterfactual_intervention.evaluation
python -m pytest components/c2_counterfactual_intervention/tests -q
```

The evaluation uses one frozen sklearn test predictor and the same four synthetic baseline inputs for all methods. Scenarios include all checks true, unavailable meal change, unknown diversity suitability, and no model-supported target within two steps. Training occurs before timing. All mandatory conditions are explicit synthetic assertions. The printed JSON contains actual measurements, not stored benchmark claims. Wall-clock runtimes vary by machine and run. An empty denominator is represented as `null`, not zero.

For generated candidate set `G`, let `T` contain members that pass transition policy and reach the intended **test-model** category. Let `F` contain members of `T` that pass feasibility. Let `C` be returned cards and `x` the baseline. The metrics are:

- **Candidate validity:** `|T| / |G|`. This is model/transition validity only, never clinical validity.
- **Feasibility pass rate:** `|F| / |T|`. For `face_graph`, unsafe paths are pruned before generation, so this rate is conditional on graph output and should be read alongside generated counts.
- **Proximity:** mean over cards of `(abs(Δmeals)/4 + abs(Δdiversity)/5)/2`.
- **Sparsity:** mean number of changed features per card (lower is sparser).
- **Diversity:** mean pairwise normalized L1 distance between card endpoints using the same divisors; zero for one card.
- **Rejected/unresolved:** counts of generated candidates marked with each status by the shared pipeline. Graph-pruned paths are not counted as rejected candidates.
- **Runtime:** elapsed milliseconds for generation, validation, feasibility, ranking, and card construction, excluding test-model training.
- **No solution:** true when no card is returned for a baseline requiring change.

These are tiny synthetic software experiments, not evidence of clinical effectiveness, safety, or population generalization. A real C1 interface needs frozen target semantics, feature encoding and preprocessing, a versioned model, and a compatible prediction adapter. Real reference records and professionally reviewed transition and feasibility rules are prerequisites for meaningful research evaluation on actual cases.
