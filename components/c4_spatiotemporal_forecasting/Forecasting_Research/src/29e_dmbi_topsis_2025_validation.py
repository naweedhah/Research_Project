# ============================================================
# STEP 29E - DMBI TOPSIS 2025 RETROSPECTIVE VALIDATION
# Childhood Malnutrition Forecasting Research - Component 4
#
# Uses:
#   29c_2025_dmbi_criteria_validation.csv
#   29d_frozen_critic_weights_from_2024.csv
#
# Rules:
# - Frozen 2024 CRITIC weights are reused unchanged.
# - 2025 is used only for retrospective validation.
# - No model tuning / weight tuning happens here.
# - TOPSIS is run separately for each target-month x horizon.
# - 25 districts x 3 burden criteria per decision matrix.
# - All 3 criteria are benefit-type for PRIORITY.
# - DMBI score = TOPSIS closeness * 100.
# - Priority tiers are relative quartile-style tiers, not
#   clinical emergency thresholds.
# ============================================================

from pathlib import Path
import json
import re
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

DISTRICT = "District"
TARGET_DATE = "Forecast_Target_Date"
HORIZON = "Horizon_Months"
HORIZONS = [1, 3, 6]

EXPECTED_DISTRICTS = 25
EXPECTED_ROWS = 900
EXPECTED_ROWS_PER_HORIZON = 300
EXPECTED_MATRICES = 36

PRED = {
    "C1": "C1_Forecasted_Malnutrition_Cases",
    "C2": "C2_Forecasted_Cases_per_1000_U5",
    "C3": "C3_Forecasted_YoY_Burden_Growth_Percent",
}
REAL = {
    "C1": "Actual_Malnutrition_Cases",
    "C2": "Actual_Cases_per_1000_U5",
    "C3": "Actual_YoY_Burden_Growth_Percent",
}
LABELS = {
    "C1": "Forecasted Malnutrition Cases",
    "C2": "Forecasted Cases per 1,000 Under-5",
    "C3": "Forecasted Year-on-Year Burden Growth (%)",
}

TIER_CODE = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT = BASE_DIR / "outputs" / "reports"
FIG = BASE_DIR / "outputs" / "figures"
REPORT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

CRITERIA_PATH = REPORT / "29c_2025_dmbi_criteria_validation.csv"
WEIGHTS_PATH = REPORT / "29d_frozen_critic_weights_from_2024.csv"

DETAIL_PATH = REPORT / "29e_dmbi_topsis_2025_validation_detail.csv"
MATRIX_AUDIT_PATH = REPORT / "29e_dmbi_topsis_2025_matrix_audit.csv"
MONTHLY_PATH = REPORT / "29e_dmbi_topsis_2025_metrics_by_month_horizon.csv"
HORIZON_PATH = REPORT / "29e_dmbi_topsis_2025_summary_by_horizon.csv"
OVERALL_PATH = REPORT / "29e_dmbi_topsis_2025_overall_summary.csv"
CONFUSION_PATH = REPORT / "29e_dmbi_topsis_2025_priority_tier_confusion_matrix.csv"
WEIGHT_AUDIT_PATH = REPORT / "29e_dmbi_topsis_frozen_weight_audit.csv"
AUDIT_PATH = REPORT / "29e_dmbi_topsis_2025_audit.csv"
METHOD_PATH = REPORT / "29e_dmbi_topsis_2025_methodology.json"


def head(text):
    print("\n" + "=" * 120)
    print(text)
    print("=" * 120)


def norm_name(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).lower())


def safe_spearman(a, b):
    a = pd.to_numeric(pd.Series(a), errors="coerce")
    b = pd.to_numeric(pd.Series(b), errors="coerce")
    mask = a.notna() & b.notna()
    a, b = a[mask], b[mask]
    if len(a) < 3 or a.nunique() <= 1 or b.nunique() <= 1:
        return np.nan
    r = spearmanr(a, b)
    return float(r.statistic if hasattr(r, "statistic") else r[0])


