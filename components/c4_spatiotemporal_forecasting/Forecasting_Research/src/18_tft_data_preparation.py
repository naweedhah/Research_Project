# ============================================================
# STEP 18 - TFT DATA PREPARATION
# Childhood Malnutrition Forecasting Research
#
# Purpose:
# - Prepare leakage-safe sequential data for
#   Temporal Fusion Transformer (TFT)
# - Keep 2025 completely outside development modelling
# - Prepare:
#       Core training          : 2015-2022
#       Full training          : 2015-2023
#       Internal-val context   : through 2023
#       External-val context   : through 2024
#
# IMPORTANT:
# - Target = Malnutrition_Cases
# - Target missing values are NOT imputed
# - Missing target blocks create separate continuous segments
# - Predictor imputation is learned from TRAINING period only
# - 2024 does NOT influence imputation decisions
# - 2025 is excluded
#
# TFT VARIABLE ROLES:
#
# STATIC:
# - District
#
# KNOWN FUTURE:
# - Time_Index
# - Month_Cat
# - Month_Sin_TFT
# - Month_Cos_TFT
#
# FUTURE UNKNOWN:
# - Malnutrition_Cases
# - Health / nutrition / socioeconomic / environmental
#   numeric predictors
#
# DATA CORRECTION:
# SAM_Cases_Annual and MAM_Wasting_Cases_Annual contain
# MONTHLY observations despite "_Annual" in their source names.
# They are therefore treated as monthly time-varying variables.
# ============================================================


from pathlib import Path
import re

import numpy as np
import pandas as pd


# ============================================================
# 1. SETTINGS
# ============================================================

TARGET_ORIGINAL = "Malnutrition_Cases"

DISTRICT_ORIGINAL = "District"

DATE_ORIGINAL = "Date"


ENCODER_LENGTH_MONTHS = 12

MAX_FORECAST_HORIZON = 6


CORE_TRAIN_END = pd.Timestamp(
    "2022-12-01"
)

FULL_TRAIN_END = pd.Timestamp(
    "2023-12-01"
)

EXTERNAL_VALIDATION_START = pd.Timestamp(
    "2024-01-01"
)

EXTERNAL_VALIDATION_END = pd.Timestamp(
    "2024-12-01"
)


MISNAMED_MONTHLY_COLUMNS = [

    "SAM_Cases_Annual",

    "MAM_Wasting_Cases_Annual"
]


# Columns that should not become unknown real predictors.

NON_PREDICTOR_SOURCE_COLUMNS = {

    "Year",

    "Month",

    "Month_Name",

    "Record_ID",

    "record_id",

    "Index",

    "index"
}


# ============================================================
# 2. PROJECT PATHS
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


TFT_DIR = (

    BASE_DIR
    / "data"
    / "model_ready"
    / "tft"
)


REPORT_DIR = (

    BASE_DIR
    / "outputs"
    / "reports"
)


TFT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 3. INTRODUCTION
# ============================================================

print(
    "\n"
    +
    "=" * 115
)

print(
    "STEP 18 - TFT DATA PREPARATION"
)

print(
    "=" * 115
)


print(
    "\nTFT development strategy:"
)

print(
    "- Core training: 2015-2022"
)

print(
    "- Internal validation year: 2023"
)

print(
    "- Full training period: 2015-2023"
)

print(
    "- External validation year: 2024"
)

print(
    "- 2025 excluded from TFT development"
)

print(
    f"- Encoder history: "
    f"{ENCODER_LENGTH_MONTHS} months"
)

print(
    f"- Maximum forecast horizon: "
    f"{MAX_FORECAST_HORIZON} months"
)


print(
    "\nCorrected monthly-variable handling:"
)

for column in MISNAMED_MONTHLY_COLUMNS:

    print(
        f"- {column} -> MONTHLY historical variable"
    )


# ============================================================
# 4. LOAD PREPROCESSED DATA
# ============================================================

if not INPUT_PATH.exists():

    raise FileNotFoundError(

        f"Required input file not found:\n"
        f"{INPUT_PATH}"
    )


df = pd.read_csv(
    INPUT_PATH
)


# Clean accidental whitespace in names.

