# Architecture

Component 1 of *Explainable AI Framework for Early Detection and Personalized Intervention of Childhood Malnutrition in Sri Lanka*.

## Services

```
Browser (Next.js)
    → FastAPI API (auth, RBAC, domain, audit)
        → PostgreSQL
        → Redis
        → Inference service (adapters)
        → Celery alert worker
        → C2 / C3 / C4 integration adapters (mock unless URL configured)
```

## Clinical data flow

1. Health worker records a multimodal visit (anthropometry, socioeconomic, dietary, maternal/child health).
2. Data-quality validation uses the versioned clinical policy — not invented WHO cut-offs.
3. Inference runs four modality encoders and multi-head cross-attention (or the demo adapter).
4. Heads emit status, severity and a **calibrated** risk probability.
5. Latent vector `e_t` is stored with `embedding_space_id`.
6. Risk Velocity and baseline recovery rate are computed against Vt-1 and V0.
7. Adaptive alerts (stagnation, deterioration, relapse, missed follow-up) are de-duplicated by event window.
8. Integration events are persisted before external delivery.

## Research vs clinical UI

Clinical screens translate the pipeline into status, risk, progress, trend and next action.  
Research screens expose architecture, experiments and evaluation — never as a patient workflow.

## Tenancy

Facility-scoped queries in the API plus PostgreSQL RLS (`app.facility_id`, `app.rls_bypass` for system administrators).
