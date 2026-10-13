# ============================================================
# STEP 30 - FINAL FUTURE DISTRICT RISK / PRIORITY EXPORT
# UPDATED VERSION WITH NGBOOST UNCERTAINTY
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Prepare the FINAL GIS/frontend-ready future district dataset
# by combining:
#
#   Step 29F -> DMBI planning priority
#   Step 27B -> NGBoost probabilistic uncertainty
#
# IMPORTANT SYSTEM DESIGN
# -----------------------
# Random Forest:
#   -> final point forecast for malnutrition cases
#
# NGBoost:
#   -> separate probabilistic uncertainty layer
#   -> predictive mean and SD
#   -> 95% predictive interval
#   -> Low / Moderate / High uncertainty
#
# DMBI:
#   -> relative district planning priority
#
# THIS STEP DOES NOT
# ------------------
# - retrain Random Forest
# - retrain NGBoost
# - recalculate CRITIC weights
# - rerun TOPSIS
# - recalculate DMBI
# - change priority ranks
# - change priority levels
# - recalibrate uncertainty
#
# INPUTS
# ------
# outputs/reports/
#   29f_future_dmbi_critic_topsis_prioritization_2026_2030.csv
#
# outputs/reports/
#   27b_future_forecasts_with_ngboost_uncertainty_2026_2030.csv
#
# MAIN OUTPUT
# -----------
# outputs/reports/
#   30_future_district_risk_prioritization.csv
#
# NEXT
# ----
# Step 31 -> GIS priority mapping
# ============================================================

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# 1. SETTINGS
# ============================================================

DISTRICT = "District"
ORIGIN = "Forecast_Origin_Date"
TARGET = "Forecast_Target_Date"
HORIZON = "Horizon_Months"

EXPECTED_DISTRICTS = 25

EXPECTED_ROWS = {
    1: 1500,
    3: 1450,
    6: 1375,
}

EXPECTED_TOTAL = sum(
    EXPECTED_ROWS.values()
)

EXPECTED_TARGET_START = {
    1: pd.Timestamp("2026-01-01"),
    3: pd.Timestamp("2026-03-01"),
    6: pd.Timestamp("2026-06-01"),
}

EXPECTED_TARGET_END = pd.Timestamp(
    "2030-12-01"
)

PRIORITY_LEVELS = [
    "Low",
    "Medium",
    "High",
    "Critical",
]

PRIORITY_CODE = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4,
}

UNCERTAINTY_LEVELS = [
    "Low Uncertainty",
    "Moderate Uncertainty",
    "High Uncertainty",
]

POINT_FORECAST_TOLERANCE = 1e-6


# ============================================================
# 2. PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
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

STEP29F_PATH = (
    REPORT_DIR
    / "29f_future_dmbi_critic_topsis_prioritization_2026_2030.csv"
)

STEP27B_PATH = (
    REPORT_DIR
    / "27b_future_forecasts_with_ngboost_uncertainty_2026_2030.csv"
)

OUTPUT_PATH = (
    REPORT_DIR
    / "30_future_district_risk_prioritization.csv"
)

SUMMARY_PATH = (
    REPORT_DIR
    / "30_future_district_risk_prioritization_summary.csv"
)

UNCERTAINTY_SUMMARY_PATH = (
    REPORT_DIR
    / "30_future_uncertainty_summary.csv"
)

TOP5_PATH = (
    REPORT_DIR
    / "30_future_district_top5_priority.csv"
)

AUDIT_PATH = (
    REPORT_DIR
    / "30_future_district_risk_prioritization_audit.csv"
)

METHOD_PATH = (
    REPORT_DIR
    / "30_future_district_risk_prioritization_methodology.json"
)


# ============================================================
# 3. HELPERS
# ============================================================

def section(title):
    print(
        "\n"
        +
        "=" * 120
    )
    print(title)
    print("=" * 120)


def resolve_column(
    dataframe,
    candidates,
    required=True,
):
    for candidate in candidates:
        if candidate in dataframe.columns:
            return candidate

    if required:
        raise ValueError(
            "Could not find expected column. Tried: "
            f"{candidates}"
        )

    return None


def normalize_string_column(series):
    return (
        series
        .astype(str)
        .str.strip()
    )


# ============================================================
# 4. START
# ============================================================

section(
    "STEP 30 - FINAL FUTURE DISTRICT RISK / PRIORITY EXPORT WITH NGBOOST UNCERTAINTY"
)

print("\nSystem design:")
print("- Random Forest = final point forecast")
print("- NGBoost = separate uncertainty layer")
print("- DMBI = relative planning priority")
print("- Step 30 only joins + validates + exports")
print("- No model / CRITIC / TOPSIS / DMBI / uncertainty recalculation")


# ============================================================
# 5. REQUIRED FILES
# ============================================================

for required_path in [
    STEP29F_PATH,
    STEP27B_PATH,
]:
    if not required_path.exists():
        raise FileNotFoundError(
            f"Required file not found:\n"
            f"{required_path}"
        )


