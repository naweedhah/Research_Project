# ============================================================
# STEP 20 - FINAL FORECASTING STRATEGY FREEZE
# Childhood Malnutrition Forecasting Research
#
# Purpose:
# - Freeze the final H1/H3/H6 point-forecast strategy using
#   Step 17 untouched 2024 external-validation results.
# - Read the exact selected Random Forest parameters from
#   Step 16.
# - Keep NGBoost only as supplementary uncertainty support.
# - DO NOT load, inspect, train on, tune on, or evaluate 2025.
#
# Frozen selection rule:
# - Primary: lowest 2024 validation MAE.
# - Tie-breaker: lowest RMSE.
# ============================================================

from pathlib import Path
from datetime import datetime
import json

import pandas as pd


# ============================================================
# 1. SETTINGS
# ============================================================

HORIZONS = [1, 3, 6]

FINAL_POINT_MODEL = "Tuned Random Forest"
FINAL_POINT_MODEL_BASE_NAME = "Random Forest"
UNCERTAINTY_MODEL = "Tuned NGBoost"

EXPECTED_VALIDATION_ROWS = 300

SELECTION_RULE = (
    "Lowest 2024 external-validation MAE among the primary "
    "candidate models; RMSE is used only as a tie-breaker."
)


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "outputs" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STEP17_PRIMARY_PATH = (
    REPORT_DIR / "17_primary_candidate_2024_comparison.csv"
)

STEP16_PARAMS_PATH = (
    REPORT_DIR / "16_selected_hyperparameters.csv"
)

STEP17_NGBOOST_UNCERTAINTY_PATH = (
    REPORT_DIR / "17_tuned_ngboost_uncertainty_metrics.csv"
)

FREEZE_CSV_PATH = (
    REPORT_DIR / "20_final_forecasting_strategy.csv"
)

FREEZE_JSON_PATH = (
    REPORT_DIR / "20_final_forecasting_strategy.json"
)

FREEZE_AUDIT_PATH = (
    REPORT_DIR / "20_final_strategy_freeze_audit.txt"
)

SELECTED_METRICS_PATH = (
    REPORT_DIR / "20_selected_model_2024_validation_metrics.csv"
)


# ============================================================
# 3. START
# ============================================================

print("\n" + "=" * 120)
print("STEP 20 - FINAL FORECASTING STRATEGY FREEZE")
print("=" * 120)

print("\nRules:")
print("- Use Step 17 untouched 2024 validation evidence only")
print("- Primary selection metric: MAE")
print("- RMSE is only a tie-breaker")
print("- No training or tuning is performed here")
print("- 2025 data is NOT loaded")


# ============================================================
# 4. CHECK REQUIRED FILES
# ============================================================

for path in [STEP17_PRIMARY_PATH, STEP16_PARAMS_PATH]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )


# ============================================================
# 5. LOAD STEP 17 2024 VALIDATION RESULTS
# ============================================================

comparison_df = pd.read_csv(STEP17_PRIMARY_PATH)

required_columns = {
    "Horizon_Months",
    "Model",
    "Validation_Rows",
    "MAE",
    "RMSE",
    "WAPE_Percentage",
    "sMAPE_Percentage",
    "R2",
}

missing = required_columns - set(comparison_df.columns)

if missing:
    raise ValueError(
        "Step 17 comparison is missing columns: "
        f"{sorted(missing)}"
    )


# ============================================================
# 6. VERIFY FINAL MODEL USING THE PREDEFINED RULE
# ============================================================

verification_rows = []

for horizon in HORIZONS:
    horizon_df = (
        comparison_df[
            comparison_df["Horizon_Months"] == horizon
        ]
        .copy()
        .sort_values(
            ["MAE", "RMSE"],
            ascending=[True, True],
        )
        .reset_index(drop=True)
    )

    if horizon_df.empty:
        raise ValueError(
            f"No Step 17 results found for H{horizon}."
        )

    selected_model_by_rule = str(
        horizon_df.iloc[0]["Model"]
    )

    if selected_model_by_rule != FINAL_POINT_MODEL:
        raise AssertionError(
            f"H{horizon}: the predefined rule selects "
            f"'{selected_model_by_rule}', not "
            f"'{FINAL_POINT_MODEL}'. Stop before opening 2025."
        )

    selected_row = horizon_df.iloc[0]

    if int(selected_row["Validation_Rows"]) != EXPECTED_VALIDATION_ROWS:
        raise AssertionError(
            f"H{horizon}: expected {EXPECTED_VALIDATION_ROWS} "
            f"validation rows, found "
            f"{int(selected_row['Validation_Rows'])}."
        )

    verification_rows.append({
        "Horizon_Months": horizon,
        "Rule_Selected_Model": selected_model_by_rule,
        "MAE": float(selected_row["MAE"]),
        "RMSE": float(selected_row["RMSE"]),
        "Verification": "PASS",
    })

verification_df = pd.DataFrame(verification_rows)


# ============================================================
# 7. LOAD STEP 16 SELECTED HYPERPARAMETERS
# ============================================================

params_df = pd.read_csv(STEP16_PARAMS_PATH)

