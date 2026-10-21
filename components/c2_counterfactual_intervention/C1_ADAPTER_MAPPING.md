# Phase 6 C1 compatibility mapping

**Status:** structural compatibility and mocked HTTP contract tests only. Genuine GA-RGCA weights, fitted preprocessor, calibrators, metadata and service were not available in this checkout. No clinical validation is claimed.

## Inputs and time

`C1Snapshot` (`c2-c1-snapshot-v1`) carries pseudonymous ID, visit metadata, current non-actionable groups, verified `historical_baseline`, C1 `ga_rgca_context`, expected model/schema versions, and provenance. The horizon is C1's **12-month nutritional-risk task** from the baseline assessment; altering a feeding field in this *same* snapshot is hypothetical and does not represent a measured future outcome. Historical height/weight and age are required. Today's height or weight is never substituted. `predict_payload()` copies every group and changes only `ga_rgca_context.meal_frequency` and/or `.dietary_diversity`; it always sends `allow_demo=false`.

| C1 feature | Exact values | Phase 6 interpretation |
| --- | --- | --- |
| `Meal_Frequency_per_Day` | `2 meals/day`; `3 meals/day`; `4+ meals/day` | Ordered labels only. `4+` does not mean exactly four. |
| `Dietary_Diversity` | `Less than 2 varieties`; `2 to 5 varieties`; `More than 5 varieties` | Ordered labels only. The middle label is not an exact number or WHO score. |

These are the strings accepted by C1's `ga_rgca.py`; the real model reads them from `ga_rgca_context`, not from C2's legacy integer scale or C1's demo `dietary.dietary_diversity_score`. Phase 6 allows only adjacent upward category proposals and no proposals below six months. This transition rule is a **software test policy**, not a reviewed feeding recommendation. Mandatory suitability, eligibility, availability, practicality, transition justification and budget checks must be supplied; unknown remains unresolved. C2's historical integer 1–5 / 0–5 fixtures remain available and independent.

## Outputs

`C1Output` (`c2-c1-output-v3`) parses top-level C1 status, severity, source, mode, model version, task and score flags plus `calibrated_probabilities.ga_rgca`. Underweight and Stunting are separate binary outputs. Normal/MAM/SAM is one acute distribution. Severity is a separate distribution. No “wasting probability” is invented. The `risk_score` is not used as a calibrated benefit estimate; C1 currently says `score_is_calibrated=false`. The public Phase 6 response exposes category comparisons and test-only provenance, while keeping numeric probabilities out of cards and API comparison fields.

The HTTP adapter checks `/health` and `/model-info` before each call, then `POST /predict` with a bounded timeout. It rejects unavailable/incompatible services, non-200 responses, `DEMO` source, wrong model/task/score semantics, missing probabilities, inconsistent type/severity, and feature snapshot mismatches. It needs `C1_INFERENCE_URL` and, where required, `C1_INFERENCE_TOKEN` from the environment. The C2 real API additionally requires a server-held `C2_REAL_API_TOKEN` and `C1_REAL_POLICY_SHA256`, computed over the approved canonical JSON acceptance policy. Merely setting these values is **not** evidence of real integration. Never put tokens in a request body or repository file.

Real bounded search is the first planned method. Real DiCE requires a fitted joint-output classifier and matched reference data; real FACE-inspired graph needs governed category reference points. Neither is provided by C1. No synthetic method silently substitutes for unavailable real inference.

## Still required from C1

Artifact files and checksums; loaded `/model-info` and `/health`; agreed authentication; exact fitted-preprocessor encoding/version and missingness rules; verified historical data provenance; approved label definitions, condition worsening policy and acceptance transitions; real baseline/candidate fixtures; model applicability evidence; governed DiCE/FACE reference data if those methods are attempted. C1 documentation currently assigns counterfactual ownership to C3 while this repository assigns the engine to C2; resolve endpoint and ownership before integration.
