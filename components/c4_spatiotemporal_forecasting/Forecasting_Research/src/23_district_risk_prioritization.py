# ============================================================
# STEP 23 - DISTRICT RISK LEVEL + PRIORITIZATION
# Childhood Malnutrition Forecasting Research
#
# PURPOSE
# -------
# Convert the final frozen Random Forest forecasts from Step 21
# into:
#   1) LOW / MEDIUM / HIGH district risk levels
#   2) district priority ranks
#
# METHODOLOGY PROTECTION
# ----------------------
# - NO model training
# - NO hyperparameter tuning
# - NO model selection
# - NO use of 2025 actual targets to define risk thresholds
# - Risk thresholds are frozen from historical 2015-2023
#   observed malnutrition counts only
# - Step 21 final predictions are used unchanged
#
# RISK RULE
# ---------
# LOW    : predicted count <= historical 33rd percentile
# MEDIUM : 33rd percentile < predicted count <= 67th percentile
# HIGH   : predicted count > historical 67th percentile
#
# PRIORITY RULE
# -------------
# Within each Forecast_Target_Date + Horizon:
#   Priority Rank 1 = highest predicted malnutrition burden
#   Priority Rank 25 = lowest predicted malnutrition burden
# ============================================================

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd


# ============================================================
# 1. SETTINGS
# ============================================================

warnings.filterwarnings("ignore")

HORIZONS = [1, 3, 6]

TARGET = "Malnutrition_Cases"

HISTORICAL_START_YEAR = 2015
HISTORICAL_END_YEAR = 2023

LOW_QUANTILE = 0.33
HIGH_QUANTILE = 0.67

EXPECTED_DISTRICTS = 25
EXPECTED_ROWS_PER_HORIZON = 300


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
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

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

HISTORICAL_DATA_PATH = (
    PROCESSED_DIR
    / "malnutrition_preprocessed_base.csv"
)

STEP21_PREDICTION_PATH = (
    REPORT_DIR
    / "21_final_2025_lockbox_predictions.csv"
)


# ============================================================
# 3. INTRODUCTION
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "STEP 23 - DISTRICT RISK LEVEL + PRIORITIZATION"
)

print(
    "=" * 120
)

print(
    "\nMethodology protection:"
)

print(
    "- Step 21 final predictions are used unchanged"
)

print(
    "- No model training or tuning is performed"
)

print(
    "- 2025 actual targets are NOT used to define risk thresholds"
)

print(
    "- Risk thresholds are derived only from 2015-2023 historical target values"
)

print(
    "- District priority is based on predicted burden within each target month and horizon"
)


# ============================================================
# 4. INPUT CHECK
# ============================================================

for path in [
    HISTORICAL_DATA_PATH,
    STEP21_PREDICTION_PATH,
]:

    if not path.exists():

        raise FileNotFoundError(
            "Required input file was not found:\n"
            f"{path}"
        )


print(
    "\nInput files found successfully."
)


# ============================================================
# 5. LOAD HISTORICAL DATA
# ============================================================

historical_df = pd.read_csv(
    HISTORICAL_DATA_PATH
)


required_historical_columns = {
    "Year",
    TARGET,
}


missing_historical_columns = (
    required_historical_columns
    -
    set(
        historical_df.columns
    )
)


if missing_historical_columns:

    raise ValueError(
        "Historical data is missing required columns: "
        f"{sorted(missing_historical_columns)}"
    )


historical_df[
    "Year"
] = pd.to_numeric(
    historical_df[
        "Year"
    ],
    errors="coerce",
)


historical_df[
    TARGET
] = pd.to_numeric(
    historical_df[
        TARGET
    ],
    errors="coerce",
)


threshold_source_df = (
    historical_df[
        historical_df[
            "Year"
        ]
        .between(
            HISTORICAL_START_YEAR,
            HISTORICAL_END_YEAR,
            inclusive="both",
        )
    ]
    .copy()
)


