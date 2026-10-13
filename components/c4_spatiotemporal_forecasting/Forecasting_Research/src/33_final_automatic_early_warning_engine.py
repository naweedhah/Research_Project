# ============================================================
# STEP 33 - FINAL AUTOMATIC MALNUTRITION EARLY WARNING ENGINE
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Build dashboard-ready early warnings from the already-generated
# Step 32B decision-support output.
#
# FINAL WARNING DESIGN
# --------------------
# - Current real calendar month = forecast origin.
# - H1, H3 and H6 are checked from the SAME origin.
# - HIGH / CRITICAL trigger a dashboard warning.
# - MEDIUM = watch only.
# - LOW = no warning.
# - ONE combined notification is created per district.
# - The overall district warning is the highest severity across
#   H1 / H3 / H6.
# - If the same district is risky at several horizons, the frontend
#   receives one district record containing all three horizons.
#
# IMPORTANT
# ---------
# DMBI Priority_Level is a planning-priority category.
# It is NOT a clinical diagnosis or clinical emergency category.
#
# INPUT
# -----
# outputs/reports/32b_future_triposha_packet_planning_demand.csv
#
# OUTPUTS
# -------
# outputs/reports/33_current_horizon_status_all_districts.csv
# outputs/reports/33_current_early_warnings.csv
# outputs/reports/33_current_early_warning_district_summary.csv
# outputs/reports/33_current_early_warning_summary.csv
# outputs/reports/33_early_warning_audit.csv
# outputs/reports/33_early_warning_methodology.json
# ============================================================

from pathlib import Path
from datetime import datetime
import json
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# 1. SETTINGS
# ============================================================

EXPECTED_DISTRICTS = 25
EXPECTED_HORIZONS = [1, 3, 6]

WARNING_PRIORITIES = {"HIGH", "CRITICAL"}

HORIZON_TYPE = {
    1: "SHORT-TERM",
    3: "MEDIUM-TERM",
    6: "LONG-TERM",
}

SEVERITY_SCORE = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

ALERT_LEVEL_MAP = {
    "LOW": "NO WARNING",
    "MEDIUM": "WATCH",
    "HIGH": "HIGH EARLY WARNING",
    "CRITICAL": "CRITICAL PLANNING WARNING",
}

ALERT_COLOR_MAP = {
    "LOW": "GREEN",
    "MEDIUM": "YELLOW",
    "HIGH": "ORANGE",
    "CRITICAL": "RED",
}


# ============================================================
# 2. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "outputs" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_PATH = REPORT_DIR / "32b_future_triposha_packet_planning_demand.csv"

OUT_ALL = REPORT_DIR / "33_current_horizon_status_all_districts.csv"
OUT_WARNINGS = REPORT_DIR / "33_current_early_warnings.csv"
OUT_DISTRICT = REPORT_DIR / "33_current_early_warning_district_summary.csv"
OUT_SUMMARY = REPORT_DIR / "33_current_early_warning_summary.csv"
OUT_AUDIT = REPORT_DIR / "33_early_warning_audit.csv"
OUT_METHOD = REPORT_DIR / "33_early_warning_methodology.json"


# ============================================================
# 3. HELPERS
# ============================================================

def heading(text):
    print("\n" + "=" * 120)
    print(text)
    print("=" * 120)


def clean_columns(df):
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def safe_int(value):
    if pd.isna(value):
        return None
    return int(round(float(value)))


def month_text(value):
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%B %Y")


def normalize_priority(value):
    value = str(value).strip().upper()
    if value not in SEVERITY_SCORE:
        raise ValueError(f"Unexpected Priority_Level: {value}")
    return value


