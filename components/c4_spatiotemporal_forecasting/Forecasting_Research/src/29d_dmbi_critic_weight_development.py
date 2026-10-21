# ============================================================
# STEP 29D - DMBI CRITIC OBJECTIVE WEIGHT DEVELOPMENT
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Develop and freeze objective DMBI criterion weights using
# 2024 development data ONLY.
#
# INPUT FROM STEP 29C
# -------------------
# outputs/reports/29c_2024_dmbi_criteria_development.csv
#
# FINAL DMBI CRITERIA
# -------------------
# C1. Forecasted Malnutrition Cases
# C2. Forecasted Cases per 1,000 Under-5 Population
# C3. Forecasted Year-on-Year Burden Growth (%)
#
# IMPORTANT METHODOLOGY RULES
# ---------------------------
# 1. 2024 ONLY is used to develop CRITIC weights.
# 2. 2025 validation data is NOT loaded.
# 3. 2026-2030 future data is NOT loaded.
# 4. No manual criterion weights are supplied.
# 5. No target / actual malnutrition outcome is used to tune weights.
# 6. All three criteria are benefit-type priority criteria:
#       higher value -> higher planning priority.
# 7. Criteria are min-max normalized WITHIN each
#    Forecast_Target_Date x Horizon_Months decision matrix.
#    This preserves the fact that TOPSIS will later compare the
#    25 districts within the same month and horizon.
# 8. The normalized 2024 matrices are concatenated, and one common
#    CRITIC weight vector is estimated and frozen for H1/H3/H6.
# 9. Horizon-specific CRITIC weights are produced only as diagnostics;
#    they are NOT the frozen operational weights.
# 10. This step does NOT run TOPSIS.
#
# CRITIC FORMULA
# --------------
# For each criterion j:
#   Contrast_j = standard deviation of normalized criterion j
#   Conflict_j = sum_k (1 - corr(j, k))
#   Information_j = Contrast_j * Conflict_j
#   Weight_j = Information_j / sum(Information)
#
# NEXT STEP
# ---------
# Step 29E will use these frozen 2024 CRITIC weights to perform
# TOPSIS on 2025 retrospective validation criteria.
# ============================================================

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")


# ============================================================
# 1. SETTINGS
# ============================================================

DISTRICT_COL = "District"
TARGET_DATE_COL = "Forecast_Target_Date"
HORIZON_COL = "Horizon_Months"

EXPECTED_DISTRICTS = 25
EXPECTED_HORIZONS = [1, 3, 6]
EXPECTED_2024_ROWS = 900
EXPECTED_GROUPS = 36  # 12 months x 3 horizons

CRITERIA = [
    "C1_Forecasted_Malnutrition_Cases",
    "C2_Forecasted_Cases_per_1000_U5",
    "C3_Forecasted_YoY_Burden_Growth_Percent",
]

CRITERION_LABELS = {
    "C1_Forecasted_Malnutrition_Cases":
        "Forecasted Malnutrition Cases",
    "C2_Forecasted_Cases_per_1000_U5":
        "Forecasted Cases per 1,000 Under-5",
    "C3_Forecasted_YoY_Burden_Growth_Percent":
        "Forecasted Year-on-Year Burden Growth (%)",
}

# All three are priority/benefit criteria.
# No manual weight is present anywhere in this script.
CRITERION_DIRECTION = {
    criterion: "benefit"
    for criterion in CRITERIA
}

NORMALIZATION_EPS = 1e-12
WEIGHT_SUM_TOLERANCE = 1e-10


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

REPORT_DIR = BASE_DIR / "outputs" / "reports"
FIGURE_DIR = BASE_DIR / "outputs" / "figures"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

INPUT_2024 = (
    REPORT_DIR
    / "29c_2024_dmbi_criteria_development.csv"
)

OUT_NORMALIZED = (
    REPORT_DIR
    / "29d_critic_normalized_2024_criteria.csv"
)

OUT_GROUP_AUDIT = (
    REPORT_DIR
    / "29d_critic_2024_group_normalization_audit.csv"
)

OUT_CORRELATION = (
    REPORT_DIR
    / "29d_critic_correlation_matrix_2024.csv"
)

OUT_INFORMATION = (
    REPORT_DIR
    / "29d_critic_information_content_2024.csv"
)

