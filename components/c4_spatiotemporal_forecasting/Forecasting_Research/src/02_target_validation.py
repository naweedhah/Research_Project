# ============================================================
# STEP 02 - TARGET VALIDATION
# Childhood Malnutrition Forecasting Research
# Target Variable: Malnutrition_Cases
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 1. DEFINE PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "malnutrition_source_corrected_v2.csv"
)

REPORT_DIR = BASE_DIR / "outputs" / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. LOAD DATASET
# ============================================================

print("\n" + "=" * 80)
print("STEP 02 - TARGET VALIDATION")
print("=" * 80)

try:

    df = pd.read_csv(DATA_PATH)

    print("\nDataset loaded successfully.")
    print(f"Dataset location: {DATA_PATH}")

except FileNotFoundError:

    print("\nERROR: Dataset was not found.")
    print(f"Expected location: {DATA_PATH}")

    raise


# ============================================================
# 3. DEFINE TARGET AND IMPORTANT INDICATORS
# ============================================================

TARGET = "Malnutrition_Cases"

DIRECT_INDICATORS = [
    "Underweight",
    "Wasting",
    "Stunting"
]

REQUIRED_COLUMNS = [
    "District",
    "Year",
    "Month",
    TARGET
] + DIRECT_INDICATORS


# ============================================================
# 4. CHECK REQUIRED COLUMNS
# ============================================================

print("\n" + "-" * 80)
print("1. REQUIRED COLUMN CHECK")
print("-" * 80)

missing_required_columns = []

for column in REQUIRED_COLUMNS:

    if column in df.columns:
        print(f"[FOUND]   {column}")

    else:
        print(f"[MISSING] {column}")
        missing_required_columns.append(column)


if missing_required_columns:

    raise ValueError(
        "Required columns are missing: "
        + ", ".join(missing_required_columns)
    )


# ============================================================
# 5. BASIC TARGET SUMMARY
# ============================================================

print("\n" + "-" * 80)
print("2. BASIC TARGET SUMMARY")
print("-" * 80)

target_summary = pd.DataFrame({

    "Metric": [
        "Total Rows",
        "Available Target Values",
        "Missing Target Values",
        "Missing Percentage",
        "Minimum",
        "Maximum",
        "Mean",
        "Median",
        "Standard Deviation",
        "Unique Values",
        "Zero Values"
    ],

    "Value": [
        len(df),
        df[TARGET].notna().sum(),
        df[TARGET].isna().sum(),
        round(df[TARGET].isna().mean() * 100, 2),
        df[TARGET].min(),
        df[TARGET].max(),
        round(df[TARGET].mean(), 2),
        round(df[TARGET].median(), 2),
        round(df[TARGET].std(), 2),
        df[TARGET].nunique(dropna=True),
        (df[TARGET] == 0).sum()
    ]
})

print(target_summary.to_string(index=False))

target_summary.to_csv(
    REPORT_DIR / "target_basic_summary.csv",
    index=False
)


# ============================================================
# 6. IDENTIFY EXACT TARGET MISSING ROWS
# ============================================================

print("\n" + "-" * 80)
print("3. TARGET MISSING ROWS")
print("-" * 80)

target_missing_rows = (
    df[df[TARGET].isna()]
    .copy()
)

print(
    f"Number of rows with missing target: "
    f"{len(target_missing_rows)}"
)

if not target_missing_rows.empty:

    columns_to_show = [
        "District",
        "Year",
        "Month",
        TARGET,
        "Underweight",
        "Wasting",
        "Stunting"
    ]

    print(
        target_missing_rows[
            columns_to_show
        ].to_string(index=False)
    )

    target_missing_rows.to_csv(
        REPORT_DIR / "target_missing_rows.csv",
        index=False
    )


# ============================================================
# 7. TARGET MISSINGNESS BY YEAR
# ============================================================

print("\n" + "-" * 80)
print("4. TARGET MISSINGNESS BY YEAR")
print("-" * 80)