df.columns = [

    str(column).strip()

    for column in df.columns
]


print(
    f"\nInput file:"
)

print(
    INPUT_PATH
)


print(
    f"\nInput rows: "
    f"{len(df)}"
)

print(
    f"Input columns: "
    f"{len(df.columns)}"
)


# ============================================================
# 5. REQUIRED COLUMN CHECK
# ============================================================

required_columns = [

    DISTRICT_ORIGINAL,

    DATE_ORIGINAL,

    TARGET_ORIGINAL
]


for column in required_columns:

    if column not in df.columns:

        raise ValueError(

            f"Required column missing: "
            f"{column}"
        )


# ============================================================
# 6. DATE PREPARATION
# ============================================================

df[
    DATE_ORIGINAL
] = pd.to_datetime(

    df[
        DATE_ORIGINAL
    ],

    errors="coerce"
)


if df[
    DATE_ORIGINAL
].isna().any():

    raise ValueError(
        "Invalid Date values detected."
    )


df = (

    df
    .sort_values(

        [
            DISTRICT_ORIGINAL,
            DATE_ORIGINAL
        ]
    )
    .reset_index(
        drop=True
    )
)


print(
    f"\nOriginal date range: "
    f"{df[DATE_ORIGINAL].min().date()} "
    f"to "
    f"{df[DATE_ORIGINAL].max().date()}"
)


# ============================================================
# 7. DUPLICATE DISTRICT-MONTH CHECK
# ============================================================

duplicate_count = int(

    df
    .duplicated(

        subset=[

            DISTRICT_ORIGINAL,

            DATE_ORIGINAL
        ]

    )
    .sum()
)


print(
    f"Duplicate District-Date rows: "
    f"{duplicate_count}"
)


if duplicate_count != 0:

    raise ValueError(

        "Duplicate district-month rows detected. "
        "TFT preparation stopped."
    )


# ============================================================
# 8. EXCLUDE 2025 FROM DEVELOPMENT DATA
# ============================================================

rows_2025_or_later = int(

    (
        df[
            DATE_ORIGINAL
        ]
        >=
        pd.Timestamp(
            "2025-01-01"
        )
    )
    .sum()
)


development_df = (

    df[
        df[
            DATE_ORIGINAL
        ]
        <=
        EXTERNAL_VALIDATION_END
    ]
    .copy()
)


print(
    f"\nRows excluded from 2025+: "
    f"{rows_2025_or_later}"
)


print(
    f"Development rows through 2024: "
    f"{len(development_df)}"
)


if (

    development_df[
        DATE_ORIGINAL
    ].max()

    >
    EXTERNAL_VALIDATION_END
):

    raise ValueError(
        "2025 data entered TFT development dataset."
    )


# ============================================================
# 9. SANITIZE COLUMN NAMES FOR TFT
# ============================================================

def create_safe_name(
    value
):

    safe_name = re.sub(

        r"[^A-Za-z0-9_]+",

        "_",

        str(value)
    )


    safe_name = (
        safe_name
        .strip("_")
    )


    if safe_name == "":

        safe_name = "Feature"


    if safe_name[0].isdigit():

        safe_name = (
            "F_"
            +
            safe_name
        )


    return safe_name


original_columns = (
    development_df
    .columns
    .tolist()
)


safe_columns = []

used_names = {}


mapping_records = []


for original_column in original_columns:

    base_name = create_safe_name(
        original_column
    )


    safe_name = base_name


    if safe_name in used_names:

        used_names[
            safe_name
        ] += 1

        safe_name = (

            f"{base_name}_"
            f"{used_names[base_name]}"
        )

    else:

        used_names[
            safe_name
        ] = 0


    safe_columns.append(
        safe_name
    )


    mapping_records.append({

        "Original_Column":
            original_column,

        "TFT_Column":
            safe_name,

        "Changed":
            original_column != safe_name
    })


column_mapping_df = pd.DataFrame(
    mapping_records
)


development_df.columns = (
    safe_columns
)


column_mapping_df.to_csv(

    REPORT_DIR
    / "18_tft_column_name_mapping.csv",

    index=False
)