OUT_WEIGHTS = (
    REPORT_DIR
    / "29d_frozen_critic_weights_from_2024.csv"
)

OUT_HORIZON_DIAGNOSTIC = (
    REPORT_DIR
    / "29d_critic_weights_by_horizon_diagnostic.csv"
)

OUT_AUDIT = (
    REPORT_DIR
    / "29d_dmbi_critic_audit.csv"
)

OUT_METHOD = (
    REPORT_DIR
    / "29d_dmbi_critic_methodology.json"
)

FIGURE_PATH = (
    FIGURE_DIR
    / "29d_frozen_critic_weights_2024.png"
)


# ============================================================
# 3. DISPLAY HELPERS
# ============================================================

def header(title, width=120):
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def subheader(title, width=120):
    print("\n" + "-" * width)
    print(title)
    print("-" * width)


# ============================================================
# 4. CORE HELPERS
# ============================================================

def validate_group_structure(dataframe, label):
    counts = (
        dataframe
        .groupby(
            [TARGET_DATE_COL, HORIZON_COL]
        )[DISTRICT_COL]
        .nunique()
    )

    if len(counts) != EXPECTED_GROUPS:
        raise ValueError(
            f"{label}: expected {EXPECTED_GROUPS} month/horizon groups, "
            f"found {len(counts)}."
        )

    if not (counts == EXPECTED_DISTRICTS).all():
        bad = counts[counts != EXPECTED_DISTRICTS]
        raise ValueError(
            f"{label}: every decision matrix must contain "
            f"{EXPECTED_DISTRICTS} districts. Bad groups:\n{bad}"
        )


def minmax_normalize_group(group):
    """
    Normalize the three benefit criteria to [0, 1] within one
    target-month x horizon decision matrix.

    Constant criterion within a group receives 0.5 for all districts,
    reflecting no within-group discriminatory power.
    """
    out = group.copy()
    audit_rows = []

    for criterion in CRITERIA:
        values = pd.to_numeric(
            out[criterion],
            errors="coerce",
        ).astype(float)

        minimum = float(values.min())
        maximum = float(values.max())
        span = maximum - minimum

        normalized_col = f"N_{criterion}"

        if abs(span) <= NORMALIZATION_EPS:
            out[normalized_col] = 0.5
            constant = True
        else:
            out[normalized_col] = (
                (values - minimum)
                / span
            )
            constant = False

        audit_rows.append({
            TARGET_DATE_COL:
                pd.Timestamp(group[TARGET_DATE_COL].iloc[0]),
            HORIZON_COL:
                int(group[HORIZON_COL].iloc[0]),
            "Criterion":
                criterion,
            "Minimum":
                minimum,
            "Maximum":
                maximum,
            "Range":
                span,
            "Constant_Within_Group":
                constant,
        })

    return out, audit_rows


def compute_critic(normalized_dataframe, scope_label):
    """
    Compute CRITIC objective weights from already-normalized data.
    """
    normalized_cols = [
        f"N_{criterion}"
        for criterion in CRITERIA
    ]

    matrix = (
        normalized_dataframe[normalized_cols]
        .apply(pd.to_numeric, errors="coerce")
        .astype(float)
    )

    if matrix.isna().any().any():
        raise ValueError(
            f"{scope_label}: missing values found in normalized CRITIC matrix."
        )

    # Population standard deviation is used consistently for the
    # full 2024 development matrix.
    contrast = matrix.std(ddof=0)

    # CRITIC convention uses the Pearson correlation matrix.
    correlation = matrix.corr(method="pearson")

    if correlation.isna().any().any():
        raise ValueError(
            f"{scope_label}: CRITIC correlation matrix contains NaN."
        )

    conflict = pd.Series(index=normalized_cols, dtype=float)
    information = pd.Series(index=normalized_cols, dtype=float)

    for criterion_col in normalized_cols:
        conflict_value = float(
            (1.0 - correlation.loc[criterion_col]).sum()
        )

        conflict.loc[criterion_col] = conflict_value
        information.loc[criterion_col] = (
            float(contrast.loc[criterion_col])
            * conflict_value
        )

    information_sum = float(information.sum())

    if information_sum <= 0:
        raise ValueError(
            f"{scope_label}: total CRITIC information content is not positive."
        )

    weights = information / information_sum

    rows = []

    for criterion in CRITERIA:
        normalized_col = f"N_{criterion}"

        rows.append({
            "Scope":
                scope_label,
            "Criterion":
                criterion,
            "Criterion_Label":
                CRITERION_LABELS[criterion],
            "Direction":
                CRITERION_DIRECTION[criterion],
            "Contrast_SD":
                float(contrast.loc[normalized_col]),
            "Conflict_Sum_1_minus_r":
                float(conflict.loc[normalized_col]),
            "Information_Content":
                float(information.loc[normalized_col]),
            "CRITIC_Weight":
                float(weights.loc[normalized_col]),
        })

    info_df = pd.DataFrame(rows)

    # Return correlation matrix with original criterion names for clarity.
    renamed_corr = correlation.copy()
    renamed_corr.index = CRITERIA
    renamed_corr.columns = CRITERIA

    return info_df, renamed_corr