threshold_source_df = (
    threshold_source_df[
        threshold_source_df[
            TARGET
        ]
        .notna()
    ]
    .copy()
)


if threshold_source_df.empty:

    raise ValueError(
        "No valid 2015-2023 historical target values were available "
        "for risk-threshold calculation."
    )


# ============================================================
# 6. FREEZE HISTORICAL RISK THRESHOLDS
# ============================================================

low_threshold = float(
    threshold_source_df[
        TARGET
    ]
    .quantile(
        LOW_QUANTILE
    )
)


high_threshold = float(
    threshold_source_df[
        TARGET
    ]
    .quantile(
        HIGH_QUANTILE
    )
)


if not (
    np.isfinite(
        low_threshold
    )
    and
    np.isfinite(
        high_threshold
    )
):

    raise ValueError(
        "Risk thresholds are not finite."
    )


if (
    low_threshold
    >=
    high_threshold
):

    raise ValueError(
        "Invalid risk thresholds: low threshold must be below high threshold."
    )


print(
    "\n"
    + "=" * 120
)

print(
    "FROZEN HISTORICAL RISK THRESHOLDS"
)

print(
    "=" * 120
)

print(
    f"Historical period       : "
    f"{HISTORICAL_START_YEAR}-{HISTORICAL_END_YEAR}"
)

print(
    f"Historical target rows  : "
    f"{len(threshold_source_df)}"
)

print(
    f"33rd percentile         : "
    f"{low_threshold:.4f}"
)

print(
    f"67th percentile         : "
    f"{high_threshold:.4f}"
)

print(
    "\nRisk definition:"
)

print(
    f"LOW    : Prediction <= {low_threshold:.4f}"
)

print(
    f"MEDIUM : {low_threshold:.4f} < Prediction <= {high_threshold:.4f}"
)

print(
    f"HIGH   : Prediction > {high_threshold:.4f}"
)


# ============================================================
# 7. LOAD STEP 21 FINAL PREDICTIONS
# ============================================================

prediction_df = pd.read_csv(
    STEP21_PREDICTION_PATH
)


required_prediction_columns = {
    "Horizon_Months",
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Prediction",
}


missing_prediction_columns = (
    required_prediction_columns
    -
    set(
        prediction_df.columns
    )
)


if missing_prediction_columns:

    raise ValueError(
        "Step 21 prediction file is missing required columns: "
        f"{sorted(missing_prediction_columns)}"
    )


prediction_df[
    "Forecast_Origin_Date"
] = pd.to_datetime(
    prediction_df[
        "Forecast_Origin_Date"
    ]
)


prediction_df[
    "Forecast_Target_Date"
] = pd.to_datetime(
    prediction_df[
        "Forecast_Target_Date"
    ]
)


prediction_df[
    "Prediction"
] = pd.to_numeric(
    prediction_df[
        "Prediction"
    ],
    errors="coerce",
)


if prediction_df[
    "Prediction"
].isna().any():

    raise ValueError(
        "Step 21 prediction file contains missing/non-numeric predictions."
    )


# ============================================================
# 8. HARD VALIDATION CHECKS
# ============================================================