original_to_safe = dict(

    zip(

        column_mapping_df[
            "Original_Column"
        ],

        column_mapping_df[
            "TFT_Column"
        ]
    )
)


TARGET = (
    original_to_safe[
        TARGET_ORIGINAL
    ]
)


DISTRICT = (
    original_to_safe[
        DISTRICT_ORIGINAL
    ]
)


DATE = (
    original_to_safe[
        DATE_ORIGINAL
    ]
)


# ============================================================
# 10. VERIFY CORRECTED SAM / MAM COLUMNS
# ============================================================

print(
    "\nChecking corrected SAM/MAM variables:"
)


for original_column in MISNAMED_MONTHLY_COLUMNS:

    if original_column in original_to_safe:

        safe_column = (
            original_to_safe[
                original_column
            ]
        )

        print(
            f"PASS: "
            f"{original_column} -> "
            f"{safe_column} "
            f"(monthly)"
        )

    else:

        print(
            f"WARNING: "
            f"{original_column} "
            f"not found."
        )


# ============================================================
# 11. CREATE CALENDAR / KNOWN-FUTURE FEATURES
# ============================================================

minimum_date = pd.Timestamp(
    "2015-01-01"
)


development_df[
    "Time_Index"
] = (

    (
        development_df[
            DATE
        ].dt.year
        -
        minimum_date.year
    )

    *
    12

    +

    (
        development_df[
            DATE
        ].dt.month
        -
        minimum_date.month
    )

).astype(int)


development_df[
    "Month_Cat"
] = (

    development_df[
        DATE
    ]
    .dt.month
    .astype(int)
    .astype(str)
    .str.zfill(2)
)


development_df[
    "Month_Sin_TFT"
] = np.sin(

    2
    *
    np.pi
    *
    development_df[
        DATE
    ].dt.month

    /
    12
)


development_df[
    "Month_Cos_TFT"
] = np.cos(

    2
    *
    np.pi
    *
    development_df[
        DATE
    ].dt.month

    /
    12
)


# ============================================================
# 12. TARGET CHECK
# ============================================================

development_df[
    TARGET
] = pd.to_numeric(

    development_df[
        TARGET
    ],

    errors="coerce"
)


missing_target_count = int(

    development_df[
        TARGET
    ]
    .isna()
    .sum()
)


print(
    f"\nMissing target rows through 2024: "
    f"{missing_target_count}"
)


print(
    "Target missing values will NOT be imputed."
)


# ============================================================
# 13. IDENTIFY NUMERIC HISTORICAL PREDICTORS
# ============================================================

source_numeric_predictors = []


for original_column in original_columns:

    if original_column in {

        TARGET_ORIGINAL,

        DISTRICT_ORIGINAL,

        DATE_ORIGINAL
    }:

        continue


    if original_column in NON_PREDICTOR_SOURCE_COLUMNS:

        continue


    safe_column = (
        original_to_safe[
            original_column
        ]
    )


    numeric_series = pd.to_numeric(

        development_df[
            safe_column
        ],

        errors="coerce"
    )


    # Only keep columns that are genuinely numeric.

    if numeric_series.notna().sum() > 0:

        development_df[
            safe_column
        ] = numeric_series

        source_numeric_predictors.append(
            safe_column
        )


print(
    f"\nCandidate historical numeric predictors: "
    f"{len(source_numeric_predictors)}"
)


# ============================================================
# 14. TRAINING-PERIOD FEATURE QUALITY CHECK
# ============================================================

training_quality_df = (

    development_df[

        development_df[
            DATE
        ]
        <=
        FULL_TRAIN_END

    ]
    .copy()
)


usable_unknown_reals = []

feature_quality_records = []


