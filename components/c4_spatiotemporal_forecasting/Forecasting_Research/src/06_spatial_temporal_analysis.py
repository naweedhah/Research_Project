# ============================================================
# STEP 06 - SPATIAL / DISTRICT & TEMPORAL ANALYSIS
# Childhood Malnutrition Forecasting Research
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# 1. PROJECT PATHS
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
# 2. LOAD DATA
# ============================================================

print("\n" + "=" * 90)
print("STEP 06 - SPATIAL / DISTRICT & TEMPORAL ANALYSIS")
print("=" * 90)

try:

    df = pd.read_csv(DATA_PATH)

    print("\nDataset loaded successfully.")
    print(f"Dataset location: {DATA_PATH}")

except FileNotFoundError:

    print("\nERROR: Preprocessed dataset not found.")
    print(f"Expected path: {DATA_PATH}")

    raise


# ============================================================
# 3. PREPARE DATE
# ============================================================

print("\n" + "-" * 90)
print("1. DATE PREPARATION")
print("-" * 90)

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)

df = (
    df
    .sort_values(
        [
            "District",
            "Date"
        ]
    )
    .reset_index(drop=True)
)

print(
    f"Date range: "
    f"{df['Date'].min().date()} "
    f"to "
    f"{df['Date'].max().date()}"
)

print(
    f"Districts: "
    f"{df['District'].nunique()}"
)


# ============================================================
# 4. REQUIRED COLUMN CHECK
# ============================================================

print("\n" + "-" * 90)
print("2. REQUIRED COLUMN CHECK")
print("-" * 90)

TARGET = "Malnutrition_Cases"

required_columns = [
    "District",
    "Year",
    "Month",
    "Date",
    TARGET,
    "Under 5 Population"
]

missing_required = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_required:

    raise ValueError(
        "Required columns missing: "
        + ", ".join(missing_required)
    )

for column in required_columns:

    print(f"[FOUND] {column}")


# ============================================================
# 5. DISTRICT TARGET SUMMARY
# ============================================================

print("\n" + "-" * 90)
print("3. DISTRICT TARGET SUMMARY")
print("-" * 90)

district_summary = (
    df
    .groupby("District")[TARGET]
    .agg(
        Available_Observations="count",
        Missing_Observations=lambda x:
            int(x.isna().sum()),
        Mean_Cases="mean",
        Median_Cases="median",
        Min_Cases="min",
        Max_Cases="max",
        SD_Cases="std"
    )
    .reset_index()
)

district_summary[
    "CV_Percentage"
] = (
    district_summary["SD_Cases"]
    /
    district_summary["Mean_Cases"]
    * 100
)

district_summary = (
    district_summary
    .sort_values(
        "Mean_Cases",
        ascending=False
    )
)

print(
    district_summary
    .round(2)
    .to_string(index=False)
)

district_summary.to_csv(
    REPORT_DIR
    / "06_district_target_summary.csv",
    index=False
)


# ============================================================
# 6. CREATE POPULATION-NORMALIZED EXPLORATORY RATE
# ============================================================

print("\n" + "-" * 90)
print("4. POPULATION-NORMALIZED MALNUTRITION RATE")
print("-" * 90)

# Exploratory indicator only:
# Malnutrition cases per 1,000 children under age 5.
#
# This does NOT replace the forecasting target.

valid_population = (
    df["Under 5 Population"] > 0
)

df[
    "Malnutrition_Rate_per_1000_U5"
] = np.nan

df.loc[
    valid_population,
    "Malnutrition_Rate_per_1000_U5"
] = (
    df.loc[
        valid_population,
        TARGET
    ]
    /
    df.loc[
        valid_population,
        "Under 5 Population"
    ]
    * 1000
)

rate_summary = (
    df
    .groupby("District")[
        "Malnutrition_Rate_per_1000_U5"
    ]
    .agg(
        Available_Observations="count",
        Mean_Rate="mean",
        Median_Rate="median",
        Min_Rate="min",
        Max_Rate="max",
        SD_Rate="std"
    )
    .reset_index()
    .sort_values(
        "Mean_Rate",
        ascending=False
    )
)

print(
    rate_summary
    .round(2)
    .to_string(index=False)
)

rate_summary.to_csv(
    REPORT_DIR
    / "06_district_malnutrition_rate_per_1000.csv",
    index=False
)

print(
    "\nIMPORTANT:"
)

print(
    "The rate is used only for exploratory "
    "district comparison."
)

