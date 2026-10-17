# ============================================================
# STEP 34 - DASHBOARD DATA EXPORT
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Convert the final research-pipeline outputs into a small,
# stable set of frontend/backend-ready dashboard files.
#
# IMPORTANT DESIGN
# ----------------
# 1. This step DOES NOT train, tune, or modify any model.
# 2. Random Forest remains the final point-forecast model.
# 3. NGBoost remains the separate uncertainty layer.
# 4. DMBI remains the relative district planning-priority layer.
# 5. SHAP remains the explanation layer for RF forecasts.
# 6. Triposha remains the planning-demand layer.
# 7. Step 33 remains the current automatic early-warning engine.
#
# FRONTEND FORECAST BEHAVIOUR
# ---------------------------
# User selects only:
#   - Year
#   - Month
#   - District
#
# Selected Year + Month = Forecast Origin.
#
# The frontend/backend then receives H1, H3 and H6 automatically
# for the SAME forecast origin. No horizon selector is required.
#
# MAIN INPUTS
# -----------
# outputs/reports/
#   32b_future_triposha_packet_planning_demand.csv
#   28b_future_shap_domain_explanations_2026_2030.csv
#   33_current_horizon_status_all_districts.csv
#   33_current_early_warning_district_summary.csv
#   33_current_early_warning_summary.csv
#
# Optional:
#   outputs/reports/31_future_gis_priority_2026_2030.csv
#   outputs/gis/31_sri_lanka_district_boundaries_wgs84.geojson
#   data/processed/malnutrition_preprocessed_base.csv
#
# OUTPUT DIRECTORY
# ----------------
# outputs/dashboard/
#
# MAIN OUTPUTS
# ------------
# metadata.json
# forecast_records.csv
# forecast_lookup.json
# shap_explanations.json
# resource_planning.csv
# gis_priority.csv
# warnings.json
# warning_summary.json
# annual_trends.json
# dataset_dashboard.csv
# district_boundaries.geojson        (if available)
# dashboard_manifest.json
# 34_dashboard_export_audit.csv
# ============================================================

from pathlib import Path
import json
import shutil
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# 1. SETTINGS
# ============================================================

EXPECTED_DISTRICTS = 25
EXPECTED_HORIZONS = [1, 3, 6]

SEVERITY_SCORE = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

WARNING_LEVELS = {"HIGH", "CRITICAL"}


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

REPORT_DIR = BASE_DIR / "outputs" / "reports"
GIS_DIR = BASE_DIR / "outputs" / "gis"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

DASHBOARD_DIR = BASE_DIR / "outputs" / "dashboard"
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 3. INPUT PATHS
# ============================================================

STEP32B_PATH = (
    REPORT_DIR
    / "32b_future_triposha_packet_planning_demand.csv"
)

STEP28B_PATH = (
    REPORT_DIR
    / "28b_future_shap_domain_explanations_2026_2030.csv"
)

STEP33_ALL_PATH = (
    REPORT_DIR
    / "33_current_horizon_status_all_districts.csv"
)

STEP33_DISTRICT_PATH = (
    REPORT_DIR
    / "33_current_early_warning_district_summary.csv"
)

STEP33_SUMMARY_PATH = (
    REPORT_DIR
    / "33_current_early_warning_summary.csv"
)

STEP31_GIS_PATH = (
    REPORT_DIR
    / "31_future_gis_priority_2026_2030.csv"
)

BOUNDARY_PATH = (
    GIS_DIR
    / "31_sri_lanka_district_boundaries_wgs84.geojson"
)

HISTORICAL_PATH = (
    PROCESSED_DIR
    / "malnutrition_preprocessed_base.csv"
)


# ============================================================
# 4. OUTPUT PATHS
# ============================================================

METADATA_OUT = DASHBOARD_DIR / "metadata.json"
FORECAST_RECORDS_OUT = DASHBOARD_DIR / "forecast_records.csv"
FORECAST_LOOKUP_OUT = DASHBOARD_DIR / "forecast_lookup.json"
SHAP_OUT = DASHBOARD_DIR / "shap_explanations.json"
RESOURCE_OUT = DASHBOARD_DIR / "resource_planning.csv"
GIS_OUT = DASHBOARD_DIR / "gis_priority.csv"
WARNINGS_OUT = DASHBOARD_DIR / "warnings.json"
WARNING_SUMMARY_OUT = DASHBOARD_DIR / "warning_summary.json"
ANNUAL_TRENDS_OUT = DASHBOARD_DIR / "annual_trends.json"
DATASET_OUT = DASHBOARD_DIR / "dataset_dashboard.csv"
BOUNDARY_OUT = DASHBOARD_DIR / "district_boundaries.geojson"
MANIFEST_OUT = DASHBOARD_DIR / "dashboard_manifest.json"
AUDIT_OUT = REPORT_DIR / "34_dashboard_export_audit.csv"


