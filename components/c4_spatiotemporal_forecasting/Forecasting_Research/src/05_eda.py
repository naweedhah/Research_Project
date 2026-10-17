# ============================================================
# STEP 05 - EXPLORATORY DATA ANALYSIS (EDA)
# Childhood Malnutrition Forecasting Research
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# 1. DEFINE PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "malnutrition_preprocessed_base.csv"
)

REPORT_DIR = (
    BASE_DIR
    / "outputs"
    / "reports"
)

FIGURE_DIR = (
    BASE_DIR
    / "outputs"
    / "figures"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. LOAD DATASET
# ============================================================

print("\n" + "=" * 85)
print("STEP 05 - EXPLORATORY DATA ANALYSIS")
print("=" * 85)

try:

    df = pd.read_csv(DATA_PATH)

    print("\nDataset loaded successfully.")
    print(f"Dataset location: {DATA_PATH}")

except FileNotFoundError:

    print("\nERROR: Preprocessed dataset was not found.")
    print(f"Expected location: {DATA_PATH}")

    raise


# ============================================================
# 3. PREPARE DATE COLUMN
# ============================================================

print("\n" + "-" * 85)
print("1. DATE PREPARATION")
print("-" * 85)

if "Date" in df.columns:

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

else:

    df["Date"] = pd.to_datetime(
        dict(
            year=df["Year"],
            month=df["Month"],
            day=1
        ),
        errors="coerce"
    )


print(
    f"Minimum date: "
    f"{df['Date'].min().date()}"
)

print(
    f"Maximum date: "
    f"{df['Date'].max().date()}"
)


# ============================================================
# 4. REQUIRED COLUMN CHECK
# ============================================================

print("\n" + "-" * 85)
print("2. REQUIRED COLUMN CHECK")
print("-" * 85)

TARGET = "Malnutrition_Cases"

required_columns = [
    "District",
    "Year",
    "Month",
    "Date",
    TARGET
]

missing_required = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_required:

    raise ValueError(
        "Required columns are missing: "
        + ", ".join(missing_required)
    )

for column in required_columns:

    print(f"[FOUND] {column}")


# ============================================================
# 5. BASIC TARGET DISTRIBUTION
# ============================================================

print("\n" + "-" * 85)
print("3. TARGET DISTRIBUTION")
print("-" * 85)

target_valid = (
    df[TARGET]
    .dropna()
)

target_distribution = pd.DataFrame({

    "Metric": [
        "Available Values",
        "Missing Values",
        "Minimum",
        "Q1",
        "Median",
        "Mean",
        "Q3",
        "Maximum",
        "Standard Deviation",
        "Skewness"
    ],

    "Value": [
        target_valid.count(),
        df[TARGET].isna().sum(),
        target_valid.min(),
        target_valid.quantile(0.25),
        target_valid.median(),
        target_valid.mean(),
        target_valid.quantile(0.75),
        target_valid.max(),
        target_valid.std(),
        target_valid.skew()
    ]
})

print(
    target_distribution
    .to_string(index=False)
)

target_distribution.to_csv(
    REPORT_DIR
    / "eda_target_distribution.csv",
    index=False
)


# ============================================================
# 6. TARGET HISTOGRAM
# ============================================================

plt.figure(
    figsize=(9, 6)
)

plt.hist(
    target_valid,
    bins=30,
    edgecolor="black"
)

plt.title(
    "Distribution of Malnutrition Cases"
)

plt.xlabel(
    "Malnutrition Cases"
)

plt.ylabel(
    "Frequency"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_target_histogram.png",
    dpi=300
)

plt.close()


# ============================================================
# 7. TARGET BOXPLOT
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.boxplot(
    target_valid,
    orientation="vertical"
)

plt.title(
    "Boxplot of Malnutrition Cases"
)

plt.ylabel(
    "Malnutrition Cases"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_target_boxplot.png",
    dpi=300
)

plt.close()


# ============================================================
# 8. YEARLY TARGET TREND
# ============================================================

print("\n" + "-" * 85)
print("4. YEARLY TARGET TREND")
print("-" * 85)

yearly_target = (
    df
    .groupby("Year")[TARGET]
    .agg(
        Available_Observations="count",
        Mean="mean",
        Median="median",
        Minimum="min",
        Maximum="max",
        Standard_Deviation="std"
    )
    .reset_index()
)

print(
    yearly_target
    .to_string(index=False)
)

yearly_target.to_csv(
    REPORT_DIR
    / "eda_yearly_target_summary.csv",
    index=False
)


plt.figure(
    figsize=(10, 6)
)

plt.plot(
    yearly_target["Year"],
    yearly_target["Mean"],
    marker="o"
)

plt.title(
    "Average Malnutrition Cases by Year"
)

plt.xlabel("Year")

plt.ylabel(
    "Mean Malnutrition Cases"
)

plt.grid(
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_yearly_target_trend.png",
    dpi=300
)

plt.close()


# ============================================================
# 9. MONTHLY / SEASONAL TARGET PATTERN
# ============================================================

print("\n" + "-" * 85)
print("5. MONTHLY / SEASONAL TARGET PATTERN")
print("-" * 85)

monthly_target = (
    df
    .groupby("Month")[TARGET]
    .agg(
        Available_Observations="count",
        Mean="mean",
        Median="median",
        Minimum="min",
        Maximum="max",
        Standard_Deviation="std"
    )
    .reset_index()
)

print(
    monthly_target
    .to_string(index=False)
)

monthly_target.to_csv(
    REPORT_DIR
    / "eda_monthly_target_summary.csv",
    index=False
)


plt.figure(
    figsize=(10, 6)
)

plt.plot(
    monthly_target["Month"],
    monthly_target["Mean"],
    marker="o"
)

plt.xticks(
    range(1, 13)
)

plt.title(
    "Average Malnutrition Cases by Month"
)

plt.xlabel("Month")

plt.ylabel(
    "Mean Malnutrition Cases"
)

plt.grid(
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_monthly_seasonality.png",
    dpi=300
)

plt.close()


# ============================================================
# 10. DISTRICT-LEVEL TARGET ANALYSIS
# ============================================================

print("\n" + "-" * 85)
print("6. DISTRICT-LEVEL TARGET ANALYSIS")
print("-" * 85)

district_target = (
    df
    .groupby("District")[TARGET]
    .agg(
        Available_Observations="count",
        Missing_Observations=lambda x:
            x.isna().sum(),
        Mean="mean",
        Median="median",
        Minimum="min",
        Maximum="max",
        Standard_Deviation="std"
    )
    .reset_index()
)

district_target = (
    district_target
    .sort_values(
        "Mean",
        ascending=False
    )
)

print(
    district_target
    .to_string(index=False)
)

district_target.to_csv(
    REPORT_DIR
    / "eda_district_target_summary.csv",
    index=False
)


plot_district = (
    district_target
    .sort_values(
        "Mean",
        ascending=True
    )
)

plt.figure(
    figsize=(10, 9)
)

plt.barh(
    plot_district["District"],
    plot_district["Mean"]
)

plt.title(
    "Average Malnutrition Cases by District"
)

plt.xlabel(
    "Mean Malnutrition Cases"
)

plt.ylabel(
    "District"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_district_target_mean.png",
    dpi=300
)

plt.close()


# ============================================================
# 11. DISTRICT-YEAR TARGET SUMMARY
# ============================================================

print("\n" + "-" * 85)
print("7. DISTRICT-YEAR TARGET ANALYSIS")
print("-" * 85)

district_year_target = (
    df
    .groupby(
        [
            "District",
            "Year"
        ]
    )[TARGET]
    .agg(
        Available_Months="count",
        Mean="mean",
        Median="median",
        Minimum="min",
        Maximum="max"
    )
    .reset_index()
)

district_year_target.to_csv(
    REPORT_DIR
    / "eda_district_year_target_summary.csv",
    index=False
)

print(
    f"District-year combinations analysed: "
    f"{len(district_year_target)}"
)


# ============================================================
# 12. DISTRICT-YEAR HEATMAP
# ============================================================

heatmap_data = (
    district_year_target
    .pivot(
        index="District",
        columns="Year",
        values="Mean"
    )
)

plt.figure(
    figsize=(13, 10)
)

image = plt.imshow(
    heatmap_data,
    aspect="auto"
)

plt.colorbar(
    image,
    label="Mean Malnutrition Cases"
)

plt.xticks(
    range(
        len(
            heatmap_data.columns
        )
    ),
    heatmap_data.columns,
    rotation=45
)

plt.yticks(
    range(
        len(
            heatmap_data.index
        )
    ),
    heatmap_data.index
)

plt.title(
    "District-Year Mean Malnutrition Cases"
)

plt.xlabel("Year")

plt.ylabel("District")

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_district_year_heatmap.png",
    dpi=300
)

