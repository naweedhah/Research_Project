# Backend

One API server for the integrated system. It contains no ML logic of its own: each
router loads and calls the code/model from its component folder under `components/`.

| Router | Prefix | Component |
|--------|--------|-----------|
| `app/routers/risk.py` | `/risk` | C1 |
| `app/routers/interventions.py` | `/interventions` | C2 |
| `app/routers/maintenance.py` | `/maintenance` | C3 |
| `app/routers/forecast.py` | `/forecast` | C4 |

Each router currently has only a placeholder `/status` endpoint.

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs are then at http://localhost:8000/docs.

## Component 3 — model reliability and maintenance

Code: `app/routers/maintenance.py` (endpoints) and `app/c3/` (`live.py` live workflow, `service.py` demonstration
sandbox, `results.py` experiment results, `dashboard.html` model-health page). It imports the C3 package from
`components/c3_reliability_maintenance`, reads child-level data from `C3_DATA_DIR` and keeps live state in
`C3_STATE_DIR` (default `components/c3_reliability_maintenance/state/`). Neither is stored in the repo.

```bash
export C3_DATA_DIR=/path/to/clean_malnutrition_data
uvicorn app.main:app --reload            # or: components/c3_reliability_maintenance/run_demo.sh
python -m pytest tests_c3                # API tests; the real-data tests skip without C3_DATA_DIR
```

Interactive API docs: http://localhost:8000/docs (section "Model reliability and maintenance").

**Live workflow** — real batches; models, history and batches are saved and survive restarts:

| Endpoint | What it does |
|---|---|
| `POST /maintenance/live/batches` | Submit a screening round: `records` (one per child: pseudonymous `record_id` + every model input, `null` if not recorded), optional `batch_id`, `area`, `collected_from`/`collected_to`, `context` (`live`/`offline`/`none`). C3 validates it, checks drift and gives a label-free warning. Unknown answer options and ignored fields are reported. |
| `POST /maintenance/live/batches/{id}/outcomes` | Outcomes arrive (`labels`: record_id → 0/1, `require_approval`, default true). A newly deployed model is checked first (automatic rollback if worse than the previous one); then C3 assesses, adapts on 60% of the labelled records and verifies on the other 40%. |
| `GET /maintenance/live/status`, `/live/batches`, `/live/batches/{id}`, `/live/history` | Active model, pending approval, batches and their results, version history |
| `POST /maintenance/live/approve?approver=`, `/live/reject-pending`, `/live/rollback`, `/live/reset?confirm=true` | Human controls (reset deletes all live state) |

Responses never contain child records, only decisions and aggregate numbers. Errors: 400 invalid input, 404 unknown
batch, 409 conflicting state (e.g. nothing to approve, outcomes already submitted), 503 data not available.
`python -m component3.experiments.simulate_live` (from the C3 folder) sends a round of held-out real children, optionally
under a stress shift, and then their outcomes.

**Demonstration sandbox** (in memory, used by the dashboard): `GET /maintenance/status`, `/scenarios`, `/history`,
`/dashboard`; `POST /maintenance/cycle`, `/approve`, `/reject-pending`, `/rollback`, `/reset`.

**Shared:** `GET /maintenance/context?start=&end=&offline=` (external signals), `GET /maintenance/results` (experiment
summaries with links to `/results/{run}/report` and `/results/{run}/figures/{name}`).
