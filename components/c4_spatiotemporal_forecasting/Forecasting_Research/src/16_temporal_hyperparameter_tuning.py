from pathlib import Path
import warnings
import json

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


# ============================================================
# STEP 16 - TRAIN-ONLY TEMPORAL HYPERPARAMETER TUNING
# ============================================================

warnings.filterwarnings("ignore")

RANDOM_STATE = 42
HORIZONS = [1, 3, 6]
TUNING_YEARS = [2021, 2022, 2023]
TARGET = "Forecast_Target"

BASE_DIR = Path(__file__).resolve().parent.parent
SPLIT_DIR = BASE_DIR / "data" / "splits"
REPORT_DIR = BASE_DIR / "outputs" / "reports"
FIGURE_DIR = BASE_DIR / "outputs" / "figures"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

print("\n" + "=" * 120)
print("STEP 16 - TRAIN-ONLY TEMPORAL HYPERPARAMETER TUNING")
print("=" * 120)
print("Models: Random Forest, XGBoost, LightGBM, NGBoost")
print("Historical tuning years: 2021, 2022, 2023")
print("Strict rule: Forecast_Target_Date <= Forecast_Origin_Date")
print("2024 validation data is NOT loaded.")
print("2025 final test data is NOT loaded.")
print("TFT is handled separately.")


# ============================================================
# METRICS
# ============================================================

def mae(y_true, y_pred):
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def wape(y_true, y_pred):
    denominator = np.sum(np.abs(y_true))
    if denominator == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denominator * 100)


def smape(y_true, y_pred):
    denominator = np.abs(y_true) + np.abs(y_pred)
    valid = denominator != 0
    if valid.sum() == 0:
        return np.nan
    return float(
        np.mean(
            2 * np.abs(y_true[valid] - y_pred[valid]) / denominator[valid]
        ) * 100
    )


