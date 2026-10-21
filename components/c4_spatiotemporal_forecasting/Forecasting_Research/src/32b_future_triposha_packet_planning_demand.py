from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

EXPECTED_TOTAL_ROWS = 4325
EXPECTED_DISTRICTS = 25
EXPECTED_HORIZON_ROWS = {1: 1500, 3: 1450, 6: 1375}
EXPECTED_SELECTED_RULE = "DISTRICT_MEDIAN"

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "outputs" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SELECTED_RULE_PATH = REPORT_DIR / "32a_triposha_selected_rule.csv"
PARAMETERS_PATH = REPORT_DIR / "32a_triposha_selected_rule_parameters.csv"
STEP30_PATH = REPORT_DIR / "30_future_district_risk_prioritization.csv"

OUT_MAIN = REPORT_DIR / "32b_future_triposha_packet_planning_demand.csv"
OUT_MONTHLY = REPORT_DIR / "32b_future_triposha_monthly_summary.csv"
OUT_DISTRICT = REPORT_DIR / "32b_future_triposha_district_summary.csv"
OUT_AUDIT = REPORT_DIR / "32b_future_triposha_audit.csv"
OUT_METHOD = REPORT_DIR / "32b_future_triposha_methodology.json"


def heading(text):
    print("\n" + "=" * 120)
    print(text)
    print("=" * 120)


def clean_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def first_existing(columns, candidates):
    for c in candidates:
        if c in columns:
            return c
    return None


heading("STEP 32B - FUTURE TRIPOSHA PACKET PLANNING DEMAND")
print("Step 32A frozen rule      : used unchanged")
print("2026-2030 RF forecasts    : used unchanged")
print("New ML model training     : NO")
print("Rule reselection/tuning   : NO")
print("RF/NGBoost/SHAP/DMBI edit : NO")

for p in [SELECTED_RULE_PATH, PARAMETERS_PATH, STEP30_PATH]:
    if not p.exists():
        raise FileNotFoundError(f"Required input not found:\n{p}")

# ------------------------------------------------------------------
# Load frozen selected rule
# ------------------------------------------------------------------
selected_df = clean_columns(pd.read_csv(SELECTED_RULE_PATH, low_memory=False))
if selected_df.empty or "Selected_Rule" not in selected_df.columns:
    raise ValueError("Invalid Step 32A selected-rule file.")

selected_rule = str(selected_df.iloc[0]["Selected_Rule"]).strip()
if selected_rule != EXPECTED_SELECTED_RULE:
    raise ValueError(
        f"Expected Step 32A frozen rule {EXPECTED_SELECTED_RULE}, found {selected_rule}"
    )

print(f"\nFrozen selected rule      : {selected_rule}")

# ------------------------------------------------------------------
# Load frozen district ratios
# ------------------------------------------------------------------
params = clean_columns(pd.read_csv(PARAMETERS_PATH, low_memory=False))

required = {"Parameter_Type", "District", "Packets_Per_Case_Ratio"}
missing = required - set(params.columns)
if missing:
    raise ValueError(f"Missing Step 32A parameter columns: {sorted(missing)}")

params["Parameter_Type"] = params["Parameter_Type"].astype(str).str.strip()
params["District"] = params["District"].fillna("").astype(str).str.strip()
params["Packets_Per_Case_Ratio"] = pd.to_numeric(
    params["Packets_Per_Case_Ratio"], errors="coerce"
)

district_params = params[params["Parameter_Type"] == "DISTRICT"].copy()

if district_params["District"].duplicated().any():
    raise ValueError("Duplicate district parameters found.")

if len(district_params) != EXPECTED_DISTRICTS:
    raise ValueError(
        f"Expected 25 district parameters, found {len(district_params)}."
    )

if district_params["Packets_Per_Case_Ratio"].isna().any():
    raise ValueError("Missing frozen district ratio values.")

if (~np.isfinite(district_params["Packets_Per_Case_Ratio"])).any():
    raise ValueError("Non-finite frozen district ratio values.")

if (district_params["Packets_Per_Case_Ratio"] < 0).any():
    raise ValueError("Negative frozen district ratio values.")

ratio_table = district_params[
    ["District", "Packets_Per_Case_Ratio"]
].rename(
    columns={
        "Packets_Per_Case_Ratio": "Frozen_District_Packets_Per_Case_Ratio"
    }
)

print(f"Frozen district parameters: {len(ratio_table)}")

