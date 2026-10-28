# Component 4 — Spatiotemporal Childhood Malnutrition Forecasting and Decision Support

> **Research Project:** Explainable AI Framework for Early Detection and Personalized Childhood Malnutrition Intervention  
> **Group ID:** J26-IT-399  
> **Individual Component:** Spatiotemporal Childhood Malnutrition Forecasting and Decision Support  
> **Student:** I. G. I. N. Imbulgoda  
> **Student ID:** IT23375178  
> **Specialization:** Information Technology — SLIIT

---

## 1. Component Overview

This component develops an end-to-end district-level childhood malnutrition forecasting and decision-support workflow for Sri Lanka.

The implemented system combines:

- multi-horizon forecasting for **H1, H3 and H6**;
- baseline, statistical, machine-learning and deep-learning model comparison;
- strict leakage-aware temporal validation;
- final **Random Forest Regressor** point forecasts;
- **NGBoost** uncertainty estimation and 95% prediction intervals;
- **SHAP** feature-level and domain-level explainability;
- **DMBI** district prioritization using CRITIC and TOPSIS;
- district GIS priority mapping;
- Triposha resource-planning estimates;
- automated early-warning generation;
- stable dashboard export files;
- a **FastAPI** backend;
- a **React + Vite** frontend dashboard;
- authentication and SMTP-based warning email support.

The component is intended as a **decision-support system**. It does not replace clinical diagnosis, individual patient assessment, treatment guidelines, or professional medical judgement.

---

## 2. Main Research Problem

Health officers need an early way to identify districts that may experience a higher childhood malnutrition burden in the future. A purely reactive approach provides limited time for district prioritization, resource planning and early intervention.

This component addresses that problem by forecasting district-level malnutrition burden in advance and integrating prediction, uncertainty, explanation, prioritization, GIS information and planning outputs in one workflow.

---

## 3. Forecast Horizons

The research uses three forecast horizons:

| Horizon | Meaning |
|---|---|
| **H1** | 1 month ahead |
| **H3** | 3 months ahead |
| **H6** | 6 months ahead |

The research scripts define the horizons as:

```python
HORIZONS = [1, 3, 6]
```

During future dashboard use, the user selects a **forecast-origin year, month and district**. The system then returns H1, H3 and H6 for that same origin.

---

## 4. High-Level Architecture

```text
Historical District-Level Data
        |
        v
Research / ML Pipeline
        |
        |-- Random Forest point forecasts
        |-- NGBoost uncertainty
        |-- SHAP explanations
        |-- DMBI prioritization
        |-- Triposha planning
        |-- Early warnings
        |-- GIS outputs
        v
outputs/dashboard/
CSV + JSON + GeoJSON files
        |
        v
FastAPI Backend
REST API Endpoints
        |
        v
React + Vite Frontend
Dashboard / Forecast / XAI / GIS / Resources / Warnings
```

The main research outputs are file-based. The backend reads the generated CSV, JSON and GeoJSON files and serves them through REST APIs.

---

# 5. Submission Checklist

## 5.1 Research and Data Pipeline

- [x] Data understanding implemented
- [x] Forecast target validated
- [x] Data-quality analysis implemented
- [x] Safe preprocessing implemented
- [x] Exploratory data analysis implemented
- [x] Spatial and temporal analysis implemented
- [x] Leakage-aware multi-horizon feature engineering implemented
- [x] Chronological train/validation/test split implemented
- [x] Train-only preprocessing and feature analysis implemented
- [x] No random train/test split used for the forecasting evaluation workflow
- [x] H1, H3 and H6 handled explicitly

## 5.2 Model Development and Comparison

- [x] Baseline forecasting models evaluated
- [x] SARIMA evaluated
- [x] XGBoost evaluated
- [x] LSTM evaluated
- [x] NGBoost evaluated
- [x] Random Forest Regressor evaluated
- [x] LightGBM evaluated
- [x] Temporal Fusion Transformer evaluated separately
- [x] Strict rolling-origin validation implemented
- [x] Train-only temporal hyperparameter tuning implemented
- [x] Tuned models revalidated
- [x] Final forecasting strategy frozen before opening the final test period
- [x] Final point-forecast model selected using predefined validation criteria

## 5.3 Model Evaluation

- [x] MAE calculated
- [x] RMSE calculated
- [x] WAPE calculated
- [x] sMAPE calculated
- [x] R² calculated
- [x] Model-comparison reports generated
- [x] Validation graphs generated
- [x] H1/H3/H6 evaluated separately
- [x] 2025 final lockbox evaluation implemented

> **Important:** This is a regression problem. Therefore, classification “accuracy” is not used as the primary evaluation measure. Model performance is assessed using regression metrics such as MAE, RMSE, WAPE, sMAPE and R².

## 5.4 Final Forecasting Strategy