# ============================================================
# 5. HELPERS
# ============================================================

def heading(text):
    print("\n" + "=" * 120)
    print(text)
    print("=" * 120)


def require_file(path, label):
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found:\n{path}\n"
            "Run the required previous pipeline step first."
        )


def clean_columns(df):
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def find_column(df, candidates, required=True):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    if required:
        raise ValueError(
            "None of the expected columns were found:\n"
            f"{candidates}\n"
            f"Available columns:\n{list(df.columns)}"
        )

    return None


def to_date_string(value):
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def to_month_string(value):
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m")


def safe_float(value):
    if pd.isna(value):
        return None
    return float(value)


def safe_int(value):
    if pd.isna(value):
        return None
    return int(round(float(value)))


def normalize_priority(value):
    if pd.isna(value):
        return None
    return str(value).strip().upper()


def json_ready(value):
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if pd.isna(value):
        return None
    return value


def dump_json(path, obj):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            obj,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )


# ============================================================
# 6. START
# ============================================================

heading("STEP 34 - DASHBOARD DATA EXPORT")

print(f"Project root      : {BASE_DIR}")
print(f"Dashboard outputs : {DASHBOARD_DIR}")

print("\nFrontend contract:")
print("- User selects Year + Month + District")
print("- Selected Year + Month is the forecast origin")
print("- H1 / H3 / H6 are returned automatically")
print("- Clinic Staff page is not supported by this component export")


# ============================================================
# 7. REQUIRED INPUT CHECK
# ============================================================

require_file(
    STEP32B_PATH,
    "Step 32B future planning output",
)

require_file(
    STEP33_ALL_PATH,
    "Step 33 current horizon status",
)

require_file(
    STEP33_DISTRICT_PATH,
    "Step 33 district warning summary",
)

require_file(
    STEP33_SUMMARY_PATH,
    "Step 33 warning summary",
)


# ============================================================
# 8. LOAD MASTER FUTURE PLANNING DATA
# ============================================================

heading("LOAD FINAL FUTURE PLANNING DATA")

future = clean_columns(
    pd.read_csv(
        STEP32B_PATH,
        low_memory=False,
    )
)

district_col = find_column(
    future,
    ["District"],
)

origin_col = find_column(
    future,
    ["Forecast_Origin_Date"],
)

target_col = find_column(
    future,
    ["Forecast_Target_Date"],
)

horizon_col = find_column(
    future,
    ["Horizon_Months"],
)

rf_col = find_column(
    future,
    [
        "RF_Predicted_Cases",
        "Predicted_Cases",
        "Prediction",
    ],
)

priority_col = find_column(
    future,
    ["Priority_Level"],
)

dmbi_col = find_column(
    future,
    [
        "DMBI_Score",
        "DMBI_Score_0_100",
    ],
)

lower_col = find_column(
    future,
    [
        "NGBoost_Lower_95",
        "Lower_95",
    ],
    required=False,
)

upper_col = find_column(
    future,
    [
        "NGBoost_Upper_95",
        "Upper_95",
    ],
    required=False,
)

uncertainty_col = find_column(
    future,
    ["Uncertainty_Level"],
    required=False,
)

confidence_col = find_column(
    future,
    ["Confidence_Label"],
    required=False,
)

priority_rank_col = find_column(
    future,
    ["Priority_Rank"],
    required=False,
)

triposha_col = find_column(
    future,
    ["Estimated_Triposha_Packets_Planning"],
)

triposha_lower_col = find_column(
    future,
    [
        "Triposha_Packets_Lower_95_ForecastDriven_Planning",
    ],
    required=False,
)

triposha_upper_col = find_column(
    future,
    [
        "Triposha_Packets_Upper_95_ForecastDriven_Planning",
    ],
    required=False,
)

future[origin_col] = pd.to_datetime(
    future[origin_col],
    errors="coerce",
)

future[target_col] = pd.to_datetime(
    future[target_col],
    errors="coerce",
)

future[horizon_col] = pd.to_numeric(
    future[horizon_col],
    errors="coerce",
)

future[rf_col] = pd.to_numeric(
    future[rf_col],
    errors="coerce",
)

future[dmbi_col] = pd.to_numeric(
    future[dmbi_col],
    errors="coerce",
)

future[triposha_col] = pd.to_numeric(
    future[triposha_col],
    errors="coerce",
)

