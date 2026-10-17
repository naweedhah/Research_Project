# ============================================================
# STEP 25 - RESOURCE DEMAND ESTIMATION
# Childhood Malnutrition Forecasting Research
#
# PURPOSE
# -------
# Estimate district-level Triposha packet demand from the
# final frozen malnutrition forecasts.
#
# IMPORTANT INTERPRETATION
# ------------------------
# This is a PLANNING / OPERATIONAL estimate only.
# It is NOT a clinical dosage recommendation.
#
# METHOD
# ------
# 1) Use historical pre-2025 data only (2015-2023).
# 2) For months where both values are valid:
#
#       Historical Packet Ratio
#       = Triposha_Packets_Distributed / Malnutrition_Cases
#
# 3) For each district:
#       Q25 ratio -> lower planning estimate
#       Median    -> base planning estimate
#       Q75 ratio -> upper planning estimate
#
# 4) Multiply the Step 21/23 predicted malnutrition count by
#    the frozen historical district ratio.
#
# If a district does not have enough valid historical Triposha
# observations, the national historical ratios are used as a
# fallback.
#
# METHODOLOGY PROTECTION
# ----------------------
# - No forecasting model training
# - No tuning
# - No model selection
# - 2025 actual malnutrition outcomes are NOT used to estimate
#   the resource conversion ratios
# - 2025 actual Triposha distribution is NOT used
# - Step 23 predictions are used unchanged
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

RESOURCE_COLUMN = "Triposha_Packets_Distributed"

HISTORICAL_START_YEAR = 2015
HISTORICAL_END_YEAR = 2023

MIN_DISTRICT_HISTORY_ROWS = 12

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

STEP23_RISK_PATH = (
    REPORT_DIR
    / "23_district_risk_prioritization.csv"
)


# ============================================================
# 3. INTRODUCTION
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "STEP 25 - RESOURCE DEMAND ESTIMATION"
)

print(
    "=" * 120
)

print(
    "\nMethodology protection:"
)

print(
    "- Step 23 final predictions are used unchanged"
)

print(
    "- Historical resource conversion is learned only from 2015-2023"
)

print(
    "- 2025 actual malnutrition outcomes are NOT used"
)

print(
    "- 2025 actual Triposha distribution is NOT used"
)

print(
    "- No model training, tuning, or model selection is performed"
)

print(
    "- Estimates are for planning support, NOT clinical dosage"
)


# ============================================================
# 4. INPUT CHECK
# ============================================================