for column in source_numeric_predictors:

    training_values = pd.to_numeric(

        training_quality_df[
            column
        ],

        errors="coerce"
    )


    non_missing_count = int(

        training_values
        .notna()
        .sum()
    )


    unique_non_missing = int(

        training_values
        .dropna()
        .nunique()
    )


    if non_missing_count == 0:

        status = (
            "Removed - All Missing In Training"
        )


    elif unique_non_missing <= 1:

        status = (
            "Removed - Constant In Training"
        )


    else:

        status = (
            "Usable"
        )

        usable_unknown_reals.append(
            column
        )


    original_matches = (

        column_mapping_df[

            column_mapping_df[
                "TFT_Column"
            ]
            ==
            column

        ][
            "Original_Column"
        ]
        .tolist()
    )


    original_name = (

        original_matches[0]

        if original_matches

        else column
    )


    feature_quality_records.append({

        "Original_Variable":
            original_name,

        "TFT_Variable":
            column,

        "Training_Non_Missing":
            non_missing_count,

        "Training_Unique_Values":
            unique_non_missing,

        "Status":
            status
    })


feature_quality_df = pd.DataFrame(
    feature_quality_records
)


feature_quality_df.to_csv(

    REPORT_DIR
    / "18_tft_predictor_quality_report.csv",

    index=False
)


print(
    f"Usable historical numeric predictors: "
    f"{len(usable_unknown_reals)}"
)


removed_predictor_count = (

    len(source_numeric_predictors)

    -
    len(usable_unknown_reals)
)


print(
    f"Removed unusable predictors: "
    f"{removed_predictor_count}"
)


# ============================================================
# 15. TRAIN-ONLY MEDIAN IMPUTATION
# ============================================================

print(
    "\nLearning predictor medians "
    "from 2015-2023 TRAINING period only..."
)


training_for_imputation = (

    development_df[

        (
            development_df[
                DATE
            ]
            <=
            FULL_TRAIN_END
        )

        &

        (
            development_df[
                TARGET
            ]
            .notna()
        )

    ]
    .copy()
)


imputation_records = []


for column in usable_unknown_reals:

    median_value = (

        pd.to_numeric(

            training_for_imputation[
                column
            ],

            errors="coerce"
        )

        .median()
    )


    if pd.isna(
        median_value
    ):

        raise ValueError(

            f"Training median could not be "
            f"calculated for {column}"
        )


    missing_before = int(

        development_df[
            column
        ]
        .isna()
        .sum()
    )


    development_df[
        column
    ] = (

        pd.to_numeric(

            development_df[
                column
            ],

            errors="coerce"
        )

        .fillna(
            float(
                median_value
            )
        )

        .astype(float)
    )


    missing_after = int(

        development_df[
            column
        ]
        .isna()
        .sum()
    )


    imputation_records.append({

        "Variable":
            column,

        "Training_Median":
            float(
                median_value
            ),

        "Missing_Before":
            missing_before,

        "Missing_After":
            missing_after
    })


imputation_df = pd.DataFrame(
    imputation_records
)


imputation_df.to_csv(

    REPORT_DIR
    / "18_tft_train_only_imputation_values.csv",

    index=False
)


remaining_predictor_nans = int(

    development_df[
        usable_unknown_reals
    ]
    .isna()
    .sum()
    .sum()
)


print(
    f"Remaining predictor NaNs after "
    f"train-only imputation: "
    f"{remaining_predictor_nans}"
)


if remaining_predictor_nans != 0:

    raise ValueError(

        "Predictor missing values remain "
        "after imputation."
    )


# ============================================================
# 16. DO NOT IMPUTE TARGET
# ============================================================

target_missing_after_imputation = int(

    development_df[
        TARGET
    ]
    .isna()
    .sum()
)


if (

    target_missing_after_imputation

    !=

    missing_target_count
):

    raise ValueError(

        "Target values were accidentally modified "
        "during TFT preprocessing."
    )


print(
    "Target protection check: PASS"
)


# ============================================================
# 17. REMOVE TARGET-MISSING ROWS FROM SEQUENCES
# ============================================================
#
# We do not create fake target values.
# Instead, missing-target periods break the time series
# into separate continuous sequence segments.
# ============================================================

observed_df = (

    development_df[

        development_df[
            TARGET
        ]
        .notna()

    ]

    .copy()
)


observed_df = (

    observed_df
    .sort_values(

        [
            DISTRICT,
            DATE
        ]
    )
    .reset_index(
        drop=True
    )
)


print(
    f"\nRows with observed targets: "
    f"{len(observed_df)}"
)


