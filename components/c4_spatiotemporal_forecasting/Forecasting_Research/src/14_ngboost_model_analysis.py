# ============================================================
# STEP 14 - NGBOOST PROBABILISTIC REGRESSION ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# Purpose:
# - Train NGBoost models for H1, H3 and H6
# - Use TRAIN data only for fitting
# - Evaluate on 2024 VALIDATION only
# - Produce point forecasts
# - Produce predictive uncertainty
# - Generate 95% prediction intervals
# - Compare against:
#       Seasonal Naive
#       SARIMA
#       XGBoost
#       LSTM
#
# IMPORTANT:
# - 2025 TEST data is NOT loaded
# - Hyperparameter tuning is NOT performed yet
# - Normal distribution is used as the initial
#   probabilistic distribution
# ============================================================

import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import norm

from sklearn.tree import DecisionTreeRegressor

from ngboost import NGBRegressor
from ngboost.distns import Normal
from ngboost.scores import LogScore


# ============================================================
# 1. GENERAL SETTINGS
# ============================================================

warnings.filterwarnings("ignore")

RANDOM_STATE = 42

HORIZONS = [
    1,
    3,
    6
]

TARGET = "Forecast_Target"


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

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

MODEL_DIR = (
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

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 3. INTRODUCTION
# ============================================================

print("\n" + "=" * 110)

print(
    "STEP 14 - NGBOOST PROBABILISTIC REGRESSION ANALYSIS"
)

print("=" * 110)


print(
    "\nStrategy:"
)

print(
    "- Train using 2015-2023 training data only"
)

print(
    "- Evaluate using 2024 validation data"
)

print(
    "- Generate point forecasts"
)

print(
    "- Generate predictive uncertainty"
)

print(
    "- Calculate 95% prediction intervals"
)

print(
    "- 2025 final test data is NOT loaded"
)

print(
    "- Hyperparameter tuning is NOT performed yet"
)


# ============================================================
# 4. METRIC FUNCTIONS
# ============================================================

def calculate_mae(
    y_true,
    y_pred
):

    return np.mean(
        np.abs(
            y_true
            -
            y_pred
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
        denominator
        !=
        0
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
# 5. RESULT STORAGE
# ============================================================

metric_records = []

uncertainty_records = []

model_summary_records = []


# ============================================================
# 6. PROCESS EACH FORECAST HORIZON
# ============================================================

for horizon in HORIZONS:

    print(
        "\n"
        +
        "=" * 110
    )

    print(
        f"H{horizon} - "
        f"{horizon}-MONTH AHEAD NGBOOST"
    )

    print(
        "=" * 110
    )


    # ========================================================
    # 6.1 INPUT FILE PATHS
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


    for path in [

        train_path,
        validation_path,
        feature_manifest_path

    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Required file not found: {path}"
            )


    # ========================================================
    # 6.2 LOAD TRAIN + VALIDATION
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
    # 7. TARGET CHECK
    # ========================================================

    if (
        train_df[
            TARGET
        ]
        .isna()
        .any()
    ):

        raise ValueError(
            f"H{horizon}: Missing TRAIN target values."
        )


    if (
        validation_df[
            TARGET
        ]
        .isna()
        .any()
    ):

        raise ValueError(
            f"H{horizon}: Missing VALIDATION target values."
        )


    # ========================================================
    # 8. LOAD NUMERIC FEATURES
    # ========================================================

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
            f"H{horizon}: Features missing "
            f"from training set: "
            f"{missing_train_features}"
        )


    if missing_validation_features:

        raise ValueError(
            f"H{horizon}: Features missing "
            f"from validation set: "
            f"{missing_validation_features}"
        )


    # ========================================================
    # 9. TRAIN-ONLY DISTRICT ENCODING
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


    train_districts = set(

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
        train_districts
    )


    print(
        f"Training district categories : "
        f"{len(train_districts)}"
    )


    print(
        f"Unseen validation districts  : "
        f"{len(unseen_validation_districts)}"
    )


    # --------------------------------------------------------
    # One-hot encode districts
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


    # Validation columns must match training categories.

    validation_dummies = (

        validation_dummies
        .reindex(

            columns=train_dummies.columns,

            fill_value=0
        )
    )


    # ========================================================
    # 10. BUILD MODEL MATRICES
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


    if (
        X_train
        .isna()
        .any()
        .any()
    ):

        raise ValueError(
            f"H{horizon}: NaN values detected "
            f"in X_train."
        )


    if (
        X_validation
        .isna()
        .any()
        .any()
    ):

        raise ValueError(
            f"H{horizon}: NaN values detected "
            f"in X_validation."
        )


    # ========================================================
    # 11. INITIAL NGBOOST CONFIGURATION
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )

    print(
        "3. TRAIN NGBOOST REGRESSOR"
    )

    print(
        "-" * 110
    )


    # This is an INITIAL candidate configuration.
    #
    # We are NOT claiming that this is the
    # final tuned NGBoost configuration.

    base_learner = DecisionTreeRegressor(

        criterion="friedman_mse",

        max_depth=3,

        min_samples_leaf=10,

        random_state=RANDOM_STATE
    )


    ngboost_model = NGBRegressor(

        Dist=Normal,

        Score=LogScore,

        Base=base_learner,

        natural_gradient=True,

        n_estimators=300,

        learning_rate=0.03,

        minibatch_frac=1.0,

        col_sample=1.0,

        verbose=False,

        random_state=RANDOM_STATE
    )


    ngboost_model.fit(

        X_train,

        y_train
    )


    print(
        "NGBoost training complete."
    )


    # ========================================================
    # 12. POINT FORECAST
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )

    print(
        "4. 2024 VALIDATION POINT FORECAST"
    )

    print(
        "-" * 110
    )


    point_predictions = (

        ngboost_model
        .predict(
            X_validation
        )
    )


    point_predictions = np.asarray(

        point_predictions,

        dtype=float
    )


    negative_predictions = int(

        (
            point_predictions
            <
            0
        )
        .sum()
    )


    # ========================================================
    # 13. POINT FORECAST METRICS
    # ========================================================

    validation_mae = calculate_mae(

        y_validation,

        point_predictions
    )


    validation_rmse = calculate_rmse(

        y_validation,

        point_predictions
    )


    validation_wape = calculate_wape(

        y_validation,

        point_predictions
    )


    validation_smape = calculate_smape(

        y_validation,

        point_predictions
    )


    validation_r2 = calculate_r2(

        y_validation,

        point_predictions
    )


    print(
        f"MAE   : "
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


    print(
        f"Negative point predictions: "
        f"{negative_predictions}"
    )


    metric_records.append({

        "Horizon_Months":
            horizon,

        "Model":
            "NGBoost",

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
            negative_predictions
    })


    # ========================================================
    # 14. PROBABILISTIC DISTRIBUTION
    # ========================================================

    print(
        "\n"
        +
        "-" * 110
    )

    print(
        "5. PROBABILISTIC UNCERTAINTY ANALYSIS"
    )

    print(
        "-" * 110
    )


    predictive_distribution = (

        ngboost_model
        .pred_dist(
            X_validation
        )
    )


    distribution_mean = np.asarray(

        predictive_distribution
        .params[
            "loc"
        ],

        dtype=float
    )


    distribution_scale = np.asarray(

        predictive_distribution
        .params[
            "scale"
        ],

        dtype=float
    )


    # Prevent numerical zero standard deviation.

    distribution_scale = np.maximum(

        distribution_scale,

        1e-8
    )


    # ========================================================
    # 15. 95% PREDICTION INTERVAL
    # ========================================================

    z_95 = norm.ppf(
        0.975
    )


    lower_95 = (

        distribution_mean

        -

        (
            z_95
            *
            distribution_scale
        )
    )


    upper_95 = (

        distribution_mean

        +

        (
            z_95
            *
            distribution_scale
        )
    )


    interval_covered = (

        (
            y_validation
            >=
            lower_95
        )

        &

        (
            y_validation
            <=
            upper_95
        )
    )


    interval_coverage = (

        interval_covered
        .mean()
        *
        100
    )


    interval_width = (

        upper_95
        -
        lower_95
    )


    mean_interval_width = float(

        np.mean(
            interval_width
        )
    )


    median_interval_width = float(

        np.median(
            interval_width
        )
    )


    negative_lower_bounds = int(

        (
            lower_95
            <
            0
        )
        .sum()
    )


    # ========================================================
    # 16. NEGATIVE LOG-LIKELIHOOD
    # ========================================================

    log_probability = norm.logpdf(

        y_validation,

        loc=distribution_mean,

        scale=distribution_scale
    )


    gaussian_nll = float(

        -
        np.mean(
            log_probability
        )
    )


    print(
        f"95% Interval Coverage : "
        f"{interval_coverage:.2f}%"
    )


    print(
        f"Mean Interval Width   : "
        f"{mean_interval_width:.4f}"
    )


    print(
        f"Median Interval Width : "
        f"{median_interval_width:.4f}"
    )


    print(
        f"Negative lower bounds : "
        f"{negative_lower_bounds}"
    )


    print(
        f"Gaussian NLL          : "
        f"{gaussian_nll:.4f}"
    )


    # IMPORTANT:
    #
    # We do NOT clip negative interval bounds here.
    #
    # The purpose is to evaluate the raw probabilistic
    # model before deciding whether:
    #
    # - uncertainty calibration is required
    # - another distribution is more suitable
    # - a non-negative transformation is appropriate


    uncertainty_records.append({

        "Horizon_Months":
            horizon,

        "Validation_Rows":
            len(
                validation_df
            ),

        "Nominal_Interval_Percentage":
            95.0,

        "Observed_Interval_Coverage_Percentage":
            interval_coverage,

        "Mean_Interval_Width":
            mean_interval_width,

        "Median_Interval_Width":
            median_interval_width,

        "Negative_Lower_Bounds":
            negative_lower_bounds,

        "Gaussian_NLL":
            gaussian_nll
    })


    # ========================================================
    # 17. SAVE VALIDATION PREDICTIONS
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

        "NGBoost_Point_Prediction":
            point_predictions,

        "Predicted_Distribution_Mean":
            distribution_mean,

        "Predicted_SD":
            distribution_scale,

        "Lower_95":
            lower_95,

        "Upper_95":
            upper_95,

        "Covered_By_95_Interval":
            interval_covered,

        "Residual":
            (
                y_validation
                -
                point_predictions
            ),

        "Absolute_Error":
            np.abs(
                y_validation
                -
                point_predictions
            )
    })


    prediction_output.to_csv(

        REPORT_DIR
        /
        f"14_ngboost_h{horizon}_validation_predictions.csv",

        index=False
    )


    # ========================================================
    # 18. SAVE CANDIDATE MODEL
    # ========================================================

    model_package = {

        "model":
            ngboost_model,

        "horizon_months":
            horizon,

        "numeric_features":
            numeric_features,

        "district_dummy_columns":
            train_dummies.columns.tolist(),

        "all_model_features":
            X_train.columns.tolist(),

        "distribution":
            "Normal"
    }


    joblib.dump(

        model_package,

        MODEL_DIR
        /
        f"ngboost_h{horizon}_candidate.joblib"
    )


    # ========================================================
    # 19. VALIDATION TREND + UNCERTAINTY FIGURE
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

            Prediction_Mean=(
                "NGBoost_Point_Prediction",
                "mean"
            ),

            Lower_95_Mean=(
                "Lower_95",
                "mean"
            ),

            Upper_95_Mean=(
                "Upper_95",
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
            "Prediction_Mean"
        ],

        marker="o",

        label="NGBoost Prediction"
    )


    plt.fill_between(

        monthly_plot[
            "Forecast_Target_Date"
        ],

        monthly_plot[
            "Lower_95_Mean"
        ],

        monthly_plot[
            "Upper_95_Mean"
        ],

        alpha=0.2,

        label="95% Prediction Interval"
    )


    plt.title(
        f"NGBoost Validation Forecast - H{horizon}"
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
        f"14_ngboost_h{horizon}_validation_forecast.png",

        dpi=300
    )


    plt.close()


    # ========================================================
    # 20. HORIZON DATA SUMMARY
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

        "Distribution":
            "Normal"
    })