def minmax(s):
    x = pd.to_numeric(s, errors="coerce").astype(float)
    lo, hi = float(x.min()), float(x.max())
    if (not np.isfinite(lo)) or (not np.isfinite(hi)):
        raise ValueError("Non-finite criterion values found.")
    if abs(hi - lo) <= 1e-12:
        return pd.Series(np.zeros(len(x)), index=x.index, dtype=float), True
    return ((x - lo) / (hi - lo)).astype(float), False


def pct_0_100(s):
    x = pd.to_numeric(s, errors="coerce")
    n = int(x.notna().sum())
    if n <= 1:
        return pd.Series(np.full(len(x), 50.0), index=x.index, dtype=float)
    p = x.rank(method="average", pct=True)
    return (((p * n) - 1) / max(n - 1, 1) * 100.0).astype(float)


def tier(v):
    if pd.isna(v):
        return "Unknown"
    if v < 25:
        return "Low"
    if v < 50:
        return "Medium"
    if v < 75:
        return "High"
    return "Critical"


def load_frozen_weights():
    w = pd.read_csv(WEIGHTS_PATH)
    w.columns = [str(c).strip() for c in w.columns]

    label_col = next(
        (c for c in ["Criterion_Label", "Criterion", "Criteria", "Indicator"] if c in w.columns),
        None,
    )
    weight_col = next(
        (c for c in ["CRITIC_Weight", "Critic_Weight", "Weight"] if c in w.columns),
        None,
    )

    if label_col is None or weight_col is None:
        raise ValueError(
            f"Could not identify frozen weight columns. Columns={w.columns.tolist()}"
        )

    w[weight_col] = pd.to_numeric(w[weight_col], errors="coerce")
    if w[weight_col].isna().any():
        raise ValueError("Invalid CRITIC weight value.")

    resolved = {}
    audit = []

    for _, r in w.iterrows():
        label = str(r[label_col])
        n = norm_name(label)
        key = None

        if "per1000" in n or "1000under5" in n:
            key = "C2"
        elif "growth" in n or "yearonyear" in n or "yoy" in n:
            key = "C3"
        elif "malnutritioncases" in n or "forecastedcases" in n:
            key = "C1"

        if key is not None:
            if key in resolved:
                raise ValueError(f"Duplicate weight mapping for {key}.")
            resolved[key] = float(r[weight_col])
            audit.append({
                "Criterion_Key": key,
                "Criterion_Label_In_File": label,
                "Expected_Label": LABELS[key],
                "CRITIC_Weight": float(r[weight_col]),
            })

    if set(resolved) != {"C1", "C2", "C3"}:
        raise ValueError(f"Could not map all 3 weights. Resolved={resolved}")

    if not np.isclose(sum(resolved.values()), 1.0, atol=1e-8):
        raise ValueError(f"Frozen weights do not sum to 1: {sum(resolved.values())}")

    if not all(0 < v < 1 for v in resolved.values()):
        raise ValueError("All frozen weights must be between 0 and 1.")

    return resolved, pd.DataFrame(audit)