target_missing_by_year = (
    df.assign(
        Target_Missing=df[TARGET].isna()
    )
    .groupby("Year")["Target_Missing"]
    .agg(
        Total_Rows="size",
        Missing_Count="sum"
    )
    .reset_index()
)

target_missing_by_year[
    "Missing_Percentage"
] = (
    target_missing_by_year["Missing_Count"]
    / target_missing_by_year["Total_Rows"]
    * 100
).round(2)

print(
    target_missing_by_year
    .to_string(index=False)
)

target_missing_by_year.to_csv(
    REPORT_DIR / "target_missing_by_year.csv",
    index=False
)


# ============================================================
# 8. TARGET MISSINGNESS BY DISTRICT
# ============================================================

print("\n" + "-" * 80)
print("5. TARGET MISSINGNESS BY DISTRICT")
print("-" * 80)

target_missing_by_district = (
    df.assign(
        Target_Missing=df[TARGET].isna()
    )
    .groupby("District")["Target_Missing"]
    .agg(
        Total_Rows="size",
        Missing_Count="sum"
    )
    .reset_index()
)

target_missing_by_district[
    "Missing_Percentage"
] = (
    target_missing_by_district["Missing_Count"]
    / target_missing_by_district["Total_Rows"]
    * 100
).round(2)

district_missing_only = (
    target_missing_by_district[
        target_missing_by_district[
            "Missing_Count"
        ] > 0
    ]
)

if not district_missing_only.empty:

    print(
        district_missing_only
        .to_string(index=False)
    )

else:

    print(
        "No district-level target missingness detected."
    )

target_missing_by_district.to_csv(
    REPORT_DIR
    / "target_missing_by_district.csv",
    index=False
)


# ============================================================
# 9. TARGET MISSINGNESS BY MONTH
# ============================================================

print("\n" + "-" * 80)
print("6. TARGET MISSINGNESS BY MONTH")
print("-" * 80)

target_missing_by_month = (
    df.assign(
        Target_Missing=df[TARGET].isna()
    )
    .groupby("Month")["Target_Missing"]
    .agg(
        Total_Rows="size",
        Missing_Count="sum"
    )
    .reset_index()
)

target_missing_by_month[
    "Missing_Percentage"
] = (
    target_missing_by_month["Missing_Count"]
    / target_missing_by_month["Total_Rows"]
    * 100
).round(2)

print(
    target_missing_by_month
    .to_string(index=False)
)

target_missing_by_month.to_csv(
    REPORT_DIR
    / "target_missing_by_month.csv",
    index=False
)


# ============================================================
# 10. TARGET / INDICATOR MISSINGNESS OVERLAP
# ============================================================

print("\n" + "-" * 80)
print("7. TARGET / INDICATOR MISSINGNESS OVERLAP")
print("-" * 80)

target_missing_mask = df[TARGET].isna()

overlap_results = []

for column in DIRECT_INDICATORS:

    feature_missing_mask = df[column].isna()

    both_missing = (
        target_missing_mask
        & feature_missing_mask
    ).sum()

    target_missing_only = (
        target_missing_mask
        & ~feature_missing_mask
    ).sum()

    indicator_missing_only = (
        ~target_missing_mask
        & feature_missing_mask
    ).sum()

    neither_missing = (
        ~target_missing_mask
        & ~feature_missing_mask
    ).sum()

    same_missing_pattern = (
        target_missing_mask
        .equals(feature_missing_mask)
    )

    overlap_results.append({

        "Indicator": column,

        "Target_Missing":
            int(target_missing_mask.sum()),

        "Indicator_Missing":
            int(feature_missing_mask.sum()),

        "Both_Missing":
            int(both_missing),

        "Target_Missing_Only":
            int(target_missing_only),

        "Indicator_Missing_Only":
            int(indicator_missing_only),

        "Neither_Missing":
            int(neither_missing),

        "Exact_Same_Missing_Pattern":
            same_missing_pattern
    })


missing_overlap_df = pd.DataFrame(
    overlap_results
)

print(
    missing_overlap_df
    .to_string(index=False)
)

missing_overlap_df.to_csv(
    REPORT_DIR
    / "target_indicator_missing_overlap.csv",
    index=False
)