- [x] Final point-forecast family: **Tuned Random Forest**
- [x] Separate H1/H3/H6 Random Forest configurations supported
- [x] Final future forecasting implemented for 2026–2030
- [x] Future forecasting avoids using unavailable future target values
- [x] H1 recursive target-state handling implemented for future forecasting
- [x] Future non-target predictors handled using a transparent seasonal-naive projection assumption

## 5.5 Uncertainty and Explainability

- [x] NGBoost retained as the separate uncertainty model
- [x] 95% prediction interval generated
- [x] Uncertainty level / confidence label supported
- [x] Tree SHAP used to explain Random Forest forecasts
- [x] SHAP additivity audit implemented
- [x] Local top drivers generated
- [x] Global feature importance generated
- [x] District-level SHAP summaries generated
- [x] Domain-level SHAP explanation generated
- [x] SHAP is interpreted as model behaviour, not clinical causation

## 5.6 District Prioritization and GIS

- [x] DMBI criteria preparation implemented
- [x] C1: Forecasted Malnutrition Cases
- [x] C2: Forecasted Cases per 1,000 Under-5 Population
- [x] C3: Forecasted Year-on-Year Burden Growth (%)
- [x] Objective CRITIC weighting implemented
- [x] CRITIC weights developed using 2024 development data
- [x] 2025 retrospective TOPSIS validation implemented
- [x] Future CRITIC-TOPSIS DMBI prioritization implemented
- [x] DMBI score generated as TOPSIS closeness × 100
- [x] Relative priority categories supported
- [x] GIS-ready future district-priority outputs generated
- [x] Sri Lanka district-boundary integration supported

## 5.7 Resource Planning and Early Warning

- [x] Triposha conversion-rule development implemented
- [x] Triposha rule development uses historical development data
- [x] Validation and retrospective checks implemented
- [x] Future Triposha packet planning demand generated
- [x] Resource estimates explicitly treated as planning estimates, not clinical dosage recommendations
- [x] Automatic early-warning engine implemented
- [x] HIGH / CRITICAL priority can trigger a warning
- [x] MEDIUM retained as watch status
- [x] LOW retained as no-warning status
- [x] One combined district notification can summarize H1/H3/H6 status

## 5.8 Dashboard Export

- [x] Final dashboard export step implemented
- [x] Forecast records exported
- [x] Forecast lookup exported
- [x] SHAP explanations exported
- [x] Resource-planning outputs exported
- [x] GIS priority data exported
- [x] Warnings exported
- [x] Warning summary exported
- [x] Annual trends exported
- [x] Dashboard dataset exported
- [x] District boundaries copied when available
- [x] Dashboard manifest generated

## 5.9 Backend

- [x] FastAPI backend implemented
- [x] REST API architecture implemented
- [x] Swagger/OpenAPI documentation available through FastAPI
- [x] CORS configured for local frontend development
- [x] Forecast endpoints implemented
- [x] Dashboard endpoints implemented
- [x] Explainability endpoints implemented
- [x] Resource-planning endpoints implemented
- [x] GIS endpoints implemented
- [x] Trend endpoints implemented
- [x] District-detail endpoints implemented
- [x] Early-warning endpoints implemented
- [x] Authentication implemented
- [x] JWT access-token handling implemented
- [x] SMTP warning-email functionality implemented
- [x] PDF warning-report service included

## 5.10 Frontend

- [x] React frontend implemented
- [x] Vite build system used
- [x] Tailwind CSS included
- [x] React Router navigation implemented
- [x] Dashboard page implemented
- [x] Forecast page implemented
- [x] Explainable AI page implemented
- [x] Resource Planning page implemented
- [x] GIS Priority Map page implemented
- [x] Trend Analysis page implemented
- [x] District Details page implemented
- [x] Early Warning / Notifications page implemented
- [x] Authentication-aware protected routes implemented
- [x] API service layer implemented
- [x] CSV / Excel / PDF / Print export components included

---

# 6. Research Pipeline — Script-by-Script Guide

The `src/` folder contains the research workflow in numbered order.