# ============================================================
# 21. COMBINE POINT FORECAST RESULTS
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
    "NGBOOST VALIDATION RESULTS"
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
    "14_ngboost_validation_metrics.csv",

    index=False
)


# ============================================================
# 22. UNCERTAINTY RESULTS
# ============================================================

uncertainty_df = pd.DataFrame(
    uncertainty_records
)


print(
    "\n"
    +
    "=" * 110
)

print(
    "NGBOOST UNCERTAINTY RESULTS"
)

print(
    "=" * 110
)


print(

    uncertainty_df
    .round(4)
    .to_string(
        index=False
    )
)


uncertainty_df.to_csv(

    REPORT_DIR
    /
    "14_ngboost_uncertainty_metrics.csv",

    index=False
)


# ============================================================
# 23. SAVE DATA SUMMARY
# ============================================================

model_summary_df = pd.DataFrame(
    model_summary_records
)


model_summary_df.to_csv(

    REPORT_DIR
    /
    "14_ngboost_model_data_summary.csv",

    index=False
)


# ============================================================
# 24. CREATE FULL MODEL COMPARISON
# ============================================================

comparison_records = []


# ------------------------------------------------------------
# NGBOOST
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
            "NGBoost",

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


# ------------------------------------------------------------
# LSTM
# ------------------------------------------------------------

