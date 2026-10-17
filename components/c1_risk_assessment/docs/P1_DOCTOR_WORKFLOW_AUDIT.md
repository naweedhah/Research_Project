# P1 Doctor Workflow & Clinical UX Audit

Controlled correction pass after P0 scientific integrity.  
Scope: clinician workflow coherence only — no ML training / PCA / SHAP / C2–C4.

**P0 preserved:** RESEARCH DEMO banner, Demo Progression Score, Demo Score Velocity, Illustrative 2D Latent Projection, current-status demonstration, Unknown ≠ No, 1-based visits, seed/inference sync.

---

## P1-01 — Structured clinician review

| Field | Detail |
|---|---|
| **Issue** | Reviews stored as `[Clinician review]` clinical-note text and parsed in multiple places. |
| **Current files** | `child_profile.parse_clinician_review`, `dashboard._review_status`, `child_list.review_status`, `care.add_note`, seed notes. |
| **Current behavior** | Fragile string parsing; profile vs dashboard disagree on awaiting-review. |
| **Why problematic** | Not queryable, not auditable for AI-vs-clinician research, inconsistent KPIs. |
| **Required correction** | `clinician_reviews` table + API; stop creating new reviews via note text; preserve old notes. |
| **Files modified** | models, migration, care/reviews API, profile/list/dashboard/seed, UI form. |
| **Tests** | Create review leaves AI prediction unchanged; RBAC; AGREE/DISAGREE/FURTHER_ASSESSMENT. |

---

## P1-02 — Dashboard review status

| Field | Detail |
|---|---|
| **Issue** | Awaiting-review KPI only counts children with OPEN/ACKNOWLEDGED alerts + no note. |
| **Current files** | `api/dashboard.py` |
| **Current behavior** | Predicted-but-unreviewed children without alerts undercounted; opaque priority scoring mixes concerns. |
| **Why problematic** | Doctor cannot trust “patients needing my attention”. |
| **Required correction** | Use structured reviews; unique-child priority with transparent ordering; count unique pending reviews. |
| **Files modified** | `dashboard.py`, frontend dashboard if needed. |
| **Tests** | Unique awaiting-review count. |

---

## P1-03 — Child profile hierarchy / duplication

| Field | Detail |
|---|---|
| **Issue** | Measurements + AI score fused in 3D HUD; no dedicated clinical-snapshot; metrics repeated. |
| **Current files** | `child-profile-view.tsx`, `child-model-hud.tsx` |
| **Current behavior** | Alert-first layout; identity mixed into stage; progress/state can feel duplicated. |
| **Why problematic** | Doctor cannot scan hierarchy; cognitive overload. |
| **Required correction** | Overview order: header → attention → measurements → AI assessment → longitudinal → review + follow-up → history; compact HUD snapshot. |
| **Files modified** | profile view, HUD, charts labels. |
| **Tests** | Markup contract: primary sections once. |

---

## P1-04 — 3D child semantics

| Field | Detail |
|---|---|
| **Issue** | `applyRiskGlow` scales emissive by risk; `riskIntensity` default 0.5 invents mid-risk. |
| **Current files** | `ChildModel.tsx`, `ChildModelViewer.tsx` |
| **Current behavior** | Body glow tied to score — implies anatomical risk map. |
| **Why problematic** | C1 does not locate malnutrition anatomically. |
| **Required correction** | Neutral material always; remove risk→emissive mapping; decorative connectors only. |
| **Files modified** | ChildModel*, viewer wiring. |
| **Tests** | No risk glow helper / always neutral. |

---

## P1-05 — Follow-up confirmation