| Step | Script | Purpose |
|---|---|---|
| 01 | `01_data_understanding.py` | Understand source-corrected dataset structure and basic properties |
| 02 | `02_target_validation.py` | Validate `Malnutrition_Cases` as the forecasting target |
| 03 | `03_data_quality_analysis.py` | Audit missing values, consistency and data quality |
| 04 | `04_preprocessing.py` | Perform safe preprocessing |
| 05 | `05_eda.py` | Exploratory data analysis |
| 06 | `06_spatial_temporal_analysis.py` | Analyze district and temporal patterns |
| 07 | `07_leakage_aware_feature_engineering.py` | Create leakage-aware lags, rolling and multi-horizon features |
| 08 | `08_time_based_split.py` | Chronological train/validation/test split |
| 09 | `09_train_only_preprocessing_feature_analysis.py` | Learn preprocessing and feature statistics using training data only |
| 10 | `10_baseline_models.py` | Evaluate baseline models including Seasonal Naive |
| 11 | `11_sarima_model_analysis.py` | District-specific SARIMA analysis |
| 12 | `12_xgboost_model_analysis.py` | XGBoost regression candidate analysis |
| 13 | `13_lstm_model_analysis.py` | LSTM candidate analysis |
| 14 | `14_ngboost_model_analysis.py` | NGBoost candidate and probabilistic analysis |
| 14A | `14a_random_forest_model_analysis.py` | Random Forest candidate analysis |
| 14B | `14b_lightgbm_model_analysis.py` | LightGBM candidate analysis |
| 15 | `15_strict_rolling_origin_validation.py` | Strict rolling-origin revalidation of candidate models |
| 15B | `15b_tft_strict_rolling_origin_validation.py` | Strict rolling-origin validation for TFT |
| 16 | `16_temporal_hyperparameter_tuning.py` | Train-only temporal tuning for RF/XGBoost/LightGBM/NGBoost |
| 16B | `16b_tft_temporal_hyperparameter_tuning.py` | Train-only temporal tuning for TFT |
| 17 | `17_tuned_model_revalidation.py` | Revalidate tuned candidate models |
| 18 | `18_tft_data_preparation.py` | Prepare TFT data |
| 19 | `19_tft_model_analysis.py` | TFT model analysis |
| 20 | `20_final_strategy_freeze.py` | Freeze final point-forecast and uncertainty strategy before final testing |
| 21 | `21_final_2025_lockbox_test.py` | Final 2025 lockbox test |
| 21B | `21b_ngboost_2025_uncertainty_lockbox_audit.py` | Audit NGBoost uncertainty on 2025 lockbox data |
| 22 | `22_final_random_forest_shap_analysis_FIXED.py` | Final Random Forest SHAP analysis |
| 22B | `22b_2025_shap_domain_explanation.py` | Convert 2025 feature SHAP into domain-level explanations |
| 23 | `23_district_risk_prioritization.py` | Historical/final district risk and prioritization output |
| 24 | `24_district_risk_map.py` | District risk map preparation |
| 25 | `25_resource_demand_estimation.py` | Initial Triposha planning-demand estimation |
| 26 | `26_early_warning_alert_generation.py` | Initial early-warning alert generation |
| 27 | `27_future_forecast_2026_2030.py` | Generate final RF future forecasts for 2026–2030 |
| 27B | `27b_future_ngboost_uncertainty_2026_2030.py` | Add future NGBoost uncertainty and 95% intervals |
| 28 | `28_future_random_forest_shap_analysis.py` | Generate future SHAP explanations |
| 28B | `28b_future_shap_domain_explanation.py` | Generate future domain-level SHAP explanations |
| 29C | `29c_dmbi_criteria_preparation.py` | Prepare DMBI criteria |
| 29D | `29d_dmbi_critic_weight_development.py` | Develop and freeze objective CRITIC weights |
| 29E | `29e_dmbi_topsis_2025_validation.py` | Retrospective DMBI/TOPSIS validation on 2025 |
| 29F | `29f_dmbi_future_critic_topsis_prioritization.py` | Generate future DMBI priority scores |
| 30 | `30_future_district_risk_prioritization.py` | Combine future DMBI and uncertainty for final district priority output |
| 31 | `31_future_gis_priority_mapping.py` | Generate GIS-ready future priority mapping data |
| 32A | `32a_triposha_conversion_rule_development.py` | Develop and validate Triposha conversion rule |
| 32B | `32b_future_triposha_packet_planning_demand.py` | Apply frozen rule to future forecasts |
| 33 | `33_final_automatic_early_warning_engine.py` | Generate automatic H1/H3/H6 warnings |
| 34 | `34_dashboard_data_export.py` | Export stable backend/frontend-ready dashboard files |

---

# 7. Temporal Data Design

The research uses chronological splitting rather than random splitting.

The Step 08 design is:

```text
TRAIN      : forecast target dates from 2015 to 2023
VALIDATION : forecast target dates in 2024
TEST       : forecast target dates in 2025
```

Important protections implemented across later validation/tuning steps include:

- future labels are not supplied to earlier forecast origins;
- preprocessing statistics are derived only from data available to the relevant training period;
- 2025 is kept out of model selection until the frozen final strategy is ready;
- strict rolling-origin / walk-forward validation is used to mimic real forecasting conditions.

---

# 8. Models Evaluated

The research compares multiple modelling families to justify the final model selection.

### Baseline Models

- Global Training Mean
- District Historical Training Mean
- Seasonal Naive

### Statistical Model

- SARIMA

### Machine-Learning Models

