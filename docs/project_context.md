# Childhood Malnutrition AI Research Project — Project Context and Finalized Component 3

## 1. Project overview

### 1.1 Research setting

This project is a group research project focused on applying AI/ML to childhood nutrition and malnutrition-related decision support in Sri Lanka, with the intended workflow aligned to the country's community maternal-and-child-health system and MOH/PHM context.

The project is designed as four complementary components:

1. **Multimodal Early Detection / Risk Assessment Model**
2. **Personalized Counterfactual Intervention Engine**
3. **Adaptive Model Reliability Monitoring and Safe Maintenance Framework**
4. **Spatio-Temporal Malnutrition Burden Forecasting and Nutrition Resource Demand Visualization**

The components have deliberately different responsibilities:

- **C1 asks:** What is this child's malnutrition risk/status?
- **C2 asks:** Given the child's situation and predicted risk, what feasible changes/interventions could improve the child's situation?
- **C3 asks:** Can the deployed prediction model still be trusted, and if not, how should it be safely maintained?
- **C4 asks:** Where and when is malnutrition burden likely to increase, and where may nutrition resources be needed?

C3 therefore does not compete with C1. It operates around the prediction model produced by C1.

---

## 2. Sri Lankan data and field context

### 2.1 Field observations

The project team investigated the practical data available through the Sri Lankan public-health system. A major finding was that detailed individual child information is not necessarily centralized at higher administrative levels.

Detailed records may remain with:

- local PHMs,
- MOH areas,
- parents/caregivers,
- Child Health and Development Records (CHDRs),
- growth charts and routine community records.

The team also found that historical data availability differs between PHMs because staff may have been transferred or may have different lengths of service.

### 2.2 Nutrition Month data

The most realistic historical source identified for the project is the annual **Nutrition Month** data collection.

The Family Health Bureau's Child Nutrition Unit states that it conducts annual child nutrition status surveys during Nutrition Month and maintains child-health/nutrition records. The FHB also publishes Nutrition Month summary reports and provides PHM child-nutrition forms. It additionally lists a 2020 Sri Lankan manual for management of severe and moderate acute undernutrition in children under five.

Important project implication:

> The available historical data are better understood as repeated annual cross-sectional snapshots than as a continuous longitudinal dataset.

The project currently expects approximately four to five usable annual snapshots (for example, around 2022–2026), subject to what can actually be digitized and obtained.

### 2.3 Historical versus 2026 data

The historical Nutrition Month records are expected to contain mainly variables such as:

- age or information from which age can be derived,
- sex,
- height,
- weight,
- nutritional/growth-status information,
- date/year,
- PHM/MOH-area information where available.

The **2026 collection** is expected to be richer and may contain variables such as:

- maternal age,
- maternal education,
- household income range,
- family size,
- occupation where available,
- exclusive breastfeeding,
- breastfeeding duration,
- complementary feeding,
- meals per day,
- dietary diversity,
- Triposha,
- vitamin supplementation,
- birth weight where available.

Some variables, especially household income, may contain reporting error or under-reporting.

External contextual data may also be considered for C4 or controlled experiments, including:

- inflation/CPI,
- food prices,
- rainfall,
- floods/disasters,
- disease/outbreak context.

However, repeating a yearly macroeconomic value for hundreds of children does **not** create hundreds of independent socioeconomic observations. The limited number of annual observations must therefore be respected in modelling.

### 2.4 Geographic limitation

The accessible MOH areas are concentrated in essentially the same geographic region. Consequently, the historical data do not provide strong spatial diversity.

This limits claims about nationwide geographic generalization and makes it inappropriate to manufacture artificial geographic heterogeneity merely to make a model appear stronger.

---

## 3. Important terminology issue: stunting, wasting, underweight, MAM and SAM

The project team encountered an important distinction during field discussions.

Sri Lankan nutrition surveillance separately tracks indicators such as:

- stunting,
- wasting,
- underweight.

However, field staff explained that a child with one of these growth/nutritional indicators is not necessarily operationally treated as a **"malnourished child"** requiring the same management pathway. In particular, the community-management workflow distinguishes children requiring management for moderate or severe acute undernutrition.

This means the research team must not simply assume that:

> stunting = malnutrition case  
> wasting = malnutrition case  
> underweight = malnutrition case.

