# ============================================================
# STEP 14A - RANDOM FOREST REGRESSION MODEL ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# Purpose:
# - Train Random Forest regression models for H1, H3 and H6
# - Use TRAIN data only for model fitting
# - Evaluate only using 2024 VALIDATION data
# - Compare with existing forecasting models
#
# IMPORTANT:
# - 2025 TEST data is NOT loaded or evaluated
# - Hyperparameter tuning is NOT performed yet
# - This is the initial Random Forest candidate model
# ============================================================


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path

from sklearn.ensemble import RandomForestRegressor

import joblib


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
print(
    "STEP 14A - RANDOM FOREST REGRESSION MODEL ANALYSIS"
)
print("=" * 110)


print(
    "\nTraining strategy:"
)


print(
    "- Train Random Forest using training data only"
)


print(
    "- Evaluate using 2024 validation data"
)


print(
    "- H1, H3 and H6 evaluated separately"
)


print(
    "- 2025 final test data is NOT loaded"
)


print(
    "- Hyperparameter tuning is NOT performed yet"
)


print(
    "- Train-only median-imputed predictors are used"
)


print(
    "- No scaling is required for Random Forest"
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
                y_true
                -
                y_pred
            ) ** 2
        )
    )


def calculate_wape(
    y_true,
    y_pred
):

    denominator = np.sum(
        np.abs(
            y_true
        )
    )

    if denominator == 0:

        return np.nan

    return (
        np.sum(
            np.abs(
                y_true
                -
                y_pred
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
        np.abs(
            y_true
        )
        +
        np.abs(
            y_pred
        )
    )


    numerator = (
        2
        *
        np.abs(
            y_true
            -
            y_pred
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
            y_true
            -
            y_pred
        ) ** 2
    )


    ss_tot = np.sum(
        (
            y_true
            -
            np.mean(
                y_true
            )
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
# 4. STORAGE
# ============================================================

metric_records = []

model_summary_records = []


# ============================================================
# 5. PROCESS EACH FORECAST HORIZON
# ============================================================

for horizon in HORIZONS:

    print(
        "\n"
        +
        "=" * 110
    )


    print(
        f"H{horizon} - "
        f"{horizon}-MONTH AHEAD RANDOM FOREST"
    )


    print(
        "=" * 110
    )


    # ========================================================
    # 5.1 INPUT FILES
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


    # ========================================================
    # 5.2 LOAD DATA
    # ========================================================

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
    # 5.3 REQUIRED COLUMN CHECK
    # ========================================================

    required_columns = [
        "District",
        "Forecast_Origin_Date",
        "Forecast_Target_Date",
        TARGET
    ]


    for column in required_columns:

        if column not in train_df.columns:

            raise ValueError(
                f"H{horizon}: "
                f"{column} missing from training dataset."
            )


        if column not in validation_df.columns:

            raise ValueError(
                f"H{horizon}: "
                f"{column} missing from validation dataset."
            )


    # ========================================================
    # 5.4 TARGET CHECK
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
    # 5.5 LOAD STEP 09 USABLE FEATURES
    # ========================================================

    if "Feature" not in feature_manifest.columns:

        raise ValueError(
            f"H{horizon}: "
            f"'Feature' column missing from feature manifest."
        )


    numeric_features = (
        feature_manifest[
            "Feature"
        ]
        .tolist()
    )


    print(
        f"Numeric engineered features: "
        f"{len(numeric_features)}"
    )


    # ========================================================
    # 5.6 FEATURE EXISTENCE CHECK
    # ========================================================

    missing_train_features = [

        feature

        for feature
        in numeric_features

        if feature
        not in train_df.columns
    ]


    missing_validation_features = [

        feature

        for feature
        in numeric_features

        if feature
        not in validation_df.columns
    ]


    if missing_train_features:

        raise ValueError(
            f"H{horizon}: "
            f"Features missing from TRAIN: "
            f"{missing_train_features}"
        )


    if missing_validation_features:

        raise ValueError(
            f"H{horizon}: "
            f"Features missing from VALIDATION: "
            f"{missing_validation_features}"
        )


    # ========================================================
    # 6. TRAIN-ONLY DISTRICT ENCODING
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )


    print(
        "1. TRAIN-ONLY DISTRICT ENCODING"
    )


    print(
        "-" * 110
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
            "WARNING: "
            "Unseen validation districts detected."
        )


    # --------------------------------------------------------
    # TRAIN one-hot encoding
    # --------------------------------------------------------

    train_dummies = pd.get_dummies(

        train_df[
            "District"
        ],

        prefix="District",

        dtype=float
    )


    # --------------------------------------------------------
    # VALIDATION one-hot encoding
    # --------------------------------------------------------

    validation_dummies = pd.get_dummies(

        validation_df[
            "District"
        ],

        prefix="District",

        dtype=float
    )


    # IMPORTANT:
    # Validation must use only categories learned from TRAIN.

    validation_dummies = (
        validation_dummies
        .reindex(
            columns=train_dummies.columns,
            fill_value=0
        )
    )


    # ========================================================
    # 7. BUILD RANDOM FOREST MODEL MATRICES
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )


    print(
        "2. BUILD MODEL MATRICES"
    )


    print(
        "-" * 110
    )


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


    # ========================================================
    # 7.1 NaN CHECK
    # ========================================================

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
            f"H{horizon}: "
            f"NaN values detected in X_train."
        )


    if validation_nan_count > 0:

        raise ValueError(
            f"H{horizon}: "
            f"NaN values detected in X_validation."
        )


    # ========================================================
    # 8. RANDOM FOREST MODEL
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )


    print(
        "3. TRAIN RANDOM FOREST REGRESSOR"
    )


    print(
        "-" * 110
    )


    # --------------------------------------------------------
    # INITIAL FIXED CONFIGURATION
    #
    # IMPORTANT:
    # These are NOT final tuned hyperparameters.
    #
    # Hyperparameter tuning will be performed later
    # using historical training-period validation only.
    # --------------------------------------------------------

    model = RandomForestRegressor(

        n_estimators=300,

        criterion="squared_error",

        max_depth=None,

        min_samples_split=2,

        min_samples_leaf=1,

        max_features=1.0,

        bootstrap=True,

        random_state=RANDOM_STATE,

        n_jobs=-1
    )


    model.fit(
        X_train,
        y_train
    )


    print(
        "Random Forest training complete."
    )


    # ========================================================
    # 9. 2024 VALIDATION PREDICTION
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )


    print(
        "4. 2024 VALIDATION PREDICTION"
    )


    print(
        "-" * 110
    )


    validation_predictions = (
        model.predict(
            X_validation
        )
    )


    negative_prediction_count = int(
        np.sum(
            validation_predictions
            <
            0
        )
    )


    print(
        f"Negative validation predictions: "
        f"{negative_prediction_count}"
    )


    # IMPORTANT:
    # Do not clip predictions here.
    # Raw model behaviour should be evaluated first.


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


    # ========================================================
    # 11. STORE METRICS
    # ========================================================

    metric_records.append({

        "Horizon_Months":
            horizon,

        "Model":
            "Random Forest",

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
    # 12. SAVE VALIDATION PREDICTIONS
    # ========================================================

    prediction_output = pd.DataFrame({

        "District":
            validation_df[
                "District"
            ]
            .reset_index(
                drop=True
            ),

        "Forecast_Origin_Date":
            validation_df[
                "Forecast_Origin_Date"
            ]
            .reset_index(
                drop=True
            ),

        "Forecast_Target_Date":
            validation_df[
                "Forecast_Target_Date"
            ]
            .reset_index(
                drop=True
            ),

        "Actual_Target":
            y_validation,

        "Random_Forest_Prediction":
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
        (
            f"14a_random_forest_h{horizon}"
            f"_validation_predictions.csv"
        ),

        index=False
    )


    # ========================================================
    # 13. FEATURE IMPORTANCE
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )


    print(
        "5. RANDOM FOREST FEATURE IMPORTANCE"
    )


    print(
        "-" * 110
    )


    feature_importance_df = pd.DataFrame({

        "Feature":
            X_train.columns,

        "Importance":
            model.feature_importances_
    })


    feature_importance_df = (

        feature_importance_df
        .sort_values(
            "Importance",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


    print(
        feature_importance_df
        .head(20)
        .round(6)
        .to_string(
            index=False
        )
    )


    feature_importance_df.to_csv(

        REPORT_DIR
        /
        (
            f"14a_random_forest_h{horizon}"
            f"_feature_importance.csv"
        ),

        index=False
    )


    # NOTE:
    # Feature importance here is exploratory.
    # It must not be interpreted as causal importance.


    # ========================================================
    # 14. SAVE CANDIDATE MODEL
    # ========================================================

    candidate_model_path = (

        CANDIDATE_MODEL_DIR
        /
        (
            f"14a_random_forest_h{horizon}"
            f"_candidate.joblib"
        )
    )


    candidate_package = {

        "model":
            model,

        "horizon_months":
            horizon,

        "target":
            TARGET,

        "numeric_features":
            numeric_features,

        "district_dummy_columns":
            train_dummies.columns.tolist(),

        "total_model_features":
            X_train.columns.tolist(),

        "random_state":
            RANDOM_STATE,

        "note":
            (
                "Initial Random Forest candidate model. "
                "Not hyperparameter tuned."
            )
    }


    joblib.dump(
        candidate_package,
        candidate_model_path
    )


    print(
        f"\nCandidate model saved: "
        f"{candidate_model_path.name}"
    )


    # ========================================================
    # 15. MONTHLY VALIDATION TREND FIGURE
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

            Random_Forest_Mean=(
                "Random_Forest_Prediction",
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
            "Random_Forest_Mean"
        ],

        marker="o",

        label="Random Forest"
    )


    plt.title(
        f"Random Forest Validation Forecast - H{horizon}"
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
        (
            f"14a_random_forest_h{horizon}"
            f"_validation_trend.png"
        ),

        dpi=300
    )


    plt.close()


    # ========================================================
    # 16. MODEL DATA SUMMARY
    # ========================================================

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
            ),

        "Number_of_Trees":
            model.n_estimators
    })