- XGBoost Regressor
- Random Forest Regressor
- LightGBM Regressor
- NGBoost

### Deep-Learning Models

- LSTM
- Temporal Fusion Transformer (TFT)

This design allows the final model to be selected from a meaningful comparison rather than choosing one algorithm in advance.

---

# 9. Evaluation Metrics

The research uses regression metrics rather than classification accuracy.

| Metric | Simple Meaning | Preferred Direction |
|---|---|---|
| **MAE** | Average absolute prediction error | Lower is better |
| **RMSE** | Error metric that penalizes large errors more strongly | Lower is better |
| **WAPE** | Overall absolute error as a percentage of actual burden | Lower is better |
| **sMAPE** | Symmetric percentage error | Lower is better |
| **R²** | Amount of target variation explained by the model | Higher is generally better |

Example Random Forest candidate metric output:

```text
outputs/reports/14a_random_forest_validation_metrics.csv
```

Example candidate comparison output:

```text
outputs/reports/14a_model_comparison_after_random_forest.csv
```

Example evaluation figure:

```text
outputs/figures/14a_model_mae_comparison.png
```

Example H1/H3/H6 validation trend figures:

```text
outputs/figures/14a_random_forest_h1_validation_trend.png
outputs/figures/14a_random_forest_h3_validation_trend.png
outputs/figures/14a_random_forest_h6_validation_trend.png
```

---

# 10. Final Model Selection

The final strategy is frozen in:

```text
src/20_final_strategy_freeze.py
```

The implementation defines:

```text
Final point-forecast model: Tuned Random Forest
Base model family: Random Forest
```

Separate Step 16-selected Random Forest parameters are retained for H1, H3 and H6.

The final selection is made from validation evidence before the 2025 lockbox is used for final testing. This avoids selecting a model using the final test set.

### Viva-ready justification

> Multiple forecasting approaches were evaluated, including baseline, statistical, machine-learning and deep-learning models. They were compared using regression evaluation metrics under strict temporal validation. Random Forest showed the best overall validation performance under the predefined selection rule, so the tuned Random Forest strategy was frozen as the final point-forecast model.

---

# 11. Final Future Forecasting

Future forecasting is implemented in:

```text
src/27_future_forecast_2026_2030.py
```

Main design:

- uses the frozen Random Forest strategy;
- retrains using genuinely available labels through 2025-12;
- creates future district forecasts for 2026–2030;
- maintains the original H1/H3/H6 meaning;
- uses H1 recursively for future target-state maintenance;
- does not use unknown future actual target values;
- uses a transparent 12-month seasonal-naive assumption for future non-target predictors.

---

# 12. NGBoost Uncertainty Layer

NGBoost is retained as a **separate uncertainty model**, not as the final point-forecast model.

Implemented in:

```text
src/27b_future_ngboost_uncertainty_2026_2030.py
```

It provides:

- predictive mean;
- predictive standard deviation;
- lower 95% prediction bound;
- upper 95% prediction bound;
- uncertainty level;
- confidence label.

### Important interpretation

A 95% prediction interval is **not 95% accuracy**. It represents a probabilistic uncertainty range around the forecast.

---

# 13. Explainable AI — SHAP

Future Random Forest explanation is implemented in:

```text
src/28_future_random_forest_shap_analysis.py
```

The SHAP layer:

- explains the Random Forest point forecast;
- reconstructs the Step 27 model feature state;
- checks that saved RF predictions can be reproduced;
- calculates Tree SHAP values;
- audits SHAP additivity;
- saves local and global explanation outputs;
- identifies top local drivers per forecast.

Interpretation:

```text
Positive SHAP value -> pushes the RF prediction upward
Negative SHAP value -> pushes the RF prediction downward
```

SHAP explains **model behaviour**. It does not establish clinical causation.

Domain-level explanations are created in:

```text
src/28b_future_shap_domain_explanation.py
```

This converts detailed model features into more understandable domain-level explanations for decision-support users.

---

# 14. DMBI — District Malnutrition Burden Index

DMBI is a **relative district planning-priority index**. It is not a diagnosis and is not a probability.

## 14.1 DMBI Criteria

The final criteria are:

1. **C1 — Forecasted Malnutrition Cases**
2. **C2 — Forecasted Cases per 1,000 Under-5 Population**
3. **C3 — Forecasted Year-on-Year Burden Growth (%)**

### C2

```text
C2 = Forecasted Cases / Under-5 Population × 1000
```

### C3

```text
C3 = (Current Forecast - Previous-Year Same-Month Burden)
     / Previous-Year Same-Month Burden × 100
```

## 14.2 CRITIC Weighting

Implemented in:

```text
src/29d_dmbi_critic_weight_development.py
```

CRITIC calculates objective criterion weights using contrast and inter-criterion conflict. The implementation develops and freezes these weights from 2024 development data.