if future[
    [
        district_col,
        origin_col,
        target_col,
        horizon_col,
        rf_col,
        priority_col,
        dmbi_col,
        triposha_col,
    ]
].isna().any().any():
    raise ValueError(
        "Step 32B contains missing/invalid required dashboard values."
    )

future[horizon_col] = future[horizon_col].astype(int)

unexpected_horizons = sorted(
    set(future[horizon_col].unique())
    - set(EXPECTED_HORIZONS)
)

if unexpected_horizons:
    raise ValueError(
        f"Unexpected horizons found: {unexpected_horizons}"
    )

print(f"Rows             : {len(future)}")
print(f"Districts        : {future[district_col].nunique()}")
print(
    "Forecast origins : "
    f"{future[origin_col].min().date()} to "
    f"{future[origin_col].max().date()}"
)
print(
    "Target dates     : "
    f"{future[target_col].min().date()} to "
    f"{future[target_col].max().date()}"
)


# ============================================================
# 9. EXPORT FLAT FORECAST RECORDS
# ============================================================

heading("EXPORT FORECAST RECORDS")

forecast_records = pd.DataFrame(
    {
        "District": future[district_col].astype(str).str.strip(),
        "Forecast_Origin_Date": future[origin_col],
        "Forecast_Origin_Year": future[origin_col].dt.year.astype(int),
        "Forecast_Origin_Month": future[origin_col].dt.month.astype(int),
        "Forecast_Origin_Month_Name": future[origin_col].dt.month_name(),
        "Forecast_Target_Date": future[target_col],
        "Forecast_Target_Year": future[target_col].dt.year.astype(int),
        "Forecast_Target_Month": future[target_col].dt.month.astype(int),
        "Forecast_Target_Month_Name": future[target_col].dt.month_name(),
        "Horizon_Months": future[horizon_col].astype(int),
        "Horizon_Label": "H" + future[horizon_col].astype(str),
        "RF_Predicted_Cases": future[rf_col].astype(float),
        "DMBI_Score": future[dmbi_col].astype(float),
        "Priority_Level": future[priority_col].astype(str).str.strip(),
        "Estimated_Triposha_Packets_Planning":
            future[triposha_col].astype(float),
    }
)

if priority_rank_col is not None:
    forecast_records["Priority_Rank"] = pd.to_numeric(
        future[priority_rank_col],
        errors="coerce",
    )

if lower_col is not None:
    forecast_records["NGBoost_Lower_95"] = pd.to_numeric(
        future[lower_col],
        errors="coerce",
    )

if upper_col is not None:
    forecast_records["NGBoost_Upper_95"] = pd.to_numeric(
        future[upper_col],
        errors="coerce",
    )

if uncertainty_col is not None:
    forecast_records["Uncertainty_Level"] = (
        future[uncertainty_col]
        .astype(str)
        .str.strip()
    )

if confidence_col is not None:
    forecast_records["Confidence_Label"] = (
        future[confidence_col]
        .astype(str)
        .str.strip()
    )

if triposha_lower_col is not None:
    forecast_records[
        "Triposha_Packets_Lower_95"
    ] = pd.to_numeric(
        future[triposha_lower_col],
        errors="coerce",
    )

if triposha_upper_col is not None:
    forecast_records[
        "Triposha_Packets_Upper_95"
    ] = pd.to_numeric(
        future[triposha_upper_col],
        errors="coerce",
    )

forecast_records = (
    forecast_records
    .sort_values(
        [
            "Forecast_Origin_Date",
            "District",
            "Horizon_Months",
        ]
    )
    .reset_index(drop=True)
)

forecast_records.to_csv(
    FORECAST_RECORDS_OUT,
    index=False,
)

print(f"Saved: {FORECAST_RECORDS_OUT}")


# ============================================================
# 10. BUILD AUTO H1/H3/H6 FORECAST LOOKUP
# ============================================================

heading("BUILD FORECAST LOOKUP - YEAR + MONTH + DISTRICT -> H1/H3/H6")

lookup_records = []