print(
    f"Target-missing rows excluded from "
    f"TFT sequences: "
    f"{missing_target_count}"
)


# ============================================================
# 18. CREATE CONTINUOUS SERIES SEGMENTS
# ============================================================

previous_date = (

    observed_df
    .groupby(
        DISTRICT
    )[
        DATE
    ]
    .shift(1)
)


month_gap = (

    (
        observed_df[
            DATE
        ].dt.year
        -
        previous_date.dt.year
    )

    *
    12

    +

    (
        observed_df[
            DATE
        ].dt.month
        -
        previous_date.dt.month
    )
)


new_segment = (

    previous_date.isna()

    |

    (
        month_gap
        !=
        1
    )
)


observed_df[
    "Segment_Number"
] = (

    new_segment
    .astype(int)

    .groupby(
        observed_df[
            DISTRICT
        ]
    )

    .cumsum()

    .astype(int)
)


observed_df[
    "Series_ID"
] = (

    observed_df[
        DISTRICT
    ]
    .astype(str)

    +
    "__segment_"

    +
    observed_df[
        "Segment_Number"
    ]
    .astype(str)
)


series_count = int(

    observed_df[
        "Series_ID"
    ]
    .nunique()
)


print(
    f"Continuous TFT series segments: "
    f"{series_count}"
)


# ============================================================
# 19. CONTINUITY AUDIT
# ============================================================

segment_audit_records = []


continuity_failures = 0


for series_id, series_df in observed_df.groupby(
    "Series_ID"
):

    series_df = (

        series_df
        .sort_values(
            DATE
        )
    )


    date_differences = (

        series_df[
            DATE
        ]
        .diff()
        .dropna()
    )


    expected_difference = pd.DateOffset(
        months=1
    )


    continuity_ok = True


    if len(series_df) > 1:

        periods = (

            series_df[
                DATE
            ]
            .dt.to_period(
                "M"
            )
        )


        period_numbers = np.array([

            period.year * 12
            +
            period.month

            for period in periods
        ])


        if not np.all(

            np.diff(
                period_numbers
            )
            ==
            1
        ):

            continuity_ok = False


    if not continuity_ok:

        continuity_failures += 1


    segment_audit_records.append({

        "Series_ID":
            series_id,

        "District":
            series_df[
                DISTRICT
            ].iloc[0],

        "Start_Date":
            series_df[
                DATE
            ].min(),

        "End_Date":
            series_df[
                DATE
            ].max(),

        "Rows":
            len(
                series_df
            ),

        "Continuous_Monthly":
            continuity_ok,

        "Enough_For_12_Month_Encoder":
            (
                len(series_df)
                >=
                ENCODER_LENGTH_MONTHS
            ),

        "Enough_For_12_Encoder_Plus_6_Forecast":
            (
                len(series_df)
                >=
                (
                    ENCODER_LENGTH_MONTHS
                    +
                    MAX_FORECAST_HORIZON
                )
            )
    })


segment_audit_df = pd.DataFrame(
    segment_audit_records
)


segment_audit_df.to_csv(

    REPORT_DIR
    / "18_tft_segment_continuity_audit.csv",

    index=False
)


print(
    f"Continuity failures: "
    f"{continuity_failures}"
)


if continuity_failures != 0:

    raise ValueError(

        "A TFT segment contains a "
        "non-consecutive monthly gap."
    )


# ============================================================
# 20. CREATE TFT SPLIT LABEL
# ============================================================

observed_df[
    "TFT_Split"
] = np.select(

    [

        observed_df[
            DATE
        ]
        <=
        CORE_TRAIN_END,

        (
            observed_df[
                DATE
            ]
            >
            CORE_TRAIN_END
        )
        &
        (
            observed_df[
                DATE
            ]
            <=
            FULL_TRAIN_END
        ),

        (
            observed_df[
                DATE
            ]
            >=
            EXTERNAL_VALIDATION_START
        )
        &
        (
            observed_df[
                DATE
            ]
            <=
            EXTERNAL_VALIDATION_END
        )
    ],

    [

        "Core_Train_2015_2022",

        "Internal_Validation_2023",

        "External_Validation_2024"
    ],

    default="Outside_Development"
)