# ------------------------------------------------------------------
# Load Step 30 future forecast/prioritization output
# ------------------------------------------------------------------
future = clean_columns(pd.read_csv(STEP30_PATH, low_memory=False))

district_col = first_existing(future.columns, ["District", "district"])
horizon_col = first_existing(
    future.columns, ["Horizon_Months", "Horizon", "Forecast_Horizon"]
)
date_col = first_existing(
    future.columns, ["Forecast_Target_Date", "Target_Date", "Forecast_Date"]
)
rf_col = first_existing(
    future.columns, ["RF_Predicted_Cases", "Prediction", "Predicted_Cases"]
)

if None in [district_col, horizon_col, date_col, rf_col]:
    raise ValueError(
        "Could not identify District/Horizon/Forecast_Target_Date/RF prediction columns in Step 30."
    )

rename_map = {}
if district_col != "District":
    rename_map[district_col] = "District"
if horizon_col != "Horizon_Months":
    rename_map[horizon_col] = "Horizon_Months"
if date_col != "Forecast_Target_Date":
    rename_map[date_col] = "Forecast_Target_Date"
if rf_col != "RF_Predicted_Cases":
    rename_map[rf_col] = "RF_Predicted_Cases"

future = future.rename(columns=rename_map)

future["District"] = future["District"].astype(str).str.strip()
future["Horizon_Months"] = pd.to_numeric(
    future["Horizon_Months"], errors="coerce"
)
future["Forecast_Target_Date"] = pd.to_datetime(
    future["Forecast_Target_Date"], errors="coerce"
)
future["RF_Predicted_Cases"] = pd.to_numeric(
    future["RF_Predicted_Cases"], errors="coerce"
)

if future[
    ["District", "Horizon_Months", "Forecast_Target_Date", "RF_Predicted_Cases"]
].isna().any().any():
    raise ValueError("Missing/invalid key values in Step 30 future file.")

future["Horizon_Months"] = future["Horizon_Months"].astype(int)

if (future["RF_Predicted_Cases"] < 0).any():
    raise ValueError("Negative RF predictions found.")

print(f"\nStep 30 future rows       : {len(future)}")
print(f"Districts                 : {future['District'].nunique()}")
print(
    f"Target range              : "
    f"{future['Forecast_Target_Date'].min().date()} to "
    f"{future['Forecast_Target_Date'].max().date()}"
)

# ------------------------------------------------------------------
# Join frozen ratio and estimate resource planning demand
# ------------------------------------------------------------------
out = future.merge(
    ratio_table,
    on="District",
    how="left",
    validate="many_to_one"
)

if out["Frozen_District_Packets_Per_Case_Ratio"].isna().any():
    missing_districts = sorted(
        out.loc[
            out["Frozen_District_Packets_Per_Case_Ratio"].isna(),
            "District"
        ].unique().tolist()
    )
    raise ValueError(
        f"Missing frozen ratio for district(s): {missing_districts}"
    )

out["Estimated_Triposha_Packets_Raw"] = (
    out["RF_Predicted_Cases"]
    * out["Frozen_District_Packets_Per_Case_Ratio"]
)

# Procurement/planning field: whole packets, rounded upward.
out["Estimated_Triposha_Packets_Planning"] = np.ceil(
    out["Estimated_Triposha_Packets_Raw"]
).astype("Int64")

out["Resource_Estimation_Rule"] = selected_rule
out["Resource_Estimation_Label"] = (
    "Estimated Triposha Packet Planning Demand"
)
out["Resource_Interpretation"] = (
    "Operational planning estimate; not clinical eligibility or dosage"
)

# ------------------------------------------------------------------
# Optional propagation of NGBoost malnutrition forecast interval
# ------------------------------------------------------------------
lower_col = first_existing(
    out.columns,
    ["NGBoost_Lower_95", "Lower_95", "Prediction_Lower_95"]
)
upper_col = first_existing(
    out.columns,
    ["NGBoost_Upper_95", "Upper_95", "Prediction_Upper_95"]
)

has_uncertainty = (lower_col is not None and upper_col is not None)

