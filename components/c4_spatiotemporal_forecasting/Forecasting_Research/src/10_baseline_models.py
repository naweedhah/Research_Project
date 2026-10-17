# ============================================================
# STEP 10 - BASELINE FORECASTING MODELS
# Childhood Malnutrition Forecasting Research
#
# Baselines:
# 1. Global Training Mean
# 2. District Historical Training Mean
# 3. Seasonal Naive (same month previous year)
#
# Evaluation:
# - VALIDATION period only (2024)
# - TEST period (2025) is NOT evaluated here
#
# Metrics:
# - MAE
# - RMSE
# - WAPE
# - sMAPE
# - R²
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# 1. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SPLIT_DIR = (
    BASE_DIR
    / "data"
    / "splits"
)

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
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


print("\n" + "=" * 100)
print("STEP 10 - BASELINE FORECASTING MODELS")
print("=" * 100)

print(
    "\nValidation period only: 2024"
)

print(
    "2025 final test targets are NOT used "
    "during this baseline comparison."
)


# ============================================================
# 3. LOAD ORIGINAL PREPROCESSED DATA
# ============================================================

BASE_DATA_PATH = (
    PROCESSED_DIR
    / "malnutrition_preprocessed_base.csv"
)

if not BASE_DATA_PATH.exists():

    raise FileNotFoundError(
        f"Base dataset not found: {BASE_DATA_PATH}"
    )


base_df = pd.read_csv(
    BASE_DATA_PATH
)


base_df["Date"] = pd.to_datetime(
    base_df["Date"],
    errors="coerce"
)


if base_df["Date"].isna().any():

    raise ValueError(
        "Invalid dates found in base dataset."
    )


# Create lookup:
# District + historical month -> actual historical target

historical_lookup = (
    base_df[
        [
            "District",
            "Date",
            "Malnutrition_Cases"
        ]
    ]
    .rename(
        columns={
            "Date":
                "Historical_Date",

            "Malnutrition_Cases":
                "Historical_Target"
        }
    )
)


# ============================================================
# 4. METRIC FUNCTIONS
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
# 5. EVALUATION FUNCTION
# ============================================================

def evaluate_predictions(
    horizon,
    baseline_name,
    dataframe,
    prediction_column
):

    evaluation_df = (
        dataframe[
            [
                TARGET,
                prediction_column
            ]
        ]
        .dropna()
        .copy()
    )


    total_rows = len(
        dataframe
    )

    evaluated_rows = len(
        evaluation_df
    )


    coverage_percentage = (
        evaluated_rows
        /
        total_rows
        *
        100
    )


    if evaluated_rows == 0:

        return {

            "Horizon_Months":
                horizon,

            "Baseline":
                baseline_name,

            "Total_Validation_Rows":
                total_rows,

            "Evaluated_Rows":
                0,

            "Coverage_Percentage":
                0,

            "MAE":
                np.nan,

            "RMSE":
                np.nan,

            "WAPE_Percentage":
                np.nan,

            "sMAPE_Percentage":
                np.nan,

            "R2":
                np.nan
        }


    y_true = (
        evaluation_df[
            TARGET
        ]
        .to_numpy(
            dtype=float
        )
    )


    y_pred = (
        evaluation_df[
            prediction_column
        ]
        .to_numpy(
            dtype=float
        )
    )


    return {

        "Horizon_Months":
            horizon,

        "Baseline":
            baseline_name,

        "Total_Validation_Rows":
            total_rows,

        "Evaluated_Rows":
            evaluated_rows,

        "Coverage_Percentage":
            coverage_percentage,

        "MAE":
            calculate_mae(
                y_true,
                y_pred
            ),

        "RMSE":
            calculate_rmse(
                y_true,
                y_pred
            ),

        "WAPE_Percentage":
            calculate_wape(
                y_true,
                y_pred
            ),

        "sMAPE_Percentage":
            calculate_smape(
                y_true,
                y_pred
            ),

        "R2":
            calculate_r2(
                y_true,
                y_pred
            )
    }


# ============================================================
# 6. STORAGE
# ============================================================

all_metric_records = []

baseline_summary_records = []


# ============================================================
# 7. PROCESS EACH HORIZON
# ============================================================