# ============================================================
# 11. ZERO TARGET ANALYSIS
# ============================================================

print("\n" + "-" * 80)
print("8. ZERO TARGET ANALYSIS")
print("-" * 80)

zero_target_rows = (
    df[df[TARGET] == 0]
    .copy()
)

print(
    f"Number of zero target rows: "
    f"{len(zero_target_rows)}"
)

if not zero_target_rows.empty:

    print(
        zero_target_rows[
            [
                "District",
                "Year",
                "Month",
                TARGET,
                "Underweight",
                "Wasting",
                "Stunting"
            ]
        ].to_string(index=False)
    )

    zero_target_rows.to_csv(
        REPORT_DIR
        / "zero_target_rows.csv",
        index=False
    )


# ============================================================
# 12. MONTHLY TARGET VARIATION
# ============================================================

print("\n" + "-" * 80)
print("9. MONTHLY TARGET VARIATION")
print("-" * 80)

district_year_variation = (
    df
    .groupby(
        ["District", "Year"]
    )[TARGET]
    .agg(
        Available_Months="count",
        Unique_Target_Values="nunique",
        Minimum="min",
        Maximum="max",
        Mean="mean",
        Std_Deviation="std"
    )
    .reset_index()
)


# IMPORTANT CORRECTION:
# Only check constant periods where target values are actually available.
# Full-missing district-years must NOT be classified as constant periods.

constant_target_periods = (
    district_year_variation[
        (
            district_year_variation[
                "Available_Months"
            ] > 0
        )
        &
        (
            district_year_variation[
                "Unique_Target_Values"
            ] <= 1
        )
    ]
)


print(
    "District-years with available data "
    "but only one unique target value: "
    f"{len(constant_target_periods)}"
)


if not constant_target_periods.empty:

    print(
        constant_target_periods
        .to_string(index=False)
    )

else:

    print(
        "No constant district-year target "
        "periods detected among available data."
    )


# Separately identify completely missing district-years

fully_missing_target_periods = (
    district_year_variation[
        district_year_variation[
            "Available_Months"
        ] == 0
    ]
)


print(
    "\nDistrict-years with completely "
    "missing target data: "
    f"{len(fully_missing_target_periods)}"
)


if not fully_missing_target_periods.empty:

    print(
        fully_missing_target_periods[
            [
                "District",
                "Year",
                "Available_Months"
            ]
        ].to_string(index=False)
    )

    fully_missing_target_periods.to_csv(
        REPORT_DIR
        / "fully_missing_target_district_years.csv",
        index=False
    )


district_year_variation.to_csv(
    REPORT_DIR
    / "target_district_year_variation.csv",
    index=False
)


# ============================================================
# 13. MONTH-TO-MONTH TARGET CHANGE
# ============================================================

print("\n" + "-" * 80)
print("10. MONTH-TO-MONTH TARGET CHANGE")
print("-" * 80)

time_df = (
    df
    .sort_values(
        ["District", "Year", "Month"]
    )
    .copy()
)

time_df[
    "Previous_Month_Target"
] = (
    time_df
    .groupby("District")[TARGET]
    .shift(1)
)

time_df[
    "Target_Change"
] = (
    time_df[TARGET]
    - time_df[
        "Previous_Month_Target"
    ]
)

time_df[
    "Absolute_Target_Change"
] = (
    time_df[
        "Target_Change"
    ].abs()
)

valid_changes = (
    time_df[
        "Target_Change"
    ].dropna()
)

if not valid_changes.empty:

    print(
        f"Mean monthly change     : "
        f"{valid_changes.mean():.2f}"
    )

    print(
        f"Median monthly change   : "
        f"{valid_changes.median():.2f}"
    )

    print(
        f"Minimum monthly change  : "
        f"{valid_changes.min():.2f}"
    )

    print(
        f"Maximum monthly change  : "
        f"{valid_changes.max():.2f}"
    )

    print(
        f"Mean absolute change    : "
        f"{valid_changes.abs().mean():.2f}"
    )