for column in ["Model", "Horizon_Months", "Selected_Parameters"]:
    if column not in params_df.columns:
        raise ValueError(
            f"Step 16 parameter file is missing column: {column}"
        )


def get_selected_parameters(model_name, horizon):
    row = params_df[
        (params_df["Model"] == model_name)
        &
        (params_df["Horizon_Months"] == horizon)
    ]

    if len(row) != 1:
        raise ValueError(
            f"Expected one Step 16 parameter row for "
            f"{model_name} H{horizon}; found {len(row)}."
        )

    return json.loads(
        row.iloc[0]["Selected_Parameters"]
    )


# ============================================================
# 8. BUILD FROZEN H1/H3/H6 STRATEGY
# ============================================================

freeze_rows = []
json_horizons = {}

for horizon in HORIZONS:
    validation_row = comparison_df[
        (comparison_df["Horizon_Months"] == horizon)
        &
        (comparison_df["Model"] == FINAL_POINT_MODEL)
    ]

    if len(validation_row) != 1:
        raise ValueError(
            f"Expected one {FINAL_POINT_MODEL} row for H{horizon}."
        )

    validation_row = validation_row.iloc[0]

    parameters = get_selected_parameters(
        FINAL_POINT_MODEL_BASE_NAME,
        horizon,
    )

    config_id = parameters.get("Config_ID", "UNKNOWN")

    freeze_rows.append({
        "Horizon_Months": horizon,
        "Final_Model": FINAL_POINT_MODEL,
        "Base_Model": FINAL_POINT_MODEL_BASE_NAME,
        "Config_ID": config_id,
        "Selection_Rule": SELECTION_RULE,
        "Validation_Rows_2024": int(validation_row["Validation_Rows"]),
        "Validation_MAE_2024": float(validation_row["MAE"]),
        "Validation_RMSE_2024": float(validation_row["RMSE"]),
        "Validation_WAPE_2024": float(validation_row["WAPE_Percentage"]),
        "Validation_sMAPE_2024": float(validation_row["sMAPE_Percentage"]),
        "Validation_R2_2024": float(validation_row["R2"]),
        "Selected_Parameters": json.dumps(parameters, sort_keys=True),
        "Frozen": True,
        "Final_Test_Year": 2025,
        "2025_Used_For_Selection": False,
    })

    json_horizons[f"H{horizon}"] = {
        "horizon_months": horizon,
        "model": FINAL_POINT_MODEL,
        "base_model": FINAL_POINT_MODEL_BASE_NAME,
        "config_id": config_id,
        "parameters": parameters,
        "validation_2024": {
            "rows": int(validation_row["Validation_Rows"]),
            "mae": float(validation_row["MAE"]),
            "rmse": float(validation_row["RMSE"]),
            "wape_percentage": float(validation_row["WAPE_Percentage"]),
            "smape_percentage": float(validation_row["sMAPE_Percentage"]),
            "r2": float(validation_row["R2"]),
        },
    }

freeze_df = pd.DataFrame(freeze_rows)


# ============================================================
# 9. SUPPLEMENTARY NGBOOST UNCERTAINTY STRATEGY
# ============================================================

uncertainty_strategy = {
    "enabled": False,
    "model": UNCERTAINTY_MODEL,
    "role": (
        "Supplementary uncertainty model only; it is not the "
        "primary point-forecast model."
    ),
    "horizons": {},
}

if STEP17_NGBOOST_UNCERTAINTY_PATH.exists():
    uncertainty_df = pd.read_csv(
        STEP17_NGBOOST_UNCERTAINTY_PATH
    )

    uncertainty_strategy["enabled"] = True

    for horizon in HORIZONS:
        row = uncertainty_df[
            uncertainty_df["Horizon_Months"] == horizon
        ]

        if len(row) != 1:
            continue

        row = row.iloc[0]
        coverage = float(row["Observed_Coverage_Percentage"])

        if coverage < 90.0:
            note = (
                "Observed coverage is below 90%; treat the "
                "95% interval as under-calibrated supplementary "
                "uncertainty information."
            )
        elif coverage < 93.0:
            note = (
                "Observed coverage is moderately below 95%; "
                "retain only as supplementary uncertainty information."
            )
        else:
            note = (
                "Observed coverage is close to the nominal 95%; "
                "retain as supplementary uncertainty information."
            )

        ngb_params = get_selected_parameters(
            "NGBoost",
            horizon,
        )

        uncertainty_strategy["horizons"][f"H{horizon}"] = {
            "config_id": ngb_params.get("Config_ID", "UNKNOWN"),
            "parameters": ngb_params,
            "nominal_coverage_percentage": float(
                row["Nominal_Coverage_Percentage"]
            ),
            "observed_coverage_percentage": coverage,
            "mean_interval_width": float(row["Mean_Interval_Width"]),
            "negative_lower_bounds": int(row["Negative_Lower_Bounds"]),
            "calibration_note": note,
        }


# ============================================================
# 10. SAVE CSV + JSON + AUDIT RECORD
# ============================================================

freeze_timestamp = (
    datetime.now()
    .astimezone()
    .isoformat(timespec="seconds")
)

