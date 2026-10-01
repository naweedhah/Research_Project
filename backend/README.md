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
