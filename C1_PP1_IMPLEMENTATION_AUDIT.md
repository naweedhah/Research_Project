# Component 1 — PP1 Implementation and ML Integration Audit

**Project:** Explainable AI Framework for Early Detection and Personalized Intervention of Childhood Malnutrition in Sri Lanka  
**Component 1:** Multimodal Early Detection of Paediatric Malnutrition Type and Severity  
**Student / product identity:** Kavindi T.A.C., IT22541048, J26-IT-399 (`packages/contracts/product.json`)  
**Product name:** Child Nutrition Intelligence Platform (CNIP)  
**Audit date:** 20 October 2026  
**Scope:** Read-only forensic review of the current checkout. No application code, configuration, schema, artifacts, or data were modified.  
**Runtime this audit:** Inference `GET /health` and `GET /model-info` (8001), API `GET /health` (8000), frontend HTTP 200 (3000) were executed. A live authenticated prediction POST through the UI was **not** re-run. Live child-row counts were **not** queried.

---

## Executive Technical Summary

The website is a working three-process local prototype: Next.js clinician UI on port 3000, FastAPI clinical API on 8000, FastAPI inference service on 8001, PostgreSQL 16 on 5432. At the time of this audit the three HTTP services were up. The inference process reported **`GA-RGCA-v4-Rolling-RSL` loaded**, **`model_loaded: true`**, **`demo: false`**, **`clinical_use: false`**, 12-month horizon, SuperLearner experts LogisticRegression / RandomForest / XGBoost / LightGBM / GA_RGCA_v4, and artifact path `ml/artifacts/ga_rgca_v4_rsl`. All six required v4 files are present on disk.

The production inference path is **not a mock**. `C1_MODEL_VERSION` must be `ga_rgca_v4_rsl` or the inference process refuses to start (`services/inference/app/main.py` lines 25–29). Missing artifacts produce HTTP 503 `MODEL_NOT_AVAILABLE`. Incomplete age/sex/height/weight produces HTTP 422. There is no silent demo-score fallback on that path.

The intended rolling-origin mapping is implemented in `GaRgcaV4Model.snapshot_frame`: the **current visit** is converted to `Baseline_*` features. Historical diagnosis labels (`Hist_2025_*`, MAM/SAM/Underweight/Stunting as predictors) are on a forbidden list and are not placed on the model frame. A clinic visit **can** be converted into the notebook’s Baseline representation for growth (age months, height cm, weight kg, BMI from kg/cm², birth weight kg→g, sex). Socioeconomic, feeding and supplementation categories are collected primarily at **child registration** and then **carried forward**; the follow-up visit form collects a different operational feeding vocabulary that is **not** remapped onto the v4 category names.

WHO current-status assessment is implemented **client-side** from stored anthropometry (`apps/web/src/data/who-growth-standards.ts`) and is visually separated from the 12-month GA-RGCA forecast on the main clinical screens. Explainability is **not SHAP**. The site shows calibrated head probabilities, modality reliability gates, ensemble-variance uncertainty, OOD/latent-distance flags, conformal acute sets, and model-returned triage text.

The login surface is **doctor-only**. PHM and Medical Officer of Health are **not** implemented roles. Other enum roles exist in RBAC tables but cannot authenticate through `POST /auth/login`.

**PP1 demonstration is technically possible** if the three local processes remain up and a seeded doctor account is used. The prototype is a research decision-support system, not a clinically validated product. Repeated rolling-origin prospective validation is explicitly **false** in both metadata and `/model-info`.

---

## Actual Technology Stack and Architecture

### Technology-stack table

| Layer | Actual technology | Evidence |
|---|---|---|
| Frontend | Next.js App Router (`next` ^15.1.3), React 19, TypeScript | `apps/web/package.json` |
| UI / styling | Tailwind CSS 3.4, custom clinical components, lucide-react, framer-motion, recharts, some Three.js (`@react-three/fiber`) on login atmosphere | `apps/web/package.json`; `apps/web/src/screens/Login.tsx` |
| Data fetching | TanStack Query 5, cookie + CSRF `fetch` client | `apps/web/src/services/component4/httpClient.ts` |
| Backend | FastAPI clinical API, SQLAlchemy ORM, Pydantic settings, httpx to inference | `services/api/app/main.py`; `services/api/app/core/config.py`; `services/api/app/services/prediction.py` |
| Auth | JWT access + refresh cookies, CSRF header, Fernet field encryption for names/IDs | `services/api/app/api/auth.py`; `services/api/app/core/security.py` |
| Database | PostgreSQL 16, database name `cnip`, SQLAlchemy models, Alembic migrations (present in repo) | `.env.example`; `services/api/app/models/` |
| Inference | FastAPI + PyTorch (CPU) + joblib/sklearn/XGBoost/LightGBM SuperLearner | `services/inference/app/main.py`; `services/inference/app/ga_rgca_v4.py` |
| Model artifacts | Local directory `ml/artifacts/ga_rgca_v4_rsl/` (gitignored binaries) | `REQUIRED_FILES` in `ga_rgca_v4.py` lines 38–45; disk listing this audit |
| Process manager | PowerShell `START_PROJECT.ps1` / `STOP_PROJECT.ps1`, PID files under `.run/` | `START_PROJECT.ps1` |
| Docker | Legacy only (`legacy/docker/docker-compose.yml`). Current local path is **Docker-free**. | glob of compose files |
| C2/C3/C4 | URLs blank, `INTEGRATION_MODE=mock` | `.env.example` lines 53–60 |
| Redis / SMS / FHIR | Optional / mock / disabled | `.env.example` |

Secrets (JWT, encryption key, database passwords) exist in `.env` / `.env.example`. They are **not** reproduced in this report.

### Real architecture (not the example)

```
Clinician browser
    │  Next.js 15  http://localhost:3000
    │  cookies: access + refresh + csrf
    ▼
Clinical API  FastAPI  http://127.0.0.1:8000
    │  RBAC + RLS session context
    │  persist Child / Visit / Anthropometry / Prediction
    ├──────────────► PostgreSQL 16 :5432  db=cnip
    │
    │  POST {INFERENCE_URL}/predict   (default http://127.0.0.1:8001/predict)
    ▼
Inference API  FastAPI  :8001
    │  GaRgcaV4Adapter.predict
    │  GaRgcaV4Model.snapshot_frame  → Baseline_* (20 features)
    │  neural ensemble (3 members, d_model 96, hidden 144, 4 heads)
    │  tree experts + SuperLearner policy fusion
    │  no mock fallback
    ▼
Artifacts  ml/artifacts/ga_rgca_v4_rsl/
    ga_rgca_v4_states.pt
    multimodal_preprocessor_v4.joblib
    binary_calibrators_v4.joblib
    rolling_tree_experts_v4.joblib
    superlearner_policy_v4.joblib
    metadata_v4.json
    │
    ▼
PredictionResult JSON
    │
    ▼
API persists Prediction + LatentEmbedding + TrajectoryMetric + audit
    │
    ▼
Frontend dashboard / child profile / visit result cards
    WHO z-scores computed in the browser from stored kg/cm (not a DB column)
```

C2 explainability, C3 counterfactuals and C4 drift are **not** on the live path. `shap_available` is hard-coded `false` in `services/api/app/api/integrations.py`.

### Source-file map