outside_count = int(

    (
        observed_df[
            "TFT_Split"
        ]
        ==
        "Outside_Development"
    )
    .sum()
)


if outside_count != 0:

    raise ValueError(

        "Unexpected rows exist outside "
        "the TFT development periods."
    )


# ============================================================
# 21. DATA TYPE PREPARATION
# ============================================================

observed_df[
    DISTRICT
] = (

    observed_df[
        DISTRICT
    ]
    .astype(str)
)


observed_df[
    "Series_ID"
] = (

    observed_df[
        "Series_ID"
    ]
    .astype(str)
)


observed_df[
    "Month_Cat"
] = (

    observed_df[
        "Month_Cat"
    ]
    .astype(str)
)


observed_df[
    TARGET
] = (

    observed_df[
        TARGET
    ]
    .astype(float)
)


observed_df[
    "Time_Index"
] = (

    observed_df[
        "Time_Index"
    ]
    .astype(int)
)


for column in usable_unknown_reals:

    observed_df[
        column
    ] = (

        observed_df[
            column
        ]
        .astype(float)
    )


# ============================================================
# 22. DEFINE TFT VARIABLE ROLES
# ============================================================

STATIC_CATEGORICALS = [

    DISTRICT
]


KNOWN_CATEGORICALS = [

    "Month_Cat"
]


KNOWN_REALS = [

    "Time_Index",

    "Month_Sin_TFT",

    "Month_Cos_TFT"
]


UNKNOWN_REALS = [

    TARGET

] + usable_unknown_reals


# ============================================================
# 23. VARIABLE MANIFEST
# ============================================================

manifest_records = []


manifest_records.append({

    "Variable":
        DISTRICT,

    "Role":
        "Static Categorical",

    "Original_Source":
        DISTRICT_ORIGINAL,

    "Future_Availability":
        "Static",

    "Notes":
        "District identifier"
})


manifest_records.append({

    "Variable":
        "Month_Cat",

    "Role":
        "Known Time-Varying Categorical",

    "Original_Source":
        "Calendar",

    "Future_Availability":
        "Known",

    "Notes":
        "Calendar month known in advance"
})


for column in KNOWN_REALS:

    manifest_records.append({

        "Variable":
            column,

        "Role":
            "Known Time-Varying Real",

        "Original_Source":
            "Calendar",

        "Future_Availability":
            "Known",

        "Notes":
            "Calendar/time feature known in advance"
    })


manifest_records.append({

    "Variable":
        TARGET,

    "Role":
        "Target / Unknown Time-Varying Real",

    "Original_Source":
        TARGET_ORIGINAL,

    "Future_Availability":
        "Unknown",

    "Notes":
        "Forecast target; future actual values are not model inputs"
})


for column in usable_unknown_reals:

    match = (

        column_mapping_df[

            column_mapping_df[
                "TFT_Column"
            ]
            ==
            column

        ]
    )


    if len(match) > 0:

        original_source = (
            match[
                "Original_Column"
            ]
            .iloc[0]
        )

    else:

        original_source = column


    note = (
        "Historical observed predictor only"
    )


    if original_source in MISNAMED_MONTHLY_COLUMNS:

        note = (

            "Source name contains '_Annual', "
            "but observations are monthly; "
            "treated as monthly historical predictor."
        )


    manifest_records.append({

        "Variable":
            column,

        "Role":
            "Unknown Time-Varying Real",

        "Original_Source":
            original_source,

        "Future_Availability":
            "Unknown",

        "Notes":
            note
    })


variable_manifest_df = pd.DataFrame(
    manifest_records
)


variable_manifest_df.to_csv(

    REPORT_DIR
    / "18_tft_variable_manifest.csv",

    index=False
)


# ============================================================
# 24. ORDER MODEL-READY COLUMNS
# ============================================================

front_columns = [

    "Series_ID",

    DISTRICT,

    DATE,

    "TFT_Split",

    "Segment_Number",

    "Time_Index",

    "Month_Cat",

    "Month_Sin_TFT",

    "Month_Cos_TFT",

    TARGET
]


final_columns = (

    front_columns

    +

    usable_unknown_reals
)


