# ============================================================
# STEP 11 - SARIMA MODEL ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# Purpose:
# - Train district-specific SARIMA models
# - Select SARIMA orders using TRAIN data only
# - Use AIC for training-only order comparison
# - Perform rolling-origin validation for H1, H3 and H6
# - Compare against the existing baseline results
#
# IMPORTANT:
# - 2025 test targets are NOT used
# - SARIMA order selection uses data up to 2023-12 only
# - Validation forecasts use only information available
#   at or before each forecast origin
# ============================================================

import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import ConvergenceWarning


# ============================================================
# 1. SUPPRESS NON-CRITICAL STATSMODELS WARNINGS
# ============================================================

warnings.filterwarnings(
    "ignore",
    category=ConvergenceWarning
)

warnings.filterwarnings(
    "ignore",
    message="Non-stationary starting autoregressive parameters"
)

warnings.filterwarnings(
    "ignore",
    message="Non-invertible starting MA parameters"
)

warnings.filterwarnings(
    "ignore",
    message="Too few observations"
)


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

BASE_DATA_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "malnutrition_preprocessed_base.csv"
)

SPLIT_DIR = (
    BASE_DIR
    / "data"
    / "splits"
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
# 3. SETTINGS
# ============================================================

TARGET = "Malnutrition_Cases"

TRAIN_CUTOFF = pd.Timestamp(
    "2023-12-01"
)

HORIZONS = [
    1,
    3,
    6
]


# Focused SARIMA candidate search.
# We are NOT assuming one SARIMA order for all districts.

ORDER_CANDIDATES = [

    (1, 0, 0),
    (0, 0, 1),

    (0, 1, 0),
    (1, 1, 0),
    (0, 1, 1),
    (1, 1, 1)
]


SEASONAL_ORDER_CANDIDATES = [

    (0, 0, 0, 12),
    (1, 0, 0, 12),
    (0, 0, 1, 12),
    (1, 0, 1, 12),
    (1, 1, 0, 12),
    (0, 1, 1, 12)
]


print("\n" + "=" * 105)
print("STEP 11 - SARIMA MODEL ANALYSIS")
print("=" * 105)

print(
    "\nSARIMA order selection:"
)

print(
    "- District-specific"
)

print(
    "- Training data only"
)

print(
    "- AIC used for candidate-model comparison"
)

print(
    "- Seasonal period = 12 months"
)

print(
    "\nValidation strategy:"
)

print(
    "- Rolling forecast origin"
)

print(
    "- H1, H3 and H6"
)

print(
    "- Validation target year = 2024"
)

print(
    "- 2025 test targets are NOT used"
)


# ============================================================
# 4. LOAD BASE MONTHLY DATA
# ============================================================

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
        "Invalid Date values found."
    )


base_df = (
    base_df
    .sort_values(
        [
            "District",
            "Date"
        ]
    )
    .reset_index(drop=True)
)


print(
    f"\nDataset rows : {len(base_df)}"
)

print(
    f"Districts    : {base_df['District'].nunique()}"
)

print(
    f"Date range   : "
    f"{base_df['Date'].min().date()} "
    f"to "
    f"{base_df['Date'].max().date()}"
)


# ============================================================
# 5. METRIC FUNCTIONS
# ============================================================

def mae(y_true, y_pred):

    return np.mean(
        np.abs(
            y_true - y_pred
        )
    )


def rmse(y_true, y_pred):

    return np.sqrt(
        np.mean(
            (
                y_true - y_pred
            ) ** 2
        )
    )


def wape(y_true, y_pred):

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


def smape(y_true, y_pred):

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


def r2_score_manual(
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
        ss_res / ss_tot
    )


# ============================================================
# 6. CREATE TRAINING SERIES
# ============================================================

print("\n" + "=" * 105)
print("1. DISTRICT-SPECIFIC TRAINING-ONLY SARIMA ORDER SEARCH")
print("=" * 105)


districts = sorted(
    base_df[
        "District"
    ]
    .unique()
)


order_search_records = []

best_order_records = []