| Layer | Entry | Principal files |
|---|---|---|
| Frontend entry | `apps/web/src/app/page.tsx`, `apps/web/src/app/login/page.tsx` | `apps/web/src/screens/Login.tsx` |
| Clinical shell | `apps/web/src/app/(clinical)/layout.tsx` | `apps/web/src/components/layout/app-shell.tsx` |
| Child list | `/children` | `apps/web/src/components/component1/children-worklist.tsx` |
| Child profile | `/children/[childId]` | `apps/web/src/components/component1/child-profile-view.tsx` |
| Registration | modal from children list | `apps/web/src/components/component1/register-child-modal.tsx` |
| New visit | `/children/[childId]/visits/new` | `apps/web/src/screens/component4/NewVisitPage.tsx` |
| Result cards | used on visit result + profile | `apps/web/src/components/component1/assessment-result-cards.tsx` |
| Explainability dialog | profile `?tab=ai` | `apps/web/src/components/component1/explainability-dialog.tsx` |
| WHO engine | client-only | `apps/web/src/data/who-growth-standards.ts`, `apps/web/src/data/who-lms-tables.ts` |
| HTTP client | | `apps/web/src/services/component4/httpClient.ts` |
| API entry | `services/api/app/main.py` | routers: auth, children, visits, dashboard, alerts, care, trajectory, research, admin, integrations, export |
| Score orchestration | | `services/api/app/services/prediction.py` (`build_inference_payload`, `run_inference`, `active_model`) |
| Type interpretation | | `services/api/app/services/malnutrition_type.py` |
| Inference entry | `services/inference/app/main.py` | `GaRgcaV4Adapter`, `POST /predict`, `GET /model-info` |
| v4 runtime | | `services/inference/app/ga_rgca_v4.py` |
| Identity / RBAC | | `services/api/app/models/enums.py`, `services/api/app/core/security.py`, `services/api/app/core/deps.py` |
| Persistence | | `services/api/app/models/paediatric.py`, `services/api/app/models/intelligence.py` |
| Launcher | | `START_PROJECT.ps1` |

---

## Component 1 User Roles and Complete Workflow

### Roles that actually exist

`UserRole` in `services/api/app/models/enums.py` lines 6–12:

- `system_admin`
- `facility_admin`
- `doctor`
- `health_worker`
- `nutritionist`
- `researcher`

**PHM and MOH are not roles.** They appear only as optional geographic fields on the child record (`Child.moh_area`, `Child.phm_area` in `paediatric.py` lines 27–28) and as registration labels.

### Roles that can actually log in

`POST /auth/login` (`services/api/app/api/auth.py` lines 82–84) rejects any user whose role is not `DOCTOR` with HTTP 403: “This application is restricted to clinician accounts”. Refresh (`auth.py` line 123) applies the same restriction.

Seed (`services/api/app/seed.py` lines 764–766) creates **only doctor** users from `packages/contracts/demo_directory.json`.

**Implemented for PP1: doctor only.** Other RBAC permission sets in `PERMISSIONS` (`security.py` lines 75–148) are code, not a usable multi-role product.

### Doctor capabilities (code)

| Action | Screen / API | Backend enforcement | Status |
|---|---|---|---|
| Login | `/login` → `POST /auth/login` | yes | WORKING (runtime login not re-tested this audit; service is up) |
| Dashboard | `/dashboard` → `GET /dashboard` | `child:read` | WORKING / IMPLEMENTED BUT UNVERIFIED at UI click |
| Children list | `/children` | `child:read` | WORKING (connected) |
| Register child | modal → `POST /children` | `child:write` | WORKING |
| View profile + visit history | `/children/[id]` | `child:read` + facility scope | WORKING |
| New assessment | `/children/[id]/visits/new` → `POST /children/{id}/visits` | `visit:write`; prediction auto-runs unless draft | WORKING in code |
| View predictions | profile, worklist, result cards | stored `predictions` | WORKING in code |
| Revisit previous predictions | visit timeline on profile | one active prediction per visit; older runs `is_active=false` | PARTIALLY IMPLEMENTED (history of visits yes; run-level UI limited) |
| Uncertainty / reliability / triage | result card + AI details dialog | from `ga_rgca` JSON | WORKING in code |
| Clinician review | profile `#clinician-review` → `POST /visits/{id}/clinician-review` | `note:write` | IMPLEMENTED |
| Reports | `/children/[id]/report`, `/reports` | `report:export` on some routes | PARTIALLY IMPLEMENTED |
| Alerts | `/alerts` | `alert:read` | IMPLEMENTED (velocity/stagnation rules, not model heads) |
| Analytics | `/analytics` | not in primary nav | PARTIALLY IMPLEMENTED (uses `/dashboard` + child list) |
| Admin / research / models | `/admin/*`, `/research`, `/research/models` | permissions exist; **login blocked for non-doctors**; not in primary nav | DEMO / HIDDEN |

Primary nav (`app-shell.tsx` lines 31–36): Dashboard, Children, Clinic board, Alerts only.

### Complete doctor workflow and status

1. Open `http://localhost:3000` → login form. **WORKING** (page served HTTP 200 this audit).
2. `POST /auth/login` with a doctor account; cookies set. **IMPLEMENTED BUT UNVERIFIED** this audit (no credentialed call).
3. Redirect `/dashboard`. Priority list from persisted children/predictions. **IMPLEMENTED**; live KPI numbers UNVERIFIED this audit.
4. `/children` — register or open a child. **WORKING** in code.
5. Registration collects identity, DOB, sex, birth weight kg, maternal/household v4 categories, feeding/supplementation v4 categories (`register-child-modal.tsx`). **WORKING**.
6. Open child profile — identity, visit table, current WHO vs 12-month prediction HUD. **WORKING** in code.
7. New visit: age/sex from DOB; enter today’s weight kg and height cm; operational feeding; confirm “matches clinic record”; submit. **WORKING** in code.
8. API validates payload (`validate_visit_payload`), writes visit + modality tables, then `run_inference`. **WORKING** in code.
9. Inference maps current visit → Baseline_*, runs v4 SuperLearner, returns heads. **WORKING** at process level (model loaded). Live POST UNVERIFIED this audit.
10. API stores `Prediction` (`is_active` true; previous runs on same visit deactivated), latent embedding, trajectory metric, audit `PREDICTION_GENERATED`. **WORKING** in code.
11. UI shows dual cards: Current WHO assessment | 12-month GA-RGCA prediction. **WORKING** in code (`assessment-result-cards.tsx`).
12. Optional AI details, report, clinician review. **IMPLEMENTED**.

Draft visits (`save_as_draft`) skip inference (`visits.py` lines 248–249).

---

## Machine Learning Model Integration Status

### A. Model availability