# ============================================================
# 6. LOAD STEP 29F DMBI OUTPUT
# ============================================================

section(
    "LOAD STEP 29F FINAL DMBI PRIORITIZATION"
)

dmbi = pd.read_csv(
    STEP29F_PATH,
    low_memory=False,
)

dmbi.columns = [
    str(column).strip()
    for column in dmbi.columns
]

required_dmbi = {
    DISTRICT,
    TARGET,
    HORIZON,
    "DMBI_Score_0_100",
    "Priority_Rank",
    "Priority_Level",
}

missing_dmbi = (
    required_dmbi
    -
    set(
        dmbi.columns
    )
)

if missing_dmbi:
    raise ValueError(
        "Step 29F missing required columns: "
        f"{sorted(missing_dmbi)}"
    )

dmbi_cases_col = resolve_column(
    dmbi,
    [
        "C1_Forecasted_Malnutrition_Cases",
        "Predicted_Cases",
        "Forecasted_Cases",
    ],
)

dmbi_rate_col = resolve_column(
    dmbi,
    [
        "C2_Forecasted_Cases_per_1000_U5",
        "Forecasted_Cases_per_1000_U5",
        "Cases_per_1000_U5",
    ],
)

dmbi_growth_col = resolve_column(
    dmbi,
    [
        "C3_Forecasted_YoY_Burden_Growth_Percent",
        "Forecasted_YoY_Burden_Growth_Percent",
        "YoY_Growth_Percent",
    ],
)

dmbi_origin_col = resolve_column(
    dmbi,
    [
        ORIGIN,
        "Origin_Date",
    ],
    required=False,
)

dmbi[DISTRICT] = normalize_string_column(
    dmbi[DISTRICT]
)

dmbi[TARGET] = pd.to_datetime(
    dmbi[TARGET],
    errors="coerce",
)

if dmbi_origin_col is not None:
    dmbi[dmbi_origin_col] = pd.to_datetime(
        dmbi[dmbi_origin_col],
        errors="coerce",
    )

dmbi[HORIZON] = pd.to_numeric(
    dmbi[HORIZON],
    errors="coerce",
)

for column in [
    dmbi_cases_col,
    dmbi_rate_col,
    dmbi_growth_col,
    "DMBI_Score_0_100",
    "Priority_Rank",
]:
    dmbi[column] = pd.to_numeric(
        dmbi[column],
        errors="coerce",
    )

if (
    dmbi[
        [
            DISTRICT,
            TARGET,
            HORIZON,
            dmbi_cases_col,
            dmbi_rate_col,
            dmbi_growth_col,
            "DMBI_Score_0_100",
            "Priority_Rank",
        ]
    ]
    .isna()
    .any()
    .any()
):
    raise ValueError(
        "Step 29F contains missing/invalid required values."
    )

print(
    f"Rows              : "
    f"{len(dmbi)}"
)

print(
    f"Districts         : "
    f"{dmbi[DISTRICT].nunique()}"
)

print(
    f"Target period     : "
    f"{dmbi[TARGET].min().date()} to "
    f"{dmbi[TARGET].max().date()}"
)


# ============================================================
# 7. LOAD STEP 27B NGBOOST UNCERTAINTY
# ============================================================

section(
    "LOAD STEP 27B FUTURE NGBOOST UNCERTAINTY"
)

uncertainty = pd.read_csv(
    STEP27B_PATH,
    low_memory=False,
)

uncertainty.columns = [
    str(column).strip()
    for column in uncertainty.columns
]

required_uncertainty = {
    DISTRICT,
    TARGET,
    HORIZON,
    "RF_Predicted_Cases",
    "NGBoost_Mean",
    "NGBoost_Predicted_SD",
    "NGBoost_Lower_95",
    "NGBoost_Upper_95",
    "NGBoost_Interval_Width",
    "NGBoost_Relative_Interval_Width",
    "Uncertainty_Level",
    "Confidence_Label",
    "Nominal_Interval_Percentage",
    "Validated_2025_Observed_Coverage_Percentage",
}

missing_uncertainty = (
    required_uncertainty
    -
    set(
        uncertainty.columns
    )
)

if missing_uncertainty:
    raise ValueError(
        "Step 27B missing required uncertainty columns: "
        f"{sorted(missing_uncertainty)}"
    )

uncertainty_origin_col = resolve_column(
    uncertainty,
    [
        ORIGIN,
        "Origin_Date",
    ],
    required=False,
)

uncertainty[DISTRICT] = normalize_string_column(
    uncertainty[DISTRICT]
)

uncertainty[TARGET] = pd.to_datetime(
    uncertainty[TARGET],
    errors="coerce",
)

if uncertainty_origin_col is not None:
    uncertainty[uncertainty_origin_col] = pd.to_datetime(
        uncertainty[uncertainty_origin_col],
        errors="coerce",
    )

uncertainty[HORIZON] = pd.to_numeric(
    uncertainty[HORIZON],
    errors="coerce",
)

