# Integration Quickstart — C1 with C3 (Shamiq) and C4 (Naveed)

## Ownership

| Component | Owns |
|---|---|
| **C1 (Chanodya)** | Child/visit/prediction/longitudinal/alerts/clinician review/follow-up/model registry |
| **C3 (Shamiq)** | Counterfactual generation, feasibility, ranking, intervention options |
| **C4 (Naveed)** | Population/model drift, recalibration decisions |

Source of truth if components disagree:

- Patient/visit/prediction → **C1**
- Intervention result → **C3**
- Drift / model-maintenance decision → **C4**

## Architecture

Separate applications → versioned HTTP/event contracts → durable outbox → independent deployment.

C1 does **not** share PostgreSQL with C3/C4.

## Configure C1

```bash
INTEGRATION_MODE=live          # or mock for local-only
C3_COUNTERFACTUAL_URL=https://c3.example
C3_INTEGRATION_TOKEN=...
C4_DRIFT_URL=https://c4.example
C4_INTEGRATION_TOKEN=...
INTEGRATION_TIMEOUT_SECONDS=8
INTEGRATION_MAX_RETRIES=5
```

With `INTEGRATION_MODE=mock` or empty URLs, C1 boots and clinics work; events stay queued (`NOT_CONFIGURED`).

## Sequences

### C3

Doctor completes clinician review with `REQUEST_INTERVENTION_REASSESSMENT` → C1 saves review → outbox event `counterfactual.requested` → worker POSTs `/v1/intervention-reassessments` → C1 stores external request/result refs.

### C4

Prediction commits → outbox `prediction.completed` → worker POSTs observation → later clinician review → `clinician_review.completed` → C4 may POST `/integrations/c4/model-update-proposals` (Bearer C4 token) → C1 registers `CANDIDATE` → authorized `POST /models/{id}/activate` → `model.activated` event.

## Contracts

See `C1_TO_C3_CONTRACT.md`, `C1_TO_C4_CONTRACT.md`, and `packages/contracts/integrations/*.json`.

## Privacy

Never send: full name, caregiver name/phone, MRN, NIC, address, clinical free-text notes.