print(
    "Malnutrition_Cases remains the main "
    "forecasting target."
)


# ============================================================
# 7. DISTRICT RATE FIGURE
# ============================================================

rate_plot = (
    rate_summary
    .sort_values(
        "Mean_Rate",
        ascending=True
    )
)

plt.figure(
    figsize=(10, 9)
)

plt.barh(
    rate_plot["District"],
    rate_plot["Mean_Rate"]
)

plt.title(
    "Mean Malnutrition Cases per 1,000 Under-5 Children"
)

plt.xlabel(
    "Cases per 1,000 Under-5 Children"
)

plt.ylabel(
    "District"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "06_district_rate_per_1000.png",
    dpi=300
)

plt.close()


# ============================================================
# 8. DISTRICT TEMPORAL TREND SLOPES
# ============================================================

print("\n" + "-" * 90)
print("5. DISTRICT TEMPORAL TREND ANALYSIS")
print("-" * 90)

trend_results = []

start_date = df["Date"].min()

df[
    "Month_Index"
] = (
    (
        df["Date"].dt.year
        - start_date.year
    )
    * 12
    +
    (
        df["Date"].dt.month
        - start_date.month
    )
)

for district, group in df.groupby("District"):

    valid = (
        group[
            [
                "Month_Index",
                TARGET
            ]
        ]
        .dropna()
    )

    if len(valid) >= 2:

        slope, intercept = np.polyfit(
            valid["Month_Index"],
            valid[TARGET],
            1
        )

        annualized_slope = (
            slope * 12
        )

    else:

        slope = np.nan
        annualized_slope = np.nan

    trend_results.append({

        "District":
            district,

        "Available_Observations":
            len(valid),

        "Monthly_Linear_Slope":
            slope,

        "Approx_Annual_Change":
            annualized_slope
    })

trend_df = pd.DataFrame(
    trend_results
)

trend_df = (
    trend_df
    .sort_values(
        "Approx_Annual_Change"
    )
)

print(
    trend_df
    .round(3)
    .to_string(index=False)
)

trend_df.to_csv(
    REPORT_DIR
    / "06_district_temporal_trend_slopes.csv",
    index=False
)

print(
    "\nNOTE:"
)

print(
    "Trend slope is descriptive only."
)

print(
    "It does not prove that the trend will "
    "continue into the future."
)


# ============================================================
# 9. DISTRICT TREND SLOPE FIGURE
# ============================================================

trend_plot = (
    trend_df
    .sort_values(
        "Approx_Annual_Change",
        ascending=True
    )
)

plt.figure(
    figsize=(10, 9)
)

plt.barh(
    trend_plot["District"],
    trend_plot[
        "Approx_Annual_Change"
    ]
)

plt.axvline(
    0,
    linewidth=1
)

plt.title(
    "Approximate Annual Target Trend by District"
)

plt.xlabel(
    "Estimated Change in Cases per Year"
)

plt.ylabel(
    "District"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "06_district_temporal_slopes.png",
    dpi=300
)

plt.close()


# ============================================================
# 10. YEARLY DISTRICT MEANS
# ============================================================

print("\n" + "-" * 90)
print("6. DISTRICT-YEAR TEMPORAL MATRIX")
print("-" * 90)

district_year_mean = (
    df
    .groupby(
        [
            "District",
            "Year"
        ]
    )[TARGET]
    .mean()
    .reset_index(
        name="Mean_Malnutrition_Cases"
    )
)

district_year_mean.to_csv(
    REPORT_DIR
    / "06_district_year_mean.csv",
    index=False
)

print(
    f"District-year combinations: "
    f"{len(district_year_mean)}"
)


# ============================================================
# 11. DISTRICT YEAR HEATMAP
# ============================================================

heatmap_data = (
    district_year_mean
    .pivot(
        index="District",
        columns="Year",
        values="Mean_Malnutrition_Cases"
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
    "District-Level Malnutrition Pattern Across Years"
)

plt.xlabel("Year")

plt.ylabel("District")

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "06_district_year_temporal_heatmap.png",
    dpi=300
)

plt.close()


# ============================================================
# 12. MONTHLY SEASONAL PATTERN
# ============================================================

print("\n" + "-" * 90)
print("7. OVERALL MONTHLY SEASONAL PATTERN")
print("-" * 90)