for path in [
    HISTORICAL_DATA_PATH,
    STEP23_RISK_PATH,
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
    "District",
    TARGET,
    RESOURCE_COLUMN,
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
        "Historical dataset is missing required columns: "
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


historical_df[
    RESOURCE_COLUMN
] = pd.to_numeric(
    historical_df[
        RESOURCE_COLUMN
    ],
    errors="coerce",
)


history = (
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


# ============================================================
# 6. BUILD VALID HISTORICAL RESOURCE-RATIO SAMPLE
# ============================================================

valid_history = (
    history[
        history[
            TARGET
        ]
        .notna()
        &
        history[
            RESOURCE_COLUMN
        ]
        .notna()
        &
        (
            history[
                TARGET
            ]
            >
            0
        )
        &
        (
            history[
                RESOURCE_COLUMN
            ]
            >=
            0
        )
    ]
    .copy()
)


if valid_history.empty:

    raise ValueError(
        "No valid pre-2025 historical rows are available "
        "for Triposha resource estimation."
    )


valid_history[
    "Packets_Per_Case_Ratio"
] = (
    valid_history[
        RESOURCE_COLUMN
    ]
    /
    valid_history[
        TARGET
    ]
)


valid_history = (
    valid_history[
        np.isfinite(
            valid_history[
                "Packets_Per_Case_Ratio"
            ]
        )
    ]
    .copy()
)


if valid_history.empty:

    raise ValueError(
        "Historical Triposha packet ratios could not be calculated."
    )


# ============================================================
# 7. NATIONAL HISTORICAL FALLBACK RATIOS
# ============================================================

national_q25 = float(
    valid_history[
        "Packets_Per_Case_Ratio"
    ]
    .quantile(
        0.25
    )
)


national_median = float(
    valid_history[
        "Packets_Per_Case_Ratio"
    ]
    .median()
)


national_q75 = float(
    valid_history[
        "Packets_Per_Case_Ratio"
    ]
    .quantile(
        0.75
    )
)


if not (
    np.isfinite(
        national_q25
    )
    and
    np.isfinite(
        national_median
    )
    and
    np.isfinite(
        national_q75
    )
):

    raise ValueError(
        "National historical resource ratios are not finite."
    )


print(
    "\n"
    + "=" * 120
)

print(
    "HISTORICAL NATIONAL TRIPOSHA RATIO"
)

print(
    "=" * 120
)

print(
    f"Historical period          : "
    f"{HISTORICAL_START_YEAR}-{HISTORICAL_END_YEAR}"
)

print(
    f"Valid historical rows      : "
    f"{len(valid_history)}"
)

print(
    f"National Q25 packets/case  : "
    f"{national_q25:.4f}"
)

print(
    f"National Median packets/case: "
    f"{national_median:.4f}"
)

print(
    f"National Q75 packets/case  : "
    f"{national_q75:.4f}"
)


# ============================================================
# 8. DISTRICT-SPECIFIC HISTORICAL RATIOS
# ============================================================

district_ratio_records = []


for district, district_df in (
    valid_history
    .groupby(
        "District"
    )
):

    row_count = len(
        district_df
    )


    if (
        row_count
        >=
        MIN_DISTRICT_HISTORY_ROWS
    ):

        q25 = float(
            district_df[
                "Packets_Per_Case_Ratio"
            ]
            .quantile(
                0.25
            )
        )

        median = float(
            district_df[
                "Packets_Per_Case_Ratio"
            ]
            .median()
        )

        q75 = float(
            district_df[
                "Packets_Per_Case_Ratio"
            ]
            .quantile(
                0.75
            )
        )

        source = (
            "DISTRICT_HISTORICAL"
        )

    else:

        q25 = national_q25

        median = national_median

        q75 = national_q75

        source = (
            "NATIONAL_FALLBACK"
        )


    district_ratio_records.append({
        "District":
            district,

        "Historical_Valid_Rows":
            row_count,

        "Ratio_Q25":
            q25,

        "Ratio_Median":
            median,

        "Ratio_Q75":
            q75,

        "Ratio_Source":
            source,
    })


district_ratio_df = pd.DataFrame(
    district_ratio_records
)


# ============================================================
# 9. ENSURE ALL 25 DISTRICTS HAVE A RESOURCE RATIO
# ============================================================

all_districts = sorted(
    historical_df[
        "District"
    ]
    .dropna()
    .unique()
)


existing_ratio_districts = set(
    district_ratio_df[
        "District"
    ]
)


for district in all_districts:

    if (
        district
        not in
        existing_ratio_districts
    ):

        district_ratio_df = pd.concat(
            [
                district_ratio_df,

                pd.DataFrame(
                    [{
                        "District":
                            district,

                        "Historical_Valid_Rows":
                            0,

                        "Ratio_Q25":
                            national_q25,

                        "Ratio_Median":
                            national_median,

                        "Ratio_Q75":
                            national_q75,

                        "Ratio_Source":
                            "NATIONAL_FALLBACK",
                    }]
                ),
            ],
            ignore_index=True,
        )


district_ratio_df = (
    district_ratio_df
    .sort_values(
        "District"
    )
    .reset_index(
        drop=True
    )
)


if (
    district_ratio_df[
        "District"
    ]
    .nunique()
    !=
    EXPECTED_DISTRICTS
):

    raise ValueError(
        f"Expected {EXPECTED_DISTRICTS} district resource ratios, "
        f"found {district_ratio_df['District'].nunique()}."
    )


district_ratio_path = (
    REPORT_DIR
    / "25_historical_triposha_ratio_by_district.csv"
)


district_ratio_df.to_csv(
    district_ratio_path,
    index=False,
)


print(
    "\nDistrict resource ratios:"
)

print(
    district_ratio_df[
        [
            "District",
            "Historical_Valid_Rows",
            "Ratio_Median",
            "Ratio_Source",
        ]
    ]
    .round({
        "Ratio_Median":
            4
    })
    .to_string(
        index=False
    )
)


# ============================================================
# 10. LOAD STEP 23 FINAL PREDICTIONS + RISK
# ============================================================

prediction_df = pd.read_csv(
    STEP23_RISK_PATH
)


required_prediction_columns = {
    "Horizon_Months",
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Prediction",
    "Risk_Level",
    "Priority_Rank",
    "Priority_Band",
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
        "Step 23 output is missing required columns: "
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
        "Step 23 contains missing/non-numeric predictions."
    )


# ============================================================
# 11. HARD FORECAST VALIDATION
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
    )


    if (
        len(
            horizon_df
        )
        !=
        EXPECTED_ROWS_PER_HORIZON
    ):

        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_ROWS_PER_HORIZON} rows, "
            f"found {len(horizon_df)}."
        )


    if (
        horizon_df[
            "District"
        ]
        .nunique()
        !=
        EXPECTED_DISTRICTS
    ):

        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_DISTRICTS} districts."
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
            f"H{horizon}: target dates are not exclusively 2025."
        )


    print(
        f"H{horizon}: "
        f"rows={len(horizon_df)}, "
        f"districts={horizon_df['District'].nunique()}, "
        f"months={horizon_df['Forecast_Target_Date'].nunique()} "
        f"[PASS]"
    )


