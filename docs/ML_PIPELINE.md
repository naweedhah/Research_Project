# ML pipeline

```
Data
 → preprocessing (train-only impute/scale; group-aware split by child)
 → baselines (Random Forest, XGBoost, LightGBM, Concatenation MLP)
 → proposed multimodal Cross-Attention
 → calibration (temperature scaling)
 → inference adapters
 → longitudinal tracking (e_t, Risk Velocity, UMAP/PCA projection)
```

## Feature sets

`packages/contracts/feature_sets.yaml`

- **current_status** may use contemporaneous anthropometry.
- **early_risk** forbids variables that deterministically define the target.

Automated checks live in `ml/preprocessing/pipeline.py` and `ml/tests/test_leakage.py`.

## Proposed architecture

Four modality encoders (MLP; dietary may use a TabNet-style attentive branch) produce embeddings of dimension 64 or 128. A learnable fusion query attends over the four tokens (multi-head attention) and yields fused `e_t`. Separate heads predict type/status, severity and risk.

This design is technically defensible. Superiority versus concatenation MLP is an empirical question and is not claimed a priori.

## Commands

```bash
python -m ml.training.train_baselines
python -m ml.training.train_multimodal
python -m ml.evaluation.compare_models
python -m ml.trajectory.fit_projection
```

Random seeds are set from YAML configs. Non-deterministic pieces (UMAP, some GPU reductions) are documented in training logs.
