# Authoritative Component 1 Context

**Project:** Explainable AI Framework for Early Detection and Personalized Intervention of Childhood Malnutrition in Sri Lanka  
**Project ID:** J26-IT-399  
**Component 1 owner:** Kavindi T.A.C. / Chanodya — IT22541048

This document is the **functional, research, architecture and UX context** for Component 1.  
Enforceable Cursor rule: `.cursor/rules/component1-research-context.mdc`

When code conflicts with this specification, identify the conflict and align implementation while preserving working infrastructure.

---

## System flow (four components)

```text
CHILD DATA → C1 (predict + track progress) → C2 (explain + context + trust)
                                          → C3 (feasible interventions)
                                          → C4 (population/model drift)

Future visits → C1 measures individual improvement
Predictions + outcomes over time → C4 monitors model reliability
```

**C1 question:** Is this individual child improving or deteriorating across visits?  
**C4 question:** Is the model becoming unreliable because the population distribution changed?

Do not merge these.

---

## C1 owns

- Modality encoders + Multi-Head Cross-Attention + fused embedding `e_t`
- Status/type, severity (config-driven), calibrated probability/risk
- Longitudinal profile, Risk Velocity, baseline-relative change
- Progress states, stagnation/deterioration/relapse alerts, follow-up overdue
- Latent sequence storage and **versioned** projection for visualization
- Deployment of prediction/progression service

## C1 does NOT own

| Feature | Owner |
|---------|--------|
| SHAP / full XAI | C2 |
| Food price, weather, outbreak context | C2 |
| Counterfactual intervention generation | C3 |
| Treatment prescription | C3 + clinician |
| Concept drift / recalibration triggers | C4 |

If C2 not connected: **"Explainability component not connected."** — no fake explanations.

---

## Data modalities (four)

1. Anthropometric / child features  
2. Socioeconomic / household (incl. WASH unless split later)  
3. Dietary / feeding  
4. Maternal and child health  

**Entry principle:** stable background data at baseline + carry-forward; visit-specific data per visit.  
**Never invent inputs.** Unknown ≠ No.

---

## Model pipeline

Preprocessing (versioned, no leakage) → encoders → Cross-Attention → `e_t` → status + severity + calibrated risk.

**Target leakage:** distinguish current-status classification vs genuine early-risk prediction. Do not claim "early prediction" without temporal support.

**V0 baseline** stores: inputs snapshot, model/preprocessing versions, prediction, calibrated risk, embedding, data quality.

**Follow-ups V1…Vn:** same pipeline + Risk Velocity + progress state + alerts.

---

## Risk Velocity

```text
RV_t = [Risk(V_{t-1}) - Risk(V_t)] / elapsed months
```

Positive RV → risk decreased. Stagnation thresholds are **configurable/policy-driven**, not hard-coded zero.

---

## Latent trajectory

Fit PCA/UMAP on reference embeddings; version artifact; transform new `e_t`.  
**Do not** fake coordinates or paint unvalidated "healthy zones."  
Disclaimer: representation trajectory does not independently determine clinical status.

---

## Primary doctor progress view

Lead with:

- AI probability trend (defined semantics)
- Weight / height / MUAC trends (actual measurements only)
- Visit chronology

Advanced section: latent trajectory, model metadata.

---

## Progress states & alerts

Improving · Limited progress/stagnation · Deteriorating · Possible regression/relapse · Insufficient history

Alert lifecycle: OPEN → ACKNOWLEDGED → IN REVIEW → RESOLVED / DISMISSED WITH REASON

Do not infer non-adherence. Use "limited improvement detected."

---

## Clinician review (required pattern)

AI assessment block + clinician agree/disagree/uncertain + structured status + note + workflow decision (monitor / nutrition review / investigate / refer / request intervention reassessment).

---

## Doctor page hierarchy

Patient → clinical measurements → AI assessment → progress since last visit → alert → clinician review → follow-up → advanced AI details

Not: huge futuristic chart above buried clinical facts.

---

## UI philosophy

Modern and clean yes; game scores, fake holographic maps, unvalidated 3D, neon cyberpunk no.  
Advanced styling around **real data**.

---

## Safe terminology

| Prefer | Avoid |
|--------|--------|
| AI-assisted assessment | AI diagnosis |
| Model-assessed probability | Undefined "Risk %" |
| Possible deterioration | Treatment must change |
| Request intervention reassessment | AI recommends treatment |
| Clinical review recommended | Treatment failed |

---

## Model modes

- `demo` → **DEMO MODEL — NOT FOR CLINICAL USE**, synthetic labelled  
- `pytorch` / `onnx` → real artifacts + schema + calibration + version metadata  

Never fabricate performance until experiments exist.

---

## Development priority

1. **P0** — data integrity, no fake inputs/metrics/misleading UI  
2. **P1** — doctor workflow (trends, review, alerts, reports)  
3. **P2** — real ML pipeline, baselines, ablation, calibration  
4. **P3** — HIMS/FHIR, messaging, ops  

---

## Acceptance demo (25 steps)

Login → patients requiring review → open child → measurements visible → new visit with carry-forward → validation → inference → save → RV + trends + trajectory → progress state → alerts → clinician review → C3 reassessment request → C2/C4 integration hooks → versioned audit → no fabricated evidence.

---

## One-line reminder

> C1 is the predictive and child-level longitudinal intelligence core: multimodal fusion, calibrated outputs, repeated-visit change metrics, and workflow alerts — always as **decision support** with clinician review, feeding C2/C3/C4 without absorbing their research scope.

---

## Full section index (authoritative spec sections 1–79)

1. Overall research project · 2. Four components · 3. C2 · 4. C3 · 5. C4 · 6. Research question · 7. Research vs CRUD · 8. Modalities · 9. Data entry · 10. Never invent inputs · 11. Baselines · 12. Preprocessing · 13. Encoders · 14. Cross-Attention · 15. Latent embedding · 16. Outputs · 17. Target leakage · 18. V0 · 19. Follow-ups · 20. Longitudinal profile · 21. Risk Velocity · 22. Baseline-relative change · 23. Latent trajectory · 24. No fake healthy zones · 25. Primary progress viz · 26. Progress states · 27. Stagnation · 28. Deterioration · 29. Relapse · 30. Missed follow-up · 31. Alert recipients · 32. Doctor role · 33. Clinician review · 34. No predicted vs actual without evidence · 35. Child profile layout · 36. Dashboard · 37. Not audit homepage · 38. Measurement trends · 39. WHO handling · 40. Data quality · 41. Age/sex · 42. Structured categoricals · 43. C1 flow diagram · 44. Output contract · 45. Model versioning · 46. Real projection · 47–49. Evaluation · 50. Longitudinal data · 51. Pseudonymization · 52–55. UI/terminology · 56. Non-adherence · 57. Alert workflow · 58. Follow-up · 59. Reporting · 60. Intervention timeline · 61–63. Boundaries/integration · 64. Example workflow · 65–68. Value/deployment · 69. Architecture · 70. Demo vs real · 71–73. Evidence · 74. Priorities · 75. Acceptance · 76–79. Summary/instructions

For the complete prose of each section, refer to the authoritative specification provided to the project team (also encoded in `.cursor/rules/component1-research-context.mdc`).