uncertainty_numeric_columns = [
    "RF_Predicted_Cases",
    "NGBoost_Mean",
    "NGBoost_Predicted_SD",
    "NGBoost_Lower_95",
    "NGBoost_Upper_95",
    "NGBoost_Interval_Width",
    "NGBoost_Relative_Interval_Width",
    "Nominal_Interval_Percentage",
    "Validated_2025_Observed_Coverage_Percentage",
]

for column in uncertainty_numeric_columns:
    uncertainty[column] = pd.to_numeric(
        uncertainty[column],
        errors="coerce",
    )

if (
    uncertainty[
        [
            DISTRICT,
            TARGET,
            HORIZON,
            *uncertainty_numeric_columns,
            "Uncertainty_Level",
            "Confidence_Label",
        ]
    ]
    .isna()
    .any()
    .any()
):
    raise ValueError(
        "Step 27B contains missing/invalid required uncertainty values."
    )

print(
    f"Rows              : "
    f"{len(uncertainty)}"
)

print(
    f"Districts         : "
    f"{uncertainty[DISTRICT].nunique()}"
)

print(
    f"Target period     : "
    f"{uncertainty[TARGET].min().date()} to "
    f"{uncertainty[TARGET].max().date()}"
)


# ============================================================
# 8. VALIDATE BOTH INPUTS
# ============================================================

section(
    "VALIDATE DMBI + UNCERTAINTY INPUT STRUCTURE"
)

for name, dataframe in [
    (
        "Step 29F DMBI",
        dmbi,
    ),
    (
        "Step 27B uncertainty",
        uncertainty,
    ),
]:
    if len(dataframe) != EXPECTED_TOTAL:
        raise ValueError(
            f"{name}: expected {EXPECTED_TOTAL} rows, "
            f"found {len(dataframe)}."
        )

    if (
        dataframe[DISTRICT]
        .nunique()
        !=
        EXPECTED_DISTRICTS
    ):
        raise ValueError(
            f"{name}: expected 25 districts."
        )

    for horizon, expected_rows in EXPECTED_ROWS.items():

        horizon_df = dataframe[
            dataframe[HORIZON]
            ==
            horizon
        ]

        if len(horizon_df) != expected_rows:
            raise ValueError(
                f"{name} H{horizon}: expected "
                f"{expected_rows} rows, found "
                f"{len(horizon_df)}."
            )

        if (
            horizon_df[TARGET].min()
            !=
            EXPECTED_TARGET_START[
                horizon
            ]
        ):
            raise ValueError(
                f"{name} H{horizon}: unexpected first target."
            )

        if (
            horizon_df[TARGET].max()
            !=
            EXPECTED_TARGET_END
        ):
            raise ValueError(
                f"{name} H{horizon}: unexpected final target."
            )

    matrix_sizes = (
        dataframe
        .groupby(
            [
                TARGET,
                HORIZON,
            ]
        )[DISTRICT]
        .nunique()
    )

    if not (
        matrix_sizes
        ==
        EXPECTED_DISTRICTS
    ).all():
        raise ValueError(
            f"{name}: incomplete 25-district decision matrix."
        )

print(
    f"Step 29F rows      : "
    f"{len(dmbi)} [PASS]"
)

print(
    f"Step 27B rows      : "
    f"{len(uncertainty)} [PASS]"
)

print(
    f"Districts          : "
    f"25 [PASS]"
)


# ============================================================
# 9. UNIQUE JOIN KEYS
# ============================================================

section(
    "AUDIT JOIN KEYS"
)

join_keys = [
    DISTRICT,
    TARGET,
    HORIZON,
]

dmbi_duplicate_keys = int(
    dmbi
    .duplicated(
        subset=join_keys
    )
    .sum()
)

uncertainty_duplicate_keys = int(
    uncertainty
    .duplicated(
        subset=join_keys
    )
    .sum()
)

if dmbi_duplicate_keys != 0:
    raise ValueError(
        f"Step 29F duplicate join keys: "
        f"{dmbi_duplicate_keys}"
    )

if uncertainty_duplicate_keys != 0:
    raise ValueError(
        f"Step 27B duplicate join keys: "
        f"{uncertainty_duplicate_keys}"
    )

dmbi_keys = set(
    map(
        tuple,
        dmbi[
            join_keys
        ]
        .itertuples(
            index=False,
            name=None,
        )
    )
)

uncertainty_keys = set(
    map(
        tuple,
        uncertainty[
            join_keys
        ]
        .itertuples(
            index=False,
            name=None,
        )
    )
)

missing_in_uncertainty = (
    dmbi_keys
    -
    uncertainty_keys
)

extra_in_uncertainty = (
    uncertainty_keys
    -
    dmbi_keys
)

if missing_in_uncertainty:
    raise ValueError(
        f"{len(missing_in_uncertainty)} DMBI keys "
        f"are missing from Step 27B."
    )

if extra_in_uncertainty:
    raise ValueError(
        f"{len(extra_in_uncertainty)} Step 27B keys "
        f"are absent from Step 29F."
    )