freeze_json = {
    "step": 20,
    "title": "Final Forecasting Strategy Freeze",
    "status": "FROZEN",
    "freeze_timestamp": freeze_timestamp,
    "selection_basis": (
        "Step 17 untouched 2024 external validation."
    ),
    "selection_rule": SELECTION_RULE,
    "point_forecast_strategy": json_horizons,
    "uncertainty_strategy": uncertainty_strategy,
    "final_test_policy": {
        "year": 2025,
        "used_for_tuning": False,
        "used_for_model_selection": False,
        "rule": (
            "Do not change the frozen model family or "
            "hyperparameters after viewing 2025 results."
        ),
    },
}

freeze_df.to_csv(
    FREEZE_CSV_PATH,
    index=False,
)

with open(
    FREEZE_JSON_PATH,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        freeze_json,
        file,
        indent=2,
        ensure_ascii=False,
    )

selected_metrics_df = (
    comparison_df[
        comparison_df["Model"] == FINAL_POINT_MODEL
    ]
    .copy()
    .sort_values("Horizon_Months")
    .reset_index(drop=True)
)

selected_metrics_df.to_csv(
    SELECTED_METRICS_PATH,
    index=False,
)


# ============================================================
# 11. WRITE HUMAN-READABLE AUDIT FILE
# ============================================================

audit_lines = [
    "STEP 20 - FINAL FORECASTING STRATEGY FREEZE",
    "=" * 72,
    f"Freeze timestamp: {freeze_timestamp}",
    "",
    "Selection basis:",
    "- Step 17 untouched 2024 external validation",
    "- Primary metric: MAE",
    "- RMSE used only as a tie-breaker",
    "- 2025 was not used for tuning or model selection",
    "",
    "Frozen point-forecast strategy:",
]

for _, row in freeze_df.sort_values("Horizon_Months").iterrows():
    audit_lines.append(
        f"- H{int(row['Horizon_Months'])}: "
        f"{row['Final_Model']} ({row['Config_ID']}) | "
        f"MAE={row['Validation_MAE_2024']:.4f}, "
        f"RMSE={row['Validation_RMSE_2024']:.4f}, "
        f"WAPE={row['Validation_WAPE_2024']:.4f}%"
    )


audit_lines.extend([
    "",
    "Selection-rule verification:",
])

for _, row in verification_df.iterrows():
    audit_lines.append(
        f"- H{int(row['Horizon_Months'])}: "
        f"{row['Rule_Selected_Model']} | {row['Verification']}"
    )


audit_lines.extend([
    "",
    "Uncertainty support:",
])

if uncertainty_strategy["enabled"]:
    audit_lines.append(
        "- Tuned NGBoost retained only as supplementary "
        "probabilistic support."
    )

    for horizon_key, details in uncertainty_strategy["horizons"].items():
        audit_lines.append(
            f"- {horizon_key}: coverage="
            f"{details['observed_coverage_percentage']:.4f}% | "
            f"mean interval width="
            f"{details['mean_interval_width']:.4f}"
        )
        audit_lines.append(
            "  " + details["calibration_note"]
        )
else:
    audit_lines.append(
        "- NGBoost uncertainty report was not available."
    )


audit_lines.extend([
    "",
    "LOCKBOX RULE:",
    (
        "The 2025 final test may now be opened only with this "
        "frozen strategy. Do not change the selected model family "
        "or hyperparameters after seeing 2025 performance."
    ),
])

with open(
    FREEZE_AUDIT_PATH,
    "w",
    encoding="utf-8",
) as file:
    file.write("\n".join(audit_lines))


# ============================================================
# 12. PRINT RESULTS
# ============================================================

print("\n" + "=" * 120)
print("FROZEN POINT-FORECAST STRATEGY")
print("=" * 120)

print(
    freeze_df[
        [
            "Horizon_Months",
            "Final_Model",
            "Config_ID",
            "Validation_MAE_2024",
            "Validation_RMSE_2024",
            "Validation_WAPE_2024",
            "Validation_R2_2024",
        ]
    ]
    .round(4)
    .to_string(index=False)
)

print("\n" + "=" * 120)
print("SELECTION-RULE VERIFICATION")
print("=" * 120)

print(
    verification_df
    .round(4)
    .to_string(index=False)
)

print("\n" + "=" * 120)
print("STEP 20 SUMMARY")
print("=" * 120)

print("- Final point-forecast family: Tuned Random Forest")
print("- H1/H3/H6 use their Step 16 selected RF parameters")
print("- NGBoost is supplementary uncertainty support only")
print("- No model training or tuning was performed")
print("- 2025 data was NOT loaded")

print("\nFreeze files saved to:")
print(FREEZE_CSV_PATH)
print(FREEZE_JSON_PATH)
print(FREEZE_AUDIT_PATH)
print(SELECTED_METRICS_PATH)

print("\nNEXT STEP:")
print("STEP 21 - FINAL 2025 LOCKBOX TEST")
print("Use only the strategy frozen by Step 20.")

print("\nSTEP 20 - FINAL FORECASTING STRATEGY FREEZE COMPLETE")
print("=" * 120)
