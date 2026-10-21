# Professor demonstration guide

One-page flow for showing the Child Nutrition Intelligence Platform to Professor Guwani.

## Start

1. Double-click `START_PROJECT.bat` in the project folder (or run `.\START_PROJECT.ps1`).
2. Wait until the window says **SYSTEM READY**.
3. Browser: http://localhost:3000
4. Sign in with the demonstration doctor account already used on this laptop (`doctor@demo.local`). Use the usual local demo password — do not read it aloud.

The active model is **GA-RGCA-v4-Rolling-RSL**. Horizon: **12 months**. This is a research decision-support prototype. Clinician confirmation is required.

## Demo flow

1. **Dashboard** — clinic totals and who needs attention today.
2. **Children** — each row keeps **current WHO** and the **12-month prediction** in separate columns.
3. Open **C-1137** or another child with several visits.
4. Show **current WHO assessment** from the latest measurements (the child today).
5. Show the **next-12-month GA-RGCA prediction** (navy / future). Say clearly: these are different time points.
6. Show the four probabilities: Underweight, Stunting, MAM, SAM.
7. **Progress** — visit cards and the trend chart. Each visit keeps its own stored prediction.
8. **AI Details** — model identity, uncertainty, applicability, conformal set, modality reliability. Reliability is not feature importance.
9. **Clinic Board** — who needs review, with current WHO and future risk as separate reasons.
10. Optionally **New Visit** on a follow-up child. A new visit creates a new 12-month prediction and does not rewrite earlier visits.
11. **Model Intelligence** — one active model, 3 neural members, 5 SuperLearner experts, research (not clinical) metrics.
12. Close with limitations: research prototype, not externally validated, not for independent clinical use.

Suggested contrast child: **C-1135** (current undernutrition and a high 12-month Stunting prediction).

## If something fails

Run:

```
.\CHECK_PROFESSOR_DEMO.ps1
```

Then open the `logs` folder (`launcher.log`, `api.err.log`, `inference.err.log`, `frontend.err.log`).

### Emergency recovery

| Problem | What to do |
|---|---|
| Website will not load | Run `.\STOP_PROJECT.ps1`, then `START_PROJECT.bat` again. Wait for SYSTEM READY. |
| API errors / cannot save a visit | Same full restart. Confirm Clinical API is READY in the checker. |
| Predictions fail / model not loaded | Check `http://127.0.0.1:8001/model-info` and `logs\inference.err.log`. Restart the project. Do not invent a result. |
| PostgreSQL unavailable | Windows Services → start **postgresql-x64-16**. Then start the project again. |

Saved children and visits stay in the local `cnip` database across restarts.

## After the session

Run `.\STOP_PROJECT.ps1`. PostgreSQL can stay running.
