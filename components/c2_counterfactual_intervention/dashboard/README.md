# FedNutri-XAI Component 2 research dashboard

Standalone React interface for the existing C2 FastAPI research routes. The Studio uses a synthetic test predictor. The separate C1 Model Validation screen invokes the genuine loaded model through a fixed synthetic C2 fixture with `allow_demo=false`, and never issues intervention cards. No real child records are stored. Neither mode is clinically validated.

## Prerequisites

- Node.js 20.19+ or 22.12+ and npm (Node 24 is also supported by current Vite).
- Python environment with the repository's backend and C2 requirements installed.
- A working FastAPI server at `http://127.0.0.1:8000`.

## Windows launch

Open two PowerShell terminals at `D:\Research_Project`:

```powershell
$env:PYTHONPATH = '.;backend'
py -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
cd components/c2_counterfactual_intervention/dashboard
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. The Vite proxy forwards `/interventions` and `/health` to FastAPI. The default API base path is empty, so browser requests stay on the Vite origin. Set `VITE_API_BASE_PATH` only for a same-origin deployment or a backend with properly configured CORS; never put C1 secrets in `VITE_*` variables.

## Validation

```powershell
npm.cmd run build
npm.cmd run test
```

From the repository root:

```powershell
$env:PYTHONPATH = '.;backend'
py -m pytest components/c2_counterfactual_intervention/tests -q
```

## API and fixture contract

- `GET /interventions/status` drives the Overview status cards.
- `POST /interventions/c1-research` drives Studio results. The dashboard sends `mode=simulated` only.
- Eight JSON fixtures under `src/fixtures` were serialized from `supervisor_demo.demo_request()`. They contain synthetic identifiers, measurements, prices and policy assertions.
- Selecting a scenario loads its complete Python-generated fixture. A changed profile preserves the entered synthetic measurements but clears the fixture's positive feasibility assertions, food planning and policy approval. Such a run may return unresolved candidates; the UI never creates a substitute card.
- The public response shows category labels, actual backend explanation and rejection reasons. No risk percentages or predicted risk-reduction claims are shown.

## Scope and troubleshooting

Overview, Counterfactual Studio, C1 Model Validation and Food Price References are functional. Algorithm Comparison and Evidence & Status are clearly marked as upcoming. Model Validation calls `GET /interventions/c1-validation` only when the user starts a check. Food Price References calls `GET /interventions/price-references` and identifies Colombo coverage, source report and dates. Neither page makes a treatment or Kalmunai availability claim. The official-price CLI remains available for illustrative unit conversion.

If the Overview reports an offline backend, confirm FastAPI starts and `http://127.0.0.1:8000/interventions/status` responds. HTTP 422 means the submitted fixture or edited values failed backend validation. HTTP 503 means a backend dependency is unavailable. A timeout or malformed response is displayed as an error, with no generated cards. Real C1 model artifacts, professional review, verified household data and Kalmunai availability remain external dependencies.

On this workstation, the default npm registry certificate was not trusted. Installation succeeded with TLS verification enabled using `npm.cmd install --registry=https://registry.yarnpkg.com --replace-registry-host=always`. Use that process-scoped command if the same certificate problem recurs. Do not disable npm's `strict-ssl` setting. The committed lockfile records exact package versions and integrity hashes.
