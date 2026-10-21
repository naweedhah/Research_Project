# ============================================================
# STEP 07 - LEAKAGE-AWARE MULTI-HORIZON FEATURE ENGINEERING
# CORRECTED VERSION
#
# IMPORTANT CORRECTION:
# SAM_Cases_Annual and MAM_Wasting_Cases_Annual are actually
# MONTHLY variables. "_Annual" is only a source naming mistake.
#
# Therefore they are treated like other monthly predictors:
# Lag 1, 3, 6 and 12 months.
# ============================================================

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 1. SETTINGS
# ============================================================

TARGET = "Malnutrition_Cases"

HORIZONS = [1, 3, 6]

TARGET_LAGS = [1, 3, 6, 12]

PREDICTOR_LAGS = [1, 3, 6, 12]

ROLLING_WINDOWS = [3, 6, 12]


# These names contain "_Annual",
# but the actual observations are MONTHLY.

MISNAMED_MONTHLY_COLUMNS = [
    "SAM_Cases_Annual",
    "MAM_Wasting_Cases_Annual"
]


# ============================================================
# 2. PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

INPUT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "malnutrition_preprocessed_base.csv"
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


# ============================================================
# 3. LOAD DATA
# ============================================================

print("\n" + "=" * 100)
print("STEP 07 - CORRECTED LEAKAGE-AWARE FEATURE ENGINEERING")
print("=" * 100)


if not INPUT_PATH.exists():

    raise FileNotFoundError(
        f"File not found: {INPUT_PATH}"
    )


df = pd.read_csv(
    INPUT_PATH
)


# Remove accidental spaces in column names

df.columns = [
    column.strip()
    for column in df.columns
]


required_columns = [
    "District",
    "Date",
    TARGET
]


for column in required_columns:

    if column not in df.columns:

        raise ValueError(
            f"Required column missing: {column}"
        )


df["Date"] = pd.to_datetime(
    df["Date"]
)


df = (
    df
    .sort_values(
        [
            "District",
            "Date"
        ]
    )
    .reset_index(
        drop=True
    )
)


print(
    f"\nInput rows: {len(df)}"
)

print(
    f"Districts: {df['District'].nunique()}"
)

print(
    f"Date range: "
    f"{df['Date'].min().date()} "
    f"to "
    f"{df['Date'].max().date()}"
)


# ============================================================
# 4. DISTRICT-MONTH CONTINUITY CHECK
# ============================================================

print("\n" + "-" * 100)
print("1. MONTHLY CONTINUITY CHECK")
print("-" * 100)


continuity_records = []


for district, district_df in df.groupby(
    "District"
):

    district_df = (
        district_df
        .sort_values("Date")
    )


    expected_dates = pd.date_range(

        start=district_df["Date"].min(),

        end=district_df["Date"].max(),

        freq="MS"
    )


    actual_dates = pd.DatetimeIndex(
        district_df["Date"]
    )


    missing_months = expected_dates.difference(
        actual_dates
    )


    duplicates = int(

        district_df.duplicated(
            subset=["Date"]
        ).sum()
    )


    continuity_records.append({

        "District":
            district,

        "Observed_Months":
            len(actual_dates),

        "Expected_Months":
            len(expected_dates),

        "Missing_Calendar_Months":
            len(missing_months),

        "Duplicate_Months":
            duplicates
    })


continuity_df = pd.DataFrame(
    continuity_records
)


print(
    continuity_df.to_string(
        index=False
    )
)


if (
    continuity_df[
        "Missing_Calendar_Months"
    ].sum()
    != 0
):

    raise ValueError(
        "Missing calendar months found."
    )


if (
    continuity_df[
        "Duplicate_Months"
    ].sum()
    != 0
):

    raise ValueError(
        "Duplicate district-month rows found."
    )


print(
    "\nMonthly continuity check PASSED."
)


continuity_df.to_csv(

    REPORT_DIR
    / "07_monthly_continuity_audit.csv",

    index=False
)


# ============================================================
# 5. IDENTIFY MONTHLY NUMERIC PREDICTORS
# ============================================================

print("\n" + "-" * 100)
print("2. MONTHLY VARIABLE DEFINITION")
print("-" * 100)


numeric_columns = (

    df
    .select_dtypes(
        include=[np.number]
    )
    .columns
    .tolist()
)


# These are helper/target fields, not raw predictors.

excluded_numeric_columns = {

    TARGET,

    "Year",

    "Month",

    "Time_Index",

    "Month_Sin",

    "Month_Cos"
}


monthly_predictors = [

    column
    for column in numeric_columns

    if column
    not in excluded_numeric_columns
]


