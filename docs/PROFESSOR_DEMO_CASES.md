# Professor demo cases

Use child IDs only. Do not read names aloud.

Recommended order: **C-1137**, then **C-1135**. Optional contrast: **C-1141**.

---

## C-1137

Purpose:
Shows **current WHO** and the **12-month prediction** differing.

Latest stored visit (V6, 2026-09-25):

- Age origin: 22 months
- Height origin: 77.4 cm
- Weight origin: 9.7 kg
- Current WHO: **Stunting** (WAZ −1.70, HAZ −2.95, WHZ −0.33)
- Predicted type: **Normal**
- Highest predicted condition risk: **Stunting 19.79%**
- Underweight 0.81% · MAM 1.34% · SAM 0.15%
- Severity: Normal
- Uncertainty flag: false
- Triage: Routine monitoring
- Model: GA-RGCA-v4-Rolling-RSL

Teaching point:
The child can have a current WHO undernutrition label from today's measurements while the 12-month model type is Normal. Do not glue “Normal” to 19.79% — 19.79% is Stunting risk, not a Normal-class probability.

Visit history is clean: dates, age, height and weight all increase V1→V6. No missing measurements on the stored visits. V6 was restored on 20 Oct 2026 from `backups/cnip-pre-v4-only-cleanup.dump` (original 17 Oct import; deleted 18 Oct).

---

## C-1135

Purpose:
Shows a **high future Stunting risk** signal.

Latest stored visit (V5, 2026-10-09):

- Age origin: 30 months
- Height origin: 83.3 cm
- Weight origin: 10.6 kg
- Predicted type: **Stunting**
- Stunting probability: **91.37%**
- Underweight 2.01% · MAM 1.07% · SAM 0.06%
- Severity: Moderate
- Uncertainty flag: false
- Triage: Priority clinical assessment
- Model: GA-RGCA-v4-Rolling-RSL

Teaching point:
This is a future-risk example. The Stunting head is the predicted type and the displayed probability is that head (91.37%), not a residual Normal score.

Data-quality note (do not alter): V3→V4 weight 10.3 → 10.1 kg (−0.2 kg), then V5 recovered to 10.6 kg. Height and age increase throughout. Not a missing-measurement issue.

---

## C-1141 (optional contrast)

Purpose:
Shows **current WHO wasting** against a **12-month Normal** prediction.

Latest stored visit (V5, 2026-10-02):

- Age origin: 37 months
- Height origin: 94.5 cm
- Weight origin: 11.2 kg
- Current WHO: **Underweight + Wasting (MAM)** (WAZ −2.15, HAZ −0.60, WHZ −2.83)
- Predicted type: **Normal**
- Highest predicted condition risk: **MAM 17.91%**
- Underweight 15.51% · Stunting 0.07% · SAM 4.66%
- Severity: Moderate
- Uncertainty flag: true
- Triage: Clinician review / closer monitoring
- Model: GA-RGCA-v4-Rolling-RSL

Teaching point:
A current WHO wasting/underweight finding is not the same object as the 12-month type. This child has five stored visits (V1–V5). V3–V5 were restored on 20 Oct 2026 from the same pre-cleanup backup as C-1137 V6.

Data-quality note (do not alter): V2→V4 weight 11.4 → 11.3 → 11.0 kg, then V5 11.2 kg.

---

Do not add a new visit to C-1137 or C-1135 during the demonstration unless a disposable test child is used instead.