# ============================================================
# 17. RANDOM FOREST VALIDATION RESULTS
# ============================================================

metrics_df = pd.DataFrame(
    metric_records
)


print(
    "\n"
    +
    "=" * 110
)


print(
    "RANDOM FOREST VALIDATION RESULTS"
)


print(
    "=" * 110
)


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
    "14a_random_forest_validation_metrics.csv",

    index=False
)


# ============================================================
# 18. MODEL DATA SUMMARY
# ============================================================

model_summary_df = pd.DataFrame(
    model_summary_records
)


model_summary_df.to_csv(

    REPORT_DIR
    /
    "14a_random_forest_model_data_summary.csv",

    index=False
)


# ============================================================
# 19. MODEL COMPARISON
# ============================================================

print(
    "\n"
    +
    "=" * 110
)


print(
    "MODEL COMPARISON AFTER RANDOM FOREST"
)


print(
    "=" * 110
)


comparison_records = []


# ============================================================
# 19.1 HELPER FUNCTION
# ============================================================

def append_model_metrics(
    dataframe,
    model_name
):

    required_metric_columns = [

        "Horizon_Months",
        "MAE",
        "RMSE",
        "WAPE_Percentage",
        "sMAPE_Percentage",
        "R2"
    ]


    missing_columns = [

        column

        for column
        in required_metric_columns

        if column
        not in dataframe.columns
    ]


    if missing_columns:

        print(
            f"WARNING: {model_name} metrics skipped. "
            f"Missing columns: {missing_columns}"
        )

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
                row[
                    "MAE"
                ],

            "RMSE":
                row[
                    "RMSE"
                ],

            "WAPE_Percentage":
                row[
                    "WAPE_Percentage"
                ],

            "sMAPE_Percentage":
                row[
                    "sMAPE_Percentage"
                ],

            "R2":
                row[
                    "R2"
                ]
        })


