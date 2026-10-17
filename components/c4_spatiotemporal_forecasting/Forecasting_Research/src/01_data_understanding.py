# ============================================================
# STEP 01 - DATA UNDERSTANDING
# Childhood Malnutrition Forecasting Research
# Source-Corrected Dataset
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 1. DEFINE PROJECT PATHS
# ============================================================

# Main project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Updated source-corrected dataset
DATA_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "malnutrition_source_corrected_v2.csv"
)

# Folder used to save analysis reports
REPORT_DIR = BASE_DIR / "outputs" / "reports"

# Create the folder if it does not exist
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. LOAD DATASET
# ============================================================

print("\n" + "=" * 75)
print("STEP 01 - DATA UNDERSTANDING")
print("=" * 75)

try:

    df = pd.read_csv(DATA_PATH)

    print("\nDataset loaded successfully.")
    print(f"Dataset location: {DATA_PATH}")

except FileNotFoundError:

    print("\nERROR: Dataset was not found.")
    print(f"Expected location: {DATA_PATH}")

    raise


# ============================================================
# 3. DATASET SIZE
# ============================================================

print("\n" + "-" * 75)
print("1. DATASET SIZE")
print("-" * 75)

print(f"Number of rows    : {df.shape[0]}")
print(f"Number of columns : {df.shape[1]}")


# ============================================================
# 4. COLUMN NAMES
# ============================================================

print("\n" + "-" * 75)
print("2. COLUMN NAMES")
print("-" * 75)

for number, column in enumerate(df.columns, start=1):

    print(f"{number:02d}. {column}")


# ============================================================
# 5. VIEW FIRST AND LAST RECORDS
# ============================================================

print("\n" + "-" * 75)
print("3. FIRST 5 RECORDS")
print("-" * 75)

print(df.head())


print("\n" + "-" * 75)
print("4. LAST 5 RECORDS")
print("-" * 75)

print(df.tail())


# ============================================================
# 6. DATA TYPES
# ============================================================

print("\n" + "-" * 75)
print("5. DATA TYPES")
print("-" * 75)

print(df.dtypes)


# ============================================================
# 7. CHECK IMPORTANT RESEARCH COLUMNS
# ============================================================

print("\n" + "-" * 75)
print("6. IMPORTANT RESEARCH COLUMNS")
print("-" * 75)

important_columns = [
    "District",
    "Year",
    "Month",
    "Malnutrition_Cases"
]

for column in important_columns:

    if column in df.columns:

        print(f"[FOUND]   {column}")

    else:

        print(f"[MISSING] {column}")


# ============================================================
# 8. CHECK SOURCE-CORRECTED COLUMNS
# ============================================================

print("\n" + "-" * 75)
print("7. SOURCE-CORRECTED COLUMNS")
print("-" * 75)

source_corrected_columns = [
    "Triposha_Packets_Distributed",
    "Nutrition_Programmes_Conducted",
    "Field_Nutrition_Clinics_Available",
    "Hospital_Nutrition_Clinics_Available",
    "Low_Birth_Weight_Cases"
]

for column in source_corrected_columns:

    if column in df.columns:

        missing_count = df[column].isna().sum()

        print(
            f"[FOUND] {column}"
            f" | Missing Values = {missing_count}"
        )

    else:

        print(
            f"[MISSING COLUMN] {column}"
        )


# ============================================================
# 9. DISTRICT INFORMATION
# ============================================================

print("\n" + "-" * 75)
print("8. DISTRICT INFORMATION")
print("-" * 75)

if "District" in df.columns:

    district_count = (
        df["District"]
        .nunique(dropna=True)
    )

    print(
        f"Number of unique districts: "
        f"{district_count}"
    )

    print("\nDistrict list:")

    districts = sorted(
        df["District"]
        .dropna()
        .astype(str)
        .unique()
    )

    for district in districts:

        print(f"- {district}")

else:

    print("District column was not found.")


