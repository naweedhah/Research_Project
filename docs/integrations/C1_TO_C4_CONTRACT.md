# C1 ↔ C4 Contract (Drift observations + model update proposals)

## C1 → C4 events

| Event | When | Path |
|---|---|---|
| `c1.prediction.completed` | After prediction commit | `POST {C4}/v1/observations/predictions` |
| `c1.clinician_review.completed` | After structured review | `POST {C4}/v1/observations/clinician-reviews` |
| `c1.model.activated` | After authorized activation | `POST {C4}/v1/observations/model-activations` |

Headers: Bearer `C4_INTEGRATION_TOKEN`, correlation, contract version, idempotency.

Idempotency examples:

- `c4-prediction:{prediction_id}`
- `c4-review:{clinician_review_id}`

Schemas: `c1-c4-prediction-observation.v1.json`, `c1-c4-clinician-review-observation.v1.json`.

### Score semantics (critical)

Demo:

```json
"score": { "value": 0.58, "kind": "demo_progression_score", "is_probability": false, "is_calibrated": false }
```

Future calibrated model may use `calibrated_malnutrition_probability` without changing envelope shape.

Features: approved de-identified snapshot + missingness + schema versions. No operational identity.

Clinician review observation: assessment/workflow + optional clinician_status/severity (**null if not recorded**). No clinical free-text.

## C4 → C1 model update

`POST /integrations/c4/model-update-proposals`  
Auth: Bearer `C4_INTEGRATION_TOKEN` only (not clinicians, not C3).

Schema: `c1-c4-model-update-proposal.v1.json`

C1 validates `contract_version=1.0`, feature/label schema vs active model, artifact uri+sha256.  
Registers `ModelStatus.CANDIDATE` — **never auto-activates**.

Activation: existing `POST /models/{id}/activate` (`model:activate`).

Unsupported `contract_version` → 422.

## Failure

C4 offline ≠ prediction failure. Events stay pending/retryable.

## Status

`GET /integrations/status` (admin/research) — CONNECTED / DEGRADED / OFFLINE / NOT_CONFIGURED.