print(
    f"Step 29F duplicate keys : "
    f"{dmbi_duplicate_keys} [PASS]"
)

print(
    f"Step 27B duplicate keys : "
    f"{uncertainty_duplicate_keys} [PASS]"
)

print(
    f"Exact key-set match     : "
    f"{len(dmbi_keys)} rows [PASS]"
)


# ============================================================
# 10. PREPARE UNCERTAINTY COLUMNS FOR JOIN
# ============================================================

uncertainty_keep = [
    *join_keys,
    "RF_Predicted_Cases",
    "NGBoost_Mean",
    "NGBoost_Predicted_SD",
    "NGBoost_Lower_95",
    "NGBoost_Upper_95",
    "NGBoost_Interval_Width",
    "NGBoost_Relative_Interval_Width",
    "Uncertainty_Level",
    "Confidence_Label",
    "Nominal_Interval_Percentage",
    "Validated_2025_Observed_Coverage_Percentage",
]

# Optional audit fields if Step 27B has them.
optional_uncertainty_columns = [
    "RF_Point_Inside_NGBoost_95",
]

for column in optional_uncertainty_columns:
    if column in uncertainty.columns:
        uncertainty_keep.append(
            column
        )

uncertainty_for_join = (
    uncertainty[
        uncertainty_keep
    ]
    .copy()
)


# ============================================================
# 11. JOIN STEP 29F + STEP 27B
# ============================================================

section(
    "JOIN DMBI PRIORITY WITH NGBOOST UNCERTAINTY"
)

merged = dmbi.merge(
    uncertainty_for_join,
    on=join_keys,
    how="left",
    validate="one_to_one",
    indicator=True,
)

join_failures = int(
    (
        merged[
            "_merge"
        ]
        !=
        "both"
    )
    .sum()
)

if join_failures != 0:
    raise ValueError(
        f"Uncertainty join failures: "
        f"{join_failures}"
    )

merged = merged.drop(
    columns=[
        "_merge"
    ]
)

print(
    f"Joined rows        : "
    f"{len(merged)} [PASS]"
)

print(
    f"Join failures      : "
    f"{join_failures} [PASS]"
)


# ============================================================
# 12. RF POINT FORECAST CONSISTENCY AUDIT
# ============================================================

section(
    "AUDIT RANDOM FOREST POINT FORECAST CONSISTENCY"
)

point_difference = (
    merged[
        dmbi_cases_col
    ]
    -
    merged[
        "RF_Predicted_Cases"
    ]
).abs()

max_point_difference = float(
    point_difference.max()
)

mean_point_difference = float(
    point_difference.mean()
)

if (
    max_point_difference
    >
    POINT_FORECAST_TOLERANCE
):
    raise ValueError(
        "Step 29F forecasted cases do not match "
        "Step 27B Random Forest point forecasts. "
        f"Max absolute difference="
        f"{max_point_difference:.12f}"
    )

print(
    "Max RF point difference  : "
    f"{max_point_difference:.12f} [PASS]"
)

print(
    "Mean RF point difference : "
    f"{mean_point_difference:.12f} [PASS]"
)


# ============================================================
# 13. UNCERTAINTY VALIDITY AUDIT
# ============================================================

section(
    "AUDIT NGBOOST UNCERTAINTY"
)

invalid_interval_count = int(
    (
        merged[
            "NGBoost_Lower_95"
        ]
        >
        merged[
            "NGBoost_Upper_95"
        ]
    )
    .sum()
)

negative_lower_count = int(
    (
        merged[
            "NGBoost_Lower_95"
        ]
        <
        0
    )
    .sum()
)

invalid_sd_count = int(
    (
        merged[
            "NGBoost_Predicted_SD"
        ]
        <=
        0
    )
    .sum()
)

invalid_width_count = int(
    (
        merged[
            "NGBoost_Interval_Width"
        ]
        <
        0
    )
    .sum()
)

unknown_uncertainty_levels = sorted(
    set(
        merged[
            "Uncertainty_Level"
        ]
        .astype(str)
        .unique()
    )
    -
    set(
        UNCERTAINTY_LEVELS
    )
)

if invalid_interval_count != 0:
    raise ValueError(
        f"Invalid NGBoost intervals: "
        f"{invalid_interval_count}"
    )

if negative_lower_count != 0:
    raise ValueError(
        f"Negative saved lower bounds: "
        f"{negative_lower_count}"
    )

if invalid_sd_count != 0:
    raise ValueError(
        f"Invalid NGBoost SD rows: "
        f"{invalid_sd_count}"
    )

if invalid_width_count != 0:
    raise ValueError(
        f"Invalid interval widths: "
        f"{invalid_width_count}"
    )

if unknown_uncertainty_levels:
    raise ValueError(
        "Unexpected uncertainty levels: "
        f"{unknown_uncertainty_levels}"
    )

print(
    f"Invalid intervals        : "
    f"{invalid_interval_count} [PASS]"
)

print(
    f"Negative lower bounds    : "
    f"{negative_lower_count} [PASS]"
)