| Question | Finding |
|---|---|
| Which model does the website use? | **GA-RGCA-v4-Rolling-RSL only.** Not v3. Not mock. |
| Are trained artifacts physically present? | **Yes**, on this workstation under `ml/artifacts/ga_rgca_v4_rsl/`. Binaries are gitignored (`.gitignore` lines 30–57), so a fresh clone without copying artifacts **cannot** load the model. |
| Files required and present | `ga_rgca_v4_states.pt`, `multimodal_preprocessor_v4.joblib`, `binary_calibrators_v4.joblib`, `rolling_tree_experts_v4.joblib`, `superlearner_policy_v4.joblib`, `metadata_v4.json` (`ga_rgca_v4.py` lines 38–45). All six were listed on disk this audit. |
| Are neural weights, preprocessor, calibrators, tree experts and SuperLearner policy loaded? | **Yes**, `GaRgcaV4Model` constructor (`ga_rgca_v4.py` ~713–809) loads all six and fails if policy/expert keys are missing. |
| Does inference reconstruct the trained v4 architecture? | **Intended yes.** Runtime class `GrowthAnchoredRGCAV4` (`ga_rgca_v4.py` line 454): growth-anchor history view, context-conditioned reliability gates, task-specific multi-head attention (`V4_D_MODEL=96`, `V4_HIDDEN=144`, `V4_HEADS=4`, 3 ensemble members). File header states notebook `Chanodya_Component1_FINAL_GA_RGCA_v4_Rolling_SuperLearner` with FAST_MODE off. Bit-exact reconstruction versus the Colab notebook was **not** diffed in this audit. |
| Serialization compatibility | joblib + PyTorch `states.pt`. Service is **loaded**, which is strong evidence the formats match this environment. |
| What does the running service report? | **Verified this audit** `GET http://127.0.0.1:8001/model-info`: `active_model=GA-RGCA-v4-Rolling-RSL`, `model_loaded=true`, `ga_rgca_loaded=true`, `ga_rgca_error=null`, `rolling_origin=true`, `prediction_horizon_months=12`, `superlearner=true`, `experts=[LogisticRegression, RandomForest, XGBoost, LightGBM, GA_RGCA_v4]`, `neural_ensemble_members=3`, `clinical_use=false`, `demo=false`, `repeated_origin_prospective_validation=false`. |
| Missing / incompatible artifact | Load returns `(None, error)`; `POST /predict` raises 503 `MODEL_NOT_AVAILABLE` (`main.py` lines 81–88). Startup of launcher also exits if files missing (`START_PROJECT.ps1` lines 62–67). |
| Silent mock fallback? | **No** on the v4 adapter. `allow_demo` exists on `PredictRequest` (`main.py` line 47) and is unused. API `run_inference` maps transport errors to 503 “No demo score was substituted.” (`prediction.py` lines 280–286). Wrong `model_version` in the response raises 503 (`prediction.py` lines 315–316). |
| Does the model load successfully? | **Yes — verified at runtime this audit.** |

`active_model()` in the API requires a non-demo catalogue row `GA-RGCA` / `GA-RGCA-v4-Rolling-RSL` / `ACTIVE` (`prediction.py` lines 53–64). If that row is missing, scoring 503s even if inference is loaded.

### B. Configuration (non-secret)

| Key | Observed non-secret value / behaviour |
|---|---|
| `C1_MODEL_VERSION` | Must be `ga_rgca_v4_rsl`. Any other value prevents inference startup. |
| `GA_RGCA_V4_DIR` | Blank → `<repo>/ml/artifacts/ga_rgca_v4_rsl` (`ga_rgca_v4.py` `artifact_dir()`, lines 161–181). |
| `INFERENCE_URL` | `http://127.0.0.1:8001` |
| `API_URL` / `NEXT_PUBLIC_API_URL` | `http://localhost:8000` (frontend cookies require this host match). |
| `FRONTEND_URL` | `http://localhost:3000` |
| `EMBEDDING_DIM` | 96 |
| `SEED_ON_START` | `false` |
| `FHIR_ENABLED` | `false` |
| `INTEGRATION_MODE` | `mock` |
| `C2_EXPLAINABILITY_URL` / `C3_*` / `C4_*` | blank |
| `NOTIFICATION_PROVIDER` | `mock` |
| Demo/mock model flag | Inference `demo: false`. API scoring refuses `is_demo` catalogue rows. |

Passwords, JWT secrets and encryption keys: **omitted**.

### C. True end-to-end inference trace

1. **Frontend handler.** `NewVisitPage` submit (`apps/web/src/screens/component4/NewVisitPage.tsx` ~564–586) `POST /children/${childId}/visits` with anthropometry, socioeconomic, dietary, MCH, `ga_rgca_context`.
2. **API route.** `POST /children/{child_id}/visits` → `create_visit` (`services/api/app/api/visits.py` lines 137–264). Permission `visit:write`.
3. **Persist visit.** `Visit` + `AnthropometricRecord` + `SocioeconomicRecord` + `DietaryRecord` + `MaternalChildHealthRecord`. Context stored in `visit.data_quality.ga_rgca_context` (`visits.py` 35–48, 189).
4. **Controller calls inference.** `run_inference` (`prediction.py` line 262) unless `save_as_draft`.
5. **Payload.** `build_inference_payload` (167–184) = `current_visit_payload` (67–87) plus `historical_baseline` (ignored for growth by snapshot). Prior GA-RGCA outputs are **not** sent (`prediction.py` 169–170).
6. **HTTP.** `httpx` `POST {inference_url}/predict` (`prediction.py` 268–269).
7. **Inference route.** `predict` → `ADAPTER.predict` (`services/inference/app/main.py` 206–208, 80–144).
8. **Model load.** Module import: `V4_MODEL, V4_LOAD_ERROR = load_ga_rgca_v4()` (`main.py` 72); `load_ga_rgca_v4` at `ga_rgca_v4.py` 947–955.
9. **Preprocess.** `GaRgcaV4Model.snapshot_frame` (828–914) then `prep.transform` via `predict_v4_deployment_bundle`.
10. **Predict.** `predict_v4_deployment_bundle` (620–695): neural `_predict_neural_core_v4`, tree experts, SuperLearner `stack_weights` fusion, `_derive_primary_type_v4`, uncertainty from neural variance vs `uncertainty_binary_variance_q95`, OOD from latent Mahalanobis vs `latent_q99`, APS conformal set, triage string, modality reliability from `reliability_gates`.
11. **Calibration.** Binary calibrators `binary_calibrators_v4.joblib` via `apply_binary_calibrators` (351–358); acute/severity temperatures from the bundle.
12. **Response schema.** `GaRgcaV4Adapter.predict` packs `PredictionResult` (`main.py` 124–144): `status` = predicted type, `severity`, raw/calibrated JSON including full `ga_rgca` block, `risk_score` = max of four condition probabilities, `confidence` string `"elevated"` if `uncertainty_flag` else `"low"`, `mode="PYTORCH"`, `clinical_use=False`.
13. **API interpretation.** `apply_new_prediction_interpretation` (`malnutrition_type.py` 133–158) copies predicted type into `status` before insert.
14. **Persistence.** `Prediction(...)` (`prediction.py` 293–310); deactivate prior runs for that visit; `LatentEmbedding`; `visit.status = PREDICTED`; `_update_trajectory`; audit.
15. **Frontend renderer.** `NewVisitPage` result modal uses `CurrentConditionCard` + `PredictionCard` (`NewVisitPage.tsx` 685–697; `assessment-result-cards.tsx`). Profile HUD and worklist read the same stored block.

**Conclusion:** The website path calls the **actual GA-RGCA v4 Rolling SuperLearner**, not a simpler substitute, provided artifacts remain loaded and the API catalogue row is active. Live button-click scoring was **not** repeated in this audit; load evidence is the running `/model-info`.

Dead / unused relative to v4: `_prior_visit_features` (`prediction.py` 213–259) is not called by `build_inference_payload`. `ml/models/multimodal.py` is a training-tree module, not the inference runtime.

