# Tomorrow morning — start checklist

Do this in order. Do not open Cursor first.

1. Turn on the laptop.
2. Wait until Windows desktop is ready.
3. Double-click `START_PROJECT.bat` in the project folder.
4. Wait until the window says **SYSTEM READY**.
5. If anything looks wrong, run `CHECK_PROFESSOR_DEMO.ps1` in the same folder.
6. Open http://localhost:3000
7. Sign in with the demonstration doctor account already used on this laptop (`doctor@demo.local`). Use the usual local demo password — do not read it aloud.
8. Open **C-1137** and **C-1135**.

Notes:

- PostgreSQL (`postgresql-x64-16`) is set to start automatically with Windows.
- `START_PROJECT.bat` starts PostgreSQL check, the inference service, the clinical API, and the frontend. No other hidden windows are required.
- Cursor does not need to be open.
- Model files are loaded from `ml/artifacts/ga_rgca_v4_rsl/` inside this project folder.

If the website does not load: run `STOP_PROJECT.ps1`, then double-click `START_PROJECT.bat` again.
