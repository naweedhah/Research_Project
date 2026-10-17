# C1 → C3 Contract (Intervention Reassessment)

## Trigger

Structured clinician review with:

`workflow_action = REQUEST_INTERVENTION_REASSESSMENT`

C1 does **not** auto-call C3 on every risk increase.

## Outbound delivery

- Durable outbox: `integration_events` (`target=c3`, `event_type=counterfactual.requested`)
- HTTP: `POST {C3_COUNTERFACTUAL_URL}/v1/intervention-reassessments`
- Headers: `Authorization: Bearer {C3_INTEGRATION_TOKEN}`, `X-Correlation-ID`, `X-Contract-Version: 1.0`, `Idempotency-Key`

## Idempotency

`c3-reassessment:{prediction_id}:{clinician_review_id}`

## Request schema

`packages/contracts/integrations/c1-c3-request.v1.json`  
Pydantic: `C3InterventionRequestV1`

Includes: pseudonymous child id, visit, prediction + **score semantics** (demo vs calibrated), longitudinal C1 outputs, alerts, approved feature snapshot, data quality.  
`explanation_context_ref` is always `null` unless a future C2 reference exists — **C1 never fabricates SHAP**.

## Response schema

`c1-c3-response.v1.json` — status `QUEUED|PROCESSING|COMPLETED|FAILED`, optional `result_id` / `result_url`.

## What C1 does NOT send

Names, phones, MRN, NIC, address, clinical notes, C2 SHAP, intervention recommendations.

## Failure

C3 offline → clinician review still saves; request remains `QUEUED` / outbox retryable. UI: “Request queued · Component 3 temporarily unavailable”.

## Status for UI

`GET /children/{child_id}/c3-reassessment` (auth: `child:read`)