def action_for_severity(severity):
    if severity == "CRITICAL":
        return (
            "Immediate district-level planning attention is recommended. "
            "Review monitoring, nutrition-resource readiness and programme preparedness."
        )
    if severity == "HIGH":
        return (
            "Early planning attention is recommended. "
            "Review district monitoring and nutrition-resource preparedness."
        )
    if severity == "MEDIUM":
        return "Continue monitoring. No HIGH/CRITICAL warning is active."
    return "No active HIGH/CRITICAL planning warning."


def notification_message(district, severity, nearest_horizon=None, nearest_month=None):
    if severity == "CRITICAL":
        base = f"Critical future malnutrition planning risk detected for {district}."
    elif severity == "HIGH":
        base = f"High future malnutrition planning risk detected for {district}."
    elif severity == "MEDIUM":
        return f"{district} is currently at watch level."
    else:
        return f"No active high-risk warning for {district}."

    if nearest_horizon is not None and nearest_month:
        return (
            f"{base} Nearest active warning: "
            f"H{nearest_horizon} ({nearest_month})."
        )
    return base


def build_email_subject(row):
    return (
        f"[{row['Priority_Level']}] Malnutrition Early Warning - "
        f"{row['District']} - {month_text(row['Forecast_Target_Date'])}"
    )


def build_email_body(row):
    horizon = int(row["Horizon_Months"])
    predicted_cases = safe_int(row["RF_Predicted_Cases"])

    lower_packets = safe_int(
        row.get("Triposha_Packets_Lower_95_ForecastDriven_Planning", np.nan)
    )
    base_packets = safe_int(
        row.get("Estimated_Triposha_Packets_Planning", np.nan)
    )
    upper_packets = safe_int(
        row.get("Triposha_Packets_Upper_95_ForecastDriven_Planning", np.nan)
    )

    return (
        "CHILDHOOD MALNUTRITION EARLY WARNING\n\n"
        f"District: {row['District']}\n"
        f"Forecast target month: {month_text(row['Forecast_Target_Date'])}\n"
        f"Forecast horizon: H{horizon}\n"
        f"Predicted malnutrition cases: {predicted_cases}\n"
        f"Planning priority: {row['Priority_Level']}\n"
        f"Forecast uncertainty: {row.get('Uncertainty_Level', 'Not available')}\n"
        f"Forecast confidence: {row.get('Confidence_Label', 'Not available')}\n\n"
        "Estimated Triposha packet planning demand:\n"
        f"  Lower: {lower_packets}\n"
        f"  Base: {base_packets}\n"
        f"  Upper: {upper_packets}\n\n"
        f"Planning action: {action_for_severity(row['Priority_Level'])}\n\n"
        "Important: This is a research-based operational planning alert, "
        "not a clinical diagnosis or treatment recommendation."
    )


# ============================================================
# 4. START
# ============================================================

heading("STEP 33 - FINAL AUTOMATIC MALNUTRITION EARLY WARNING ENGINE")

print("Current real month         : AUTO-DETECTED")
print("Current month role         : forecast origin")
print("H1                         : short-term warning")
print("H3                         : medium-term warning")
print("H6                         : long-term warning")
print("Warning trigger            : DMBI Priority HIGH or CRITICAL")
print("District notification      : ONE combined notification per district")
print("Overall severity           : highest severity across H1/H3/H6")
print("NGBoost                    : uncertainty/confidence information")
print("Triposha                   : resource-planning information")
print("New ML model training      : NO")
print("Forecast/DMBI recalculation: NO")


# ============================================================
# 5. DETECT CURRENT REAL MONTH
# ============================================================

now = datetime.now()
CURRENT_ORIGIN = pd.Timestamp(year=now.year, month=now.month, day=1)

expected_targets = {
    1: CURRENT_ORIGIN + pd.DateOffset(months=1),
    3: CURRENT_ORIGIN + pd.DateOffset(months=3),
    6: CURRENT_ORIGIN + pd.DateOffset(months=6),
}

print(f"\nDetected forecast origin    : {CURRENT_ORIGIN.strftime('%B %Y')}")
for horizon in EXPECTED_HORIZONS:
    print(
        f"H{horizon} target month             : "
        f"{expected_targets[horizon].strftime('%B %Y')}"
    )


