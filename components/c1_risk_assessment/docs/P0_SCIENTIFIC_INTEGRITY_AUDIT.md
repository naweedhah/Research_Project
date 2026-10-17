# P0 Scientific Integrity Audit

Controlled correction pass for CNIP Component 1 (J26-IT-399).  
Scope: demo-safety and scientifically misleading runtime claims only.

---

## P0-01 — Persistent DEMO / not-for-clinical-use indicator

| Field | Detail |
|---|---|
| **Issue** | Demo inference is the only live adapter, but the global demo banner returns `null`. |
| **Current file/function** | `apps/web/components/demo-banner.tsx` (`DemoBanner`, `ResearchDisclaimer`); default `MODEL_MODE=demo` in `services/api/app/core/config.py` / `.env.example`. |
| **Current behavior** | Authenticated clinical pages can show synthetic scores without a persistent “not for clinical use” indicator. |
| **Why unsafe** | Supervisors/clinicians can mistake demonstration outputs for trained Cross-Attention results. |
| **Required correction** | Restore one professional header strip driven by backend model-display metadata (`model_mode` / `is_demo`), never a hard-coded React `true`. Non-demo research modes must not imply “clinically validated”. |
| **Files changed** | `apps/web/components/demo-banner.tsx`, `apps/web/components/app-shell.tsx`, `apps/web/lib/model-display.ts`, API runtime display endpoint / product enrichment, tests. |
| **Verification/test** | UI/metadata test asserting “Not for clinical use” when mode is demo. |

---

## P0-02 — “Model-Assessed Probability” mislabels the demo scalar

| Field | Detail |
|---|---|
| **Issue** | DemoModelAdapter produces a synthetic scalar (lookup/heuristic), not a calibrated class or future-risk probability. |
| **Current file/function** | `services/inference/app/main.py` `DemoModelAdapter`; UI labels in dashboard, worklist, HUD, charts, reports (`Model-Assessed Probability`). |
| **Current behavior** | UI presents the scalar as probability without demo qualification. |
| **Why unsafe** | Implies P(malnutrition) / calibrated model output that does not exist in live inference. |
| **Required correction** | Central display semantics: demo → **Demo Progression Score** (`score_is_probability: false`). Keep DB field `primary_risk_score`. Future modes can switch labels via metadata. |
| **Files changed** | Shared semantics helper (API + web), child list/dashboard/profile/charts/report/visit result copy, tests. |
| **Verification/test** | Assert demo metadata label and `score_is_probability === false`. |

---

## P0-03 — Risk Velocity terminology under demo scores

| Field | Detail |
|---|---|
| **Issue** | Longitudinal formula is correct, but inputs are demo scalars. |
| **Current file/function** | `services/api/app/services/longitudinal.py` (formula preserved); UI “Risk velocity” in profile/HUD/dashboard. |
| **Current behavior** | Unqualified clinical “Risk Velocity” label. |
| **Why unsafe** | Suggests validated recovery metric. |
| **Required correction** | Display **Demo Score Velocity** + honest tooltip when semantics are demo. Do not change the formula. |
| **Files changed** | Model-display helper; profile/HUD/dashboard/worklist labels; alert detail wording where natural. |
| **Verification/test** | Assert velocity display label for demo mode. |

---

## P0-04 — DEMO_LOOKUP visit numbering (0-based vs DB 1-based)

| Field | Detail |
|---|---|
| **Issue** | DB/seed `visit_number` is 1-based; `DEMO_LOOKUP` keys are 0-based. |
| **Current file/function** | `services/inference/app/main.py` `DEMO_LOOKUP`; `services/api/app/seed.py` `visit_number=idx+1`. |
| **Current behavior** | Seeded V1 can disagree with re-inference for the same visit_number. |
| **Why unsafe** | Non-idempotent demonstration; broken narrative integrity. |
| **Required correction** | Canonical 1-based visit numbers; shared outcomes source; regression tests for C-1042 V1…Vn. |
| **Files changed** | `packages/contracts/demo_outcomes.json`, inference adapter, seed embedding/lookup keys, inference tests. |
| **Verification/test** | Seed/inference parity tests for C-1042 visits 1–3. |

---

## P0-05 — Arithmetic projection labelled as PCA

| Field | Detail |
|---|---|
| **Issue** | `_project()` is a weighted arithmetic map stored as `pca-demo-v1`. |
| **Current file/function** | `services/api/app/services/prediction.py` `_project`; seed `projection_version="pca-demo-v1"`; UI “Projection”. |
| **Current behavior** | Runtime claims PCA for a non-PCA transform. |
| **Why unsafe** | Misrepresents scientific method. |
| **Required correction** | Version `demo-latent-projection-v1`; UI **Illustrative 2D Latent Projection** + disclaimer. Leave `ml/trajectory/fit_projection.py` unconnected. |
| **Files changed** | `prediction.py`, `seed.py`, profile Advanced AI copy, tests. |
| **Verification/test** | No active demo projection version contains `pca-demo`. |