# Remove any duplicate column names.

final_columns = list(

    dict.fromkeys(
        final_columns
    )
)


model_ready_df = (

    observed_df[
        final_columns
    ]
    .copy()
)


# ============================================================
# 25. CREATE OUTPUT DATASETS
# ============================================================

core_train_df = (

    model_ready_df[

        model_ready_df[
            DATE
        ]
        <=
        CORE_TRAIN_END

    ]
    .copy()
)


full_train_df = (

    model_ready_df[

        model_ready_df[
            DATE
        ]
        <=
        FULL_TRAIN_END

    ]
    .copy()
)


# Internal validation needs historical context.
# Therefore this contains all rows through 2023.

internal_validation_context_df = (

    model_ready_df[

        model_ready_df[
            DATE
        ]
        <=
        FULL_TRAIN_END

    ]
    .copy()
)


# External 2024 validation also needs encoder history,
# so this includes all history through 2024.

external_validation_context_df = (

    model_ready_df[
        model_ready_df[
            DATE
        ]
        <=
        EXTERNAL_VALIDATION_END
    ]
    .copy()
)


validation_2024_only_df = (

    model_ready_df[

        (
            model_ready_df[
                DATE
            ]
            >=
            EXTERNAL_VALIDATION_START
        )

        &

        (
            model_ready_df[
                DATE
            ]
            <=
            EXTERNAL_VALIDATION_END
        )

    ]
    .copy()
)


# ============================================================
# 26. TRAIN / VALIDATION DISTRICT AUDIT
# ============================================================

training_districts = set(

    full_train_df[
        DISTRICT
    ]
    .unique()
)


validation_districts = set(

    validation_2024_only_df[
        DISTRICT
    ]
    .unique()
)


unseen_validation_districts = (

    validation_districts

    -

    training_districts
)


print(
    f"\nTraining districts: "
    f"{len(training_districts)}"
)


print(
    f"2024 validation districts: "
    f"{len(validation_districts)}"
)


print(
    f"Unseen validation districts: "
    f"{len(unseen_validation_districts)}"
)


if unseen_validation_districts:

    raise ValueError(

        "2024 contains districts unseen "
        "during training."
    )


# ============================================================
# 27. FINAL LEAKAGE / DATA AUDIT
# ============================================================

if (

    model_ready_df[
        DATE
    ].max()

    >
    EXTERNAL_VALIDATION_END
):

    raise ValueError(

        "2025 rows detected in TFT "
        "development dataset."
    )


if (

    full_train_df[
        DATE
    ].max()

    >
    FULL_TRAIN_END
):

    raise ValueError(

        "2024 entered TFT full training dataset."
    )


if (

    core_train_df[
        DATE
    ].max()

    >
    CORE_TRAIN_END
):

    raise ValueError(

        "2023 entered TFT core training dataset."
    )


if model_ready_df[
    TARGET
].isna().any():

    raise ValueError(

        "Missing target values remain "
        "inside TFT sequences."
    )


if model_ready_df[
    usable_unknown_reals
].isna().any().any():

    raise ValueError(

        "Missing predictor values remain "
        "inside model-ready TFT data."
    )


print(
    "\nFinal leakage/data audit: PASS"
)


# ============================================================
# 28. SAVE MODEL-READY FILES
# ============================================================

development_output_path = (

    TFT_DIR
    / "18_tft_development_through_2024.csv"
)


core_train_output_path = (

    TFT_DIR
    / "18_tft_core_train_2015_2022.csv"
)


full_train_output_path = (

    TFT_DIR
    / "18_tft_full_train_2015_2023.csv"
)


internal_context_output_path = (

    TFT_DIR
    / "18_tft_internal_validation_context_through_2023.csv"
)


external_context_output_path = (

    TFT_DIR
    / "18_tft_external_validation_context_through_2024.csv"
)


validation_only_output_path = (

    TFT_DIR
    / "18_tft_validation_2024_only.csv"
)


model_ready_df.to_csv(

    development_output_path,

    index=False
)


core_train_df.to_csv(

    core_train_output_path,

    index=False
)


full_train_df.to_csv(

    full_train_output_path,

    index=False
)