monthly_pattern = (
    df
    .groupby("Month")[TARGET]
    .agg(
        Mean="mean",
        Median="median",
        SD="std",
        Available_Observations="count"
    )
    .reset_index()
)

overall_target_mean = (
    df[TARGET]
    .mean()
)

monthly_pattern[
    "Seasonal_Index"
] = (
    monthly_pattern["Mean"]
    /
    overall_target_mean
)

print(
    monthly_pattern
    .round(3)
    .to_string(index=False)
)

monthly_pattern.to_csv(
    REPORT_DIR
    / "06_monthly_seasonal_pattern.csv",
    index=False
)


# ============================================================
# 13. MONTHLY SEASONAL INDEX FIGURE
# ============================================================

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    monthly_pattern["Month"],
    monthly_pattern["Seasonal_Index"],
    marker="o"
)

plt.axhline(
    1.0,
    linewidth=1
)

plt.xticks(
    range(1, 13)
)

plt.title(
    "Exploratory Monthly Seasonal Index"
)

plt.xlabel("Month")

plt.ylabel(
    "Seasonal Index"
)

plt.grid(
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "06_monthly_seasonal_index.png",
    dpi=300
)

plt.close()


# ============================================================
# 14. DISTRICT-MONTH SEASONAL PATTERN
# ============================================================

print("\n" + "-" * 90)
print("8. DISTRICT-MONTH SEASONAL ANALYSIS")
print("-" * 90)

district_month = (
    df
    .groupby(
        [
            "District",
            "Month"
        ]
    )[TARGET]
    .agg(
        Mean="mean",
        Median="median",
        Available_Observations="count"
    )
    .reset_index()
)

district_month.to_csv(
    REPORT_DIR
    / "06_district_month_seasonality.csv",
    index=False
)

print(
    f"District-month combinations: "
    f"{len(district_month)}"
)


# ============================================================
# 15. DISTRICT-MONTH SEASONAL HEATMAP
# ============================================================

district_month_heatmap = (
    district_month
    .pivot(
        index="District",
        columns="Month",
        values="Mean"
    )
)

plt.figure(
    figsize=(12, 10)
)

image = plt.imshow(
    district_month_heatmap,
    aspect="auto"
)

plt.colorbar(
    image,
    label="Mean Malnutrition Cases"
)

plt.xticks(
    range(12),
    range(1, 13)
)

plt.yticks(
    range(
        len(
            district_month_heatmap.index
        )
    ),
    district_month_heatmap.index
)

plt.title(
    "District-Level Monthly Malnutrition Pattern"
)

plt.xlabel("Month")

plt.ylabel("District")

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "06_district_month_seasonality_heatmap.png",
    dpi=300
)

plt.close()


# ============================================================
# 16. CREATE TARGET LAGS FOR ANALYSIS
# ============================================================

print("\n" + "-" * 90)
print("9. TARGET LAG RELATIONSHIP ANALYSIS")
print("-" * 90)

lag_months = [
    1,
    3,
    6,
    12
]

for lag in lag_months:

    df[
        f"Target_Lag_{lag}"
    ] = (
        df
        .groupby("District")[TARGET]
        .shift(lag)
    )


# ============================================================
# 17. POOLED LAG CORRELATIONS
# ============================================================

pooled_lag_results = []

for lag in lag_months:

    lag_column = (
        f"Target_Lag_{lag}"
    )

    valid = (
        df[
            [
                TARGET,
                lag_column
            ]
        ]
        .dropna()
    )

    correlation = (
        valid[TARGET]
        .corr(
            valid[lag_column]
        )
    )

    pooled_lag_results.append({

        "Lag_Months":
            lag,

        "Valid_Pairs":
            len(valid),

        "Pooled_Correlation":
            correlation
    })

pooled_lag_df = pd.DataFrame(
    pooled_lag_results
)

print("\nPooled lag correlations:")

print(
    pooled_lag_df
    .round(4)
    .to_string(index=False)
)

pooled_lag_df.to_csv(
    REPORT_DIR
    / "06_pooled_target_lag_correlations.csv",
    index=False
)


# ============================================================
# 18. DISTRICT-SPECIFIC LAG CORRELATIONS
# ============================================================

district_lag_results = []