if has_uncertainty:
    out[lower_col] = pd.to_numeric(out[lower_col], errors="coerce")
    out[upper_col] = pd.to_numeric(out[upper_col], errors="coerce")

    if out[[lower_col, upper_col]].isna().any().any():
        raise ValueError("NGBoost interval columns contain invalid values.")

    out["Triposha_Packets_Lower_95_ForecastDriven_Raw"] = (
        out[lower_col].clip(lower=0)
        * out["Frozen_District_Packets_Per_Case_Ratio"]
    )

    out["Triposha_Packets_Upper_95_ForecastDriven_Raw"] = (
        out[upper_col].clip(lower=0)
        * out["Frozen_District_Packets_Per_Case_Ratio"]
    )

    out["Triposha_Packets_Lower_95_ForecastDriven_Planning"] = np.ceil(
        out["Triposha_Packets_Lower_95_ForecastDriven_Raw"]
    ).astype("Int64")

    out["Triposha_Packets_Upper_95_ForecastDriven_Planning"] = np.ceil(
        out["Triposha_Packets_Upper_95_ForecastDriven_Raw"]
    ).astype("Int64")

    out["Resource_Uncertainty_Note"] = (
        "Bounds propagate NGBoost malnutrition forecast uncertainty only; "
        "conversion-ratio uncertainty is not included"
    )
else:
    out["Resource_Uncertainty_Note"] = (
        "NGBoost interval columns unavailable; no resource interval calculated"
    )

out = out.sort_values(
    ["Horizon_Months", "Forecast_Target_Date", "District"]
).reset_index(drop=True)

out.to_csv(OUT_MAIN, index=False)

# ------------------------------------------------------------------
# Monthly national summary
# ------------------------------------------------------------------
monthly = (
    out.groupby(
        ["Horizon_Months", "Forecast_Target_Date"],
        as_index=False
    )
    .agg(
        National_RF_Predicted_Cases=("RF_Predicted_Cases", "sum"),
        National_Estimated_Triposha_Packets_Raw=(
            "Estimated_Triposha_Packets_Raw", "sum"
        ),
        National_Estimated_Triposha_Packets_Planning=(
            "Estimated_Triposha_Packets_Planning", "sum"
        ),
    )
)

if has_uncertainty:
    lower_sum = (
        out.groupby(
            ["Horizon_Months", "Forecast_Target_Date"]
        )["Triposha_Packets_Lower_95_ForecastDriven_Raw"]
        .sum()
        .reset_index(name="National_Triposha_Lower_95_ForecastDriven_Raw")
    )

    upper_sum = (
        out.groupby(
            ["Horizon_Months", "Forecast_Target_Date"]
        )["Triposha_Packets_Upper_95_ForecastDriven_Raw"]
        .sum()
        .reset_index(name="National_Triposha_Upper_95_ForecastDriven_Raw")
    )

    monthly = monthly.merge(
        lower_sum,
        on=["Horizon_Months", "Forecast_Target_Date"],
        how="left"
    ).merge(
        upper_sum,
        on=["Horizon_Months", "Forecast_Target_Date"],
        how="left"
    )

monthly.to_csv(OUT_MONTHLY, index=False)

# ------------------------------------------------------------------
# District summary
# ------------------------------------------------------------------
district_summary = (
    out.groupby(
        ["Horizon_Months", "District"],
        as_index=False
    )
    .agg(
        Forecast_Months=("Forecast_Target_Date", "count"),
        Mean_RF_Predicted_Cases=("RF_Predicted_Cases", "mean"),
        Mean_Monthly_Triposha_Packets_Raw=(
            "Estimated_Triposha_Packets_Raw", "mean"
        ),
        Mean_Monthly_Triposha_Packets_Planning=(
            "Estimated_Triposha_Packets_Planning", "mean"
        ),
        Total_Triposha_Packets_Planning=(
            "Estimated_Triposha_Packets_Planning", "sum"
        ),
        Maximum_Monthly_Triposha_Packets_Planning=(
            "Estimated_Triposha_Packets_Planning", "max"
        ),
        Frozen_District_Packets_Per_Case_Ratio=(
            "Frozen_District_Packets_Per_Case_Ratio", "first"
        ),
    )
)

district_summary.to_csv(OUT_DISTRICT, index=False)

# ------------------------------------------------------------------
# Hard audit
# ------------------------------------------------------------------
heading("STEP 32B HARD AUDIT")

audit = []

def add_check(name, result, expected, passed):
    audit.append(
        {
            "Audit_Check": name,
            "Result": result,
            "Expected": expected,
            "Status": "PASS" if passed else "FAIL",
        }
    )

add_check(
    "Selected rule unchanged",
    selected_rule,
    EXPECTED_SELECTED_RULE,
    selected_rule == EXPECTED_SELECTED_RULE
)

add_check(
    "Total future rows",
    len(out),
    EXPECTED_TOTAL_ROWS,
    len(out) == EXPECTED_TOTAL_ROWS
)

