# ============================================================
# STEP 04 - SAFE PREPROCESSING
# Childhood Malnutrition Forecasting Research
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 1. DEFINE PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "malnutrition_source_corrected_v2.csv"
)

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

REPORT_DIR = (
    BASE_DIR
    / "outputs"
    / "reports"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_PATH = (
    PROCESSED_DIR
    / "malnutrition_preprocessed_base.csv"
)


# ============================================================
# 2. LOAD DATASET
# ============================================================

print("\n" + "=" * 85)
print("STEP 04 - SAFE PREPROCESSING")
print("=" * 85)

try:

    df = pd.read_csv(INPUT_PATH)

    print("\nDataset loaded successfully.")
    print(f"Input dataset: {INPUT_PATH}")

except FileNotFoundError:

    print("\nERROR: Dataset was not found.")
    print(f"Expected path: {INPUT_PATH}")

    raise


# Keep copy for comparison
original_df = df.copy()


# ============================================================
# 3. INITIAL DATASET INFORMATION
# ============================================================

print("\n" + "-" * 85)
print("1. INITIAL DATASET INFORMATION")
print("-" * 85)

print(
    f"Rows             : "
    f"{df.shape[0]}"
)

print(
    f"Columns          : "
    f"{df.shape[1]}"
)

print(
    f"Missing cells    : "
    f"{df.isna().sum().sum()}"
)


# ============================================================
# 4. CLEAN COLUMN NAMES
# ============================================================

print("\n" + "-" * 85)
print("2. CLEAN COLUMN NAMES")
print("-" * 85)

original_columns = df.columns.tolist()

df.columns = (
    df.columns
    .str.strip()
)

renamed_columns = []

for old_name, new_name in zip(
    original_columns,
    df.columns
):

    if old_name != new_name:

        renamed_columns.append({
            "Original_Name":
                old_name,

            "Cleaned_Name":
                new_name
        })


if renamed_columns:

    renamed_df = pd.DataFrame(
        renamed_columns
    )

    print(
        renamed_df
        .to_string(index=False)
    )

    renamed_df.to_csv(
        REPORT_DIR
        / "preprocessing_column_name_changes.csv",
        index=False
    )

else:

    print(
        "No column-name cleaning was required."
    )


# ============================================================
# 5. CLEAN STRING VALUES
# ============================================================

print("\n" + "-" * 85)
print("3. CLEAN STRING VALUES")
print("-" * 85)

string_columns = [
    column
    for column in df.columns
    if (
        pd.api.types.is_object_dtype(
            df[column]
        )
        or
        pd.api.types.is_string_dtype(
            df[column]
        )
    )
]


for column in string_columns:

    df[column] = (
        df[column]
        .astype("string")
        .str.strip()
    )


print(
    "String values were trimmed "
    "for leading/trailing spaces."
)

print(
    f"String columns processed: "
    f"{len(string_columns)}"
)


# ============================================================
# 6. BASIC REQUIRED COLUMN CHECK
# ============================================================

print("\n" + "-" * 85)
print("4. REQUIRED COLUMN CHECK")
print("-" * 85)

required_columns = [
    "District",
    "Year",
    "Month",
    "Malnutrition_Cases"
]

missing_required = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing_required:

    raise ValueError(
        "Required columns are missing: "
        + ", ".join(
            missing_required
        )
    )


for column in required_columns:

    print(
        f"[FOUND] {column}"
    )


# ============================================================
# 7. YEAR AND MONTH TYPE CHECK
# ============================================================

print("\n" + "-" * 85)
print("5. YEAR / MONTH VALIDATION")
print("-" * 85)


df["Year"] = pd.to_numeric(
    df["Year"],
    errors="coerce"
)

df["Month"] = pd.to_numeric(
    df["Month"],
    errors="coerce"
)


invalid_year_count = (
    df["Year"].isna().sum()
)

invalid_month_count = (
    (
        df["Month"].isna()
    )
    |
    (
        ~df["Month"].isin(
            range(1, 13)
        )
    )
).sum()


print(
    f"Invalid Year values  : "
    f"{invalid_year_count}"
)

print(
    f"Invalid Month values : "
    f"{invalid_month_count}"
)


if invalid_year_count > 0:

    raise ValueError(
        "Invalid Year values were detected."
    )


if invalid_month_count > 0:

    raise ValueError(
        "Invalid Month values were detected."
    )


df["Year"] = (
    df["Year"]
    .astype(int)
)

df["Month"] = (
    df["Month"]
    .astype(int)
)


# ============================================================
# 8. CREATE DATE COLUMN
# ============================================================

print("\n" + "-" * 85)
print("6. CREATE DATE COLUMN")
print("-" * 85)

df["Date"] = pd.to_datetime(
    dict(
        year=df["Year"],
        month=df["Month"],
        day=1
    ),
    errors="coerce"
)


invalid_date_count = (
    df["Date"]
    .isna()
    .sum()
)


print(
    f"Invalid generated dates: "
    f"{invalid_date_count}"
)


if invalid_date_count > 0:

    raise ValueError(
        "Date creation failed for some rows."
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
# 9. SORT DATA CHRONOLOGICALLY
# ============================================================

print("\n" + "-" * 85)
print("7. CHRONOLOGICAL SORTING")
print("-" * 85)

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
    "Dataset sorted by District and Date."
)


# ============================================================
# 10. DUPLICATE CHECK
# ============================================================

print("\n" + "-" * 85)
print("8. DUPLICATE CHECK")
print("-" * 85)

key_columns = [
    "District",
    "Year",
    "Month"
]


duplicate_count = (
    df.duplicated(
        subset=key_columns
    )
    .sum()
)


print(
    "Duplicate District-Year-Month rows: "
    f"{duplicate_count}"
)


if duplicate_count > 0:

    duplicate_rows = (
        df[
            df.duplicated(
                subset=key_columns,
                keep=False
            )
        ]
        .copy()
    )

    duplicate_rows.to_csv(
        REPORT_DIR
        / "preprocessing_duplicate_rows.csv",
        index=False
    )

    raise ValueError(
        "Duplicate time records detected. "
        "They were NOT automatically removed."
    )


# ============================================================
# 11. TARGET MISSING VALUE STATUS
# ============================================================

print("\n" + "-" * 85)
print("9. TARGET MISSING VALUE STATUS")
print("-" * 85)

TARGET = "Malnutrition_Cases"

target_missing_count = (
    df[TARGET]
    .isna()
    .sum()
)


print(
    f"Missing target values: "
    f"{target_missing_count}"
)


target_missing_rows = (
    df[
        df[TARGET].isna()
    ]
    .copy()
)


if not target_missing_rows.empty:

    target_missing_rows[
        [
            "District",
            "Year",
            "Month",
            "Date",
            TARGET
        ]
    ].to_csv(
        REPORT_DIR
        / "preprocessing_unresolved_target_missing.csv",
        index=False
    )


print(
    "Decision: Missing target values "
    "were NOT imputed."
)


# ============================================================
# 12. DIRECT MALNUTRITION INDICATOR STATUS
# ============================================================

print("\n" + "-" * 85)
print("10. DIRECT INDICATOR MISSING STATUS")
print("-" * 85)

direct_indicators = [
    "Underweight",
    "Wasting",
    "Stunting"
]


direct_indicator_results = []

for column in direct_indicators:

    if column in df.columns:

        direct_indicator_results.append({

            "Column":
                column,

            "Missing_Count":
                df[column]
                .isna()
                .sum(),

            "Missing_Percentage":
                round(
                    df[column]
                    .isna()
                    .mean()
                    * 100,
                    2
                ),

            "Treatment":
                "Preserved; no blind imputation"
        })


direct_indicator_df = pd.DataFrame(
    direct_indicator_results
)


print(
    direct_indicator_df
    .to_string(index=False)
)


direct_indicator_df.to_csv(
    REPORT_DIR
    / "preprocessing_direct_indicator_status.csv",
    index=False
)


# ============================================================
# 13. CLIMATE MISSING VALUE STATUS
# ============================================================

print("\n" + "-" * 85)
print("11. CLIMATE MISSING VALUE STATUS")
print("-" * 85)

climate_columns = [
    "ALLSKY_KT",
    "ALLSKY_SFC_SW_DWN",
    "CLRSKY_SFC_PAR_TOT",
    "CLRSKY_SFC_SW_DWN",
    "PRECTOTCORR",
    "RH2M",
    "T2M",
    "WS10M"
]


climate_results = []

for column in climate_columns:

    if column in df.columns:

        climate_results.append({

            "Column":
                column,

            "Missing_Count":
                df[column]
                .isna()
                .sum(),

            "Missing_Percentage":
                round(
                    df[column]
                    .isna()
                    .mean()
                    * 100,
                    2
                ),

            "Treatment":
                "Preserved for later source/spatial handling"
        })


climate_status_df = pd.DataFrame(
    climate_results
)


print(
    climate_status_df
    .to_string(index=False)
)


climate_status_df.to_csv(
    REPORT_DIR
    / "preprocessing_climate_missing_status.csv",
    index=False
)


# ============================================================
# 14. VITAMIN A QUALITY STATUS
# ============================================================

print("\n" + "-" * 85)
print("12. VITAMIN A QUALITY STATUS")
print("-" * 85)

vitamin_columns = [
    "Vitamin A Coverage (Postpartum) (%)",
    "Vitamin A Coverage (Children) (%)"
]


vitamin_results = []

for column in vitamin_columns:

    if column not in df.columns:
        continue

    vitamin_results.append({

        "Column":
            column,

        "Missing_Count":
            df[column]
            .isna()
            .sum(),

        "Above_100_Count":
            (
                df[column] > 100
            ).sum(),

        "Minimum":
            df[column].min(),

        "Maximum":
            df[column].max(),

        "Treatment":
            (
                "Preserved pending "
                "source-definition verification"
            )
    })


vitamin_status_df = pd.DataFrame(
    vitamin_results
)


print(
    vitamin_status_df
    .to_string(index=False)
)


vitamin_status_df.to_csv(
    REPORT_DIR
    / "preprocessing_vitamin_a_status.csv",
    index=False
)


# ============================================================
# 15. BREASTFEEDING MISSING STATUS
# ============================================================

print("\n" + "-" * 85)
print("13. BREASTFEEDING MISSING STATUS")
print("-" * 85)

if "breastfeeding" in df.columns:

    breastfeeding_missing = (
        df["breastfeeding"]
        .isna()
        .sum()
    )

    print(
        f"Missing breastfeeding values: "
        f"{breastfeeding_missing}"
    )

    print(
        "Decision: values preserved. "
        "No future-aware interpolation applied."
    )


# ============================================================
# 16. OUTLIER HANDLING DECISION
# ============================================================

print("\n" + "-" * 85)
print("14. OUTLIER HANDLING DECISION")
print("-" * 85)

print(
    "Potential statistical extreme values "
    "were NOT removed."
)

print(
    "Reason: an extreme observation may "
    "represent a genuine district/month event."
)

print(
    "Outliers will be investigated during EDA "
    "and model error analysis."
)


# ============================================================
# 17. SOURCE-CORRECTED VARIABLE CHECK
# ============================================================

print("\n" + "-" * 85)
print("15. SOURCE-CORRECTED VARIABLE CHECK")
print("-" * 85)

source_corrected_columns = [
    "Triposha_Packets_Distributed",
    "Nutrition_Programmes_Conducted",
    "Field_Nutrition_Clinics_Available",
    "Hospital_Nutrition_Clinics_Available",
    "Low_Birth_Weight_Cases"
]


source_results = []

for column in source_corrected_columns:

    if column in df.columns:

        source_results.append({

            "Column":
                column,

            "Missing_Count":
                df[column]
                .isna()
                .sum(),

            "Available_Count":
                df[column]
                .notna()
                .sum()
        })


source_status_df = pd.DataFrame(
    source_results
)


print(
    source_status_df
    .to_string(index=False)
)


# ============================================================
# 18. CREATE PREPROCESSING DECISION REPORT
# ============================================================

print("\n" + "-" * 85)
print("16. PREPROCESSING DECISION REPORT")
print("-" * 85)

decision_report = pd.DataFrame({

    "Issue": [
        "Column-name whitespace",
        "Target missing values",
        "Underweight/Wasting/Stunting missing",
        "Polonnaruwa climate missing",
        "Vitamin A Postpartum missing",
        "Vitamin A values above 100",
        "Breastfeeding missing values",
        "Potential IQR outliers",
        "Duplicate time records"
    ],

    "Decision": [
        "Strip whitespace from column names",
        "Preserve missing target; do not impute",
        "Preserve for later leakage-aware feature handling",
        "Preserve; do not use simple time interpolation",
        "Preserve; do not blindly interpolate",
        "Preserve until source definition is verified",
        "Preserve for later time-aware treatment",
        "Retain and investigate during EDA",
        "No duplicates detected; no deletion required"
    ],

    "Reason": [
        "Naming cleanup does not alter analytical values",
        "Target is the supervised learning label",
        "Direct indicators may create leakage if handled incorrectly",
        "Entire district history is missing, so within-district interpolation is impossible",
        "Missingness is a complete recent-year block",
        "Coverage values may depend on numerator/denominator definitions",
        "Future observations must not be used to fill earlier values",
        "Extreme values may be genuine observations",
        "Automatic deletion is unnecessary"
    ]
})


print(
    decision_report
    .to_string(index=False)
)


decision_report.to_csv(
    REPORT_DIR
    / "preprocessing_decision_report.csv",
    index=False
)


# ============================================================
# 19. FINAL MISSING VALUE SUMMARY
# ============================================================

print("\n" + "-" * 85)
print("17. FINAL MISSING VALUE SUMMARY")
print("-" * 85)

final_missing_summary = pd.DataFrame({

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


final_missing_summary = (
    final_missing_summary[
        final_missing_summary[
            "Missing_Count"
        ] > 0
    ]
    .sort_values(
        "Missing_Count",
        ascending=False
    )
)


print(
    final_missing_summary
    .to_string(index=False)
)


final_missing_summary.to_csv(
    REPORT_DIR
    / "preprocessing_remaining_missing_values.csv",
    index=False
)


# ============================================================
# 20. SAVE PREPROCESSED BASE DATASET
# ============================================================

print("\n" + "-" * 85)
print("18. SAVE PREPROCESSED DATASET")
print("-" * 85)

df.to_csv(
    OUTPUT_PATH,
    index=False
)


print(
    "Preprocessed base dataset saved."
)

print(
    f"Output path: {OUTPUT_PATH}"
)


# ============================================================
# 21. VERIFY RAW DATA WAS NOT MODIFIED
# ============================================================

print("\n" + "-" * 85)
print("19. RAW DATA PROTECTION CHECK")
print("-" * 85)

print(
    "Input raw/source-corrected dataset "
    "was read only."
)

print(
    "All changes were saved to "
    "data/processed/."
)


# ============================================================
# 22. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 85)
print("PREPROCESSING SUMMARY")
print("=" * 85)

print(
    f"Input rows              : "
    f"{original_df.shape[0]}"
)

print(
    f"Output rows             : "
    f"{df.shape[0]}"
)

print(
    f"Input columns           : "
    f"{original_df.shape[1]}"
)

print(
    f"Output columns          : "
    f"{df.shape[1]}"
)

print(
    f"Target missing retained : "
    f"{df[TARGET].isna().sum()}"
)

print(
    f"Duplicate time rows     : "
    f"{duplicate_count}"
)

print(
    f"Date column created     : "
    f"{'Date' in df.columns}"
)

print(
    "\nActions performed:"
)

print(
    "- Column names cleaned"
)

print(
    "- String values trimmed"
)

print(
    "- Year and Month validated"
)

print(
    "- Date column created"
)

print(
    "- Data sorted chronologically"
)

print(
    "- Duplicate keys checked"
)

print(
    "- Missing-data decisions documented"
)

print(
    "- No blind imputation performed"
)

print(
    "- No outliers automatically removed"
)

print(
    "- No Vitamin A values capped"
)

print(
    "- Raw/source dataset not overwritten"
)


# ============================================================
# 23. COMPLETE
# ============================================================

print("\nReports saved to:")
print(REPORT_DIR)

print("\nProcessed dataset saved to:")
print(OUTPUT_PATH)

print(
    "\nSTEP 04 - SAFE PREPROCESSING COMPLETE"
)

print("=" * 85)