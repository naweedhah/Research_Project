# C2 supervisor validation report

Research demonstration only. All child inputs are invented software fixtures.
Genuine C1 inference is separate from simulated C2 acceptance; neither is clinical validation.

## Standalone algorithms

- Case: synthetic_24m; test ID: SYNTHETIC-C2-24M; budget: LKR 1500 weekly.
- Exact model-input SHA-256: `1e8772e03f08e0a57c558bad3113be6ee7bd7634bbecf3a680e7b757b1edcefa`; budget is excluded from model input.
- Research-test cards: 3; genuine C1 required: False.
- bounded_search: 3 test-eligible, 0 rejected or unresolved; source SIMULATED_TEST_ONLY.
- dice: 1 test-eligible, 0 rejected or unresolved; source SIMULATED_TEST_ONLY.
- face_graph: 3 test-eligible, 0 rejected or unresolved; source SIMULATED_TEST_ONLY.
- Rank 1: {'dietary_diversity': 'More than 5 varieties'}; methods bounded_search, face_graph; Eligible in Research Test only.
- Rank 2: {'meal_frequency': '4+ meals/day'}; methods bounded_search, face_graph; Eligible in Research Test only.
- Rank 3: {'meal_frequency': '4+ meals/day', 'dietary_diversity': 'More than 5 varieties'}; methods bounded_search, dice, face_graph; Eligible in Research Test only.

## Food cost and schedule

Shopping quantities are household price scenarios, not child portions or treatment plans.
- #1 Egg and greens example: LKR 716.12 / weekly; within_budget; 7 illustrative days; 4 reviewed food groups.
- #2 Fish and fruit example: LKR 846.63 / weekly; within_budget; 7 illustrative days; 4 reviewed food groups.
- #3 Essentials example: LKR 238.48 / weekly; within_budget; 7 illustrative days; 3 reviewed food groups.
- #4 Varied groups example: LKR 1713.08 / weekly; above_budget; 7 illustrative days; 6 reviewed food groups.
- Prices: DCS Colombo District reference records; Kalmunai prices and local availability are unverified.

## Genuine GA-RGCA-v3 inference

- C1 status: verified; model: GA-RGCA-v3; source: GA-RGCA-v3; clinical use: False.
- Baseline: Stunting; severity Normal; uncertainty True; underweight 0.000100; stunting 0.111800; acute {'Normal': 0.988, 'MAM': 0.0118, 'SAM': 0.0002}.
- Candidate 1: {'meal_frequency': {'from': '3 meals/day', 'to': '4+ meals/day'}}; only feeding fields changed: True.
  - Actual prediction: Stunting; severity Normal; uncertainty True; underweight 0.000100; stunting 0.111900; acute {'Normal': 0.9872, 'MAM': 0.0126, 'SAM': 0.0002}.
  - Probability deltas: {'underweight': 0.0, 'stunting': 0.0001, 'acute': {'Normal': -0.0008, 'MAM': 0.0008, 'SAM': 0.0}}.
  - Model-policy result: rejected; reasons: stunting_probability increases; MAM model probability increases; no approved categorical improvement.
  - Unresolved evidence: model uncertainty requires review; real-mode research authorization has not been supplied; individual clinical suitability and local availability are unknown; reviewed feeding practice and intervention affordability are unavailable.
- Candidate 2: {'dietary_diversity': {'from': '2 to 5 varieties', 'to': 'More than 5 varieties'}}; only feeding fields changed: True.
  - Actual prediction: Stunting; severity Normal; uncertainty True; underweight 0.000100; stunting 0.093700; acute {'Normal': 0.9877, 'MAM': 0.0121, 'SAM': 0.0003}.
  - Probability deltas: {'underweight': 0.0, 'stunting': -0.0181, 'acute': {'Normal': -0.0003, 'MAM': 0.0003, 'SAM': 0.0001}}.
  - Model-policy result: rejected; reasons: MAM model probability increases; SAM model probability increases; no approved categorical improvement.
  - Unresolved evidence: model uncertainty requires review; real-mode research authorization has not been supplied; individual clinical suitability and local availability are unknown; reviewed feeding practice and intervention affordability are unavailable.
- Candidate 3: {'meal_frequency': {'from': '3 meals/day', 'to': '4+ meals/day'}, 'dietary_diversity': {'from': '2 to 5 varieties', 'to': 'More than 5 varieties'}}; only feeding fields changed: True.
  - Actual prediction: Stunting; severity Normal; uncertainty True; underweight 0.000000; stunting 0.102500; acute {'Normal': 0.9878, 'MAM': 0.0119, 'SAM': 0.0003}.
  - Probability deltas: {'underweight': -0.0001, 'stunting': -0.0093, 'acute': {'Normal': -0.0002, 'MAM': 0.0001, 'SAM': 0.0001}}.
  - Model-policy result: rejected; reasons: MAM model probability increases; SAM model probability increases; no approved categorical improvement.
  - Unresolved evidence: model uncertainty requires review; real-mode research authorization has not been supplied; individual clinical suitability and local availability are unknown; reviewed feeding practice and intervention affordability are unavailable.

## Remaining research boundaries

- No real-mode C2 research authorization or treatment-effect evidence was supplied.
- Individual clinical suitability, programme eligibility, feeding practice, local availability and household affordability require independent review.
- Run verification: `py -m pytest components/c2_counterfactual_intervention/tests -q`; in the dashboard run `npm.cmd test -- --run` and `npm.cmd run build`.