best_orders = {}


# ============================================================
# 7. TRAIN-ONLY SARIMA ORDER SEARCH
# ============================================================

for district in districts:

    print(
        f"\nSearching SARIMA order for: "
        f"{district}"
    )


    district_train = (

        base_df[
            (
                base_df[
                    "District"
                ]
                == district
            )
            &
            (
                base_df[
                    "Date"
                ]
                <= TRAIN_CUTOFF
            )
        ]
        [
            [
                "Date",
                TARGET
            ]
        ]
        .copy()
    )


    district_train = (

        district_train
        .set_index("Date")[TARGET]
        .asfreq("MS")
    )


    non_missing_count = (
        district_train
        .notna()
        .sum()
    )


    if non_missing_count < 36:

        raise ValueError(
            f"{district}: Insufficient training observations."
        )


    best_aic = np.inf

    best_order = None

    best_seasonal_order = None

    best_converged = False

    best_result = None


    # --------------------------------------------------------
    # Search candidate SARIMA configurations
    # --------------------------------------------------------

    for order in ORDER_CANDIDATES:

        for seasonal_order in SEASONAL_ORDER_CANDIDATES:

            try:

                model = SARIMAX(

                    district_train,

                    order=order,

                    seasonal_order=seasonal_order,

                    trend="n",

                    enforce_stationarity=False,

                    enforce_invertibility=False
                )


                result = model.fit(

                    disp=False,

                    maxiter=200
                )


                model_aic = (
                    result.aic
                )


                converged = bool(

                    result
                    .mle_retvals
                    .get(
                        "converged",
                        True
                    )
                )


                order_search_records.append({

                    "District":
                        district,

                    "Order":
                        str(order),

                    "Seasonal_Order":
                        str(seasonal_order),

                    "AIC":
                        model_aic,

                    "Converged":
                        converged,

                    "Status":
                        "SUCCESS"
                })


                # Prefer converged models.
                #
                # If no converged model has yet been found,
                # we temporarily allow the best finite-AIC
                # model as a fallback.

                should_update = False


                if np.isfinite(model_aic):

                    if (
                        converged
                        and
                        (
                            not best_converged
                            or
                            model_aic < best_aic
                        )
                    ):

                        should_update = True


                    elif (
                        not best_converged
                        and
                        model_aic < best_aic
                    ):

                        should_update = True


                if should_update:

                    best_aic = (
                        model_aic
                    )

                    best_order = (
                        order
                    )

                    best_seasonal_order = (
                        seasonal_order
                    )

                    best_converged = (
                        converged
                    )

                    best_result = (
                        result
                    )


            except Exception as error:

                order_search_records.append({

                    "District":
                        district,

                    "Order":
                        str(order),

                    "Seasonal_Order":
                        str(seasonal_order),

                    "AIC":
                        np.nan,

                    "Converged":
                        False,

                    "Status":
                        f"FAILED: {type(error).__name__}"
                })


    # --------------------------------------------------------
    # Ensure a valid model was found
    # --------------------------------------------------------

    if best_order is None:

        raise RuntimeError(
            f"No SARIMA configuration succeeded "
            f"for {district}."
        )


    # --------------------------------------------------------
    # Residual diagnostic on selected training model
    # --------------------------------------------------------

    residuals = (
        pd.Series(
            best_result.resid
        )
        .dropna()
    )


    # Remove early initialization residuals.

    if len(residuals) > 12:

        residuals_for_test = (
            residuals.iloc[12:]
        )

    else:

        residuals_for_test = (
            residuals
        )


    if len(residuals_for_test) >= 24:

        ljung_box = acorr_ljungbox(

            residuals_for_test,

            lags=[12],

            return_df=True
        )


        ljung_box_stat = float(
            ljung_box[
                "lb_stat"
            ]
            .iloc[0]
        )


        ljung_box_pvalue = float(
            ljung_box[
                "lb_pvalue"
            ]
            .iloc[0]
        )

    else:

        ljung_box_stat = np.nan
        ljung_box_pvalue = np.nan


    best_orders[
        district
    ] = {

        "order":
            best_order,

        "seasonal_order":
            best_seasonal_order
    }


    best_order_records.append({

        "District":
            district,

        "Training_Non_Missing_Observations":
            int(
                non_missing_count
            ),

        "Best_Order":
            str(
                best_order
            ),

        "Best_Seasonal_Order":
            str(
                best_seasonal_order
            ),

        "Best_AIC":
            best_aic,

        "Converged":
            best_converged,

        "Residual_Mean":
            residuals.mean(),

        "Residual_SD":
            residuals.std(),

        "Ljung_Box_Lag_12_Statistic":
            ljung_box_stat,

        "Ljung_Box_Lag_12_PValue":
            ljung_box_pvalue
    })


    print(
        f"Selected: "
        f"SARIMA{best_order}"
        f"x{best_seasonal_order} "
        f"AIC={best_aic:.2f} "
        f"Converged={best_converged}"
    )