for district, group in df.groupby("District"):

    for lag in lag_months:

        lag_column = (
            f"Target_Lag_{lag}"
        )

        valid = (
            group[
                [
                    TARGET,
                    lag_column
                ]
            ]
            .dropna()
        )

        if len(valid) >= 12:

            correlation = (
                valid[TARGET]
                .corr(
                    valid[
                        lag_column
                    ]
                )
            )

        else:

            correlation = np.nan

        district_lag_results.append({

            "District":
                district,

            "Lag_Months":
                lag,

            "Valid_Pairs":
                len(valid),

            "Correlation":
                correlation
        })

district_lag_df = pd.DataFrame(
    district_lag_results
)

district_lag_df.to_csv(
    REPORT_DIR
    / "06_district_target_lag_correlations.csv",
    index=False
)


lag_summary = (
    district_lag_df
    .groupby(
        "Lag_Months"
    )["Correlation"]
    .agg(
        Mean_District_Correlation="mean",
        Median_District_Correlation="median",
        Min_District_Correlation="min",
        Max_District_Correlation="max",
        Districts_Available="count"
    )
    .reset_index()
)

print(
    "\nDistrict-level lag correlation summary:"
)

print(
    lag_summary
    .round(4)
    .to_string(index=False)
)

lag_summary.to_csv(
    REPORT_DIR
    / "06_lag_correlation_summary.csv",
    index=False
)

print(
    "\nIMPORTANT:"
)

print(
    "Strong lag correlation suggests that "
    "historical target values may contain "
    "useful predictive information."
)

print(
    "This does NOT yet mean every lag will "
    "be selected as a final feature."
)


# ============================================================
# 19. LAG CORRELATION FIGURE
# ============================================================

plt.figure(
    figsize=(8, 6)
)

plt.plot(
    lag_summary["Lag_Months"],
    lag_summary[
        "Median_District_Correlation"
    ],
    marker="o"
)

plt.xticks(
    lag_months
)

plt.title(
    "Median District-Level Target Lag Correlation"
)

plt.xlabel(
    "Lag in Months"
)

plt.ylabel(
    "Median Pearson Correlation"
)

plt.grid(
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "06_target_lag_correlations.png",
    dpi=300
)

plt.close()


# ============================================================
# 20. YEAR-OVER-YEAR CHANGE
# ============================================================

print("\n" + "-" * 90)
print("10. YEAR-OVER-YEAR TARGET CHANGE")
print("-" * 90)

df[
    "Target_Lag_12_For_YoY"
] = (
    df
    .groupby("District")[TARGET]
    .shift(12)
)


# Signed change:
# Positive = target increased compared with same month last year
# Negative = target decreased compared with same month last year

df[
    "YoY_Change"
] = (
    df[TARGET]
    -
    df[
        "Target_Lag_12_For_YoY"
    ]
)


# Absolute magnitude of the change
# This value can never be negative

df[
    "YoY_Absolute_Change"
] = (
    df[
        "YoY_Change"
    ]
    .abs()
)


# Percentage change requires a valid previous-year value.
# Previous value must also be greater than zero to avoid
# division by zero.

valid_yoy_denominator = (
    df[
        "Target_Lag_12_For_YoY"
    ].notna()
    &
    (
        df[
            "Target_Lag_12_For_YoY"
        ] > 0
    )
)


df[
    "YoY_Percentage_Change"
] = np.nan


df.loc[
    valid_yoy_denominator,
    "YoY_Percentage_Change"
] = (
    df.loc[
        valid_yoy_denominator,
        "YoY_Change"
    ]
    /
    df.loc[
        valid_yoy_denominator,
        "Target_Lag_12_For_YoY"
    ]
    * 100
)


yoy_summary = pd.DataFrame({

    "Metric": [
        "Available YoY Comparisons",
        "Mean Signed YoY Change",
        "Median Signed YoY Change",
        "Mean Absolute YoY Change",
        "Median Absolute YoY Change",
        "Mean YoY Percentage Change",
        "Median YoY Percentage Change"
    ],

    "Value": [
        df[
            "YoY_Change"
        ].notna().sum(),

        df[
            "YoY_Change"
        ].mean(),

        df[
            "YoY_Change"
        ].median(),

        df[
            "YoY_Absolute_Change"
        ].mean(),

        df[
            "YoY_Absolute_Change"
        ].median(),

        df[
            "YoY_Percentage_Change"
        ].mean(),

        df[
            "YoY_Percentage_Change"
        ].median()
    ]
})


print(
    yoy_summary
    .round(3)
    .to_string(index=False)
)


yoy_summary.to_csv(
    REPORT_DIR
    / "06_year_over_year_change_summary.csv",
    index=False
)