At the same time, the project must also avoid making the opposite overgeneralization that Sri Lanka has only three nutrition categories.

The correct research procedure is:

1. inspect the actual Nutrition Month/PHM form and data fields;
2. determine exactly how stunting, wasting and underweight are recorded;
3. determine exactly how MAM and SAM are recorded;
4. determine what category is assigned when a child has a growth abnormality but does not meet the operational MAM/SAM criteria;
5. align C1's target with the actual operational decision the system is intended to support.

This is a **data/label-definition dependency** and should be resolved before finalizing the C1 target.

The Family Health Bureau currently lists both Nutrition Month reports/forms and the national manual on management of severe and moderate acute undernutrition. These official resources support treating the surveillance indicators and acute-undernutrition management workflow as related but not automatically identical concepts.

---

# 4. Component 1 — Multimodal Early Detection / Risk Assessment

## 4.1 Original concept

The initial idea for C1 was to classify children into:

- stunting,
- wasting,
- underweight,
- normal.

This is problematic if treated as a mutually exclusive four-class target because a child can satisfy more than one nutritional/growth condition. More importantly, the field investigation showed that the project's intended operational decision may not use these indicators as mutually exclusive "malnutrition classes."

## 4.2 Current direction

The working direction is to make C1 intervention-oriented and aligned with the actual Sri Lankan community workflow.

A possible target is:

- Normal,
- MAM,
- SAM.

However, **this should only be finalized after confirming the exact labels used in the obtained Nutrition Month records.**

The target should not be chosen merely because it is convenient for a machine-learning classifier.

## 4.3 Major methodological issue

If C1 uses only:

- age,
- height,
- weight,

and then predicts a nutritional category that is itself mathematically defined from those anthropometric measurements, the model may simply reproduce a clinical classification rule.

That would make the ML contribution weak.

Therefore, the preferred C1 formulation is to use upstream, non-anthropometric predictors such as:

- maternal factors,
- household factors,
- dietary factors,
- feeding practices,
- supplementation,
- birth information where available,
- age/sex,

while treating the anthropometrically defined nutritional status as the outcome.

This makes C1 a **risk assessment / early identification model** rather than a neural-network implementation of a WHO/MOH lookup rule.

The project must also avoid target leakage. If height and weight directly determine the target label, those variables should not be used as ordinary predictive inputs when the goal is to demonstrate meaningful risk prediction from upstream factors.

## 4.4 Model family

Because the rich 2026 dataset is expected to contain roughly a few thousand children rather than millions of observations, classical tabular ML models are likely to be more appropriate than a deep neural network.

Potential candidates include:

- multinomial/logistic regression,
- Random Forest,
- XGBoost,
- CatBoost.

The final choice should be based on the actual data size, class counts, missingness and validation results.

Class balance is critical. The total sample size alone does not guarantee that a three-class model is viable. The number of genuine MAM and especially SAM cases must be established after the data inventory/pilot.

---

# 5. Component 2 — Personalized Counterfactual Intervention Engine

C2 receives information from C1 and turns prediction/risk information into actionable intervention guidance.

The intended direction is:

> **Prediction → feasible intervention recommendation**

The component is not merely an explanation module. It should answer a practical question such as:

> "What realistic changes to modifiable factors could move this child toward a healthier predicted state?"

The proposed technical direction uses counterfactual explanation/intervention methods such as:

- **DiCE** for diverse counterfactual explanations;
- **FACE** for feasible/actionable counterfactual paths.

The intervention engine should prioritize changes that are:

- clinically/health-contextually plausible,
- feasible for the family,
- within modifiable variables,
- consistent with Sri Lankan community nutrition practice.

Where expert validation is available, proposed counterfactual recommendations should be reviewed for plausibility.

C2 therefore differs from C1:

- C1 predicts risk/status.
- C2 identifies feasible changes that could potentially improve that prediction.

---

# 6. Component 3 — Adaptive Model Reliability Monitoring and Safe Maintenance Framework

## 6.1 Final working title

> **Adaptive Model Reliability Monitoring and Safe Maintenance Framework**

A shorter implementation description can use:

> **Bounded-Autonomous Model Maintenance**

The word **"policy-driven"** should not be used as the main title or headline novelty claim. It can create unnecessary expectations about reinforcement learning, formal policy optimization, or extensive policy experiments.