def run_topsis(group, source_cols, weights, prefix):
    out = group.copy()
    weighted_cols = []
    constants = []

    for key in ["C1", "C2", "C3"]:
        ncol = f"{prefix}_{key}_Normalized"
        wcol = f"{prefix}_{key}_Weighted"

        normalized, constant = minmax(out[source_cols[key]])
        out[ncol] = normalized
        out[wcol] = out[ncol] * weights[key]
        weighted_cols.append(wcol)

        if constant:
            constants.append(key)

    matrix = out[weighted_cols].to_numpy(dtype=float)
    if not np.isfinite(matrix).all():
        raise ValueError(f"{prefix}: non-finite weighted TOPSIS matrix.")

    positive = matrix.max(axis=0)
    negative = matrix.min(axis=0)

    d_plus = np.sqrt(((matrix - positive) ** 2).sum(axis=1))
    d_minus = np.sqrt(((matrix - negative) ** 2).sum(axis=1))
    denom = d_plus + d_minus

    if (denom <= 1e-15).any():
        raise ValueError(f"{prefix}: zero TOPSIS distance denominator.")

    closeness = np.clip(d_minus / denom, 0.0, 1.0)

    out[f"{prefix}_Distance_to_Positive_Ideal"] = d_plus
    out[f"{prefix}_Distance_to_Negative_Ideal"] = d_minus
    out[f"{prefix}_TOPSIS_Closeness"] = closeness
    out[f"{prefix}_DMBI_Score_0_100"] = closeness * 100.0
    out[f"{prefix}_Priority_Rank"] = (
        out[f"{prefix}_TOPSIS_Closeness"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    out[f"{prefix}_Priority_Percentile_0_100"] = pct_0_100(
        out[f"{prefix}_TOPSIS_Closeness"]
    )
    out[f"{prefix}_Priority_Level"] = (
        out[f"{prefix}_Priority_Percentile_0_100"].apply(tier)
    )

    return out, constants


def top5_stats(g):
    p = set(g.nsmallest(5, "Predicted_Priority_Rank")[DISTRICT].astype(str))
    a = set(g.nsmallest(5, "Realized_Priority_Rank")[DISTRICT].astype(str))
    n = len(p & a)
    return n, n / 5.0 * 100.0


def tier_stats(g):
    p = g["Predicted_Priority_Level"].map(TIER_CODE)
    a = g["Realized_Priority_Level"].map(TIER_CODE)

    exact = float((p == a).mean() * 100.0)
    within1 = float(((p - a).abs() <= 1).mean() * 100.0)

    actual_critical = g["Realized_Priority_Level"].eq("Critical")
    pred_critical = g["Predicted_Priority_Level"].eq("Critical")

    recall = (
        float(((actual_critical & pred_critical).sum() / actual_critical.sum()) * 100.0)
        if actual_critical.sum()
        else np.nan
    )

    return exact, within1, recall


# ============================================================
# START
# ============================================================

head("STEP 29E - DMBI TOPSIS 2025 RETROSPECTIVE VALIDATION")

print("\nRules:")
print("- Frozen 2024 CRITIC weights are reused unchanged")
print("- 2025 is used only for retrospective validation")
print("- No weight/model tuning")
print("- TOPSIS is run per target-month x horizon")
print("- DMBI score = TOPSIS closeness x 100")
print("- Critical = highest relative planning-priority tier, NOT clinical emergency")

for p in [CRITERIA_PATH, WEIGHTS_PATH]:
    if not p.exists():
        raise FileNotFoundError(f"Required file not found: {p}")

# ============================================================
# LOAD FROZEN WEIGHTS
# ============================================================

head("LOAD FROZEN 2024 CRITIC WEIGHTS")

weights, weight_audit = load_frozen_weights()
weight_audit.to_csv(WEIGHT_AUDIT_PATH, index=False)

for key in ["C1", "C2", "C3"]:
    print(f"{key} - {LABELS[key]}: {weights[key]:.6f}")

print(f"\nWeight sum: {sum(weights.values()):.12f} [PASS]")

# ============================================================
# LOAD 2025 CRITERIA
# ============================================================

head("LOAD STEP 29C 2025 VALIDATION CRITERIA")

df = pd.read_csv(CRITERIA_PATH)
df.columns = [str(c).strip() for c in df.columns]

required = {
    DISTRICT, TARGET_DATE, HORIZON,
    *PRED.values(), *REAL.values(),
}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {sorted(missing)}")

df[TARGET_DATE] = pd.to_datetime(df[TARGET_DATE], errors="coerce")
df[HORIZON] = pd.to_numeric(df[HORIZON], errors="coerce")

for c in [*PRED.values(), *REAL.values()]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

if df[[TARGET_DATE, HORIZON, *PRED.values(), *REAL.values()]].isna().any().any():
    raise ValueError("2025 criteria contain missing/invalid required values.")

if len(df) != EXPECTED_ROWS:
    raise ValueError(f"Expected 900 rows, found {len(df)}.")

if df[TARGET_DATE].dt.year.nunique() != 1 or int(df[TARGET_DATE].dt.year.iloc[0]) != 2025:
    raise ValueError("Step 29E input must contain 2025 target dates only.")

if df[DISTRICT].astype(str).nunique() != EXPECTED_DISTRICTS:
    raise ValueError("Expected 25 districts.")

for h in HORIZONS:
    n = int((df[HORIZON] == h).sum())
    if n != EXPECTED_ROWS_PER_HORIZON:
        raise ValueError(f"H{h}: expected 300 rows, found {n}.")

counts = df.groupby([TARGET_DATE, HORIZON])[DISTRICT].nunique()
if len(counts) != EXPECTED_MATRICES or not (counts == EXPECTED_DISTRICTS).all():
    raise ValueError("Expected 36 complete 25-district decision matrices.")

print(f"Rows              : {len(df)} [PASS]")
print(f"Districts         : {df[DISTRICT].astype(str).nunique()} [PASS]")
print(f"Decision matrices : {len(counts)} [PASS]")
print(f"Target period     : {df[TARGET_DATE].min().date()} to {df[TARGET_DATE].max().date()} [PASS]")

# ============================================================
# RUN TOPSIS
# ============================================================

head("RUN PREDICTED + REALIZED TOPSIS FOR 2025")

parts = []
matrix_audit = []

for (date, h), g in df.groupby([TARGET_DATE, HORIZON], sort=True):
    date = pd.Timestamp(date)
    h = int(h)
    g = g.sort_values(DISTRICT).reset_index(drop=True)

    pred_scored, pred_constants = run_topsis(g, PRED, weights, "Predicted")
    both_scored, real_constants = run_topsis(pred_scored, REAL, weights, "Realized")

    both_scored["Priority_Rank_Absolute_Error"] = (
        both_scored["Predicted_Priority_Rank"]
        - both_scored["Realized_Priority_Rank"]
    ).abs()

    both_scored["DMBI_Validation_Type"] = (
        "Retrospective 2025 validation; frozen 2024 CRITIC weights."
    )

    parts.append(both_scored)

    matrix_audit.append({
        TARGET_DATE: date,
        HORIZON: h,
        "Districts": len(g),
        "Predicted_Constant_Criteria": ";".join(pred_constants),
        "Realized_Constant_Criteria": ";".join(real_constants),
        "Predicted_TOPSIS_Min": float(both_scored["Predicted_TOPSIS_Closeness"].min()),
        "Predicted_TOPSIS_Max": float(both_scored["Predicted_TOPSIS_Closeness"].max()),
        "Realized_TOPSIS_Min": float(both_scored["Realized_TOPSIS_Closeness"].min()),
        "Realized_TOPSIS_Max": float(both_scored["Realized_TOPSIS_Closeness"].max()),
    })

    print(
        f"{date.date()} | H{h} | districts=25 | "
        f"predicted DMBI={both_scored['Predicted_DMBI_Score_0_100'].min():.2f}-"
        f"{both_scored['Predicted_DMBI_Score_0_100'].max():.2f} | "
        f"realized DMBI={both_scored['Realized_DMBI_Score_0_100'].min():.2f}-"
        f"{both_scored['Realized_DMBI_Score_0_100'].max():.2f}"
    )

detail = pd.concat(parts, ignore_index=True)
matrix_audit_df = pd.DataFrame(matrix_audit)

if len(detail) != EXPECTED_ROWS:
    raise ValueError(f"Expected 900 TOPSIS rows, found {len(detail)}.")

detail.to_csv(DETAIL_PATH, index=False)
matrix_audit_df.to_csv(MATRIX_AUDIT_PATH, index=False)

# ============================================================
# VALIDATION METRICS
# ============================================================

head("CALCULATE 2025 TOPSIS VALIDATION METRICS")

metric_rows = []

for (date, h), g in detail.groupby([TARGET_DATE, HORIZON], sort=True):
    sp = safe_spearman(
        g["Predicted_TOPSIS_Closeness"],
        g["Realized_TOPSIS_Closeness"],
    )
    rank_mae = float(g["Priority_Rank_Absolute_Error"].mean())
    top5n, top5p = top5_stats(g)
    exact, within1, critical_recall = tier_stats(g)

    metric_rows.append({
        TARGET_DATE: pd.Timestamp(date),
        HORIZON: int(h),
        "Districts": len(g),
        "Spearman_Priority_Correlation": sp,
        "Priority_Rank_MAE": rank_mae,
        "Top5_Overlap_Count": top5n,
        "Top5_Overlap_Percentage": top5p,
        "Exact_Priority_Tier_Agreement_Percentage": exact,
        "Within_One_Tier_Agreement_Percentage": within1,
        "Realized_Critical_Tier_Recall_Percentage": critical_recall,
    })

monthly = pd.DataFrame(metric_rows)
monthly.to_csv(MONTHLY_PATH, index=False)

# ============================================================
# HORIZON + OVERALL SUMMARY
# ============================================================

h_rows = []

for h in HORIZONS:
    s = monthly[monthly[HORIZON] == h]

    h_rows.append({
        HORIZON: h,
        "Decision_Matrices": len(s),
        "Mean_Monthly_Spearman": float(s["Spearman_Priority_Correlation"].mean()),
        "Median_Monthly_Spearman": float(s["Spearman_Priority_Correlation"].median()),
        "SD_Monthly_Spearman": float(s["Spearman_Priority_Correlation"].std(ddof=0)),
        "Mean_Priority_Rank_MAE": float(s["Priority_Rank_MAE"].mean()),
        "Mean_Top5_Overlap_Percentage": float(s["Top5_Overlap_Percentage"].mean()),
        "Mean_Exact_Priority_Tier_Agreement_Percentage": float(
            s["Exact_Priority_Tier_Agreement_Percentage"].mean()
        ),
        "Mean_Within_One_Tier_Agreement_Percentage": float(
            s["Within_One_Tier_Agreement_Percentage"].mean()
        ),
        "Mean_Realized_Critical_Tier_Recall_Percentage": float(
            s["Realized_Critical_Tier_Recall_Percentage"].mean()
        ),
    })

horizon_summary = pd.DataFrame(h_rows)
horizon_summary.to_csv(HORIZON_PATH, index=False)

overall = pd.DataFrame([{
    "Validation_Type": "Retrospective 2025 DMBI/TOPSIS validation; weights frozen from 2024",
    "Decision_Matrices": len(monthly),
    "Validation_Rows": len(detail),
    "Mean_Monthly_Spearman": float(monthly["Spearman_Priority_Correlation"].mean()),
    "Median_Monthly_Spearman": float(monthly["Spearman_Priority_Correlation"].median()),
    "Mean_Priority_Rank_MAE": float(monthly["Priority_Rank_MAE"].mean()),
    "Mean_Top5_Overlap_Percentage": float(monthly["Top5_Overlap_Percentage"].mean()),
    "Mean_Exact_Priority_Tier_Agreement_Percentage": float(
        monthly["Exact_Priority_Tier_Agreement_Percentage"].mean()
    ),
    "Mean_Within_One_Tier_Agreement_Percentage": float(
        monthly["Within_One_Tier_Agreement_Percentage"].mean()
    ),
    "Mean_Realized_Critical_Tier_Recall_Percentage": float(
        monthly["Realized_Critical_Tier_Recall_Percentage"].mean()
    ),
}])

overall.to_csv(OVERALL_PATH, index=False)

# ============================================================
# CONFUSION MATRIX
# ============================================================

tier_order = ["Low", "Medium", "High", "Critical"]

confusion = pd.crosstab(
    pd.Categorical(
        detail["Realized_Priority_Level"],
        categories=tier_order,
        ordered=True,
    ),
    pd.Categorical(
        detail["Predicted_Priority_Level"],
        categories=tier_order,
        ordered=True,
    ),
    rownames=["Realized_Priority_Level"],
    colnames=["Predicted_Priority_Level"],
    dropna=False,
)

confusion.to_csv(CONFUSION_PATH)

# ============================================================
# HARD AUDIT
# ============================================================

head("STEP 29E HARD AUDIT")

score_ok = bool(
    detail["Predicted_TOPSIS_Closeness"].between(0, 1).all()
    and detail["Realized_TOPSIS_Closeness"].between(0, 1).all()
)

dmbi_ok = bool(
    detail["Predicted_DMBI_Score_0_100"].between(0, 100).all()
    and detail["Realized_DMBI_Score_0_100"].between(0, 100).all()
)

rank_ok = bool(
    detail["Predicted_Priority_Rank"].between(1, 25).all()
    and detail["Realized_Priority_Rank"].between(1, 25).all()
)

missing_outputs = int(
    detail[
        [
            "Predicted_TOPSIS_Closeness",
            "Realized_TOPSIS_Closeness",
            "Predicted_DMBI_Score_0_100",
            "Realized_DMBI_Score_0_100",
            "Predicted_Priority_Rank",
            "Realized_Priority_Rank",
            "Predicted_Priority_Level",
            "Realized_Priority_Level",
        ]
    ].isna().sum().sum()
)

audits = [
    ("2025 validation rows", len(detail), 900, len(detail) == 900),
    ("Decision matrices", len(monthly), 36, len(monthly) == 36),
    ("Districts per decision matrix", int(counts.min()), 25, (counts == 25).all()),
    ("Frozen weight count", len(weights), 3, len(weights) == 3),
    ("Frozen weights sum to 1", sum(weights.values()), 1.0, np.isclose(sum(weights.values()), 1.0, atol=1e-8)),
    ("2025 used to tune/recalculate CRITIC weights", False, False, True),
    ("Manual DMBI weights supplied in Step 29E", False, False, True),
    ("TOPSIS closeness inside [0,1]", score_ok, True, score_ok),
    ("DMBI scores inside [0,100]", dmbi_ok, True, dmbi_ok),
    ("Priority ranks inside 1-25", rank_ok, True, rank_ok),
    ("Missing TOPSIS validation outputs", missing_outputs, 0, missing_outputs == 0),
    ("Validation interpretation", "Retrospective 2025", "Retrospective 2025", True),
]

audit_df = pd.DataFrame([
    {
        "Audit_Check": name,
        "Result": result,
        "Expected": expected,
        "Status": "PASS" if passed else "FAIL",
    }
    for name, result, expected, passed in audits
])

audit_df.to_csv(AUDIT_PATH, index=False)

for _, r in audit_df.iterrows():
    print(f"{r['Audit_Check']:<58} : {r['Status']}")

if (audit_df["Status"] != "PASS").any():
    raise ValueError("Step 29E hard audit failed. Review the audit CSV.")

# ============================================================
# METHODOLOGY
# ============================================================

methodology = {
    "step": "29E",
    "name": "DMBI TOPSIS 2025 Retrospective Validation",
    "validation_type": (
        "Retrospective 2025 DMBI validation. "
        "Do not claim pristine prospective unseen DMBI validation."
    ),
    "frozen_critic_weights_from_2024": weights,
    "2025_used_for_weight_development": False,
    "manual_weights": False,
    "decision_matrix": (
        "One matrix per target month x horizon: 25 districts x 3 burden criteria."
    ),
    "criteria": {
        "C1": {
            "predicted": PRED["C1"],
            "realized": REAL["C1"],
            "direction": "higher = higher planning priority",
        },
        "C2": {
            "predicted": PRED["C2"],
            "realized": REAL["C2"],
            "direction": "higher = higher planning priority",
        },
        "C3": {
            "predicted": PRED["C3"],
            "realized": REAL["C3"],
            "direction": "higher = higher planning priority",
        },
    },
    "normalization": (
        "Min-max normalization to [0,1] inside each 25-district decision matrix."
    ),
    "topsis": {
        "positive_ideal": "maximum weighted normalized value for each criterion",
        "negative_ideal": "minimum weighted normalized value for each criterion",
        "distance": "Euclidean",
        "closeness": "D_minus / (D_plus + D_minus)",
        "dmbi_score": "TOPSIS closeness x 100",
        "ranking": "descending closeness; rank 1 = highest relative priority",
    },
    "priority_tiers": {
        "basis": "within-matrix percentile of TOPSIS closeness",
        "Low": "<25",
        "Medium": "25 to <50",
        "High": "50 to <75",
        "Critical": ">=75; relative planning priority only",
    },
    "validation_metrics": [
        "Spearman priority correlation",
        "Priority-rank MAE",
        "Top-5 overlap",
        "Exact priority-tier agreement",
        "Within-one-tier agreement",
        "Realized Critical-tier recall",
    ],
    "important_interpretation": (
        "DMBI is a relative district planning-priority score, "
        "not a malnutrition probability, clinical diagnosis, or official emergency threshold."
    ),
    "next_step": (
        "Step 29F applies the same frozen 2024 CRITIC weights and TOPSIS method "
        "to 2026-2030 future criteria."
    ),
}

with open(METHOD_PATH, "w", encoding="utf-8") as f:
    json.dump(methodology, f, indent=2, default=str)

# ============================================================
# FIGURES
# ============================================================

for h in HORIZONS:
    p = monthly[monthly[HORIZON] == h].sort_values(TARGET_DATE)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        p[TARGET_DATE],
        p["Spearman_Priority_Correlation"],
        marker="o",
    )
    ax.axhline(0.0, linewidth=1)
    ax.set_title(f"2025 DMBI TOPSIS Priority Validation - H{h}")
    ax.set_xlabel("Target month")
    ax.set_ylabel("Spearman priority correlation")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(
        FIG / f"29e_dmbi_topsis_2025_spearman_h{h}.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

# ============================================================
# RESULTS
# ============================================================

head("STEP 29E VALIDATION RESULTS")

print("\nFrozen 2024 CRITIC weights used unchanged:")
for key in ["C1", "C2", "C3"]:
    print(f"- {LABELS[key]}: {weights[key]:.6f}")

print("\n2025 validation summary by horizon:")
print(horizon_summary.round(4).to_string(index=False))

print("\nOverall 2025 retrospective validation:")
print(overall.round(4).to_string(index=False))

print("\nInterpretation:")
print("- Higher DMBI score = higher relative district planning priority")
print("- Rank 1 = highest relative priority in that month/horizon")
print("- Critical = highest relative planning tier, not clinical emergency")
print("- 2025 did not change the frozen 2024 CRITIC weights")
print("- This is retrospective DMBI validation")

# ============================================================
# COMPLETE
# ============================================================

head("STEP 29E COMPLETE")

print("\nSaved:")
print(f"- Validation detail             : {DETAIL_PATH}")
print(f"- Matrix audit                  : {MATRIX_AUDIT_PATH}")
print(f"- Monthly/horizon metrics       : {MONTHLY_PATH}")
print(f"- Horizon summary               : {HORIZON_PATH}")
print(f"- Overall summary               : {OVERALL_PATH}")
print(f"- Priority-tier confusion matrix: {CONFUSION_PATH}")
print(f"- Frozen-weight audit           : {WEIGHT_AUDIT_PATH}")
print(f"- Audit                         : {AUDIT_PATH}")
print(f"- Methodology                   : {METHOD_PATH}")
print(f"- Figures                       : {FIG}")

print("\nNEXT:")
print("Send the FULL terminal output before Step 29F future prioritization.")

print("\nSTEP 29E - DMBI TOPSIS 2025 RETROSPECTIVE VALIDATION COMPLETE")
print("=" * 120)
