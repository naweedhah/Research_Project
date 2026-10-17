# ============================================================
# STEP 12 - XGBOOST REGRESSION MODEL ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# Purpose:
# - Train XGBoost regression models for H1, H3 and H6
# - Use TRAIN data only for fitting
# - Evaluate only on 2024 VALIDATION data
# - Compare with SARIMA and Seasonal Naive baseline
#
# IMPORTANT:
# - 2025 TEST data is NOT loaded or evaluated
# - Hyperparameter tuning is NOT performed yet
# - SHAP is NOT performed yet
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from xgboost import XGBRegressor


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

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

FIGURE_DIR.mkdir(
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


print("\n" + "=" * 105)
print("STEP 12 - XGBOOST REGRESSION MODEL ANALYSIS")
print("=" * 105)

print(
    "\nTraining strategy:"
)

print(
    "- Fit XGBoost using training data only"
)

print(
    "- Evaluate using 2024 validation data"
)

print(
    "- 2025 final test data is NOT used"
)

print(
    "- Hyperparameter tuning is postponed "
    "to a later model-tuning stage"
)


# ============================================================
# 3. METRIC FUNCTIONS
# ============================================================

def calculate_mae(
    y_true,
    y_pred
):

    return np.mean(
        np.abs(
            y_true - y_pred
        )
    )


def calculate_rmse(
    y_true,
    y_pred
):

    return np.sqrt(
        np.mean(
            (
                y_true - y_pred
            ) ** 2
        )
    )


def calculate_wape(
    y_true,
    y_pred
):

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


def calculate_smape(
    y_true,
    y_pred
):

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


def calculate_r2(
    y_true,
    y_pred
):

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
# 3.1 XGBOOST FEATURE-NAME COMPATIBILITY
# ============================================================

def make_xgboost_safe_feature_name(feature_name):
    """
    XGBoost does not allow some characters such as [, ] and <
    inside pandas feature names.

    This function changes ONLY the column label used internally
    by XGBoost. It does NOT change any feature values.
    """

    safe_name = str(feature_name)

    safe_name = safe_name.replace("<", "LT")
    safe_name = safe_name.replace(">", "GT")
    safe_name = safe_name.replace("[", "(")
    safe_name = safe_name.replace("]", ")")

    return safe_name


# ============================================================
# 4. STORAGE
# ============================================================

metric_records = []

model_summary_records = []


# ============================================================
# 5. PROCESS EACH FORECAST HORIZON
# ============================================================

for horizon in HORIZONS:

    print("\n" + "=" * 105)

    print(
        f"H{horizon} - "
        f"{horizon}-MONTH AHEAD XGBOOST"
    )

    print("=" * 105)


    # ========================================================
    # 5.1 LOAD TRAIN AND VALIDATION ONLY
    # ========================================================

    train_path = (
        MODEL_READY_DIR
        / f"h{horizon}_train_preprocessed.csv"
    )

    validation_path = (
        MODEL_READY_DIR
        / f"h{horizon}_validation_preprocessed.csv"
    )

    feature_manifest_path = (
        REPORT_DIR
        / f"09_h{horizon}_usable_feature_manifest.csv"
    )


    for path in [
        train_path,
        validation_path,
        feature_manifest_path
    ]:

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
    # 5.2 TARGET CHECK
    # ========================================================

    if train_df[TARGET].isna().any():

        raise ValueError(
            f"H{horizon}: Missing training targets."
        )


    if validation_df[TARGET].isna().any():

        raise ValueError(
            f"H{horizon}: Missing validation targets."
        )


    # ========================================================
    # 5.3 LOAD USABLE FEATURES FROM STEP 09
    # ========================================================

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
            f"H{horizon}: Features missing from train: "
            f"{missing_train_features}"
        )


    if missing_validation_features:

        raise ValueError(
            f"H{horizon}: Features missing from validation: "
            f"{missing_validation_features}"
        )


    print(
        f"Numeric engineered features: "
        f"{len(numeric_features)}"
    )


    # ========================================================
    # 6. TRAIN-ONLY DISTRICT ENCODING
    # ========================================================

    print("\n" + "-" * 105)
    print("1. TRAIN-ONLY DISTRICT ENCODING")
    print("-" * 105)


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
        set(
            train_districts
        )
    )


    print(
        f"Training district categories : "
        f"{len(train_districts)}"
    )

    print(
        f"Unseen validation districts  : "
        f"{len(unseen_validation_districts)}"
    )


    if unseen_validation_districts:

        print(
            "WARNING: Unseen validation districts "
            "will receive zero for all training "
            "district dummy columns."
        )


    # --------------------------------------------------------
    # One-hot encode TRAIN categories
    # --------------------------------------------------------

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


    # IMPORTANT:
    # Validation is aligned to TRAIN columns.
    # Validation cannot introduce new encoded columns.

    validation_dummies = (

        validation_dummies
        .reindex(
            columns=train_dummies.columns,
            fill_value=0
        )
    )


    # ========================================================
    # 7. BUILD MODEL MATRICES
    # ========================================================

    print("\n" + "-" * 105)
    print("2. BUILD MODEL MATRICES")
    print("-" * 105)


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


    # --------------------------------------------------------
    # XGBoost feature-name compatibility
    # --------------------------------------------------------
    # Keep original names for reports / interpretation.
    # Only the internal XGBoost matrix column labels are sanitized.

    if list(X_train.columns) != list(X_validation.columns):

        raise ValueError(
            f"H{horizon}: Train/validation feature columns "
            "are not aligned before XGBoost sanitization."
        )


    original_model_feature_names = [
        str(column)
        for column in X_train.columns
    ]


    safe_model_feature_names = [
        make_xgboost_safe_feature_name(column)
        for column in original_model_feature_names
    ]


    safe_name_index = pd.Index(
        safe_model_feature_names
    )


    if safe_name_index.duplicated().any():

        duplicate_safe_names = (
            safe_name_index[
                safe_name_index.duplicated(
                    keep=False
                )
            ]
            .unique()
            .tolist()
        )

        raise ValueError(
            f"H{horizon}: Duplicate feature names were "
            "created after XGBoost sanitization: "
            f"{duplicate_safe_names}"
        )


    X_train.columns = safe_model_feature_names
    X_validation.columns = safe_model_feature_names


    feature_name_map_df = pd.DataFrame({

        "Original_Feature":
            original_model_feature_names,

        "XGBoost_Safe_Feature":
            safe_model_feature_names
    })


    feature_name_map_df.to_csv(

        REPORT_DIR
        / f"12_xgboost_h{horizon}_feature_name_map.csv",

        index=False
    )


    changed_name_count = int(
        (
            feature_name_map_df[
                "Original_Feature"
            ]
            !=
            feature_name_map_df[
                "XGBoost_Safe_Feature"
            ]
        ).sum()
    )


    print(
        f"XGBoost feature-name compatibility check: PASS"
    )

    print(
        f"Sanitized feature names: "
        f"{changed_name_count}"
    )


    print(
        f"X_train shape      : "
        f"{X_train.shape}"
    )

    print(
        f"X_validation shape : "
        f"{X_validation.shape}"
    )


    if X_train.isna().any().any():

        raise ValueError(
            f"H{horizon}: NaN values found in X_train."
        )


    if X_validation.isna().any().any():

        raise ValueError(
            f"H{horizon}: NaN values found in X_validation."
        )


    # ========================================================
    # 8. XGBOOST MODEL
    # ========================================================

    print("\n" + "-" * 105)
    print("3. TRAIN XGBOOST REGRESSOR")
    print("-" * 105)


    # Fixed initial configuration.
    #
    # This is NOT presented as the final tuned
    # configuration.
    #
    # Proper hyperparameter tuning will be
    # performed later.

    model = XGBRegressor(

        objective="reg:squarederror",

        n_estimators=100,

        max_depth=6,

        learning_rate=0.3,

        subsample=1.0,

        colsample_bytree=1.0,

        reg_lambda=1.0,

        random_state=RANDOM_STATE,

        n_jobs=-1,

        tree_method="hist"
    )


    model.fit(
        X_train,
        y_train
    )


    print(
        "XGBoost training complete."
    )


    # ========================================================
    # 9. VALIDATION PREDICTION
    # ========================================================

    print("\n" + "-" * 105)
    print("4. 2024 VALIDATION PREDICTION")
    print("-" * 105)


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
        )
        .sum()
    )


    print(
        f"Negative validation predictions: "
        f"{negative_prediction_count}"
    )


    # No clipping is applied here.
    #
    # We want to evaluate the model's raw predictions
    # before deciding whether non-negative constraints
    # or a count-specific objective are justified.


    # ========================================================
    # 10. CALCULATE VALIDATION METRICS
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
            "XGBoost",

        "Validation_Rows":
            len(
                validation_df
            ),

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
    # 11. SAVE VALIDATION PREDICTIONS
    # ========================================================

    prediction_output = pd.DataFrame({

        "District":
            validation_df[
                "District"
            ],

        "Forecast_Origin_Date":
            validation_df[
                "Forecast_Origin_Date"
            ],

        "Forecast_Target_Date":
            validation_df[
                "Forecast_Target_Date"
            ],

        "Actual_Target":
            y_validation,

        "XGBoost_Prediction":
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
        / f"12_xgboost_h{horizon}_validation_predictions.csv",

        index=False
    )


    # ========================================================
    # 12. FEATURE IMPORTANCE
    # ========================================================

    print("\n" + "-" * 105)
    print("5. XGBOOST FEATURE IMPORTANCE")
    print("-" * 105)


    feature_importance_df = pd.DataFrame({

        "Feature":
            original_model_feature_names,

        "XGBoost_Safe_Feature":
            safe_model_feature_names,

        "Importance":
            model.feature_importances_
    })


    feature_importance_df = (

        feature_importance_df
        .sort_values(
            "Importance",
            ascending=False
        )
        .reset_index(drop=True)
    )


    print(
        feature_importance_df
        .head(20)
        .round(6)
        .to_string(index=False)
    )


    feature_importance_df.to_csv(

        REPORT_DIR
        / f"12_xgboost_h{horizon}_feature_importance.csv",

        index=False
    )


    # IMPORTANT:
    #
    # Built-in XGBoost feature importance is
    # exploratory here.
    #
    # Final explainability will later use SHAP.


    # ========================================================
    # 13. MONTHLY VALIDATION PLOT
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

            XGBoost_Mean=(
                "XGBoost_Prediction",
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
            "XGBoost_Mean"
        ],

        marker="o",

        label="XGBoost"
    )


    plt.title(
        f"XGBoost Validation Forecast - H{horizon}"
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
        / f"12_xgboost_h{horizon}_validation_trend.png",

        dpi=300
    )


    plt.close()


    model_summary_records.append({

        "Horizon_Months":
            horizon,

        "Training_Rows":
            len(
                train_df
            ),

        "Validation_Rows":
            len(
                validation_df
            ),

        "Numeric_Features":
            len(
                numeric_features
            ),

        "District_Dummy_Features":
            len(
                train_dummies.columns
            ),

        "Total_Model_Features":
            X_train.shape[1],

        "Unseen_Validation_Districts":
            len(
                unseen_validation_districts
            )
    })