# ============================================================
# 5. START
# ============================================================

header(
    "STEP 29D - DMBI CRITIC OBJECTIVE WEIGHT DEVELOPMENT"
)

print("\nRules:")
print("- 2024 development criteria ONLY")
print("- 2025 validation data is NOT loaded")
print("- 2026-2030 future data is NOT loaded")
print("- No manual DMBI weights")
print("- One common frozen CRITIC weight vector for H1/H3/H6")
print("- TOPSIS is NOT executed in this step")


# ============================================================
# 6. LOAD 2024 DEVELOPMENT CRITERIA
# ============================================================

if not INPUT_2024.exists():
    raise FileNotFoundError(
        "Required Step 29C output not found:\n"
        f"{INPUT_2024}"
    )

header("LOAD STEP 29C 2024 DEVELOPMENT CRITERIA")

data = pd.read_csv(INPUT_2024)

data.columns = [
    str(column).strip()
    for column in data.columns
]

required_columns = {
    DISTRICT_COL,
    TARGET_DATE_COL,
    HORIZON_COL,
    *CRITERIA,
}

missing_columns = (
    required_columns
    - set(data.columns)
)

if missing_columns:
    raise ValueError(
        "Step 29C 2024 criteria file is missing columns: "
        f"{sorted(missing_columns)}"
    )

data[TARGET_DATE_COL] = pd.to_datetime(
    data[TARGET_DATE_COL],
    errors="coerce",
)

data[HORIZON_COL] = pd.to_numeric(
    data[HORIZON_COL],
    errors="coerce",
).astype("Int64")

for criterion in CRITERIA:
    data[criterion] = pd.to_numeric(
        data[criterion],
        errors="coerce",
    )

if len(data) != EXPECTED_2024_ROWS:
    raise ValueError(
        f"Expected {EXPECTED_2024_ROWS} 2024 criteria rows, "
        f"found {len(data)}."
    )

if data[
    [TARGET_DATE_COL, HORIZON_COL, *CRITERIA]
].isna().any().any():
    raise ValueError(
        "Missing/invalid required values detected in 2024 criteria."
    )

if set(data[HORIZON_COL].astype(int).unique()) != set(EXPECTED_HORIZONS):
    raise ValueError(
        "Expected horizons H1, H3 and H6 only."
    )

if not (
    data[TARGET_DATE_COL].dt.year == 2024
).all():
    raise ValueError(
        "Step 29D input contains target dates outside 2024."
    )

validate_group_structure(
    data,
    "2024 development",
)

print(f"Rows             : {len(data)} [PASS]")
print(f"Districts        : {data[DISTRICT_COL].nunique()} [PASS]")
print(f"Decision matrices: {EXPECTED_GROUPS} [PASS]")
print("Target year      : 2024 only [PASS]")


# ============================================================
# 7. WITHIN-MONTH/HORIZON MIN-MAX NORMALIZATION
# ============================================================

header(
    "NORMALIZE CRITERIA WITHIN EACH TARGET-MONTH x HORIZON MATRIX"
)

normalized_parts = []
group_audit_records = []

for (target_date, horizon), group in data.groupby(
    [TARGET_DATE_COL, HORIZON_COL],
    sort=True,
):
    normalized_group, audit_rows = minmax_normalize_group(
        group
    )

    normalized_parts.append(normalized_group)
    group_audit_records.extend(audit_rows)