# ============================================================
# 6. LOAD STEP 32B OUTPUT
# ============================================================

if not INPUT_PATH.exists():
    raise FileNotFoundError(
        f"Required Step 32B input not found:\n{INPUT_PATH}"
    )

df = clean_columns(pd.read_csv(INPUT_PATH, low_memory=False))

required_columns = {
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Horizon_Months",
    "RF_Predicted_Cases",
    "DMBI_Score",
    "Priority_Level",
    "Uncertainty_Level",
    "Confidence_Label",
    "Estimated_Triposha_Packets_Planning",
    "Triposha_Packets_Lower_95_ForecastDriven_Planning",
    "Triposha_Packets_Upper_95_ForecastDriven_Planning",
}

missing_columns = required_columns - set(df.columns)
if missing_columns:
    raise ValueError(
        "Missing required Step 32B columns: "
        f"{sorted(missing_columns)}"
    )

df["Forecast_Origin_Date"] = pd.to_datetime(
    df["Forecast_Origin_Date"], errors="coerce"
)
df["Forecast_Target_Date"] = pd.to_datetime(
    df["Forecast_Target_Date"], errors="coerce"
)
df["Horizon_Months"] = pd.to_numeric(
    df["Horizon_Months"], errors="coerce"
)
df["RF_Predicted_Cases"] = pd.to_numeric(
    df["RF_Predicted_Cases"], errors="coerce"
)
df["DMBI_Score"] = pd.to_numeric(
    df["DMBI_Score"], errors="coerce"
)

df["District"] = df["District"].astype(str).str.strip()
df["Priority_Level"] = df["Priority_Level"].apply(normalize_priority)

key_columns = [
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Horizon_Months",
    "RF_Predicted_Cases",
    "DMBI_Score",
    "Priority_Level",
]

if df[key_columns].isna().any().any():
    raise ValueError(
        "Missing or invalid required values found in Step 32B input."
    )

df["Horizon_Months"] = df["Horizon_Months"].astype(int)


# ============================================================
# 7. FILTER CURRENT FORECAST ORIGIN
# ============================================================

current = df[
    df["Forecast_Origin_Date"] == CURRENT_ORIGIN
].copy()

if current.empty:
    available = (
        df["Forecast_Origin_Date"]
        .dropna()
        .sort_values()
        .unique()
    )

    if len(available) > 0:
        first_origin = pd.Timestamp(available[0])
        last_origin = pd.Timestamp(available[-1])
        available_text = (
            f"{first_origin.strftime('%B %Y')} to "
            f"{last_origin.strftime('%B %Y')}"
        )
    else:
        available_text = "none"

    raise ValueError(
        "\nNo forecast exists for the real current month as origin.\n"
        f"Current month: {CURRENT_ORIGIN.strftime('%B %Y')}\n"
        f"Available forecast-origin range: {available_text}\n"
        "Step 33 stops rather than silently using a different month."
    )

print(f"\nCurrent-origin rows         : {len(current)}")


# ============================================================
# 8. STRICT H1 / H3 / H6 CHECK
# ============================================================

for horizon in EXPECTED_HORIZONS:
    horizon_df = current[
        current["Horizon_Months"] == horizon
    ].copy()

    if horizon_df.empty:
        raise ValueError(
            f"No H{horizon} rows found for current origin."
        )

    district_count = int(horizon_df["District"].nunique())
    if district_count != EXPECTED_DISTRICTS:
        raise ValueError(
            f"H{horizon}: expected {EXPECTED_DISTRICTS} districts, "
            f"found {district_count}."
        )

    expected_target = expected_targets[horizon]
    if not (
        horizon_df["Forecast_Target_Date"] == expected_target
    ).all():
        raise ValueError(
            f"H{horizon}: target-date semantics failed. "
            f"Expected {expected_target.date()}."
        )