print(
    f"Monthly numeric predictors: "
    f"{len(monthly_predictors)}"
)


# ============================================================
# 6. VERIFY SAM/MAM CORRECTION
# ============================================================

print(
    "\nCorrecting source naming mistake:"
)


for column in MISNAMED_MONTHLY_COLUMNS:

    if column not in df.columns:

        raise ValueError(
            f"{column} was not found in dataset."
        )


    if column not in monthly_predictors:

        raise ValueError(
            f"{column} was not classified as monthly."
        )


    print(
        f"[CORRECT] {column} -> MONTHLY predictor"
    )


print(
    "\nNo SAM/MAM previous-year-only treatment will be used."
)


# ============================================================
# 7. CALENDAR FEATURES
# ============================================================

print("\n" + "-" * 100)
print("3. CALENDAR FEATURES")
print("-" * 100)


minimum_date = df["Date"].min()


calendar_features = pd.DataFrame(
    index=df.index
)


calendar_features[
    "Month_Sin"
] = np.sin(

    2
    *
    np.pi
    *
    df["Date"].dt.month
    /
    12
)


calendar_features[
    "Month_Cos"
] = np.cos(

    2
    *
    np.pi
    *
    df["Date"].dt.month
    /
    12
)


calendar_features[
    "Time_Index"
] = (

    (
        df["Date"].dt.year
        -
        minimum_date.year
    )
    *
    12

    +

    (
        df["Date"].dt.month
        -
        minimum_date.month
    )

).astype(int)


print(
    "Created Month_Sin, Month_Cos and Time_Index."
)


# ============================================================
# 8. TARGET LAGS
# ============================================================

print("\n" + "-" * 100)
print("4. HISTORICAL TARGET LAG FEATURES")
print("-" * 100)


target_feature_dict = {}


for lag in TARGET_LAGS:

    feature_name = (
        f"Malnutrition_Lag_{lag}"
    )


    target_feature_dict[
        feature_name
    ] = (

        df
        .groupby("District")[
            TARGET
        ]
        .shift(lag)
    )


print(
    f"Target lags created: {TARGET_LAGS}"
)


# ============================================================
# 9. TARGET ROLLING FEATURES
# ============================================================

print("\n" + "-" * 100)
print("5. LEAKAGE-SAFE TARGET ROLLING FEATURES")
print("-" * 100)


for window in ROLLING_WINDOWS:

    mean_name = (
        f"Malnutrition_Rolling_Mean_{window}"
    )


    std_name = (
        f"Malnutrition_Rolling_STD_{window}"
    )


    target_feature_dict[
        mean_name
    ] = (

        df
        .groupby("District")[
            TARGET
        ]
        .transform(

            lambda x:

            x
            .shift(1)
            .rolling(
                window=window,
                min_periods=window
            )
            .mean()
        )
    )


    target_feature_dict[
        std_name
    ] = (

        df
        .groupby("District")[
            TARGET
        ]
        .transform(

            lambda x:

            x
            .shift(1)
            .rolling(
                window=window,
                min_periods=window
            )
            .std()
        )
    )


print(
    f"Rolling windows created: "
    f"{ROLLING_WINDOWS}"
)

print(
    "All rolling features use shift(1) first."
)


target_features_df = pd.DataFrame(
    target_feature_dict
)


# ============================================================
# 10. MONTHLY PREDICTOR LAGS
# ============================================================

print("\n" + "-" * 100)
print("6. LAGGED MONTHLY PREDICTORS")
print("-" * 100)


predictor_feature_dict = {}


for predictor in monthly_predictors:

    for lag in PREDICTOR_LAGS:

        feature_name = (
            f"{predictor}_Lag_{lag}"
        )


        predictor_feature_dict[
            feature_name
        ] = (

            df
            .groupby("District")[
                predictor
            ]
            .shift(lag)
        )


predictor_features_df = pd.DataFrame(
    predictor_feature_dict
)


print(
    f"Predictor lag periods: "
    f"{PREDICTOR_LAGS}"
)

print(
    "Current/same-period predictor values "
    "are NOT directly used."
)


# ============================================================
# 11. EXPLICITLY VERIFY SAM/MAM LAGS
# ============================================================

print("\nSAM/MAM monthly lag verification:")


for column in MISNAMED_MONTHLY_COLUMNS:

    for lag in PREDICTOR_LAGS:

        feature_name = (
            f"{column}_Lag_{lag}"
        )


        if feature_name not in predictor_features_df.columns:

            raise ValueError(
                f"Missing feature: {feature_name}"
            )


        print(
            f"[PASS] {feature_name}"
        )


