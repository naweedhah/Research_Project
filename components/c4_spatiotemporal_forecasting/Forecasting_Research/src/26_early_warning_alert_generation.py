# ============================================================
# STEP 26 - EARLY WARNING ALERT GENERATION
# Childhood Malnutrition Forecasting Research
#
# PURPOSE
# -------
# Convert the final frozen district-level forecasts into
# simple horizon-specific early-warning alerts.
#
# INPUTS
# ------
# Step 25 resource-demand output is used because it already
# contains:
#   - Step 23 final prediction
#   - Step 23 risk level
#   - Step 23 district priority rank/band
#   - Step 25 Triposha planning estimate
#
# IMPORTANT METHODOLOGY NOTE
# --------------------------
# This step does NOT retrain, tune, select, or modify any model.
# It does NOT change Step 23 risk classification or priority.
#
# H1 = 1-month-ahead warning
# H3 = 3-month-ahead warning
# H6 = 6-month-ahead warning
#
# ALERT RULE
# ----------
# RED:
#   HIGH risk AND Priority Rank <= 5
#
# ORANGE:
#   HIGH risk OR Priority Rank <= 5
#
# YELLOW:
#   MEDIUM risk
#
# GREEN:
#   LOW risk
#
# This is a research-defined operational alert rule.
# It is NOT an official clinical/public-health warning standard.
#
# IMPORTANT:
# Alert generation is horizon-specific.
# H1/H3/H6 predictions for the same target month are NOT mixed
# together to create one alert because they originate at
# different forecast dates.
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

EXPECTED_DISTRICTS = 25
EXPECTED_MONTHS = 12
EXPECTED_ROWS_PER_HORIZON = 300
EXPECTED_TOTAL_ROWS = 900

TOP_PRIORITY_CUTOFF = 5


# ============================================================
# 2. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

REPORT_DIR = BASE_DIR / "outputs" / "reports"

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

STEP25_PATH = (
    REPORT_DIR
    / "25_triposha_resource_demand_estimates.csv"
)


# ============================================================
# 3. INTRODUCTION
# ============================================================

print("\n" + "=" * 120)
print("STEP 26 - EARLY WARNING ALERT GENERATION")
print("=" * 120)

print("\nMethodology protection:")
print("- Step 23 final predictions are retained unchanged")
print("- Step 23 risk levels are retained unchanged")
print("- Step 23 district priority is retained unchanged")
print("- Step 25 Triposha planning estimates are retained unchanged")
print("- No model training, tuning, or selection is performed")
print("- No 2025 actual outcome is used to generate alerts")
print("- H1/H3/H6 are handled separately")
print("- Alert levels are research-defined operational indicators, not clinical standards")

print("\nAlert rule:")
print(f"- RED    : HIGH risk AND Priority Rank <= {TOP_PRIORITY_CUTOFF}")
print(f"- ORANGE : HIGH risk OR Priority Rank <= {TOP_PRIORITY_CUTOFF}")
print("- YELLOW : MEDIUM risk")
print("- GREEN  : LOW risk")


# ============================================================
# 4. INPUT CHECK
# ============================================================

if not STEP25_PATH.exists():

    raise FileNotFoundError(
        "Step 25 resource-demand output was not found:\n"
        f"{STEP25_PATH}\n\n"
        "Run Step 25 first."
    )


df = pd.read_csv(
    STEP25_PATH
)


# ============================================================
# 5. REQUIRED COLUMN CHECK
# ============================================================

required_columns = {
    "Horizon_Months",
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Prediction",
    "Risk_Level",
    "Priority_Rank",
    "Priority_Band",
    "Estimated_Triposha_Packets_Lower",
    "Estimated_Triposha_Packets_Base",
    "Estimated_Triposha_Packets_Upper",
}


missing_columns = (
    required_columns
    -
    set(df.columns)
)


if missing_columns:

    raise ValueError(
        "Step 25 output is missing required columns: "
        f"{sorted(missing_columns)}"
    )


# ============================================================
# 6. TYPE CLEANING
# ============================================================

df[
    "Forecast_Origin_Date"
] = pd.to_datetime(
    df[
        "Forecast_Origin_Date"
    ],
    errors="coerce",
)


df[
    "Forecast_Target_Date"
] = pd.to_datetime(
    df[
        "Forecast_Target_Date"
    ],
    errors="coerce",
)


