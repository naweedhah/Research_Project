# ============================================================
# STEP 17 - TUNED MODEL REVALIDATION
# Childhood Malnutrition Forecasting Research
#
# Revalidates tuned RF/XGBoost/LightGBM/NGBoost + tuned TFT
# on untouched 2024 using strict rolling-origin methodology.
# SARIMA, LSTM and Seasonal Naive strict Step-15 results are
# retained as references. 2025 is never loaded.
# ============================================================

from pathlib import Path
import warnings, json, random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from ngboost import NGBRegressor
from ngboost.distns import Normal
from ngboost.scores import LogScore

import torch
import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.data import GroupNormalizer, NaNLabelEncoder
from pytorch_forecasting.metrics import QuantileLoss

warnings.filterwarnings("ignore")
RANDOM_STATE = 42
HORIZONS = [1, 3, 6]
TABULAR_TARGET = "Forecast_Target"
TFT_TARGET = "Malnutrition_Cases"
DISTRICT = "District"
DATE = "Date"
ENCODER = 12
PRED_LEN = 6
QUANTILES = [0.025, 0.50, 0.975]
TFT_BATCH = 64
TFT_MAX_EPOCHS = 50
TFT_PATIENCE = 6


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    pl.seed_everything(seed, workers=True)


set_seed(RANDOM_STATE)