largest_changes = (
    time_df[
        [
            "District",
            "Year",
            "Month",
            TARGET,
            "Previous_Month_Target",
            "Target_Change",
            "Absolute_Target_Change"
        ]
    ]
    .dropna(
        subset=[
            "Absolute_Target_Change"
        ]
    )
    .sort_values(
        "Absolute_Target_Change",
        ascending=False
    )
    .head(20)
)

print(
    "\nLargest month-to-month changes:"
)

print(
    largest_changes
    .to_string(index=False)
)

largest_changes.to_csv(
    REPORT_DIR
    / "largest_target_monthly_changes.csv",
    index=False
)


# ============================================================
# 14. CORRELATION WITH DIRECT INDICATORS
# ============================================================

print("\n" + "-" * 80)
print("11. TARGET CORRELATION WITH DIRECT INDICATORS")
print("-" * 80)

correlation_results = []

for column in DIRECT_INDICATORS:

    valid_data = (
        df[
            [TARGET, column]
        ]
        .dropna()
    )

    if len(valid_data) >= 2:

        correlation = (
            valid_data[TARGET]
            .corr(
                valid_data[column]
            )
        )

    else:

        correlation = np.nan

    correlation_results.append({

        "Variable":
            column,

        "Valid_Pairs":
            len(valid_data),

        "Pearson_Correlation":
            round(correlation, 4)
            if pd.notna(correlation)
            else np.nan
    })


correlation_df = pd.DataFrame(
    correlation_results
)

print(
    correlation_df
    .to_string(index=False)
)

correlation_df.to_csv(
    REPORT_DIR
    / "target_direct_indicator_correlations.csv",
    index=False
)


# ============================================================
# 15. SIMPLE TARGET CONSTRUCTION CHECKS
# ============================================================

print("\n" + "-" * 80)
print("12. SIMPLE TARGET CONSTRUCTION CHECKS")
print("-" * 80)

construction_columns = [
    TARGET,
    "Underweight",
    "Wasting",
    "Stunting"
]

construction_df = (
    df[
        construction_columns
    ]
    .dropna()
    .copy()
)


construction_df[
    "Indicator_Sum"
] = (
    construction_df[
        [
            "Underweight",
            "Wasting",
            "Stunting"
        ]
    ]
    .sum(axis=1)
)


construction_df[
    "Indicator_Mean"
] = (
    construction_df[
        [
            "Underweight",
            "Wasting",
            "Stunting"
        ]
    ]
    .mean(axis=1)
)


construction_df[
    "Indicator_Max"
] = (
    construction_df[
        [
            "Underweight",
            "Wasting",
            "Stunting"
        ]
    ]
    .max(axis=1)
)


candidate_formulas = {

    "Underweight":
        construction_df["Underweight"],

    "Wasting":
        construction_df["Wasting"],

    "Stunting":
        construction_df["Stunting"],

    "Underweight + Wasting + Stunting":
        construction_df["Indicator_Sum"],

    "Mean of Underweight/Wasting/Stunting":
        construction_df["Indicator_Mean"],

    "Maximum of Underweight/Wasting/Stunting":
        construction_df["Indicator_Max"]
}


construction_checks = []

for formula_name, candidate_values in (
    candidate_formulas.items()
):

    exact_matches = np.isclose(
        construction_df[TARGET],
        candidate_values,
        rtol=0,
        atol=1e-8
    )

    match_count = int(
        exact_matches.sum()
    )

    match_percentage = (
        match_count
        / len(construction_df)
        * 100
    )

    construction_checks.append({

        "Candidate_Formula":
            formula_name,

        "Valid_Rows":
            len(construction_df),

        "Exact_Matches":
            match_count,

        "Match_Percentage":
            round(
                match_percentage,
                2
            )
    })


construction_check_df = pd.DataFrame(
    construction_checks
)

print(
    construction_check_df
    .to_string(index=False)
)

construction_check_df.to_csv(
    REPORT_DIR
    / "target_construction_checks.csv",
    index=False
)


print(
    "\nIMPORTANT: These tests only check "
    "simple mathematical relationships."
)

print(
    "They DO NOT prove how the target "
    "was originally created."
)