for horizon in HORIZONS:

    horizon_df = (
        prediction_df[
            prediction_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
        .copy()
    )


    if (
        len(
            horizon_df
        )
        !=
        EXPECTED_ROWS_PER_HORIZON
    ):

        raise ValueError(
            f"H{horizon}: expected {EXPECTED_ROWS_PER_HORIZON} predictions, "
            f"found {len(horizon_df)}."
        )


    if not (
        horizon_df[
            "Forecast_Target_Date"
        ]
        .dt
        .year
        .eq(
            2025
        )
        .all()
    ):

        raise AssertionError(
            f"H{horizon}: target dates are not exclusively in 2025."
        )


    district_count = (
        horizon_df[
            "District"
        ]
        .nunique()
    )


    if (
        district_count
        !=
        EXPECTED_DISTRICTS
    ):

        raise ValueError(
            f"H{horizon}: expected {EXPECTED_DISTRICTS} districts, "
            f"found {district_count}."
        )


    target_month_counts = (
        horizon_df
        .groupby(
            "Forecast_Target_Date"
        )
        .size()
    )


    if not (
        target_month_counts
        .eq(
            EXPECTED_DISTRICTS
        )
        .all()
    ):

        raise ValueError(
            f"H{horizon}: every 2025 target month must contain "
            f"{EXPECTED_DISTRICTS} district predictions."
        )


    print(
        f"H{horizon}: "
        f"rows={len(horizon_df)}, "
        f"districts={district_count}, "
        f"target months={horizon_df['Forecast_Target_Date'].nunique()} "
        f"[PASS]"
    )


# ============================================================
# 9. ASSIGN RISK LEVEL
# ============================================================

def assign_risk_level(
    prediction,
):

    if (
        prediction
        <=
        low_threshold
    ):

        return "LOW"

    elif (
        prediction
        <=
        high_threshold
    ):

        return "MEDIUM"

    else:

        return "HIGH"


prediction_df[
    "Risk_Level"
] = (
    prediction_df[
        "Prediction"
    ]
    .apply(
        assign_risk_level
    )
)


prediction_df[
    "Risk_Score"
] = (
    prediction_df[
        "Risk_Level"
    ]
    .map({
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
    })
    .astype(int)
)


# ============================================================
# 10. DISTRICT PRIORITY RANK
# ============================================================

prediction_df[
    "Priority_Rank"
] = (
    prediction_df
    .groupby(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
        ]
    )[
        "Prediction"
    ]
    .rank(
        method="first",
        ascending=False,
    )
    .astype(int)
)


prediction_df[
    "Priority_Percentile"
] = (
    prediction_df
    .groupby(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
        ]
    )[
        "Prediction"
    ]
    .rank(
        method="average",
        ascending=True,
        pct=True,
    )
    *
    100
)


# ============================================================
# 11. PRIORITY BAND
# ============================================================

def assign_priority_band(
    rank,
):

    if rank <= 5:

        return "VERY HIGH PRIORITY"

    elif rank <= 10:

        return "HIGH PRIORITY"

    elif rank <= 15:

        return "MEDIUM PRIORITY"

    elif rank <= 20:

        return "LOW PRIORITY"

    else:

        return "VERY LOW PRIORITY"


prediction_df[
    "Priority_Band"
] = (
    prediction_df[
        "Priority_Rank"
    ]
    .apply(
        assign_priority_band
    )
)


# ============================================================
# 12. ADD THRESHOLD METADATA
# ============================================================

prediction_df[
    "Low_Risk_Threshold"
] = (
    low_threshold
)


prediction_df[
    "High_Risk_Threshold"
] = (
    high_threshold
)


prediction_df[
    "Threshold_Source_Period"
] = (
    f"{HISTORICAL_START_YEAR}-{HISTORICAL_END_YEAR}"
)


prediction_df[
    "Threshold_Method"
] = (
    "Historical target 33rd/67th percentiles"
)


# ============================================================
# 13. FINAL COLUMN ORDER
# ============================================================

preferred_columns = [
    "Horizon_Months",
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Prediction",
    "Risk_Level",
    "Risk_Score",
    "Priority_Rank",
    "Priority_Percentile",
    "Priority_Band",
    "Low_Risk_Threshold",
    "High_Risk_Threshold",
    "Threshold_Source_Period",
    "Threshold_Method",
]


final_columns = [
    column
    for column in preferred_columns
    if column in prediction_df.columns
]