# ============================================================
# 12. COMBINE ENGINEERED FEATURES
# ============================================================

feature_data = pd.concat(

    [
        df[
            [
                "District",
                "Date"
            ]
        ].copy(),

        calendar_features,

        target_features_df,

        predictor_features_df
    ],

    axis=1
)


feature_columns = [

    column

    for column in feature_data.columns

    if column
    not in [
        "District",
        "Date"
    ]
]


print("\n" + "-" * 100)
print("7. MODEL FEATURE COUNT")
print("-" * 100)


print(
    f"Total leakage-aware engineered features: "
    f"{len(feature_columns)}"
)


# Expected:
# 3 calendar
# + 4 target lags
# + 6 target rolling
# + 35 monthly predictors * 4 lags
# = 153


# ============================================================
# 13. LEAKAGE AUDIT
# ============================================================

print("\n" + "-" * 100)
print("8. LEAKAGE AUDIT")
print("-" * 100)


leakage_checks = []


# Current target excluded

check_1 = (
    TARGET
    not in feature_columns
)


leakage_checks.append({

    "Check":
        "Current Malnutrition_Cases excluded",

    "Passed":
        check_1
})


# Same-period predictors excluded

same_period_found = [

    predictor

    for predictor in monthly_predictors

    if predictor
    in feature_columns
]


check_2 = (
    len(same_period_found)
    ==
    0
)


leakage_checks.append({

    "Check":
        "Same-period raw predictors excluded",

    "Passed":
        check_2
})


# Wrong Previous_Year SAM/MAM features must not exist

wrong_previous_year_features = [

    f"{column}_Previous_Year"

    for column in MISNAMED_MONTHLY_COLUMNS
]


check_3 = all(

    feature
    not in feature_columns

    for feature
    in wrong_previous_year_features
)


leakage_checks.append({

    "Check":
        "Incorrect SAM/MAM Previous_Year features absent",

    "Passed":
        check_3
})


# Future target features absent

check_4 = all(

    "Target_H"
    not in feature

    for feature
    in feature_columns
)


leakage_checks.append({

    "Check":
        "Future target columns excluded",

    "Passed":
        check_4
})


leakage_audit_df = pd.DataFrame(
    leakage_checks
)


print(
    leakage_audit_df.to_string(
        index=False
    )
)


if not leakage_audit_df[
    "Passed"
].all():

    raise ValueError(
        "Leakage audit FAILED."
    )


print(
    "\nLeakage audit PASSED."
)


leakage_audit_df.to_csv(

    REPORT_DIR
    / "07_leakage_audit.csv",

    index=False
)


# ============================================================
# 14. CREATE FUTURE TARGET LABELS
# ============================================================

print("\n" + "-" * 100)
print("9. CREATE MULTI-HORIZON FORECAST TARGETS")
print("-" * 100)


target_label_dict = {}


for horizon in HORIZONS:

    target_name = (
        f"Target_H{horizon}"
    )


    target_date_name = (
        f"Target_Date_H{horizon}"
    )


    target_label_dict[
        target_name
    ] = (

        df
        .groupby("District")[
            TARGET
        ]
        .shift(
            -horizon
        )
    )


    target_label_dict[
        target_date_name
    ] = (

        df["Date"]
        +
        pd.DateOffset(
            months=horizon
        )
    )


    print(
        f"H{horizon}: "
        f"features at month t -> "
        f"target at month t+{horizon}"
    )


target_labels_df = pd.DataFrame(
    target_label_dict
)


feature_data = pd.concat(

    [
        feature_data,
        target_labels_df
    ],

    axis=1
)


# ============================================================
# 15. TARGET ALIGNMENT VALIDATION
# ============================================================

print("\n" + "-" * 100)
print("10. TARGET ALIGNMENT VALIDATION")
print("-" * 100)


alignment_records = []


target_lookup = (

    df[
        [
            "District",
            "Date",
            TARGET
        ]
    ]
    .rename(

        columns={

            "Date":
                "Lookup_Target_Date",

            TARGET:
                "Lookup_Target"
        }
    )
)