plt.close()


# ============================================================
# 13. NUMERICAL FEATURE CORRELATION WITH TARGET
# ============================================================

print("\n" + "-" * 85)
print("8. NUMERICAL FEATURE CORRELATION WITH TARGET")
print("-" * 85)

numeric_df = (
    df
    .select_dtypes(
        include=np.number
    )
)

correlation_series = (
    numeric_df
    .corr()[TARGET]
    .drop(
        TARGET
    )
)

correlation_report = pd.DataFrame({

    "Variable":
        correlation_series.index,

    "Pearson_Correlation":
        correlation_series.values
})

correlation_report[
    "Absolute_Correlation"
] = (
    correlation_report[
        "Pearson_Correlation"
    ]
    .abs()
)

correlation_report = (
    correlation_report
    .sort_values(
        "Absolute_Correlation",
        ascending=False
    )
)

print(
    correlation_report
    .to_string(index=False)
)

correlation_report.to_csv(
    REPORT_DIR
    / "eda_target_all_numeric_correlations.csv",
    index=False
)

print("\nIMPORTANT:")

print(
    "Correlation measures association only."
)

print(
    "It does NOT prove that a variable causes "
    "malnutrition."
)


# ============================================================
# 14. TOP CORRELATION BAR CHART
# ============================================================