print(
    f"Invalid predicted SD     : "
    f"{invalid_sd_count} [PASS]"
)

print(
    f"Invalid interval widths  : "
    f"{invalid_width_count} [PASS]"
)

print(
    "Uncertainty levels       : "
    "Low / Moderate / High [PASS]"
)


# ============================================================
# 14. ORIGIN DATE AUDIT
# ============================================================

section(
    "AUDIT FORECAST ORIGIN DATES"
)

origin_mismatch_count = 0

if (
    dmbi_origin_col is not None
    and
    uncertainty_origin_col is not None
):
    origin_compare = dmbi[
        join_keys
        +
        [
            dmbi_origin_col
        ]
    ].merge(
        uncertainty[
            join_keys
            +
            [
                uncertainty_origin_col
            ]
        ],
        on=join_keys,
        how="inner",
        suffixes=(
            "_DMBI",
            "_Uncertainty",
        ),
        validate="one_to_one",
    )

    left_origin = (
        origin_compare[
            f"{dmbi_origin_col}_DMBI"
        ]
        if (
            f"{dmbi_origin_col}_DMBI"
            in
            origin_compare.columns
        )
        else
        origin_compare[
            dmbi_origin_col
        ]
    )

    right_origin = (
        origin_compare[
            f"{uncertainty_origin_col}_Uncertainty"
        ]
        if (
            f"{uncertainty_origin_col}_Uncertainty"
            in
            origin_compare.columns
        )
        else
        origin_compare[
            uncertainty_origin_col
        ]
    )

    origin_mismatch_count = int(
        (
            left_origin
            !=
            right_origin
        )
        .sum()
    )

    if origin_mismatch_count != 0:
        raise ValueError(
            f"Forecast origin date mismatches: "
            f"{origin_mismatch_count}"
        )

print(
    f"Origin date mismatches   : "
    f"{origin_mismatch_count} [PASS]"
)


# ============================================================
# 15. BUILD FINAL MAP-READY OUTPUT
# ============================================================

section(
    "BUILD FINAL MAP-READY DATASET"
)

final = pd.DataFrame()

final[
    DISTRICT
] = merged[
    DISTRICT
].astype(str)

if dmbi_origin_col is not None:
    final[
        ORIGIN
    ] = merged[
        dmbi_origin_col
    ]
elif uncertainty_origin_col is not None:
    final[
        ORIGIN
    ] = (
        uncertainty[
            join_keys
            +
            [
                uncertainty_origin_col
            ]
        ]
        .rename(
            columns={
                uncertainty_origin_col:
                    ORIGIN
            }
        )
        .merge(
            merged[
                join_keys
            ],
            on=join_keys,
            how="right",
            validate="one_to_one",
        )[
            ORIGIN
        ]
    )
else:
    final[
        ORIGIN
    ] = [
        target_date
        -
        pd.DateOffset(
            months=int(
                horizon
            )
        )
        for (
            target_date,
            horizon,
        )
        in zip(
            merged[
                TARGET
            ],
            merged[
                HORIZON
            ],
        )
    ]

final[
    TARGET
] = merged[
    TARGET
]

final[
    HORIZON
] = (
    merged[
        HORIZON
    ]
    .astype(int)
)

# Main point forecast.
final[
    "RF_Predicted_Cases"
] = (
    merged[
        "RF_Predicted_Cases"
    ]
    .astype(float)
)

# DMBI burden criteria.
final[
    "Forecasted_Cases_per_1000_U5"
] = (
    merged[
        dmbi_rate_col
    ]
    .astype(float)
)

final[
    "Forecasted_YoY_Burden_Growth_Percent"
] = (
    merged[
        dmbi_growth_col
    ]
    .astype(float)
)

# NGBoost uncertainty.
final[
    "NGBoost_Predictive_Mean"
] = (
    merged[
        "NGBoost_Mean"
    ]
    .astype(float)
)

final[
    "NGBoost_Predicted_SD"
] = (
    merged[
        "NGBoost_Predicted_SD"
    ]
    .astype(float)
)

final[
    "NGBoost_Lower_95"
] = (
    merged[
        "NGBoost_Lower_95"
    ]
    .astype(float)
)

final[
    "NGBoost_Upper_95"
] = (
    merged[
        "NGBoost_Upper_95"
    ]
    .astype(float)
)

final[
    "NGBoost_95_Interval_Width"
] = (
    merged[
        "NGBoost_Interval_Width"
    ]
    .astype(float)
)

final[
    "NGBoost_Relative_Interval_Width"
] = (
    merged[
        "NGBoost_Relative_Interval_Width"
    ]
    .astype(float)
)

final[
    "Uncertainty_Level"
] = (
    merged[
        "Uncertainty_Level"
    ]
    .astype(str)
    .str.strip()
)

final[
    "Confidence_Label"
] = (
    merged[
        "Confidence_Label"
    ]
    .astype(str)
    .str.strip()
)