numeric_columns = [
    "Horizon_Months",
    "Prediction",
    "Priority_Rank",
    "Estimated_Triposha_Packets_Lower",
    "Estimated_Triposha_Packets_Base",
    "Estimated_Triposha_Packets_Upper",
]


for column in numeric_columns:

    df[
        column
    ] = pd.to_numeric(
        df[
            column
        ],
        errors="coerce",
    )


if df[
    [
        "Horizon_Months",
        "Prediction",
        "Priority_Rank",
    ]
].isna().any().any():

    raise ValueError(
        "Core Step 25 alert inputs contain missing/non-numeric values."
    )


df[
    "Risk_Level"
] = (
    df[
        "Risk_Level"
    ]
    .astype(str)
    .str.strip()
    .str.upper()
)


valid_risk_levels = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


unexpected_risk = sorted(
    set(
        df[
            "Risk_Level"
        ]
        .dropna()
        .unique()
    )
    -
    valid_risk_levels
)


if unexpected_risk:

    raise ValueError(
        "Unexpected Step 23 risk levels found: "
        f"{unexpected_risk}"
    )


# ============================================================
# 7. HARD VALIDATION
# ============================================================

print("\n" + "=" * 120)
print("INPUT VALIDATION")
print("=" * 120)


if len(df) != EXPECTED_TOTAL_ROWS:

    raise ValueError(
        f"Expected {EXPECTED_TOTAL_ROWS} total rows, "
        f"found {len(df)}."
    )


for horizon in HORIZONS:

    hdf = df[
        df[
            "Horizon_Months"
        ]
        ==
        horizon
    ].copy()


    rows = len(
        hdf
    )

    districts = hdf[
        "District"
    ].nunique()

    months = hdf[
        "Forecast_Target_Date"
    ].nunique()


    if rows != EXPECTED_ROWS_PER_HORIZON:

        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_ROWS_PER_HORIZON} rows, "
            f"found {rows}."
        )


    if districts != EXPECTED_DISTRICTS:

        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_DISTRICTS} districts, "
            f"found {districts}."
        )


    if months != EXPECTED_MONTHS:

        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_MONTHS} target months, "
            f"found {months}."
        )


    if not (
        hdf[
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
        f"rows={rows}, "
        f"districts={districts}, "
        f"months={months} "
        f"[PASS]"
    )


# ============================================================
# 8. ALERT RULE
# ============================================================

def generate_alert_level(
    risk_level,
    priority_rank,
):

    if (
        risk_level
        ==
        "HIGH"
        and
        priority_rank
        <=
        TOP_PRIORITY_CUTOFF
    ):

        return "RED"


    if (
        risk_level
        ==
        "HIGH"
        or
        priority_rank
        <=
        TOP_PRIORITY_CUTOFF
    ):

        return "ORANGE"


    if (
        risk_level
        ==
        "MEDIUM"
    ):

        return "YELLOW"


    return "GREEN"


df[
    "Alert_Level"
] = df.apply(
    lambda row:
        generate_alert_level(
            row[
                "Risk_Level"
            ],
            row[
                "Priority_Rank"
            ],
        ),
    axis=1,
)


# ============================================================
# 9. ALERT REASON
# ============================================================

def generate_alert_reason(
    risk_level,
    priority_rank,
):

    top_priority = (
        priority_rank
        <=
        TOP_PRIORITY_CUTOFF
    )


    if (
        risk_level
        ==
        "HIGH"
        and
        top_priority
    ):

        return (
            "HIGH forecast risk and Top-5 district priority"
        )


    if (
        risk_level
        ==
        "HIGH"
    ):

        return (
            "HIGH forecast risk"
        )


    if top_priority:

        return (
            "Top-5 predicted district burden"
        )


    if (
        risk_level
        ==
        "MEDIUM"
    ):

        return (
            "MEDIUM forecast risk"
        )


    return (
        "LOW forecast risk"
    )


df[
    "Alert_Reason"
] = df.apply(
    lambda row:
        generate_alert_reason(
            row[
                "Risk_Level"
            ],
            row[
                "Priority_Rank"
            ],
        ),
    axis=1,
)


# ============================================================
# 10. LEAD-TIME LABEL
# ============================================================

lead_time_labels = {
    1:
        "1-MONTH-AHEAD",

    3:
        "3-MONTH-AHEAD",

    6:
        "6-MONTH-AHEAD",
}


df[
    "Warning_Lead_Time"
] = df[
    "Horizon_Months"
].map(
    lead_time_labels
)


# ============================================================
# 11. ACTION MESSAGE
# ============================================================
#
# These messages are planning-support messages only.
# They do not prescribe clinical treatment.
# ============================================================

def action_message(
    alert_level,
):

    if alert_level == "RED":

        return (
            "Immediate planning attention recommended; "
            "review district resource readiness and monitoring."
        )


    if alert_level == "ORANGE":

        return (
            "Elevated planning attention recommended; "
            "review resource readiness and district trend."
        )


    if alert_level == "YELLOW":

        return (
            "Continue monitoring and routine resource planning."
        )


    return (
        "Routine monitoring."
    )


df[
    "Planning_Action"
] = df[
    "Alert_Level"
].apply(
    action_message
)


# ============================================================
# 12. HUMAN-READABLE ALERT MESSAGE
# ============================================================

def build_alert_message(
    row,
):

    target_month = (
        row[
            "Forecast_Target_Date"
        ]
        .strftime(
            "%Y-%m"
        )
    )


    base_packets = int(
        np.ceil(
            row[
                "Estimated_Triposha_Packets_Base"
            ]
        )
    )


    return (
        f"{row['Alert_Level']} early warning | "
        f"{row['District']} | "
        f"{row['Warning_Lead_Time']} | "
        f"Target {target_month} | "
        f"Predicted cases {row['Prediction']:.2f} | "
        f"Risk {row['Risk_Level']} | "
        f"Priority rank {int(row['Priority_Rank'])}/25 | "
        f"Estimated Triposha base demand {base_packets} packets."
    )


df[
    "Alert_Message"
] = df.apply(
    build_alert_message,
    axis=1,
)


# ============================================================
# 13. ALERT ORDER
# ============================================================

alert_order = {
    "RED":
        4,

    "ORANGE":
        3,

    "YELLOW":
        2,

    "GREEN":
        1,
}


df[
    "Alert_Severity_Order"
] = df[
    "Alert_Level"
].map(
    alert_order
)


# ============================================================
# 14. FINAL OUTPUT
# ============================================================

output_columns = [
    "Horizon_Months",
    "Warning_Lead_Time",
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",

    "Prediction",
    "Risk_Level",
    "Priority_Rank",
    "Priority_Band",

    "Alert_Level",
    "Alert_Severity_Order",
    "Alert_Reason",
    "Planning_Action",

    "Estimated_Triposha_Packets_Lower",
    "Estimated_Triposha_Packets_Base",
    "Estimated_Triposha_Packets_Upper",

    "Alert_Message",
]


alerts_df = (
    df[
        output_columns
    ]
    .sort_values(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
            "Alert_Severity_Order",
            "Priority_Rank",
        ],
        ascending=[
            True,
            True,
            False,
            True,
        ],
    )
    .reset_index(
        drop=True
    )
)


