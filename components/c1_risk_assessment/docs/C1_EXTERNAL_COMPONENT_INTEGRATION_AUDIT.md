# C1 External Component Integration Audit

Controlled integration-readiness pass for CNIP Component 1 (J26-IT-399).  
Scope: C1 → C3 (Shamiq) and C1 → C4 (Naveed) contracts only. No C3/C4 algorithms.

---

## Current integration inventory

| Path | Role | Works vs mock |
|---|---|---|
| `services/api/app/api/integrations.py` | Sync HTTP stubs: C3 `/reassess`, C2 `/explain`, C4 `/observe` | Persist works; sync HTTP best-effort; no retry |
| `services/api/app/integrations/c3/client.py` | Constants only | Mock messaging |
| `services/api/app/integrations/c4/client.py` | `CONNECTED = False` | Stub |
| `services/api/app/integrations/c2/client.py` | Constants only | Mock messaging |
| `services/api/app/services/prediction.py` `_emit_event` | Writes `integration_events` with `target=internal` | **No delivery** |
| `services/api/app/services/clinician_review.py` | Stores `REQUEST_INTERVENTION_REASSESSMENT` | **Does not enqueue C3** |
| `services/api/app/models/operations.py` `IntegrationEvent` | Minimal outbox columns | Missing status/attempts/idempotency |
| `workers/alerts/tasks.py` | Missed follow-ups only | No integration drain |
| `packages/contracts/` | Clinical/feature YAML | **No integration schemas** |

### Endpoints / payloads (before this pass)

| Endpoint | Payload | Delivery |
|---|---|---|
| `POST /integrations/counterfactual/request` | `CounterfactualRequest` (loose) | Sync if `C3_COUNTERFACTUAL_URL` |
| `POST /integrations/drift/observe` | Untyped `dict` | Sync if `C4_DRIFT_URL` |
| Prediction `_emit_event` | `{child_id, visit_id, model_version, risk, mode}` | Never |

### Config

`C2_EXPLAINABILITY_URL`, `C3_COUNTERFACTUAL_URL`, `C4_DRIFT_URL`, `INTEGRATION_MODE=mock` (mode unused). No service tokens.

---

## What genuinely works

- Persist `integration_events` rows
- Manual C3 request API (doctor permission `integration:request`)
- Honest C2 “not connected” UI
- Demo score display semantics (P0)

## What is mock / missing

| Gap | Risk |
|---|---|
| No durable delivery status / retries | Lost events when C3/C4 offline |
| Clinician reassessment ≠ C3 enqueue | Product gap |
| No typed C4 prediction/review observations | Drift partner cannot consume reliably |
| No C4 model-update proposal / `CANDIDATE` | Activation unsafe |
| No M2M auth tokens | Cookie-based coupling risk |
| Identity fields may leak in loose payloads | Privacy |
| Demo score sent as bare `risk` | Misleads C4 |

---

## Tight-coupling risks (to remove)

1. Inline `httpx` in FastAPI handlers  
2. Hardcoded `/reassess`, `/observe` paths without versioned contracts  
3. Untyped C4 dict payloads  
4. `INTEGRATION_MODE` unused  
5. Model activate with no candidate gate for C4 proposals  

---

## Required changes (this pass)

| Change | Files |
|---|---|
| Versioned JSON contracts + Pydantic DTOs | `packages/contracts/integrations/*`, `app/integrations/common/*` |
| Approved feature snapshot builder | `app/integrations/common/feature_snapshot.py` |
| Extend outbox + Celery drain | model, migration `0004`, `delivery.py`, worker |
| C3 enqueue on clinician reassessment | `care.py` + C3 mapper |
| C4 observations on prediction + review | `prediction.py`, `care.py` |
| C4 model-update proposal → `CANDIDATE` | `integrations.py`, `ModelStatus` |
| Service tokens + status API | config, auth, admin UI |
| C3 status on child profile | compact panel |
| Docs + examples + tests | `docs/integrations/*` |

---

## Non-goals (preserved)

- No counterfactual / ranking / feasibility logic in C1  
- No concept-drift / recalibration / retraining in C1  
- No SHAP / C2 implementation  
- No shared DB with C3/C4  
- P0 demo semantics and P1 clinician workflow preserved  