# ============================================================
# 19.2 RANDOM FOREST
# ============================================================

append_model_metrics(
    metrics_df,
    "Random Forest"
)


# ============================================================
# 19.3 SARIMA
# ============================================================

sarima_metrics_path = (
    REPORT_DIR
    /
    "11_sarima_validation_metrics.csv"
)


if sarima_metrics_path.exists():

    sarima_df = pd.read_csv(
        sarima_metrics_path
    )

    append_model_metrics(
        sarima_df,
        "SARIMA"
    )


# ============================================================
# 19.4 XGBOOST
# ============================================================

xgboost_metrics_path = (
    REPORT_DIR
    /
    "12_xgboost_validation_metrics.csv"
)


if xgboost_metrics_path.exists():

    xgboost_df = pd.read_csv(
        xgboost_metrics_path
    )

    append_model_metrics(
        xgboost_df,
        "XGBoost"
    )


# ============================================================
# 19.5 LSTM
# ============================================================

lstm_metrics_path = (
    REPORT_DIR
    /
    "13_lstm_validation_metrics.csv"
)


if lstm_metrics_path.exists():

    lstm_df = pd.read_csv(
        lstm_metrics_path
    )

    append_model_metrics(
        lstm_df,
        "LSTM"
    )


# ============================================================
# 19.6 NGBOOST
# ============================================================