all_alerts_path = (
    REPORT_DIR
    / "26_early_warning_alerts.csv"
)


alerts_df.to_csv(
    all_alerts_path,
    index=False,
)


# ============================================================
# 15. ACTIVE WARNINGS
# ============================================================
#
# GREEN = routine monitoring, so active-warning report keeps
# RED / ORANGE / YELLOW only.
# ============================================================

active_alerts_df = (
    alerts_df[
        alerts_df[
            "Alert_Level"
        ]
        .isin(
            [
                "RED",
                "ORANGE",
                "YELLOW",
            ]
        )
    ]
    .copy()
)


active_alerts_path = (
    REPORT_DIR
    / "26_active_warning_alerts.csv"
)


active_alerts_df.to_csv(
    active_alerts_path,
    index=False,
)


# ============================================================
# 16. RED ALERT REPORT
# ============================================================

red_alerts_df = (
    alerts_df[
        alerts_df[
            "Alert_Level"
        ]
        ==
        "RED"
    ]
    .copy()
)


red_alerts_path = (
    REPORT_DIR
    / "26_red_alerts.csv"
)


red_alerts_df.to_csv(
    red_alerts_path,
    index=False,
)


# ============================================================
# 17. MONTHLY ALERT SUMMARY
# ============================================================

monthly_summary = (
    alerts_df
    .groupby(
        [
            "Horizon_Months",
            "Warning_Lead_Time",
            "Forecast_Target_Date",
        ],
        as_index=False,
    )
    .agg(
        RED_Alerts=(
            "Alert_Level",
            lambda x:
                int(
                    (
                        x
                        ==
                        "RED"
                    )
                    .sum()
                ),
        ),

        ORANGE_Alerts=(
            "Alert_Level",
            lambda x:
                int(
                    (
                        x
                        ==
                        "ORANGE"
                    )
                    .sum()
                ),
        ),

        YELLOW_Alerts=(
            "Alert_Level",
            lambda x:
                int(
                    (
                        x
                        ==
                        "YELLOW"
                    )
                    .sum()
                ),
        ),

        GREEN_Alerts=(
            "Alert_Level",
            lambda x:
                int(
                    (
                        x
                        ==
                        "GREEN"
                    )
                    .sum()
                ),
        ),

        Total_Predicted_Cases=(
            "Prediction",
            "sum",
        ),

        Total_Base_Triposha_Demand=(
            "Estimated_Triposha_Packets_Base",
            "sum",
        ),
    )
)