## 14.3 TOPSIS Prioritization

Retrospective 2025 validation:

```text
src/29e_dmbi_topsis_2025_validation.py
```

Future prioritization:

```text
src/29f_dmbi_future_critic_topsis_prioritization.py
```

The final DMBI score is:

```text
DMBI Score = TOPSIS Closeness × 100
```

Priority categories are relative planning-priority tiers within the relevant decision matrix. They should not be interpreted as clinical emergency thresholds.

---

# 15. GIS Priority Mapping

Implemented in:

```text
src/31_future_gis_priority_mapping.py
```

The GIS layer combines future district priority information with Sri Lankan district boundaries.

The design intentionally keeps these meanings separate:

```text
Random Forest -> point forecast
NGBoost       -> probabilistic uncertainty
DMBI          -> relative planning priority
GIS           -> spatial presentation of district priority
```

---

# 16. Triposha Resource Planning

Triposha planning is implemented as an operational planning layer, not as a medical dosage recommendation.

### Rule Development

```text
src/32a_triposha_conversion_rule_development.py
```

The code separates:

```text
Development  : 2015-2023
Validation   : 2024
Retrospective: 2025
```

The selected frozen rule is then used in:

```text
src/32b_future_triposha_packet_planning_demand.py
```

The future resource-planning step does not retrain RF, NGBoost, SHAP or DMBI.

---

# 17. Automatic Early Warning

Implemented in:

```text
src/33_final_automatic_early_warning_engine.py
```

Final warning design:

```text
HIGH / CRITICAL -> warning
MEDIUM          -> watch
LOW             -> no warning
```

H1, H3 and H6 are checked from the same selected forecast origin, and a combined district notification can use the highest severity across the horizons.

---

# 18. Dashboard Export Contract

The final research-to-application bridge is:

```text
src/34_dashboard_data_export.py
```

The step does **not** retrain or modify any model. It packages final research results into stable dashboard files.

Expected dashboard directory:

```text
Forecasting_Research/
└── outputs/
    └── dashboard/
```

Main dashboard files:

```text
metadata.json
forecast_records.csv
forecast_lookup.json
shap_explanations.json
resource_planning.csv
gis_priority.csv
warnings.json
warning_summary.json
annual_trends.json
dataset_dashboard.csv
district_boundaries.geojson
dashboard_manifest.json
34_dashboard_export_audit.csv
```

`district_boundaries.geojson` is exported when the boundary source is available.

---

# 19. Backend Architecture

Backend location:

```text
backend/
```

Main application:

```text
backend/app/main.py
```

Framework:

```text
FastAPI
```

The main FastAPI application includes:

- Component 4 forecast router;
- authentication router;
- email router;
- AI health-assistant router;
- CORS configuration;
- health endpoint.

### Swagger / OpenAPI

When the backend is running, FastAPI provides interactive API documentation at:

```text
http://127.0.0.1:8000/docs
```

If the backend is started on another port such as `8001`, use:

```text
http://127.0.0.1:8001/docs
```

Swagger is used to **inspect and test API endpoints**. The frontend/backend integration itself is performed through REST API requests.

---

# 20. Backend Research-Output Configuration

Research file locations are configured in:

```text
backend/app/config.py
```

Expected research component root:

```text
components/
└── c4_spatiotemporal_forecasting/
    └── Forecasting_Research/
```

The backend expects dashboard outputs under:

```text
components/c4_spatiotemporal_forecasting/Forecasting_Research/outputs/dashboard/
```

Configured files include:

```text
metadata.json
forecast_lookup.json
forecast_records.csv
warnings.json
warning_summary.json
shap_explanations.json
resource_planning.csv
gis_priority.csv
district_boundaries.geojson
annual_trends.json
dataset_dashboard.csv
dashboard_manifest.json
```

---

# 21. Main Backend API Groups

Most Component 4 research routes are nested below:

```text
/forecast
```

Important endpoint groups include:

| API Area | Example Route |
|---|---|
| Component status | `GET /forecast/status` |
| Forecast | `GET /forecast/` |
| Forecast by selected month | `GET /forecast/by-selected-month` |
| District list | `GET /forecast/districts` |
| Forecast origins | `GET /forecast/origins` |
| Dashboard | `GET /forecast/dashboard/...` |
| Explainability | `GET /forecast/explainability/by-selected-month` |
| Resources | `GET /forecast/resources/by-selected-month` |
| GIS Map | `GET /forecast/map/priority/by-selected-month` |
| Boundaries | `GET /forecast/map/boundaries` |
| Trends | `GET /forecast/trends/clinical/by-selected-month` |
| District details | `GET /forecast/districts/details/by-selected-month` |
| Early warnings | `GET /forecast/warnings/...` |
| Authentication | `POST /auth/register`, `POST /auth/login` |
| Current user | `GET /auth/me` |
| Warning email | `POST /email/send-warning-report` |
| AI assistant | `POST /ai/chat` |
| Health check | `GET /health` |