The preferred wording is:

> **adaptive maintenance decision mechanism**

or

> **predefined maintenance decision framework**.

---

## 6.2 Core problem

A prediction model that performs well during development may become less reliable after deployment because the data environment can change.

Examples:

- demographic composition changes,
- dietary patterns change,
- socioeconomic conditions change,
- feature availability changes,
- data-quality deteriorates,
- measurement practices change,
- prevalence changes,
- relationships between predictors and outcomes change.

However:

> **Data changed ≠ model broken.**

A distribution shift does not automatically mean that model reliability has deteriorated.

This is the central idea of C3.

The system therefore needs to answer:

> **Has the data changed in a way that actually threatens the reliability of the prediction model, and if so, what is the least-invasive safe maintenance action?**

---

# 7. C3 research question

### Primary research question

> **How can a deployed childhood malnutrition risk model determine whether a detected data shift is actually harmful to model reliability and safely adapt itself using the least-invasive validated maintenance action?**

A shorter presentation version is:

> **Can a bounded-autonomous maintenance system detect when the C1 model becomes unreliable, select an appropriate corrective action, verify the correction, and safely promote or reject the updated model?**

---

# 8. C3 conceptual architecture

The final architecture is:

> **Observe / Monitor → Assess → Decide → Adapt / Repair → Verify → Promote / Rollback**

### 8.1 Monitor

C3 continuously or periodically observes incoming model data.

The monitoring layer can track:

- feature distribution changes,
- missingness,
- out-of-range values,
- prediction-distribution changes,
- selected data-quality indicators.

Candidate shift detectors include:

- PSI,
- Kolmogorov–Smirnov (KS),
- Wasserstein distance if needed.

The implementation should not use every possible detector. A small set of justified detectors is preferable.

A feasible core configuration is:

- PSI or KS for selected numerical features,
- missingness-rate monitoring,
- prediction-distribution monitoring.

---

# 9. C3 must distinguish types of shift

The project should not call every distribution change "concept drift."

### Covariate shift

The input distribution changes:

\[
P(X) \text{ changes}
\]

Example:

The proportion of children receiving a particular dietary pattern changes.

### Label shift

The class distribution changes:

\[
P(Y) \text{ changes}
\]

Example:

The proportion of MAM/SAM cases changes.

### Concept shift

The relationship between inputs and outcomes changes:

\[
P(Y|X) \text{ changes}
\]

This generally requires outcome labels or an appropriate delayed evaluation process.

Therefore, PSI/KS alone cannot establish that concept drift has occurred.

---

# 10. Reliability impact assessment

This is the key layer separating C3 from a simple drift detector.

Suppose PSI says:

> "Dietary-diversity feature has shifted."

C3 must **not** immediately retrain.

Instead it asks:

> "Did this shift actually cause model reliability to deteriorate?"

When outcome labels are available, C3 can evaluate:

### Predictive performance

Depending on the task:

- F1,
- recall,
- AUPRC,
- AUROC.

For the malnutrition application, class-specific recall—especially for clinically important minority classes—may be particularly important.

### Calibration

Possible metrics:

- Expected Calibration Error (ECE),
- Brier score.

The exact metrics should be finalized according to C1's final target and class distribution.

### Delayed-label reality

In real deployment, outcome labels may not be immediately available.

Therefore:

- **Immediate monitoring:** detects possible shift/data-quality problems.
- **Delayed evaluation:** once reliable labels become available, C3 evaluates actual performance/calibration.

If labels are unavailable, C3 should not claim:

> "The model is definitely failing."

Instead it should report:

> **"Potential reliability risk detected; outcome-based verification pending."**

This distinction is important for a clinically responsible system.

---

# 11. Adaptive maintenance decision mechanism

After monitoring and reliability assessment, C3 selects an action.

The core action set is deliberately small:

### Action 1 — No Action

If:

- a shift is detected,
- but model reliability remains within acceptable limits,

then the system does nothing.

This is important because unnecessary model updates can themselves introduce risk.

### Action 2 — Recalibration

If predictive discrimination remains acceptable but probability calibration deteriorates, C3 can generate a recalibrated candidate.

Potential methods:

- temperature scaling,
- Platt scaling,
- isotonic regression.

Only one main recalibration method needs to be selected for the core implementation.

### Action 3 — Retraining