# ============================================================
# 16. TARGET / INDICATOR RANGE COMPARISON
# ============================================================

print("\n" + "-" * 80)
print("13. TARGET / INDICATOR RANGE COMPARISON")
print("-" * 80)

range_columns = [
    TARGET,
    "Underweight",
    "Wasting",
    "Stunting"
]

range_results = []

for column in range_columns:

    range_results.append({

        "Variable":
            column,

        "Minimum":
            df[column].min(),

        "Maximum":
            df[column].max(),

        "Mean":
            round(
                df[column].mean(),
                2
            ),

        "Median":
            round(
                df[column].median(),
                2
            )
    })


range_df = pd.DataFrame(
    range_results
)

print(
    range_df
    .to_string(index=False)
)

range_df.to_csv(
    REPORT_DIR
    / "target_indicator_range_comparison.csv",
    index=False
)


# ============================================================
# 17. TARGET IQR EXTREME VALUE SCREENING
# ============================================================

print("\n" + "-" * 80)
print("14. TARGET IQR EXTREME VALUE SCREENING")
print("-" * 80)

target_non_missing = (
    df[TARGET]
    .dropna()
)

Q1 = target_non_missing.quantile(0.25)
Q3 = target_non_missing.quantile(0.75)

IQR = Q3 - Q1

lower_bound = (
    Q1
    - 1.5 * IQR
)

upper_bound = (
    Q3
    + 1.5 * IQR
)

target_iqr_outliers = (
    df[
        (df[TARGET] < lower_bound)
        |
        (df[TARGET] > upper_bound)
    ]
    .copy()
)

print(f"Q1          : {Q1:.2f}")
print(f"Q3          : {Q3:.2f}")
print(f"IQR         : {IQR:.2f}")
print(f"Lower Bound : {lower_bound:.2f}")
print(f"Upper Bound : {upper_bound:.2f}")

print(
    "Potential IQR extreme target rows: "
    f"{len(target_iqr_outliers)}"
)

if not target_iqr_outliers.empty:

    print(
        target_iqr_outliers[
            [
                "District",
                "Year",
                "Month",
                TARGET
            ]
        ]
        .sort_values(
            TARGET,
            ascending=False
        )
        .to_string(index=False)
    )

    target_iqr_outliers.to_csv(
        REPORT_DIR
        / "target_iqr_extreme_rows.csv",
        index=False
    )


print(
    "\nNOTE: IQR extreme values are not "
    "automatically treated as errors."
)

print(
    "They must be investigated before "
    "any removal or transformation."
)


# ============================================================
# 18. NEGATIVE TARGET CHECK
# ============================================================

print("\n" + "-" * 80)
print("15. NEGATIVE TARGET CHECK")
print("-" * 80)

negative_target_count = (
    df[TARGET] < 0
).sum()

print(
    f"Negative target values: "
    f"{negative_target_count}"
)

if negative_target_count == 0:

    print(
        "No negative Malnutrition_Cases "
        "values detected."
    )


# ============================================================
# 19. TARGET COUNT-VALUE CHECK
# ============================================================

print("\n" + "-" * 80)
print("16. TARGET COUNT-VALUE CHECK")
print("-" * 80)

valid_target = (
    df[TARGET]
    .dropna()
)

non_integer_like = (
    ~np.isclose(
        valid_target,
        np.round(valid_target)
    )
)

non_integer_like_count = int(
    non_integer_like.sum()
)

print(
    "Non-integer-like target values: "
    f"{non_integer_like_count}"
)

if non_integer_like_count == 0:

    print(
        "Available target values behave "
        "like count values."
    )


# ============================================================
# 20. TARGET LEAKAGE RISK REVIEW
# ============================================================

print("\n" + "-" * 80)
print("17. TARGET LEAKAGE RISK REVIEW")
print("-" * 80)