top_correlation_variables = (
    correlation_report
    .head(15)
    .sort_values(
        "Absolute_Correlation",
        ascending=True
    )
)

plt.figure(
    figsize=(10, 8)
)

plt.barh(
    top_correlation_variables[
        "Variable"
    ],
    top_correlation_variables[
        "Pearson_Correlation"
    ]
)

plt.title(
    "Variables Most Correlated with Malnutrition Cases"
)

plt.xlabel(
    "Pearson Correlation"
)

plt.ylabel(
    "Variable"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_top_target_correlations.png",
    dpi=300
)

plt.close()


# ============================================================
# 15. DIRECT INDICATOR RELATIONSHIPS
# ============================================================

print("\n" + "-" * 85)
print("9. DIRECT MALNUTRITION INDICATOR RELATIONSHIPS")
print("-" * 85)

direct_indicators = [
    "Underweight",
    "Wasting",
    "Stunting"
]

direct_relationship_results = []

for feature in direct_indicators:

    if feature not in df.columns:
        continue

    valid_pair = (
        df[
            [
                TARGET,
                feature
            ]
        ]
        .dropna()
    )

    correlation = (
        valid_pair[
            TARGET
        ]
        .corr(
            valid_pair[
                feature
            ]
        )
    )

    direct_relationship_results.append({

        "Variable":
            feature,

        "Valid_Pairs":
            len(valid_pair),

        "Pearson_Correlation":
            correlation
    })

direct_relationship_df = pd.DataFrame(
    direct_relationship_results
)

print(
    direct_relationship_df
    .to_string(index=False)
)

direct_relationship_df.to_csv(
    REPORT_DIR
    / "eda_direct_indicator_relationships.csv",
    index=False
)


# ============================================================
# 16. SCATTER PLOTS FOR DIRECT INDICATORS
# ============================================================

for feature in direct_indicators:

    if feature not in df.columns:
        continue

    plot_data = (
        df[
            [
                TARGET,
                feature
            ]
        ]
        .dropna()
    )

    plt.figure(
        figsize=(8, 6)
    )

    plt.scatter(
        plot_data[feature],
        plot_data[TARGET],
        alpha=0.5
    )

    plt.title(
        f"{TARGET} vs {feature}"
    )

    plt.xlabel(feature)

    plt.ylabel(TARGET)

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR
        / f"eda_scatter_{feature.lower()}.png",
        dpi=300
    )

    plt.close()


# ============================================================
# 17. YEAR-MONTH TEMPORAL TREND
# ============================================================

