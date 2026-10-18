# Deployment

The supported demonstration launch is native Windows. Docker is not required.

## This computer

First time:

```powershell
.\SETUP_PROJECT.ps1
```

Every demonstration:

```powershell
.\START_PROJECT.ps1
```

Stop with `.\STOP_PROJECT.ps1`. Status with `.\CHECK_PROJECT.ps1`.

Local services:

- Website: http://localhost:3000
- API: http://127.0.0.1:8000
- Inference: http://127.0.0.1:8001
- PostgreSQL: 127.0.0.1:5432, database `cnip`

`SEED_ON_START` stays false. Schema updates are `alembic upgrade head` from `services/api`. They do not drop tables.

Startup requires the prediction service to report `GA-RGCA-v4-Rolling-RSL`. Another model version fails startup.

Do not enable live SMS/email unless `NOTIFICATION_PROVIDER` and API keys are explicitly configured.

Archived container files, if still present, are not part of normal startup.