Use Swagger to view the exact query parameters and current response schemas.

---

# 22. Authentication and Email

The backend implements JWT-based authentication.

Relevant files:

```text
backend/app/routers/auth_routes.py
backend/app/services/auth_service.py
backend/app/schemas/auth_schemas.py
```

Current local authentication state is file-based:

```text
backend/data/users.json
```

Warning-email duplicate/state tracking is also file-based:

```text
backend/data/sent_warning_emails.json
```

Therefore, the current application does **not require a traditional relational database for the main research dashboard pipeline**.

SMTP email configuration is read from environment variables in `backend/.env`.

Expected variables include:

```text
JWT_SECRET_KEY
JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
SMTP_FROM_EMAIL
SMTP_FROM_NAME
```

> Do not commit real secrets or passwords to Git.

---

# 23. Frontend Architecture

Frontend location:

```text
frontend/
```

Main technologies:

- React
- Vite
- React Router
- Tailwind CSS
- Recharts
- React Leaflet / Leaflet
- jsPDF
- XLSX
- Papa Parse

Main Component 4 pages:

```text
frontend/src/pages/component4/
├── DashboardPage.jsx
├── ForecastPage.jsx
├── ExplainableAIPage.jsx
├── ResourcePlanningPage.jsx
├── GISPriorityMapPage.jsx
├── TrendAnalysisPage.jsx
├── DistrictDetailsPage.jsx
└── NotificationsPage.jsx
```

Component 4 page routes:

```text
/dashboard
/forecast
/explainable-ai
/resource-planning
/gis-map
/trend-analysis
/district-details
/early-warning
```

Frontend API service layer:

```text
frontend/src/services/component4/
```

Includes services for:

- authentication;
- dashboard;
- forecast;
- explainability;
- resources;
- GIS;
- trends;
- warnings;
- district details;
- AI assistant.

---

# 24. Frontend API Configuration

The frontend API base URL is configured using:

```text
VITE_API_BASE_URL
```

Default code fallback:

```text
http://localhost:8000
```

Example `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If the backend is deliberately running on port `8001`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

Restart Vite after changing `.env`.

---

# 25. Suggested Repository Structure

The integrated repository should follow the structure expected by `backend/app/config.py`:

```text
project-root/
├── components/
│   └── c4_spatiotemporal_forecasting/
│       └── Forecasting_Research/
│           ├── data/
│           │   ├── raw/
│           │   ├── processed/
│           │   ├── splits/
│           │   └── model_ready/
│           ├── src/
│           ├── models/
│           └── outputs/
│               ├── reports/
│               ├── figures/
│               ├── models/
│               ├── gis/
│               └── dashboard/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── config.py
│   │   └── main.py
│   ├── data/
│   ├── generated_reports/
│   ├── requirements.txt
│   └── .env
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── context/
    │   ├── pages/
    │   ├── routes/
    │   ├── services/
    │   └── config/
    ├── package.json
    └── .env
```

---

# 26. How to Run the Research Pipeline

Run commands from the `Forecasting_Research` directory.

Example:

```bash
python src/01_data_understanding.py
python src/02_target_validation.py
python src/03_data_quality_analysis.py
python src/04_preprocessing.py
python src/05_eda.py
python src/06_spatial_temporal_analysis.py
python src/07_leakage_aware_feature_engineering.py
python src/08_time_based_split.py
python src/09_train_only_preprocessing_feature_analysis.py
python src/10_baseline_models.py
python src/11_sarima_model_analysis.py
python src/12_xgboost_model_analysis.py
python src/13_lstm_model_analysis.py
python src/14_ngboost_model_analysis.py
python src/14a_random_forest_model_analysis.py
python src/14b_lightgbm_model_analysis.py
python src/15_strict_rolling_origin_validation.py
python src/15b_tft_strict_rolling_origin_validation.py
python src/16_temporal_hyperparameter_tuning.py
python src/16b_tft_temporal_hyperparameter_tuning.py
python src/17_tuned_model_revalidation.py
python src/18_tft_data_preparation.py
python src/19_tft_model_analysis.py
python src/20_final_strategy_freeze.py
python src/21_final_2025_lockbox_test.py
python src/21b_ngboost_2025_uncertainty_lockbox_audit.py
python src/22_final_random_forest_shap_analysis_FIXED.py
python src/22b_2025_shap_domain_explanation.py
python src/23_district_risk_prioritization.py
python src/24_district_risk_map.py
python src/25_resource_demand_estimation.py
python src/26_early_warning_alert_generation.py
python src/27_future_forecast_2026_2030.py
python src/27b_future_ngboost_uncertainty_2026_2030.py
python src/28_future_random_forest_shap_analysis.py
python src/28b_future_shap_domain_explanation.py
python src/29c_dmbi_criteria_preparation.py
python src/29d_dmbi_critic_weight_development.py
python src/29e_dmbi_topsis_2025_validation.py
python src/29f_dmbi_future_critic_topsis_prioritization.py
python src/30_future_district_risk_prioritization.py
python src/31_future_gis_priority_mapping.py
python src/32a_triposha_conversion_rule_development.py
python src/32b_future_triposha_packet_planning_demand.py
python src/33_final_automatic_early_warning_engine.py
python src/34_dashboard_data_export.py
```

> Some later steps depend on files produced by earlier steps. Run the numbered research workflow in sequence unless you already have the required upstream outputs.

---

# 27. How to Run the Backend

From the `backend` directory:

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Alternative port:

```powershell
uvicorn app.main:app --reload --port 8001
```

Health check:

```text
http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# 28. How to Run the Frontend