If predictive performance has substantially deteriorated and sufficient labelled data are available, C3 can generate a retrained candidate.

Retraining should be more consequential than recalibration and therefore should have a stronger verification gate.

### Action 4 — Hold / Human Review

If:

- the evidence is ambiguous,
- data quality is severely compromised,
- there is insufficient labelled data,
- or the candidate fails safety criteria,

the system can enter a HOLD state rather than making an automatic update.

---

# 12. Least-invasive maintenance principle

C3 should prefer the smallest intervention capable of restoring acceptable reliability.

Conceptually:

\[
a^* =
\arg\min_{a\in A} \text{AdaptationCost}(a)
\]

subject to:

\[
\text{Reliability}(M_a) \geq \tau
\]

where:

- \(A\) = available maintenance actions,
- \(a\) = candidate action,
- \(M_a\) = model after applying the action,
- \(\tau\) = minimum acceptable reliability threshold.

This should be presented as a **design principle**, not as evidence that the project is building a sophisticated learned optimization policy.

The practical hierarchy is:

> No modification → Recalibration → More substantial adaptation/retraining → Hold/human review

depending on the evidence.

---

# 13. Candidate model generation

C3 does not directly overwrite the active C1 model.

Suppose:

> **C1 v1.0 = current active model**

C3 detects harmful degradation.

It then generates:

> **Candidate v1.1**

or, for a more substantial retraining event:

> **Candidate v2.0**

The candidate is evaluated before becoming active.

This creates a separation between:

- **active production/reference model**
- **candidate maintenance model**

---

# 14. Verification gate

This is one of the most important parts of C3.

The candidate must be evaluated using data that were **not used to perform the adaptation**.

The basic flow is:

```text
Current model
      ↓
Shift detected
      ↓
Reliability degradation confirmed
      ↓
Choose maintenance action
      ↓
Generate candidate model
      ↓
Evaluate on untouched verification set
      ↓
 ┌───────────────┴───────────────┐
 PASS                           FAIL
  ↓                              ↓
Promote candidate          Reject candidate
  ↓                              ↓
New active model            Retain / rollback
```

A candidate should only be promoted if it satisfies predefined criteria such as:

- acceptable predictive performance,
- acceptable calibration,
- acceptable minority-class performance,
- no unacceptable degradation on the protected/verification set.

This prevents C3 from becoming an uncontrolled automatic retraining system.

---

# 15. Bounded autonomy

The system can be described as **bounded-autonomous** rather than fully autonomous.

C3 can autonomously:

1. monitor data,
2. detect predefined shifts,
3. assess reliability when labels are available,
4. select from predefined maintenance actions,
5. generate a candidate,
6. verify the candidate,
7. promote the candidate if predefined safety criteria are met,
8. reject/rollback if the candidate fails.

C3 does **not**:

- invent new maintenance algorithms,
- change clinical definitions arbitrarily,
- continuously rewrite itself,
- deploy arbitrary models without validation,
- make clinical treatment decisions.

The autonomy is therefore bounded by:

- predefined detectors,
- predefined thresholds,
- predefined maintenance actions,
- predefined verification criteria.

This is a much safer and more defensible interpretation of "autonomous maintenance."

---

# 16. Experimental design

The strongest core experiment compares four strategies.

## Strategy A — Static model

The C1 model is trained once and never updated.

This represents the baseline:

> "Deploy once and leave it alone."

## Strategy B — Always recalibrate

Whenever the predefined shift condition occurs, recalibration is performed.

This tests a simple fixed maintenance strategy.

## Strategy C — Always retrain

Whenever the predefined shift condition occurs, the model is retrained.

This represents an aggressive maintenance strategy.

## Strategy D — Proposed adaptive maintenance

The proposed system:

> Monitor → Assess → Decide → Adapt → Verify → Promote/Rollback.

This tests whether intelligent maintenance decisions outperform indiscriminate maintenance.

---

# 17. Main C3 hypothesis

> **An adaptive maintenance decision mechanism can recover model reliability under harmful distribution shifts while producing fewer unnecessary interventions than indiscriminate recalibration or retraining.**

This gives C3 a measurable research contribution.

The research is therefore not:

> "We made a drift detector."

It is:

> **"We designed and evaluated a closed-loop mechanism for deciding when model maintenance is necessary, what level of maintenance is appropriate, and whether the resulting model is safe to promote."**