| Field | Detail |
|---|---|
| **Issue** | Prediction auto-creates `SCHEDULED` follow-ups without clinician confirmation. |
| **Current files** | `prediction._schedule_follow_up`, `FollowUpSchedulePanel`, `FollowUpStatus` |
| **Current behavior** | Silent clinically authoritative appointment. |
| **Why problematic** | Doctor did not confirm. |
| **Required correction** | Auto-create as `SUGGESTED`; UI Confirm / Change Date; confirm → `SCHEDULED`. |
| **Files modified** | enums, prediction, care API, follow-up panel, seed. |
| **Tests** | Suggested not treated as clinician-approved until confirm. |

---

## P1-06 — Alert assignment

| Field | Detail |
|---|---|
| **Issue** | `_notify_facility` notifies all facility `DOCTOR` users. |
| **Current files** | `prediction._notify_facility`, `Alert.assigned_to` |
| **Current behavior** | Broad broadcast; ignores `assigned_doctor_id`. |
| **Why problematic** | Noise; wrong inbox. |
| **Required correction** | Primary: assigned doctor / responsible user; fallback facility clinical inbox (doctors + facility_admin with alert:read), not every user. Set `assigned_to`. |
| **Files modified** | prediction notify helper. |
| **Tests** | Assigned doctor receives; fallback when unassigned. |

---

## P1-07 — Alert lifecycle

| Field | Detail |
|---|---|
| **Issue** | Dismiss lacks audit; lifecycle UI may be incomplete; detail wording. |
| **Current files** | `api/alerts.py`, alerts page |
| **Current behavior** | OPEN→ACK→IN_REVIEW→RESOLVED/DISMISS; dismiss requires reason but unaudited. |
| **Required correction** | Audit dismiss/resolve/in-review; factual demo-safe trigger detail; preserve history. |
| **Files modified** | alerts API, enums AuditAction, alerts UI. |
| **Tests** | Valid transitions; dismiss requires reason. |

---

## P1-08 — Visit validation alignment

| Field | Detail |
|---|---|
| **Issue** | FE allows height OR MUAC; BE requires height always. |
| **Current files** | `visits/new/page.tsx` `validationHints`; `quality.REQUIRED_ANTHRO` |
| **Current behavior** | Frontend READY can 422 on predict. |
| **Required correction** | Align FE with backend required fields; expose readiness from real validation semantics. |
| **Files modified** | visit form, optional shared hints from quality constants. |
| **Tests** | Anthropometric required fields consistency. |

---

## P1-09 — Clinical report vs research export

| Field | Detail |
|---|---|
| **Issue** | Report thin; research export may appear in doctor reports UI. |
| **Current files** | report page, `trajectory.report`, `reports/page.tsx` |
| **Required correction** | Structured doctor summary with review/follow-up/alerts; demo disclaimer; keep research export on research/admin surfaces with permission gate. |
| **Files modified** | report API + page; reports page gating. |
| **Tests** | Structured sections + disclaimer. |

---

## P1-10 — Low-value / misleading UI

| Field | Detail |
|---|---|
| **Issue** | Possible duplicated metrics; advanced AI dominating overview. |
| **Required correction** | Keep Advanced AI secondary; remove generic audit from doctor home if present; reduce duplication. |
| **Files modified** | dashboard, profile. |
| **Tests** | Profile markup contracts. |

---

## P1-11 — RBAC UI consistency

| Field | Detail |
|---|---|
| **Issue** | Command palette always shows Register; export button ungated. |
| **Current files** | `command-palette.tsx`, `reports/page.tsx`, `security.PERMISSIONS` |
| **Required correction** | Gate UI on `/auth/me` permissions. |
| **Files modified** | command palette, reports, children actions. |
| **Tests** | Permission-gated actions (unit/UI contract where practical). |

---

## Implementation notes (post-correction)

- Migration `0003_clinician_reviews` adds structured reviews + `SUGGESTED` follow-up status.
- Old `[Clinician review]` notes are preserved in seed but are no longer authoritative; new reviews use `/visits/{id}/clinician-review`.
- Re-seed / migrate after deploy so structured reviews and suggested follow-ups exist in demo data.
- P0 demo display semantics remain unchanged.