From the `frontend` directory:

```bash
npm install
npm run dev
```

Typical local Vite URL:

```text
http://localhost:5173
```

Production build:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

---

# 29. Backend Dependencies

The supplied backend `requirements.txt` includes the backend runtime packages required by the current API application, including:

- FastAPI
- Uvicorn
- Pydantic
- Pandas
- NumPy
- PyJWT
- python-dotenv
- ReportLab
- Pillow
- email-validator
- Argon2-related password packages

Install them with:

```bash
pip install -r requirements.txt
```

The separate research pipeline additionally uses research/ML libraries imported by its scripts, including packages such as scikit-learn, statsmodels, XGBoost, LightGBM, NGBoost, PyTorch, PyTorch Forecasting, Lightning, SHAP and Matplotlib. These must be available in the research environment when the corresponding scripts are executed.

---

# 30. Key Research Outputs to Show During Evaluation / Viva

### Model Evaluation

```text
outputs/reports/
outputs/figures/
```

Useful evidence includes:

```text
14a_random_forest_validation_metrics.csv
14a_model_comparison_after_random_forest.csv
14a_model_mae_comparison.png
14a_random_forest_h1_validation_trend.png
14a_random_forest_h3_validation_trend.png
14a_random_forest_h6_validation_trend.png
```

For the final model-selection evidence, prioritize the later strict-validation, tuned-revalidation and Step 20 frozen-strategy outputs rather than relying only on the initial Step 14A candidate result.

### Final Future Forecast

```text
27_future_forecast_2026_2030.py
27b_future_ngboost_uncertainty_2026_2030.py
```

### Explainability

```text
28_future_random_forest_shap_analysis.py
28b_future_shap_domain_explanation.py
```

### District Prioritization

```text
29c_dmbi_criteria_preparation.py
29d_dmbi_critic_weight_development.py
29e_dmbi_topsis_2025_validation.py
29f_dmbi_future_critic_topsis_prioritization.py
```

### GIS

```text
31_future_gis_priority_mapping.py
```

### Resource Planning

```text
32a_triposha_conversion_rule_development.py
32b_future_triposha_packet_planning_demand.py
```

### Early Warning

```text
33_final_automatic_early_warning_engine.py
```

### Dashboard Integration

```text
34_dashboard_data_export.py
backend/app/
frontend/src/pages/component4/
```

---

# 31. Important Methodology Statements

These statements accurately describe the implementation and are useful for reports, demonstrations and viva questions.

### Why multiple models?

> Different forecasting approaches were compared so the final model could be justified using empirical validation rather than chosen in advance.

### Why no classification accuracy?

> The target is a continuous number of malnutrition cases, so this is a regression problem. Therefore, regression metrics such as MAE, RMSE, WAPE, sMAPE and R² are used instead of classification accuracy.

### Why Random Forest?

> The tuned Random Forest strategy was selected after temporal validation and model comparison under the predefined selection rule, and it was frozen before final lockbox evaluation.

### What does NGBoost do?

> Random Forest produces the final point forecast. NGBoost provides a separate probabilistic uncertainty layer and 95% prediction interval.

### What does SHAP do?

> SHAP identifies which model inputs pushed an individual Random Forest prediction upward or downward relative to its baseline. It explains model behaviour and does not prove medical causation.

### What is DMBI?

> DMBI is a relative district planning-priority index. It combines forecasted burden, burden per 1,000 under-5 children and year-on-year growth using objective CRITIC weighting and TOPSIS prioritization.

### What is Swagger?

> Swagger is the interactive API documentation and testing interface automatically provided by FastAPI. It is used to test and verify backend endpoints.

### How are frontend and backend connected?

> The React frontend communicates with the FastAPI backend through REST API calls. Swagger is used for testing the APIs, not for creating the frontend-backend connection.

### Is a database required?

