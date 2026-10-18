# Viva launch guide

## Before the viva

1. Turn the laptop on.
2. PostgreSQL should already be running. The launcher checks it. If it is stopped, open the Windows Services app and start **postgresql-x64-16**.
3. Double-click `START_PROJECT.bat`, or run `.\START_PROJECT.ps1` in this project folder.
4. Wait until the window says **SYSTEM READY**.
5. The browser opens at http://localhost:3000.
6. Sign in with the demonstration doctor account: doctor@demo.local. Use the same password you already use for this project.

## What to show

- Dashboard
- Children
- New visit
- Current WHO undernutrition assessment
- 12-month GA-RGCA prediction
- AI Details
- Clinic Board
- A second visit, which creates a new 12-month prediction and keeps the earlier one

The model in use is **GA-RGCA-v4-Rolling-RSL**. It is a research decision-support prototype. A clinician must confirm the result.

## If something fails

1. Run `.\CHECK_PROJECT.ps1`.
2. Read the short message in the launcher window.
3. Open the `logs` folder next to this project for `launcher.log`, `api.err.log`, `inference.err.log`, and `frontend.err.log`.

Redis and the background worker are optional. The demonstration does not need them.

## After the viva

Run `.\STOP_PROJECT.ps1`. Saved children and visits stay in the local database.