for horizon in HORIZONS:

    print("\n" + "=" * 100)

    print(
        f"H{horizon} - "
        f"{horizon}-MONTH AHEAD BASELINE EVALUATION"
    )

    print("=" * 100)


    # ========================================================
    # 7.1 LOAD TRAINING AND VALIDATION SPLITS
    # ========================================================

    train_path = (
        SPLIT_DIR
        / f"h{horizon}_train.csv"
    )

    validation_path = (
        SPLIT_DIR
        / f"h{horizon}_validation.csv"
    )


    if not train_path.exists():

        raise FileNotFoundError(
            f"Training file not found: {train_path}"
        )


    if not validation_path.exists():

        raise FileNotFoundError(
            f"Validation file not found: {validation_path}"
        )


    train_df = pd.read_csv(
        train_path
    )

    validation_df = pd.read_csv(
        validation_path
    )


    train_df[
        "Forecast_Target_Date"
    ] = pd.to_datetime(
        train_df[
            "Forecast_Target_Date"
        ],
        errors="coerce"
    )


    validation_df[
        "Forecast_Target_Date"
    ] = pd.to_datetime(
        validation_df[
            "Forecast_Target_Date"
        ],
        errors="coerce"
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
    # 7.2 CHECK VALIDATION PERIOD
    # ========================================================

    validation_years = sorted(
        validation_df[
            "Forecast_Target_Date"
        ]
        .dt.year
        .unique()
    )


    print(
        f"Validation target years: "
        f"{validation_years}"
    )


    if validation_years != [2024]:

        raise ValueError(
            f"H{horizon}: Validation period "
            f"is not exclusively 2024."
        )


    # ========================================================
    # 8. BASELINE 1 - GLOBAL TRAINING MEAN
    # ========================================================

    print("\n" + "-" * 100)
    print("1. GLOBAL TRAINING MEAN BASELINE")
    print("-" * 100)


    global_train_mean = (
        train_df[
            TARGET
        ]
        .mean()
    )


    validation_df[
        "Prediction_Global_Train_Mean"
    ] = (
        global_train_mean
    )


    print(
        f"Training target mean: "
        f"{global_train_mean:.3f}"
    )


    global_metrics = evaluate_predictions(

        horizon=horizon,

        baseline_name=(
            "Global Training Mean"
        ),

        dataframe=validation_df,

        prediction_column=(
            "Prediction_Global_Train_Mean"
        )
    )


    all_metric_records.append(
        global_metrics
    )


    # ========================================================
    # 9. BASELINE 2 - DISTRICT TRAINING MEAN
    # ========================================================

    print("\n" + "-" * 100)
    print("2. DISTRICT HISTORICAL TRAINING MEAN BASELINE")
    print("-" * 100)


    district_train_mean = (
        train_df
        .groupby(
            "District"
        )[TARGET]
        .mean()
        .rename(
            "District_Training_Mean"
        )
    )


    validation_df[
        "Prediction_District_Train_Mean"
    ] = (
        validation_df[
            "District"
        ]
        .map(
            district_train_mean
        )
    )


    missing_district_mean = (
        validation_df[
            "Prediction_District_Train_Mean"
        ]
        .isna()
        .sum()
    )


    print(
        f"Validation rows without district "
        f"training mean: "
        f"{missing_district_mean}"
    )


    district_metrics = evaluate_predictions(

        horizon=horizon,

        baseline_name=(
            "District Historical Mean"
        ),

        dataframe=validation_df,

        prediction_column=(
            "Prediction_District_Train_Mean"
        )
    )


    all_metric_records.append(
        district_metrics
    )


    # ========================================================
    # 10. BASELINE 3 - SEASONAL NAIVE
    # ========================================================

    print("\n" + "-" * 100)
    print("3. SEASONAL NAIVE BASELINE")
    print("-" * 100)


    # Example:
    #
    # Target date = June 2024
    #
    # Seasonal naive prediction =
    # actual Malnutrition_Cases from June 2023
    #
    # This is historical information and therefore
    # does not use the future target being predicted.


    validation_df[
        "Seasonal_Historical_Date"
    ] = (
        validation_df[
            "Forecast_Target_Date"
        ]
        -
        pd.DateOffset(
            years=1
        )
    )


    validation_df = (
        validation_df
        .merge(
            historical_lookup,
            how="left",
            left_on=[
                "District",
                "Seasonal_Historical_Date"
            ],
            right_on=[
                "District",
                "Historical_Date"
            ]
        )
    )


    validation_df[
        "Prediction_Seasonal_Naive"
    ] = (
        validation_df[
            "Historical_Target"
        ]
    )


    seasonal_missing = (
        validation_df[
            "Prediction_Seasonal_Naive"
        ]
        .isna()
        .sum()
    )


    print(
        f"Seasonal historical values missing: "
        f"{seasonal_missing}"
    )


    seasonal_metrics = evaluate_predictions(

        horizon=horizon,

        baseline_name=(
            "Seasonal Naive"
        ),

        dataframe=validation_df,

        prediction_column=(
            "Prediction_Seasonal_Naive"
        )
    )


    all_metric_records.append(
        seasonal_metrics
    )


    # ========================================================
    # 11. PRINT HORIZON METRICS
    # ========================================================

    current_metrics_df = pd.DataFrame(
        [
            global_metrics,
            district_metrics,
            seasonal_metrics
        ]
    )


    print("\nValidation metrics:")

    print(
        current_metrics_df[
            [
                "Baseline",
                "Coverage_Percentage",
                "MAE",
                "RMSE",
                "WAPE_Percentage",
                "sMAPE_Percentage",
                "R2"
            ]
        ]
        .round(4)
        .to_string(index=False)
    )


    # ========================================================
    # 12. SAVE VALIDATION PREDICTIONS
    # ========================================================

    prediction_columns = [
        "District",
        "Forecast_Origin_Date",
        "Forecast_Target_Date",
        TARGET,
        "Prediction_Global_Train_Mean",
        "Prediction_District_Train_Mean",
        "Seasonal_Historical_Date",
        "Prediction_Seasonal_Naive"
    ]


    available_prediction_columns = [

        column
        for column in prediction_columns

        if column in validation_df.columns
    ]


    validation_predictions = (

        validation_df[
            available_prediction_columns
        ]
        .copy()
    )


    validation_predictions.to_csv(

        REPORT_DIR
        /
        f"10_h{horizon}_baseline_validation_predictions.csv",

        index=False
    )


    # ========================================================
    # 13. STORE SUMMARY
    # ========================================================

    baseline_summary_records.append({

        "Horizon_Months":
            horizon,

        "Training_Rows":
            len(train_df),

        "Validation_Rows":
            len(validation_df),

        "Training_Target_Mean":
            global_train_mean,

        "District_Mean_Missing_Predictions":
            missing_district_mean,

        "Seasonal_Naive_Missing_Predictions":
            seasonal_missing
    })


# ============================================================
# 14. COMBINE METRICS
# ============================================================

metrics_df = pd.DataFrame(
    all_metric_records
)


metrics_df = (
    metrics_df
    .sort_values(
        [
            "Horizon_Months",
            "MAE"
        ]
    )
)


print("\n" + "=" * 100)
print("ALL BASELINE VALIDATION RESULTS")
print("=" * 100)


print(
    metrics_df[
        [
            "Horizon_Months",
            "Baseline",
            "Coverage_Percentage",
            "MAE",
            "RMSE",
            "WAPE_Percentage",
            "sMAPE_Percentage",
            "R2"
        ]
    ]
    .round(4)
    .to_string(index=False)
)


metrics_df.to_csv(
    REPORT_DIR
    / "10_baseline_validation_metrics.csv",
    index=False
)


# ============================================================
# 15. SAVE BASELINE SUMMARY
# ============================================================

baseline_summary_df = pd.DataFrame(
    baseline_summary_records
)


baseline_summary_df.to_csv(
    REPORT_DIR
    / "10_baseline_data_summary.csv",
    index=False
)


# ============================================================
# 16. CREATE MAE COMPARISON FIGURE
# ============================================================

pivot_mae = (
    metrics_df
    .pivot(
        index="Horizon_Months",
        columns="Baseline",
        values="MAE"
    )
)


ax = pivot_mae.plot(
    kind="bar",
    figsize=(11, 6)
)


plt.title(
    "Baseline Validation MAE by Forecast Horizon"
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
    title="Baseline"
)

plt.tight_layout()


plt.savefig(
    FIGURE_DIR
    / "10_baseline_mae_comparison.png",
    dpi=300
)

plt.close()


# ============================================================
# 17. RMSE COMPARISON FIGURE
# ============================================================

pivot_rmse = (
    metrics_df
    .pivot(
        index="Horizon_Months",
        columns="Baseline",
        values="RMSE"
    )
)


ax = pivot_rmse.plot(
    kind="bar",
    figsize=(11, 6)
)


plt.title(
    "Baseline Validation RMSE by Forecast Horizon"
)

plt.xlabel(
    "Forecast Horizon (Months)"
)

plt.ylabel(
    "RMSE"
)

plt.xticks(
    rotation=0
)

plt.legend(
    title="Baseline"
)

plt.tight_layout()


plt.savefig(
    FIGURE_DIR
    / "10_baseline_rmse_comparison.png",
    dpi=300
)

plt.close()


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 100)
print("STEP 10 SUMMARY")
print("=" * 100)