for horizon in HORIZONS:

    target_name = (
        f"Target_H{horizon}"
    )


    target_date_name = (
        f"Target_Date_H{horizon}"
    )


    audit_df = (

        feature_data[
            [
                "District",
                target_date_name,
                target_name
            ]
        ]
        .rename(

            columns={

                target_date_name:
                    "Lookup_Target_Date",

                target_name:
                    "Generated_Target"
            }
        )
        .merge(

            target_lookup,

            on=[
                "District",
                "Lookup_Target_Date"
            ],

            how="left"
        )
    )


    comparable = (

        audit_df[
            "Generated_Target"
        ].notna()

        &

        audit_df[
            "Lookup_Target"
        ].notna()
    )


    generated_values = (

        audit_df.loc[
            comparable,
            "Generated_Target"
        ]
        .to_numpy(
            dtype=float
        )
    )


    expected_values = (

        audit_df.loc[
            comparable,
            "Lookup_Target"
        ]
        .to_numpy(
            dtype=float
        )
    )


    mismatch_count = int(

        (
            ~np.isclose(
                generated_values,
                expected_values
            )
        )
        .sum()
    )


    available_labels = int(

        feature_data[
            target_name
        ]
        .notna()
        .sum()
    )


    alignment_records.append({

        "Horizon_Months":
            horizon,

        "Target_Column":
            target_name,

        "Alignment_Mismatches":
            mismatch_count,

        "Available_Target_Labels":
            available_labels
    })


alignment_df = pd.DataFrame(
    alignment_records
)


print(
    alignment_df.to_string(
        index=False
    )
)


if (
    alignment_df[
        "Alignment_Mismatches"
    ].sum()
    !=
    0
):

    raise ValueError(
        "Target alignment FAILED."
    )


print(
    "\nTarget alignment audit PASSED."
)


alignment_df.to_csv(

    REPORT_DIR
    / "07_target_alignment_audit.csv",

    index=False
)


# ============================================================
# 16. FEATURE MISSINGNESS
# ============================================================

print("\n" + "-" * 100)
print("11. ENGINEERED FEATURE MISSINGNESS")
print("-" * 100)


missingness_records = []


for feature in feature_columns:

    missing_count = int(

        feature_data[
            feature
        ]
        .isna()
        .sum()
    )


    missingness_records.append({

        "Feature":
            feature,

        "Missing_Count":
            missing_count,

        "Missing_Percentage":
            (
                missing_count
                /
                len(feature_data)
                *
                100
            )
    })


missingness_df = pd.DataFrame(
    missingness_records
)


missingness_df = (

    missingness_df
    .sort_values(

        "Missing_Percentage",

        ascending=False
    )
)


print(

    missingness_df
    .head(20)
    .round(2)
    .to_string(
        index=False
    )
)


print(
    "\nIMPORTANT:"
)

print(
    "Missing feature values are NOT imputed here."
)

print(
    "Imputation will be learned from training data only."
)


missingness_df.to_csv(

    REPORT_DIR
    / "07_engineered_feature_missingness.csv",

    index=False
)


# ============================================================
# 17. SAVE MASTER ALL-HORIZON DATASET
# ============================================================

print("\n" + "-" * 100)
print("12. SAVE MASTER FEATURE DATASET")
print("-" * 100)


MASTER_OUTPUT = (

    PROCESSED_DIR
    /
    "malnutrition_leakage_aware_features_all_horizons.csv"
)


feature_data.to_csv(

    MASTER_OUTPUT,

    index=False
)


print(
    f"Saved: {MASTER_OUTPUT}"
)


# ============================================================
# 18. CREATE HORIZON-SPECIFIC DATASETS
# ============================================================

print("\n" + "-" * 100)
print("13. CREATE HORIZON-SPECIFIC DATASETS")
print("-" * 100)


horizon_summary_records = []


