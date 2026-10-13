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

Code: `app/routers/maintenance.py` (endpoints) and `app/c3/` (service + model-health page). It imports the C3 package
from `components/c3_reliability_maintenance` and reads child-level data from `C3_DATA_DIR` (never stored in the repo).

```bash
export C3_DATA_DIR=/path/to/clean_malnutrition_data
uvicorn app.main:app --reload            # then open http://localhost:8000/maintenance/dashboard
python -m pytest tests_c3                # API tests (cycle tests skip without the data)
```

Endpoints: `GET /maintenance/status`, `/scenarios`, `/context?start=&end=&offline=`, `/history`, `/dashboard`;
`POST /maintenance/cycle`, `/approve`, `/reject-pending`, `/rollback`, `/reset`.