normalized = (
    pd.concat(
        normalized_parts,
        ignore_index=True,
    )
    .sort_values(
        [TARGET_DATE_COL, HORIZON_COL, DISTRICT_COL]
    )
    .reset_index(drop=True)
)

group_audit_df = pd.DataFrame(
    group_audit_records
)

normalized_columns = [
    f"N_{criterion}"
    for criterion in CRITERIA
]

if normalized[normalized_columns].isna().any().any():
    raise ValueError(
        "Normalization produced missing values."
    )

normalized_min = float(
    normalized[normalized_columns].min().min()
)

normalized_max = float(
    normalized[normalized_columns].max().max()
)

if (
    normalized_min < -NORMALIZATION_EPS
    or
    normalized_max > 1.0 + NORMALIZATION_EPS
):
    raise ValueError(
        "Normalized values are outside [0, 1]."
    )

constant_group_count = int(
    group_audit_df[
        "Constant_Within_Group"
    ].sum()
)

normalized.to_csv(
    OUT_NORMALIZED,
    index=False,
)

group_audit_df.to_csv(
    OUT_GROUP_AUDIT,
    index=False,
)

print(f"Normalized rows            : {len(normalized)} [PASS]")
print(f"Normalized range           : {normalized_min:.6f} to {normalized_max:.6f} [PASS]")
print(f"Constant criterion-groups  : {constant_group_count}")


# ============================================================
# 8. GLOBAL CRITIC WEIGHTS - FROZEN OPERATIONAL WEIGHTS
# ============================================================

header(
    "CALCULATE GLOBAL 2024 CRITIC WEIGHTS"
)

information_df, correlation_df = compute_critic(
    normalized,
    "GLOBAL_2024_ALL_HORIZONS",
)

weight_sum = float(
    information_df["CRITIC_Weight"].sum()
)

if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
    raise ValueError(
        f"CRITIC weights do not sum to 1. Sum={weight_sum}"
    )

if (
    information_df["CRITIC_Weight"] <= 0
).any():
    raise ValueError(
        "All frozen CRITIC weights must be positive."
    )

information_df.to_csv(
    OUT_INFORMATION,
    index=False,
)

correlation_df.to_csv(
    OUT_CORRELATION,
    index=True,
)

frozen_weights_df = information_df[
    [
        "Criterion",
        "Criterion_Label",
        "Direction",
        "CRITIC_Weight",
    ]
].copy()

frozen_weights_df["Weight_Source"] = (
    "2024 development only"
)

frozen_weights_df["Frozen_For_2025_Validation"] = True
frozen_weights_df["Frozen_For_2026_2030_Application"] = True

frozen_weights_df.to_csv(
    OUT_WEIGHTS,
    index=False,
)

print("\nFROZEN CRITIC WEIGHTS:")
print(
    frozen_weights_df[
        [
            "Criterion_Label",
            "CRITIC_Weight",
        ]
    ]
    .round(6)
    .to_string(index=False)
)

print(f"\nWeight sum: {weight_sum:.12f} [PASS]")


# ============================================================
# 9. HORIZON-SPECIFIC DIAGNOSTICS ONLY
# ============================================================

header(
    "HORIZON-SPECIFIC CRITIC DIAGNOSTICS (NOT FROZEN WEIGHTS)"
)

diagnostic_rows = []

for horizon in EXPECTED_HORIZONS:
    subset = normalized[
        normalized[HORIZON_COL].astype(int) == horizon
    ].copy()

    diagnostic_info, _ = compute_critic(
        subset,
        f"H{horizon}_2024_DIAGNOSTIC",
    )

    for _, row in diagnostic_info.iterrows():
        diagnostic_rows.append({
            "Horizon_Months":
                horizon,
            "Criterion":
                row["Criterion"],
            "Criterion_Label":
                row["Criterion_Label"],
            "Diagnostic_CRITIC_Weight":
                row["CRITIC_Weight"],
            "Operational_Use":
                "Diagnostic only - NOT frozen operational weight",
        })

horizon_diagnostic_df = pd.DataFrame(
    diagnostic_rows
)

horizon_diagnostic_df.to_csv(
    OUT_HORIZON_DIAGNOSTIC,
    index=False,
)

