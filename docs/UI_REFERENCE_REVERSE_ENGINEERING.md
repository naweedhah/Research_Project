# UI reference reverse engineering

Two reference videos were analysed frame-by-frame with ffmpeg (frames were kept in a temporary folder and are not committed):

- `Recording 2026-10-15 174358.mp4` — a screen recording of an earlier clinic application. It is the **information-architecture** reference: a dark left rail, a light canvas, a child register, a child profile with a 3D figure, and a clinic board.
- `visualizing-health-data-in-motion.mp4` — the **motion and material** benchmark: deep navy backgrounds, translucent glass panels, cyan accents, slow 3D rotation, data that animates into place.

This document records what was extracted and how it was translated into the paediatric malnutrition prototype without changing any clinical or model logic.

## Depth model (five layers)

| Layer | Purpose | Implementation |
| --- | --- | --- |
| 0 Canvas | Soft light background with two faint radial washes | `body` background `#eef3f6` + cyan/blue radial gradients, fixed attachment |
| 1 Glass surfaces | Content cards | `bg-white/70–85`, `backdrop-blur-xl`, `rounded-[24px]/[28px]`, `border-white/70`, `shadow-card` |
| 2 Navy intelligence | Anything that is a *prediction* | `bg-[#0E243D]`, white text, cyan `#58D3CA` labels, `shadow-elevated` |
| 3 Floating chrome | Navigation rail and pill header | sticky navy rail 96px with grouped sections; sticky white/75 pill header |
| 4 Overlays | New visit, AI details | blurred navy scrim `#0A2748/50`, rounded 28px dialogs |

The rule that drives the whole product: **light glass = measured now, navy = predicted next 12 months.** These never share a card.

## Material

- Palette: canvas `#F4F7FA/#EEF3F6`, navy `#0E243D/#102A4C/#173D6B`, blue `#3E75B8/#346FA7`, cyan `#45C4BB/#58D3CA`, amber `#E8AE4E`, coral `#E66C61`.
- Status colours (children register, clinic board): Normal green, Underweight red, Stunting amber, MAM orange, SAM deep red.
- Typography: Inter; kicker labels 11px uppercase tracking 0.16–0.18em; page titles 30px semibold; numbers tabular.

## Motion

Tokens live in `apps/web/src/components/futuristic/motion-tokens.ts`.

- Ease `[0.16, 1, 0.3, 1]`; micro 180ms, card 480ms, hero 850ms, stagger 60ms.
- Visit cards animate in sequence (`VisitMotionTimeline`); progress bars grow with `transition-[width]`.
- The login orb rotates at 0.18 rad/s; floating labels drift 6px.
- Every animation respects `prefers-reduced-motion` (CSS `.motion-safe-only`, `useReducedMotion`, and a `matchMedia` listener for the R3F scene).

## 3D

- Login: React Three Fiber sphere with `meshPhysicalMaterial` transmission, one cyan torus and one white torus. `dpr` capped at 1.25, loaded with `next/dynamic` (`ssr: false`).
- Child profile: the existing neutral child twin, `dpr` capped at 1.5, cyan rim light, 62vh glass stage with a cyan halo ring. The twin is a visual metaphor for the visit timeline only; it does not encode any clinical value.

## Data visualisation

- Probabilities are horizontal bars with the numeric value beside them; never a gauge without a number.
- Facility distributions show *Current WHO* (light card) beside *Next 12 months* (navy card) with identical bar styling so the two time points can be compared but not confused.
- Recharts axes use `#5C6E82` ticks, no axis lines, rounded bar tops.

## Navigation

Grouped rail using existing routes only:

- Clinic — Dashboard, Children, Clinic board, Alerts
- Child care — Visits, Reports
- Intelligence — Analytics, Model
- System — Admin

Mobile keeps the four Clinic items in a bottom bar.

## What was deliberately not borrowed

- No invented vitals (heart rate, SpO2, blood pressure), no MUAC, no oedema, no organ or DNA visuals.
- No SHAP or feature-importance charts; modality reliability is labelled as usability of each information group.
- No live "accuracy" counters. The 14 research metrics are shown once, labelled "Research evaluation on the study dataset".