---

## Model Input Schema Compatibility

### Field-by-field comparison

| Notebook feature | Website field | Backend field | Type / unit | Transformation | Availability | Issue |
|---|---|---|---|---|---|---|
| Baseline_Age_months | Age (months), read-only from DOB | `anthropometric_records.age_months` | float months | DOB + visit date | Current visit | WORKING |
| Baseline_Height_cm | Height / length (cm) | `height_cm` | cm | none | Current visit | WORKING |
| Baseline_Weight_kg | Weight (kg) | `weight_kg` | kg | none | Current visit | WORKING |
| Baseline_BMI | not entered | computed in `snapshot_frame` | kg/m² | `weight / (height/100)²` (`ga_rgca_v4.py` 849) | derived | WORKING |
| Birth_Weight_g | Birth weight (kg) at registration | `birth_weight_kg` | kg stored | `* 1000` to grams (`ga_rgca_v4.py` 868) | registration / carried on visit anthro | WORKING if recorded |
| Sex | Sex | `sex` enum `male`/`female` | category | alias map to `Male`/`Female` (`CATEGORY_ALIASES`) | registration | `intersex`/`unknown` would fail as missing sex (422) |
| Baseline_Age_Band | none | derived | `0-5` … `48-60` | `make_age_band` (`ga_rgca_v4.py` 193–199) | derived | WORKING |
| Baseline_Maternal_Age_years | Maternal age (years) | `ga_rgca_context.maternal_age_years` | years | `_finite` | registration, carried | Not on follow-up form UI |
| Family_Size | Family size | `socioeconomic.household_size` | count | `_finite` | registration / socio | WORKING |
| Maternal_Education | Maternal education | `ga_rgca_context.maternal_education` or socio | category | vocab + alias | registration | Follow-up form uses a **different** `maternal_education` socio field; research category is `research_maternal_education` with **no visit UI** |
| Household_Income_Range | Household income range | `ga_rgca_context.household_income_range` | category | vocab | registration | No visit UI; carried |
| Father_Occupation | Father's occupation | `ga_rgca_context.father_occupation` | category | vocab | registration | No visit UI; carried |
| Mother_Occupation | Mother's occupation | `ga_rgca_context.mother_occupation` or `maternal_employment` | category | vocab | registration | Dual naming |
| Exclusive_Breastfeeding | Registration: Yes/No. Visit: Exclusive/Stopped/Never | `ga_rgca_context.exclusive_breastfeeding` vs `dietary.breastfeeding_status` | category | only context token used | **Mismatch** | Visit control does **not** write the v4 field |
| Breastfeeding_Duration | Registration categories | `ga_rgca_context.breastfeeding_duration` | category | alias | registration | No visit UI |
| Complementary_Feeding_Timing | Registration timing vs visit Yes/No | context vs `dietary.complementary_feeding` bool | category vs bool | only context used | **Mismatch** | |
| Meal_Frequency_per_Day | Registration categorical; visit 0 / 1–2 / 3–4 / 5+ numeric | context `meal_frequency` vs `dietary.meal_frequency` | category vs number | only context category used | **Mismatch** | Numeric visit meals are not mapped to `2 meals/day` etc. |
| Dietary_Diversity | Registration varieties | `ga_rgca_context.dietary_diversity` | category | alias | registration | Visit does not collect it |
| Triposha_Supplementation | Registration No / irregular / regular | `ga_rgca_context.triposha_supplementation` | category | alias | registration | Not on visit form |
| Vitamin_Supplementation | Registration Yes/No; visit vitamin A yes/no | context vs `maternal_child_health.vitamin_a` | category vs bool | only context used | **Mismatch** | |

### Specific investigations

- **Months vs years:** Child age is months. Maternal age is years. Correct.
- **kg vs g:** Birth weight stored kg, converted to grams at snapshot. Visit weight remains kg. Correct if clinicians enter kg (registration hint says “Not grams”).
- **cm vs m:** Height is centimetres throughout. BMI uses `/100`. Correct.
- **BMI:** Computed at inference, not a user field. Correct.
- **Categorical encoding:** Values must sit in the saved preprocessor vocab or they become missing (`category_token`, `ga_rgca_v4.py` 810–826). Unmapped non-empty values are listed in `unmapped_categories` and the feature is treated as not recorded.
- **Sex:** Frontend registration offers only female/male. Aliases `m`/`f` exist. Intersex in the API enum is incompatible with the trained Sex vocab.
- **Missing values:** Required for scoring: age, sex, height>0, weight>0 (`snapshot_frame` 838–847). Other Baseline_* columns may be null; limitations such as `Family_Size_not_recorded` are appended. Preprocessor uses training medians / missing indicators (training-time behaviour).
- **Invalid measurements:** API `validate_visit_payload` can 422 before inference. ROLLING_VALID_RANGES (age 0–60, height 40–125, weight 1–40, etc.) exist in `ga_rgca_v4.py` 102–110; snapshot does **not** itself 422 on range — out-of-range values can still be scored and may trigger OOD.
- **Age eligibility:** WHO and rolling ranges are 0–60 months. Children older than 60 months get no WHO classification (`who-growth-standards.ts` 70–71, 150).
- **Historical malnutrition labels:** Form state includes `historical_mam/sam/underweight/stunting` (`NewVisitPage.tsx` 175–178, 577–580). They are stored in `ga_rgca_context` JSON. They are **not** columns of `snapshot_frame`. Forbidden predictors (`FORBIDDEN_ROLLING_INPUTS`, `ga_rgca_v4.py` 51–66) would abort if those **column names** appeared on the frame. Current field names do not leak into the model matrix. **The v4 rolling model does not use previous diagnosis labels as predictors.**
- **Independent frontend vs backend transforms:** Frontend does not compute BMI. Frontend WHO z-scores are display-only and are **not** sent to the model. Dual feeding vocabularies (operational vs research) are the main transform split.
- **Can the current clinic visit become Baseline_*?** **Yes for growth.** The current visit’s age, height, weight, derived BMI, sex, age band, and birth weight (if stored) become the rolling origin. Contextual modalities are **the carried registration snapshot**, not a freshly measured feeding interview in v4 tokens, unless the doctor re-entered them at registration/edit. Metadata already warns: “Contextual predictor timing should be verified” (`ga_rgca_v4.py` `RESEARCH_LIMITATIONS`).

`historical_baseline` **is** attached by the API (`prediction.py` 179–183) but snapshot **ignores its growth** and only appends limitation `historical_baseline_growth_ignored_for_rolling_origin` (`ga_rgca_v4.py` 904–906). Predictions are **not** permanently anchored to visit 1.

---

## Rolling Prediction Implementation

**Classification: Implemented rolling prediction (current visit = origin) + historical visit tracking. Not a dedicated +12-month outcome-validation workspace. Not mock monthly trajectories from the 12-month model.**

