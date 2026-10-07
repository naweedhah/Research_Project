# ============================================================
# STEP 14B - LIGHTGBM REGRESSION MODEL ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# Purpose:
# - Train LightGBM regression models for H1, H3 and H6
# - Use TRAIN data only for model fitting
# - Evaluate only on 2024 VALIDATION data
# - Keep 2025 TEST data completely untouched
# - Compare LightGBM with previously analysed models
#
# IMPORTANT:
# - Hyperparameter tuning is NOT performed here
# - 2024 is evaluation data only
# - 2024 is NOT used for early stopping or tuning
# - 2025 test data is NOT loaded
# ============================================================

import re
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from lightgbm import LGBMRegressor


# ============================================================
# 1. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_READY_DIR = (
    BASE_DIR
    / "data"
    / "model_ready"
)

REPORT_DIR = (
    BASE_DIR
    / "outputs"
    / "reports"
)

FIGURE_DIR = (
    BASE_DIR
    / "outputs"
    / "figures"
)

CANDIDATE_MODEL_DIR = (
    BASE_DIR
    / "models"
    / "candidates"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CANDIDATE_MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. SETTINGS
# ============================================================

HORIZONS = [
    1,
    3,
    6
]

TARGET = "Forecast_Target"

RANDOM_STATE = 42


print("\n" + "=" * 110)
print("STEP 14B - LIGHTGBM REGRESSION MODEL ANALYSIS")
print("=" * 110)

print("\nTraining strategy:")
print("- Train LightGBM using training data only")
print("- Evaluate using 2024 validation data")
print("- H1, H3 and H6 evaluated separately")
print("- 2025 final test data is NOT loaded")
print("- Hyperparameter tuning is NOT performed yet")
print("- 2024 is NOT used for early stopping")
print("- Train-only median-imputed predictors are used")
print("- No scaling is required for LightGBM")


# ============================================================
# 3. METRIC FUNCTIONS
# ============================================================

def calculate_mae(y_true, y_pred):

    return np.mean(
        np.abs(
            y_true - y_pred
        )
    )


def calculate_rmse(y_true, y_pred):

    return np.sqrt(
        np.mean(
            (
                y_true - y_pred
            ) ** 2
        )
    )


def calculate_wape(y_true, y_pred):

    denominator = np.sum(
        np.abs(y_true)
    )

    if denominator == 0:

        return np.nan

    return (
        np.sum(
            np.abs(
                y_true - y_pred
            )
        )
        /
        denominator
        *
        100
    )


def calculate_smape(y_true, y_pred):

    denominator = (
        np.abs(y_true)
        +
        np.abs(y_pred)
    )

    numerator = (
        2
        *
        np.abs(
            y_true - y_pred
        )
    )

    valid = (
        denominator != 0
    )

    if valid.sum() == 0:

        return np.nan

    return (
        np.mean(
            numerator[valid]
            /
            denominator[valid]
        )
        *
        100
    )


def calculate_r2(y_true, y_pred):

    ss_res = np.sum(
        (
            y_true - y_pred
        ) ** 2
    )

    ss_tot = np.sum(
        (
            y_true
            -
            np.mean(y_true)
        ) ** 2
    )

    if ss_tot == 0:

        return np.nan

    return (
        1
        -
        (
            ss_res
            /
            ss_tot
        )
    )


# ============================================================
# 4. LIGHTGBM SAFE FEATURE NAMES
# ============================================================

def make_safe_feature_names(columns):

    safe_names = []

    used_names = {}

    mapping_records = []

    for column in columns:

        original_name = str(column)

        safe_name = re.sub(
            r"[^A-Za-z0-9_]+",
            "_",
            original_name
        )

        safe_name = safe_name.strip("_")

        if safe_name == "":
            safe_name = "Feature"

        base_name = safe_name

        if base_name in used_names:

            used_names[base_name] += 1

            safe_name = (
                f"{base_name}_"
                f"{used_names[base_name]}"
            )

        else:

            used_names[base_name] = 0

        safe_names.append(
            safe_name
        )

        mapping_records.append({
            "Original_Feature":
                original_name,

            "LightGBM_Feature":
                safe_name,

            "Changed":
                original_name != safe_name
        })

    return (
        safe_names,
        pd.DataFrame(mapping_records)
    )


# ============================================================
# 5. STORAGE
# ============================================================

metric_records = []

model_summary_records = []


# ============================================================
# 6. PROCESS H1 / H3 / H6
# ============================================================

for horizon in HORIZONS:

    print("\n" + "=" * 110)

    print(
        f"H{horizon} - "
        f"{horizon}-MONTH AHEAD LIGHTGBM"
    )

    print("=" * 110)


    # ========================================================
    # 6.1 LOAD TRAIN + VALIDATION ONLY
    # ========================================================

    train_path = (
        MODEL_READY_DIR
        /
        f"h{horizon}_train_preprocessed.csv"
    )

    validation_path = (
        MODEL_READY_DIR
        /
        f"h{horizon}_validation_preprocessed.csv"
    )

    feature_manifest_path = (
        REPORT_DIR
        /
        f"09_h{horizon}_usable_feature_manifest.csv"
    )


    required_paths = [
        train_path,
        validation_path,
        feature_manifest_path
    ]


    for path in required_paths:

        if not path.exists():

            raise FileNotFoundError(
                f"Required file not found: {path}"
            )


    train_df = pd.read_csv(
        train_path
    )

    validation_df = pd.read_csv(
        validation_path
    )

    feature_manifest = pd.read_csv(
        feature_manifest_path
    )


    print(
        f"\nTRAIN rows      : "
        f"{len(train_df)}"
    )

    print(
        f"VALIDATION rows : "
        f"{len(validation_df)}"
    )


    # ========================================================
    # 6.2 TARGET CHECK
    # ========================================================

    if TARGET not in train_df.columns:

        raise ValueError(
            f"H{horizon}: Target missing from train data."
        )


    if TARGET not in validation_df.columns:

        raise ValueError(
            f"H{horizon}: Target missing from validation data."
        )


    if train_df[TARGET].isna().any():

        raise ValueError(
            f"H{horizon}: Missing training targets detected."
        )


    if validation_df[TARGET].isna().any():

        raise ValueError(
            f"H{horizon}: Missing validation targets detected."
        )


    # ========================================================
    # 6.3 LOAD STEP 09 USABLE FEATURES
    # ========================================================

    if "Feature" not in feature_manifest.columns:

        raise ValueError(
            f"H{horizon}: Feature column not found "
            f"in Step 09 manifest."
        )


    numeric_features = (
        feature_manifest[
            "Feature"
        ]
        .tolist()
    )


    missing_train_features = [

        feature

        for feature in numeric_features

        if feature not in train_df.columns
    ]


    missing_validation_features = [

        feature

        for feature in numeric_features

        if feature not in validation_df.columns
    ]


    if missing_train_features:

        raise ValueError(
            f"H{horizon}: Missing TRAIN features: "
            f"{missing_train_features}"
        )


    if missing_validation_features:

        raise ValueError(
            f"H{horizon}: Missing VALIDATION features: "
            f"{missing_validation_features}"
        )


    print(
        f"Numeric engineered features: "
        f"{len(numeric_features)}"
    )


    # ========================================================
    # 7. TRAIN-ONLY DISTRICT ENCODING
    # ========================================================

    print("\n" + "-" * 110)
    print("1. TRAIN-ONLY DISTRICT ENCODING")
    print("-" * 110)


    if "District" not in train_df.columns:

        raise ValueError(
            f"H{horizon}: District column missing."
        )


    train_districts = sorted(
        train_df[
            "District"
        ]
        .dropna()
        .unique()
    )


    validation_districts = set(
        validation_df[
            "District"
        ]
        .dropna()
        .unique()
    )


    unseen_validation_districts = (
        validation_districts
        -
        set(train_districts)
    )


    print(
        f"Training district categories : "
        f"{len(train_districts)}"
    )

    print(
        f"Unseen validation districts  : "
        f"{len(unseen_validation_districts)}"
    )


    train_dummies = pd.get_dummies(

        train_df[
            "District"
        ],

        prefix="District",

        dtype=float
    )


    validation_dummies = pd.get_dummies(

        validation_df[
            "District"
        ],

        prefix="District",

        dtype=float
    )


    # Validation must follow TRAIN categories only.

    validation_dummies = (
        validation_dummies
        .reindex(
            columns=train_dummies.columns,
            fill_value=0
        )
    )


    # ========================================================
    # 8. BUILD MODEL MATRICES
    # ========================================================

    print("\n" + "-" * 110)
    print("2. BUILD MODEL MATRICES")
    print("-" * 110)


    X_train_numeric = (
        train_df[
            numeric_features
        ]
        .astype(float)
        .reset_index(drop=True)
    )


    X_validation_numeric = (
        validation_df[
            numeric_features
        ]
        .astype(float)
        .reset_index(drop=True)
    )


    train_dummies = (
        train_dummies
        .reset_index(drop=True)
    )


    validation_dummies = (
        validation_dummies
        .reset_index(drop=True)
    )


    X_train = pd.concat(

        [
            X_train_numeric,
            train_dummies
        ],

        axis=1
    )


    X_validation = pd.concat(

        [
            X_validation_numeric,
            validation_dummies
        ],

        axis=1
    )


    y_train = (
        train_df[
            TARGET
        ]
        .to_numpy(
            dtype=float
        )
    )


    y_validation = (
        validation_df[
            TARGET
        ]
        .to_numpy(
            dtype=float
        )
    )


    print(
        f"X_train shape      : "
        f"{X_train.shape}"
    )

    print(
        f"X_validation shape : "
        f"{X_validation.shape}"
    )


    train_nan_count = int(
        X_train
        .isna()
        .sum()
        .sum()
    )


    validation_nan_count = int(
        X_validation
        .isna()
        .sum()
        .sum()
    )


    print(
        f"TRAIN feature NaNs      : "
        f"{train_nan_count}"
    )

    print(
        f"VALIDATION feature NaNs : "
        f"{validation_nan_count}"
    )


    if train_nan_count > 0:

        raise ValueError(
            f"H{horizon}: NaN values found in X_train."
        )


    if validation_nan_count > 0:

        raise ValueError(
            f"H{horizon}: NaN values found in X_validation."
        )


    # ========================================================
    # 8.1 LIGHTGBM-SAFE FEATURE NAMES
    # ========================================================

    original_feature_columns = (
        X_train.columns.tolist()
    )


    safe_feature_names, feature_name_mapping = (
        make_safe_feature_names(
            original_feature_columns
        )
    )


    X_train.columns = (
        safe_feature_names
    )

    X_validation.columns = (
        safe_feature_names
    )


    changed_feature_names = int(
        feature_name_mapping[
            "Changed"
        ].sum()
    )


    print(
        f"LightGBM feature names sanitized: "
        f"{changed_feature_names}"
    )


    feature_name_mapping.to_csv(

        REPORT_DIR
        /
        f"14b_lightgbm_h{horizon}_feature_name_mapping.csv",

        index=False
    )


    # ========================================================
    # 9. TRAIN LIGHTGBM
    # ========================================================

    print("\n" + "-" * 110)
    print("3. TRAIN LIGHTGBM REGRESSOR")
    print("-" * 110)


    # Fixed INITIAL configuration only.
    #
    # These are NOT final tuned hyperparameters.
    #
    # IMPORTANT:
    # 2024 validation is NOT used for early stopping.
    # Proper hyperparameter tuning will be performed later
    # using historical training-period validation only.

    model = LGBMRegressor(

        objective="regression",

        n_estimators=100,

        learning_rate=0.10,

        num_leaves=31,

        max_depth=-1,

        min_child_samples=20,

        subsample=1.0,

        colsample_bytree=1.0,

        reg_alpha=0.0,

        reg_lambda=0.0,

        random_state=RANDOM_STATE,

        n_jobs=-1,

        verbosity=-1
    )


    model.fit(
        X_train,
        y_train
    )


    print(
        "LightGBM training complete."
    )


    # ========================================================
    # 10. 2024 VALIDATION PREDICTION
    # ========================================================

    print("\n" + "-" * 110)
    print("4. 2024 VALIDATION PREDICTION")
    print("-" * 110)


    validation_predictions = (
        model.predict(
            X_validation
        )
    )


    negative_prediction_count = int(
        (
            validation_predictions
            <
            0
        ).sum()
    )


    print(
        f"Negative validation predictions: "
        f"{negative_prediction_count}"
    )


    # ========================================================
    # 11. CALCULATE METRICS
    # ========================================================

    validation_mae = calculate_mae(
        y_validation,
        validation_predictions
    )


    validation_rmse = calculate_rmse(
        y_validation,
        validation_predictions
    )


    validation_wape = calculate_wape(
        y_validation,
        validation_predictions
    )


    validation_smape = calculate_smape(
        y_validation,
        validation_predictions
    )


    validation_r2 = calculate_r2(
        y_validation,
        validation_predictions
    )


    print(
        f"\nMAE   : "
        f"{validation_mae:.4f}"
    )

    print(
        f"RMSE  : "
        f"{validation_rmse:.4f}"
    )

    print(
        f"WAPE  : "
        f"{validation_wape:.4f}%"
    )

    print(
        f"sMAPE : "
        f"{validation_smape:.4f}%"
    )

    print(
        f"R²    : "
        f"{validation_r2:.4f}"
    )


    metric_records.append({

        "Horizon_Months":
            horizon,

        "Model":
            "LightGBM",

        "Validation_Rows":
            len(validation_df),

        "MAE":
            validation_mae,

        "RMSE":
            validation_rmse,

        "WAPE_Percentage":
            validation_wape,

        "sMAPE_Percentage":
            validation_smape,

        "R2":
            validation_r2,

        "Negative_Predictions":
            negative_prediction_count
    })


    # ========================================================
    # 12. SAVE VALIDATION PREDICTIONS
    # ========================================================

    prediction_output = pd.DataFrame({

        "District":
            validation_df[
                "District"
            ].reset_index(
                drop=True
            ),

        "Forecast_Origin_Date":
            validation_df[
                "Forecast_Origin_Date"
            ].reset_index(
                drop=True
            ),

        "Forecast_Target_Date":
            validation_df[
                "Forecast_Target_Date"
            ].reset_index(
                drop=True
            ),

        "Actual_Target":
            y_validation,

        "LightGBM_Prediction":
            validation_predictions,

        "Residual":
            (
                y_validation
                -
                validation_predictions
            ),

        "Absolute_Error":
            np.abs(
                y_validation
                -
                validation_predictions
            )
    })


    prediction_output.to_csv(

        REPORT_DIR
        /
        f"14b_lightgbm_h{horizon}_validation_predictions.csv",

        index=False
    )


    # ========================================================
    # 13. FEATURE IMPORTANCE
    # ========================================================

    print("\n" + "-" * 110)
    print("5. LIGHTGBM FEATURE IMPORTANCE")
    print("-" * 110)


    importance_df = pd.DataFrame({

        "Feature":
            original_feature_columns,

        "LightGBM_Feature":
            X_train.columns,

        "Importance":
            model.feature_importances_
    })


    importance_df = (
        importance_df
        .sort_values(
            "Importance",
            ascending=False
        )
        .reset_index(drop=True)
    )


    print(
        importance_df[
            [
                "Feature",
                "Importance"
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )


    importance_df.to_csv(

        REPORT_DIR
        /
        f"14b_lightgbm_h{horizon}_feature_importance.csv",

        index=False
    )


    # ========================================================
    # 14. MONTHLY VALIDATION TREND PLOT
    # ========================================================

    prediction_output[
        "Forecast_Target_Date"
    ] = pd.to_datetime(

        prediction_output[
            "Forecast_Target_Date"
        ]
    )


    monthly_plot = (

        prediction_output

        .groupby(
            "Forecast_Target_Date"
        )

        .agg(

            Actual_Mean=(
                "Actual_Target",
                "mean"
            ),

            LightGBM_Mean=(
                "LightGBM_Prediction",
                "mean"
            )
        )

        .reset_index()
    )


    plt.figure(
        figsize=(12, 6)
    )


    plt.plot(

        monthly_plot[
            "Forecast_Target_Date"
        ],

        monthly_plot[
            "Actual_Mean"
        ],

        marker="o",

        label="Actual"
    )


    plt.plot(

        monthly_plot[
            "Forecast_Target_Date"
        ],

        monthly_plot[
            "LightGBM_Mean"
        ],

        marker="o",

        label="LightGBM"
    )


    plt.title(
        f"LightGBM Validation Forecast - H{horizon}"
    )


    plt.xlabel(
        "Target Month"
    )


    plt.ylabel(
        "Mean Malnutrition Cases"
    )


    plt.legend()

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()


    plt.savefig(

        FIGURE_DIR
        /
        f"14b_lightgbm_h{horizon}_validation_trend.png",

        dpi=300
    )


    plt.close()


    # ========================================================
    # 15. SAVE CANDIDATE MODEL
    # ========================================================

    model_bundle = {

        "model":
            model,

        "horizon_months":
            horizon,

        "numeric_features":
            numeric_features,

        "district_categories":
            train_districts,

        "district_dummy_columns":
            train_dummies.columns.tolist(),

        "original_model_features":
            original_feature_columns,

        "lightgbm_model_features":
            X_train.columns.tolist(),

        "target":
            TARGET,

        "random_state":
            RANDOM_STATE
    }


    candidate_model_path = (

        CANDIDATE_MODEL_DIR
        /
        f"14b_lightgbm_h{horizon}_candidate.joblib"
    )


    joblib.dump(
        model_bundle,
        candidate_model_path
    )


    print(
        f"\nCandidate model saved: "
        f"{candidate_model_path.name}"
    )


    # ========================================================
    # 16. MODEL DATA SUMMARY
    # ========================================================

    model_summary_records.append({

        "Horizon_Months":
            horizon,

        "Training_Rows":
            len(train_df),

        "Validation_Rows":
            len(validation_df),

        "Numeric_Features":
            len(numeric_features),

        "District_Dummy_Features":
            len(
                train_dummies.columns
            ),

        "Total_Model_Features":
            X_train.shape[1],

        "Unseen_Validation_Districts":
            len(
                unseen_validation_districts
            ),

        "Sanitized_Feature_Names":
            changed_feature_names
    })


# ============================================================
# 17. COMBINE LIGHTGBM RESULTS
# ============================================================

metrics_df = pd.DataFrame(
    metric_records
)


print("\n" + "=" * 110)
print("LIGHTGBM VALIDATION RESULTS")
print("=" * 110)


print(
    metrics_df
    .round(4)
    .to_string(
        index=False
    )
)


metrics_df.to_csv(

    REPORT_DIR
    /
    "14b_lightgbm_validation_metrics.csv",

    index=False
)


# ============================================================
# 18. SAVE MODEL DATA SUMMARY
# ============================================================

model_summary_df = pd.DataFrame(
    model_summary_records
)


model_summary_df.to_csv(

    REPORT_DIR
    /
    "14b_lightgbm_model_data_summary.csv",

    index=False
)


# ============================================================
# 19. MODEL COMPARISON
# ============================================================

print("\n" + "=" * 110)
print("MODEL COMPARISON AFTER LIGHTGBM")
print("=" * 110)


comparison_records = []


def add_metric_dataframe(
    dataframe,
    model_name
):

    required_columns = [
        "Horizon_Months",
        "MAE",
        "RMSE",
        "WAPE_Percentage",
        "sMAPE_Percentage",
        "R2"
    ]


    if not all(
        column in dataframe.columns
        for column in required_columns
    ):

        return


    for _, row in dataframe.iterrows():

        comparison_records.append({

            "Horizon_Months":
                int(
                    row[
                        "Horizon_Months"
                    ]
                ),

            "Model":
                model_name,

            "MAE":
                row["MAE"],

            "RMSE":
                row["RMSE"],

            "WAPE_Percentage":
                row[
                    "WAPE_Percentage"
                ],

            "sMAPE_Percentage":
                row[
                    "sMAPE_Percentage"
                ],

            "R2":
                row["R2"]
        })


# ------------------------------------------------------------
# CURRENT LIGHTGBM
# ------------------------------------------------------------

add_metric_dataframe(
    metrics_df,
    "LightGBM"
)


# ------------------------------------------------------------
# PREVIOUS MODEL METRIC FILES
# ------------------------------------------------------------

previous_models = [

    (
        "SARIMA",
        "11_sarima_validation_metrics.csv"
    ),

    (
        "XGBoost",
        "12_xgboost_validation_metrics.csv"
    ),

    (
        "LSTM",
        "13_lstm_validation_metrics.csv"
    ),

    (
        "NGBoost",
        "14_ngboost_validation_metrics.csv"
    ),

    (
        "Random Forest",
        "14a_random_forest_validation_metrics.csv"
    )
]


for model_name, filename in previous_models:

    metric_path = (
        REPORT_DIR
        /
        filename
    )

    if metric_path.exists():

        previous_df = pd.read_csv(
            metric_path
        )

        add_metric_dataframe(
            previous_df,
            model_name
        )

    else:

        print(
            f"Comparison file not found, skipped: "
            f"{filename}"
        )


# ------------------------------------------------------------
# SEASONAL NAIVE BASELINE
# ------------------------------------------------------------

baseline_path = (
    REPORT_DIR
    /
    "10_baseline_validation_metrics.csv"
)


if baseline_path.exists():

    baseline_df = pd.read_csv(
        baseline_path
    )


    if "Baseline" in baseline_df.columns:

        seasonal_df = (

            baseline_df[
                baseline_df[
                    "Baseline"
                ]
                ==
                "Seasonal Naive"
            ]
            .copy()
        )


        add_metric_dataframe(
            seasonal_df,
            "Seasonal Naive"
        )


# ============================================================
# 20. PRINT + SAVE COMPARISON
# ============================================================

comparison_df = pd.DataFrame(
    comparison_records
)


if not comparison_df.empty:

    comparison_df = (

        comparison_df

        .sort_values(
            [
                "Horizon_Months",
                "MAE"
            ]
        )

        .reset_index(
            drop=True
        )
    )


    print(
        comparison_df
        .round(4)
        .to_string(
            index=False
        )
    )


    comparison_df.to_csv(

        REPORT_DIR
        /
        "14b_model_comparison_after_lightgbm.csv",

        index=False
    )


    # ========================================================
    # 21. MAE COMPARISON FIGURE
    # ========================================================

    mae_pivot = (

        comparison_df

        .pivot_table(

            index="Horizon_Months",

            columns="Model",

            values="MAE",

            aggfunc="first"
        )
    )


    mae_pivot.plot(

        kind="bar",

        figsize=(12, 6)
    )


    plt.title(
        "2024 Validation MAE - Model Comparison"
    )


    plt.xlabel(
        "Forecast Horizon (Months)"
    )


    plt.ylabel(
        "MAE"
    )


    plt.xticks(
        rotation=0
    )


    plt.legend(
        title="Model"
    )


    plt.tight_layout()


    plt.savefig(

        FIGURE_DIR
        /
        "14b_model_mae_comparison.png",

        dpi=300
    )


    plt.close()


# ============================================================
# 22. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 110)
print("STEP 14B SUMMARY")
print("=" * 110)


print(
    "LightGBM regression analysis completed "
    "for H1, H3 and H6."
)


print("\nMethodology:")

print(
    "- Leakage-aware engineered features "
    "from Step 09 used"
)

print(
    "- Numeric feature count loaded dynamically "
    "from Step 09 manifest"
)

print(
    "- District encoded using TRAIN-derived "
    "one-hot columns"
)

print(
    "- Train-only median-imputed predictors used"
)

print(
    "- No feature scaling applied because "
    "LightGBM is tree-based"
)

print(
    "- LightGBM fitted using TRAIN data only"
)

print(
    "- 2024 used only for external validation"
)

print(
    "- 2024 was NOT used for early stopping "
    "or hyperparameter selection"
)

print(
    "- 2025 final test data was NOT loaded"
)

print(
    "- MAE, RMSE, WAPE, sMAPE and R² evaluated"
)

print(
    "- Raw negative prediction count recorded"
)

print(
    "- Feature importance is exploratory only"
)

print(
    "- Hyperparameters have NOT yet been tuned"
)


print("\nIMPORTANT:")

print(
    "Do NOT select the final forecasting model "
    "from this initial result alone."
)

print(
    "LightGBM must later undergo the same "
    "strict temporal validation and tuning "
    "process as the other candidate models."
)


print("\nReports saved to:")
print(REPORT_DIR)


print("\nFigures saved to:")
print(FIGURE_DIR)


print("\nCandidate models saved to:")
print(CANDIDATE_MODEL_DIR)


print("\nSTEP 14B - LIGHTGBM REGRESSION MODEL ANALYSIS COMPLETE")
print("=" * 110)