# ============================================================
# 12. MERGE FROZEN HISTORICAL RESOURCE RATIOS
# ============================================================

resource_df = (
    prediction_df
    .merge(
        district_ratio_df,
        on=
            "District",
        how=
            "left",
        validate=
            "many_to_one",
    )
)


if resource_df[
    "Ratio_Median"
].isna().any():

    missing_districts = sorted(
        resource_df.loc[
            resource_df[
                "Ratio_Median"
            ]
            .isna(),
            "District",
        ]
        .unique()
    )

    raise ValueError(
        "Missing historical resource ratio for districts: "
        f"{missing_districts}"
    )


# ============================================================
# 13. RESOURCE DEMAND ESTIMATION
# ============================================================

resource_df[
    "Estimated_Triposha_Packets_Lower"
] = (
    np.ceil(
        resource_df[
            "Prediction"
        ]
        *
        resource_df[
            "Ratio_Q25"
        ]
    )
    .astype(int)
)


resource_df[
    "Estimated_Triposha_Packets_Base"
] = (
    np.ceil(
        resource_df[
            "Prediction"
        ]
        *
        resource_df[
            "Ratio_Median"
        ]
    )
    .astype(int)
)


resource_df[
    "Estimated_Triposha_Packets_Upper"
] = (
    np.ceil(
        resource_df[
            "Prediction"
        ]
        *
        resource_df[
            "Ratio_Q75"
        ]
    )
    .astype(int)
)


# Safety ordering check.
if not (
    (
        resource_df[
            "Estimated_Triposha_Packets_Lower"
        ]
        <=
        resource_df[
            "Estimated_Triposha_Packets_Base"
        ]
    )
    &
    (
        resource_df[
            "Estimated_Triposha_Packets_Base"
        ]
        <=
        resource_df[
            "Estimated_Triposha_Packets_Upper"
        ]
    )
).all():

    raise AssertionError(
        "Resource interval ordering failed."
    )


# ============================================================
# 14. RESOURCE PRIORITY RANK
# ============================================================

resource_df[
    "Resource_Priority_Rank"
] = (
    resource_df
    .groupby(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
        ]
    )[
        "Estimated_Triposha_Packets_Base"
    ]
    .rank(
        method="first",
        ascending=False,
    )
    .astype(int)
)


# ============================================================
# 15. SAVE FULL RESOURCE DEMAND OUTPUT
# ============================================================

output_columns = [
    "Horizon_Months",
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Prediction",
    "Risk_Level",
    "Priority_Rank",
    "Priority_Band",
    "Historical_Valid_Rows",
    "Ratio_Q25",
    "Ratio_Median",
    "Ratio_Q75",
    "Ratio_Source",
    "Estimated_Triposha_Packets_Lower",
    "Estimated_Triposha_Packets_Base",
    "Estimated_Triposha_Packets_Upper",
    "Resource_Priority_Rank",
]


resource_output_df = (
    resource_df[
        output_columns
    ]
    .sort_values(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
            "Resource_Priority_Rank",
        ]
    )
    .reset_index(
        drop=True
    )
)


resource_output_path = (
    REPORT_DIR
    / "25_triposha_resource_demand_estimates.csv"
)


resource_output_df.to_csv(
    resource_output_path,
    index=False,
)


# ============================================================
# 16. MONTHLY NATIONAL RESOURCE SUMMARY
# ============================================================

monthly_summary_df = (
    resource_output_df
    .groupby(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
        ],
        as_index=False,
    )
    .agg(
        Total_Predicted_Malnutrition_Cases=(
            "Prediction",
            "sum"
        ),

        Estimated_Triposha_Lower=(
            "Estimated_Triposha_Packets_Lower",
            "sum"
        ),

        Estimated_Triposha_Base=(
            "Estimated_Triposha_Packets_Base",
            "sum"
        ),

        Estimated_Triposha_Upper=(
            "Estimated_Triposha_Packets_Upper",
            "sum"
        ),

        High_Risk_Districts=(
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
    )
)


monthly_summary_path = (
    REPORT_DIR
    / "25_monthly_national_triposha_demand.csv"
)


monthly_summary_df.to_csv(
    monthly_summary_path,
    index=False,
)


# ============================================================
# 17. TOP-5 RESOURCE PRIORITY DISTRICTS
# ============================================================

top5_resource_df = (
    resource_output_df[
        resource_output_df[
            "Resource_Priority_Rank"
        ]
        <=
        5
    ]
    .copy()
)