# ============================================================
# 8. SAVE SARIMA ORDER SEARCH RESULTS
# ============================================================

order_search_df = pd.DataFrame(
    order_search_records
)


order_search_df.to_csv(

    REPORT_DIR
    / "11_sarima_order_search_results.csv",

    index=False
)


best_order_df = pd.DataFrame(
    best_order_records
)


best_order_df.to_csv(

    REPORT_DIR
    / "11_sarima_selected_orders.csv",

    index=False
)


print("\n" + "=" * 105)
print("SELECTED SARIMA ORDERS")
print("=" * 105)


print(
    best_order_df[
        [
            "District",
            "Best_Order",
            "Best_Seasonal_Order",
            "Best_AIC",
            "Converged",
            "Ljung_Box_Lag_12_PValue"
        ]
    ]
    .round(4)
    .to_string(index=False)
)


print(
    "\nResidual diagnostic interpretation:"
)

print(
    "Ljung-Box p-value > 0.05 suggests no strong "
    "remaining lag-12 residual autocorrelation."
)

print(
    "This diagnostic is used for model assessment, "
    "not as the only selection criterion."
)


# ============================================================
# 9. LOAD 2024 VALIDATION REQUESTS
# ============================================================

print("\n" + "=" * 105)
print("2. BUILD ROLLING-ORIGIN VALIDATION REQUESTS")
print("=" * 105)


validation_requests = []


for horizon in HORIZONS:

    validation_path = (

        SPLIT_DIR
        / f"h{horizon}_validation.csv"
    )


    if not validation_path.exists():

        raise FileNotFoundError(
            f"Validation dataset not found: "
            f"{validation_path}"
        )


    validation_df = pd.read_csv(
        validation_path
    )


    validation_df[
        "Forecast_Origin_Date"
    ] = pd.to_datetime(
        validation_df[
            "Forecast_Origin_Date"
        ]
    )


    validation_df[
        "Forecast_Target_Date"
    ] = pd.to_datetime(
        validation_df[
            "Forecast_Target_Date"
        ]
    )


    validation_df[
        "Evaluation_Horizon"
    ] = horizon


    validation_requests.append(

        validation_df[
            [
                "District",
                "Forecast_Origin_Date",
                "Forecast_Target_Date",
                "Forecast_Target",
                "Evaluation_Horizon"
            ]
        ]
    )


requests_df = pd.concat(

    validation_requests,

    ignore_index=True
)


requests_df = (

    requests_df
    .sort_values(
        [
            "District",
            "Forecast_Origin_Date",
            "Evaluation_Horizon"
        ]
    )
    .reset_index(drop=True)
)


print(
    f"Total validation forecast requests: "
    f"{len(requests_df)}"
)

print(
    f"Unique district-origin combinations: "
    f"{requests_df[['District', 'Forecast_Origin_Date']].drop_duplicates().shape[0]}"
)


# ============================================================
# 10. ROLLING-ORIGIN SARIMA VALIDATION
# ============================================================

print("\n" + "=" * 105)
print("3. ROLLING-ORIGIN SARIMA VALIDATION")
print("=" * 105)


