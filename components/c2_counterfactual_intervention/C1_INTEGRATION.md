# Component 1 → Component 2 integration contract (draft)

**Status:** no C1 model, frozen feature contract, target labels, model artifact, or reference data are present in this repository. This file is a handoff template, not a claim that integration or clinical validation is complete.

## Versioned predictor interface

A real predictor must expose `contract: PredictorContract` (interface version `c2-predictor-v1`) and `predict_category(child: ChildFeatures) -> str`. The contract records:

- Stable model ID and model version.
- Exact ordered model-input feature names and their source fields, types, units, categorical values, preprocessing, and missing-value handling.
- Every target code and its verified operational definition; one explicitly designated desired target.
- Model artifact ID and SHA-256. Loading code must verify the artifact hash and dependency/preprocessing versions before registration. Do not load an untrusted pickle merely because a path exists.
- Reference-data ID and provenance where graph or DiCE methods require reference instances.

`register_real_predictor` accepts only a contract declaring `mode="real"`. API real-mode requests require the matching model ID and version. No real predictor is currently registered, so the API returns 503. A synthetic predictor or an incompatible version cannot satisfy a real-mode request. Registration and verified C1 integration are separate status fields; `integration_verified=True` should only be set after the frozen C1 handoff passes its checks. The `clinical_ready` status remains false even after a real predictor is registered; professional and clinical validation is a separate gate.

### Mapping template for C1 to complete

Fill one row per actual model input after C1 freezes its feature set. **Do not infer units or encodings from field names.** If C1 needs fields absent from `ChildFeatures`, extend the request schema and mapping explicitly within the agreed integration scope.

| C1 feature name | C2 source field | Source form/data column | Type | Unit or allowed categories | Preprocessing/encoding | Missing-value rule | Actionability policy | Verified by |
|---|---|---|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

| C1 target code | Operational definition and source label | Evidence for desired direction | Verified by |
|---|---|---|---|
| TBD | TBD | TBD | TBD |

### Current feature inventory versus intended project data

The project context lists age, sex, height, weight, status, and area/year in historical records; richer anticipated 2026 fields include maternal age/education, income range, family size, occupation, breastfeeding history, complementary feeding, meals, dietary diversity, Triposha/vitamins, and birth weight. These are *potential* data fields, not a confirmed C1 model schema. The current C2 request accepts only the subset below:

| Group | Current C2 fields | Integration decision |
|---|---|---|
| Actionable test behaviors | `meals_per_day`, `dietary_diversity` | +1 transitions are synthetic software rules; replace only after domain review. C1 must actually use and encode these fields for meaningful model comparison. |
| Immutable | `age_months`, `sex` | Remain unchanged in every candidate. |
| Historical | `birth_weight_kg`, `historical_exclusive_breastfeeding` | Observed only; never rewritten as a present intervention. |
| Observed, non-actionable here | `supplement_use` | Distinct from access and eligibility; no supplement candidate is generated. |
| Household/socioeconomic context | `household_income_band` | Never manipulated to change a prediction. Maternal and family fields are not in the current request. |
| Feasibility/eligibility context | budget, local availability, practicality, age suitability, eligibility, clinical suitability, transition justification; supplement access/programme eligibility/suitability | Unknown does not pass. These are constraints, not changed prediction features. Clinic access is not modelled and must not be inferred. |
| Anthropometric/status/geographic fields | Not in C2 child schema | Do not add as mutable features. Their role depends on C1's finalized target and leakage review. |

## Method-specific handoff

- **Bounded search:** C1 adapter supplies the versioned contract and category prediction. Actionable transitions remain in the C2 policy.
- **DiCE:** adapter additionally supplies the same fitted classifier used by `predict_category`, an explicit versioned reference dataframe, exact query mapping, outcome column, target class encoding, and class-label mapping. The generator checks baseline and candidate agreement between the DiCE model and final predictor. Incompatible models fail; they do not use the test model as fallback.
- **FACE-inspired graph:** adapter additionally supplies versioned reference points with the required actionable columns. The current graph supports integer one-step transitions in the two Phase 1 features. Applying it to different real features requires a reviewed graph representation and policy. Do not reuse the synthetic design grid as real reference data.

## Integration checklist

1. Confirm C1's operational target labels against source forms and any MAM/SAM versus surveillance-indicator distinction.
2. Freeze model ID/version, exact feature order, preprocessing code/version, encodings, units, and missing-data rules.
3. Verify whether each candidate feature is a true C1 input, actionable, temporally appropriate, and free of target leakage.
4. Obtain an approved, de-identified reference dataset where required; record provenance, coverage, and access controls. Do not commit child-level records or model binaries.
5. Verify model artifact checksum and dependencies; load only trusted artifacts.
6. Test baseline and candidate predictions against the frozen C1 adapter; fail on category or version mismatch.
7. Obtain domain-expert review of allowed transitions, local feasibility/eligibility rules, intervention wording, and professional review workflow.
8. Evaluate on held-out real data under the project’s privacy and research protocol. Synthetic software tests alone cannot support clinical-effectiveness claims.

## Phase 5 two-output handoff (`c2-predictor-v2`)

C1's planned output has **two distinct labels**: malnutrition type and severity.
For this interface, C1 supplies `predict_outcomes(child) -> ModelPrediction` and
a `PredictorContract` with `output_mode="type_severity"`,
`interface_version="c2-predictor-v2"`, separately defined `type_targets` and
`severity_targets`, an exact `severity_order` from least to most severe, and
explicit `accepted_type_transitions`. These definitions must be approved by C1
and domain reviewers; C2 does not assign clinical meaning to any code. The old
single-category v1 path remains for compatibility and synthetic testing; it
must not be presented as a validated mapping of type and severity.

`ModelPrediction` has `type_label`, `severity_label`, and optional per-output
probability maps for internal evaluation. A missing or undeclared baseline
label makes the adapter incompatible. Missing or unsupported candidate output
is unresolved. Candidate severity must not move to a higher index in C1's
declared order. A type change must be in the declared allowed-transition set.
At least one output must make approved progress; a candidate with no change is
rejected. Probabilities are never part of intervention cards, and no
probability difference is interpreted as clinical benefit.

For DiCE, C1 must additionally provide an adapter whose classifier predicts a
**joint type/severity label**, with `dice_prediction(label)` mapping each joint
class back to both C1 outputs, `dice_target_label` denoting an approved target,
and matching reference data and query preprocessing. Generation-model labels
are checked against `predict_outcomes` at baseline and every emitted candidate;
the shared pipeline applies non-worsening policy again. If a valid joint-label
classifier or verified reference set is unavailable, use bounded search or the
graph method only when their own prerequisites are satisfied. The graph method
requires explicit C1 reference points and never falls back to the synthetic
grid in real mode. All three methods use the same final policy gate.

**Still required from C1:** exact input feature list and encodings, both output
label definitions, a reviewed severity order and allowable type transitions,
model artifact hash and loading code, missing-output rules, calibrated
probabilities if supplied, and versioned reference data where needed. A
qualified reviewer must approve feeding transitions, safety/eligibility rules,
food evidence sources, intervention wording, and referral policy separately.