for (
    origin_date,
    district,
), group in forecast_records.groupby(
    [
        "Forecast_Origin_Date",
        "District",
    ],
    sort=True,
):
    group = group.sort_values(
        "Horizon_Months"
    )

    horizon_map = {}

    for _, row in group.iterrows():
        h = int(row["Horizon_Months"])

        item = {
            "horizon": h,
            "target_date": to_date_string(
                row["Forecast_Target_Date"]
            ),
            "target_month": to_month_string(
                row["Forecast_Target_Date"]
            ),
            "predicted_cases": safe_float(
                row["RF_Predicted_Cases"]
            ),
            "priority_level": normalize_priority(
                row["Priority_Level"]
            ),
            "dmbi_score": safe_float(
                row["DMBI_Score"]
            ),
            "triposha_packets": safe_int(
                row[
                    "Estimated_Triposha_Packets_Planning"
                ]
            ),
        }

        for source_col, key in [
            ("NGBoost_Lower_95", "lower_95"),
            ("NGBoost_Upper_95", "upper_95"),
            ("Uncertainty_Level", "uncertainty_level"),
            ("Confidence_Label", "confidence_label"),
            ("Priority_Rank", "priority_rank"),
            ("Triposha_Packets_Lower_95", "triposha_lower_95"),
            ("Triposha_Packets_Upper_95", "triposha_upper_95"),
        ]:
            if source_col in row.index:
                item[key] = json_ready(
                    row[source_col]
                )

        horizon_map[f"h{h}"] = item

    # Most origin/district combinations should contain H1/H3/H6.
    # Near the end of the 2030 forecast range, longer horizons may
    # naturally be unavailable because their targets would fall
    # outside the final forecast target period.
    lookup_records.append(
        {
            "district": district,
            "forecast_origin": to_date_string(
                origin_date
            ),
            "year": int(
                pd.Timestamp(origin_date).year
            ),
            "month": int(
                pd.Timestamp(origin_date).month
            ),
            "month_name": pd.Timestamp(
                origin_date
            ).month_name(),
            "available_horizons": sorted(
                [
                    int(key.replace("h", ""))
                    for key in horizon_map
                ]
            ),
            "forecasts": horizon_map,
        }
    )

dump_json(
    FORECAST_LOOKUP_OUT,
    lookup_records,
)

print(f"Lookup groups: {len(lookup_records)}")
print(f"Saved        : {FORECAST_LOOKUP_OUT}")


# ============================================================
# 11. SHAP EXPLANATION EXPORT
# ============================================================

heading("EXPORT SHAP EXPLANATIONS")

shap_export = []

if STEP28B_PATH.exists():
    shap_df = clean_columns(
        pd.read_csv(
            STEP28B_PATH,
            low_memory=False,
        )
    )

    shap_district = find_column(
        shap_df,
        ["District"],
    )
    shap_origin = find_column(
        shap_df,
        ["Forecast_Origin_Date"],
    )
    shap_target = find_column(
        shap_df,
        ["Forecast_Target_Date"],
    )
    shap_horizon = find_column(
        shap_df,
        ["Horizon_Months"],
    )

    shap_df[shap_origin] = pd.to_datetime(
        shap_df[shap_origin],
        errors="coerce",
    )
    shap_df[shap_target] = pd.to_datetime(
        shap_df[shap_target],
        errors="coerce",
    )

    for _, row in shap_df.iterrows():
        record = {
            "district": str(
                row[shap_district]
            ).strip(),
            "forecast_origin": to_date_string(
                row[shap_origin]
            ),
            "target_date": to_date_string(
                row[shap_target]
            ),
            "horizon": int(
                row[shap_horizon]
            ),
            "predicted_cases": safe_float(
                row.get(
                    "RF_Predicted_Cases",
                    np.nan,
                )
            ),
            "dominant_domain": json_ready(
                row.get(
                    "Dominant_Domain",
                    None,
                )
            ),
            "dominant_domain_shap": safe_float(
                row.get(
                    "Dominant_Domain_SHAP",
                    np.nan,
                )
            ),
            "dominant_domain_direction": json_ready(
                row.get(
                    "Dominant_Domain_Direction",
                    None,
                )
            ),
            "explanation": json_ready(
                row.get(
                    "Doctor_Friendly_SHAP_Explanation",
                    None,
                )
            ),
            "top_increasing": [],
            "top_decreasing": [],
        }

        for rank in [1, 2, 3]:
            domain = row.get(
                f"Top_Increasing_{rank}_Domain",
                np.nan,
            )

            if not pd.isna(domain):
                record["top_increasing"].append(
                    {
                        "rank": rank,
                        "domain": json_ready(domain),
                        "domain_shap": safe_float(
                            row.get(
                                f"Top_Increasing_{rank}_Domain_SHAP",
                                np.nan,
                            )
                        ),
                        "top_feature": json_ready(
                            row.get(
                                f"Top_Increasing_{rank}_Top_Feature",
                                None,
                            )
                        ),
                        "top_feature_shap": safe_float(
                            row.get(
                                f"Top_Increasing_{rank}_Top_Feature_SHAP",
                                np.nan,
                            )
                        ),
                    }
                )

            domain = row.get(
                f"Top_Decreasing_{rank}_Domain",
                np.nan,
            )

            if not pd.isna(domain):
                record["top_decreasing"].append(
                    {
                        "rank": rank,
                        "domain": json_ready(domain),
                        "domain_shap": safe_float(
                            row.get(
                                f"Top_Decreasing_{rank}_Domain_SHAP",
                                np.nan,
                            )
                        ),
                        "top_feature": json_ready(
                            row.get(
                                f"Top_Decreasing_{rank}_Top_Feature",
                                None,
                            )
                        ),
                        "top_feature_shap": safe_float(
                            row.get(
                                f"Top_Decreasing_{rank}_Top_Feature_SHAP",
                                np.nan,
                            )
                        ),
                    }
                )

        shap_export.append(record)

    print(f"SHAP records: {len(shap_export)}")