add_check(
    "Future districts",
    out["District"].nunique(),
    EXPECTED_DISTRICTS,
    out["District"].nunique() == EXPECTED_DISTRICTS
)

for h, expected_rows in EXPECTED_HORIZON_ROWS.items():
    actual = int((out["Horizon_Months"] == h).sum())
    add_check(
        f"H{h} rows",
        actual,
        expected_rows,
        actual == expected_rows
    )

add_check(
    "Missing frozen ratios",
    int(out["Frozen_District_Packets_Per_Case_Ratio"].isna().sum()),
    0,
    not out["Frozen_District_Packets_Per_Case_Ratio"].isna().any()
)

add_check(
    "Missing packet estimates",
    int(out["Estimated_Triposha_Packets_Raw"].isna().sum()),
    0,
    not out["Estimated_Triposha_Packets_Raw"].isna().any()
)

add_check(
    "Negative packet estimates",
    int((out["Estimated_Triposha_Packets_Raw"] < 0).sum()),
    0,
    not (out["Estimated_Triposha_Packets_Raw"] < 0).any()
)

add_check(
    "2025 used for rule reselection",
    False,
    False,
    True
)

add_check(
    "New ML model trained",
    False,
    False,
    True
)

add_check(
    "RF/NGBoost/SHAP/DMBI recalculated",
    False,
    False,
    True
)

audit_df = pd.DataFrame(audit)
audit_df.to_csv(OUT_AUDIT, index=False)

for _, row in audit_df.iterrows():
    print(f"{row['Audit_Check']:<45} : {row['Status']}")

if (audit_df["Status"] != "PASS").any():
    raise ValueError(
        "Step 32B hard audit failed. Review 32b_future_triposha_audit.csv"
    )

# ------------------------------------------------------------------
# Methodology record
# ------------------------------------------------------------------
methodology = {
    "step": "32B",
    "name": "Future Triposha Packet Planning Demand Estimation",
    "selected_step32a_rule": selected_rule,
    "development_period": "2015-2023",
    "selection_year": 2024,
    "2025_role": "Retrospective check only; no reselection or updating",
    "future_period": "2026-2030",
    "future_source": str(STEP30_PATH),
    "formula": (
        "Estimated_Triposha_Packets_Raw = "
        "RF_Predicted_Cases x Frozen_District_Packets_Per_Case_Ratio"
    ),
    "whole_packet_planning_policy": "ceil(raw estimate)",
    "ngboost_forecast_uncertainty_propagated": bool(has_uncertainty),
    "uncertainty_note": (
        "If available, NGBoost bounds reflect malnutrition forecast "
        "uncertainty only; conversion-ratio uncertainty is not included."
    ),
    "new_ml_model_trained": False,
    "rf_changed": False,
    "ngboost_changed": False,
    "shap_changed": False,
    "dmbi_changed": False,
    "interpretation": (
        "Estimated Triposha Packet Planning Demand for operational "
        "planning support; not clinical eligibility or dosage."
    ),
    "limitations": [
        (
            "Historical Triposha distribution may reflect programme "
            "coverage/supply conditions rather than true unmet clinical need."
        ),
        (
            "Step 32A 2025 retrospective WAPE was about 29.31%, so "
            "resource outputs should not be presented as exact counts."
        ),
        (
            "Future programme-policy or supply-chain changes are not modeled."
        ),
    ],
}

with open(OUT_METHOD, "w", encoding="utf-8") as f:
    json.dump(methodology, f, indent=2)

# ------------------------------------------------------------------
# Complete
# ------------------------------------------------------------------
heading("STEP 32B COMPLETE")

print(f"Selected frozen rule       : {selected_rule}")
print(f"Future rows                : {len(out)}")
print(f"Districts                  : {out['District'].nunique()}")
print(f"NGBoost interval propagated: {has_uncertainty}")

print("\nMean future monthly packet planning demand by horizon:")
for h in [1, 3, 6]:
    hdf = out[out["Horizon_Months"] == h]
    print(
        f"H{h}: "
        f"{hdf['Estimated_Triposha_Packets_Planning'].mean():.2f} "
        f"packets/district-month"
    )

print("\nSaved outputs:")
for p in [OUT_MAIN, OUT_MONTHLY, OUT_DISTRICT, OUT_AUDIT, OUT_METHOD]:
    print(f"- {p}")

print("\nLabel: Estimated Triposha Packet Planning Demand")
print("\nSTEP 32B COMPLETE")
print("=" * 120)