| Question | Evidence | Answer |
|---|---|---|
| Latest visit vs first visit? | `snapshot_frame` docstring “Current visit becomes Baseline_*” (`ga_rgca_v4.py` 829). | Each scored visit is a new origin. |
| New forecast on each valid assessment? | `create_visit` always calls `run_inference` unless draft (`visits.py` 248–252). | Yes. |
| `prediction_origin_visit_id`? | No dedicated column. `predictions.visit_id` **is** the origin. | Equivalent yes. |
| Origin date saved? | `visits.visit_date`; also `visit_date` in inference payload. | Yes. |
| Horizon recorded as 12 months? | `metadata_v4.json` `prediction_horizon_months: 12`; result `prediction_horizon_months`; UI copy “12-month GA-RGCA prediction”. Column `Prediction_Horizon_months` set to `V4_HORIZON_MONTHS` (884). | Yes, in JSON + UI, not a SQL column. |
| Previous predictions retained? | Unique `(visit_id, run_number)`; older runs `is_active=false` (`prediction.py` 288–291). Visits are not overwritten. | Yes at DB. Active UI shows the active run. |
| Clinician can view prediction history? | Profile visit table + selectable visits (`child-profile-view.tsx`). | Yes, per visit. |
| Forecast vs observed outcome distinguished? | Dual cards and column headers “Current · WHO status” vs “Future · 12-month prediction” (`children-worklist.tsx` 315–316; `assessment-result-cards.tsx`). | Yes on primary screens. |
| Compare earlier prediction with later measured outcome? | No paired “forecast made at T vs WHO at T+12 months” view. Charts plot visit-level points (`child-profile-charts.tsx`). Trajectory metrics compare **consecutive 12-month forecast scores**, not forecast vs later WHO (`TrajectoryMetric` in `intelligence.py` 119–135; `_update_trajectory` in `prediction.py`). | **Not implemented** as outcome validation. |
| Dashboard labelling | Dashboard copy: “Current WHO state and the 12-month prediction stay separate” (`DashboardPage.tsx` ~300). | Future risk is labelled as prediction, not current diagnosis, on the screens inspected. |
| Trajectory graph source | Recharts lines through stored visit probabilities / weight / height (`child-profile-charts.tsx` 19–23, 41–44). Not interpolated monthly model outputs. | Actual stored outputs + measured anthro. |
| Monthly predictions implied? | Velocity is **pp/month between visits** (`monthlyVelocityDisplay` in `child-profile.ts`), not 12 independent monthly model forecasts. | Risk of misreading exists if a presenter calls it “monthly prediction”. The trained head is 12-month. |

Notebook limitation is surfaced in UI: “One historical 12-month origin validated; repeated rolling-origin prospective validation still required.” `/model-info` `repeated_origin_prospective_validation: false`.

---

## Prediction Outputs, Explainability and Clinical Safety

### Output comparison

| Notebook output | API output | Database field | UI display | Correct meaning | Status |
|---|---|---|---|---|---|
| Predicted primary malnutrition type | `status` + `predicted_malnutrition_type` + `ga_rgca.predicted_malnutrition_type` | `predictions.status_prediction` | Type chip | Derived by `_derive_primary_type_v4` (SAM>MAM>UW/ST strength>Normal) | Shown |
| Detected conditions | `detected_conditions` | inside `calibrated_probabilities.ga_rgca` | bars flagged | Overlapping positives | Shown |
| Underweight / Stunting / MAM / SAM probabilities | same keys on `ga_rgca` | JSON | four risk bars | Calibrated SuperLearner heads | Shown |
| Underweight / stunting positive flags | `underweight_positive`, `stunting_positive` | JSON | used to flag bars | Thresholded binaries (metadata 0.32 / 0.26) | Shown indirectly |
| Acute status Normal/MAM/SAM | `acute_status`, `acute_probabilities` | JSON | in AI details | Mutually exclusive acute head | Shown in details; type chip may also be MAM/SAM |
| Overall severity Normal/Moderate/Severe | `severity` / `severity_prediction` | `predictions.severity_prediction` | Severity chip **hidden when type is Normal** (`displayPredictedSeverity`) | Separate ordinal head | Shown when type ≠ Normal |
| Ensemble uncertainty flag | `uncertainty_flag` | JSON | warning icon | `neural variance > q95` | Shown |
| Ensemble variance | `ensemble_variance` / `binary_variance` | JSON | used to compute “Model confidence %” | Variance of neural ensemble | Shown as transformed % |
| OOD / applicability | `out_of_distribution_flag`, `latent_distance` | JSON | AI details | Training-latent Mahalanobis vs q99; **not** externally validated OOD | Shown with disclaimer |
| Acute conformal set | `acute_conformal_prediction_set` | JSON | AI details | APS set | Shown in details |
| Triage | `triage` | JSON | “Recommendation” | Rule on heads + uncertainty/OOD (`predict_v4_deployment_bundle` 651–660) | Shown |
| Model version | `model_version` | `model_version_id` FK + JSON | model label | GA-RGCA-v4-Rolling-RSL | Shown |
| Horizon | `prediction_horizon_months` | JSON | “12-month” copy | 12 | Shown |
| Modality reliability | `modality_reliability` | JSON | AI details | Gate scores for history/socio/feeding/supplementation | Shown |
| `clinical_use` | false | n/a | disclaimer | Research prototype | Shown |
| Input snapshot | `input_snapshot` | inside JSON | AI details | Feature vector actually scored | Shown |
| Latent vector | `latent_embedding` | `latent_embeddings.embedding` | 2D toy projection `_project` | **Not** PCA; deterministic hash-like 2D (`prediction.py` 351–358) | DEMO-ish visualisation |

`predictions.confidence` stores the adapter string `"elevated"` or `"low"` (`main.py` 130). That is **not** a probability.

### Malnutrition type versus severity

The model has:

- overlapping Underweight/Stunting binaries,
- mutually exclusive Normal/MAM/SAM acute status,
- separate Normal/Moderate/Severe severity.

The website **also** collapses these into one **primary type** chip that can be Normal, Underweight, Stunting, MAM or SAM — the same derivation as the notebook (`_derive_primary_type_v4`, `ga_rgca_v4.py` 590–617). The four bars keep the heads separate. **Risk for viva:** a viewer may think MAM/SAM are mutually exclusive “types” alongside Underweight/Stunting. Presenters should say the chip is a **priority label**, not a single softmax class.

When primary type is Normal, severity is hidden in UI (`displayPredictedSeverity`). Stored severity may still be `Normal` from the severity head.

### WHO assessment versus model prediction

**Yes, current WHO assessment is implemented**, independently of the model:

- File: `apps/web/src/data/who-growth-standards.ts`
- LMS tables: `apps/web/src/data/who-lms-tables.ts`
- Indicators: WAZ, HAZ, WHZ. No BMI-for-age, no MUAC, no oedema (comment lines 1–19).
- Cut-offs: strict `< -2` for underweight/stunting/wasting; SAM `WHZ < -3`; MAM `-3 ≤ WHZ < -2`.
- Age 0–60 months; length tables if age < 24 months, else height tables.
- Tail restriction on weight-based z (`lmsZ(..., restrictTails)`).
- **Not a database column.** Computed whenever the UI has sex, age, kg, cm.

WHO describes **today’s measured undernutrition**. GA-RGCA describes **12-month predicted risk**. Primary screens keep them in separate cards. Do not present a forecast as a current diagnosis.

### Confidence and uncertainty

Two different quantities:

1. **API `confidence` string:** `"elevated"` if `uncertainty_flag` else `"low"` (`main.py` 130). Flag = neural binary variance > training q95 (`0.004274…` in `metadata_v4.json`).
2. **UI “Model confidence” percentage:** `1 - 2 * sqrt(binary_variance)`, clamped 0–1, displayed as percent (`assessment-result-cards.tsx` 240–246, 295–304). Comment in that file states it is a **display-only ensemble-agreement transform**, not a calibrated class probability.

