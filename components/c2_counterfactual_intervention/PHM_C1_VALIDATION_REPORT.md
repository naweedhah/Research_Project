# PHM / GA-RGCA-v3 model comparison audit

Research model sensitivity only; no intervention or clinical approval.
The source workbook does not establish direct observation of the feeding fields.

- Source: `PHM_prediction_2025_to_2026.xlsx`; SHA-256 `04c4bd1a396d39891668f21035eeab4e3c5ddd3400b8e2d3fd633ae33912a97b`.
- Scan order: 2025 source risk first; complete eligible cohort: True.
- Linked profiles: 1542; technically eligible: 1042.
- Genuine C1 baselines: 1042; candidates: 2837.
- Improvement signals: 2631; model-rule passes: 3 across 2 profiles.
- Mixed trade-offs: 2256; candidates with worsening: 2462.
- Uncertainty exclusions: 84; research-authorized: 0; feasibility unresolved: 2837.
- Candidate model-rule pass rate: 0.1057%; denominator 2837 evaluated candidates.
- Eligible-profile model-rule pass rate: 0.1919% across 1042 eligible profiles.
- Exclusion counts can overlap: {"age_outside_6_59_or_missing": 160, "feeding_category_incompatible": 291, "historical_growth_missing": 14, "implausible_historical_growth": 11, "link_not_good": 202, "no_upward_feeding_category": 64}.

## Reproducible comparison examples

### TC01 — model-rule-passing candidate, if found

- Case alias: `PHM-LOCAL-0118`; model `GA-RGCA-v3`; source feeding observation status **unverified**.
- Feeding change: {"dietary_diversity": {"from": "Less than 2 varieties", "to": "2 to 5 varieties"}}.
- Baseline probabilities (underweight, stunting, MAM, SAM): (0.1025, 0.0399, 0.1201, 0.0004).
- Candidate probabilities (same order): (0.0612, 0.0366, 0.1131, 0.0004).
- Type / severity / uncertainty: Underweight / Moderate / False → Normal / Moderate / False.
- Probability deltas: {"MAM": -0.007, "SAM": 0.0, "stunting": -0.0033, "underweight": -0.0413}.
- Model-rule pass: True; reasons: none at model-comparison stage.
- Research authorization, individual suitability, local availability and household affordability remain unresolved.
- Case alias: `PHM-LOCAL-0118`; model `GA-RGCA-v3`; source feeding observation status **unverified**.
- Feeding change: {"dietary_diversity": {"from": "Less than 2 varieties", "to": "2 to 5 varieties"}, "meal_frequency": {"from": "3 meals/day", "to": "4+ meals/day"}}.
- Baseline probabilities (underweight, stunting, MAM, SAM): (0.1025, 0.0399, 0.1201, 0.0004).
- Candidate probabilities (same order): (0.0467, 0.0364, 0.1159, 0.0004).
- Type / severity / uncertainty: Underweight / Moderate / False → Normal / Moderate / False.
- Probability deltas: {"MAM": -0.0042, "SAM": 0.0, "stunting": -0.0035, "underweight": -0.0558}.
- Model-rule pass: True; reasons: none at model-comparison stage.
- Research authorization, individual suitability, local availability and household affordability remain unresolved.
- Case alias: `PHM-LOCAL-0139`; model `GA-RGCA-v3`; source feeding observation status **unverified**.
- Feeding change: {"dietary_diversity": {"from": "Less than 2 varieties", "to": "2 to 5 varieties"}}.
- Baseline probabilities (underweight, stunting, MAM, SAM): (0.9838, 0.377, 0.5063, 0.0028).
- Candidate probabilities (same order): (0.9701, 0.3663, 0.4963, 0.0028).
- Type / severity / uncertainty: MAM / Moderate / False → Underweight / Moderate / False.
- Probability deltas: {"MAM": -0.01, "SAM": 0.0, "stunting": -0.0107, "underweight": -0.0137}.
- Model-rule pass: True; reasons: none at model-comparison stage.
- Research authorization, individual suitability, local availability and household affordability remain unresolved.

### TC02 — mixed risk trade-off

- Case alias: `PHM-LOCAL-0001`; model `GA-RGCA-v3`; source feeding observation status **unverified**.
- Feeding change: {"meal_frequency": {"from": "3 meals/day", "to": "4+ meals/day"}}.
- Baseline probabilities (underweight, stunting, MAM, SAM): (0.1485, 0.8445, 0.015, 0.0001).
- Candidate probabilities (same order): (0.1115, 0.8451, 0.0154, 0.0001).
- Type / severity / uncertainty: Stunting / Moderate / False → Stunting / Moderate / False.
- Probability deltas: {"MAM": 0.0004, "SAM": 0.0, "stunting": 0.0006, "underweight": -0.037}.
- Model-rule pass: False; reasons: stunting_probability increases; MAM model probability increases; stunting_probability worsens.
- Research authorization, individual suitability, local availability and household affordability remain unresolved.

### TC03 — worsening without an improvement signal

- Case alias: `PHM-LOCAL-0047`; model `GA-RGCA-v3`; source feeding observation status **unverified**.
- Feeding change: {"meal_frequency": {"from": "3 meals/day", "to": "4+ meals/day"}}.
- Baseline probabilities (underweight, stunting, MAM, SAM): (0.0001, 0.5151, 0.004, 0.0001).
- Candidate probabilities (same order): (0.0001, 0.5158, 0.0041, 0.0001).
- Type / severity / uncertainty: Stunting / Moderate / False → Stunting / Moderate / False.
- Probability deltas: {"MAM": 0.0001, "SAM": 0.0, "stunting": 0.0007, "underweight": 0.0}.
- Model-rule pass: False; reasons: stunting_probability increases; MAM model probability increases; stunting_probability worsens.
- Research authorization, individual suitability, local availability and household affordability remain unresolved.

### TC04 — uncertain model comparison

- Case alias: `PHM-LOCAL-0002`; model `GA-RGCA-v3`; source feeding observation status **unverified**.
- Feeding change: {"dietary_diversity": {"from": "2 to 5 varieties", "to": "More than 5 varieties"}}.
- Baseline probabilities (underweight, stunting, MAM, SAM): (0.0001, 0.8459, 0.008, 0.0002).
- Candidate probabilities (same order): (0.0001, 0.8399, 0.0087, 0.0003).
- Type / severity / uncertainty: Stunting / Moderate / True → Stunting / Severe / True.
- Probability deltas: {"MAM": 0.0007, "SAM": 0.0001, "stunting": -0.006, "underweight": 0.0}.
- Model-rule pass: False; reasons: predicted severity worsens; MAM model probability increases; SAM model probability increases; model uncertainty requires review.
- Research authorization, individual suitability, local availability and household affordability remain unresolved.

## Additional existing software checks

- TC05: The standalone budget sensitivity test changes illustrative food affordability without changing model input or prediction.
- TC06: The five-month fixture is excluded from complementary-feeding candidate generation and C1 comparison.
- Full input snapshots and outputs are retained only in the local private JSON supplied to the discovery command; no source names, identifiers, or raw rows are published here.
- `allow_demo=false`; each candidate request preserves every non-feeding input. The C1 adapter checks GA-RGCA-v3/PYTORCH provenance and returned feeding/history fields.
- This audit does not establish a causal feeding benefit, independently observed feeding inputs, authorized research use, clinical suitability, or Kalmunai affordability.