# ============================================================
# 9. CREATE HORIZON-LEVEL WARNING STATUS
# ============================================================

current["Warning_Triggered"] = current[
    "Priority_Level"
].isin(WARNING_PRIORITIES)

current["Warning_Type"] = current[
    "Horizon_Months"
].map(HORIZON_TYPE)

current["Early_Warning_Level"] = current[
    "Priority_Level"
].map(ALERT_LEVEL_MAP)

current["Alert_Color"] = current[
    "Priority_Level"
].map(ALERT_COLOR_MAP)

current["Target_Month_Display"] = current[
    "Forecast_Target_Date"
].dt.strftime("%B %Y")

current["Predicted_Cases_Display"] = current[
    "RF_Predicted_Cases"
].round().astype(int)

current["Warning_Reason"] = np.where(
    current["Warning_Triggered"],
    current["Priority_Level"]
    + " relative forecast-based district planning priority",
    "No HIGH/CRITICAL planning-priority warning",
)

current["Warning_Interpretation"] = (
    "Planning early warning based on existing DMBI relative planning priority; "
    "not a clinical emergency classification."
)

current["Email_Subject"] = current.apply(
    build_email_subject, axis=1
)
current["Email_Body_Text"] = current.apply(
    build_email_body, axis=1
)


# ============================================================
# 10. SAVE ALL CURRENT HORIZON STATUS
# ============================================================

current = (
    current
    .sort_values(
        [
            "Horizon_Months",
            "Warning_Triggered",
            "DMBI_Score",
            "District",
        ],
        ascending=[True, False, False, True],
    )
    .reset_index(drop=True)
)

current.to_csv(OUT_ALL, index=False)


# ============================================================
# 11. SAVE RAW WARNING ROWS
# ============================================================

warnings_only = current[
    current["Warning_Triggered"]
].copy()

warnings_only.to_csv(OUT_WARNINGS, index=False)


# ============================================================
# 12. BUILD ONE COMBINED NOTIFICATION PER DISTRICT
# ============================================================

district_records = []

