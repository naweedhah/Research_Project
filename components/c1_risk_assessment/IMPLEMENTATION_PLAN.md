# Implementation Plan — Child Nutrition Intelligence Platform

**Component 1:** Multimodal Early Detection Model for Paediatric Malnutrition Type and Severity Prediction  
**Enhanced Scope:** Longitudinal Risk & Latent Trajectory Progress Tracking System  
**Research Member:** Kavindi T.A.C. (IT22541048) · Project ID J26-IT-399

This document records architecture, assumptions, and the phase sequence used to build the working system.

---

## 1. Product identity

Product name, subtitle, and research metadata live in a **single source of truth**:

`packages/contracts/product.json`

Frontend and backend consume this file (copied/mounted at build time). Renaming the product later requires changing that file only.

---

## 2. Architecture

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Next.js Web │────▶│  FastAPI API │────▶│ PostgreSQL      │
│  (apps/web)  │     │ (services/api)│     │ Redis           │
└──────────────┘     └──────┬───────┘     └─────────────────┘
                            │
                 ┌──────────┼──────────┐
                 ▼          ▼          ▼
        ┌────────────┐ ┌─────────┐ ┌──────────────────┐
        │ Inference  │ │ Celery  │ │ C2 / C3 / C4     │
        │ service    │ │ alerts  │ │ integration      │
        │ (adapters) │ │ worker  │ │ adapters (mock)  │
        └────────────┘ └─────────┘ └──────────────────┘
                 ▲
                 │ training artifacts (optional)
        ┌────────┴────────┐
        │ ml/ pipelines   │
        │ baselines + MCA │
        └─────────────────┘
```

### Service boundaries

| Service | Responsibility |
|---|---|
| `apps/web` | Clinical and research UI. Never trusts UI-only RBAC. |
| `services/api` | Auth, RBAC, domain, audit, orchestration, OpenAPI. |
| `services/inference` | Model adapters (demo / sklearn / pytorch / onnx). Stateless. |
| `workers/alerts` | Scheduled missed-follow-up and duplicate-safe alert evaluation. |
| `ml/` | Training, evaluation, calibration, trajectory projection. Separate from production inference. |
| `packages/contracts` | Shared product config, label schemas, feature-set YAML. |

### Clinical workflow (implemented)

Health worker login → dashboard → find/register child → profile → new visit (6-step wizard) → data quality → inference (4 encoders → cross-attention → heads) → persist prediction + latent `e_t` → Risk Velocity vs V0 / Vt-1 → progress state → adaptive alerts → optional C3 reassessment request.

---

## 3. Assumptions (research-safe)

1. **This is an undergraduate research prototype**, not a clinically validated medical device.
2. **Demo model** is deterministic and labelled `DEMO MODEL — NOT FOR CLINICAL USE`. No fabricated clinical validity.
3. **Label schema** (`normal`, `stunting`, `wasting`, `underweight` + severity) is a **development default** pending final research label definition.
4. **Clinical thresholds** (stagnation, deterioration, follow-up grace) come from versioned `clinical_policy_versions` marked **Research / Demo Configuration**.
5. **WHO growth standards are not reimplemented.** Anthropometric z-scores are not invented. Measurements are stored; any future WHO computation will be a pluggable calculator.
6. **No real SMS/email** in development. Notification providers are mocks unless credentials and `NOTIFICATION_PROVIDER` are explicitly set.
7. **C2/C3/C4** are integration interfaces + mock adapters. Component 1 does not implement another member’s novelty.
8. **Synthetic seed data** is labelled as such. C-1042 is the canonical demonstration case (82% → 61% → 59%).
9. **PII isolation:** caregiver names/contact are operational tables only. ML features use the pseudonymous child ID and approved clinical/socioeconomic/dietary/health fields.
10. **Embedding comparison** is refused across incompatible `embedding_space_id` values unless an alignment artifact exists.
11. **Predictions are immutable.** Re-runs create a new prediction row; one is marked active for clinical view.
12. **PostgreSQL UUID primary keys.** Facility-scoped access enforced in the API; RLS policies applied for least privilege.

---

## 4. Packages to install

### Frontend (`apps/web`)

- next, react, react-dom, typescript
- tailwindcss, postcss, autoprefixer
- class-variance-authority, clsx, tailwind-merge
- lucide-react
- react-hook-form, @hookform/resolvers, zod
- @tanstack/react-query
- recharts
- plotly.js, react-plotly.js
- framer-motion (subtle transitions only)
- cmdk (command palette)
- date-fns
- sonner (toasts)
- radix-ui primitives (via shadcn)

### Backend (`services/api`)

- fastapi, uvicorn, pydantic, pydantic-settings
- sqlalchemy[asyncio], asyncpg, alembic, psycopg2-binary
- python-jose[cryptography], passlib[bcrypt], bcrypt
- redis, celery
- httpx, python-multipart
- structlog
- prometheus-client (optional `/metrics`)
- pytest, pytest-asyncio, httpx

### Inference (`services/inference`)

- fastapi, uvicorn, pydantic, pydantic-settings
- numpy, torch (cpu), scikit-learn, joblib
- onnxruntime (optional)
- httpx

### ML (`ml/`)

- torch, scikit-learn, xgboost, lightgbm
- numpy, pandas, umap-learn, joblib
- pyyaml, matplotlib
- imbalanced-learn (SMOTENC, train-fold only)

### Infrastructure

- postgres:16-alpine
- redis:7-alpine
- nginx (production reverse proxy)

---

## 5. Phase sequence

| Phase | Deliverable |
|---|---|
| 1 | Monorepo, Docker Compose, env, product config |
| 2 | PostgreSQL schema + Alembic |
| 3 | Authentication + RBAC |
| 4 | Child registry |
| 5 | Visit workflow |
| 6 | Demo inference adapter |
| 7 | Predictions + progress UI |
| 8 | Longitudinal metrics (Risk Velocity, baseline recovery) |
| 9 | Trajectory visualization |
| 10 | Alerts + scheduler |
| 11 | Research / model-evaluation pages |
| 12 | ML training pipelines |
| 13 | C2/C3/C4 integration interfaces |
| 14 | Admin + audit tools |
| 15 | Tests (API, ML, frontend, Playwright) |
| 16 | Production Docker |
| 17 | Documentation |

After each phase: format, lint, typecheck, tests, and fix errors before continuing.

---

## 6. Demo accounts (development only)

| Role | Email | Password | Facility |
|---|---|---|---|
| Doctor (Colombo) | doctor@demo.local | DemoPass123! | MOH Colombo Demo |
| Doctor (Kandy) | doctor.kandy@demo.local | DemoPass123! | MOH Kandy Demo |
| Doctor (Galle) | doctor.galle@demo.local | DemoPass123! | MOH Galle Demo |

Only doctor accounts can sign in. Non-doctor seed roles are not created in new installs.

Never use these passwords in production.

---

## 7. Out of scope for this software iteration (research dependencies, not bugs)

- Real approved paediatric dataset and ethical clearance
- Clinically validated stagnation / deterioration thresholds
- WHO z-score engine as a diagnostic authority
- Live C2 explainability, C3 counterfactual, C4 drift services
- Production SMS/email credentials
- Hospital FHIR connectivity to a live national system