**It is not the predicted-type probability.** Predicted-type probability is a separate chip number (`predictedTypeChipProbability`): for a condition, that head’s probability; for Normal, the UI often hides it.

Uncertain and OOD cases: triage becomes “Clinician review / closer monitoring” (`ga_rgca_v4.py` 657–658). Warning icon shown. Disclaimers state the latent-distance flag is not externally validated OOD detection.

### Explainability — what is real

| Method | Implemented in website inference path? |
|---|---|
| SHAP | **No.** `shap_available: false`. Docs and C2 contract state C1 never fabricates SHAP. |
| Permutation importance | **No** at runtime. |
| Feature-attribution charts | **No.** Explainability dialog says stored class outputs “are not feature attributions.” |
| Modality reliability | **Yes** — model `reliability_gates`. |
| Attention visualization | Weights exist inside the net; **no attention heatmap UI**. |
| Calibrated head probabilities | **Yes.** |
| Input snapshot / missing features | **Yes.** |
| Hardcoded explanation prose | Disclaimers and research limitations are **fixed strings** (`RESEARCH_LIMITATIONS`). Triage strings are **fixed rules** on model outputs, not an LLM. |

### Clinical recommendations

Generated in `predict_v4_deployment_bundle` (651–660) from acute index, binary positives, uncertainty and OOD. Not hardcoded in the frontend except as display of `ga.triage`.

Product disclaimer (`packages/contracts/product.json`): “AI-assisted decision support. Clinical review required.” Login and result footers: “Research decision-support prototype. Clinician confirmation required.” `clinical_use` is always false.

---

## Database and Prediction History

### Tables that actually exist (Component 1 relevant)

From SQLAlchemy models:

```
organizations 1──* facilities 1──* users
                     │
                     └──* children (soft-delete, encrypted name, registration_intake JSON)
                            │
                            ├── 0..1 caregivers (encrypted phone)
                            └──* visits
                                  ├── 0..1 anthropometric_records
                                  ├── 0..1 socioeconomic_records
                                  ├── 0..1 dietary_records
                                  ├── 0..1 maternal_child_health_records
                                  └──* predictions ── model_versions
                                        └── latent_embeddings
                            └──* trajectory_metrics (from_visit → to_visit)
                            └──* alerts
                            └──* follow_up_schedules
audit / login_attempts / refresh_tokens / notifications / integration_events / experiment_runs
```

There is **no** separate `future_risk_forecasts` table. The 12-month forecast **is** `predictions`. There is **no** `prediction_explanations` table; explanations live in `calibrated_probabilities` JSON (`ga_rgca` block including `input_snapshot`, reliability, conformal set).

### Capabilities

| Capability | Supported? |
|---|---|
| Multiple visits per child | Yes (`uq_visit_child_number`) |
| Historical growth records | Yes (`anthropometric_records` per visit) |
| Multiple forecasts per child | Yes, one active prediction per visit; multiple `run_number`s |
| Audit trail | `write_audit` on visit create, prediction, login |
| Model-version traceability | `predictions.model_version_id`, JSON `model_version` |
| Input snapshot preservation | JSON `input_snapshot` plus `input_hash` SHA-256 of payload |
| Dashboard from DB | `GET /dashboard` aggregates persisted children/visits/predictions/alerts — not a static JSON fixture. `Dashboard.synthetic` exists as a flag in the frontend type; clinic list filters `child_is_synthetic`. |
| WHO in DB | No |

Facility-scoped access: `assert_child_access`. RLS is documented for children/visits/alerts/follow-ups in prior operational notes; this audit did not re-verify `FORCE ROW LEVEL SECURITY` on the live database (UNVERIFIED).

---

## Frontend Pages and Feature Inventory

Primary navigation: Dashboard, Children, Clinic board, Alerts.

| Page | Route | Purpose | Implemented | Data source | Connected? | PP1 demo? | Category |
|---|---|---|---|---|---|---|---|
| Login | `/login` | Doctor sign-in | Email/password, CSRF, disclaimer | `POST /auth/login` | Yes | Yes | Fully functional (auth not re-clicked this audit) |
| Dashboard | `/dashboard` | Priority patients, KPIs | WHO vs 12-month copy, lists | `GET /dashboard` | Yes | Yes | Fully functional |
| Children worklist | `/children` | Find/register children | Dual WHO / future columns, search | `GET /children` | Yes | **Yes — best overview** | Fully functional |
| Register child | modal on `/children` | Create record + v4 context | Full v4 category form | `POST /children` | Yes | Yes | Fully functional |
| Child profile | `/children/[childId]` | Record, visits, HUD, review | Visit history, WHO vs AI, charts | `GET /children/{id}` | Yes | **Yes — best clinical screen** | Fully functional |
| New visit | `/children/[childId]/visits/new` | Assessment + score | Growth + operational feeding; auto-predict | `POST .../visits` | Yes | **Yes — live inference if services up** | Fully functional with schema caveats |
| Visit result | same route after POST | Dual cards | WHO + PredictionCard | response body | Yes | Yes | Fully functional |
| AI details | `/children/[id]?tab=ai` | Reliability, conformal, snapshot | explainability-dialog | stored `ga_rgca` | Yes | Yes | Fully functional (not SHAP) |
| Report | `/children/[id]/report` | Printable WHO + 12-month | ReportPage | profile + visit | Yes | Yes | Fully functional |
| Clinic board | `/clinic-board` | Clinic operations board | uses clinic children | API | Yes | Supporting | Partially functional / supporting |
| Alerts | `/alerts` | Deterioration/stagnation | rule engine on risk velocity | `GET /alerts` | Yes | Supporting | Fully functional as rules, not model XAI |
| Analytics | `/analytics` | Aggregates | dashboard + child ages | API | Yes but **not in nav** | Weak | Partially functional |
| Reports list | `/reports` | Export/list | | API | Partial | Weak | Partially functional |
| Research home | `/research` | Research copy | | | Hidden | Supporting | Static / supporting |
| Models | `/research/models` | Architecture narrative | `/models` API | Hidden | Supporting | Partially functional |
| Admin * | `/admin/system|users|settings|security` | Admin | RBAC | **Doctor login only; not in nav** | No for PP1 | Not usable as designed |
| Trajectory | `/children/[id]/trajectory`, `/model-trajectory` | Latent/progress | 2D projection is toy | API | Weak | Partially functional |
| Visits list | `/visits` | Global visits | | | Weak | Partially functional |

### PP1 requirement check

| Requirement | Assessment |
|---|---|
| Users understand the component purpose | Yes — login and cards state current WHO vs 12-month risk. |
| Healthcare worker can navigate | Doctor can. PHM/MOH workflow **does not exist**. |
| Frontend demonstrates actual functionality | Yes, against real API and loaded v4 model. |
| Research contribution visible | Yes if AI details + dual cards are shown. SuperLearner internals are not plotted. |
| AI output understandable and responsible | Mostly, if the presenter explains type chip vs four heads and “confidence %” vs probability. |
| Prototype mature enough to demonstrate | **Yes, as a research prototype**, if processes stay up. |

### Three most valuable actual screenshots