else:
    print(
        "Optional Step 28B SHAP summary was not found. "
        "SHAP export will be empty."
    )

dump_json(
    SHAP_OUT,
    shap_export,
)

print(f"Saved: {SHAP_OUT}")


# ============================================================
# 12. RESOURCE PLANNING EXPORT
# ============================================================

heading("EXPORT RESOURCE PLANNING")

resource_columns = [
    "District",
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
    "Horizon_Months",
    "RF_Predicted_Cases",
    "Priority_Level",
    "DMBI_Score",
    "Estimated_Triposha_Packets_Planning",
]

for optional in [
    "Triposha_Packets_Lower_95",
    "Triposha_Packets_Upper_95",
    "Uncertainty_Level",
    "Confidence_Label",
]:
    if optional in forecast_records.columns:
        resource_columns.append(optional)

resource_df = forecast_records[
    resource_columns
].copy()

resource_df.to_csv(
    RESOURCE_OUT,
    index=False,
)

print(f"Saved: {RESOURCE_OUT}")


# ============================================================
# 13. GIS PRIORITY EXPORT
# ============================================================

heading("EXPORT GIS PRIORITY")

if STEP31_GIS_PATH.exists():
    gis_df = clean_columns(
        pd.read_csv(
            STEP31_GIS_PATH,
            low_memory=False,
        )
    )
    gis_df.to_csv(
        GIS_OUT,
        index=False,
    )
else:
    # Step 32B already carries the final planning and forecast
    # attributes needed for a frontend map. Use it as fallback.
    gis_df = forecast_records.copy()
    gis_df.to_csv(
        GIS_OUT,
        index=False,
    )

print(f"Saved: {GIS_OUT}")

if BOUNDARY_PATH.exists():
    shutil.copy2(
        BOUNDARY_PATH,
        BOUNDARY_OUT,
    )
    print(f"Saved: {BOUNDARY_OUT}")
else:
    print(
        "Optional district boundary GeoJSON not found. "
        "Run Step 31 if the frontend requires the map boundary file."
    )


# ============================================================
# 14. CURRENT EARLY WARNING EXPORT
# ============================================================

heading("EXPORT CURRENT EARLY WARNINGS")

warning_all = clean_columns(
    pd.read_csv(
        STEP33_ALL_PATH,
        low_memory=False,
    )
)

warning_district = clean_columns(
    pd.read_csv(
        STEP33_DISTRICT_PATH,
        low_memory=False,
    )
)

warning_summary_df = clean_columns(
    pd.read_csv(
        STEP33_SUMMARY_PATH,
        low_memory=False,
    )
)

warning_all["Forecast_Origin_Date"] = pd.to_datetime(
    warning_all["Forecast_Origin_Date"],
    errors="coerce",
)

warning_all["Forecast_Target_Date"] = pd.to_datetime(
    warning_all["Forecast_Target_Date"],
    errors="coerce",
)

# Rebuild the combined frontend warning contract from the
# horizon-level file. This keeps Step 34 compatible even if the
# exact Step 33 district-summary columns change later.
warning_records = []

