# Child Nutrition Intelligence Platform

**AI-Assisted Malnutrition Risk & Progress Monitoring**

Undergraduate research prototype (Component 1 · J26-IT-399).  
**AI-assisted decision support. Clinical review required.**  
When the demo adapter is active the UI shows **DEMO MODEL — NOT FOR CLINICAL USE**.

Product name lives in `packages/contracts/product.json`.

---

## Architecture

| Service | Role |
|---|---|
| `apps/web` | Next.js clinical / research UI |
| `services/api` | FastAPI domain API, auth, RBAC, audit |
| `services/inference` | Model adapters (demo / sklearn / pytorch / onnx) |
| `workers/alerts` | Celery beat + worker for missed follow-ups |
| `ml/` | Training, evaluation, calibration, trajectory projection |
| PostgreSQL + Redis | Persistence and queue |

See `docs/ARCHITECTURE.md` for data flow.
See `docs/COMPONENT1_CONTEXT.md` for authoritative Component 1 research, clinical UX, and component-boundary specification (J26-IT-399).

---

## Prerequisites

- Docker and Docker Compose (recommended), or
- Node.js 22, Python 3.12, PostgreSQL 16, Redis 7

---

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Web: http://localhost:3000
- API + OpenAPI: http://localhost:8000/docs
- Inference: http://localhost:8001/health

First boot runs `alembic upgrade head` and seeds demonstration data.

### Local web dev (without rebuilding Docker web)

From the **repository root**:

```bash
npm run dev
```

Or from `apps/web` directly. The Next.js app lives in `apps/web` — there is no separate frontend at the root except the convenience scripts in root `package.json`.

API and database should still be running via Docker:

```bash
docker compose up -d postgres redis api
```

---

## Demo accounts (development only)

Password for all seed users: `doctor123`

| Role | Email | Name |
|---|---|---|
| Doctor (Colombo) | doctor@demo.local | Prof. Pujitha Wickramasinghe |
| Doctor (Colombo) | doctor@gmail.com | Prof. Shamya de Silva |
| Doctor (Kandy) | doctor.kandy@demo.local | Prof. A.H.H.M. Jayaweera |

Only doctor accounts can sign in. Non-doctor seed roles are not created in new installs.

Never use these passwords in production.

The seed includes **25 synthetic demonstration children** across Colombo, Kandy, and Galle facilities.

Canonical demonstration child: **C-1042** (risk 82% → 61% → 59%, stagnating).

---

## Environment

Copy `.env.example`. Important keys:

- `DATABASE_URL`, `REDIS_URL`
- `JWT_SECRET`, `JWT_REFRESH_SECRET`
- `MODEL_MODE=demo` (or `pytorch` / `sklearn` / `onnx`)
- `MODEL_ARTIFACT_PATH`
- `FRONTEND_URL`
- `NOTIFICATION_PROVIDER=mock`

---

## Database

```bash
cd services/api
alembic upgrade head
python -m app.seed
```

---

## Tests

```bash
# API
cd services/api && pytest -q

# ML
cd ../.. && PYTHONPATH=. pytest -q ml/tests

# Frontend
npm run test
npm run build
```

(`npm run dev`, `npm test`, etc. work from the repository root and delegate to `apps/web`.)

---

## Train models

From the repository root:

```bash
python -m ml.data.make_synthetic
python -m ml.training.train_baselines
python -m ml.training.train_multimodal
python -m ml.evaluation.compare_models
python -m ml.trajectory.fit_projection
```

Configs: `ml/configs/baseline.yaml`, `multimodal.yaml`, `longitudinal.yaml`.

If no experiment has been run, research pages show **No experimental result available**. Metrics are never fabricated.

---

## Switch Demo → real model

1. Train and place an artifact under `MODEL_ARTIFACT_PATH`.
2. Set in `.env`:

```text
MODEL_MODE=pytorch
MODEL_ARTIFACT_PATH=/artifacts/active/multimodal.pt
```

3. Restart the inference service. The frontend does not need changes. Demo badge disappears only when `mode` is not `DEMO`.

---

## Production

See `docs/DEPLOYMENT.md` and `docker-compose.prod.yml`.