1. **`/children` worklist** — include: “Current · WHO status” and “Future · 12-month prediction” columns, a real child ID, search box, no severity on Normal rows.
2. **`/children/{id}` profile overview** — include: identity, Current WHO assessment card (z-scores + label), 12-month GA-RGCA card (type chip, four probability bars, recommendation, model confidence, uncertainty icon), visit table with more than one visit if available.
3. **`/children/{id}?tab=ai` or post-submit visit result + Open AI Details** — include: modality reliability, uncertainty/OOD, conformal set, input snapshot, model version `GA-RGCA-v4-Rolling-RSL`, horizon 12 months, “not feature attributions” note, research disclaimer.

Do not screenshot admin pages or SHAP (there is none).

---

## Testing, Runtime Status and Deployment

### Runtime this audit

| Check | Result | Classification |
|---|---|---|
| `GET http://127.0.0.1:8001/health` | `status=ok`, `active_model=GA-RGCA-v4-Rolling-RSL`, `model_loaded=true` | **Actually executed and passed** |
| `GET http://127.0.0.1:8001/model-info` | v4 SuperLearner payload as above | **Actually executed and passed** |
| `GET http://127.0.0.1:8000/health` | `{"status":"ok","service":"api","product":"CNIP"}` | **Actually executed and passed** |
| `GET http://localhost:3000` | HTTP 200 | **Actually executed and passed** |
| Ports listening | 3000, 8000, 8001 | **Actually executed and passed** |
| Authenticated UI click / new visit score | not run | **Not executed** |
| pytest / vitest / Playwright this audit | not run (avoid hitting production DB / mutating state) | **Not executed** |
| Frontend production build | not rebuilt | **Not executed** |

### Existing tests (recorded in repo, not re-run)

API: `services/api/tests/` — malnutrition type, model display (`clinical_use is False`), quality, child profile, longitudinal, dashboard, historical baseline, visit integrity, registration, RBAC, integrations, clinician review, child list, alerts.

Inference: `services/inference/tests/test_ga_rgca_v4.py`.

Frontend unit: vitest files under `apps/web/src/**/*.test.ts`.

E2E: `apps/web/e2e/phm-flow.spec.ts` still searches for child **C-1042** after doctor login. That ID is not the current clinic demonstration set documented in later recovery notes. Treat this e2e as **stale / likely BROKEN** if executed against the current database.

Training-tree tests in `ml/tests/` exercise `ml.models`, not the website adapter.

### Deployment

Local: `START_PROJECT.ps1` starts inference 8001, waits `/health`, asserts `/model-info` `GA-RGCA-v4-Rolling-RSL`, starts API 8000, starts `next start` if `apps/web/.next/BUILD_ID` exists else `next dev`. Docker compose is **legacy**. No production cloud config was audited as active.

### PP1 live-demo blockers

1. If inference/API/frontend are stopped, scoring cannot run (no mock).
2. If `ml/artifacts/ga_rgca_v4_rsl/` is missing on the demo machine, launcher exits.
3. If API `model_versions` row is not ACTIVE non-demo v4, `active_model()` 503s.
4. Cookie host mismatch (`localhost` vs `127.0.0.1`) on `NEXT_PUBLIC_API_URL`.
5. Port 3000 conflicts if both `next start` and `next dev` are launched.

At this audit, (1) was not blocking: all three processes responded.

### Research-data protection

- Names and external IDs stored encrypted (`full_name_encrypted`, `external_patient_id_encrypted`).
- Login restricted to doctors; facility-scoped child access in code.
- `clinical_use=false`; prototype labelling present.
- Model binaries gitignored; `.env` should be gitignored (standard). **Do not commit patient dumps.**
- This report contains **no** child-level records or credentials.
- Whether live logs print PII: **UNVERIFIED** (log files not dumped).
- RLS enforcement on the running cluster: **UNVERIFIED this audit**.

---

## User Feedback / Clinical Evaluation Evidence

Searched the repository for prototype feedback, clinician comments, user testing, and clinical evaluation write-ups.

| Item | Result |
|---|---|
| Named clinician who reviewed the **running website** | **NOT VERIFIED IN REPOSITORY** |
| Documented screen-by-screen user-test notes | **NOT VERIFIED IN REPOSITORY** |
| Implemented vs pending UX feedback log | **NOT VERIFIED IN REPOSITORY** |
| Model-card style limitations in code/UI | Present (`RESEARCH_LIMITATIONS`, `/model-info` flags) — these are **author-stated research limitations**, not external clinical validation |
| `clinically_validated` / `external_validation_complete` | Both **false** on running `/model-info` |
| Clinician review **feature** (agree/disagree in-app) | Implemented as software (`care.py` `create_visit_clinician_review`). Existence of stored reviews in the live DB: **UNVERIFIED this audit** |

Do not present in-app review widgets as completed clinical validation. Do not present Colab metrics as website user feedback.

---

## Notebook-to-Website Traceability Matrix

| Capability | Notebook support | Website implementation | End-to-end verified? | Evidence | Remaining gap |
|---|---|---|---|---|---|
| Multimodal feature processing | Yes | Yes — four views in snapshot | Load yes; live POST this audit no | `ROLLING_VIEW_SPECS`; `/model-info` | Follow-up form does not re-collect v4 categorical tokens |
| Reliability-aware cross-attention | Yes | Yes in `GrowthAnchoredRGCAV4` | Architecture loaded | `ga_rgca_v4.py` 454–475 | No attention visualisation |
| Underweight & stunting prediction | Yes | Yes | Load yes | heads + UI bars | — |
| Normal/MAM/SAM acute status | Yes | Yes | Load yes | `acute_status` JSON + details UI | Type chip can hide the distinction |
| Overall severity | Yes | Yes; hidden in UI when type Normal | Load yes | severity head + `displayPredictedSeverity` | Stored vs displayed severity |
| 12-month future-risk | Yes | Yes | Load yes | horizon 12, UI labels | — |
| Rolling-origin from new visits | Yes | Yes in snapshot | Code yes; repeated prospective validation **false** | `rolling_origin: true` | Contextual features often carried, not re-measured |
| Calibrated probabilities | Yes | Yes | Load yes | calibrators + temperatures | — |
| Uncertainty-aware review | Yes | Yes | Code + UI | variance flag + triage | “Confidence %” is not a probability |
| Missing-modality handling | Yes | Yes (null → limitation + missing indicators) | Code | `snapshot_frame` | Easy to silently miss feeding/supplement categories |
| Modality reliability reporting | Yes | Yes in AI details | Code | `modality_reliability` | — |
| Explainable outputs | Partial (reliability, not SHAP) | Reliability + probs + snapshot; **no SHAP** | Code | explainability-dialog; integrations `shap_available: false` | If PP1 expects SHAP, it is absent |
| Applicability / OOD | Latent distance | Flag + disclaimer | Code | `latent_q99` | Not externally validated (stated) |
| Persistent assessment history | n/a | Yes | Code | visits + predictions | No T vs T+12 outcome pairing UI |
| Actual trained model through website | Export artifacts | Loaded in running inference | **Service load verified** | `/model-info` | Button-to-score not re-run this audit |

---

## PP1 Readiness Assessment

### A. Strongest implemented achievements (five)