pivot_diag = horizon_diagnostic_df.pivot(
    index="Criterion_Label",
    columns="Horizon_Months",
    values="Diagnostic_CRITIC_Weight",
)

print(
    pivot_diag.round(6).to_string()
)


# ============================================================
# 10. HARD AUDIT
# ============================================================

header("STEP 29D HARD AUDIT")

manual_weight_present = False
loaded_2025 = False
loaded_future = False
actual_outcome_used_for_weighting = False

all_weights_positive = bool(
    (frozen_weights_df["CRITIC_Weight"] > 0).all()
)

all_weights_below_one = bool(
    (frozen_weights_df["CRITIC_Weight"] < 1).all()
)

all_directions_benefit = bool(
    (
        frozen_weights_df["Direction"]
        == "benefit"
    ).all()
)

audit_rows = [
    {
        "Audit_Check": "Input rows",
        "Result": len(data),
        "Expected": EXPECTED_2024_ROWS,
        "Status": "PASS" if len(data) == EXPECTED_2024_ROWS else "FAIL",
    },
    {
        "Audit_Check": "Input target year",
        "Result": "2024 only",
        "Expected": "2024 only",
        "Status": "PASS",
    },
    {
        "Audit_Check": "Decision matrices",
        "Result": EXPECTED_GROUPS,
        "Expected": EXPECTED_GROUPS,
        "Status": "PASS",
    },
    {
        "Audit_Check": "Districts per decision matrix",
        "Result": EXPECTED_DISTRICTS,
        "Expected": EXPECTED_DISTRICTS,
        "Status": "PASS",
    },
    {
        "Audit_Check": "Manual criterion weights supplied",
        "Result": manual_weight_present,
        "Expected": False,
        "Status": "PASS" if not manual_weight_present else "FAIL",
    },
    {
        "Audit_Check": "2025 validation data loaded",
        "Result": loaded_2025,
        "Expected": False,
        "Status": "PASS" if not loaded_2025 else "FAIL",
    },
    {
        "Audit_Check": "2026-2030 future data loaded",
        "Result": loaded_future,
        "Expected": False,
        "Status": "PASS" if not loaded_future else "FAIL",
    },
    {
        "Audit_Check": "Actual outcome used to tune CRITIC weights",
        "Result": actual_outcome_used_for_weighting,
        "Expected": False,
        "Status": "PASS" if not actual_outcome_used_for_weighting else "FAIL",
    },
    {
        "Audit_Check": "Normalized values inside [0,1]",
        "Result": f"{normalized_min:.6f} to {normalized_max:.6f}",
        "Expected": "0 to 1",
        "Status": "PASS",
    },
    {
        "Audit_Check": "Frozen weight count",
        "Result": len(frozen_weights_df),
        "Expected": 3,
        "Status": "PASS" if len(frozen_weights_df) == 3 else "FAIL",
    },
    {
        "Audit_Check": "Frozen weights sum to 1",
        "Result": weight_sum,
        "Expected": 1.0,
        "Status": "PASS" if abs(weight_sum - 1.0) <= WEIGHT_SUM_TOLERANCE else "FAIL",
    },
    {
        "Audit_Check": "All frozen weights positive",
        "Result": all_weights_positive,
        "Expected": True,
        "Status": "PASS" if all_weights_positive else "FAIL",
    },
    {
        "Audit_Check": "All frozen weights below 1",
        "Result": all_weights_below_one,
        "Expected": True,
        "Status": "PASS" if all_weights_below_one else "FAIL",
    },
    {
        "Audit_Check": "All criteria are benefit-type",
        "Result": all_directions_benefit,
        "Expected": True,
        "Status": "PASS" if all_directions_benefit else "FAIL",
    },
    {
        "Audit_Check": "TOPSIS executed in Step 29D",
        "Result": False,
        "Expected": False,
        "Status": "PASS",
    },
]

audit_df = pd.DataFrame(audit_rows)

audit_df.to_csv(
    OUT_AUDIT,
    index=False,
)

for _, row in audit_df.iterrows():
    print(
        f"{row['Audit_Check']:<55} : {row['Status']}"
    )

if (audit_df["Status"] != "PASS").any():
    raise ValueError(
        "Step 29D hard audit failed. Review audit output."
    )


# ============================================================
# 11. METHODOLOGY RECORD
# ============================================================