for district, district_df in current.groupby("District"):

    district_df = district_df.sort_values(
        "Horizon_Months"
    ).copy()

    if set(district_df["Horizon_Months"]) != set(EXPECTED_HORIZONS):
        raise ValueError(
            f"{district}: expected H1/H3/H6 rows."
        )

    rows = {
        int(row["Horizon_Months"]): row
        for _, row in district_df.iterrows()
    }

    priorities = {
        h: rows[h]["Priority_Level"]
        for h in EXPECTED_HORIZONS
    }

    overall_severity = max(
        priorities.values(),
        key=lambda x: SEVERITY_SCORE[x],
    )

    triggered_rows = district_df[
        district_df["Warning_Triggered"]
    ].sort_values("Horizon_Months")

    warning_triggered = not triggered_rows.empty

    if warning_triggered:
        nearest_row = triggered_rows.iloc[0]
        nearest_horizon = int(
            nearest_row["Horizon_Months"]
        )
        nearest_month = nearest_row[
            "Target_Month_Display"
        ]
        triggered_horizons = ", ".join(
            f"H{int(h)}"
            for h in triggered_rows["Horizon_Months"].tolist()
        )
        triggered_target_months = ", ".join(
            triggered_rows["Target_Month_Display"].tolist()
        )
    else:
        nearest_horizon = None
        nearest_month = ""
        triggered_horizons = ""
        triggered_target_months = ""

    record = {
        "District": district,
        "Current_Forecast_Origin": CURRENT_ORIGIN,
        "Warning_Triggered": bool(warning_triggered),
        "Overall_Severity": overall_severity,
        "Alert_Color": ALERT_COLOR_MAP[overall_severity],
        "Number_of_Triggered_Horizons": int(len(triggered_rows)),
        "Triggered_Horizons": triggered_horizons,
        "Triggered_Target_Months": triggered_target_months,
        "Nearest_Warning_Horizon": nearest_horizon,
        "Nearest_Warning_Month": nearest_month,
        "Notification_Message": notification_message(
            district,
            overall_severity,
            nearest_horizon,
            nearest_month,
        ),
        "Planning_Action": action_for_severity(
            overall_severity
        ),
    }

    for horizon in EXPECTED_HORIZONS:
        row = rows[horizon]

        record[f"H{horizon}_Priority"] = row["Priority_Level"]
        record[f"H{horizon}_Target_Date"] = row["Forecast_Target_Date"]
        record[f"H{horizon}_Target_Month"] = row["Target_Month_Display"]
        record[f"H{horizon}_Predicted_Cases"] = safe_int(
            row["RF_Predicted_Cases"]
        )
        record[f"H{horizon}_DMBI_Score"] = float(
            row["DMBI_Score"]
        )
        record[f"H{horizon}_Uncertainty_Level"] = row.get(
            "Uncertainty_Level", ""
        )
        record[f"H{horizon}_Confidence_Label"] = row.get(
            "Confidence_Label", ""
        )
        record[f"H{horizon}_Triposha_Packets_Base"] = safe_int(
            row.get(
                "Estimated_Triposha_Packets_Planning",
                np.nan,
            )
        )
        record[f"H{horizon}_Triposha_Packets_Lower"] = safe_int(
            row.get(
                "Triposha_Packets_Lower_95_ForecastDriven_Planning",
                np.nan,
            )
        )
        record[f"H{horizon}_Triposha_Packets_Upper"] = safe_int(
            row.get(
                "Triposha_Packets_Upper_95_ForecastDriven_Planning",
                np.nan,
            )
        )

    district_records.append(record)

district_summary = pd.DataFrame(district_records)

district_summary["Severity_Sort"] = district_summary[
    "Overall_Severity"
].map(SEVERITY_SCORE)

district_summary = (
    district_summary
    .sort_values(
        [
            "Warning_Triggered",
            "Severity_Sort",
            "Nearest_Warning_Horizon",
            "District",
        ],
        ascending=[False, False, True, True],
        na_position="last",
    )
    .drop(columns=["Severity_Sort"])
    .reset_index(drop=True)
)

district_summary.to_csv(
    OUT_DISTRICT,
    index=False,
)


# ============================================================
# 13. OVERALL DASHBOARD SUMMARY
# ============================================================

active_districts = district_summary[
    district_summary["Warning_Triggered"]
].copy()

summary_rows = []

for horizon in EXPECTED_HORIZONS:
    horizon_df = current[
        current["Horizon_Months"] == horizon
    ].copy()

    summary_rows.append(
        {
            "Forecast_Origin": CURRENT_ORIGIN,
            "Horizon_Months": horizon,
            "Warning_Type": HORIZON_TYPE[horizon],
            "Forecast_Target_Month": expected_targets[horizon],
            "Districts_Scanned": int(
                horizon_df["District"].nunique()
            ),
            "Critical_Warnings": int(
                (horizon_df["Priority_Level"] == "CRITICAL").sum()
            ),
            "High_Warnings": int(
                (horizon_df["Priority_Level"] == "HIGH").sum()
            ),
            "Total_Warnings": int(
                horizon_df["Warning_Triggered"].sum()
            ),
            "Watch_Medium": int(
                (horizon_df["Priority_Level"] == "MEDIUM").sum()
            ),
            "Low": int(
                (horizon_df["Priority_Level"] == "LOW").sum()
            ),
        }
    )

summary_df = pd.DataFrame(summary_rows)

summary_df["Unique_Districts_With_Active_Warning"] = int(
    len(active_districts)
)
summary_df["Unique_Critical_Districts"] = int(
    (
        active_districts["Overall_Severity"] == "CRITICAL"
    ).sum()
)
summary_df["Unique_High_Districts"] = int(
    (
        active_districts["Overall_Severity"] == "HIGH"
    ).sum()
)