prediction_records = []


grouped_requests = (
    requests_df
    .groupby(
        [
            "District",
            "Forecast_Origin_Date"
        ],
        sort=True
    )
)


total_groups = (
    grouped_requests
    .ngroups
)


current_group = 0


for (
    district,
    forecast_origin
), group in grouped_requests:

    current_group += 1


    if (
        current_group == 1
        or
        current_group % 25 == 0
        or
        current_group == total_groups
    ):

        print(
            f"Processing rolling origin "
            f"{current_group}/{total_groups}"
        )


    selected_order = (
        best_orders[
            district
        ]["order"]
    )


    selected_seasonal_order = (
        best_orders[
            district
        ]["seasonal_order"]
    )


    # --------------------------------------------------------
    # Historical data available at forecast origin only
    # --------------------------------------------------------

    history = (

        base_df[
            (
                base_df[
                    "District"
                ]
                == district
            )
            &
            (
                base_df[
                    "Date"
                ]
                <= forecast_origin
            )
        ]
        [
            [
                "Date",
                TARGET
            ]
        ]
        .copy()
    )


    history_series = (

        history
        .set_index(
            "Date"
        )[TARGET]
        .asfreq("MS")
    )


    # Maximum requested horizon at this origin.

    max_horizon = int(
        group[
            "Evaluation_Horizon"
        ]
        .max()
    )


    model_failed = False

    failure_reason = None


    try:

        model = SARIMAX(

            history_series,

            order=selected_order,

            seasonal_order=selected_seasonal_order,

            trend="n",

            enforce_stationarity=False,

            enforce_invertibility=False
        )


        fitted_model = model.fit(

            disp=False,

            maxiter=200
        )


        forecast_values = (

            fitted_model
            .forecast(
                steps=max_horizon
            )
        )


        forecast_values = np.asarray(
            forecast_values,
            dtype=float
        )


    except Exception as error:

        model_failed = True

        failure_reason = (
            f"{type(error).__name__}: "
            f"{str(error)}"
        )

        forecast_values = None


    # --------------------------------------------------------
    # Store every H1/H3/H6 request for this origin
    # --------------------------------------------------------

    for _, request in group.iterrows():

        horizon = int(
            request[
                "Evaluation_Horizon"
            ]
        )


        if model_failed:

            prediction = np.nan

        else:

            prediction = float(
                forecast_values[
                    horizon - 1
                ]
            )


        prediction_records.append({

            "District":
                district,

            "Forecast_Origin_Date":
                forecast_origin,

            "Forecast_Target_Date":
                request[
                    "Forecast_Target_Date"
                ],

            "Horizon_Months":
                horizon,

            "Actual_Target":
                request[
                    "Forecast_Target"
                ],

            "SARIMA_Prediction":
                prediction,

            "SARIMA_Order":
                str(
                    selected_order
                ),

            "SARIMA_Seasonal_Order":
                str(
                    selected_seasonal_order
                ),

            "Model_Failed":
                model_failed,

            "Failure_Reason":
                failure_reason
        })


predictions_df = pd.DataFrame(
    prediction_records
)


predictions_df.to_csv(

    REPORT_DIR
    / "11_sarima_validation_predictions.csv",

    index=False
)


# ============================================================
# 11. VALIDATION METRICS BY HORIZON
# ============================================================

print("\n" + "=" * 105)
print("4. SARIMA VALIDATION METRICS")
print("=" * 105)


metric_records = []


