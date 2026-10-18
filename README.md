# Child Nutrition Intelligence Platform

Research decision-support prototype for a university demonstration.
A clinician must confirm every result. This is not a medical device.

Active model: **GA-RGCA-v4-Rolling-RSL**
Prediction: rolling 12-month nutritional risk

## QUICK START

### First time only

1. Install Python 3.12 from [python.org](https://www.python.org/downloads/). Tick **Add python.exe to PATH**.
2. Install Node.js LTS from [nodejs.org](https://nodejs.org/).
3. Install PostgreSQL 16. It is already used on this computer if the PostgreSQL service is running.
4. In this folder, run:

```powershell
.\SETUP_PROJECT.ps1
```

### Normal use

```powershell
.\START_PROJECT.ps1
```

Or double-click `START_PROJECT.bat`.

Wait until the window says **SYSTEM READY**. The browser opens at http://localhost:3000.

### Stop

```powershell
.\STOP_PROJECT.ps1
```

This stops the website, the clinical API, and the prediction service. It does not stop PostgreSQL, and it does not delete visits.

### Check status

```powershell
.\CHECK_PROJECT.ps1
```

## Addresses

| Part | Address |
|---|---|
| Website | http://localhost:3000 |
| Clinical API | http://127.0.0.1:8000 |
| Prediction service | http://127.0.0.1:8001 |
| Database | PostgreSQL on 127.0.0.1 port 5432, database `cnip` |

Docker is not required. Older container files are kept only as an archive in `legacy/docker` and are not used to start the project.

## If something fails

Run `.\CHECK_PROJECT.ps1`.

Log files are in the `logs` folder:

- `launcher.log`
- `inference.log` and `inference.err.log`
- `api.log` and `api.err.log`
- `frontend.log` and `frontend.err.log`

A short demonstration checklist is in `docs/VIVA_LAUNCH_GUIDE.md`.

## What starts

Required:

- PostgreSQL
- GA-RGCA v4 prediction service
- Clinical API
- Website

Optional, and not started by the launcher:

- Redis
- Background alert worker

The clinic demonstration works when Redis and the worker are absent.

## Model files

The active weights stay in `ml/artifacts/ga_rgca_v4_rsl/`.
Older v3 weights stay in `ml/artifacts/ga_rgca_v3/` for rollback only.
The launcher does not retrain the model and does not change thresholds.

`C1_MODEL_VERSION` must be `ga_rgca_v4_rsl` or `ga_rgca_v3`. Any other value is rejected. The default is `ga_rgca_v4_rsl`.

## For developers

```powershell
cd services\api
.\.venv\Scripts\python.exe -m pytest -q

cd ..\inference
.\.venv\Scripts\python.exe -m pytest -q

cd ..\..\apps\web
npm run typecheck
npm test
npm run build
```

Database schema updates, without deleting data:

```powershell
cd services\api
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The one-time demonstration seed runs only from `SETUP_PROJECT.ps1` when the users table is empty. Starting the project does not seed again.