for district, group in warning_all.groupby(
    "District",
    sort=True,
):
    group = group.sort_values(
        "Horizon_Months"
    )

    horizons = {}

    for _, row in group.iterrows():
        horizon = int(
            row["Horizon_Months"]
        )

        priority = normalize_priority(
            row["Priority_Level"]
        )

        horizons[f"h{horizon}"] = {
            "horizon": horizon,
            "target_date": to_date_string(
                row["Forecast_Target_Date"]
            ),
            "target_month": to_month_string(
                row["Forecast_Target_Date"]
            ),
            "target_month_display": pd.Timestamp(
                row["Forecast_Target_Date"]
            ).strftime("%B %Y"),
            "priority": priority,
            "warning_triggered":
                priority in WARNING_LEVELS,
            "predicted_cases": safe_int(
                row.get(
                    "RF_Predicted_Cases",
                    np.nan,
                )
            ),
            "dmbi_score": safe_float(
                row.get(
                    "DMBI_Score",
                    np.nan,
                )
            ),
            "uncertainty_level": json_ready(
                row.get(
                    "Uncertainty_Level",
                    None,
                )
            ),
            "confidence_label": json_ready(
                row.get(
                    "Confidence_Label",
                    None,
                )
            ),
            "triposha_packets": safe_int(
                row.get(
                    "Estimated_Triposha_Packets_Planning",
                    np.nan,
                )
            ),
        }

    priorities = [
        h["priority"]
        for h in horizons.values()
        if h["priority"] in SEVERITY_SCORE
    ]

    overall = (
        max(
            priorities,
            key=lambda x: SEVERITY_SCORE[x],
        )
        if priorities
        else "LOW"
    )

    active = [
        h
        for h in horizons.values()
        if h["warning_triggered"]
    ]

    if not active:
        continue

    active = sorted(
        active,
        key=lambda x: x["horizon"],
    )

    nearest = active[0]

    if overall == "CRITICAL":
        message = (
            f"Critical future malnutrition planning risk "
            f"detected for {district}."
        )
        action = (
            "Immediate district-level planning attention is recommended."
        )
    else:
        message = (
            f"High future malnutrition planning risk "
            f"detected for {district}."
        )
        action = (
            "Early planning attention and resource preparedness are recommended."
        )

    warning_records.append(
        {
            "district": str(district).strip(),
            "forecast_origin": to_date_string(
                group[
                    "Forecast_Origin_Date"
                ].iloc[0]
            ),
            "overall_severity": overall,
            "warning_triggered": True,
            "nearest_warning_horizon":
                nearest["horizon"],
            "nearest_warning_month":
                nearest["target_month"],
            "nearest_warning_month_display":
                nearest[
                    "target_month_display"
                ],
            "triggered_horizons": [
                item["horizon"]
                for item in active
            ],
            "message": message,
            "action": action,
            "horizons": horizons,
        }
    )

warning_records = sorted(
    warning_records,
    key=lambda x: (
        -SEVERITY_SCORE[
            x["overall_severity"]
        ],
        x["nearest_warning_horizon"],
        x["district"],
    ),
)

dump_json(
    WARNINGS_OUT,
    warning_records,
)

critical_count = sum(
    item["overall_severity"] == "CRITICAL"
    for item in warning_records
)

high_count = sum(
    item["overall_severity"] == "HIGH"
    for item in warning_records
)

preview = [
    {
        "district": item["district"],
        "overall_severity":
            item["overall_severity"],
        "nearest_warning_horizon":
            item[
                "nearest_warning_horizon"
            ],
        "nearest_warning_month_display":
            item[
                "nearest_warning_month_display"
            ],
        "message": item["message"],
    }
    for item in warning_records[:5]
]

warning_summary = {
    "forecast_origin": (
        warning_records[0]["forecast_origin"]
        if warning_records
        else None
    ),
    "warning_count": len(
        warning_records
    ),
    "critical_count": int(
        critical_count
    ),
    "high_count": int(
        high_count
    ),
    "latest_warnings": preview,
}

dump_json(
    WARNING_SUMMARY_OUT,
    warning_summary,
)

print(f"Unique warning districts : {len(warning_records)}")
print(f"Critical districts       : {critical_count}")
print(f"High districts           : {high_count}")
print(f"Saved: {WARNINGS_OUT}")
print(f"Saved: {WARNING_SUMMARY_OUT}")


# ============================================================
# 15. HISTORICAL TREND + DATASET EXPORT
# ============================================================

heading("EXPORT HISTORICAL TREND / DATASET")

annual_trends = []