> The main research dashboard pipeline is file-based. The backend reads precomputed CSV, JSON and GeoJSON outputs. Current local authentication and sent-email state are stored in JSON files.

---

# 32. Safety and Interpretation Boundaries

The following outputs must be interpreted correctly:

- Forecasts are **decision-support estimates**, not diagnoses.
- A 95% prediction interval is **not 95% accuracy**.
- SHAP contribution values explain the model and do **not** establish causation.
- DMBI is a **relative planning-priority index**, not a clinical probability.
- DMBI priority tiers are not emergency-diagnosis thresholds.
- Triposha estimates are **resource-planning estimates**, not individual medical dosage recommendations.
- Final decisions should be made together with qualified health professionals and relevant official guidance.

---

# 33. Reproducibility and Leakage Protection

The workflow includes several controls intended to improve reproducibility and avoid temporal leakage:

- chronological splitting;
- forecast-origin-aware validation;
- strict rolling-origin revalidation;
- train-derived preprocessing statistics;
- train-only temporal hyperparameter tuning;
- fixed random seeds where supported;
- model strategy freeze before final lockbox evaluation;
- explicit audit outputs for later forecast/explanation stages;
- no future actual targets used for 2026–2030 future inference.

---

# 34. Final End-to-End Flow

```text
1. Historical district-level data
        ↓
2. Data quality + preprocessing
        ↓
3. Leakage-aware feature engineering
        ↓
4. Chronological train / validation / test split
        ↓
5. Baseline + statistical + ML + deep-learning comparison
        ↓
6. Strict rolling-origin validation
        ↓
7. Train-only temporal hyperparameter tuning
        ↓
8. Tuned model revalidation
        ↓
9. Freeze final Tuned Random Forest strategy
        ↓
10. 2025 lockbox test
        ↓
11. Future RF forecasts for 2026–2030
        ↓
12. NGBoost uncertainty / 95% prediction interval
        ↓
13. SHAP feature + domain explanation
        ↓
14. DMBI CRITIC-TOPSIS district prioritization
        ↓
15. GIS priority mapping
        ↓
16. Triposha resource-planning demand
        ↓
17. Automatic early-warning generation
        ↓
18. Dashboard-ready export files
        ↓
19. FastAPI REST backend
        ↓
20. React decision-support dashboard
```

---

# 35. Final Submission Verification Checklist

Before submission, verify the repository contains or can regenerate the following:

- [ ] Required research input data is present in the expected `data/` folders
- [ ] All research scripts in `src/` are committed
- [ ] Important final reports are present or reproducible
- [ ] Important final figures are present or reproducible
- [ ] Final saved model bundles required by downstream scripts are present or reproducible
- [ ] `outputs/dashboard/` has been generated using Step 34
- [ ] `dashboard_manifest.json` exists
- [ ] Backend `requirements.txt` is committed
- [ ] Real `.env` secrets are **not** committed
- [ ] An `.env.example` is added if required by the submission guideline
- [ ] `backend/data/users.json` is reviewed before submission because it may contain local user information
- [ ] `backend/data/sent_warning_emails.json` is reviewed before submission because it may contain local email state
- [ ] Generated warning PDFs are reviewed before committing
- [ ] Frontend `node_modules/` is not committed
- [ ] Frontend `dist/` is included only if the submission explicitly requires a built application
- [ ] Backend starts without errors
- [ ] `/health` returns a successful response
- [ ] Swagger `/docs` loads successfully
- [ ] Frontend starts successfully
- [ ] Frontend can reach the configured FastAPI URL
- [ ] Login / authentication works
- [ ] Forecast H1/H3/H6 loads for a valid selection
- [ ] SHAP explanation loads
- [ ] DMBI priority information loads
- [ ] GIS map loads
- [ ] Resource-planning information loads
- [ ] Early-warning information loads
- [ ] Warning email is tested only with safe test recipient details
- [ ] README commands are tested from a clean environment where possible

---

# 36. Component Completion Summary

The supplied code covers the full Component 4 chain from research modelling to application integration:

```text
Data
→ Forecasting
→ Model Evaluation
→ Final Model Selection
→ Future Forecasting
→ Uncertainty
→ Explainability
→ District Prioritization
→ GIS
→ Resource Planning
→ Early Warning
→ Dashboard Export
→ FastAPI Backend
→ React Frontend
```

The final design keeps the roles of the major methods clearly separated:

```text
Random Forest = final point forecast
NGBoost       = uncertainty
SHAP          = explanation
DMBI          = relative district priority
GIS           = spatial decision-support view
Triposha      = planning-demand estimate
Warnings      = automatic attention signal
FastAPI       = backend API layer
React         = user-facing dashboard
```

---

## License / Academic Use

This repository is prepared for academic research and project-submission purposes. Any external dataset, geographic boundary file, library, framework or third-party asset should retain its original license and attribution requirements.