for horizon in HORIZONS:

    horizon_df = (

        predictions_df[
            predictions_df[
                "Horizon_Months"
            ]
            == horizon
        ]
        .copy()
    )


    total_rows = (
        len(
            horizon_df
        )
    )


    valid_predictions = (

        horizon_df[
            [
                "Actual_Target",
                "SARIMA_Prediction"
            ]
        ]
        .dropna()
    )


    evaluated_rows = (
        len(
            valid_predictions
        )
    )


    coverage = (
        evaluated_rows
        /
        total_rows
        *
        100
    )


    if evaluated_rows == 0:

        metric_records.append({

            "Horizon_Months":
                horizon,

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
        })


        continue


    y_true = (

        valid_predictions[
            "Actual_Target"
        ]
        .to_numpy(
            dtype=float
        )
    )


    y_pred = (

        valid_predictions[
            "SARIMA_Prediction"
        ]
        .to_numpy(
            dtype=float
        )
    )


    metric_records.append({

        "Horizon_Months":
            horizon,

        "Total_Validation_Rows":
            total_rows,

        "Evaluated_Rows":
            evaluated_rows,

        "Coverage_Percentage":
            coverage,

        "MAE":
            mae(
                y_true,
                y_pred
            ),

        "RMSE":
            rmse(
                y_true,
                y_pred
            ),

        "WAPE_Percentage":
            wape(
                y_true,
                y_pred
            ),

        "sMAPE_Percentage":
            smape(
                y_true,
                y_pred
            ),

        "R2":
            r2_score_manual(
                y_true,
                y_pred
            )
    })


metrics_df = pd.DataFrame(
    metric_records
)


print(
    metrics_df
    .round(4)
    .to_string(index=False)
)


metrics_df.to_csv(

    REPORT_DIR
    / "11_sarima_validation_metrics.csv",

    index=False
)


# ============================================================
# 12. DISTRICT-LEVEL VALIDATION METRICS
# ============================================================

district_metric_records = []


for (
    horizon,
    district
), group in predictions_df.groupby(
    [
        "Horizon_Months",
        "District"
    ]
):


    valid = (

        group[
            [
                "Actual_Target",
                "SARIMA_Prediction"
            ]
        ]
        .dropna()
    )


    if len(valid) == 0:

        continue


    y_true = (
        valid[
            "Actual_Target"
        ]
        .to_numpy(
            dtype=float
        )
    )


    y_pred = (
        valid[
            "SARIMA_Prediction"
        ]
        .to_numpy(
            dtype=float
        )
    )


    district_metric_records.append({

        "Horizon_Months":
            horizon,

        "District":
            district,

        "Evaluated_Rows":
            len(valid),

        "MAE":
            mae(
                y_true,
                y_pred
            ),

        "RMSE":
            rmse(
                y_true,
                y_pred
            ),

        "WAPE_Percentage":
            wape(
                y_true,
                y_pred
            ),

        "sMAPE_Percentage":
            smape(
                y_true,
                y_pred
            )
    })


district_metrics_df = pd.DataFrame(
    district_metric_records
)


district_metrics_df.to_csv(

    REPORT_DIR
    / "11_sarima_district_validation_metrics.csv",

    index=False
)


# ============================================================
# 13. COMPARE WITH SEASONAL NAIVE BASELINE
# ============================================================

baseline_metrics_path = (

    REPORT_DIR
    / "10_baseline_validation_metrics.csv"
)


if baseline_metrics_path.exists():

    baseline_df = pd.read_csv(
        baseline_metrics_path
    )


    seasonal_baseline = (

        baseline_df[
            baseline_df[
                "Baseline"
            ]
            == "Seasonal Naive"
        ]
        [
            [
                "Horizon_Months",
                "MAE",
                "RMSE",
                "WAPE_Percentage",
                "sMAPE_Percentage",
                "R2"
            ]
        ]
        .copy()
    )


    seasonal_baseline = (

        seasonal_baseline
        .rename(
            columns={
                "MAE":
                    "Seasonal_Naive_MAE",

                "RMSE":
                    "Seasonal_Naive_RMSE",

                "WAPE_Percentage":
                    "Seasonal_Naive_WAPE",

                "sMAPE_Percentage":
                    "Seasonal_Naive_sMAPE",

                "R2":
                    "Seasonal_Naive_R2"
            }
        )
    )


    comparison_df = (

        metrics_df
        .merge(
            seasonal_baseline,
            on="Horizon_Months",
            how="left"
        )
    )


    comparison_df[
        "SARIMA_MAE_Difference_vs_Seasonal"
    ] = (

        comparison_df[
            "MAE"
        ]
        -
        comparison_df[
            "Seasonal_Naive_MAE"
        ]
    )


    comparison_df[
        "SARIMA_RMSE_Difference_vs_Seasonal"
    ] = (

        comparison_df[
            "RMSE"
        ]
        -
        comparison_df[
            "Seasonal_Naive_RMSE"
        ]
    )


    print("\n" + "=" * 105)
    print("SARIMA VS SEASONAL NAIVE VALIDATION COMPARISON")
    print("=" * 105)


    print(
        comparison_df[
            [
                "Horizon_Months",
                "MAE",
                "Seasonal_Naive_MAE",
                "SARIMA_MAE_Difference_vs_Seasonal",
                "RMSE",
                "Seasonal_Naive_RMSE",
                "R2",
                "Seasonal_Naive_R2"
            ]
        ]
        .round(4)
        .to_string(index=False)
    )


    comparison_df.to_csv(

        REPORT_DIR
        / "11_sarima_vs_seasonal_baseline.csv",

        index=False
    )