# ============================================================
# 10. YEAR COVERAGE
# ============================================================

print("\n" + "-" * 75)
print("9. YEAR COVERAGE")
print("-" * 75)

if "Year" in df.columns:

    print(
        f"Minimum year: "
        f"{df['Year'].min()}"
    )

    print(
        f"Maximum year: "
        f"{df['Year'].max()}"
    )

    print("\nRows per year:")

    print(
        df["Year"]
        .value_counts()
        .sort_index()
    )

else:

    print("Year column was not found.")


# ============================================================
# 11. MONTH COVERAGE
# ============================================================

print("\n" + "-" * 75)
print("10. MONTH INFORMATION")
print("-" * 75)

if "Month" in df.columns:

    month_count = (
        df["Month"]
        .nunique(dropna=True)
    )

    print(
        f"Number of unique months: "
        f"{month_count}"
    )

    print("\nMonth values:")

    print(
        sorted(
            df["Month"]
            .dropna()
            .unique()
        )
    )

else:

    print("Month column was not found.")


# ============================================================
# 12. DISTRICT-YEAR MONTHLY COVERAGE
# ============================================================

print("\n" + "-" * 75)
print("11. DISTRICT-YEAR COVERAGE")
print("-" * 75)

time_columns = {
    "District",
    "Year",
    "Month"
}

if time_columns.issubset(df.columns):

    district_year_counts = (
        df
        .groupby(
            ["District", "Year"]
        )
        .size()
        .reset_index(
            name="Number_of_Monthly_Rows"
        )
    )

    incomplete_district_years = (
        district_year_counts[
            district_year_counts[
                "Number_of_Monthly_Rows"
            ] != 12
        ]
    )

    print(
        "District-years without exactly "
        f"12 monthly rows: "
        f"{len(incomplete_district_years)}"
    )

    if not incomplete_district_years.empty:

        print(
            incomplete_district_years
            .to_string(index=False)
        )

        incomplete_district_years.to_csv(
            REPORT_DIR
            / "incomplete_district_years.csv",
            index=False
        )

else:

    print(
        "District, Year, or Month column "
        "is missing."
    )


# ============================================================
# 13. DUPLICATE DISTRICT-YEAR-MONTH CHECK
# ============================================================

print("\n" + "-" * 75)
print("12. DUPLICATE DISTRICT-MONTH CHECK")
print("-" * 75)

if time_columns.issubset(df.columns):

    duplicate_mask = df.duplicated(
        subset=[
            "District",
            "Year",
            "Month"
        ],
        keep=False
    )

    duplicate_count = (
        duplicate_mask.sum()
    )

    print(
        "Duplicate District-Year-Month rows: "
        f"{duplicate_count}"
    )

    if duplicate_count > 0:

        duplicate_rows = (
            df.loc[duplicate_mask]
            .sort_values(
                [
                    "District",
                    "Year",
                    "Month"
                ]
            )
        )

        duplicate_rows.to_csv(
            REPORT_DIR
            / "duplicate_records.csv",
            index=False
        )


# ============================================================
# 14. MISSING VALUE OVERVIEW
# ============================================================

print("\n" + "-" * 75)
print("13. MISSING VALUE OVERVIEW")
print("-" * 75)

missing_report = pd.DataFrame({

    "Column":
        df.columns,

    "Missing_Count":
        df.isna().sum().values,

    "Missing_Percentage":
        (
            df.isna().mean()
            * 100
        ).round(2).values
})


missing_report = (
    missing_report
    .sort_values(
        by="Missing_Count",
        ascending=False
    )
)


print(
    missing_report
    .to_string(index=False)
)


missing_report.to_csv(
    REPORT_DIR
    / "missing_value_summary.csv",
    index=False
)


# ============================================================
# 15. COLUMNS WITH MISSING VALUES
# ============================================================

print("\n" + "-" * 75)
print("14. COLUMNS WITH MISSING VALUES")
print("-" * 75)