print(
    "Baseline forecasting completed for "
    "H1, H3 and H6."
)


print(
    "\nBaselines evaluated:"
)

print(
    "- Global Training Mean"
)

print(
    "- District Historical Training Mean"
)

print(
    "- Seasonal Naive"
)


print(
    "\nMetrics:"
)

print(
    "- MAE"
)

print(
    "- RMSE"
)

print(
    "- WAPE"
)

print(
    "- sMAPE"
)

print(
    "- R²"
)


print(
    "\nLeakage protection:"
)

print(
    "- Baseline statistics learned from TRAIN only"
)

print(
    "- Seasonal naive uses same month from previous year"
)

print(
    "- Evaluation uses 2024 validation targets only"
)

print(
    "- 2025 final test targets were not evaluated"
)

print(
    "- No advanced model trained yet"
)


print(
    "\nNOTE:"
)

print(
    "MAPE is not used because the target dataset "
    "contains a zero value, which can make ordinary "
    "MAPE undefined or unstable."
)


print(
    "\nNEXT STEP:"
)

print(
    "Train and analyse the first candidate "
    "forecasting model: SARIMA."
)


print("\nReports saved to:")
print(REPORT_DIR)

print("\nFigures saved to:")
print(FIGURE_DIR)


print(
    "\nSTEP 10 - BASELINE FORECASTING MODELS COMPLETE"
)

print("=" * 100)