# ============================================================
# 14. CREATE VALIDATION TREND FIGURES
# ============================================================

for horizon in HORIZONS:

    horizon_predictions = (

        predictions_df[
            predictions_df[
                "Horizon_Months"
            ]
            == horizon
        ]
        .copy()
    )


    monthly_plot = (

        horizon_predictions
        .groupby(
            "Forecast_Target_Date"
        )
        .agg(
            Actual_Mean=(
                "Actual_Target",
                "mean"
            ),

            SARIMA_Mean=(
                "SARIMA_Prediction",
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
            "SARIMA_Mean"
        ],

        marker="o",

        label="SARIMA"
    )


    plt.title(
        f"SARIMA Validation Forecast - H{horizon}"
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
        / f"11_sarima_h{horizon}_validation_trend.png",

        dpi=300
    )


    plt.close()


# ============================================================
# 15. MODEL FAILURE SUMMARY
# ============================================================

failure_summary = (

    predictions_df
    .groupby(
        "Horizon_Months"
    )[
        "Model_Failed"
    ]
    .agg(
        Total_Requests="count",
        Failed_Requests="sum"
    )
    .reset_index()
)


failure_summary[
    "Failure_Percentage"
] = (

    failure_summary[
        "Failed_Requests"
    ]
    /
    failure_summary[
        "Total_Requests"
    ]
    *
    100
)


failure_summary.to_csv(

    REPORT_DIR
    / "11_sarima_failure_summary.csv",

    index=False
)


print("\n" + "=" * 105)
print("SARIMA FORECAST FAILURE SUMMARY")
print("=" * 105)


print(
    failure_summary
    .round(2)
    .to_string(index=False)
)


# ============================================================
# 16. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 105)
print("STEP 11 SUMMARY")
print("=" * 105)


print(
    "SARIMA candidate-model analysis completed."
)


print(
    "\nMethodology:"
)

print(
    "- One SARIMA model structure selected per district"
)

print(
    "- SARIMA orders selected using training-period AIC"
)

print(
    "- Monthly seasonal period = 12"
)

print(
    "- Rolling-origin validation used for 2024"
)

print(
    "- Each forecast uses history available only "
    "up to its forecast origin"
)

print(
    "- H1, H3 and H6 evaluated separately"
)

print(
    "- Residual lag-12 Ljung-Box diagnostic recorded"
)

print(
    "- 2025 final test targets were not evaluated"
)


print(
    "\nIMPORTANT:"
)

print(
    "The final forecasting model is NOT selected yet."
)

print(
    "SARIMA results will later be compared with "
    "XGBoost, LSTM and NGBoost."
)


print(
    "\nNEXT STEP:"
)

print(
    "XGBoost regression model analysis."
)


print("\nReports saved to:")
print(REPORT_DIR)

print("\nFigures saved to:")
print(FIGURE_DIR)


print(
    "\nSTEP 11 - SARIMA MODEL ANALYSIS COMPLETE"
)

print("=" * 105)