methodology = {
    "step": "29D",
    "name": "DMBI CRITIC Objective Weight Development",
    "development_period": "2024 only",
    "input_file": str(INPUT_2024),
    "criteria": [
        {
            "name": criterion,
            "label": CRITERION_LABELS[criterion],
            "direction": CRITERION_DIRECTION[criterion],
        }
        for criterion in CRITERIA
    ],
    "normalization": {
        "method": "Min-max normalization to [0,1]",
        "scope": (
            "Within each Forecast_Target_Date x Horizon_Months "
            "decision matrix of 25 districts"
        ),
        "constant_group_rule": (
            "If a criterion is constant within one decision matrix, "
            "all districts receive normalized value 0.5 for that criterion."
        ),
    },
    "critic": {
        "contrast": "Population standard deviation of normalized criterion",
        "correlation": "Pearson correlation",
        "conflict": "Sum_k(1 - correlation_jk)",
        "information_content": "contrast_j * conflict_j",
        "weight": "information_j / sum(information)",
    },
    "operational_weight_design": (
        "One common CRITIC weight vector is estimated from all normalized "
        "2024 month/horizon decision matrices and frozen for H1/H3/H6."
    ),
    "horizon_specific_weights": (
        "Calculated for diagnostic comparison only and not used operationally."
    ),
    "manual_weights_used": False,
    "2025_loaded": False,
    "future_2026_2030_loaded": False,
    "actual_outcome_used_for_weighting": False,
    "frozen_weights": {
        row["Criterion"]: float(row["CRITIC_Weight"])
        for _, row in frozen_weights_df.iterrows()
    },
    "next_step": (
        "Step 29E: apply the frozen 2024 CRITIC weights in TOPSIS "
        "to 2025 retrospective validation criteria."
    ),
    "interpretation": (
        "CRITIC weights measure objective information contrast and conflict "
        "among the three DMBI planning criteria. They are not causal-effect "
        "weights and are not clinical importance scores."
    ),
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
# 12. FIGURE
# ============================================================

plot_df = frozen_weights_df.copy()

fig, ax = plt.subplots(figsize=(10, 6))

ax.bar(
    plot_df["Criterion_Label"],
    plot_df["CRITIC_Weight"],
)

ax.set_title(
    "Frozen DMBI CRITIC Weights Developed from 2024"
)

ax.set_xlabel("DMBI criterion")
ax.set_ylabel("CRITIC weight")
ax.tick_params(axis="x", rotation=20)

fig.tight_layout()

fig.savefig(
    FIGURE_PATH,
    dpi=300,
    bbox_inches="tight",
)

plt.close(fig)


# ============================================================
# 13. FINAL SUMMARY
# ============================================================

header("STEP 29D COMPLETE")

print("\nFrozen 2024 CRITIC weights:")

for _, row in frozen_weights_df.iterrows():
    print(
        f"- {row['Criterion_Label']}: "
        f"{row['CRITIC_Weight']:.6f}"
    )

print(f"\nWeight sum: {weight_sum:.12f}")

print("\nInterpretation:")
print("- Weights were learned objectively from 2024 criterion structure")
print("- No 2025 information was used")
print("- No future 2026-2030 information was used")
print("- These weights are now frozen")
print("- They are NOT causal or clinical importance weights")

print("\nSaved:")
print(f"- Normalized 2024 criteria      : {OUT_NORMALIZED}")
print(f"- Normalization audit           : {OUT_GROUP_AUDIT}")
print(f"- CRITIC correlation matrix     : {OUT_CORRELATION}")
print(f"- CRITIC information content    : {OUT_INFORMATION}")
print(f"- FROZEN CRITIC weights         : {OUT_WEIGHTS}")
print(f"- Horizon diagnostic weights    : {OUT_HORIZON_DIAGNOSTIC}")
print(f"- Audit                         : {OUT_AUDIT}")
print(f"- Methodology                   : {OUT_METHOD}")
print(f"- Figure                        : {FIGURE_PATH}")

print("\nNEXT:")
print(
    "Send the FULL terminal output before Step 29E TOPSIS 2025 validation."
)

print(
    "\nSTEP 29D - DMBI CRITIC OBJECTIVE WEIGHT DEVELOPMENT COMPLETE"
)
print("=" * 120)