columns_with_missing = (
    missing_report[
        missing_report[
            "Missing_Count"
        ] > 0
    ]
)

if not columns_with_missing.empty:

    print(
        columns_with_missing
        .to_string(index=False)
    )

else:

    print(
        "No missing values were detected."
    )


# ============================================================
# 16. NUMERICAL DATA SUMMARY
# ============================================================

print("\n" + "-" * 75)
print("15. NUMERICAL DATA SUMMARY")
print("-" * 75)

numeric_columns = (
    df
    .select_dtypes(
        include=np.number
    )
    .columns
    .tolist()
)

print(
    f"Number of numerical columns: "
    f"{len(numeric_columns)}"
)

if numeric_columns:

    numerical_summary = (
        df[numeric_columns]
        .describe()
        .T
    )

    print(numerical_summary)

    numerical_summary.to_csv(
        REPORT_DIR
        / "numerical_summary.csv"
    )

else:

    print(
        "No numerical columns were found."
    )


# ============================================================
# 17. CATEGORICAL DATA SUMMARY
# ============================================================

print("\n" + "-" * 75)
print("16. CATEGORICAL DATA SUMMARY")
print("-" * 75)

# Select non-numerical columns safely
categorical_columns = [
    column
    for column in df.columns
    if not pd.api.types.is_numeric_dtype(
        df[column]
    )
]

print(
    f"Number of categorical columns: "
    f"{len(categorical_columns)}"
)

for column in categorical_columns:

    print(
        f"{column}: "
        f"{df[column].nunique(dropna=True)} "
        "unique values"
    )


# ============================================================
# 18. TARGET VARIABLE BASIC ANALYSIS
# ============================================================

print("\n" + "-" * 75)
print("17. TARGET VARIABLE - MALNUTRITION CASES")
print("-" * 75)

TARGET = "Malnutrition_Cases"

if TARGET in df.columns:

    print(
        f"Total rows       : "
        f"{len(df)}"
    )

    print(
        f"Available values : "
        f"{df[TARGET].notna().sum()}"
    )

    print(
        f"Missing values   : "
        f"{df[TARGET].isna().sum()}"
    )

    print(
        f"Minimum          : "
        f"{df[TARGET].min()}"
    )

    print(
        f"Maximum          : "
        f"{df[TARGET].max()}"
    )

    print(
        f"Mean             : "
        f"{df[TARGET].mean():.2f}"
    )

    print(
        f"Median           : "
        f"{df[TARGET].median():.2f}"
    )

    print(
        f"Standard Dev.    : "
        f"{df[TARGET].std():.2f}"
    )

    print(
        f"Unique values    : "
        f"{df[TARGET].nunique(dropna=True)}"
    )

else:

    print(
        f"Target column '{TARGET}' "
        "was not found."
    )


# ============================================================
# 19. NEGATIVE VALUE SCREENING
# ============================================================

print("\n" + "-" * 75)
print("18. NEGATIVE VALUE SCREENING")
print("-" * 75)

negative_results = []

for column in numeric_columns:

    negative_count = (
        df[column] < 0
    ).sum()

    if negative_count > 0:

        negative_results.append({

            "Column":
                column,

            "Negative_Count":
                negative_count
        })


if negative_results:

    negative_df = pd.DataFrame(
        negative_results
    )

    print(
        negative_df
        .to_string(index=False)
    )

    negative_df.to_csv(
        REPORT_DIR
        / "negative_value_summary.csv",
        index=False
    )

else:

    print(
        "No negative numerical values detected."
    )


# ============================================================
# 20. COMPLETE COLUMN PROFILE
# ============================================================

print("\n" + "-" * 75)
print("19. COMPLETE COLUMN PROFILE")
print("-" * 75)

