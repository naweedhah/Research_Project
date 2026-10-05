# ============================================================
# STEP 03 - DATA QUALITY ANALYSIS
# Childhood Malnutrition Forecasting Research
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

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. LOAD DATASET
# ============================================================

print("\n" + "=" * 85)
print("STEP 03 - DATA QUALITY ANALYSIS")
print("=" * 85)

try:

    df = pd.read_csv(DATA_PATH)

    print("\nDataset loaded successfully.")
    print(f"Dataset location: {DATA_PATH}")

except FileNotFoundError:

    print("\nERROR: Dataset was not found.")
    print(f"Expected location: {DATA_PATH}")

    raise


# ============================================================
# 3. BASIC QUALITY OVERVIEW
# ============================================================

print("\n" + "-" * 85)
print("1. BASIC DATA QUALITY OVERVIEW")
print("-" * 85)

print(f"Rows                 : {df.shape[0]}")
print(f"Columns              : {df.shape[1]}")
print(f"Total cells          : {df.size}")
print(
    f"Total missing cells  : "
    f"{df.isna().sum().sum()}"
)

print(
    f"Missing percentage   : "
    f"{(df.isna().sum().sum() / df.size) * 100:.2f}%"
)


# ============================================================
# 4. COLUMN NAME QUALITY CHECK
# ============================================================

print("\n" + "-" * 85)
print("2. COLUMN NAME QUALITY CHECK")
print("-" * 85)

column_name_issues = []

for column in df.columns:

    cleaned_name = column.strip()

    if column != cleaned_name:

        column_name_issues.append({
            "Original_Column_Name": column,
            "Suggested_Column_Name": cleaned_name,
            "Issue":
                "Leading or trailing whitespace"
        })


if column_name_issues:

    column_name_issues_df = pd.DataFrame(
        column_name_issues
    )

    print(
        column_name_issues_df
        .to_string(index=False)
    )

    column_name_issues_df.to_csv(
        REPORT_DIR
        / "dq_column_name_issues.csv",
        index=False
    )

else:

    print(
        "No leading or trailing whitespace "
        "detected in column names."
    )


# ============================================================
# 5. DUPLICATE RECORD CHECK
# ============================================================

print("\n" + "-" * 85)
print("3. DUPLICATE RECORD CHECK")
print("-" * 85)

full_duplicate_count = (
    df.duplicated().sum()
)

print(
    f"Exact duplicate rows: "
    f"{full_duplicate_count}"
)


key_columns = [
    "District",
    "Year",
    "Month"
]

if set(key_columns).issubset(df.columns):

    key_duplicate_mask = (
        df.duplicated(
            subset=key_columns,
            keep=False
        )
    )

    key_duplicate_count = (
        key_duplicate_mask.sum()
    )

    print(
        "Duplicate District-Year-Month rows: "
        f"{key_duplicate_count}"
    )

    if key_duplicate_count > 0:

        key_duplicates = (
            df.loc[key_duplicate_mask]
            .sort_values(key_columns)
        )

        key_duplicates.to_csv(
            REPORT_DIR
            / "dq_duplicate_time_records.csv",
            index=False
        )


# ============================================================
# 6. MISSING VALUE SUMMARY
# ============================================================

print("\n" + "-" * 85)
print("4. MISSING VALUE SUMMARY")
print("-" * 85)


def missing_level(percentage):

    if percentage == 0:
        return "None"

    elif percentage <= 5:
        return "Low"

    elif percentage <= 20:
        return "Moderate"

    elif percentage <= 40:
        return "High"

    else:
        return "Very High"