---

# 18. Shift/stress-test design

Because the available historical dataset is only a small number of annual cross-sectional snapshots, C3 should not pretend that it has a continuous real-world data stream.

A defensible evaluation can combine:

### Tier A — Real annual variation

Use available annual Nutrition Month data to demonstrate that distributions can vary across cohorts/years where comparable variables exist.

This is auxiliary evidence, not proof that the rich 2026 C1 model is historically validated.

### Tier B — Controlled stress testing

Use the 2026 dataset as a controlled testbed.

Apply systematic, clinically/plausibly motivated perturbations to create known distribution-shift scenarios.

### Tier C — Maintenance comparison

Run the static, always-recalibrate, always-retrain and proposed adaptive maintenance strategies under those scenarios.

---

# 19. Stress-test taxonomy

Avoid creating arbitrary random perturbations.

Use a small number of systematic categories.

## A. Data-quality degradation

Examples:

- increased missingness in dietary variables,
- measurement noise,
- out-of-range or corrupted values.

## B. Covariate shift

Change the distribution of selected input variables.

Examples:

- demographic composition,
- household characteristics,
- dietary patterns.

## C. Label/prevalence shift

Change class prevalence in evaluation data.

Example:

- increased proportion of MAM/SAM cases.

## D. Operational shift

Simulate changes in data collection.

Examples:

- a feature becomes unavailable,
- one field has systematically higher missingness,
- a collection procedure changes.

One or two well-designed scenarios per category are sufficient for the core study.

### Concept shift

A genuine change in \(P(Y|X)\) is more difficult to simulate convincingly and requires careful interpretation.

It should therefore be treated as a stretch experiment rather than the core claim.

---

# 20. C3 evaluation metrics

The metrics should remain focused.

## Shift monitoring

Potential metrics:

- PSI,
- KS,
- missingness rate,
- optionally Wasserstein distance.

## Model reliability

Potential metrics:

- F1,
- recall,
- AUPRC/AUROC where appropriate,
- ECE,
- Brier score.

## Maintenance effectiveness

Potential metrics:

- reliability recovery,
- unnecessary intervention rate,
- failed adaptation rate,
- rollback success rate,
- maintenance frequency/cost.

A useful recovery concept is:

\[
Recovery =
\frac{Performance_{after}-Performance_{degraded}}
{Performance_{original}-Performance_{degraded}}
\]

The exact interpretation must be adapted for metrics where lower values are better, such as calibration error.

---

# 21. What makes C3 novel

The novelty should **not** be presented as:

> "We invented a new drift detector."

or:

> "We invented a new retraining algorithm."

Instead:

> **The contribution is the integration of distribution-shift monitoring, reliability assessment, adaptive maintenance-action selection, candidate-model verification, and safe model promotion/rollback into a closed-loop model-maintenance framework for childhood malnutrition prediction.**

A supervisor-friendly version:

> **"Our novelty is not a new drift-detection or model-training algorithm. It is the integration of distribution-shift monitoring, reliability assessment, adaptive model maintenance and safety-gated model promotion into a closed-loop system that can autonomously maintain the deployed prediction model."**

The contribution becomes stronger because the system answers all of these questions:

1. Did the data change?
2. Does that change actually matter?
3. Does the model's reliability deteriorate?
4. What is the least-invasive appropriate response?
5. Did the response actually repair the problem?
6. Is the updated model safe enough to promote?
7. If not, can the system reject/rollback it?

---

# 22. Why C3 is independent from C1

A simple explanation:

> **C1 is the prediction system; C3 is the model-maintenance system around it.**

C1 asks:

> **"What is this child's risk/status?"**

C3 asks:

> **"Can we still trust this prediction model under changing data, and if not, how should we safely update it?"**

C1 can therefore be evaluated on ordinary predictive performance.

C3 is evaluated on:

- detecting harmful shifts,
- distinguishing harmless shifts from harmful ones,
- choosing maintenance actions,
- recovering reliability,
- avoiding unnecessary updates,
- safely promoting or rejecting candidates.

---

# 23. Important limitations and honest claims

### Limited temporal depth

Only approximately four to five annual snapshots are expected historically.

Therefore, the project should not claim to have a genuine continuous data stream.

