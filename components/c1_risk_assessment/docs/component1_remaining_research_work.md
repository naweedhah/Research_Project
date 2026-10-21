# Component 1 remaining research work

This list is research and evaluation work. It is not a production-code defect list and must not be “fixed” by changing GA-RGCA weights, thresholds, or unvalidated WHO formulas.

## WHO reference assessment

The repository does not contain a validated authoritative HAZ / WAZ / WHZ implementation for this prototype. Do not invent WHO z-score formulas in the application. Do not feed newly derived WHO features into GA-RGCA.

## External clinical validation

GA-RGCA v3 is a research decision-support prototype. `clinical_use` remains false. External clinical validation is not complete.

## Prospective validation

A prospective clinic study is still required before any claim of deployment readiness.

## SAM safety threshold research

Incident SAM sample size and SAM sensitivity remain research limitations. Do not retune production thresholds without a documented threshold-stability study.

## No-prior-label model comparison

Full versus NoPriorLabels comparison belongs in notebook / paper analysis, not in the serving path.

## Age subgroup improvement

Youngest age-band weakness should be studied with subgroup metrics. The application does not invent a new clinical age policy when metadata has no validated deployment limits.

## Source / domain validation

CHDR grouping, source-domain generalisation, calibration plots, decision-curve analysis, reliability-gate ablations, and statistical significance remain notebook work.

## Future product enhancements

- Optional clinician review decision stored separately from model output, if a dedicated schema is added later.
- Growth-chart replacement or reduction of the 3D body visualisation, without presenting the avatar as diagnostic.
- Deeper modality-completeness analytics if a dedicated completeness contract is defined.