print("\n" + "-" * 85)
print("10. OVERALL MONTHLY TIME TREND")
print("-" * 85)

time_target = (
    df
    .groupby("Date")[TARGET]
    .mean()
    .reset_index(
        name="Mean_Malnutrition_Cases"
    )
)

print(
    f"Monthly time points: "
    f"{len(time_target)}"
)

time_target.to_csv(
    REPORT_DIR
    / "eda_overall_monthly_time_series.csv",
    index=False
)


plt.figure(
    figsize=(14, 6)
)

plt.plot(
    time_target["Date"],
    time_target[
        "Mean_Malnutrition_Cases"
    ]
)

plt.title(
    "Overall Monthly Malnutrition Trend"
)

plt.xlabel("Date")

plt.ylabel(
    "Mean Malnutrition Cases"
)

plt.grid(
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_overall_monthly_trend.png",
    dpi=300
)

plt.close()


# ============================================================
# 18. 12-MONTH ROLLING TREND
# ============================================================

time_target[
    "Rolling_12_Month_Mean"
] = (
    time_target[
        "Mean_Malnutrition_Cases"
    ]
    .rolling(
        window=12,
        min_periods=6
    )
    .mean()
)


plt.figure(
    figsize=(14, 6)
)

plt.plot(
    time_target["Date"],
    time_target[
        "Mean_Malnutrition_Cases"
    ],
    alpha=0.5,
    label="Monthly Mean"
)

plt.plot(
    time_target["Date"],
    time_target[
        "Rolling_12_Month_Mean"
    ],
    linewidth=2,
    label="12-Month Rolling Mean"
)

plt.title(
    "Malnutrition Trend with 12-Month Rolling Mean"
)

plt.xlabel("Date")

plt.ylabel(
    "Mean Malnutrition Cases"
)

plt.legend()

plt.grid(
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "eda_12_month_rolling_trend.png",
    dpi=300
)

plt.close()


# ============================================================
# 19. MISSING VALUE ANALYSIS
# ============================================================

print("\n" + "-" * 85)
print("11. REMAINING MISSING VALUE ANALYSIS")
print("-" * 85)

missing_summary = pd.DataFrame({

    "Column":
        df.columns,

    "Missing_Count":
        df.isna()
        .sum()
        .values,

    "Missing_Percentage":
        (
            df.isna()
            .mean()
            * 100
        )
        .round(2)
        .values
})

missing_summary = (
    missing_summary[
        missing_summary[
            "Missing_Count"
        ] > 0
    ]
    .sort_values(
        "Missing_Count",
        ascending=False
    )
)

print(
    missing_summary
    .to_string(index=False)
)

missing_summary.to_csv(
    REPORT_DIR
    / "eda_remaining_missing_summary.csv",
    index=False
)


if not missing_summary.empty:

    plot_missing = (
        missing_summary
        .sort_values(
            "Missing_Count",
            ascending=True
        )
    )

    plt.figure(
        figsize=(10, 8)
    )

    plt.barh(
        plot_missing[
            "Column"
        ],
        plot_missing[
            "Missing_Count"
        ]
    )

    plt.title(
        "Remaining Missing Values"
    )

    plt.xlabel(
        "Number of Missing Values"
    )

    plt.tight_layout()

    plt.savefig(
        FIGURE_DIR
        / "eda_remaining_missing_values.png",
        dpi=300
    )

    plt.close()


# ============================================================
# 20. IQR TARGET EXTREME REVIEW
# ============================================================

print("\n" + "-" * 85)
print("12. TARGET EXTREME VALUE REVIEW")
print("-" * 85)

q1 = (
    target_valid
    .quantile(0.25)
)

q3 = (
    target_valid
    .quantile(0.75)
)

iqr = (
    q3 - q1
)

lower_bound = (
    q1
    - 1.5 * iqr
)

upper_bound = (
    q3
    + 1.5 * iqr
)

target_extremes = (
    df[
        (
            df[TARGET]
            < lower_bound
        )
        |
        (
            df[TARGET]
            > upper_bound
        )
    ]
    .copy()
)

print(
    f"Lower IQR bound: "
    f"{lower_bound:.2f}"
)