def r2(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return np.nan
    return float(1 - ss_res / ss_tot)


# ============================================================
# STRICT ORIGIN-SPECIFIC PREPROCESSING
# ============================================================

def build_model_matrices(training_df, prediction_df, features):
    train_numeric = training_df[features].apply(pd.to_numeric, errors="coerce")
    pred_numeric = prediction_df[features].apply(pd.to_numeric, errors="coerce")

    medians = train_numeric.median()
    all_missing = medians[medians.isna()].index.tolist()
    if all_missing:
        medians.loc[all_missing] = 0.0

    x_train_num = (
        train_numeric.fillna(medians).astype(float).reset_index(drop=True)
    )
    x_pred_num = (
        pred_numeric.fillna(medians).astype(float).reset_index(drop=True)
    )

    train_dummies = pd.get_dummies(
        training_df["District"].astype(str),
        prefix="District",
        dtype=float,
    ).reset_index(drop=True)

    pred_dummies = pd.get_dummies(
        prediction_df["District"].astype(str),
        prefix="District",
        dtype=float,
    )
    pred_dummies = pred_dummies.reindex(
        columns=train_dummies.columns,
        fill_value=0,
    ).reset_index(drop=True)

    x_train = pd.concat([x_train_num, train_dummies], axis=1)
    x_pred = pd.concat([x_pred_num, pred_dummies], axis=1)

    y_train = training_df[TARGET].to_numpy(dtype=np.float32)

    # NumPy avoids XGBoost errors from special source feature names.
    return (
        x_train.to_numpy(dtype=np.float32),
        y_train,
        x_pred.to_numpy(dtype=np.float32),
        all_missing,
    )


# ============================================================
# SEARCH SPACES
# Current Step-15 configurations are included as BASE entries.
# ============================================================

RF_CONFIGS = [
    {
        "Config_ID": "RF_BASE",
        "n_estimators": 300,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
        "bootstrap": True,
    },
    {
        "Config_ID": "RF_A",
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": 0.70,
        "bootstrap": True,
    },
    {
        "Config_ID": "RF_B",
        "n_estimators": 400,
        "max_depth": 20,
        "min_samples_split": 4,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
        "bootstrap": True,
    },
    {
        "Config_ID": "RF_C",
        "n_estimators": 500,
        "max_depth": 16,
        "min_samples_split": 4,
        "min_samples_leaf": 2,
        "max_features": 0.70,
        "bootstrap": True,
    },
]

XGB_CONFIGS = [
    {
        "Config_ID": "XGB_BASE",
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.30,
        "subsample": 1.00,
        "colsample_bytree": 1.00,
        "min_child_weight": 1,
        "reg_lambda": 1.0,
    },
    {
        "Config_ID": "XGB_A",
        "n_estimators": 200,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 0.90,
        "colsample_bytree": 0.90,
        "min_child_weight": 1,
        "reg_lambda": 1.0,
    },
    {
        "Config_ID": "XGB_B",
        "n_estimators": 300,
        "max_depth": 4,
        "learning_rate": 0.03,
        "subsample": 0.90,
        "colsample_bytree": 0.90,
        "min_child_weight": 3,
        "reg_lambda": 1.0,
    },
    {
        "Config_ID": "XGB_C",
        "n_estimators": 300,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 1.00,
        "colsample_bytree": 0.90,
        "min_child_weight": 3,
        "reg_lambda": 2.0,
    },
]

LGB_CONFIGS = [
    {
        "Config_ID": "LGB_BASE",
        "n_estimators": 300,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": -1,
        "min_child_samples": 20,
        "subsample": 1.00,
        "colsample_bytree": 1.00,
        "reg_lambda": 0.0,
    },
    {
        "Config_ID": "LGB_A",
        "n_estimators": 300,
        "learning_rate": 0.03,
        "num_leaves": 31,
        "max_depth": -1,
        "min_child_samples": 20,
        "subsample": 0.90,
        "colsample_bytree": 0.90,
        "reg_lambda": 1.0,
    },
    {
        "Config_ID": "LGB_B",
        "n_estimators": 500,
        "learning_rate": 0.03,
        "num_leaves": 15,
        "max_depth": -1,
        "min_child_samples": 20,
        "subsample": 0.90,
        "colsample_bytree": 0.90,
        "reg_lambda": 1.0,
    },
    {
        "Config_ID": "LGB_C",
        "n_estimators": 400,
        "learning_rate": 0.05,
        "num_leaves": 15,
        "max_depth": 10,
        "min_child_samples": 30,
        "subsample": 1.00,
        "colsample_bytree": 0.90,
        "reg_lambda": 2.0,
    },
]

NGB_CONFIGS = [
    {
        "Config_ID": "NGB_BASE",
        "n_estimators": 300,
        "learning_rate": 0.03,
        "tree_depth": 3,
        "min_samples_leaf": 10,
    },
    {
        "Config_ID": "NGB_A",
        "n_estimators": 200,
        "learning_rate": 0.03,
        "tree_depth": 2,
        "min_samples_leaf": 10,
    },
    {
        "Config_ID": "NGB_B",
        "n_estimators": 400,
        "learning_rate": 0.02,
        "tree_depth": 3,
        "min_samples_leaf": 20,
    },
    {
        "Config_ID": "NGB_C",
        "n_estimators": 300,
        "learning_rate": 0.05,
        "tree_depth": 2,
        "min_samples_leaf": 20,
    },
]

MODEL_CONFIGS = {
    "Random Forest": RF_CONFIGS,
    "XGBoost": XGB_CONFIGS,
    "LightGBM": LGB_CONFIGS,
    "NGBoost": NGB_CONFIGS,
}


# ============================================================
# LOAD TRAINING DATA ONLY
# ============================================================

horizon_data = {}

for horizon in HORIZONS:
    train_path = SPLIT_DIR / f"h{horizon}_train.csv"
    manifest_path = REPORT_DIR / f"09_h{horizon}_usable_feature_manifest.csv"

    if not train_path.exists():
        raise FileNotFoundError(train_path)
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    train_df = pd.read_csv(train_path)
    manifest = pd.read_csv(manifest_path)

    train_df["Forecast_Origin_Date"] = pd.to_datetime(
        train_df["Forecast_Origin_Date"]
    )
    train_df["Forecast_Target_Date"] = pd.to_datetime(
        train_df["Forecast_Target_Date"]
    )

    train_df = train_df[train_df[TARGET].notna()].copy()

    if train_df["Forecast_Target_Date"].dt.year.max() > 2023:
        raise ValueError(
            f"H{horizon}: training file contains target dates after 2023."
        )

    features = manifest["Feature"].tolist()

    missing = [c for c in features if c not in train_df.columns]
    if missing:
        raise KeyError(
            f"H{horizon}: missing manifest features: {missing[:10]}"
        )

    horizon_data[horizon] = {
        "train": train_df,
        "features": features,
    }

    print(
        f"H{horizon}: training rows={len(train_df)}, "
        f"features={len(features)}"
    )


# ============================================================
# MODEL FACTORY
# ============================================================

def build_model(model_name, cfg):
    if model_name == "Random Forest":
        return RandomForestRegressor(
            n_estimators=cfg["n_estimators"],
            max_depth=cfg["max_depth"],
            min_samples_split=cfg["min_samples_split"],
            min_samples_leaf=cfg["min_samples_leaf"],
            max_features=cfg["max_features"],
            bootstrap=cfg["bootstrap"],
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )

    if model_name == "XGBoost":
        return XGBRegressor(
            objective="reg:squarederror",
            n_estimators=cfg["n_estimators"],
            max_depth=cfg["max_depth"],
            learning_rate=cfg["learning_rate"],
            subsample=cfg["subsample"],
            colsample_bytree=cfg["colsample_bytree"],
            min_child_weight=cfg["min_child_weight"],
            reg_lambda=cfg["reg_lambda"],
            random_state=RANDOM_STATE,
            n_jobs=-1,
            tree_method="hist",
        )

    if model_name == "LightGBM":
        return LGBMRegressor(
            objective="regression",
            n_estimators=cfg["n_estimators"],
            learning_rate=cfg["learning_rate"],
            num_leaves=cfg["num_leaves"],
            max_depth=cfg["max_depth"],
            min_child_samples=cfg["min_child_samples"],
            subsample=cfg["subsample"],
            colsample_bytree=cfg["colsample_bytree"],
            reg_lambda=cfg["reg_lambda"],
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbose=-1,
        )

    if model_name == "NGBoost":
        base = DecisionTreeRegressor(
            criterion="friedman_mse",
            max_depth=cfg["tree_depth"],
            min_samples_leaf=cfg["min_samples_leaf"],
            random_state=RANDOM_STATE,
        )
        return NGBRegressor(
            Dist=Normal,
            Score=LogScore,
            Base=base,
            natural_gradient=True,
            n_estimators=cfg["n_estimators"],
            learning_rate=cfg["learning_rate"],
            minibatch_frac=1.0,
            col_sample=1.0,
            verbose=False,
            random_state=RANDOM_STATE,
        )

    raise ValueError(f"Unknown model: {model_name}")


# ============================================================
# STRICT TEMPORAL CONFIG EVALUATION
# ============================================================

def evaluate_configuration(model_name, cfg, horizon, train_df, features):
    fold_records = []
    prediction_records = []

    for tuning_year in TUNING_YEARS:
        fold_rows = train_df[
            train_df["Forecast_Target_Date"].dt.year == tuning_year
        ].copy()

        origins = sorted(fold_rows["Forecast_Origin_Date"].unique())
        if not origins:
            continue

        current_fold_predictions = []

        for origin_date in origins:
            prediction_rows = fold_rows[
                fold_rows["Forecast_Origin_Date"] == origin_date
            ].copy()

            training_pool = train_df[
                train_df["Forecast_Target_Date"] <= origin_date
            ].copy()

            if training_pool.empty:
                continue

            x_train, y_train, x_pred, _ = build_model_matrices(
                training_pool,
                prediction_rows,
                features,
            )

            model = build_model(model_name, cfg)
            model.fit(x_train, y_train)

            predictions = np.asarray(model.predict(x_pred), dtype=float)

            if model_name == "NGBoost":
                dist = model.pred_dist(x_pred)
                pred_sd = np.asarray(dist.params["scale"], dtype=float)
                pred_sd = np.maximum(pred_sd, 1e-8)
                z95 = norm.ppf(0.975)
                lower = predictions - z95 * pred_sd
                upper = predictions + z95 * pred_sd
            else:
                pred_sd = lower = upper = None

            for i, (_, row) in enumerate(prediction_rows.iterrows()):
                rec = {
                    "Model": model_name,
                    "Config_ID": cfg["Config_ID"],
                    "Horizon_Months": horizon,
                    "Tuning_Year": tuning_year,
                    "District": row["District"],
                    "Forecast_Origin_Date": origin_date,
                    "Forecast_Target_Date": row["Forecast_Target_Date"],
                    "Actual_Target": float(row[TARGET]),
                    "Prediction": float(predictions[i]),
                }

                if model_name == "NGBoost":
                    actual = rec["Actual_Target"]
                    rec["Predicted_SD"] = float(pred_sd[i])
                    rec["Lower_95"] = float(lower[i])
                    rec["Upper_95"] = float(upper[i])
                    rec["Covered_By_95"] = bool(
                        lower[i] <= actual <= upper[i]
                    )

                current_fold_predictions.append(rec)
                prediction_records.append(rec)

        fold_df = pd.DataFrame(current_fold_predictions)
        if fold_df.empty:
            continue

        y_true = fold_df["Actual_Target"].to_numpy(dtype=float)
        y_pred = fold_df["Prediction"].to_numpy(dtype=float)

        fold_rec = {
            "Model": model_name,
            "Config_ID": cfg["Config_ID"],
            "Horizon_Months": horizon,
            "Tuning_Year": tuning_year,
            "Rows": len(fold_df),
            "MAE": mae(y_true, y_pred),
            "RMSE": rmse(y_true, y_pred),
            "WAPE_Percentage": wape(y_true, y_pred),
            "sMAPE_Percentage": smape(y_true, y_pred),
            "R2": r2(y_true, y_pred),
        }

        if model_name == "NGBoost":
            coverage = float(fold_df["Covered_By_95"].mean() * 100)
            widths = fold_df["Upper_95"] - fold_df["Lower_95"]
            sd = fold_df["Predicted_SD"].to_numpy(dtype=float)
            gaussian_nll = float(
                -np.mean(norm.logpdf(y_true, loc=y_pred, scale=sd))
            )

            fold_rec["Interval_Coverage_95"] = coverage
            fold_rec["Mean_Interval_Width"] = float(widths.mean())
            fold_rec["Gaussian_NLL"] = gaussian_nll

        fold_records.append(fold_rec)

    return pd.DataFrame(fold_records), pd.DataFrame(prediction_records)


# ============================================================
# RUN TUNING
# ============================================================

all_folds = []
all_predictions = []

for model_name, configs in MODEL_CONFIGS.items():
    print("\n" + "=" * 120)
    print(f"{model_name.upper()} TEMPORAL TUNING")
    print("=" * 120)

    for horizon in HORIZONS:
        train_df = horizon_data[horizon]["train"]
        features = horizon_data[horizon]["features"]

        print(f"\nH{horizon} {model_name}")

        for n, cfg in enumerate(configs, start=1):
            print(
                f"Testing {cfg['Config_ID']} ({n}/{len(configs)})"
            )

            folds, preds = evaluate_configuration(
                model_name,
                cfg,
                horizon,
                train_df,
                features,
            )

            if folds.empty:
                continue

            all_folds.append(folds)
            all_predictions.append(preds)

            cols = [
                "Tuning_Year",
                "MAE",
                "RMSE",
                "WAPE_Percentage",
                "R2",
            ]
            if model_name == "NGBoost":
                cols += [
                    "Interval_Coverage_95",
                    "Gaussian_NLL",
                ]

            print(
                folds[cols]
                .round(4)
                .to_string(index=False)
            )

if not all_folds:
    raise RuntimeError("No tuning results were generated.")

fold_df = pd.concat(all_folds, ignore_index=True)
prediction_df = pd.concat(all_predictions, ignore_index=True)

fold_df.to_csv(
    REPORT_DIR / "16_temporal_tuning_fold_results.csv",
    index=False,
)
prediction_df.to_csv(
    REPORT_DIR / "16_temporal_tuning_predictions.csv",
    index=False,
)


# ============================================================
# SUMMARIZE CONFIGS
# ============================================================

summary = (
    fold_df.groupby(
        ["Model", "Horizon_Months", "Config_ID"]
    )
    .agg(
        Mean_MAE=("MAE", "mean"),
        SD_MAE=("MAE", "std"),
        Mean_RMSE=("RMSE", "mean"),
        Mean_WAPE=("WAPE_Percentage", "mean"),
        Mean_sMAPE=("sMAPE_Percentage", "mean"),
        Mean_R2=("R2", "mean"),
    )
    .reset_index()
)

ngb = fold_df[fold_df["Model"] == "NGBoost"].copy()

if not ngb.empty:
    ngb_extra = (
        ngb.groupby(
            ["Model", "Horizon_Months", "Config_ID"]
        )
        .agg(
            Mean_95_Coverage=("Interval_Coverage_95", "mean"),
            Mean_Interval_Width=("Mean_Interval_Width", "mean"),
            Mean_Gaussian_NLL=("Gaussian_NLL", "mean"),
        )
        .reset_index()
    )

    summary = summary.merge(
        ngb_extra,
        on=["Model", "Horizon_Months", "Config_ID"],
        how="left",
    )

summary = summary.sort_values(
    ["Model", "Horizon_Months", "Mean_MAE", "Mean_RMSE"]
).reset_index(drop=True)

summary.to_csv(
    REPORT_DIR / "16_temporal_tuning_summary.csv",
    index=False,
)


# ============================================================
# SELECT BEST CONFIG PER MODEL / HORIZON
# ============================================================

selected = []

for model_name, configs in MODEL_CONFIGS.items():
    for horizon in HORIZONS:
        temp = summary[
            (summary["Model"] == model_name)
            &
            (summary["Horizon_Months"] == horizon)
        ].copy()

        if temp.empty:
            continue

        temp = temp.sort_values(
            ["Mean_MAE", "Mean_RMSE"]
        )

        best = temp.iloc[0]
        cfg_id = best["Config_ID"]

        cfg = next(
            c for c in configs
            if c["Config_ID"] == cfg_id
        )

        row = {
            "Model": model_name,
            "Horizon_Months": horizon,
            "Config_ID": cfg_id,
            "Mean_Tuning_MAE": best["Mean_MAE"],
            "Mean_Tuning_RMSE": best["Mean_RMSE"],
            "Mean_Tuning_WAPE": best["Mean_WAPE"],
            "Mean_Tuning_R2": best["Mean_R2"],
            "Selected_Parameters": json.dumps(cfg),
        }

        if model_name == "NGBoost":
            row["Mean_95_Coverage"] = best.get(
                "Mean_95_Coverage",
                np.nan,
            )
            row["Mean_Gaussian_NLL"] = best.get(
                "Mean_Gaussian_NLL",
                np.nan,
            )

        selected.append(row)

selected_df = pd.DataFrame(selected)

selected_df.to_csv(
    REPORT_DIR / "16_selected_hyperparameters.csv",
    index=False,
)


# ============================================================
# PRINT + FIGURES
# ============================================================

print("\n" + "=" * 120)
print("TEMPORAL TUNING SUMMARY")
print("=" * 120)
print(summary.round(4).to_string(index=False))

print("\n" + "=" * 120)
print("SELECTED TRAIN-ONLY HYPERPARAMETERS")
print("=" * 120)
print(selected_df.round(4).to_string(index=False))

for model_name in MODEL_CONFIGS:
    for horizon in HORIZONS:
        plot_df = summary[
            (summary["Model"] == model_name)
            &
            (summary["Horizon_Months"] == horizon)
        ].copy()

        if plot_df.empty:
            continue

        plt.figure(figsize=(9, 5))
        plt.bar(
            plot_df["Config_ID"],
            plot_df["Mean_MAE"],
        )
        plt.title(
            f"{model_name} Temporal Tuning - H{horizon}"
        )
        plt.xlabel("Configuration")
        plt.ylabel("Mean Historical Validation MAE")
        plt.tight_layout()

        safe_name = model_name.lower().replace(" ", "_")

        plt.savefig(
            FIGURE_DIR
            / f"16_{safe_name}_h{horizon}_tuning_mae.png",
            dpi=300,
        )
        plt.close()


print("\n" + "=" * 120)
print("STEP 16 SUMMARY")
print("=" * 120)
print("Train-only temporal hyperparameter tuning completed.")
print("- Random Forest tuned")
print("- XGBoost tuned")
print("- LightGBM tuned")
print("- NGBoost tuned as auxiliary probabilistic model")
print("- SARIMA keeps its AIC structure-selection procedure")
print("- LSTM is not tuned in this file")
print("- TFT must be handled separately")
print("- 2024 was NOT loaded for tuning")
print("- 2025 was NOT loaded")
print("\nNEXT:")
print("Use selected configs in Step 17 tuned-model revalidation.")
print("Handle TFT tuning separately before final tuned comparison.")
print("=" * 120)