monthly_summary_path = (
    REPORT_DIR
    / "26_monthly_alert_summary.csv"
)


monthly_summary.to_csv(
    monthly_summary_path,
    index=False,
)


# ============================================================
# 18. DISTRICT ALERT SUMMARY
# ============================================================

district_summary_records = []


for (
    horizon,
    district
), group in (
    alerts_df
    .groupby(
        [
            "Horizon_Months",
            "District",
        ]
    )
):

    district_summary_records.append({
        "Horizon_Months":
            horizon,

        "Warning_Lead_Time":
            lead_time_labels[
                int(
                    horizon
                )
            ],

        "District":
            district,

        "RED_Months":
            int(
                (
                    group[
                        "Alert_Level"
                    ]
                    ==
                    "RED"
                )
                .sum()
            ),

        "ORANGE_Months":
            int(
                (
                    group[
                        "Alert_Level"
                    ]
                    ==
                    "ORANGE"
                )
                .sum()
            ),

        "YELLOW_Months":
            int(
                (
                    group[
                        "Alert_Level"
                    ]
                    ==
                    "YELLOW"
                )
                .sum()
            ),

        "GREEN_Months":
            int(
                (
                    group[
                        "Alert_Level"
                    ]
                    ==
                    "GREEN"
                )
                .sum()
            ),

        "Maximum_Predicted_Cases":
            float(
                group[
                    "Prediction"
                ]
                .max()
            ),

        "Mean_Priority_Rank":
            float(
                group[
                    "Priority_Rank"
                ]
                .mean()
            ),
    })


district_summary_df = pd.DataFrame(
    district_summary_records
)


district_summary_df[
    "Mean_Priority_Rank"
] = district_summary_df[
    "Mean_Priority_Rank"
].round(
    2
)


district_summary_path = (
    REPORT_DIR
    / "26_district_alert_summary.csv"
)


district_summary_df.to_csv(
    district_summary_path,
    index=False,
)


# ============================================================
# 19. METHODOLOGY AUDIT
# ============================================================

alert_counts = (
    alerts_df[
        "Alert_Level"
    ]
    .value_counts()
    .to_dict()
)


audit = {
    "step":
        26,

    "purpose":
        "Horizon-specific district early-warning alert generation",

    "input":
        str(
            STEP25_PATH
        ),

    "forecast_horizons":
        {
            "H1":
                "1-month-ahead warning",

            "H3":
                "3-month-ahead warning",

            "H6":
                "6-month-ahead warning",
        },

    "alert_rule":
        {
            "RED":
                (
                    f"HIGH forecast risk AND "
                    f"Priority_Rank <= {TOP_PRIORITY_CUTOFF}"
                ),

            "ORANGE":
                (
                    f"HIGH forecast risk OR "
                    f"Priority_Rank <= {TOP_PRIORITY_CUTOFF}, "
                    "excluding RED"
                ),

            "YELLOW":
                "MEDIUM forecast risk",

            "GREEN":
                "LOW forecast risk",
        },

    "important_interpretation":
        (
            "Alert levels are research-defined operational "
            "planning indicators and are not official clinical "
            "or public-health warning standards."
        ),

    "horizon_handling":
        (
            "H1, H3 and H6 alerts are generated separately. "
            "Predictions from different forecast origins are not "
            "mixed to create one alert."
        ),

    "alert_counts":
        {
            str(
                key
            ):
                int(
                    value
                )
            for key, value in alert_counts.items()
        },

    "methodology_protection": [
        "Step 23 predictions retained unchanged",
        "Step 23 risk levels retained unchanged",
        "Step 23 priority retained unchanged",
        "Step 25 Triposha planning estimates retained unchanged",
        "No forecasting model training",
        "No hyperparameter tuning",
        "No model selection",
        "No 2025 actual malnutrition outcomes used for alert generation",
        "No cross-horizon mixing for a single alert",
    ],
}