risk_output_df = (
    prediction_df[
        final_columns
    ]
    .sort_values(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
            "Priority_Rank",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 14. SAVE FULL RISK + PRIORITIZATION OUTPUT
# ============================================================

risk_output_path = (
    REPORT_DIR
    / "23_district_risk_prioritization.csv"
)


risk_output_df.to_csv(
    risk_output_path,
    index=False,
)


# ============================================================
# 15. MONTHLY RISK SUMMARY
# ============================================================

monthly_risk_summary = (
    risk_output_df
    .groupby(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
            "Risk_Level",
        ],
        as_index=False,
    )
    .agg(
        District_Count=(
            "District",
            "count"
        ),

        Mean_Predicted_Cases=(
            "Prediction",
            "mean"
        ),

        Min_Predicted_Cases=(
            "Prediction",
            "min"
        ),

        Max_Predicted_Cases=(
            "Prediction",
            "max"
        ),
    )
)


risk_order = pd.CategoricalDtype(
    categories=[
        "HIGH",
        "MEDIUM",
        "LOW",
    ],
    ordered=True,
)


monthly_risk_summary[
    "Risk_Level"
] = (
    monthly_risk_summary[
        "Risk_Level"
    ]
    .astype(
        risk_order
    )
)


monthly_risk_summary = (
    monthly_risk_summary
    .sort_values(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
            "Risk_Level",
        ]
    )
)


monthly_summary_path = (
    REPORT_DIR
    / "23_monthly_risk_summary.csv"
)


monthly_risk_summary.to_csv(
    monthly_summary_path,
    index=False,
)


# ============================================================
# 16. TOP-5 PRIORITY DISTRICTS
# ============================================================

top5_df = (
    risk_output_df[
        risk_output_df[
            "Priority_Rank"
        ]
        <=
        5
    ]
    .copy()
    .sort_values(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
            "Priority_Rank",
        ]
    )
)


top5_output_path = (
    REPORT_DIR
    / "23_top5_priority_districts.csv"
)


top5_df.to_csv(
    top5_output_path,
    index=False,
)


# ============================================================
# 17. DISTRICT-LEVEL 2025 SUMMARY
# ============================================================

district_summary = (
    risk_output_df
    .groupby(
        [
            "Horizon_Months",
            "District",
        ],
        as_index=False,
    )
    .agg(
        Mean_Predicted_Cases=(
            "Prediction",
            "mean"
        ),

        Maximum_Predicted_Cases=(
            "Prediction",
            "max"
        ),

        Minimum_Predicted_Cases=(
            "Prediction",
            "min"
        ),

        Mean_Priority_Rank=(
            "Priority_Rank",
            "mean"
        ),

        Best_Priority_Rank=(
            "Priority_Rank",
            "min"
        ),

        Worst_Priority_Rank=(
            "Priority_Rank",
            "max"
        ),

        High_Risk_Months=(
            "Risk_Level",
            lambda x:
                int(
                    (
                        x
                        ==
                        "HIGH"
                    )
                    .sum()
                )
        ),

        Medium_Risk_Months=(
            "Risk_Level",
            lambda x:
                int(
                    (
                        x
                        ==
                        "MEDIUM"
                    )
                    .sum()
                )
        ),

        Low_Risk_Months=(
            "Risk_Level",
            lambda x:
                int(
                    (
                        x
                        ==
                        "LOW"
                    )
                    .sum()
                )
        ),
    )
)


district_summary[
    "Mean_Priority_Rank"
] = (
    district_summary[
        "Mean_Priority_Rank"
    ]
    .round(
        2
    )
)


district_summary = (
    district_summary
    .sort_values(
        [
            "Horizon_Months",
            "Mean_Priority_Rank",
            "Mean_Predicted_Cases",
        ],
        ascending=[
            True,
            True,
            False,
        ],
    )
)


district_summary_path = (
    REPORT_DIR
    / "23_district_2025_risk_summary.csv"
)


district_summary.to_csv(
    district_summary_path,
    index=False,
)


# ============================================================
# 18. SAVE THRESHOLD AUDIT
# ============================================================