internal_validation_context_df.to_csv(

    internal_context_output_path,

    index=False
)


external_validation_context_df.to_csv(

    external_context_output_path,

    index=False
)


validation_2024_only_df.to_csv(

    validation_only_output_path,

    index=False
)


# ============================================================
# 29. SUMMARY REPORT
# ============================================================

summary_df = pd.DataFrame([{

    "Input_Rows":
        len(df),

    "Rows_Excluded_2025_Plus":
        rows_2025_or_later,

    "Development_Rows_Through_2024":
        len(development_df),

    "Target_Missing_Rows_Not_Imputed":
        missing_target_count,

    "Model_Ready_Observed_Target_Rows":
        len(model_ready_df),

    "Districts":
        model_ready_df[
            DISTRICT
        ].nunique(),

    "Continuous_Series_Segments":
        series_count,

    "Usable_Unknown_Real_Predictors":
        len(
            usable_unknown_reals
        ),

    "Core_Train_Rows_2015_2022":
        len(
            core_train_df
        ),

    "Full_Train_Rows_2015_2023":
        len(
            full_train_df
        ),

    "Validation_2024_Rows":
        len(
            validation_2024_only_df
        ),

    "Encoder_Length_Months":
        ENCODER_LENGTH_MONTHS,

    "Maximum_Forecast_Horizon_Months":
        MAX_FORECAST_HORIZON,

    "Remaining_Predictor_NaNs":
        remaining_predictor_nans,

    "Unseen_Validation_Districts":
        len(
            unseen_validation_districts
        )
}])


summary_df.to_csv(

    REPORT_DIR
    / "18_tft_data_preparation_summary.csv",

    index=False
)


# ============================================================
# 30. FINAL OUTPUT
# ============================================================

print(
    "\n"
    +
    "=" * 115
)

print(
    "STEP 18 - TFT DATA PREPARATION SUMMARY"
)

print(
    "=" * 115
)


print(
    f"\nDevelopment rows through 2024 : "
    f"{len(development_df)}"
)


print(
    f"Target-missing rows excluded  : "
    f"{missing_target_count}"
)


print(
    f"Model-ready rows              : "
    f"{len(model_ready_df)}"
)


print(
    f"Districts                     : "
    f"{model_ready_df[DISTRICT].nunique()}"
)


print(
    f"Continuous series segments    : "
    f"{series_count}"
)


print(
    f"Historical unknown predictors : "
    f"{len(usable_unknown_reals)}"
)


print(
    f"Core train rows (<=2022)      : "
    f"{len(core_train_df)}"
)


print(
    f"Full train rows (<=2023)      : "
    f"{len(full_train_df)}"
)


print(
    f"2024 validation rows          : "
    f"{len(validation_2024_only_df)}"
)


print(
    f"Unseen validation districts   : "
    f"{len(unseen_validation_districts)}"
)


print(
    "\nTFT variable roles:"
)


print(
    f"- Static categoricals : "
    f"{STATIC_CATEGORICALS}"
)


print(
    f"- Known categoricals  : "
    f"{KNOWN_CATEGORICALS}"
)


print(
    f"- Known reals         : "
    f"{KNOWN_REALS}"
)


print(
    f"- Unknown reals       : "
    f"{len(UNKNOWN_REALS)} "
    f"(including target)"
)


print(
    "\nLeakage protections:"
)


print(
    "- 2025 excluded"
)


print(
    "- 2024 not used to learn predictor medians"
)


print(
    "- Target missing values not imputed"
)


print(
    "- Missing-target blocks separated into "
    "continuous sequences"
)


print(
    "- Future unknown health/environment values "
    "remain future-unknown"
)


print(
    "- Only calendar/time variables are "
    "known-future inputs"
)


print(
    "- SAM/MAM corrected as monthly "
    "time-varying predictors"
)


print(
    "\nModel-ready TFT files saved to:"
)

print(
    TFT_DIR
)


print(
    "\nReports saved to:"
)

print(
    REPORT_DIR
)


print(
    "\nSTEP 18 - TFT DATA PREPARATION COMPLETE"
)

print(
    "=" * 115
)