ngboost_metrics_path = (
    REPORT_DIR
    /
    "14_ngboost_validation_metrics.csv"
)


if ngboost_metrics_path.exists():

    ngboost_df = pd.read_csv(
        ngboost_metrics_path
    )

    append_model_metrics(
        ngboost_df,
        "NGBoost"
    )


# ============================================================
# 19.7 SEASONAL NAIVE BASELINE
# ============================================================

baseline_metrics_path = (
    REPORT_DIR
    /
    "10_baseline_validation_metrics.csv"
)


if baseline_metrics_path.exists():

    baseline_df = pd.read_csv(
        baseline_metrics_path
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
                    row[
                        "MAE"
                    ],

                "RMSE":
                    row[
                        "RMSE"
                    ],

                "WAPE_Percentage":
                    row[
                        "WAPE_Percentage"
                    ],

                "sMAPE_Percentage":
                    row[
                        "sMAPE_Percentage"
                    ],

                "R2":
                    row[
                        "R2"
                    ]
            })


# ============================================================
# 20. BUILD COMPARISON TABLE
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
        "14a_model_comparison_after_random_forest.csv",

        index=False
    )


# ============================================================
# 21. MAE COMPARISON FIGURE
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

        figsize=(12, 7)
    )


    plt.title(
        "2024 Validation MAE - Candidate Model Comparison"
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
        "14a_model_mae_comparison.png",

        dpi=300
    )


    plt.close()


# ============================================================
# 22. FINAL SUMMARY
# ============================================================

print(
    "\n"
    +
    "=" * 110
)


print(
    "STEP 14A SUMMARY"
)


print(
    "=" * 110
)


print(
    "Random Forest regression analysis completed "
    "for H1, H3 and H6."
)


print(
    "\nMethodology:"
)


print(
    "- Leakage-aware engineered features from Step 09 used"
)


print(
    "- Numeric feature count loaded dynamically "
    "from the Step 09 manifest"
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
    "Random Forest is tree-based"
)


print(
    "- Random Forest fitted on TRAIN data only"
)


print(
    "- 2024 used for external validation"
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


print(
    "\nIMPORTANT:"
)


print(
    "Do NOT select the final forecasting model "
    "from this initial result alone."
)


print(
    "Random Forest must later undergo the same "
    "strict temporal validation and tuning process "
    "as the other candidate models."
)


print(
    "\nReports saved to:"
)


print(
    REPORT_DIR
)


print(
    "\nFigures saved to:"
)


print(
    FIGURE_DIR
)


print(
    "\nCandidate models saved to:"
)


print(
    CANDIDATE_MODEL_DIR
)


print(
    "\nSTEP 14A - RANDOM FOREST REGRESSION "
    "MODEL ANALYSIS COMPLETE"
)


print(
    "=" * 110
)