### Cross-sectional historical records

Historical Nutrition Month data are not guaranteed to follow the same children year after year.

Therefore, they should not be described as a longitudinal child-growth dataset unless the actual records establish that linkage.

### Limited geographic diversity

The available MOH areas are concentrated geographically.

Therefore, C3 should not claim nationwide spatial robustness from these records.

### Rich predictors are mainly 2026

Historical records may not contain the same maternal/dietary variables as 2026.

Therefore, historical annual data should not be presented as if they were the same feature space as the rich C1 training dataset.

### Synthetic stress testing

Controlled shift injection is a simulation, not real deployment evidence.

The correct wording is:

> "controlled stress testing designed to evaluate maintenance behavior under plausible distribution shifts."

Not:

> "we reproduced real-world concept drift."

### No live clinical deployment

The project should demonstrate the maintenance loop in a controlled research environment.

It should not claim that the system is ready for unsupervised clinical deployment.

---

# 24. Recommended seven-week implementation scope

## Week 1

- Finalize C3 architecture.
- Define shift scenarios.
- Define candidate metrics.
- Build shift-injection framework.
- Coordinate with C1 regarding model interface.
- Prioritize identification/digitization of sufficient MAM/SAM cases.

## Week 2

- Finish shift-injection engine.
- Implement initial PSI/KS/missingness monitoring.
- Establish the C1 model handoff.
- Freeze the first stable C1 baseline.

## Week 3

- Run controlled scenarios through the frozen C1 model.
- Measure distribution shifts.
- Record resulting predictive/calibration degradation.

## Week 4

- Analyze relationship between shift and reliability degradation.
- Establish initial maintenance decision conditions.
- Implement main recalibration method.

## Week 5

- Implement adaptive maintenance decision mechanism.
- Implement retraining candidate generation.
- Compare no-action/recalibration/retraining conditions.

## Week 6

- Implement untouched-set verification.
- Implement promotion/rejection.
- Implement rollback/retention behavior.
- Run the complete closed loop.

## Week 7

- Run final experiments.
- Compare all maintenance strategies.
- Calculate safety and maintenance metrics.
- Integrate with the overall prototype.
- Prepare demonstration and research documentation.

---

# 25. Core versus stretch scope

## Core

- PSI/KS/missingness monitoring.
- A small number of systematic shift scenarios.
- Reliability impact assessment.
- No Action / Recalibrate / Retrain decision mechanism.
- Candidate model generation.
- Untouched verification set.
- Promotion/rejection.
- Rollback/retention.
- Comparison against static and fixed maintenance baselines.
- Reliability and maintenance metrics.

## Stretch

- Reweighting or other limited adaptation.
- Streaming simulation.
- Automated verification service.
- Dashboard.
- Additional shift detectors.
- Fairness/subgroup monitoring.
- More sophisticated candidate adaptation.

## Out of scope

- Reinforcement-learning maintenance policy.
- Learned meta-policy for maintenance.
- Fully unrestricted autonomous model rewriting.
- Live clinical deployment.
- Continuous unsupervised learning in production.
- Claims of nationwide robustness from limited local data.

---

# 26. Potential supervisor questions and answers

## "Isn't C3 just a drift detector?"

**Answer:**

> "No. Drift detection is only the monitoring stage. C3 additionally determines whether the detected shift is associated with actual reliability degradation, selects an appropriate maintenance action, generates a candidate model, verifies it on untouched data, and promotes or rejects it. Therefore the research unit is the complete closed-loop maintenance framework."

## "Why not just retrain every time?"

**Answer:**

> "Because a distribution shift does not necessarily mean the model has become unreliable. Retraining unnecessarily can consume resources and can also introduce a new model that performs worse. We therefore compare always-retrain against our adaptive mechanism, which only intervenes when reliability evidence justifies it."

## "How does the system know what action to choose?"

**Answer:**

> "The actions are predefined rather than arbitrary. We first establish through controlled experiments how different shift conditions affect reliability. If reliability remains within the acceptable range, no update is performed. If mainly calibration deteriorates, recalibration is attempted. If predictive performance substantially deteriorates and sufficient labelled data exist, retraining is considered. Every modification must then pass the verification gate."

## "What if you detect drift but have no labels?"

**Answer:**

