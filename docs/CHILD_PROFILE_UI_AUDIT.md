# Child Profile UI Audit

**Page:** `/children/[childId]`  
**Primary components:** `child-profile-dashboard.tsx`, `page.tsx` (advanced details), `clinician-review-panel.tsx`, `follow-up-schedule-panel.tsx`, `child-workspace-links.tsx`, `child-model/*`  
**Primary API:** `GET /children/{id}` (`_child_profile` in `services/api/app/api/children.py`)  
**Related APIs:** `GET /children/{id}/trajectory`, `/risk-history`, `/progress`, `/report`; `POST /children/{id}/notes`; `POST /children/{id}/follow-ups`; `PATCH /alerts/{id}/acknowledge`

---

## Current UI sections

| Section | Location | What it shows |
|---|---|---|
| Breadcrumb + Export / Record visit | Dashboard toolbar | Identity + actions |
| Registration / no-baseline banners | Page | Empty-state CTAs |
| Child record card | Left column | ID, sex, age, DOB, Weight, Height, MUAC |
| Clinical measurements | Left column | Weight, Height, MUAC, Probability + sparklines |
| Longitudinal progress (left) | Left column | Progress label, status/severity badges, last visit, follow-up date |
| Giant 3D model + HUD chips + connector lines | Centre | Risk-coloured avatar, duplicated metrics as floating chips |
| Recent activity | Right column | Visit list with Critical/Review/Normal badges |
| Follow-up schedule | Right column | Next visit date |
| AI analytics | Right column | Probability, previous, +pp, progress, status, severity |
| Follow-up panel | Below dashboard | Same next-follow-up date again + reschedule |
| Clinician review | Below dashboard | Full AI summary again + agree/disagree form |
| Advanced details | Collapsed | Visit history, latent trajectory, 3D again, C2 empty, alerts, notes, model info |

---

## Duplicated fields

| Field | Times shown on overview | Locations |
|---|---|---|
| Weight / Height / MUAC | 3 | Child record tiles, Clinical measurements, HUD chips |
| Model-assessed probability | 4 | Measurements tile, HUD, AI analytics (large), visit list |
| Nutritional status (e.g. Wasting) | 3 | Longitudinal badges, AI analytics copy, visit list |
| Severity | 3 | Longitudinal badges, AI analytics copy, visit list |
| Progress (Deteriorating) | 3 | Longitudinal subtitle + implied again, AI analytics, visit badges |
| Last visit date | 2 | Longitudinal card, visit timeline |
| Follow-up date | 3 | Longitudinal card, Follow-up schedule card, HUD chip, plus panel below |
| Child ID | 2+ | Breadcrumb, child record, HUD |

---

## Misleading fields

| Field | Issue | Replacement |
|---|---|---|
| Visit badges `Critical` / `Normal` / `Review` | Derived from probability bands in the frontend (`visitActivityStatus`). Looks like clinical review or “normal nutrition”. Contradicts `Underweight + Normal`. | Separate nutritional status from clinician review state. |
| 3D heatmap colour | Reads as anatomical disease location. | Neutral avatar only; optional, compact, hidden below 1280px. |
| Connector lines / HUD chips | Decorative, duplicate metrics, clutter. | Remove. Use grouping, chart, timeline. |
| AI analytics + Longitudinal both showing Wasting/Moderate | Duplicate C1 output. | One AI-Assisted Assessment card. |
| Left “Longitudinal progress” without a chart | Name implies Chanodya’s enhancement; content is badges. | Real probability/measurement chart + Risk Velocity. |
| Clinician review buried below a giant 3D stage | Human-in-the-loop is not visible in 5–10s. | Care workflow column on Overview. |
| `Critical` on V1 | Not an alert/review label. | Drop probability-band badges. |

---

## Missing data (API has it, UI unused or incomplete)

| Data | API source | Planned use |
|---|---|---|
| Previous visit measurements | Prior visit `measurements` | Snapshot deltas only |
| `risk_change_pp` | Profile | AI card Current vs Previous |
| `risk_velocity` | Visit metric / `/progress` | Longitudinal sidebar |
| `baseline_recovery_rate` | Metric | Secondary “Since baseline” if present |
| `model_warning` / embedding space mismatch | Profile | Incompatible-model banner; do not compare |
| `assigned_doctor` | Profile | Header if present; never invent a name |
| `facility.code` / name | Profile | Header once |
| `data_quality` | Visit JSON | Compact indicator on AI card |
| Four modality records | Visit relations | AI Details → Data Inputs |
| Model version architecture, dim, calibration, `is_demo` | `ModelVersion` | Header demo badge once; AI Details tab |
| Clinician review notes `[Clinician review]…` | Clinical notes | Review status + recorded review |
| Open alerts + trigger previous/current risk | Alerts | Single attention banner |
| Latent `projection` + `projection_version` | Embeddings | Advanced AI tab only |
| Follow-up overdue days | Follow-up schedule vs today | One Follow-Up card |

---

## Backend fields to add (derived, not invented)

Profile payload will additionally expose:

- `previous` visit summary (measurements + prediction) when a prior visit exists
- `progress_display` (`insufficient_history` when <2 predicted visits; never fake Stable)
- `risk_velocity_pp_month` from stored metric (null if unavailable)
- `since_baseline_pp` only when baseline and current probabilities exist
- `longitudinal_comparable` false when embedding spaces differ or metric `model_compatible` is false
- `clinician_review` parsed from notes for the latest visit
- `model` metadata from the active/latest `ModelVersion`
- `model_is_demo`
- `data_quality` + `modalities` counts from stored records
- `follow_up_overdue_days` when overdue
- per-visit `review_status` for Assessment History

Frontend must not compute Risk Velocity, progress state, or probability.

---

## Planned replacement (information architecture)

```text
Patient identity          → Header (once)
Measurements              → Current Clinical Snapshot (once)
Current AI result         → AI-Assisted Assessment (once)
Change over time          → Longitudinal Progress (chart + RV + state)
Alert                     → Clinical Attention banner (only if open)
Follow-up                 → Care workflow Follow-Up card (once)
Clinician review          → Care workflow Review card
Previous assessments      → Assessment History / Visits tab
Latent / model / inputs   → AI Details / Progress & Trajectory (advanced)
```

**Removed from overview:** HUD connectors, giant 3D stage, duplicate measurement card, duplicate AI analytics, duplicate follow-up, ambiguous Critical/Normal badges, second 3D tab as primary content.

**3D avatar:** compact, neutral, header-right, `xl+` only. Not a scan. Not risk anatomy.

---

## Tabs (no full Overview clone)

| Tab | Contains |
|---|---|
| Overview | Header, alert, snapshot, AI assessment, longitudinal summary, review, follow-up, compact history |
| Visits | Full visit/measurement table |
| Progress & Trajectory | Probability + W/H/MUAC toggles, Risk Velocity, latent trajectory |
| Clinical Notes | Notes list + add note |
| AI Details | Model metadata, modalities/inputs, version/incompatibility |

---

## Design language (preserve)

Light slate/blue canvas (`#e8eef5`), white rounded cards (`rounded-2xl` / `rounded-3xl`), navy type (`#0f2744` / `#0A2748`), blue actions, thin `border-line`, `shadow-card`, restrained green/amber/red for improving / limited improvement / deterioration only.