summary_df.to_csv(
    OUT_SUMMARY,
    index=False,
)


# ============================================================
# 14. HARD AUDIT
# ============================================================

heading("STEP 33 HARD AUDIT")

audit_rows = []


def add_check(name, result, expected, passed):
    audit_rows.append(
        {
            "Audit_Check": name,
            "Result": result,
            "Expected": expected,
            "Status": "PASS" if passed else "FAIL",
        }
    )


add_check(
    "Current origin total rows",
    len(current),
    EXPECTED_DISTRICTS * len(EXPECTED_HORIZONS),
    len(current) == EXPECTED_DISTRICTS * len(EXPECTED_HORIZONS),
)

for horizon in EXPECTED_HORIZONS:
    horizon_df = current[
        current["Horizon_Months"] == horizon
    ]

    add_check(
        f"H{horizon} district rows",
        len(horizon_df),
        EXPECTED_DISTRICTS,
        len(horizon_df) == EXPECTED_DISTRICTS,
    )

    add_check(
        f"H{horizon} target semantics",
        str(horizon_df["Forecast_Target_Date"].iloc[0].date()),
        str(expected_targets[horizon].date()),
        (
            horizon_df["Forecast_Target_Date"]
            == expected_targets[horizon]
        ).all(),
    )

add_check(
    "One combined district row",
    len(district_summary),
    EXPECTED_DISTRICTS,
    len(district_summary) == EXPECTED_DISTRICTS,
)

add_check(
    "Warning trigger uses HIGH/CRITICAL only",
    sorted(
        current.loc[
            current["Warning_Triggered"],
            "Priority_Level",
        ].unique().tolist()
    ),
    ["CRITICAL", "HIGH"],
    current.loc[
        current["Warning_Triggered"],
        "Priority_Level",
    ].isin(WARNING_PRIORITIES).all(),
)

add_check(
    "District warning iff any H1/H3/H6 HIGH/CRITICAL",
    True,
    True,
    all(
        bool(row["Warning_Triggered"])
        ==
        (
            row["H1_Priority"] in WARNING_PRIORITIES
            or row["H3_Priority"] in WARNING_PRIORITIES
            or row["H6_Priority"] in WARNING_PRIORITIES
        )
        for _, row in district_summary.iterrows()
    ),
)

add_check(
    "Overall severity is highest H1/H3/H6 severity",
    True,
    True,
    all(
        row["Overall_Severity"]
        ==
        max(
            [
                row["H1_Priority"],
                row["H3_Priority"],
                row["H6_Priority"],
            ],
            key=lambda x: SEVERITY_SCORE[x],
        )
        for _, row in district_summary.iterrows()
    ),
)

add_check(
    "New ML model trained",
    False,
    False,
    True,
)

add_check(
    "Forecast recalculated",
    False,
    False,
    True,
)

add_check(
    "DMBI recalculated",
    False,
    False,
    True,
)

audit_df = pd.DataFrame(audit_rows)
audit_df.to_csv(OUT_AUDIT, index=False)

for _, row in audit_df.iterrows():
    print(
        f"{row['Audit_Check']:<58} : "
        f"{row['Status']}"
    )

if (audit_df["Status"] != "PASS").any():
    raise ValueError(
        "Step 33 hard audit failed. "
        "Review 33_early_warning_audit.csv"
    )


# ============================================================
# 15. METHODOLOGY RECORD
# ============================================================