> "The system can detect a potential shift without labels, but it cannot honestly claim that predictive performance has deteriorated. It therefore records a potential reliability risk and waits for delayed outcome labels or performs the appropriate offline audit before making a consequential maintenance decision."

## "Why is C3 separate from C1?"

**Answer:**

> "C1 builds the prediction model. C3 manages the lifecycle of that model after it has been developed. C1 answers what the child risk is; C3 answers whether the model remains reliable and how to safely maintain it when conditions change."

## "Is this fully autonomous?"

**Answer:**

> "It is bounded autonomous maintenance, not unrestricted autonomy. The system can select and execute predefined maintenance actions and promote a candidate only when predefined verification criteria are satisfied. It cannot invent arbitrary model changes or bypass safety checks."

## "Where is the novelty?"

**Answer:**

> "The novelty is the closed-loop integration of shift monitoring, reliability assessment, adaptive maintenance selection, candidate-model verification and safe promotion/rollback for the childhood malnutrition prediction setting. The contribution is the maintenance mechanism and its empirical evaluation, rather than a claim of inventing a new individual drift detector or training algorithm."

---

# 27. One-paragraph final description for the research proposal

> **Component 3: Adaptive Model Reliability Monitoring and Safe Maintenance Framework** develops a closed-loop maintenance mechanism for the childhood malnutrition prediction model produced by Component 1. The framework monitors incoming data for distribution shifts, data-quality degradation and changes in prediction behavior, but does not assume that every detected shift represents model failure. It therefore performs a separate reliability assessment using predictive-performance and calibration measures when outcome labels are available. Based on the observed shift and reliability impact, an adaptive maintenance decision mechanism selects the least-invasive appropriate response, ranging from no action to probability recalibration or retraining. Any modified model is treated as a candidate and evaluated on an untouched verification set using predefined reliability and safety criteria. Only candidates that satisfy these criteria are promoted as the new active model; otherwise, the update is rejected and the previous model is retained or restored. The component will be evaluated against static, always-recalibrate and always-retrain baselines under real annual variation where available and controlled, plausible distribution-shift scenarios. The primary contribution is therefore a bounded-autonomous, closed-loop model-maintenance framework that aims to recover reliability from harmful data changes while reducing unnecessary model interventions and preventing unsafe model updates.

---

# 28. Final project architecture

```text
                 ┌─────────────────────────────┐
                 │ Component 1                  │
                 │ Child Malnutrition           │
                 │ Risk / Status Prediction     │
                 └──────────────┬──────────────┘
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │ Component 2                  │
                 │ Counterfactual Intervention  │
                 │ & Recommendation Engine      │
                 └─────────────────────────────┘


                 ┌─────────────────────────────┐
                 │ Component 3                  │
                 │ Adaptive Model Reliability   │
                 │ Monitoring & Safe Maintenance│
                 └──────────────┬──────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
          Monitor            Assess             Decide
              │                 │                 │
              └─────────────────┼─────────────────┘
                                ▼
                           Adapt / Repair
                                │
                                ▼
                             Verify
                         ┌──────┴──────┐
                         ▼             ▼
                      Promote       Reject
                         │             │
                         ▼             ▼
                   New active      Retain/
                     model         rollback


                 ┌─────────────────────────────┐
                 │ Component 4                  │
                 │ Spatio-Temporal Burden       │
                 │ Forecasting & Resource      │
                 │ Demand Visualization         │
                 └─────────────────────────────┘
```

## 29. Key principle to remember

> **C1 predicts the child. C2 recommends what can be changed. C3 maintains the prediction model. C4 forecasts population-level need.**

That separation should remain consistent throughout the proposal, implementation, evaluation and final presentation.

## 30. Official Sri Lankan references used for project context

- Family Health Bureau — Child Nutrition Unit: https://fhb.health.gov.lk/technical-units/child-nutrition
- Family Health Bureau — Child Nutrition Unit resources: https://fhb.health.gov.lk/index.php/resources?units%5B0%5D=child-nutrition
- Family Health Bureau — Child Nutrition Unit circulars/resources: https://fhb.health.gov.lk/resources?type=circular&units%5B0%5D=child-nutrition

These official resources document the Child Nutrition Unit's role, annual Nutrition Month surveys, child-nutrition forms, Nutrition Month reports, and the Sri Lankan manual on management of severe and moderate acute undernutrition.