BASE_DIR = Path(__file__).resolve().parent.parent
SPLIT_DIR = BASE_DIR / "data" / "splits"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "outputs" / "reports"
FIGURE_DIR = BASE_DIR / "outputs" / "figures"
MODEL_DIR = BASE_DIR / "models" / "step17_tuned_revalidation"
LOG_DIR = BASE_DIR / "outputs" / "logs" / "step17_tft"
for d in [REPORT_DIR, FIGURE_DIR, MODEL_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

STEP16 = REPORT_DIR / "16_selected_hyperparameters.csv"
STEP16B = REPORT_DIR / "16b_tft_selected_hyperparameters.csv"
STEP15 = REPORT_DIR / "15_strict_model_validation_metrics.csv"
STEP15B = REPORT_DIR / "15b_tft_strict_metrics.csv"
TFT_DATA = PROCESSED_DIR / "malnutrition_preprocessed_base.csv"

print("\n" + "=" * 120)
print("STEP 17 - TUNED MODEL REVALIDATION")
print("=" * 120)
print("- Step 16/16B parameters were selected using historical data only")
print("- 2024 is used only for external revalidation")
print("- strict rolling-origin label availability is enforced")
print("- preprocessing is re-fitted at each origin")
print("- 2025 final test data is NOT loaded")


# ------------------------------------------------------------
# Metrics
# ------------------------------------------------------------
def mae(y, p): return float(np.mean(np.abs(y - p)))
def rmse(y, p): return float(np.sqrt(np.mean((y - p) ** 2)))

def wape(y, p):
    den = np.sum(np.abs(y))
    return np.nan if den == 0 else float(np.sum(np.abs(y - p)) / den * 100)

def smape(y, p):
    den = np.abs(y) + np.abs(p)
    ok = den != 0
    return np.nan if ok.sum() == 0 else float(np.mean(2 * np.abs(y[ok] - p[ok]) / den[ok]) * 100)

def r2(y, p):
    ss_res = np.sum((y - p) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return np.nan if ss_tot == 0 else float(1 - ss_res / ss_tot)

def pinball(y, p, q):
    e = y - p
    return float(np.mean(np.maximum(q * e, (q - 1) * e)))

def result_row(df, model, horizon):
    y = df["Actual_Target"].to_numpy(float)
    p = df["Prediction"].to_numpy(float)
    return {
        "Horizon_Months": int(horizon), "Model": model,
        "Validation_Rows": len(df), "MAE": mae(y, p), "RMSE": rmse(y, p),
        "WAPE_Percentage": wape(y, p), "sMAPE_Percentage": smape(y, p), "R2": r2(y, p)
    }


# ------------------------------------------------------------
# Step 16 selected parameters
# ------------------------------------------------------------
if not STEP16.exists():
    raise FileNotFoundError(f"Missing Step 16 selected parameters: {STEP16}")
params_df = pd.read_csv(STEP16)

def selected_params(model, h):
    row = params_df[(params_df["Model"] == model) & (params_df["Horizon_Months"] == h)]
    if len(row) != 1:
        raise ValueError(f"Expected one Step 16 row for {model} H{h}; found {len(row)}")
    return json.loads(row.iloc[0]["Selected_Parameters"])

for m in ["Random Forest", "XGBoost", "LightGBM", "NGBoost"]:
    for h in HORIZONS:
        p = selected_params(m, h)
        print(f"Selected {m} H{h}: {p.get('Config_ID', 'UNKNOWN')}")


# ------------------------------------------------------------
# Strict tabular preprocessing
# ------------------------------------------------------------
def model_matrices(train_df, pred_df, features):
    med = train_df[features].median()
    med.loc[med.isna()] = 0.0
    tr_num = train_df[features].fillna(med).astype(float).reset_index(drop=True)
    pr_num = pred_df[features].fillna(med).astype(float).reset_index(drop=True)
    tr_d = pd.get_dummies(train_df[DISTRICT], prefix="District", dtype=float).reset_index(drop=True)
    pr_d = pd.get_dummies(pred_df[DISTRICT], prefix="District", dtype=float)
    pr_d = pr_d.reindex(columns=tr_d.columns, fill_value=0).reset_index(drop=True)
    Xtr = pd.concat([tr_num, tr_d], axis=1).to_numpy(float)
    Xpr = pd.concat([pr_num, pr_d], axis=1).to_numpy(float)
    ytr = train_df[TABULAR_TARGET].to_numpy(float)
    return Xtr, ytr, Xpr

hdata = {}
for h in HORIZONS:
    tr_path = SPLIT_DIR / f"h{h}_train.csv"
    va_path = SPLIT_DIR / f"h{h}_validation.csv"
    mf_path = REPORT_DIR / f"09_h{h}_usable_feature_manifest.csv"
    for p in [tr_path, va_path, mf_path]:
        if not p.exists(): raise FileNotFoundError(p)
    tr = pd.read_csv(tr_path)
    va = pd.read_csv(va_path)
    mf = pd.read_csv(mf_path)
    for df in [tr, va]:
        df["Forecast_Origin_Date"] = pd.to_datetime(df["Forecast_Origin_Date"])
        df["Forecast_Target_Date"] = pd.to_datetime(df["Forecast_Target_Date"])
    tr = tr[tr[TABULAR_TARGET].notna()].copy()
    va = va[va[TABULAR_TARGET].notna()].copy()
    if not va["Forecast_Target_Date"].dt.year.eq(2024).all():
        raise AssertionError(f"H{h}: validation target dates are not all 2024")
    features = mf["Feature"].tolist()
    if len(features) != 153:
        raise ValueError(f"H{h}: expected 153 features, found {len(features)}")
    both = pd.concat([tr, va], ignore_index=True).sort_values(["Forecast_Origin_Date", DISTRICT]).reset_index(drop=True)
    hdata[h] = {"validation": va, "all": both, "features": features}
    print(f"H{h}: train={len(tr)}, validation={len(va)}, features={len(features)}")


def rf_model(p):
    return RandomForestRegressor(
        n_estimators=p["n_estimators"], max_depth=p["max_depth"],
        min_samples_split=p["min_samples_split"], min_samples_leaf=p["min_samples_leaf"],
        max_features=p["max_features"], bootstrap=p["bootstrap"],
        random_state=RANDOM_STATE, n_jobs=-1)

def xgb_model(p):
    return XGBRegressor(
        objective="reg:squarederror", n_estimators=p["n_estimators"], max_depth=p["max_depth"],
        learning_rate=p["learning_rate"], subsample=p["subsample"],
        colsample_bytree=p["colsample_bytree"], min_child_weight=p["min_child_weight"],
        reg_lambda=p["reg_lambda"], random_state=RANDOM_STATE, n_jobs=-1, tree_method="hist")

def lgb_model(p):
    return LGBMRegressor(
        objective="regression", n_estimators=p["n_estimators"], learning_rate=p["learning_rate"],
        num_leaves=p["num_leaves"], max_depth=p["max_depth"], min_child_samples=p["min_child_samples"],
        subsample=p["subsample"], colsample_bytree=p["colsample_bytree"], reg_lambda=p["reg_lambda"],
        random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)

def ngb_model(p):
    base = DecisionTreeRegressor(
        criterion="friedman_mse", max_depth=p["tree_depth"],
        min_samples_leaf=p["min_samples_leaf"], random_state=RANDOM_STATE)
    return NGBRegressor(
        Dist=Normal, Score=LogScore, Base=base, natural_gradient=True,
        n_estimators=p["n_estimators"], learning_rate=p["learning_rate"],
        minibatch_frac=1.0, col_sample=1.0, verbose=False, random_state=RANDOM_STATE)

factories = {
    "Random Forest": rf_model, "XGBoost": xgb_model,
    "LightGBM": lgb_model, "NGBoost": ngb_model,
}

print("\n" + "=" * 120)
print("1. TUNED TABULAR MODELS - 2024 STRICT REVALIDATION")
print("=" * 120)

pred_records, ngb_unc_records = [], []
for m, factory in factories.items():
    print("\n" + "-" * 120)
    print(f"TUNED {m.upper()}")
    print("-" * 120)
    for h in HORIZONS:
        va, all_df, features = hdata[h]["validation"], hdata[h]["all"], hdata[h]["features"]
        p = selected_params(m, h)
        cid = p.get("Config_ID", "UNKNOWN")
        origins = sorted(va["Forecast_Origin_Date"].unique())
        for i, origin in enumerate(origins, 1):
            rows = va[va["Forecast_Origin_Date"] == origin].copy()
            train_pool = all_df[all_df["Forecast_Target_Date"] <= origin].copy()
            Xtr, ytr, Xpr = model_matrices(train_pool, rows, features)
            model = factory(p)
            model.fit(Xtr, ytr)
            preds = model.predict(Xpr)
            if m == "NGBoost":
                dist = model.pred_dist(Xpr)
                sd = np.maximum(np.asarray(dist.params["scale"], float), 1e-8)
                mu = np.asarray(dist.params["loc"], float)
                z = norm.ppf(0.975)
                lo, hi = mu - z * sd, mu + z * sd
            print(f"{m} H{h} origin {i}/{len(origins)} | {pd.Timestamp(origin).date()} | train={len(train_pool)}")
            for j, (_, row) in enumerate(rows.iterrows()):
                actual = float(row[TABULAR_TARGET])
                rec = {
                    "Model": "Tuned " + m, "Horizon_Months": h, "Config_ID": cid,
                    "District": row[DISTRICT], "Forecast_Origin_Date": origin,
                    "Forecast_Target_Date": row["Forecast_Target_Date"],
                    "Actual_Target": actual, "Prediction": float(preds[j])
                }
                pred_records.append(rec)
                if m == "NGBoost":
                    ngb_unc_records.append({**rec, "Predicted_SD": float(sd[j]),
                        "Lower_95": float(lo[j]), "Upper_95": float(hi[j]),
                        "Covered_By_95": bool(lo[j] <= actual <= hi[j])})

pred_df = pd.DataFrame(pred_records)
pred_df.to_csv(REPORT_DIR / "17_tuned_tabular_validation_predictions.csv", index=False)

tab_metric_rows = []
for m in sorted(pred_df["Model"].unique()):
    for h in HORIZONS:
        d = pred_df[(pred_df["Model"] == m) & (pred_df["Horizon_Months"] == h)].copy()
        if len(d) != 300:
            raise ValueError(f"{m} H{h}: expected 300 predictions, found {len(d)}")
        tab_metric_rows.append(result_row(d, m, h))
tab_metrics = pd.DataFrame(tab_metric_rows)
tab_metrics.to_csv(REPORT_DIR / "17_tuned_tabular_validation_metrics.csv", index=False)

ngb_unc_df = pd.DataFrame(ngb_unc_records)
ngb_unc_metrics = []
for h in HORIZONS:
    d = ngb_unc_df[ngb_unc_df["Horizon_Months"] == h].copy()
    if d.empty: continue
    width = d["Upper_95"] - d["Lower_95"]
    y, p, sd = d["Actual_Target"].to_numpy(float), d["Prediction"].to_numpy(float), d["Predicted_SD"].to_numpy(float)
    ngb_unc_metrics.append({
        "Model": "Tuned NGBoost", "Horizon_Months": h,
        "Nominal_Coverage_Percentage": 95.0,
        "Observed_Coverage_Percentage": float(d["Covered_By_95"].mean() * 100),
        "Mean_Interval_Width": float(width.mean()), "Median_Interval_Width": float(width.median()),
        "Negative_Lower_Bounds": int((d["Lower_95"] < 0).sum()),
        "Gaussian_NLL": float(-np.mean(norm.logpdf(y, loc=p, scale=sd)))
    })
ngb_unc_metrics = pd.DataFrame(ngb_unc_metrics)
ngb_unc_metrics.to_csv(REPORT_DIR / "17_tuned_ngboost_uncertainty_metrics.csv", index=False)


# ------------------------------------------------------------
# Step 16B tuned TFT configuration
# ------------------------------------------------------------
if not STEP16B.exists():
    raise FileNotFoundError(f"Missing Step 16B selected TFT parameters: {STEP16B}")
tft_sel = pd.read_csv(STEP16B)
if len(tft_sel) != 1:
    raise ValueError(f"Expected one TFT selected row, found {len(tft_sel)}")
TFT_PARAMS = json.loads(tft_sel.iloc[0]["Selected_Parameters"])
TFT_CONFIG = TFT_PARAMS.get("Config_ID", "UNKNOWN")
print("\nSelected TFT config:")
print(json.dumps(TFT_PARAMS, indent=2))


# ------------------------------------------------------------
# TFT data and helpers
# ------------------------------------------------------------
def safe_columns(df):
    rename = {c: str(c).replace(".", "_") for c in df.columns}
    vals = list(rename.values())
    if len(vals) != len(set(vals)):
        raise ValueError("TFT-safe renaming created duplicate columns")
    return df.rename(columns=rename)

if not TFT_DATA.exists(): raise FileNotFoundError(TFT_DATA)
tft = safe_columns(pd.read_csv(TFT_DATA))
tft[DATE] = pd.to_datetime(tft[DATE])
tft = tft[tft[DATE] < pd.Timestamp("2025-01-01")].copy()  # hard 2025 lock
if tft[DATE].max() >= pd.Timestamp("2025-01-01"):
    raise AssertionError("2025 entered TFT Step 17")

exclude = {TFT_TARGET, DISTRICT, DATE, "Year", "Month"}
hist_preds = []
for c in tft.columns:
    if c in exclude: continue
    x = pd.to_numeric(tft[c], errors="coerce")
    if x.notna().sum() > 0:
        tft[c] = x
        hist_preds.append(c)
if len(hist_preds) != 35:
    raise ValueError(f"TFT schema mismatch: expected 35 historical predictors, found {len(hist_preds)}")
print(f"TFT rows through 2024: {len(tft)} | predictors={len(hist_preds)}")

start_period = pd.Period(tft[DATE].min(), freq="M")
def calendar(df):
    z = df.copy()
    per = z[DATE].dt.to_period("M")
    z["Time_Index"] = ((per.dt.year - start_period.year) * 12 + (per.dt.month - start_period.month)).astype(int)
    z["Month_Cat"] = z[DATE].dt.month.astype(str)
    mo = z[DATE].dt.month.astype(float)
    z["Month_Sin_TFT"] = np.sin(2 * np.pi * mo / 12.0)
    z["Month_Cos_TFT"] = np.cos(2 * np.pi * mo / 12.0)
    z[DISTRICT] = z[DISTRICT].astype(str)
    return z

tft = calendar(tft)

def segment(df):
    out = []
    for district, g in df.groupby(DISTRICT, sort=True):
        g = g.sort_values(DATE).copy()
        o = g[g[TFT_TARGET].notna()].copy()
        if o.empty: continue
        periods = o[DATE].dt.to_period("M").astype(int).to_numpy()
        seg = np.ones(len(o), dtype=int); cur = 1
        for i in range(1, len(o)):
            if periods[i] - periods[i-1] != 1: cur += 1
            seg[i] = cur
        o["Segment_Number"] = seg
        o["Series_ID"] = o[DISTRICT].astype(str) + "__S" + o["Segment_Number"].astype(str)
        out.append(o)
    return pd.concat(out, ignore_index=True).sort_values([DISTRICT, DATE]).reset_index(drop=True)

obs = segment(tft)
print(f"TFT observed rows={len(obs)} | continuous series={obs['Series_ID'].nunique()}")

def fit_medians(df):
    m = df[hist_preds].median(); missing = m[m.isna()].index.tolist(); m.loc[m.isna()] = 0.0
    return m, missing

def fill_medians(df, med):
    z = df.copy()
    for c in hist_preds:
        z[c] = pd.to_numeric(z[c], errors="coerce").fillna(med[c]).astype(float)
    return z

known_cats = ["Month_Cat"]
known_reals = ["Time_Index", "Month_Sin_TFT", "Month_Cos_TFT"]
unknown_reals = [TFT_TARGET] + hist_preds

def tft_dataset(df):
    return TimeSeriesDataSet(
        df, time_idx="Time_Index", target=TFT_TARGET,
        group_ids=[DISTRICT, "Series_ID"],
        min_encoder_length=ENCODER, max_encoder_length=ENCODER,
        min_prediction_length=1, max_prediction_length=PRED_LEN,
        static_categoricals=[DISTRICT],
        time_varying_known_categoricals=known_cats,
        time_varying_known_reals=known_reals,
        time_varying_unknown_reals=unknown_reals,
        target_normalizer=GroupNormalizer(groups=[DISTRICT]),
        categorical_encoders={
            DISTRICT: NaNLabelEncoder(add_nan=True),
            "Series_ID": NaNLabelEncoder(add_nan=True),
            "Month_Cat": NaNLabelEncoder(add_nan=True)},
        add_relative_time_idx=True, add_target_scales=True, add_encoder_length=True,
        allow_missing_timesteps=False, randomize_length=False)

def tft_model(ds, plateau=4):
    return TemporalFusionTransformer.from_dataset(
        ds, learning_rate=TFT_PARAMS["learning_rate"], hidden_size=TFT_PARAMS["hidden_size"],
        attention_head_size=TFT_PARAMS["attention_head_size"], dropout=TFT_PARAMS["dropout"],
        hidden_continuous_size=TFT_PARAMS["hidden_continuous_size"],
        output_size=len(QUANTILES), loss=QuantileLoss(quantiles=QUANTILES),
        optimizer="adam", reduce_on_plateau_patience=plateau,
        log_interval=-1, log_val_interval=-1)

def choose_epoch(history, idx):
    dates = history[DATE].drop_duplicates().sort_values().tolist()
    if len(dates) < 36: raise ValueError("Not enough TFT history for epoch selection")
    internal = set(dates[-12:])
    core = history[~history[DATE].isin(internal)].copy()
    valctx = history.copy()
    med, _ = fit_medians(core)
    core, valctx = fill_medians(core, med), fill_medians(valctx, med)
    core_ds = tft_dataset(core)
    min_idx = int(valctx[valctx[DATE].isin(internal)]["Time_Index"].min())
    val_ds = TimeSeriesDataSet.from_dataset(core_ds, valctx, min_prediction_idx=min_idx, stop_randomization=True)
    tr_loader = core_ds.to_dataloader(train=True, batch_size=TFT_BATCH, num_workers=0)
    va_loader = val_ds.to_dataloader(train=False, batch_size=TFT_BATCH, num_workers=0)
    set_seed(RANDOM_STATE + idx)
    model = tft_model(core_ds, 4)
    cp_dir = MODEL_DIR / "tft_internal" / f"origin_{idx:02d}"; cp_dir.mkdir(parents=True, exist_ok=True)
    cp = ModelCheckpoint(dirpath=str(cp_dir), filename="tft-{epoch:02d}-{val_loss:.4f}", monitor="val_loss", mode="min", save_top_k=1)
    es = EarlyStopping(monitor="val_loss", min_delta=1e-4, patience=TFT_PATIENCE, mode="min", verbose=False)
    logger = CSVLogger(save_dir=str(LOG_DIR), name=f"epoch_origin_{idx:02d}")
    trainer = pl.Trainer(max_epochs=TFT_MAX_EPOCHS, accelerator="cpu", devices=1, gradient_clip_val=0.1,
        callbacks=[cp, es], logger=logger, enable_checkpointing=True,
        enable_model_summary=False, enable_progress_bar=False, deterministic=True)
    trainer.fit(model, train_dataloaders=tr_loader, val_dataloaders=va_loader)
    if cp.best_model_path == "": raise RuntimeError("No TFT checkpoint produced")
    ck = torch.load(cp.best_model_path, map_location="cpu", weights_only=False)
    return int(ck["epoch"]) + 1

def prediction_context(origin, ds, med):
    frames = []
    for district, g in obs.groupby(DISTRICT, sort=True):
        g = g[g[DATE] <= origin].sort_values(DATE).copy()
        if g.empty: continue
        sid = str(g.iloc[-1]["Series_ID"])
        active = g[g["Series_ID"].astype(str) == sid].sort_values(DATE).copy()
        if len(active) < ENCODER: continue
        enc = active.tail(ENCODER).copy()
        if pd.Timestamp(enc[DATE].max()) != pd.Timestamp(origin): continue
        future = pd.DataFrame({DATE: pd.date_range(origin + pd.offsets.MonthBegin(1), periods=PRED_LEN, freq="MS"),
                               DISTRICT: str(district), "Series_ID": sid})
        future = calendar(future); future[TFT_TARGET] = 0.0
        for c in hist_preds: future[c] = float(med[c])
        combo = fill_medians(pd.concat([enc, future], ignore_index=True, sort=False), med)
        frames.append(combo)
    if not frames: raise ValueError(f"No TFT prediction context at {origin.date()}")
    ctx = pd.concat(frames, ignore_index=True)
    pred_ds = TimeSeriesDataSet.from_dataset(ds, ctx, predict=True, stop_randomization=True)
    return ctx, pred_ds

def extract_pred(obj):
    out = obj.output if hasattr(obj, "output") else obj[0]
    ind = obj.index if hasattr(obj, "index") else obj[1]
    out = out.detach().cpu().numpy() if torch.is_tensor(out) else np.asarray(out)
    return out, pd.DataFrame(ind).copy()


# ------------------------------------------------------------
# Tuned TFT strict 2024 revalidation
# ------------------------------------------------------------
print("\n" + "=" * 120)
print("2. TUNED TFT - 2024 STRICT ROLLING-ORIGIN REVALIDATION")
print("=" * 120)
origins = list(pd.date_range("2023-07-01", "2024-11-01", freq="MS"))
tft_records, tft_train_summary = [], []
for idx, origin in enumerate(origins, 1):
    print("\n" + "-" * 120)
    print(f"TUNED TFT ORIGIN {idx}/{len(origins)} | {origin.date()}")
    print("-" * 120)
    history = obs[obs[DATE] <= origin].copy()
    print(f"Available observed rows: {len(history)}")
    epoch = choose_epoch(history, idx)
    print(f"Selected historical epoch: {epoch}")
    med, missing = fit_medians(history)
    full = fill_medians(history, med)
    ds = tft_dataset(full)
    loader = ds.to_dataloader(train=True, batch_size=TFT_BATCH, num_workers=0)
    set_seed(RANDOM_STATE + 1000 + idx)
    model = tft_model(ds, 1000)
    logger = CSVLogger(save_dir=str(LOG_DIR), name=f"refit_origin_{idx:02d}")
    trainer = pl.Trainer(max_epochs=epoch, accelerator="cpu", devices=1, gradient_clip_val=0.1,
        logger=logger, enable_checkpointing=False, enable_model_summary=False,
        enable_progress_bar=False, deterministic=True)
    trainer.fit(model, train_dataloaders=loader)
    ctx, pred_ds = prediction_context(origin, ds, med)
    pred_loader = pred_ds.to_dataloader(train=False, batch_size=TFT_BATCH, num_workers=0)
    obj = model.predict(pred_loader, mode="quantiles", return_index=True,
        trainer_kwargs={"accelerator": "cpu", "devices": 1, "enable_progress_bar": False, "logger": False})
    qout, index_df = extract_pred(obj)
    if qout.ndim != 3: raise ValueError(f"Unexpected TFT output shape {qout.shape}")
    if "Series_ID" not in index_df.columns: raise KeyError("TFT prediction index missing Series_ID")
    mapping = ctx[["Series_ID", DISTRICT]].drop_duplicates().copy()
    mapping["Series_ID"] = mapping["Series_ID"].astype(str)
    mapping = mapping.set_index("Series_ID")[DISTRICT].to_dict()
    for pos in range(len(index_df)):
        sid = str(index_df.iloc[pos]["Series_ID"])
        district = mapping.get(sid)
        if district is None: continue
        for h in HORIZONS:
            target_date = origin + pd.DateOffset(months=h)
            if target_date.year != 2024: continue
            a = tft[(tft[DISTRICT].astype(str) == str(district)) & (tft[DATE] == target_date)]
            if a.empty or pd.isna(a.iloc[0][TFT_TARGET]): continue
            actual = float(a.iloc[0][TFT_TARGET])
            q025, q50, q975 = [float(qout[pos, h-1, k]) for k in range(3)]
            tft_records.append({
                "Model": "Tuned TFT", "Config_ID": TFT_CONFIG, "Horizon_Months": h,
                "District": district, "Forecast_Origin_Date": origin, "Forecast_Target_Date": target_date,
                "Actual_Target": actual, "Prediction": q50, "Lower_95": q025, "Upper_95": q975,
                "Covered_By_95": bool(q025 <= actual <= q975), "Interval_Width": q975 - q025,
                "Pinball_Q025": pinball(np.array([actual]), np.array([q025]), 0.025),
                "Pinball_Q50": pinball(np.array([actual]), np.array([q50]), 0.50),
                "Pinball_Q975": pinball(np.array([actual]), np.array([q975]), 0.975),
                "Quantile_Crossing": int(not (q025 <= q50 <= q975))})
    tft_train_summary.append({"Forecast_Origin_Date": origin, "Training_Rows": len(full),
        "Training_Series": full["Series_ID"].nunique(), "Selected_Epoch": epoch,
        "Config_ID": TFT_CONFIG, "All_Missing_Predictors": ";".join(missing)})

tft_pred = pd.DataFrame(tft_records)
for h in HORIZONS:
    n = int((tft_pred["Horizon_Months"] == h).sum())
    if n != 300: raise ValueError(f"Tuned TFT H{h}: expected 300 predictions, found {n}")
tft_pred.to_csv(REPORT_DIR / "17_tuned_tft_validation_predictions.csv", index=False)
pd.DataFrame(tft_train_summary).to_csv(REPORT_DIR / "17_tuned_tft_origin_training_summary.csv", index=False)

tft_metric_rows, tft_unc_rows = [], []
for h in HORIZONS:
    d = tft_pred[tft_pred["Horizon_Months"] == h].copy()
    tft_metric_rows.append(result_row(d, "Tuned TFT", h))
    tft_unc_rows.append({
        "Model": "Tuned TFT", "Horizon_Months": h, "Nominal_Coverage_Percentage": 95.0,
        "Observed_Coverage_Percentage": float(d["Covered_By_95"].mean() * 100),
        "Mean_Interval_Width": float(d["Interval_Width"].mean()),
        "Median_Interval_Width": float(d["Interval_Width"].median()),
        "Mean_Pinball_Loss": float(d[["Pinball_Q025", "Pinball_Q50", "Pinball_Q975"]].to_numpy(float).mean()),
        "Quantile_Crossings": int(d["Quantile_Crossing"].sum()),
        "Negative_Lower_Bounds": int((d["Lower_95"] < 0).sum())})

tft_metrics = pd.DataFrame(tft_metric_rows)
tft_unc_metrics = pd.DataFrame(tft_unc_rows)
tft_metrics.to_csv(REPORT_DIR / "17_tuned_tft_validation_metrics.csv", index=False)
tft_unc_metrics.to_csv(REPORT_DIR / "17_tuned_tft_uncertainty_metrics.csv", index=False)


# ------------------------------------------------------------
# Combine tuned metrics + strict reference models
# ------------------------------------------------------------
tuned_metrics = pd.concat([tab_metrics, tft_metrics], ignore_index=True)
tuned_metrics.to_csv(REPORT_DIR / "17_tuned_model_validation_metrics.csv", index=False)

frames = [tuned_metrics]
strict_df = None
if STEP15.exists():
    strict_df = pd.read_csv(STEP15)
    refs = strict_df[strict_df["Model"].isin(["SARIMA", "LSTM", "Seasonal Naive"])].copy()
    if "Evaluated_Rows" in refs.columns:
        refs = refs.rename(columns={"Evaluated_Rows": "Validation_Rows"})
    cols = ["Horizon_Months", "Model", "Validation_Rows", "MAE", "RMSE", "WAPE_Percentage", "sMAPE_Percentage", "R2"]
    refs = refs[cols]
    frames.append(refs)

comparison = pd.concat(frames, ignore_index=True, sort=False).sort_values(["Horizon_Months", "MAE"]).reset_index(drop=True)
comparison.to_csv(REPORT_DIR / "17_final_2024_validation_comparison.csv", index=False)
print("\n" + "=" * 120)
print("FINAL 2024 VALIDATION COMPARISON")
print("=" * 120)
print(comparison.round(4).to_string(index=False))

primary_names = ["SARIMA", "Tuned Random Forest", "Tuned XGBoost", "Tuned LightGBM", "LSTM", "Tuned TFT", "Seasonal Naive"]
primary = comparison[comparison["Model"].isin(primary_names)].copy().sort_values(["Horizon_Months", "MAE"]).reset_index(drop=True)
primary.to_csv(REPORT_DIR / "17_primary_candidate_2024_comparison.csv", index=False)
print("\n" + "=" * 120)
print("PRIMARY FINAL-CANDIDATE COMPARISON")
print("=" * 120)
print(primary.round(4).to_string(index=False))


# ------------------------------------------------------------
# Tuning improvement summary
# ------------------------------------------------------------
improvements = []
if strict_df is not None:
    mapping = {"Random Forest": "Tuned Random Forest", "XGBoost": "Tuned XGBoost",
               "LightGBM": "Tuned LightGBM", "NGBoost": "Tuned NGBoost"}
    for old_name, new_name in mapping.items():
        for h in HORIZONS:
            old = strict_df[(strict_df["Model"] == old_name) & (strict_df["Horizon_Months"] == h)]
            new = tuned_metrics[(tuned_metrics["Model"] == new_name) & (tuned_metrics["Horizon_Months"] == h)]
            if len(old) == 1 and len(new) == 1:
                a, b = float(old.iloc[0]["MAE"]), float(new.iloc[0]["MAE"])
                improvements.append({"Model": old_name, "Horizon_Months": h,
                    "Untuned_Strict_MAE": a, "Tuned_Strict_MAE": b,
                    "MAE_Improvement_Percentage": (a - b) / a * 100})
if STEP15B.exists():
    old_tft = pd.read_csv(STEP15B)
    for h in HORIZONS:
        old = old_tft[old_tft["Horizon_Months"] == h]
        new = tuned_metrics[(tuned_metrics["Model"] == "Tuned TFT") & (tuned_metrics["Horizon_Months"] == h)]
        if len(old) == 1 and len(new) == 1:
            a, b = float(old.iloc[0]["MAE"]), float(new.iloc[0]["MAE"])
            improvements.append({"Model": "TFT", "Horizon_Months": h,
                "Untuned_Strict_MAE": a, "Tuned_Strict_MAE": b,
                "MAE_Improvement_Percentage": (a - b) / a * 100})
improvement_df = pd.DataFrame(improvements)
improvement_df.to_csv(REPORT_DIR / "17_tuning_improvement_summary.csv", index=False)
print("\n" + "=" * 120)
print("TUNING IMPROVEMENT SUMMARY")
print("=" * 120)
print("No comparable untuned rows found." if improvement_df.empty else improvement_df.round(4).to_string(index=False))

print("\n" + "=" * 120)
print("NGBOOST 2024 UNCERTAINTY RESULTS")
print("=" * 120)
print(ngb_unc_metrics.round(4).to_string(index=False))
print("\n" + "=" * 120)
print("TFT 2024 UNCERTAINTY RESULTS")
print("=" * 120)
print(tft_unc_metrics.round(4).to_string(index=False))


# ------------------------------------------------------------
# Figure
# ------------------------------------------------------------
plot_df = primary[primary["Model"] != "Seasonal Naive"].copy()
if not plot_df.empty:
    pivot = plot_df.pivot(index="Horizon_Months", columns="Model", values="MAE")
    pivot.plot(kind="bar", figsize=(14, 7))
    plt.title("2024 Strict Revalidation - Tuned Candidate MAE Comparison")
    plt.xlabel("Forecast Horizon (Months)")
    plt.ylabel("MAE")
    plt.xticks(rotation=0)
    plt.legend(title="Model", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "17_tuned_models_2024_mae_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()

print("\n" + "=" * 120)
print("STEP 17 SUMMARY")
print("=" * 120)
print("Tuned-model 2024 external revalidation completed.")
print("- RF/XGBoost/LightGBM/NGBoost used Step 16 selected parameters")
print(f"- TFT used Step 16B selected configuration: {TFT_CONFIG}")
print("- 2024 was used only for external revalidation")
print("- strict rolling-origin controls were applied")
print("- SARIMA, LSTM and Seasonal Naive strict results were retained as references")
print("- 2025 final test data was NOT loaded")
print("\nNEXT STEP:")
print("Review these 2024 results and freeze the H1/H3/H6 forecasting strategy.")
print("Only after strategy freeze should the 2025 final lockbox be opened.")
print("\nSTEP 17 - TUNED MODEL REVALIDATION COMPLETE")
print("=" * 120)