methodology = {
    "step": 33,
    "name": "Final Automatic Malnutrition Early Warning Engine",
    "input": str(INPUT_PATH),
    "current_month_logic": (
        "The system runtime calendar month is automatically used "
        "as the common forecast origin."
    ),
    "horizons": {
        "H1": "origin + 1 month",
        "H3": "origin + 3 months",
        "H6": "origin + 6 months",
    },
    "warning_trigger": (
        "Existing DMBI Priority_Level is HIGH or CRITICAL."
    ),
    "medium_logic": "MEDIUM is watch only and does not trigger an active warning.",
    "low_logic": "LOW does not trigger a warning.",
    "combined_notification_logic": (
        "One combined notification record is created per district. "
        "The record contains H1, H3 and H6 status. Overall_Severity "
        "is the highest severity among H1/H3/H6."
    ),
    "nearest_warning_logic": (
        "Nearest_Warning_Horizon is the smallest horizon among active "
        "HIGH/CRITICAL horizon warnings."
    ),
    "ngboost_role": (
        "Provides uncertainty/confidence information only."
    ),
    "triposha_role": (
        "Provides resource-planning demand information."
    ),
    "new_ml_model_trained": False,
    "forecast_recalculated": False,
    "dmbi_recalculated": False,
    "interpretation": (
        "Research-based operational planning early warning. "
        "Priority levels are not clinical emergency diagnoses."
    ),
    "current_run": {
        "forecast_origin": str(CURRENT_ORIGIN.date()),
        "H1_target": str(expected_targets[1].date()),
        "H3_target": str(expected_targets[3].date()),
        "H6_target": str(expected_targets[6].date()),
        "raw_warning_rows": int(len(warnings_only)),
        "unique_warning_districts": int(len(active_districts)),
        "critical_districts": int(
            (
                active_districts["Overall_Severity"]
                == "CRITICAL"
            ).sum()
        ),
        "high_districts": int(
            (
                active_districts["Overall_Severity"]
                == "HIGH"
            ).sum()
        ),
    },
}

with open(
    OUT_METHOD,
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
# 16. COMPLETE
# ============================================================

heading("STEP 33 COMPLETE")

print(
    f"Forecast origin            : "
    f"{CURRENT_ORIGIN.strftime('%B %Y')}"
)
print(
    f"H1 target                  : "
    f"{expected_targets[1].strftime('%B %Y')}"
)
print(
    f"H3 target                  : "
    f"{expected_targets[3].strftime('%B %Y')}"
)
print(
    f"H6 target                  : "
    f"{expected_targets[6].strftime('%B %Y')}"
)

print(
    f"Raw HIGH/CRITICAL rows     : "
    f"{len(warnings_only)}"
)
print(
    f"Unique warning districts   : "
    f"{len(active_districts)}"
)
print(
    f"Critical districts         : "
    f"{int((active_districts['Overall_Severity'] == 'CRITICAL').sum())}"
)
print(
    f"High districts             : "
    f"{int((active_districts['Overall_Severity'] == 'HIGH').sum())}"
)

print("\nWarning summary by horizon:")
print(
    summary_df[
        [
            "Horizon_Months",
            "Warning_Type",
            "Forecast_Target_Month",
            "Critical_Warnings",
            "High_Warnings",
            "Total_Warnings",
            "Watch_Medium",
            "Low",
        ]
    ].to_string(index=False)
)

print("\nCombined active district notifications:")
if active_districts.empty:
    print("No active HIGH/CRITICAL district warnings.")
else:
    print(
        active_districts[
            [
                "District",
                "Overall_Severity",
                "H1_Priority",
                "H3_Priority",
                "H6_Priority",
                "Nearest_Warning_Horizon",
                "Nearest_Warning_Month",
            ]
        ].to_string(index=False)
    )

print("\nSaved outputs:")
for path in [
    OUT_ALL,
    OUT_WARNINGS,
    OUT_DISTRICT,
    OUT_SUMMARY,
    OUT_AUDIT,
    OUT_METHOD,
]:
    print(f"- {path}")

print(
    "\nSTEP 33 - FINAL AUTOMATIC MALNUTRITION EARLY WARNING ENGINE COMPLETE"
)
print("=" * 120)