if HISTORICAL_PATH.exists():
    historical = clean_columns(
        pd.read_csv(
            HISTORICAL_PATH,
            low_memory=False,
        )
    )

    year_col = find_column(
        historical,
        ["Year"],
    )
    historical_district_col = find_column(
        historical,
        ["District"],
    )
    target_historical_col = find_column(
        historical,
        ["Malnutrition_Cases"],
    )

    historical[year_col] = pd.to_numeric(
        historical[year_col],
        errors="coerce",
    )

    historical[target_historical_col] = pd.to_numeric(
        historical[target_historical_col],
        errors="coerce",
    )

    trend_source = historical.dropna(
        subset=[
            year_col,
            target_historical_col,
        ]
    ).copy()

    annual = (
        trend_source
        .groupby(
            year_col,
            as_index=False,
        )
        .agg(
            total_cases=(
                target_historical_col,
                "sum",
            ),
            mean_district_month_cases=(
                target_historical_col,
                "mean",
            ),
            available_observations=(
                target_historical_col,
                "count",
            ),
        )
        .sort_values(
            year_col
        )
    )

    annual_trends = [
        {
            "year": int(row[year_col]),
            "total_cases": float(
                row["total_cases"]
            ),
            "mean_district_month_cases":
                float(
                    row[
                        "mean_district_month_cases"
                    ]
                ),
            "available_observations":
                int(
                    row[
                        "available_observations"
                    ]
                ),
        }
        for _, row in annual.iterrows()
    ]

    # Keep a dashboard-friendly historical dataset.
    preferred_dataset_columns = [
        "Year",
        "Month",
        "Month_Name",
        "District",
        "Malnutrition_Cases",
        "Under 5 Population",
        "Live Birth",
        "Triposha_Packets_Distributed",
        "Poverty_Line_Rs_Monthly",
        "Low_Birth_Weight_Cases",
        "T2M",
        "PRECTOTCORR",
        "RH2M",
        "Household_Income",
    ]

    dataset_columns = [
        column
        for column in preferred_dataset_columns
        if column in historical.columns
    ]

    historical[
        dataset_columns
    ].to_csv(
        DATASET_OUT,
        index=False,
    )

    print(f"Saved: {DATASET_OUT}")

else:
    print(
        "Historical preprocessed dataset not found. "
        "Annual trend and dataset exports will be empty."
    )

dump_json(
    ANNUAL_TRENDS_OUT,
    annual_trends,
)

print(f"Saved: {ANNUAL_TRENDS_OUT}")


# ============================================================
# 16. METADATA
# ============================================================

heading("EXPORT DASHBOARD METADATA")

origin_dates = (
    forecast_records[
        "Forecast_Origin_Date"
    ]
    .drop_duplicates()
    .sort_values()
)

target_dates = (
    forecast_records[
        "Forecast_Target_Date"
    ]
    .drop_duplicates()
    .sort_values()
)

metadata = {
    "component": (
        "Explainable AI Framework for Early Detection "
        "and Personalized Childhood Malnutrition Intervention "
        "- District Forecasting Component"
    ),
    "point_forecast_model": "Random Forest",
    "uncertainty_model": "NGBoost",
    "explainability": "SHAP",
    "priority_method": "CRITIC-TOPSIS DMBI",
    "resource_planning": "Triposha packet planning demand",
    "forecast_horizons_months": EXPECTED_HORIZONS,
    "district_count": int(
        forecast_records[
            "District"
        ].nunique()
    ),
    "districts": sorted(
        forecast_records[
            "District"
        ].unique().tolist()
    ),
    "forecast_origin_start": to_date_string(
        origin_dates.iloc[0]
    ),
    "forecast_origin_end": to_date_string(
        origin_dates.iloc[-1]
    ),
    "forecast_target_start": to_date_string(
        target_dates.iloc[0]
    ),
    "forecast_target_end": to_date_string(
        target_dates.iloc[-1]
    ),
    "forecast_page_contract": {
        "user_inputs": [
            "year",
            "month",
            "district",
        ],
        "automatic_outputs": [
            "H1",
            "H3",
            "H6",
        ],
        "horizon_selector_required": False,
        "model_selector_required": False,
    },
    "warning_contract": {
        "active_levels": [
            "HIGH",
            "CRITICAL",
        ],
        "combined_per_district": True,
        "dashboard_preview_limit": 5,
    },
}

dump_json(
    METADATA_OUT,
    metadata,
)

print(f"Saved: {METADATA_OUT}")


# ============================================================
# 17. MANIFEST
# ============================================================

manifest = {
    "metadata": METADATA_OUT.name,
    "forecast_records": FORECAST_RECORDS_OUT.name,
    "forecast_lookup": FORECAST_LOOKUP_OUT.name,
    "shap_explanations": SHAP_OUT.name,
    "resource_planning": RESOURCE_OUT.name,
    "gis_priority": GIS_OUT.name,
    "warnings": WARNINGS_OUT.name,
    "warning_summary": WARNING_SUMMARY_OUT.name,
    "annual_trends": ANNUAL_TRENDS_OUT.name,
    "dataset_dashboard": (
        DATASET_OUT.name
        if DATASET_OUT.exists()
        else None
    ),
    "district_boundaries": (
        BOUNDARY_OUT.name
        if BOUNDARY_OUT.exists()
        else None
    ),
}

dump_json(
    MANIFEST_OUT,
    manifest,
)


