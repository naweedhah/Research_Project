# Longitudinal trajectory

## Latent vectors

Each visit stores `e_t` (64 or 128-d) with `embedding_space_id` and model version. Incompatible spaces are not silently plotted together. The UI shows:

**Model version changed — latent trajectory restarted/re-aligned**

## Risk Velocity

```
RV_t = (R_(t-1) - R_t) / elapsed_months
```

`R_t` is the configured **calibrated** risk. Positive RV is decreasing risk (improvement). The zero-tolerance is `stagnation_threshold` from `clinical_policy_versions` (demo: Research / Demo Configuration).

Zero-day intervals are rejected. Missing risk is not calculated.

## Baseline recovery rate

```
(R_0 - R_t) / elapsed_months_from_baseline
```

## Projection

PCA is the transparent 2D reference. UMAP is exploratory. Aligned UMAP is supported in the research pipeline when practical.

**Do not use t-SNE/UMAP position to make clinical decisions.** Operational alerts come from calibrated risk and longitudinal metrics.