final[
    "Nominal_Prediction_Interval_Percentage"
] = (
    merged[
        "Nominal_Interval_Percentage"
    ]
    .astype(float)
)

final[
    "Validated_2025_Observed_Coverage_Percentage"
] = (
    merged[
        "Validated_2025_Observed_Coverage_Percentage"
    ]
    .astype(float)
)

# DMBI priority.
final[
    "DMBI_Score"
] = (
    merged[
        "DMBI_Score_0_100"
    ]
    .astype(float)
)

final[
    "Priority_Rank"
] = (
    merged[
        "Priority_Rank"
    ]
    .astype(int)
)

final[
    "Priority_Level"
] = (
    merged[
        "Priority_Level"
    ]
    .astype(str)
    .str.strip()
)

final[
    "Priority_Code"
] = (
    final[
        "Priority_Level"
    ]
    .map(
        PRIORITY_CODE
    )
    .astype(int)
)

# Display helpers.
final[
    "Forecast_Year"
] = (
    final[
        TARGET
    ]
    .dt.year
    .astype(int)
)

final[
    "Forecast_Month"
] = (
    final[
        TARGET
    ]
    .dt.month
    .astype(int)
)

final[
    "Forecast_Month_Name"
] = (
    final[
        TARGET
    ]
    .dt.month_name()
)

final[
    "Horizon_Label"
] = (
    "H"
    +
    final[
        HORIZON
    ]
    .astype(str)
)

# Interpretation strings for downstream dashboard.
final[
    "Priority_Interpretation"
] = (
    "Relative forecast-based district planning priority; "
    "not a clinical emergency classification."
)

final[
    "Uncertainty_Interpretation"
] = (
    "NGBoost probabilistic 95% prediction interval; "
    "not a formal Random Forest confidence interval."
)