---

## P0-06 — Current-status demo described as early/future risk

| Field | Detail |
|---|---|
| **Issue** | Live task is current-status demo; research title remains early detection. |
| **Current file/function** | AI Details “Current-status classification”; product/research docs; any “future risk” runtime claims. |
| **Current behavior** | Mostly correct task string, but probability wording can imply future risk. |
| **Why unsafe** | Conflates research ambition with active inference. |
| **Required correction** | Demo prediction task label: **Current-status demonstration**. Remove unsupported runtime future-prediction claims only. |
| **Files changed** | Semantics helper, AI Details / report metadata, search/replace audit of runtime UI. |
| **Verification/test** | Metadata prediction_task_label for demo. |

---

## P0-07 — Unknown medical flags treated as No in demo heuristic

| Field | Detail |
|---|---|
| **Issue** | `1 if recent_diarrhoea is True else 0` maps `None` → 0. |
| **Current file/function** | `DemoModelAdapter._from_measurements` in `services/inference/app/main.py`. |
| **Current behavior** | Unknown indistinguishable from No. |
| **Why unsafe** | Violates Unknown ≠ No data integrity. |
| **Required correction** | Distinct True / False / None paths; Unknown contributes neutrally (excluded). Document behavior. |
| **Files changed** | Inference heuristic + tests. |
| **Verification/test** | True / False / None diverge for diarrhoea contribution. |

---

## P0-08 — Seed vs live inference inconsistency

| Field | Detail |
|---|---|
| **Issue** | Duplicate demo case definitions; embedding uses 0-based idx in seed vs request visit_number in inference; confidence rules differ. |
| **Current file/function** | `seed.py` CASES + `_embedding`/`_confidence_for_risk`; inference `DEMO_LOOKUP`. |
| **Current behavior** | Same child/visit can yield different score/embedding/confidence. |
| **Why unsafe** | Breaks demo reproducibility. |
| **Required correction** | Shared `demo_outcomes.json`; shared embedding helper with 1-based visit_number; demo confidence fixed as non-calibrated (`moderate`) for both paths. |
| **Files changed** | Contracts outcomes, inference, seed, tests. |
| **Verification/test** | Idempotent re-inference vs seeded outcomes. |

---

## P0-09 — Reports/export can look clinically validated

| Field | Detail |
|---|---|
| **Issue** | Child HTML report / exports lack a clear demo/not-clinical-use banner. |
| **Current file/function** | `apps/web/app/(clinical)/children/[childId]/report/page.tsx`; `POST /research/export` (`synthetic: true`). |
| **Current behavior** | Research export flags synthetic; doctor report can omit demo disclaimer. |
| **Why unsafe** | Print/screenshot can be taken as clinical evidence. |
| **Required correction** | Add RESEARCH DEMONSTRATION / Not for clinical use on demo reports; preserve `synthetic: true` on research export and reinforce demo metadata. |
| **Files changed** | Report page, export response metadata, trajectory report if applicable, tests. |
| **Verification/test** | Report/export contains not-for-clinical-use identification under demo. |

---

## P0-10 — Regression tests

| Field | Detail |
|---|---|
| **Issue** | Above failures can return without focused tests. |
| **Required correction** | Focused API/inference/frontend contract tests listed in sections 37–44 of the control prompt. |
| **Files changed** | New/updated tests under `services/inference/tests`, `services/api/tests`, `apps/web/lib`. |
| **Verification/test** | Commands in final response. |

---

## Runtime wording decisions (search)

| Phrase | Decision |
|---|---|
| Research docs mentioning PCA/UMAP as **future** method | Keep (research target). |
| Runtime `pca-demo-v1` / UI implying current plot is PCA | Correct to illustrative demo projection. |
| “Model-Assessed Probability” under demo | Correct to Demo Progression Score. |
| Official component title “Early Detection…” | Keep; active task labelled current-status demonstration. |
| “Clinically validated” | Must not appear for demo or unverified research modes. |

---

## Implementation notes (post-correction)

- Canonical outcomes: `packages/contracts/demo_outcomes.json` (1-based `visit_number`).
- Display contract: `get_model_output_display_metadata` (API) + `getModelOutputDisplayMetadata` (web).
- Persistent banner: `GET /runtime/model-display` → `DemoBanner` in app shell.
- After deploy, **re-seed** (or recreate volumes) so stored `projection_version` and embeddings match the corrected 1-based convention for existing demo DBs.