1. **Real GA-RGCA-v4-Rolling-RSL inference service with all six artifacts loaded** — `/model-info` this audit; `ga_rgca_v4.py`.
2. **Current visit → Baseline_* rolling mapping with leakage guards** — `snapshot_frame`; `FORBIDDEN_ROLLING_INPUTS`.
3. **Clinician UI that separates WHO-now from 12-month forecast** — `who-growth-standards.ts`; `assessment-result-cards.tsx`; worklist columns.
4. **Persisted multimodal visits and predictions with model version, input snapshot, audit** — `prediction.py` `run_inference`; `intelligence.py` `Prediction`.
5. **Uncertainty, reliability gates, conformal set, and explicit research-prototype / clinical_use=false labelling** — adapter + explainability dialog + product.json.

### B. Weakest / incomplete areas (ranked)

| Rank | Gap | Severity | Effect |
|---|---|---|---|
| 1 | Follow-up visit form collects operational feeding that is **not** mapped to v4 category features | **Critical** | Later visits may score with stale/missing socio-feeding-supplement modalities; research claim of “multimodal clinic visit” is only fully true at registration + anthro |
| 2 | UI “Model confidence %” is `1-2√variance`, not class probability | **High** | Easy to overclaim calibration in a viva |
| 3 | Primary type chip puts MAM/SAM in the same slot as Underweight/Stunting | **High** | Head structure can be mis-explained |
| 4 | No forecast-versus-later-WHO validation screen | **High** | Rolling-origin **software** ≠ completed prospective validation (`repeated_origin_prospective_validation: false`) |
| 5 | PHM/MOH roles not implemented; login is doctor-only | **High** for “user requirements” slide if the proposal promised PHM | Workflow story must stay “clinic doctor prototype” |
| 6 | No repository evidence of clinician user-testing of the website | **High** for the mandatory user-feedback bullet | Must not invent feedback |
| 7 | Trajectory 2D projection is a toy sum, not PCA | **Medium** | Do not call it learned latent visualisation |
| 8 | Velocity / alerts compare consecutive **forecasts**, which can be misread as monthly true risk | **Medium** | |
| 9 | Artifacts gitignored; e2e still mentions C-1042 | **Medium** | Demo machine and tests can desynchronise |
| 10 | C2 SHAP / C3 / C4 not connected | **Low** for Component 1 if scoped honestly | Out of C1 if C2 owns SHAP |

### C. Best two-slide story (do not design slides here)

**Content slide 1 — Sub-problem, solution, prototype**  
Paediatric undernutrition needs both **today’s WHO grade** and **12-month multimodal risk**. The prototype is a doctor clinic app: register child, record a visit, run **GA-RGCA v4 Rolling SuperLearner** on the current visit as Baseline_*, store the forecast. Screenshot: child profile dual cards.

**Content slide 2 — Technical contribution, evaluation, user feedback**  
Contribution: growth-anchored multimodal encoders + reliability gates + task attention, fused with LR/RF/XGB/LGBM SuperLearner; rolling 12-month origin; no diagnosis-label leakage. Evaluation: notebook metrics (reviewer already has Colab) + website `/model-info` `clinical_use=false`, `repeated_origin_prospective_validation=false`. User feedback: **state honestly that in-repo clinician website testing is not documented**; show the in-app clinician-review control as a **prototype capability**, not completed validation.

### D. Realistic 60-second demonstration (only implemented steps)

1. Confirm launcher banner / or this audit’s finding: inference loaded `GA-RGCA-v4-Rolling-RSL`.
2. Log in as the **seeded doctor** account (credentials not printed here).
3. Open **Children**. Point to WHO column vs 12-month column.
4. Open one existing child profile. Show Current WHO assessment vs 12-month type + four probabilities + triage.
5. Open AI details: reliability, uncertainty, model version, horizon 12, disclaimer. Say explicitly: this is **not SHAP**; confidence % is ensemble agreement; `clinical_use` is false.
6. **If time and services healthy:** New visit on that child with plausible kg/cm, confirm attestation, submit, wait for the same dual cards from **live** inference (timeout 120s in client). If inference 503s, **stop** — do not pretend a mock score.
7. Do **not** log in as PHM. Do **not** open admin. Do **not** claim monthly independent forecasts.

Live inference is **available at process level** as of this audit. A new visit was not submitted during the audit.

### E. Prioritized implementation plan

**Must complete before PP1**

- Keep START_PROJECT stack up; confirm `/model-info` on the viva machine.
- Rehearse the dual-card explanation (WHO now vs 12-month heads vs primary chip vs confidence %).
- Prepare one child with ≥2 visits so history is visible.
- Decide the user-feedback sentence: **no fabricated clinician quotes**.

**Should improve before PP1 (if any coding window remains; this audit did not change code)**

- Map or hide visit feeding controls so they cannot contradict carried v4 categories.
- Relabel “Model confidence” to “Ensemble agreement” in the UI.
- Point e2e at a real current child ID or skip that spec in the viva.

**Can remain future work**

- SHAP / C2, PHM role, T+12 outcome pairing, prospective multi-origin validation, real PCA latent explorer, SMS/FHIR.

---

## Critical Issues and Priority Fixes

See ranked gaps above. Nothing in this audit requires claiming the model is a mock: it is not. The credibility risks are **mis-explanation** (confidence, type chip, monthly velocity) and **over-claiming validation / user testing**.

---

## Best Screenshots and Demonstration Flow

Covered in Frontend inventory (three screenshots) and PP1 section D.

---

## Outstanding Questions Requiring Human Confirmation

1. Will the viva machine have the gitignored `ml/artifacts/ga_rgca_v4_rsl/` files and a running PostgreSQL `cnip` database?
2. Which child IDs are intended for the live demo (do not publish names)?
3. Is there **off-repo** clinician feedback (email, form, supervisor notes) that can be cited? None is in this repository.
4. Did the Colab notebook’s `GrowthAnchoredRGCAV4` match this file line-for-line? This audit did not diff against Colab.
5. Are any children in the live DB still synthetic? Code can hide them; live counts were not queried this audit.
6. Should historical MAM/SAM fields on the visit payload be removed from the UI later so reviewers do not think they are predictors? They are unused by `snapshot_frame`.

---

## Final status table

| Item | Status |
|---|---|
| Latest model version actually in use | **GA-RGCA-v4-Rolling-RSL** (running `/model-info`, 20 Oct 2026) |
| Complete v4 artifacts exist | **Yes** on this workstation (`ml/artifacts/ga_rgca_v4_rsl/`); gitignored |
| Real model inference works | **Service load: yes.** Live UI POST this audit: **UNVERIFIED** |
| Frontend connected to real inference | **Yes in code** (`POST /children/{id}/visits` → `run_inference` → `/predict`). No mock fallback |
| Current WHO assessment implemented | **Yes**, client-side LMS z-scores, not a DB column |
| 12-month prediction works | **Yes** as the trained task (`prediction_horizon_months=12`) |
| Rolling-origin prediction works | **Yes in software** (each visit → Baseline_*). Repeated prospective validation: **false** |
| Model outputs persisted | **Yes** (`predictions` + JSON `ga_rgca` + latents + audit) |
| Uncertainty and explanations shown | **Yes** (variance flag, reliability, conformal, snapshot). **Not SHAP** |
| Genuine clinician feedback documented | **NOT VERIFIED IN REPOSITORY** |
| Ready for PP1 demonstration | **Yes as a doctor-only research prototype**, if the three processes stay up and claims stay inside verified scope |

---

*End of audit. No application files were modified except creation of this report file.*