column_profile = pd.DataFrame({

    "Column":
        df.columns,

    "Data_Type":
        df.dtypes.astype(str).values,

    "Non_Null_Count":
        df.notna().sum().values,

    "Missing_Count":
        df.isna().sum().values,

    "Missing_Percentage":
        (
            df.isna().mean()
            * 100
        ).round(2).values,

    "Unique_Values": [
        df[column]
        .nunique(dropna=True)
        for column in df.columns
    ]
})


print(
    column_profile
    .to_string(index=False)
)


column_profile.to_csv(
    REPORT_DIR
    / "column_profile.csv",
    index=False
)


# ============================================================
# 21. SOURCE-CORRECTED DATA COMPLETENESS
# ============================================================

print("\n" + "-" * 75)
print("20. SOURCE-CORRECTED DATA COMPLETENESS")
print("-" * 75)

source_completion_results = []

for column in source_corrected_columns:

    if column in df.columns:

        available_count = (
            df[column]
            .notna()
            .sum()
        )

        missing_count = (
            df[column]
            .isna()
            .sum()
        )

        completeness_percentage = (
            df[column]
            .notna()
            .mean()
            * 100
        )

        source_completion_results.append({

            "Column":
                column,

            "Available_Count":
                available_count,

            "Missing_Count":
                missing_count,

            "Completeness_Percentage":
                round(
                    completeness_percentage,
                    2
                )
        })


source_completion_df = pd.DataFrame(
    source_completion_results
)

if not source_completion_df.empty:

    print(
        source_completion_df
        .to_string(index=False)
    )

    source_completion_df.to_csv(
        REPORT_DIR
        / "source_corrected_data_completeness.csv",
        index=False
    )


# ============================================================
# 22. TOTAL DATA COMPLETENESS
# ============================================================

print("\n" + "-" * 75)
print("21. OVERALL DATA COMPLETENESS")
print("-" * 75)

total_cells = (
    df.shape[0]
    * df.shape[1]
)

missing_cells = (
    df.isna()
    .sum()
    .sum()
)

available_cells = (
    total_cells
    - missing_cells
)

overall_completeness = (
    available_cells
    / total_cells
    * 100
)

print(
    f"Total cells       : "
    f"{total_cells}"
)

print(
    f"Available cells   : "
    f"{available_cells}"
)

print(
    f"Missing cells     : "
    f"{missing_cells}"
)

print(
    f"Data completeness : "
    f"{overall_completeness:.2f}%"
)


# ============================================================
# 23. FINAL DATA UNDERSTANDING SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("DATA UNDERSTANDING SUMMARY")
print("=" * 75)

print(
    f"Total rows          : "
    f"{df.shape[0]}"
)

print(
    f"Total columns       : "
    f"{df.shape[1]}"
)


if "District" in df.columns:

    print(
        f"Districts           : "
        f"{df['District'].nunique()}"
    )


if "Year" in df.columns:

    print(
        f"Year coverage       : "
        f"{df['Year'].min()} - "
        f"{df['Year'].max()}"
    )


if "Month" in df.columns:

    print(
        f"Months              : "
        f"{df['Month'].nunique()}"
    )


if time_columns.issubset(df.columns):

    duplicate_count = (
        df.duplicated(
            subset=[
                "District",
                "Year",
                "Month"
            ]
        )
        .sum()
    )

    print(
        f"Duplicate time rows : "
        f"{duplicate_count}"
    )


print(
    f"Total missing cells : "
    f"{missing_cells}"
)


print(
    f"Overall completeness: "
    f"{overall_completeness:.2f}%"
)


if TARGET in df.columns:

    print(
        f"Missing target      : "
        f"{df[TARGET].isna().sum()}"
    )


print("\nSource-corrected variables:")

for column in source_corrected_columns:

    if column in df.columns:

        print(
            f"- {column}: "
            f"{df[column].isna().sum()} "
            "missing"
        )


# ============================================================
# 24. COMPLETE
# ============================================================

print("\nReports saved to:")
print(REPORT_DIR)

print(
    "\nSTEP 01 - DATA UNDERSTANDING COMPLETE"
)

print("=" * 75)