# Childhood Malnutrition AI Research Project

AI/ML decision support for childhood nutrition in Sri Lanka, aligned with the community
maternal-and-child-health workflow (MOH / PHM). The project has four complementary components.

| # | Component | Question it answers | Folder |
|---|-----------|---------------------|--------|
| 1 | Multimodal Early Detection / Risk Assessment | What is this child's malnutrition risk/status? | [component1_risk_assessment](component1_risk_assessment/) |
| 2 | Personalized Counterfactual Intervention Engine | What feasible changes could improve the child's situation? | [component2_counterfactual_intervention](component2_counterfactual_intervention/) |
| 3 | Adaptive Model Reliability Monitoring and Safe Maintenance | Can the deployed model still be trusted, and how should it be safely maintained? | [component3_reliability_maintenance](component3_reliability_maintenance/) |
| 4 | Spatio-Temporal Burden Forecasting and Resource Demand Visualization | Where and when is burden likely to increase? | [component4_spatiotemporal_forecasting](component4_spatiotemporal_forecasting/) |

## Repository layout

```
├── component1_risk_assessment/
├── component2_counterfactual_intervention/
├── component3_reliability_maintenance/
├── component4_spatiotemporal_forecasting/
├── data/      # local only, not committed (see data/README.md)
└── docs/      # shared project context and documentation
```

Each component is self-contained: its own code, tests, dependencies and README.

## How the components connect

- **C1 → C2:** C2 uses C1's predictions to generate intervention recommendations.
- **C1 → C3:** C3 monitors and maintains the model C1 produces. The contract is defined in
  [component3/interfaces.py](component3_reliability_maintenance/component3/interfaces.py).
- **C4** forecasts area-level burden from the same data sources.

## Working in this repo

- Work inside your own component folder; do not edit another component without agreeing first.
- Create a branch per piece of work (`c1/...`, `c2/...`, `c3/...`, `c4/...`) and merge into `main` by pull request.
- **Never commit child-level data.** Data files and model artifacts are git-ignored.

Project background: [docs/project_context.md](docs/project_context.md).