for horizon in HORIZONS:

    target_name = (
        f"Target_H{horizon}"
    )


    target_date_name = (
        f"Target_Date_H{horizon}"
    )


    horizon_df = (

        feature_data[
            [
                "District",
                "Date",
                target_date_name,
                target_name
            ]
            +
            feature_columns
        ]
        .copy()
    )


    horizon_df = horizon_df.rename(

        columns={

            "Date":
                "Forecast_Origin_Date",

            target_date_name:
                "Forecast_Target_Date",

            target_name:
                "Forecast_Target"
        }
    )


    horizon_df[
        "Forecast_Horizon"
    ] = horizon


    # Keep only rows with known supervised target label

    rows_before = len(
        horizon_df
    )


    rows_without_target = int(

        horizon_df[
            "Forecast_Target"
        ]
        .isna()
        .sum()
    )


    horizon_df = (

        horizon_df[
            horizon_df[
                "Forecast_Target"
            ].notna()
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )


    # Arrange metadata first

    horizon_df = horizon_df[

        [
            "District",
            "Forecast_Origin_Date",
            "Forecast_Target_Date",
            "Forecast_Horizon",
            "Forecast_Target"
        ]

        +

        feature_columns
    ]


    output_path = (

        PROCESSED_DIR
        /
        f"malnutrition_features_h{horizon}.csv"
    )


    horizon_df.to_csv(

        output_path,

        index=False
    )


    print(
        f"H{horizon}: "
        f"{len(horizon_df)} labelled rows saved."
    )


    horizon_summary_records.append({

        "Horizon_Months":
            horizon,

        "Rows_Before_Target_Filter":
            rows_before,

        "Rows_With_Valid_Target":
            len(
                horizon_df
            ),

        "Rows_Without_Target_Label":
            rows_without_target,

        "Feature_Count":
            len(
                feature_columns
            ),

        "Output_File":
            output_path.name
    })


horizon_summary_df = pd.DataFrame(
    horizon_summary_records
)


print(
    "\nHorizon dataset summary:"
)


print(
    horizon_summary_df.to_string(
        index=False
    )
)


horizon_summary_df.to_csv(

    REPORT_DIR
    / "07_feature_engineering_summary.csv",

    index=False
)


# ============================================================
# 19. FEATURE MANIFEST
# ============================================================

manifest_records = []


for feature in feature_columns:

    source_note = ""


    if (
        feature.startswith(
            "SAM_Cases_Annual_Lag_"
        )
        or
        feature.startswith(
            "MAM_Wasting_Cases_Annual_Lag_"
        )
    ):

        source_note = (
            "Source name contains _Annual, "
            "but actual data frequency is monthly."
        )


    manifest_records.append({

        "Feature":
            feature,

        "Leakage_Status":
            "Safe",

        "Source_Note":
            source_note
    })


feature_manifest_df = pd.DataFrame(
    manifest_records
)


feature_manifest_df.to_csv(

    REPORT_DIR
    / "07_leakage_aware_feature_manifest.csv",

    index=False
)


# ============================================================
# 20. SOURCE CORRECTION REPORT
# ============================================================

correction_df = pd.DataFrame({

    "Column": [
        "SAM_Cases_Annual",
        "MAM_Wasting_Cases_Annual"
    ],

    "Actual_Frequency": [
        "Monthly",
        "Monthly"
    ],

    "Reason": [
        "_Annual is a source typing/naming error",
        "_Annual is a source typing/naming error"
    ],

    "Modelling_Treatment": [
        "Monthly predictor with lags 1,3,6,12",
        "Monthly predictor with lags 1,3,6,12"
    ]
})


correction_df.to_csv(

    REPORT_DIR
    / "07_source_frequency_correction.csv",

    index=False
)


# ============================================================
# 21. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 100)
print("CORRECTED STEP 07 SUMMARY")
print("=" * 100)


print(
    f"Input rows                  : "
    f"{len(df)}"
)

print(
    f"Districts                   : "
    f"{df['District'].nunique()}"
)

print(
    f"Forecast horizons           : "
    f"{HORIZONS}"
)

print(
    f"Monthly predictors          : "
    f"{len(monthly_predictors)}"
)

print(
    f"Target lag periods          : "
    f"{TARGET_LAGS}"
)

print(
    f"Predictor lag periods       : "
    f"{PREDICTOR_LAGS}"
)

print(
    f"Target rolling windows      : "
    f"{ROLLING_WINDOWS}"
)

print(
    f"Leakage-aware feature count : "
    f"{len(feature_columns)}"
)


print(
    "\nSAM/MAM CORRECTION:"
)

print(
    "- SAM_Cases_Annual is treated as MONTHLY"
)

print(
    "- MAM_Wasting_Cases_Annual is treated as MONTHLY"
)

print(
    "- Both receive Lag1 / Lag3 / Lag6 / Lag12"
)

print(
    "- No Previous_Year-only SAM/MAM feature is created"
)


print(
    "\nLeakage protections:"
)

print(
    "- Current Malnutrition_Cases excluded"
)

print(
    "- Future targets excluded"
)

print(
    "- Same-period numeric predictors excluded"
)

print(
    "- Historical predictor lags only"
)

print(
    "- Rolling target features use shift(1)"
)

print(
    "- No global imputation"
)

print(
    "- No global scaling"
)


print(
    "\nLeakage audit: PASS"
)

print(
    "Target alignment audit: PASS"
)

print(
    "Monthly continuity audit: PASS"
)


print(
    "\nSTEP 07 - CORRECTED FEATURE ENGINEERING COMPLETE"
)

print("=" * 100)


print(
    "\nNEXT STEP:"
)

print(
    "Re-run Step 08 because feature datasets "
    "have now changed."
)