# ============================================================
# 14. COMBINE XGBOOST RESULTS
# ============================================================

metrics_df = pd.DataFrame(
    metric_records
)


print("\n" + "=" * 105)
print("XGBOOST VALIDATION RESULTS")
print("=" * 105)


print(
    metrics_df
    .round(4)
    .to_string(index=False)
)


metrics_df.to_csv(

    REPORT_DIR
    / "12_xgboost_validation_metrics.csv",

    index=False
)


# ============================================================
# 15. MODEL DATA SUMMARY
# ============================================================

model_summary_df = pd.DataFrame(
    model_summary_records
)


model_summary_df.to_csv(

    REPORT_DIR
    / "12_xgboost_model_data_summary.csv",

    index=False
)


# ============================================================
# 16. COMPARE WITH SARIMA AND SEASONAL NAIVE
# ============================================================

print("\n" + "=" * 105)
print("MODEL COMPARISON - VALIDATION PERIOD")
print("=" * 105)


comparison_records = []


# ------------------------------------------------------------
# XGBoost
# ------------------------------------------------------------

for _, row in metrics_df.iterrows():

    comparison_records.append({

        "Horizon_Months":
            int(
                row[
                    "Horizon_Months"
                ]
            ),

        "Model":
            "XGBoost",

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
# SARIMA
# ------------------------------------------------------------

sarima_metrics_path = (
    REPORT_DIR
    / "11_sarima_validation_metrics.csv"
)


if sarima_metrics_path.exists():

    sarima_df = pd.read_csv(
        sarima_metrics_path
    )


    for _, row in sarima_df.iterrows():

        comparison_records.append({

            "Horizon_Months":
                int(
                    row[
                        "Horizon_Months"
                    ]
                ),

            "Model":
                "SARIMA",

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
# Seasonal Naive
# ------------------------------------------------------------

baseline_metrics_path = (
    REPORT_DIR
    / "10_baseline_validation_metrics.csv"
)


if baseline_metrics_path.exists():

    baseline_df = pd.read_csv(
        baseline_metrics_path
    )


    seasonal_df = (

        baseline_df[
            baseline_df[
                "Baseline"
            ]
            == "Seasonal Naive"
        ]
    )


    for _, row in seasonal_df.iterrows():

        comparison_records.append({

            "Horizon_Months":
                int(
                    row[
                        "Horizon_Months"
                    ]
                ),

            "Model":
                "Seasonal Naive",

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


comparison_df = pd.DataFrame(
    comparison_records
)


comparison_df = (

    comparison_df
    .sort_values(
        [
            "Horizon_Months",
            "MAE"
        ]
    )
)


print(
    comparison_df
    .round(4)
    .to_string(index=False)
)


comparison_df.to_csv(

    REPORT_DIR
    / "12_model_comparison_after_xgboost.csv",

    index=False
)


# ============================================================
# 17. MAE COMPARISON FIGURE
# ============================================================

if not comparison_df.empty:

    mae_pivot = (

        comparison_df
        .pivot(
            index="Horizon_Months",
            columns="Model",
            values="MAE"
        )
    )


    mae_pivot.plot(

        kind="bar",

        figsize=(11, 6)
    )


    plt.title(
        "Validation MAE: Baseline vs SARIMA vs XGBoost"
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
        / "12_model_mae_comparison.png",

        dpi=300
    )


    plt.close()


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 105)
print("STEP 12 SUMMARY")
print("=" * 105)


print(
    "XGBoost regression analysis completed "
    "for H1, H3 and H6."
)


print(
    "\nMethodology:"
)

print(
    "- 147 leakage-aware numeric features used"
)

print(
    "- District encoded using training-derived "
    "one-hot columns"
)


print(
    "- XGBoost-incompatible feature-name characters "
    "were sanitized internally without changing data values"
)



print(
    "- Train-only median-imputed data used"
)

print(
    "- No scaling applied because tree-based "
    "XGBoost does not require standard scaling"
)

print(
    "- Model fitted on training data only"
)

print(
    "- 2024 validation used for evaluation"
)

print(
    "- 2025 final test data was not loaded"
)

print(
    "- Hyperparameter tuning has NOT yet been performed"
)

print(
    "- Built-in feature importance is exploratory only"
)

print(
    "- SHAP analysis will be performed later"
)


print(
    "\nIMPORTANT:"
)

print(
    "The final forecasting model is NOT selected yet."
)

print(
    "XGBoost must still be compared with "
    "LSTM and NGBoost."
)


print(
    "\nNEXT STEP:"
)

print(
    "LSTM model preparation and analysis."
)


print("\nReports saved to:")
print(REPORT_DIR)

print("\nFigures saved to:")
print(FIGURE_DIR)


print(
    "\nSTEP 12 - XGBOOST REGRESSION "
    "MODEL ANALYSIS COMPLETE"
)

print("=" * 105)