missing_summary = pd.DataFrame({

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


missing_summary[
    "Descriptive_Level"
] = (
    missing_summary[
        "Missing_Percentage"
    ]
    .apply(missing_level)
)


missing_summary = (
    missing_summary
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
    / "dq_missing_value_summary.csv",
    index=False
)


print(
    "\nNOTE: Missingness levels are only "
    "descriptive reporting categories."
)

print(
    "They are NOT automatic rules for "
    "dropping or imputing variables."
)


# ============================================================
# 7. COLUMNS WITH MISSING DATA
# ============================================================

print("\n" + "-" * 85)
print("5. COLUMNS WITH MISSING DATA")
print("-" * 85)

missing_columns_df = (
    missing_summary[
        missing_summary[
            "Missing_Count"
        ] > 0
    ]
    .copy()
)

missing_columns = (
    missing_columns_df[
        "Column"
    ].tolist()
)


if missing_columns:

    print(
        missing_columns_df
        .to_string(index=False)
    )

else:

    print(
        "No missing values detected."
    )


# ============================================================
# 8. MISSINGNESS BY YEAR
# ============================================================

print("\n" + "-" * 85)
print("6. MISSINGNESS BY YEAR")
print("-" * 85)

missing_by_year_results = []

if "Year" in df.columns:

    for column in missing_columns:

        grouped = (
            df.groupby("Year")[column]
            .apply(
                lambda x:
                    int(x.isna().sum())
            )
        )

        for year, missing_count in grouped.items():

            if missing_count > 0:

                missing_by_year_results.append({
                    "Column": column,
                    "Year": year,
                    "Missing_Count":
                        missing_count
                })


missing_by_year_df = pd.DataFrame(
    missing_by_year_results
)


if not missing_by_year_df.empty:

    print(
        missing_by_year_df
        .to_string(index=False)
    )

    missing_by_year_df.to_csv(
        REPORT_DIR
        / "dq_missing_by_year.csv",
        index=False
    )

else:

    print(
        "No year-level missingness detected."
    )


# ============================================================
# 9. MISSINGNESS BY DISTRICT
# ============================================================

print("\n" + "-" * 85)
print("7. MISSINGNESS BY DISTRICT")
print("-" * 85)

missing_by_district_results = []

if "District" in df.columns:

    for column in missing_columns:

        grouped = (
            df.groupby("District")[column]
            .apply(
                lambda x:
                    int(x.isna().sum())
            )
        )

        for district, missing_count in grouped.items():

            if missing_count > 0:

                missing_by_district_results.append({
                    "Column": column,
                    "District": district,
                    "Missing_Count":
                        missing_count
                })


missing_by_district_df = pd.DataFrame(
    missing_by_district_results
)


if not missing_by_district_df.empty:

    print(
        missing_by_district_df
        .to_string(index=False)
    )

    missing_by_district_df.to_csv(
        REPORT_DIR
        / "dq_missing_by_district.csv",
        index=False
    )

else:

    print(
        "No district-level missingness detected."
    )


# ============================================================
# 10. MISSINGNESS BY MONTH
# ============================================================

print("\n" + "-" * 85)
print("8. MISSINGNESS BY MONTH")
print("-" * 85)

missing_by_month_results = []

if "Month" in df.columns:

    for column in missing_columns:

        grouped = (
            df.groupby("Month")[column]
            .apply(
                lambda x:
                    int(x.isna().sum())
            )
        )

        for month, missing_count in grouped.items():

            if missing_count > 0:

                missing_by_month_results.append({
                    "Column": column,
                    "Month": month,
                    "Missing_Count":
                        missing_count
                })


missing_by_month_df = pd.DataFrame(
    missing_by_month_results
)


if not missing_by_month_df.empty:

    print(
        missing_by_month_df
        .to_string(index=False)
    )

    missing_by_month_df.to_csv(
        REPORT_DIR
        / "dq_missing_by_month.csv",
        index=False
    )

else:

    print(
        "No month-level missingness detected."
    )


# ============================================================
# 11. DATA TYPE AND CARDINALITY CHECK
# ============================================================

print("\n" + "-" * 85)
print("9. DATA TYPE AND CARDINALITY CHECK")
print("-" * 85)

datatype_summary = pd.DataFrame({

    "Column":
        df.columns,

    "Data_Type":
        df.dtypes.astype(str).values,

    "Unique_Values": [
        df[column].nunique(
            dropna=True
        )
        for column in df.columns
    ],

    "Missing_Count":
        df.isna().sum().values
})


print(
    datatype_summary
    .to_string(index=False)
)


datatype_summary.to_csv(
    REPORT_DIR
    / "dq_datatype_cardinality_summary.csv",
    index=False
)


# ============================================================
# 12. INFINITE VALUE CHECK
# ============================================================

print("\n" + "-" * 85)
print("10. INFINITE VALUE CHECK")
print("-" * 85)

numeric_columns = (
    df
    .select_dtypes(
        include=np.number
    )
    .columns
    .tolist()
)


infinite_results = []

for column in numeric_columns:

    infinite_count = (
        np.isinf(
            df[column]
            .dropna()
        )
        .sum()
    )

    if infinite_count > 0:

        infinite_results.append({
            "Column": column,
            "Infinite_Count":
                int(infinite_count)
        })


if infinite_results:

    infinity_df = pd.DataFrame(
        infinite_results
    )

    print(
        infinity_df
        .to_string(index=False)
    )

    infinity_df.to_csv(
        REPORT_DIR
        / "dq_infinite_values.csv",
        index=False
    )

else:

    print(
        "No positive or negative infinity "
        "values detected."
    )


# ============================================================
# 13. NEGATIVE VALUE CHECK
# ============================================================

print("\n" + "-" * 85)
print("11. NEGATIVE VALUE CHECK")
print("-" * 85)

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
                int(negative_count),

            "Minimum_Value":
                df[column].min()
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
        / "dq_negative_values.csv",
        index=False
    )

else:

    print(
        "No negative numerical values detected."
    )


# ============================================================
# 14. ZERO VALUE PROFILE
# ============================================================

print("\n" + "-" * 85)
print("12. ZERO VALUE PROFILE")
print("-" * 85)

zero_results = []

for column in numeric_columns:

    if column in [
        "Year",
        "Month"
    ]:
        continue

    zero_count = (
        df[column] == 0
    ).sum()

    if zero_count > 0:

        zero_results.append({

            "Column":
                column,

            "Zero_Count":
                int(zero_count),

            "Zero_Percentage":
                round(
                    (
                        zero_count
                        / len(df)
                    )
                    * 100,
                    2
                )
        })


zero_df = pd.DataFrame(
    zero_results
)


if not zero_df.empty:

    print(
        zero_df
        .sort_values(
            "Zero_Count",
            ascending=False
        )
        .to_string(index=False)
    )

    zero_df.to_csv(
        REPORT_DIR
        / "dq_zero_value_profile.csv",
        index=False
    )

else:

    print(
        "No zero numerical values detected."
    )


print(
    "\nNOTE: Zero values are not automatically "
    "treated as errors."
)


# ============================================================
# 15. PERCENTAGE VARIABLE RANGE CHECK
# ============================================================

print("\n" + "-" * 85)
print("13. PERCENTAGE VARIABLE RANGE CHECK")
print("-" * 85)

percentage_columns = [
    column
    for column in df.columns
    if "%" in column
]


# breastfeeding is percentage-like even though
# the column name does not contain "%"
breastfeeding_column = next(
    (
        column
        for column in df.columns
        if column.strip().lower()
        == "breastfeeding"
    ),
    None
)


if (
    breastfeeding_column
    is not None
    and breastfeeding_column
    not in percentage_columns
):

    percentage_columns.append(
        breastfeeding_column
    )


percentage_results = []

for column in percentage_columns:

    below_zero = (
        df[column] < 0
    ).sum()

    above_100 = (
        df[column] > 100
    ).sum()

    percentage_results.append({

        "Column":
            column,

        "Minimum":
            df[column].min(),

        "Maximum":
            df[column].max(),

        "Below_0_Count":
            int(below_zero),

        "Above_100_Count":
            int(above_100)
    })


percentage_df = pd.DataFrame(
    percentage_results
)


print(
    percentage_df
    .to_string(index=False)
)


percentage_df.to_csv(
    REPORT_DIR
    / "dq_percentage_range_check.csv",
    index=False
)


print(
    "\nIMPORTANT: Values above 100 are flagged "
    "for source-definition verification."
)

print(
    "They will NOT automatically be capped "
    "or changed."
)


# ============================================================
# 16. COUNT VARIABLE VALIDITY CHECK
# ============================================================

print("\n" + "-" * 85)
print("14. COUNT VARIABLE VALIDITY CHECK")
print("-" * 85)

candidate_count_columns = [
    "Malnutrition_Cases",
    "Live Birth",
    "Under 5 Population",
    "Underweight",
    "Wasting",
    "Stunting",
    "Triposha_Packets_Distributed",
    "SAM_Cases_Annual",
    "MAM_Wasting_Cases_Annual",
    "Low_Birth_Weight_Cases",
    "Nutrition_Programmes_Conducted",
    "Field_Nutrition_Clinics_Available",
    "Hospital_Nutrition_Clinics_Available"
]


count_results = []

for column in candidate_count_columns:

    if column not in df.columns:
        continue

    valid_values = (
        df[column]
        .dropna()
    )

    negative_count = (
        valid_values < 0
    ).sum()

    non_integer_count = (
        ~np.isclose(
            valid_values,
            np.round(valid_values)
        )
    ).sum()

    count_results.append({

        "Column":
            column,

        "Available_Count":
            len(valid_values),

        "Negative_Count":
            int(negative_count),

        "Non_Integer_Like_Count":
            int(non_integer_count),

        "Minimum":
            valid_values.min()
            if len(valid_values) > 0
            else np.nan,

        "Maximum":
            valid_values.max()
            if len(valid_values) > 0
            else np.nan
    })


count_check_df = pd.DataFrame(
    count_results
)

print(
    count_check_df
    .to_string(index=False)
)


count_check_df.to_csv(
    REPORT_DIR
    / "dq_count_variable_check.csv",
    index=False
)


# ============================================================
# 17. CHILD COUNT VS UNDER-5 POPULATION CHECK
# ============================================================

print("\n" + "-" * 85)
print("15. CHILD COUNTS VS UNDER-5 POPULATION")
print("-" * 85)

child_count_columns = [
    "Malnutrition_Cases",
    "Underweight",
    "Wasting",
    "Stunting"
]


population_check_results = []

if "Under 5 Population" in df.columns:

    for column in child_count_columns:

        if column not in df.columns:
            continue

        valid_mask = (
            df[column].notna()
            &
            df[
                "Under 5 Population"
            ].notna()
        )

        violation_count = (
            df.loc[
                valid_mask,
                column
            ]
            >
            df.loc[
                valid_mask,
                "Under 5 Population"
            ]
        ).sum()

        population_check_results.append({

            "Variable":
                column,

            "Valid_Comparisons":
                int(valid_mask.sum()),

            "Count_Greater_Than_Under5":
                int(violation_count)
        })


population_check_df = pd.DataFrame(
    population_check_results
)

print(
    population_check_df
    .to_string(index=False)
)


population_check_df.to_csv(
    REPORT_DIR
    / "dq_child_population_consistency.csv",
    index=False
)


# ============================================================
# 18. BASIC ENVIRONMENTAL PLAUSIBILITY CHECK
# ============================================================

print("\n" + "-" * 85)
print("16. BASIC ENVIRONMENTAL RANGE CHECK")
print("-" * 85)

# These are broad plausibility checks only.
# They are not replacements for source-specific validation.

environment_bounds = {

    "ALLSKY_KT":
        (0, 1.5),

    "ALLSKY_SFC_SW_DWN":
        (0, None),

    "CLRSKY_SFC_PAR_TOT":
        (0, None),

    "CLRSKY_SFC_SW_DWN":
        (0, None),

    "PRECTOTCORR":
        (0, None),

    "RH2M":
        (0, 100),

    "T2M":
        (-10, 50),

    "WS10M":
        (0, None)
}


environment_results = []

for column, bounds in (
    environment_bounds.items()
):

    if column not in df.columns:
        continue

    lower_bound = bounds[0]
    upper_bound = bounds[1]

    lower_violations = 0
    upper_violations = 0

    if lower_bound is not None:

        lower_violations = (
            df[column] < lower_bound
        ).sum()

    if upper_bound is not None:

        upper_violations = (
            df[column] > upper_bound
        ).sum()

    environment_results.append({

        "Column":
            column,

        "Minimum":
            df[column].min(),

        "Maximum":
            df[column].max(),

        "Lower_Bound":
            lower_bound,

        "Upper_Bound":
            upper_bound,

        "Below_Bound_Count":
            int(lower_violations),

        "Above_Bound_Count":
            int(upper_violations)
    })


environment_df = pd.DataFrame(
    environment_results
)

print(
    environment_df
    .to_string(index=False)
)


environment_df.to_csv(
    REPORT_DIR
    / "dq_environment_range_check.csv",
    index=False
)


# ============================================================
# 19. MONTH AND MONTH_NAME CONSISTENCY
# ============================================================

print("\n" + "-" * 85)
print("17. MONTH / MONTH_NAME CONSISTENCY CHECK")
print("-" * 85)

expected_month_names = {

    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}


if {
    "Month",
    "Month_Name"
}.issubset(df.columns):

    invalid_month_count = (
        ~df["Month"].isin(
            range(1, 13)
        )
    ).sum()

    expected_names = (
        df["Month"]
        .map(
            expected_month_names
        )
    )

    actual_names = (
        df["Month_Name"]
        .astype(str)
        .str.strip()
    )

    month_name_mismatch_mask = (
        expected_names.notna()
        &
        (
            expected_names
            != actual_names
        )
    )

    mismatch_count = (
        month_name_mismatch_mask.sum()
    )

    print(
        f"Invalid Month values      : "
        f"{invalid_month_count}"
    )

    print(
        f"Month_Name mismatches     : "
        f"{mismatch_count}"
    )

    month_number_mapping = (
        df.groupby("Month")[
            "Month_Name"
        ]
        .nunique()
        .reset_index(
            name="Unique_Month_Names"
        )
    )

    reverse_mapping = (
        df.groupby("Month_Name")[
            "Month"
        ]
        .nunique()
        .reset_index(
            name="Unique_Month_Numbers"
        )
    )

    mapping_issue_count = (
        month_number_mapping[
            "Unique_Month_Names"
        ] > 1
    ).sum()

    reverse_issue_count = (
        reverse_mapping[
            "Unique_Month_Numbers"
        ] > 1
    ).sum()

    print(
        "Month numbers mapping to "
        "multiple names: "
        f"{mapping_issue_count}"
    )

    print(
        "Month names mapping to "
        "multiple numbers: "
        f"{reverse_issue_count}"
    )

    if mismatch_count > 0:

        df.loc[
            month_name_mismatch_mask,
            [
                "Year",
                "Month",
                "Month_Name",
                "District"
            ]
        ].to_csv(
            REPORT_DIR
            / "dq_month_name_mismatches.csv",
            index=False
        )


# ============================================================
# 20. DISTRICT NAME CONSISTENCY
# ============================================================

print("\n" + "-" * 85)
print("18. DISTRICT NAME CONSISTENCY")
print("-" * 85)

if "District" in df.columns:

    district_values = (
        df["District"]
        .dropna()
        .astype(str)
    )

    district_whitespace_count = (
        district_values
        != district_values.str.strip()
    ).sum()

    empty_district_count = (
        district_values
        .str.strip()
        .eq("")
        .sum()
    )

    print(
        f"Unique districts              : "
        f"{district_values.nunique()}"
    )

    print(
        f"District values with spaces   : "
        f"{district_whitespace_count}"
    )

    print(
        f"Empty district names          : "
        f"{empty_district_count}"
    )

    print("\nDistrict list:")

    for district in sorted(
        district_values
        .str.strip()
        .unique()
    ):

        print(f"- {district}")


# ============================================================
# 21. TRUE ANNUAL VARIABLE CONSISTENCY
# ============================================================

print("\n" + "-" * 85)
print("19. ANNUAL VARIABLE CONSISTENCY")
print("-" * 85)

# IMPORTANT:
# Low_Birth_Weight_Cases and
# Nutrition_Programmes_Conducted are NOT treated
# as annual variables.

annual_columns = [
    "SAM_Cases_Annual",
    "MAM_Wasting_Cases_Annual"
]


annual_summary_results = []

for column in annual_columns:

    if column not in df.columns:
        continue

    annual_group = (
        df.groupby(
            ["District", "Year"]
        )[column]
        .agg(
            Available_Values="count",
            Unique_Values=lambda x:
                x.nunique(
                    dropna=True
                ),
            Missing_Values=lambda x:
                x.isna().sum()
        )
        .reset_index()
    )

    inconsistent_groups = (
        annual_group[
            annual_group[
                "Unique_Values"
            ] > 1
        ]
    )

    fully_missing_groups = (
        annual_group[
            annual_group[
                "Available_Values"
            ] == 0
        ]
    )

    annual_summary_results.append({

        "Column":
            column,

        "District_Years_With_Multiple_Values":
            len(inconsistent_groups),

        "Completely_Missing_District_Years":
            len(fully_missing_groups)
    })

    if not inconsistent_groups.empty:

        inconsistent_groups.to_csv(
            REPORT_DIR
            / f"dq_{column}_annual_inconsistency.csv",
            index=False
        )


annual_summary_df = pd.DataFrame(
    annual_summary_results
)

print(
    annual_summary_df
    .to_string(index=False)
)

annual_summary_df.to_csv(
    REPORT_DIR
    / "dq_annual_consistency_summary.csv",
    index=False
)


# ============================================================
# 22. SOURCE-CORRECTED VARIABLE COMPLETENESS
# ============================================================

print("\n" + "-" * 85)
print("20. SOURCE-CORRECTED VARIABLE COMPLETENESS")
print("-" * 85)

source_corrected_columns = [
    "Triposha_Packets_Distributed",
    "Nutrition_Programmes_Conducted",
    "Field_Nutrition_Clinics_Available",
    "Hospital_Nutrition_Clinics_Available",
    "Low_Birth_Weight_Cases"
]


source_completion_results = []

for column in source_corrected_columns:

    if column not in df.columns:

        source_completion_results.append({

            "Column":
                column,

            "Status":
                "COLUMN NOT FOUND",

            "Available_Count":
                np.nan,

            "Missing_Count":
                np.nan,

            "Completeness_Percentage":
                np.nan
        })

        continue

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

    completeness = (
        df[column]
        .notna()
        .mean()
        * 100
    )

    source_completion_results.append({

        "Column":
            column,

        "Status":
            "Found",

        "Available_Count":
            available_count,

        "Missing_Count":
            missing_count,

        "Completeness_Percentage":
            round(
                completeness,
                2
            )
    })


source_completion_df = pd.DataFrame(
    source_completion_results
)

print(
    source_completion_df
    .to_string(index=False)
)

source_completion_df.to_csv(
    REPORT_DIR
    / "dq_source_corrected_completeness.csv",
    index=False
)


# ============================================================
# 23. PROGRAMME / CLINIC VARIABLE PROFILE
# ============================================================

print("\n" + "-" * 85)
print("21. PROGRAMME / CLINIC VARIABLE PROFILE")
print("-" * 85)

programme_clinic_columns = [
    "Triposha_Packets_Distributed",
    "Nutrition_Programmes_Conducted",
    "Field_Nutrition_Clinics_Available",
    "Hospital_Nutrition_Clinics_Available"
]


programme_results = []

for column in programme_clinic_columns:

    if column not in df.columns:
        continue

    programme_results.append({

        "Column":
            column,

        "Available_Count":
            df[column].notna().sum(),

        "Missing_Count":
            df[column].isna().sum(),

        "Zero_Count":
            (df[column] == 0).sum(),

        "Minimum":
            df[column].min(),

        "Maximum":
            df[column].max(),

        "Unique_Values":
            df[column]
            .nunique(
                dropna=True
            )
    })


programme_df = pd.DataFrame(
    programme_results
)

print(
    programme_df
    .to_string(index=False)
)

programme_df.to_csv(
    REPORT_DIR
    / "dq_programme_clinic_profile.csv",
    index=False
)


# ============================================================
# 24. CLIMATE DATA COVERAGE
# ============================================================

print("\n" + "-" * 85)
print("22. CLIMATE DATA COVERAGE")
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


climate_summary_results = []

for column in climate_columns:

    if column not in df.columns:
        continue

    climate_summary_results.append({

        "Column":
            column,

        "Available_Count":
            df[column].notna().sum(),

        "Missing_Count":
            df[column].isna().sum(),

        "Missing_Percentage":
            round(
                df[column]
                .isna()
                .mean()
                * 100,
                2
            )
    })


climate_summary_df = pd.DataFrame(
    climate_summary_results
)

print(
    climate_summary_df
    .to_string(index=False)
)

climate_summary_df.to_csv(
    REPORT_DIR
    / "dq_climate_coverage_summary.csv",
    index=False
)


# Climate missingness by district

climate_district_results = []

if "District" in df.columns:

    for column in climate_columns:

        if column not in df.columns:
            continue

        grouped = (
            df.groupby("District")[column]
            .apply(
                lambda x:
                    int(x.isna().sum())
            )
        )

        for district, missing_count in grouped.items():

            if missing_count > 0:

                climate_district_results.append({

                    "Climate_Variable":
                        column,

                    "District":
                        district,

                    "Missing_Count":
                        missing_count
                })


climate_district_df = pd.DataFrame(
    climate_district_results
)


if not climate_district_df.empty:

    print(
        "\nClimate missingness by district:"
    )

    print(
        climate_district_df
        .to_string(index=False)
    )

    climate_district_df.to_csv(
        REPORT_DIR
        / "dq_climate_missing_by_district.csv",
        index=False
    )


# ============================================================
# 25. GLOBAL IQR EXTREME VALUE SCREENING
# ============================================================

print("\n" + "-" * 85)
print("23. IQR EXTREME VALUE SCREENING")
print("-" * 85)

print(
    "This is a screening step only. "
    "Potential extremes will NOT be "
    "automatically removed."
)


iqr_results = []

excluded_iqr_columns = [
    "Year",
    "Month"
]


for column in numeric_columns:

    if column in excluded_iqr_columns:
        continue

    values = (
        df[column]
        .dropna()
    )

    if len(values) == 0:
        continue

    q1 = (
        values.quantile(0.25)
    )

    q3 = (
        values.quantile(0.75)
    )

    iqr = (
        q3 - q1
    )

    if iqr == 0:

        iqr_results.append({

            "Column":
                column,

            "Q1":
                q1,

            "Q3":
                q3,

            "IQR":
                iqr,

            "Lower_Bound":
                np.nan,

            "Upper_Bound":
                np.nan,

            "Potential_Extreme_Count":
                np.nan,

            "Screening_Note":
                "IQR = 0; standard IQR screening not suitable"
        })

        continue

    lower_bound = (
        q1 - 1.5 * iqr
    )

    upper_bound = (
        q3 + 1.5 * iqr
    )

    extreme_count = (
        (
            values < lower_bound
        )
        |
        (
            values > upper_bound
        )
    ).sum()

    iqr_results.append({

        "Column":
            column,

        "Q1":
            q1,

        "Q3":
            q3,

        "IQR":
            iqr,

        "Lower_Bound":
            lower_bound,

        "Upper_Bound":
            upper_bound,

        "Potential_Extreme_Count":
            int(extreme_count),

        "Screening_Note":
            "Review only; do not automatically remove"
    })


iqr_df = pd.DataFrame(
    iqr_results
)

print(
    iqr_df
    .to_string(index=False)
)

iqr_df.to_csv(
    REPORT_DIR
    / "dq_iqr_screening.csv",
    index=False
)


# ============================================================
# 26. LOW VARIATION SCREENING
# ============================================================

print("\n" + "-" * 85)
print("24. LOW VARIATION SCREENING")
print("-" * 85)

low_variation_results = []

for column in df.columns:

    unique_count = (
        df[column]
        .nunique(
            dropna=True
        )
    )

    if unique_count <= 2:

        low_variation_results.append({

            "Column":
                column,

            "Unique_Values":
                unique_count
        })


low_variation_df = pd.DataFrame(
    low_variation_results
)


if not low_variation_df.empty:

    print(
        low_variation_df
        .to_string(index=False)
    )

    low_variation_df.to_csv(
        REPORT_DIR
        / "dq_low_variation_columns.csv",
        index=False
    )

else:

    print(
        "No columns with <= 2 unique "
        "non-missing values detected."
    )


# ============================================================
# 27. HIGH-MISSINGNESS SCREEN
# ============================================================

print("\n" + "-" * 85)
print("25. VARIABLES WITH MORE THAN 20% MISSING")
print("-" * 85)

high_missing_df = (
    missing_summary[
        missing_summary[
            "Missing_Percentage"
        ] > 20
    ]
)


if not high_missing_df.empty:

    print(
        high_missing_df
        .to_string(index=False)
    )

else:

    print(
        "No variables currently have "
        "more than 20% missing data."
    )


# ============================================================
# 28. IMPORTANT FORECASTING DATA QUALITY NOTE
# ============================================================

print("\n" + "-" * 85)
print("26. FORECASTING DATA QUALITY NOTE")
print("-" * 85)

print(
    """
Data-quality treatment must respect time.

Future observations must not be used to clean or impute
earlier observations in a way that causes information
leakage.

Examples:

- Do not calculate an imputation value using future test data.
- Do not use future months to create predictors for earlier months.
- Annual variables must be checked for when they became available.
- Same-period health indicators must be checked before being used
  as predictors of the same-period target.
- Target missing values must not be blindly imputed.

Any learned preprocessing method should later be fitted only
using training data and then applied to validation/test data.
"""
)


# ============================================================
# 29. FINAL DATA QUALITY SUMMARY
# ============================================================

print("\n" + "=" * 85)
print("DATA QUALITY ANALYSIS SUMMARY")
print("=" * 85)

total_missing_cells = (
    df.isna()
    .sum()
    .sum()
)

columns_with_missing_count = (
    df.isna()
    .any()
    .sum()
)

columns_over_20 = (
    (
        df.isna()
        .mean()
        * 100
    ) > 20
).sum()


if set(key_columns).issubset(df.columns):

    duplicate_key_rows = (
        df.duplicated(
            subset=key_columns
        )
        .sum()
    )

else:

    duplicate_key_rows = np.nan


print(
    f"Dataset rows                    : "
    f"{df.shape[0]}"
)

print(
    f"Dataset columns                 : "
    f"{df.shape[1]}"
)

print(
    f"Total missing cells             : "
    f"{total_missing_cells}"
)

print(
    f"Columns containing missing data : "
    f"{columns_with_missing_count}"
)

print(
    f"Columns with >20% missing       : "
    f"{columns_over_20}"
)

print(
    f"Duplicate District-Year-Month   : "
    f"{duplicate_key_rows}"
)

print(
    f"Column-name whitespace issues   : "
    f"{len(column_name_issues)}"
)

print(
    f"Percentage variables screened   : "
    f"{len(percentage_columns)}"
)

print(
    f"Annual variables screened       : "
    f"{len(annual_columns)}"
)

print(
    f"Climate variables screened      : "
    f"{len(climate_columns)}"
)


if "Malnutrition_Cases" in df.columns:

    print(
        f"Missing target values           : "
        f"{df['Malnutrition_Cases'].isna().sum()}"
    )


print(
    "\nSource-corrected variables:"
)

for column in source_corrected_columns:

    if column in df.columns:

        print(
            f"- {column}: "
            f"{df[column].isna().sum()} missing"
        )


print(
    "\nIMPORTANT:"
)

print(
    "No missing values were filled."
)

print(
    "No rows were deleted."
)

print(
    "No potential outliers were removed."
)

print(
    "No percentage values were capped."
)

print(
    "The raw dataset was not modified."
)


# ============================================================
# 30. COMPLETE
# ============================================================

print("\nReports saved to:")
print(REPORT_DIR)

print(
    "\nSTEP 03 - DATA QUALITY ANALYSIS COMPLETE"
)

print("=" * 85)