audit_path = (
    REPORT_DIR
    / "26_early_warning_methodology_audit.json"
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
# 20. VALIDATE ALERT OUTPUT
# ============================================================

print("\n" + "=" * 120)
print("STEP 26 VALIDATION")
print("=" * 120)


if len(
    alerts_df
) != EXPECTED_TOTAL_ROWS:

    raise AssertionError(
        "Alert row count changed unexpectedly."
    )


if alerts_df[
    "Alert_Level"
].isna().any():

    raise AssertionError(
        "Missing alert levels were generated."
    )


if not set(
    alerts_df[
        "Alert_Level"
    ]
    .unique()
).issubset(
    {
        "RED",
        "ORANGE",
        "YELLOW",
        "GREEN",
    }
):

    raise AssertionError(
        "Unexpected alert category generated."
    )


for horizon in HORIZONS:

    count = len(
        alerts_df[
            alerts_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
    )

    print(
        f"H{horizon}: "
        f"{count} alerts "
        f"[PASS]"
    )


print(
    f"Total alerts: "
    f"{len(alerts_df)} "
    f"[PASS]"
)


# ============================================================
# 21. ALERT COUNTS
# ============================================================

print("\n" + "=" * 120)
print("ALERT COUNTS")
print("=" * 120)


for horizon in HORIZONS:

    hdf = alerts_df[
        alerts_df[
            "Horizon_Months"
        ]
        ==
        horizon
    ]


    counts = (
        hdf[
            "Alert_Level"
        ]
        .value_counts()
    )


    print(
        f"\nH{horizon} "
        f"({lead_time_labels[horizon]}):"
    )


    for level in [
        "RED",
        "ORANGE",
        "YELLOW",
        "GREEN",
    ]:

        print(
            f"  {level:<6}: "
            f"{int(counts.get(level, 0))}"
        )


# ============================================================
# 22. FIRST TARGET MONTH EXAMPLE
# ============================================================

print("\n" + "=" * 120)
print("EXAMPLE: FIRST TARGET MONTH - HIGHEST ALERTS")
print("=" * 120)


for horizon in HORIZONS:

    hdf = alerts_df[
        alerts_df[
            "Horizon_Months"
        ]
        ==
        horizon
    ]


    first_target_month = (
        hdf[
            "Forecast_Target_Date"
        ]
        .min()
    )


    example_df = (
        hdf[
            hdf[
                "Forecast_Target_Date"
            ]
            ==
            first_target_month
        ]
        .sort_values(
            [
                "Alert_Severity_Order",
                "Priority_Rank",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .head(
            8
        )
    )


    print(
        f"\nH{horizon} | "
        f"{lead_time_labels[horizon]} | "
        f"Target month: "
        f"{first_target_month.date()}"
    )


    print(
        example_df[
            [
                "Alert_Level",
                "District",
                "Prediction",
                "Risk_Level",
                "Priority_Rank",
                "Estimated_Triposha_Packets_Base",
                "Alert_Reason",
            ]
        ]
        .round(
            {
                "Prediction":
                    2
            }
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# 23. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 120)
print("STEP 26 SUMMARY")
print("=" * 120)

print("- Horizon-specific early-warning alerts were generated")
print("- H1 = 1-month-ahead warning")
print("- H3 = 3-month-ahead warning")
print("- H6 = 6-month-ahead warning")
print("- Step 23 risk and district priority were retained unchanged")
print("- Step 25 Triposha planning estimates were attached to alerts")
print("- No new model training/tuning/selection was performed")
print("- No 2025 actual outcome was used for alert generation")
print("- Alerts are planning indicators, not official clinical/public-health warnings")

print("\nSaved reports:")
print(all_alerts_path)
print(active_alerts_path)
print(red_alerts_path)
print(monthly_summary_path)
print(district_summary_path)
print(audit_path)

print(
    "\nSTEP 26 - EARLY WARNING ALERT GENERATION COMPLETE"
)
print("=" * 120)