final = (
    final
    .sort_values(
        [
            TARGET,
            HORIZON,
            "Priority_Rank",
            DISTRICT,
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 16. FINAL OUTPUT COMPLETENESS
# ============================================================

final_duplicate_keys = int(
    final
    .duplicated(
        subset=join_keys
    )
    .sum()
)

final_missing_values = int(
    final
    .isna()
    .sum()
    .sum()
)

if final_duplicate_keys != 0:
    raise ValueError(
        f"Final duplicate keys: "
        f"{final_duplicate_keys}"
    )

if final_missing_values != 0:
    raise ValueError(
        f"Final missing values: "
        f"{final_missing_values}"
    )

final.to_csv(
    OUTPUT_PATH,
    index=False,
)

print(
    f"Final rows              : "
    f"{len(final)} [PASS]"
)

print(
    f"Duplicate keys          : "
    f"{final_duplicate_keys} [PASS]"
)

print(
    f"Missing values          : "
    f"{final_missing_values} [PASS]"
)

print(
    f"Saved                   : "
    f"{OUTPUT_PATH}"
)


# ============================================================
# 17. SUMMARY OUTPUTS
# ============================================================

section(
    "BUILD PRIORITY + UNCERTAINTY SUMMARIES"
)

priority_summary = (
    final
    .groupby(
        [
            HORIZON,
            "Priority_Level",
        ],
        as_index=False,
    )
    .agg(
        Rows=(
            DISTRICT,
            "size",
        ),
        Unique_Districts=(
            DISTRICT,
            "nunique",
        ),
        Mean_DMBI_Score=(
            "DMBI_Score",
            "mean",
        ),
        Mean_RF_Predicted_Cases=(
            "RF_Predicted_Cases",
            "mean",
        ),
        Mean_Cases_per_1000_U5=(
            "Forecasted_Cases_per_1000_U5",
            "mean",
        ),
        Mean_YoY_Growth_Percent=(
            "Forecasted_YoY_Burden_Growth_Percent",
            "mean",
        ),
    )
)

priority_summary[
    "Priority_Level"
] = pd.Categorical(
    priority_summary[
        "Priority_Level"
    ],
    categories=PRIORITY_LEVELS,
    ordered=True,
)

priority_summary = (
    priority_summary
    .sort_values(
        [
            HORIZON,
            "Priority_Level",
        ]
    )
    .reset_index(
        drop=True
    )
)

priority_summary.to_csv(
    SUMMARY_PATH,
    index=False,
)

uncertainty_summary = (
    final
    .groupby(
        [
            HORIZON,
            "Uncertainty_Level",
        ],
        as_index=False,
    )
    .agg(
        Rows=(
            DISTRICT,
            "size",
        ),
        Mean_RF_Predicted_Cases=(
            "RF_Predicted_Cases",
            "mean",
        ),
        Mean_NGBoost_Predictive_Mean=(
            "NGBoost_Predictive_Mean",
            "mean",
        ),
        Mean_95_Interval_Width=(
            "NGBoost_95_Interval_Width",
            "mean",
        ),
        Mean_Relative_Interval_Width=(
            "NGBoost_Relative_Interval_Width",
            "mean",
        ),
        Validated_2025_Coverage_Percentage=(
            "Validated_2025_Observed_Coverage_Percentage",
            "first",
        ),
    )
)

uncertainty_summary[
    "Uncertainty_Level"
] = pd.Categorical(
    uncertainty_summary[
        "Uncertainty_Level"
    ],
    categories=UNCERTAINTY_LEVELS,
    ordered=True,
)

uncertainty_summary = (
    uncertainty_summary
    .sort_values(
        [
            HORIZON,
            "Uncertainty_Level",
        ]
    )
    .reset_index(
        drop=True
    )
)

uncertainty_summary.to_csv(
    UNCERTAINTY_SUMMARY_PATH,
    index=False,
)

top5 = (
    final[
        final[
            "Priority_Rank"
        ]
        <=
        5
    ]
    .copy()
    .sort_values(
        [
            TARGET,
            HORIZON,
            "Priority_Rank",
        ]
    )
)

top5.to_csv(
    TOP5_PATH,
    index=False,
)

print(
    f"Priority summary rows    : "
    f"{len(priority_summary)}"
)

print(
    f"Uncertainty summary rows : "
    f"{len(uncertainty_summary)}"
)

print(
    f"Top-5 rows               : "
    f"{len(top5)}"
)


# ============================================================
# 18. FINAL HARD AUDIT
# ============================================================

section(
    "STEP 30 HARD AUDIT"
)

checks = [
    (
        "Step 29F DMBI input exists",
        STEP29F_PATH.exists(),
        True,
    ),
    (
        "Step 27B uncertainty input exists",
        STEP27B_PATH.exists(),
        True,
    ),
    (
        "Step 29F row count",
        len(dmbi) == EXPECTED_TOTAL,
        True,
    ),
    (
        "Step 27B row count",
        len(uncertainty) == EXPECTED_TOTAL,
        True,
    ),
    (
        "Exact district-target-horizon key match",
        (
            len(
                missing_in_uncertainty
            )
            ==
            0
            and
            len(
                extra_in_uncertainty
            )
            ==
            0
        ),
        True,
    ),
    (
        "Final output row count",
        len(final) == EXPECTED_TOTAL,
        True,
    ),
    (
        "25 districts present",
        final[DISTRICT].nunique() == EXPECTED_DISTRICTS,
        True,
    ),
    (
        "All matrices contain 25 districts",
        bool(
            (
                final
                .groupby(
                    [
                        TARGET,
                        HORIZON,
                    ]
                )[DISTRICT]
                .nunique()
                ==
                EXPECTED_DISTRICTS
            )
            .all()
        ),
        True,
    ),
    (
        "No duplicate final keys",
        final_duplicate_keys == 0,
        True,
    ),
    (
        "No missing final values",
        final_missing_values == 0,
        True,
    ),
    (
        "RF point forecast matches Step 29F",
        (
            max_point_difference
            <=
            POINT_FORECAST_TOLERANCE
        ),
        True,
    ),
    (
        "NGBoost intervals valid",
        invalid_interval_count == 0,
        True,
    ),
    (
        "NGBoost lower bounds non-negative",
        negative_lower_count == 0,
        True,
    ),
    (
        "NGBoost predicted SD positive",
        invalid_sd_count == 0,
        True,
    ),
    (
        "DMBI score inside [0,100]",
        bool(
            final[
                "DMBI_Score"
            ]
            .between(
                0,
                100,
                inclusive="both",
            )
            .all()
        ),
        True,
    ),
    (
        "Priority ranks inside 1-25",
        bool(
            final[
                "Priority_Rank"
            ]
            .between(
                1,
                25,
                inclusive="both",
            )
            .all()
        ),
        True,
    ),
    (
        "Priority levels preserved",
        set(
            final[
                "Priority_Level"
            ]
            .unique()
        )
        .issubset(
            set(
                PRIORITY_LEVELS
            )
        ),
        True,
    ),
    (
        "Uncertainty levels preserved",
        set(
            final[
                "Uncertainty_Level"
            ]
            .unique()
        )
        .issubset(
            set(
                UNCERTAINTY_LEVELS
            )
        ),
        True,
    ),
    (
        "Random Forest retrained in Step 30",
        False,
        False,
    ),
    (
        "NGBoost retrained in Step 30",
        False,
        False,
    ),
    (
        "CRITIC weights recalculated in Step 30",
        False,
        False,
    ),
    (
        "TOPSIS rerun in Step 30",
        False,
        False,
    ),
    (
        "DMBI recalculated in Step 30",
        False,
        False,
    ),
    (
        "Uncertainty recalibrated in Step 30",
        False,
        False,
    ),
]

audit_rows = []

for (
    name,
    result,
    expected,
) in checks:

    passed = (
        result
        ==
        expected
    )

    audit_rows.append({
        "Audit_Check":
            name,
        "Result":
            result,
        "Expected":
            expected,
        "Status":
            (
                "PASS"
                if passed
                else
                "FAIL"
            ),
    })

audit_df = pd.DataFrame(
    audit_rows
)

audit_df.to_csv(
    AUDIT_PATH,
    index=False,
)

for _, row in audit_df.iterrows():
    print(
        f"{row['Audit_Check']:<62} : "
        f"{row['Status']}"
    )

if (
    audit_df[
        "Status"
    ]
    !=
    "PASS"
).any():
    raise ValueError(
        "Step 30 hard audit failed. "
        "Review audit output."
    )


# ============================================================
# 19. METHODOLOGY
# ============================================================

methodology = {
    "step":
        "30",
    "name":
        (
            "Final Future District Risk / Priority Export "
            "with NGBoost Uncertainty"
        ),
    "inputs": {
        "dmbi_priority":
            str(
                STEP29F_PATH
            ),
        "ngboost_uncertainty":
            str(
                STEP27B_PATH
            ),
    },
    "system_design": {
        "point_forecast":
            "Random Forest",
        "uncertainty":
            "NGBoost probabilistic predictive distribution",
        "planning_priority":
            "CRITIC-TOPSIS DMBI",
    },
    "join_key": [
        DISTRICT,
        TARGET,
        HORIZON,
    ],
    "recalculation_policy": {
        "random_forest_retrained":
            False,
        "ngboost_retrained":
            False,
        "uncertainty_recalibrated":
            False,
        "critic_weights_recalculated":
            False,
        "topsis_rerun":
            False,
        "dmbi_recalculated":
            False,
        "priority_rank_recalculated":
            False,
        "priority_level_recalculated":
            False,
    },
    "uncertainty_fields": [
        "NGBoost_Predictive_Mean",
        "NGBoost_Predicted_SD",
        "NGBoost_Lower_95",
        "NGBoost_Upper_95",
        "NGBoost_95_Interval_Width",
        "NGBoost_Relative_Interval_Width",
        "Uncertainty_Level",
        "Confidence_Label",
        "Nominal_Prediction_Interval_Percentage",
        "Validated_2025_Observed_Coverage_Percentage",
    ],
    "uncertainty_interpretation":
        (
            "The 95% interval is an NGBoost probabilistic "
            "prediction interval. It is not a formal Random "
            "Forest confidence interval and does not imply "
            "95% accuracy or certainty."
        ),
    "priority_interpretation":
        (
            "DMBI priority is a relative forecast-based district "
            "planning priority, not a clinical emergency classification."
        ),
    "next_step":
        "Step 31 GIS district priority mapping",
}

with open(
    METHOD_PATH,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        methodology,
        file,
        indent=2,
        default=str,
    )


# ============================================================
# 20. RESULTS
# ============================================================

section(
    "STEP 30 RESULTS"
)

print(
    "\nRows by horizon:"
)

print(
    final[
        HORIZON
    ]
    .value_counts()
    .sort_index()
    .to_string()
)

print(
    "\nPriority-level distribution:"
)

print(
    final[
        "Priority_Level"
    ]
    .value_counts()
    .reindex(
        PRIORITY_LEVELS
    )
    .to_string()
)

print(
    "\nUncertainty-level distribution:"
)

print(
    final[
        "Uncertainty_Level"
    ]
    .value_counts()
    .reindex(
        UNCERTAINTY_LEVELS
    )
    .to_string()
)

print(
    "\nValidated 2025 NGBoost coverage retained by horizon:"
)

coverage_display = (
    final
    .groupby(
        HORIZON
    )[
        "Validated_2025_Observed_Coverage_Percentage"
    ]
    .first()
)

for (
    horizon,
    coverage,
) in coverage_display.items():

    print(
        f"H{int(horizon)} = "
        f"{float(coverage):.4f}%"
    )


# ============================================================
# 21. COMPLETE
# ============================================================

section(
    "STEP 30 COMPLETE"
)

print("\nSaved:")
print(
    f"- Final map-ready output : "
    f"{OUTPUT_PATH}"
)

print(
    f"- Priority summary       : "
    f"{SUMMARY_PATH}"
)

print(
    f"- Uncertainty summary    : "
    f"{UNCERTAINTY_SUMMARY_PATH}"
)

print(
    f"- Top-5 priority output  : "
    f"{TOP5_PATH}"
)

print(
    f"- Audit                  : "
    f"{AUDIT_PATH}"
)

print(
    f"- Methodology            : "
    f"{METHOD_PATH}"
)

print("\nIMPORTANT:")
print(
    "- RF_Predicted_Cases remains the main point forecast."
)
print(
    "- NGBoost_Lower_95 / NGBoost_Upper_95 are the probabilistic 95% prediction range."
)
print(
    "- Do NOT describe the NGBoost interval as 95% accuracy or 95% certainty."
)
print(
    "- DMBI Priority_Level and NGBoost Uncertainty_Level are separate outputs."
)

print("\nNEXT:")
print(
    "Send the FULL terminal output before Step 31 GIS priority mapping."
)

print(
    "\nSTEP 30 - FINAL FUTURE DISTRICT RISK / PRIORITY EXPORT WITH NGBOOST UNCERTAINTY COMPLETE"
)

print("=" * 120)