lstm_metrics_path = (
    REPORT_DIR
    /
    "13_lstm_validation_metrics.csv"
)


if lstm_metrics_path.exists():

    lstm_df = pd.read_csv(
        lstm_metrics_path
    )


    for _, row in lstm_df.iterrows():

        comparison_records.append({

            "Horizon_Months":
                int(
                    row[
                        "Horizon_Months"
                    ]
                ),

            "Model":
                "LSTM",

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


# ------------------------------------------------------------
# XGBOOST
# ------------------------------------------------------------

xgboost_metrics_path = (
    REPORT_DIR
    /
    "12_xgboost_validation_metrics.csv"
)


if xgboost_metrics_path.exists():

    xgboost_df = pd.read_csv(
        xgboost_metrics_path
    )


    for _, row in xgboost_df.iterrows():

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


# ------------------------------------------------------------
# SARIMA
# ------------------------------------------------------------

sarima_metrics_path = (
    REPORT_DIR
    /
    "11_sarima_validation_metrics.csv"
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


# ------------------------------------------------------------
# SEASONAL NAIVE BASELINE
# ------------------------------------------------------------

baseline_metrics_path = (
    REPORT_DIR
    /
    "10_baseline_validation_metrics.csv"
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
            ==
            "Seasonal Naive"

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
    "\n"
    +
    "=" * 110
)

print(
    "MODEL COMPARISON AFTER NGBOOST"
)

print(
    "=" * 110
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
    "14_model_comparison_after_ngboost.csv",

    index=False
)


# ============================================================
# 25. MODEL COMPARISON GRAPH
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

        figsize=(12, 6)
    )


    plt.title(
        "Validation MAE Comparison Across Candidate Models"
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
        "14_all_candidate_models_mae_comparison.png",

        dpi=300
    )


    plt.close()


# ============================================================
# 26. FINAL SUMMARY
# ============================================================

print(
    "\n"
    +
    "=" * 110
)

print(
    "STEP 14 SUMMARY"
)

print(
    "=" * 110
)


print(
    "NGBoost candidate-model analysis completed."
)


print(
    "\nMethodology:"
)


print(
    "- Same leakage-aware engineered features used"
)


print(
    "- District categories encoded from training data"
)


print(
    "- Train-only median-imputed predictors used"
)


print(
    "- No feature scaling required for this "
    "tree-based boosting configuration"
)


print(
    "- Initial Normal predictive distribution used"
)


print(
    "- Point forecast accuracy evaluated"
)


print(
    "- Predictive standard deviation generated"
)


print(
    "- 95% prediction intervals generated"
)


print(
    "- Prediction interval coverage evaluated"
)


print(
    "- Prediction interval width evaluated"
)


print(
    "- Gaussian negative log-likelihood calculated"
)


print(
    "- 2024 used as external validation"
)


print(
    "- 2025 final test data was NOT loaded"
)


print(
    "- Hyperparameters have NOT yet been tuned"
)


print(
    "\nIMPORTANT:"
)


print(
    "Normal distribution is only the initial "
    "probabilistic candidate."
)


print(
    "Negative lower prediction bounds, interval "
    "coverage and calibration must be evaluated "
    "before final uncertainty reporting."
)


print(
    "\nCandidate models analysed so far:"
)


print(
    "- SARIMA"
)


print(
    "- XGBoost Regression"
)


print(
    "- LSTM"
)


print(
    "- NGBoost"
)


print(
    "\nNEXT STEP:"
)


print(
    "Compare all candidate models and decide "
    "which models should proceed to "
    "hyperparameter tuning."
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
    MODEL_DIR
)


print(
    "\nSTEP 14 - NGBOOST PROBABILISTIC "
    "REGRESSION ANALYSIS COMPLETE"
)

print(
    "=" * 110
)