threshold_audit = {
    "step":
        23,

    "purpose":
        "District risk classification and prioritization",

    "historical_threshold_period":
        f"{HISTORICAL_START_YEAR}-{HISTORICAL_END_YEAR}",

    "historical_target":
        TARGET,

    "historical_rows_used":
        int(
            len(
                threshold_source_df
            )
        ),

    "low_quantile":
        LOW_QUANTILE,

    "high_quantile":
        HIGH_QUANTILE,

    "low_threshold":
        low_threshold,

    "high_threshold":
        high_threshold,

    "risk_rule": {
        "LOW":
            f"Prediction <= {low_threshold:.6f}",

        "MEDIUM":
            f"{low_threshold:.6f} < Prediction <= {high_threshold:.6f}",

        "HIGH":
            f"Prediction > {high_threshold:.6f}",
    },

    "priority_rule":
        "Rank districts within each horizon and target month by descending predicted malnutrition count",

    "methodology_protection": [
        "2025 actual targets were not used to calculate thresholds",
        "Step 21 predictions were used unchanged",
        "No model training was performed",
        "No tuning was performed",
        "No model reselection was performed",
    ],
}


threshold_audit_path = (
    REPORT_DIR
    / "23_risk_threshold_audit.json"
)


with open(
    threshold_audit_path,
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        threshold_audit,
        file,
        indent=4,
    )


# ============================================================
# 19. PRINT RESULT CHECKS
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "RISK CLASSIFICATION SUMMARY"
)

print(
    "=" * 120
)


risk_count_summary = (
    risk_output_df
    .groupby(
        [
            "Horizon_Months",
            "Risk_Level",
        ]
    )
    .size()
    .reset_index(
        name="Prediction_Rows"
    )
)


risk_count_summary[
    "Risk_Level"
] = (
    risk_count_summary[
        "Risk_Level"
    ]
    .astype(
        risk_order
    )
)


risk_count_summary = (
    risk_count_summary
    .sort_values(
        [
            "Horizon_Months",
            "Risk_Level",
        ]
    )
)


print(
    risk_count_summary
    .to_string(
        index=False
    )
)


# ============================================================
# 20. PRINT EXAMPLE TOP-5
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "EXAMPLE: FIRST TARGET MONTH TOP-5 PRIORITY DISTRICTS"
)

print(
    "=" * 120
)


for horizon in HORIZONS:

    horizon_df = (
        risk_output_df[
            risk_output_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
    )

    first_target_month = (
        horizon_df[
            "Forecast_Target_Date"
        ]
        .min()
    )

    example_df = (
        horizon_df[
            horizon_df[
                "Forecast_Target_Date"
            ]
            ==
            first_target_month
        ]
        .sort_values(
            "Priority_Rank"
        )
        .head(
            5
        )
    )


    print(
        f"\nH{horizon} | Target month: "
        f"{first_target_month.date()}"
    )


    print(
        example_df[
            [
                "Priority_Rank",
                "District",
                "Prediction",
                "Risk_Level",
                "Priority_Band",
            ]
        ]
        .round({
            "Prediction": 2
        })
        .to_string(
            index=False
        )
    )


# ============================================================
# 21. FINAL SUMMARY
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "STEP 23 SUMMARY"
)

print(
    "=" * 120
)

print(
    "- Historical 2015-2023 target distribution was used to freeze risk thresholds"
)

print(
    "- 2025 actual targets were NOT used to define LOW/MEDIUM/HIGH"
)

print(
    "- Final Step 21 predictions were classified into risk levels"
)

print(
    "- Districts were ranked separately for every target month and horizon"
)

print(
    "- Priority Rank 1 represents the highest predicted burden"
)

print(
    "- No model training, tuning, or reselection was performed"
)

print(
    "\nSaved reports:"
)

print(
    risk_output_path
)

print(
    monthly_summary_path
)

print(
    top5_output_path
)

print(
    district_summary_path
)

print(
    threshold_audit_path
)

print(
    "\nSTEP 23 - DISTRICT RISK LEVEL + PRIORITIZATION COMPLETE"
)

print(
    "=" * 120
)
