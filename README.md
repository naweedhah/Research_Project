# Childhood Malnutrition AI Research Project

AI/ML decision support for childhood nutrition in Sri Lanka, aligned with the community
maternal-and-child-health workflow (MOH / PHM). The project has four complementary components.

| # | Component | Question it answers | Folder |
|---|-----------|---------------------|--------|
| 1 | Multimodal Early Detection / Risk Assessment | What is this child's malnutrition risk/status? | [components/c1_risk_assessment](components/c1_risk_assessment/) |
| 2 | Personalized Counterfactual Intervention Engine | What feasible changes could improve the child's situation? | [components/c2_counterfactual_intervention](components/c2_counterfactual_intervention/) |
| 3 | Adaptive Model Reliability Monitoring and Safe Maintenance | Can the deployed model still be trusted, and how should it be safely maintained? | [components/c3_reliability_maintenance](components/c3_reliability_maintenance/) |
| 4 | Spatio-Temporal Burden Forecasting and Resource Demand Visualization | Where and when is burden likely to increase? | [components/c4_spatiotemporal_forecasting](components/c4_spatiotemporal_forecasting/) |

## Repository layout

```
├── components/                       # research work, one folder per component
│   ├── c1_risk_assessment/
│   ├── c2_counterfactual_intervention/
│   ├── c3_reliability_maintenance/
│   └── c4_spatiotemporal_forecasting/
├── backend/                          # one API server, one router per component
├── frontend/                         # one web app, one page per component
├── data/                             # local only, not committed (see data/README.md)
└── docs/                             # shared project context and documentation
```

- **Components** are self-contained: each has its own code, tests, results and README, and
  can be run and demonstrated on its own.
- **Backend** and **frontend** form the integrated system. The backend imports from
  `components/`; the frontend calls the backend.

## How the components connect

- **C1 → C2:** C2 uses C1's predictions to generate intervention recommendations.
- **C1 → C3:** C3 monitors and maintains the model C1 produces. The contract is defined in
  [component3/interfaces.py](components/c3_reliability_maintenance/component3/interfaces.py).
- **C4** forecasts area-level burden from the same data sources.

## Working in this repo

- Work inside your own component folder, plus your own router in `backend/` and page in `frontend/`. Do not edit another member's part without agreeing first.
- Create a branch per piece of work (`c1/...`, `c2/...`, `c3/...`, `c4/...`) and merge into `main` by pull request.
- **Never commit child-level data.** Data files and model artifacts are git-ignored.

Project background: [docs/project_context.md](docs/project_context.md).