# ============================================================
# 18. HARD AUDIT
# ============================================================

heading("STEP 34 HARD AUDIT")

audit_rows = []


def add_audit(check, result, expected, passed):
    audit_rows.append(
        {
            "Audit_Check": check,
            "Result": result,
            "Expected": expected,
            "Status": (
                "PASS"
                if passed
                else "FAIL"
            ),
        }
    )


add_audit(
    "District count",
    int(
        forecast_records[
            "District"
        ].nunique()
    ),
    EXPECTED_DISTRICTS,
    int(
        forecast_records[
            "District"
        ].nunique()
    ) == EXPECTED_DISTRICTS,
)

add_audit(
    "Forecast horizons",
    sorted(
        forecast_records[
            "Horizon_Months"
        ].unique().tolist()
    ),
    EXPECTED_HORIZONS,
    sorted(
        forecast_records[
            "Horizon_Months"
        ].unique().tolist()
    ) == EXPECTED_HORIZONS,
)

duplicate_keys = int(
    forecast_records.duplicated(
        subset=[
            "District",
            "Forecast_Origin_Date",
            "Forecast_Target_Date",
            "Horizon_Months",
        ]
    ).sum()
)

add_audit(
    "Duplicate forecast keys",
    duplicate_keys,
    0,
    duplicate_keys == 0,
)

add_audit(
    "Negative RF predictions",
    int(
        (
            forecast_records[
                "RF_Predicted_Cases"
            ]
            < 0
        ).sum()
    ),
    0,
    not (
        forecast_records[
            "RF_Predicted_Cases"
        ]
        < 0
    ).any(),
)

add_audit(
    "DMBI scores inside [0,100]",
    True,
    True,
    forecast_records[
        "DMBI_Score"
    ].between(
        0,
        100,
        inclusive="both",
    ).all(),
)

add_audit(
    "Warning export unique by district",
    len(
        {
            item["district"]
            for item in warning_records
        }
    ),
    len(warning_records),
    len(
        {
            item["district"]
            for item in warning_records
        }
    )
    == len(warning_records),
)

add_audit(
    "Warning levels only HIGH/CRITICAL",
    sorted(
        {
            item[
                "overall_severity"
            ]
            for item in warning_records
        }
    ),
    "subset of HIGH/CRITICAL",
    all(
        item[
            "overall_severity"
        ]
        in WARNING_LEVELS
        for item in warning_records
    ),
)

required_exports = [
    METADATA_OUT,
    FORECAST_RECORDS_OUT,
    FORECAST_LOOKUP_OUT,
    SHAP_OUT,
    RESOURCE_OUT,
    GIS_OUT,
    WARNINGS_OUT,
    WARNING_SUMMARY_OUT,
    ANNUAL_TRENDS_OUT,
    MANIFEST_OUT,
]

add_audit(
    "Required dashboard files created",
    sum(
        path.exists()
        for path in required_exports
    ),
    len(required_exports),
    all(
        path.exists()
        for path in required_exports
    ),
)

add_audit(
    "Model retraining performed in Step 34",
    False,
    False,
    True,
)

add_audit(
    "Forecast recalculated in Step 34",
    False,
    False,
    True,
)

add_audit(
    "DMBI recalculated in Step 34",
    False,
    False,
    True,
)

audit_df = pd.DataFrame(
    audit_rows
)

audit_df.to_csv(
    AUDIT_OUT,
    index=False,
)

for _, row in audit_df.iterrows():
    print(
        f"{row['Audit_Check']:<50} : "
        f"{row['Status']}"
    )

if (
    audit_df["Status"]
    != "PASS"
).any():
    raise ValueError(
        "Step 34 dashboard export audit failed. "
        f"Review:\n{AUDIT_OUT}"
    )


# ============================================================
# 19. COMPLETE
# ============================================================

heading("STEP 34 COMPLETE")

print("Dashboard-ready data export completed successfully.")
print("\nFrontend forecast behaviour:")
print("Year + Month + District -> automatic H1/H3/H6 results")

print("\nMain files:")
for path in [
    METADATA_OUT,
    FORECAST_RECORDS_OUT,
    FORECAST_LOOKUP_OUT,
    SHAP_OUT,
    RESOURCE_OUT,
    GIS_OUT,
    WARNINGS_OUT,
    WARNING_SUMMARY_OUT,
    ANNUAL_TRENDS_OUT,
    DATASET_OUT,
    BOUNDARY_OUT,
    MANIFEST_OUT,
    AUDIT_OUT,
]:
    if path.exists():
        print(f"- {path}")

print("\nNo model was trained or modified in Step 34.")
print("=" * 120)