# ============================================================
# 21. DISTRICT VOLATILITY
# ============================================================

print("\n" + "-" * 90)
print("11. DISTRICT TEMPORAL VARIABILITY")
print("-" * 90)

district_variability = (
    df
    .groupby("District")[TARGET]
    .agg(
        Mean="mean",
        Standard_Deviation="std",
        Minimum="min",
        Maximum="max"
    )
    .reset_index()
)

district_variability[
    "Range"
] = (
    district_variability["Maximum"]
    -
    district_variability["Minimum"]
)

district_variability[
    "CV_Percentage"
] = (
    district_variability[
        "Standard_Deviation"
    ]
    /
    district_variability["Mean"]
    * 100
)

district_variability = (
    district_variability
    .sort_values(
        "CV_Percentage",
        ascending=False
    )
)

print(
    district_variability
    .round(2)
    .to_string(index=False)
)

district_variability.to_csv(
    REPORT_DIR
    / "06_district_temporal_variability.csv",
    index=False
)


# ============================================================
# 22. OVERALL MONTHLY TEMPORAL SERIES
# ============================================================

print("\n" + "-" * 90)
print("12. OVERALL MONTHLY TEMPORAL SERIES")
print("-" * 90)

overall_monthly = (
    df
    .groupby("Date")[TARGET]
    .agg(
        Mean_Cases="mean",
        Median_Cases="median",
        Total_Available_Districts="count"
    )
    .reset_index()
)

overall_monthly.to_csv(
    REPORT_DIR
    / "06_overall_monthly_temporal_series.csv",
    index=False
)


plt.figure(
    figsize=(14, 6)
)

plt.plot(
    overall_monthly["Date"],
    overall_monthly["Mean_Cases"]
)

plt.title(
    "Overall Monthly Malnutrition Pattern Across Districts"
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
    / "06_overall_monthly_temporal_pattern.png",
    dpi=300
)

plt.close()


# ============================================================
# 23. SAVE ANALYSIS DATASET
# ============================================================

# This dataset contains exploratory derived variables.
# It does NOT replace the preprocessing base dataset.

ANALYSIS_OUTPUT = (
    BASE_DIR
    / "data"
    / "processed"
    / "malnutrition_spatial_temporal_analysis.csv"
)

df.to_csv(
    ANALYSIS_OUTPUT,
    index=False
)

print(
    "\nExploratory analysis dataset saved to:"
)

print(
    ANALYSIS_OUTPUT
)


# ============================================================
# 24. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 90)
print("SPATIAL / DISTRICT & TEMPORAL ANALYSIS SUMMARY")
print("=" * 90)

print(
    f"Rows analysed                    : "
    f"{len(df)}"
)

print(
    f"Districts analysed               : "
    f"{df['District'].nunique()}"
)

print(
    f"Months in study period           : "
    f"{df['Date'].nunique()}"
)

print(
    f"Years                            : "
    f"{df['Year'].nunique()}"
)

print(
    f"Target observations available    : "
    f"{df[TARGET].notna().sum()}"
)

print(
    f"Target observations missing      : "
    f"{df[TARGET].isna().sum()}"
)

print(
    f"Lag periods investigated         : "
    f"{lag_months}"
)


print(
    "\nAnalyses completed:"
)

print(
    "- District-level target comparison"
)

print(
    "- Population-normalized rate comparison"
)

print(
    "- District temporal trend estimation"
)

print(
    "- District-year patterns"
)

print(
    "- Overall monthly seasonality"
)

print(
    "- District-specific seasonality"
)

print(
    "- 1, 3, 6 and 12-month lag relationships"
)

print(
    "- Year-over-year signed and absolute changes"
)

print(
    "- District temporal variability"
)


print(
    "\nIMPORTANT:"
)

print(
    "This step is exploratory."
)

print(
    "No district trend is assumed to continue "
    "into the future."
)

print(
    "No lag feature is automatically selected."
)

print(
    "No causal conclusions are made."
)

print(
    "Malnutrition_Rate_per_1000_U5 is an "
    "exploratory normalization and does not "
    "replace the original forecasting target."
)


# ============================================================
# 25. COMPLETE
# ============================================================

print("\nReports saved to:")
print(REPORT_DIR)

print("\nFigures saved to:")
print(FIGURE_DIR)

print(
    "\nSTEP 06 - SPATIAL / DISTRICT & "
    "TEMPORAL ANALYSIS COMPLETE"
)

print("=" * 90)