top5_resource_path = (
    REPORT_DIR
    / "25_top5_resource_priority_districts.csv"
)


top5_resource_df.to_csv(
    top5_resource_path,
    index=False,
)


# ============================================================
# 18. DISTRICT 2025 RESOURCE SUMMARY
# ============================================================

district_summary_df = (
    resource_output_df
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

        Mean_Monthly_Triposha_Base=(
            "Estimated_Triposha_Packets_Base",
            "mean"
        ),

        Total_2025_Triposha_Base=(
            "Estimated_Triposha_Packets_Base",
            "sum"
        ),

        Maximum_Monthly_Triposha_Base=(
            "Estimated_Triposha_Packets_Base",
            "max"
        ),

        Mean_Resource_Priority_Rank=(
            "Resource_Priority_Rank",
            "mean"
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
    )
)


district_summary_df[
    "Mean_Resource_Priority_Rank"
] = (
    district_summary_df[
        "Mean_Resource_Priority_Rank"
    ]
    .round(
        2
    )
)


district_summary_path = (
    REPORT_DIR
    / "25_district_2025_triposha_summary.csv"
)


district_summary_df.to_csv(
    district_summary_path,
    index=False,
)


# ============================================================
# 19. SAVE METHODOLOGY AUDIT
# ============================================================

fallback_count = int(
    (
        district_ratio_df[
            "Ratio_Source"
        ]
        ==
        "NATIONAL_FALLBACK"
    )
    .sum()
)


audit = {
    "step":
        25,

    "purpose":
        "Triposha resource demand planning estimation",

    "interpretation":
        "Operational planning estimate only; not a clinical dosage recommendation",

    "historical_period":
        f"{HISTORICAL_START_YEAR}-{HISTORICAL_END_YEAR}",

    "resource_column":
        RESOURCE_COLUMN,

    "target_column":
        TARGET,

    "valid_historical_rows":
        int(
            len(
                valid_history
            )
        ),

    "minimum_district_history_rows":
        MIN_DISTRICT_HISTORY_ROWS,

    "districts_using_national_fallback":
        fallback_count,

    "national_ratios": {
        "q25":
            national_q25,

        "median":
            national_median,

        "q75":
            national_q75,
    },

    "formula":
        "Estimated packets = Predicted malnutrition cases x historical packets-per-case ratio",

    "lower_estimate":
        "District historical Q25 ratio",

    "base_estimate":
        "District historical median ratio",

    "upper_estimate":
        "District historical Q75 ratio",

    "methodology_protection": [
        "2025 actual malnutrition outcomes were not used to define resource ratios",
        "2025 actual Triposha distribution was not used",
        "Step 23 predictions were used unchanged",
        "No model training was performed",
        "No tuning was performed",
        "No model selection was performed",
    ],
}


audit_path = (
    REPORT_DIR
    / "25_resource_demand_methodology_audit.json"
)


with open(
    audit_path,
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        audit,
        file,
        indent=4,
    )


# ============================================================
# 20. PRINT EXAMPLE TOP-5
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "EXAMPLE: FIRST TARGET MONTH TOP-5 RESOURCE PRIORITY DISTRICTS"
)

print(
    "=" * 120
)


for horizon in HORIZONS:

    horizon_df = (
        resource_output_df[
            resource_output_df[
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
            "Resource_Priority_Rank"
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
                "Resource_Priority_Rank",
                "District",
                "Prediction",
                "Risk_Level",
                "Estimated_Triposha_Packets_Lower",
                "Estimated_Triposha_Packets_Base",
                "Estimated_Triposha_Packets_Upper",
                "Ratio_Source",
            ]
        ]
        .round({
            "Prediction":
                2
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
    "STEP 25 SUMMARY"
)

print(
    "=" * 120
)

print(
    "- Historical Triposha packets-per-case ratios were calculated from 2015-2023 only"
)

print(
    "- District-specific median ratios were used where sufficient history was available"
)

print(
    "- National historical ratios were used only as fallback"
)

print(
    "- Lower / base / upper resource planning estimates were produced"
)

print(
    "- Step 23 predictions and risk classifications were retained unchanged"
)

print(
    "- No 2025 actual outcome was used to define the resource estimation rule"
)

print(
    "- These are planning estimates, NOT clinical dosage recommendations"
)

print(
    "\nSaved reports:"
)

print(
    district_ratio_path
)

print(
    resource_output_path
)

print(
    monthly_summary_path
)

print(
    top5_resource_path
)

print(
    district_summary_path
)

print(
    audit_path
)


print(
    "\nSTEP 25 - RESOURCE DEMAND ESTIMATION COMPLETE"
)

print(
    "=" * 120
)