print(
    f"Upper IQR bound: "
    f"{upper_bound:.2f}"
)

print(
    f"Potential target extreme rows: "
    f"{len(target_extremes)}"
)

if not target_extremes.empty:

    extreme_columns = [
        "District",
        "Year",
        "Month",
        TARGET
    ]

    print(
        target_extremes[
            extreme_columns
        ]
        .sort_values(
            TARGET,
            ascending=False
        )
        .to_string(index=False)
    )

    target_extremes[
        extreme_columns
    ].to_csv(
        REPORT_DIR
        / "eda_target_extreme_rows.csv",
        index=False
    )


print(
    "\nNOTE: These values are retained."
)

print(
    "IQR is used only as an exploratory "
    "screening method."
)


# ============================================================
# 21. SOURCE-CORRECTED VARIABLE SUMMARY
# ============================================================

print("\n" + "-" * 85)
print("13. SOURCE-CORRECTED VARIABLE SUMMARY")
print("-" * 85)

source_corrected_columns = [
    "Triposha_Packets_Distributed",
    "Nutrition_Programmes_Conducted",
    "Field_Nutrition_Clinics_Available",
    "Hospital_Nutrition_Clinics_Available",
    "Low_Birth_Weight_Cases"
]

source_summary_results = []

for column in source_corrected_columns:

    if column not in df.columns:
        continue

    source_summary_results.append({

        "Variable":
            column,

        "Available_Count":
            df[column]
            .notna()
            .sum(),

        "Missing_Count":
            df[column]
            .isna()
            .sum(),

        "Mean":
            df[column]
            .mean(),

        "Median":
            df[column]
            .median(),

        "Minimum":
            df[column]
            .min(),

        "Maximum":
            df[column]
            .max()
    })

source_summary_df = pd.DataFrame(
    source_summary_results
)

print(
    source_summary_df
    .to_string(index=False)
)

source_summary_df.to_csv(
    REPORT_DIR
    / "eda_source_corrected_variable_summary.csv",
    index=False
)


# ============================================================
# 22. FINAL EDA SUMMARY
# ============================================================

print("\n" + "=" * 85)
print("EDA SUMMARY")
print("=" * 85)

print(
    f"Rows analysed               : "
    f"{len(df)}"
)

print(
    f"Districts analysed          : "
    f"{df['District'].nunique()}"
)

print(
    f"Years analysed              : "
    f"{df['Year'].nunique()}"
)

print(
    f"Target observations         : "
    f"{df[TARGET].notna().sum()}"
)

print(
    f"Missing target values       : "
    f"{df[TARGET].isna().sum()}"
)

print(
    f"Target mean                 : "
    f"{df[TARGET].mean():.2f}"
)

print(
    f"Target median               : "
    f"{df[TARGET].median():.2f}"
)

print(
    f"Target minimum              : "
    f"{df[TARGET].min()}"
)

print(
    f"Target maximum              : "
    f"{df[TARGET].max()}"
)

print(
    f"Potential target extremes   : "
    f"{len(target_extremes)}"
)

print(
    f"Variables with missing data : "
    f"{len(missing_summary)}"
)


print(
    "\nEDA outputs include:"
)

print(
    "- Target distribution"
)

print(
    "- Yearly temporal trend"
)

print(
    "- Monthly seasonal pattern"
)

print(
    "- District-level differences"
)

print(
    "- District-year patterns"
)

print(
    "- Numerical correlations"
)

print(
    "- Direct indicator relationships"
)

print(
    "- Overall monthly time-series trend"
)

print(
    "- 12-month rolling trend"
)

print(
    "- Missingness analysis"
)

print(
    "- Extreme-value review"
)


print(
    "\nIMPORTANT:"
)

print(
    "EDA findings describe patterns and "
    "associations only."
)

print(
    "Correlation does not prove causation."
)

print(
    "No feature is selected only because "
    "it has high correlation."
)

print(
    "No model selection is performed "
    "during this EDA step."
)


# ============================================================
# 23. COMPLETE
# ============================================================

print("\nReports saved to:")
print(REPORT_DIR)

print("\nFigures saved to:")
print(FIGURE_DIR)

print(
    "\nSTEP 05 - EXPLORATORY DATA ANALYSIS COMPLETE"
)

print("=" * 85)