leakage_review = pd.DataFrame({

    "Variable": [
        "Underweight",
        "Wasting",
        "Stunting"
    ],

    "Risk": [
        "Requires investigation",
        "Requires investigation",
        "Requires investigation"
    ],

    "Reason": [
        (
            "May have a close relationship with "
            "the target and may be part of its "
            "reporting or definition."
        ),
        (
            "May have a close relationship with "
            "the target and may be part of its "
            "reporting or definition."
        ),
        (
            "May have a close relationship with "
            "the target and may be part of its "
            "reporting or definition."
        )
    ],

    "Decision": [
        (
            "Do not automatically remove. "
            "Check source definition and "
            "temporal availability first."
        ),
        (
            "Do not automatically remove. "
            "Check source definition and "
            "temporal availability first."
        ),
        (
            "Do not automatically remove. "
            "Check source definition and "
            "temporal availability first."
        )
    ]
})

print(
    leakage_review
    .to_string(index=False)
)

leakage_review.to_csv(
    REPORT_DIR
    / "target_leakage_review.csv",
    index=False
)


# ============================================================
# 21. FORECASTING AVAILABILITY RULE
# ============================================================

print("\n" + "-" * 80)
print("18. FORECASTING AVAILABILITY RULE")
print("-" * 80)

print(
    """
For forecasting, a predictor must only use information
that would genuinely be available at the prediction time.

Example:

To predict Malnutrition_Cases for June 2025,
the model must not use information that becomes available
after June 2025.

This applies to:

- Malnutrition indicators
- Health programme data
- Triposha data
- Birth-related variables
- Maternal-health variables
- Socioeconomic variables
- Climate variables
- Annual variables

Lagged historical values may be used when they were
already available at the forecasting date.

Same-period variables must be checked carefully before
being included in a forecasting model.
"""
)


# ============================================================
# 22. TARGET MISSING VALUE HANDLING RULE
# ============================================================

print("\n" + "-" * 80)
print("19. TARGET MISSING-VALUE HANDLING RULE")
print("-" * 80)

print(
    """
Missing target values will NOT be blindly filled using
mean, median, interpolation, or other simple imputation.

The target is the value the forecasting model must learn
to predict.

Therefore, missing target rows must first be investigated.

Possible later decisions include:

1. Recovering the original value from a verified source.
2. Excluding rows without a valid training label.
3. Using those rows only where appropriate for feature history.

The final decision will be made during preprocessing.
"""
)


# ============================================================
# 23. FINAL TARGET VALIDATION SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("TARGET VALIDATION SUMMARY")
print("=" * 80)

print(
    f"Dataset rows                 : "
    f"{len(df)}"
)

print(
    f"Available target values      : "
    f"{df[TARGET].notna().sum()}"
)

print(
    f"Missing target values        : "
    f"{df[TARGET].isna().sum()}"
)

print(
    f"Missing target percentage    : "
    f"{df[TARGET].isna().mean() * 100:.2f}%"
)

print(
    f"Zero target values           : "
    f"{(df[TARGET] == 0).sum()}"
)

print(
    f"Negative target values       : "
    f"{negative_target_count}"
)

print(
    f"Potential IQR extreme values : "
    f"{len(target_iqr_outliers)}"
)

print(
    f"Constant target periods      : "
    f"{len(constant_target_periods)}"
)

print(
    f"Fully missing target periods : "
    f"{len(fully_missing_target_periods)}"
)

print(
    f"Target minimum               : "
    f"{df[TARGET].min()}"
)

print(
    f"Target maximum               : "
    f"{df[TARGET].max()}"
)


print(
    "\nDirect indicators reviewed:"
)

for column in DIRECT_INDICATORS:

    print(f"- {column}")


print("\nIMPORTANT:")

print(
    "Underweight, Wasting and Stunting are "
    "NOT automatically selected or removed."
)

print(
    "They receive additional leakage checks "
    "because of their close relationship "
    "with malnutrition reporting."
)

print(
    "All other relevant predictor variables "
    "will also be analysed later during "
    "EDA and feature analysis."
)


# ============================================================
# 24. COMPLETE
# ============================================================

print("\nReports saved to:")
print(REPORT_DIR)

print(
    "\nSTEP 02 - TARGET VALIDATION COMPLETE"
)

print("=" * 80)