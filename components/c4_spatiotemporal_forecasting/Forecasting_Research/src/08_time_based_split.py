# ============================================================
# STEP 08 - CHRONOLOGICAL TRAIN / VALIDATION / TEST SPLIT
# Childhood Malnutrition Forecasting Research
#
# TRAIN      : Forecast target dates from 2015 to 2023
# VALIDATION : Forecast target dates in 2024
# TEST       : Forecast target dates in 2025
#
# IMPORTANT:
# - Split is based on Forecast_Target_Date
# - No random split is used
# - No imputation is performed here
# - No scaling is performed here
# - No feature selection is performed here
# - No model is trained here
# ============================================================

import pandas as pd
from pathlib import Path


# ============================================================
# 1. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

SPLIT_DIR = (
    BASE_DIR
    / "data"
    / "splits"
)

REPORT_DIR = (
    BASE_DIR
    / "outputs"
    / "reports"
)

SPLIT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. SPLIT DEFINITIONS
# ============================================================

TRAIN_END = pd.Timestamp("2023-12-31")

VALIDATION_START = pd.Timestamp("2024-01-01")
VALIDATION_END = pd.Timestamp("2024-12-31")

TEST_START = pd.Timestamp("2025-01-01")
TEST_END = pd.Timestamp("2025-12-31")


FORECAST_HORIZONS = [
    1,
    3,
    6
]


print("\n" + "=" * 100)
print("STEP 08 - CHRONOLOGICAL TRAIN / VALIDATION / TEST SPLIT")
print("=" * 100)

print("\nSplit strategy:")

print(
    "TRAIN      : Forecast_Target_Date <= 2023-12-31"
)

print(
    "VALIDATION : Forecast_Target_Date during 2024"
)

print(
    "TEST       : Forecast_Target_Date during 2025"
)

print(
    "\nIMPORTANT: Split is based on TARGET DATE, "
    "not forecast-origin year."
)


# ============================================================
# 3. STORAGE FOR REPORTS
# ============================================================

split_summary_records = []

split_audit_records = []


# ============================================================
# 4. PROCESS EACH FORECAST HORIZON
# ============================================================

for horizon in FORECAST_HORIZONS:

    print("\n" + "-" * 100)

    print(
        f"PROCESSING H{horizon} "
        f"({horizon}-MONTH AHEAD FORECAST)"
    )

    print("-" * 100)


    # --------------------------------------------------------
    # 4.1 INPUT FILE
    # --------------------------------------------------------

    input_path = (
        PROCESSED_DIR
        /
        f"malnutrition_features_h{horizon}.csv"
    )


    if not input_path.exists():

        raise FileNotFoundError(
            f"Required file not found: {input_path}"
        )


    df = pd.read_csv(
        input_path
    )


    # --------------------------------------------------------
    # COMPATIBILITY FIX FOR CORRECTED STEP 07
    # --------------------------------------------------------
    # Corrected Step 07 saves the horizon column as
    # "Forecast_Horizon". This Step 08 script expects
    # "Forecast_Horizon_Months". Rename it here before
    # the required-column validation.

    if (
        "Forecast_Horizon" in df.columns
        and
        "Forecast_Horizon_Months" not in df.columns
    ):

        df = df.rename(
            columns={
                "Forecast_Horizon": "Forecast_Horizon_Months"
            }
        )

        print(
            "Column renamed: "
            "Forecast_Horizon -> Forecast_Horizon_Months"
        )


    print(
        f"\nDataset loaded: {input_path.name}"
    )

    print(
        f"Rows loaded: {len(df)}"
    )


    # --------------------------------------------------------
    # 4.2 REQUIRED COLUMN CHECK
    # --------------------------------------------------------

    required_columns = [
        "District",
        "Forecast_Origin_Date",
        "Forecast_Target_Date",
        "Forecast_Target",
        "Forecast_Horizon_Months"
    ]


    missing_columns = [

        column
        for column in required_columns

        if column not in df.columns
    ]


    if missing_columns:

        raise ValueError(
            f"H{horizon}: Missing required columns: "
            + ", ".join(missing_columns)
        )


    print(
        "Required columns found."
    )


    # --------------------------------------------------------
    # 4.3 DATE CONVERSION
    # --------------------------------------------------------

    df[
        "Forecast_Origin_Date"
    ] = pd.to_datetime(
        df[
            "Forecast_Origin_Date"
        ],
        errors="coerce"
    )


    df[
        "Forecast_Target_Date"
    ] = pd.to_datetime(
        df[
            "Forecast_Target_Date"
        ],
        errors="coerce"
    )


    if (
        df[
            "Forecast_Origin_Date"
        ]
        .isna()
        .any()
    ):

        raise ValueError(
            f"H{horizon}: Invalid Forecast_Origin_Date detected."
        )


    if (
        df[
            "Forecast_Target_Date"
        ]
        .isna()
        .any()
    ):

        raise ValueError(
            f"H{horizon}: Invalid Forecast_Target_Date detected."
        )


    # --------------------------------------------------------
    # 4.4 TARGET LABEL CHECK
    # --------------------------------------------------------

    missing_targets = (
        df[
            "Forecast_Target"
        ]
        .isna()
        .sum()
    )


    print(
        f"Missing forecast targets: "
        f"{missing_targets}"
    )


    if missing_targets > 0:

        raise ValueError(
            f"H{horizon}: Dataset contains missing "
            f"forecast target labels."
        )


    # --------------------------------------------------------
    # 4.5 HORIZON VALUE CHECK
    # --------------------------------------------------------

    horizon_values = (
        df[
            "Forecast_Horizon_Months"
        ]
        .dropna()
        .unique()
    )


    if (
        len(horizon_values) != 1
        or horizon_values[0] != horizon
    ):

        raise ValueError(
            f"H{horizon}: Forecast horizon column "
            f"does not match expected horizon."
        )


    # --------------------------------------------------------
    # 4.6 VERIFY TARGET DATE IS AFTER ORIGIN DATE
    # --------------------------------------------------------

    invalid_temporal_order = (

        df[
            "Forecast_Target_Date"
        ]
        <=
        df[
            "Forecast_Origin_Date"
        ]

    ).sum()


    print(
        f"Target dates not after origin dates: "
        f"{invalid_temporal_order}"
    )


    if invalid_temporal_order > 0:

        raise ValueError(
            f"H{horizon}: Temporal ordering error detected."
        )


    # --------------------------------------------------------
    # 4.7 VERIFY EXACT HORIZON ALIGNMENT
    # --------------------------------------------------------

    expected_target_period = (

        df[
            "Forecast_Origin_Date"
        ]
        .dt.to_period("M")
        +
        horizon
    )


    actual_target_period = (

        df[
            "Forecast_Target_Date"
        ]
        .dt.to_period("M")
    )


    horizon_alignment_mismatch = (

        expected_target_period
        !=
        actual_target_period

    ).sum()


    print(
        f"Horizon alignment mismatches: "
        f"{horizon_alignment_mismatch}"
    )


    if horizon_alignment_mismatch > 0:

        raise ValueError(
            f"H{horizon}: Forecast horizon alignment failed."
        )


    # ========================================================
    # 5. CHRONOLOGICAL SPLIT
    # ========================================================

    print(
        "\nCreating chronological splits..."
    )


    train_df = (

        df[
            df[
                "Forecast_Target_Date"
            ]
            <= TRAIN_END
        ]
        .copy()
    )


    validation_df = (

        df[
            (
                df[
                    "Forecast_Target_Date"
                ]
                >= VALIDATION_START
            )
            &
            (
                df[
                    "Forecast_Target_Date"
                ]
                <= VALIDATION_END
            )
        ]
        .copy()
    )


    test_df = (

        df[
            (
                df[
                    "Forecast_Target_Date"
                ]
                >= TEST_START
            )
            &
            (
                df[
                    "Forecast_Target_Date"
                ]
                <= TEST_END
            )
        ]
        .copy()
    )


    # --------------------------------------------------------
    # 5.1 CHECK UNASSIGNED ROWS
    # --------------------------------------------------------

    assigned_indices = (

        set(train_df.index)
        |
        set(validation_df.index)
        |
        set(test_df.index)
    )


    unassigned_rows = (
        len(df)
        -
        len(assigned_indices)
    )


    print(
        f"Unassigned rows: "
        f"{unassigned_rows}"
    )


    if unassigned_rows > 0:

        raise ValueError(
            f"H{horizon}: Some rows were not assigned "
            f"to Train, Validation or Test."
        )


    # --------------------------------------------------------
    # 5.2 CHECK OVERLAPPING ROWS
    # --------------------------------------------------------

    train_indices = set(
        train_df.index
    )

    validation_indices = set(
        validation_df.index
    )

    test_indices = set(
        test_df.index
    )


    overlap_train_validation = len(
        train_indices
        &
        validation_indices
    )


    overlap_train_test = len(
        train_indices
        &
        test_indices
    )


    overlap_validation_test = len(
        validation_indices
        &
        test_indices
    )


    total_overlap = (
        overlap_train_validation
        +
        overlap_train_test
        +
        overlap_validation_test
    )


    print(
        f"Split overlap rows: "
        f"{total_overlap}"
    )


    if total_overlap > 0:

        raise ValueError(
            f"H{horizon}: Split overlap detected."
        )


    # ========================================================
    # 6. SORT EACH SPLIT CHRONOLOGICALLY
    # ========================================================

    sort_columns = [
        "Forecast_Target_Date",
        "District"
    ]


    train_df = (
        train_df
        .sort_values(
            sort_columns
        )
        .reset_index(drop=True)
    )


    validation_df = (
        validation_df
        .sort_values(
            sort_columns
        )
        .reset_index(drop=True)
    )


    test_df = (
        test_df
        .sort_values(
            sort_columns
        )
        .reset_index(drop=True)
    )


    # ========================================================
    # 7. TEMPORAL BOUNDARY AUDIT
    # ========================================================

    train_max_target_date = (
        train_df[
            "Forecast_Target_Date"
        ]
        .max()
    )


    validation_min_target_date = (
        validation_df[
            "Forecast_Target_Date"
        ]
        .min()
    )


    validation_max_target_date = (
        validation_df[
            "Forecast_Target_Date"
        ]
        .max()
    )


    test_min_target_date = (
        test_df[
            "Forecast_Target_Date"
        ]
        .min()
    )


    chronological_order_passed = (

        train_max_target_date
        <
        validation_min_target_date
        and
        validation_max_target_date
        <
        test_min_target_date

    )


    split_audit_records.append({

        "Horizon_Months":
            horizon,

        "Target_After_Origin":
            invalid_temporal_order == 0,

        "Exact_Horizon_Alignment":
            horizon_alignment_mismatch == 0,

        "No_Split_Overlap":
            total_overlap == 0,

        "No_Unassigned_Rows":
            unassigned_rows == 0,

        "Chronological_Order":
            chronological_order_passed
    })


    if not chronological_order_passed:

        raise ValueError(
            f"H{horizon}: Chronological split "
            f"boundary check failed."
        )


    # ========================================================
    # 8. ADD SPLIT LABEL
    # ========================================================

    train_df[
        "Data_Split"
    ] = "TRAIN"


    validation_df[
        "Data_Split"
    ] = "VALIDATION"


    test_df[
        "Data_Split"
    ] = "TEST"


    # ========================================================
    # 9. SAVE SPLIT FILES
    # ========================================================

    train_path = (
        SPLIT_DIR
        /
        f"h{horizon}_train.csv"
    )


    validation_path = (
        SPLIT_DIR
        /
        f"h{horizon}_validation.csv"
    )


    test_path = (
        SPLIT_DIR
        /
        f"h{horizon}_test.csv"
    )


    train_df.to_csv(
        train_path,
        index=False
    )


    validation_df.to_csv(
        validation_path,
        index=False
    )


    test_df.to_csv(
        test_path,
        index=False
    )


    # ========================================================
    # 10. SUMMARY
    # ========================================================

    print(
        f"\nH{horizon} split complete:"
    )


    print(
        f"TRAIN rows      : "
        f"{len(train_df)}"
    )


    print(
        f"VALIDATION rows : "
        f"{len(validation_df)}"
    )


    print(
        f"TEST rows       : "
        f"{len(test_df)}"
    )


    print(
        "\nTarget date ranges:"
    )


    print(
        f"TRAIN      : "
        f"{train_df['Forecast_Target_Date'].min().date()} "
        f"to "
        f"{train_df['Forecast_Target_Date'].max().date()}"
    )


    print(
        f"VALIDATION : "
        f"{validation_df['Forecast_Target_Date'].min().date()} "
        f"to "
        f"{validation_df['Forecast_Target_Date'].max().date()}"
    )


    print(
        f"TEST       : "
        f"{test_df['Forecast_Target_Date'].min().date()} "
        f"to "
        f"{test_df['Forecast_Target_Date'].max().date()}"
    )


    # We intentionally do NOT print target means or
    # target distributions for the TEST set.
    #
    # This helps keep the final test set as a lockbox
    # during model development.


    split_summary_records.extend([

        {
            "Horizon_Months":
                horizon,

            "Split":
                "TRAIN",

            "Rows":
                len(train_df),

            "Minimum_Target_Date":
                train_df[
                    "Forecast_Target_Date"
                ].min(),

            "Maximum_Target_Date":
                train_df[
                    "Forecast_Target_Date"
                ].max()
        },

        {
            "Horizon_Months":
                horizon,

            "Split":
                "VALIDATION",

            "Rows":
                len(validation_df),

            "Minimum_Target_Date":
                validation_df[
                    "Forecast_Target_Date"
                ].min(),

            "Maximum_Target_Date":
                validation_df[
                    "Forecast_Target_Date"
                ].max()
        },

        {
            "Horizon_Months":
                horizon,

            "Split":
                "TEST",

            "Rows":
                len(test_df),

            "Minimum_Target_Date":
                test_df[
                    "Forecast_Target_Date"
                ].min(),

            "Maximum_Target_Date":
                test_df[
                    "Forecast_Target_Date"
                ].max()
        }
    ])


# ============================================================
# 11. SAVE SPLIT SUMMARY REPORT
# ============================================================

split_summary_df = pd.DataFrame(
    split_summary_records
)


split_summary_df.to_csv(
    REPORT_DIR
    / "08_time_based_split_summary.csv",
    index=False
)


print("\n" + "=" * 100)
print("SPLIT SUMMARY")
print("=" * 100)


print(
    split_summary_df
    .to_string(index=False)
)


# ============================================================
# 12. SAVE SPLIT AUDIT REPORT
# ============================================================

split_audit_df = pd.DataFrame(
    split_audit_records
)


split_audit_df[
    "All_Checks_Passed"
] = (

    split_audit_df[
        [
            "Target_After_Origin",
            "Exact_Horizon_Alignment",
            "No_Split_Overlap",
            "No_Unassigned_Rows",
            "Chronological_Order"
        ]
    ]
    .all(axis=1)
)


print("\n" + "=" * 100)
print("TEMPORAL LEAKAGE / SPLIT AUDIT")
print("=" * 100)


print(
    split_audit_df
    .to_string(index=False)
)


split_audit_df.to_csv(
    REPORT_DIR
    / "08_time_split_leakage_audit.csv",
    index=False
)


if not (
    split_audit_df[
        "All_Checks_Passed"
    ]
    .all()
):

    raise ValueError(
        "Time-based split audit FAILED."
    )


# ============================================================
# 13. FINAL METHODOLOGY SUMMARY
# ============================================================

print("\n" + "=" * 100)
print("STEP 08 SUMMARY")
print("=" * 100)


print(
    "Chronological splitting completed for "
    "H1, H3 and H6."
)


print(
    "\nTRAIN:"
)

print(
    "Forecast targets up to December 2023."
)


print(
    "\nVALIDATION:"
)

print(
    "Forecast targets from January to "
    "December 2024."
)


print(
    "\nTEST:"
)

print(
    "Forecast targets from January to "
    "December 2025."
)


print(
    "\nLeakage protections:"
)

print(
    "- No random train-test split"
)

print(
    "- Split based on Forecast_Target_Date"
)

print(
    "- 2024 target labels are excluded from training"
)

print(
    "- 2025 target labels are excluded from training "
    "and model selection"
)

print(
    "- Test target statistics are not used during "
    "model development"
)

print(
    "- No imputation performed before split"
)

print(
    "- No scaling performed before split"
)

print(
    "- No supervised feature selection performed "
    "before split"
)

print(
    "- No model trained in this step"
)


print(
    "\nIMPORTANT REAL-WORLD INTERPRETATION:"
)

print(
    "For a forecast made later in 2025, historical "
    "observations from earlier months may be used "
    "if they would genuinely be available at that "
    "forecast origin."
)

print(
    "However, the future target being predicted is "
    "never used to fit the model."
)


print(
    "\nNEXT STEP:"
)

print(
    "Train-only preprocessing and feature analysis."
)


print("\nSplit datasets saved to:")
print(SPLIT_DIR)

print("\nReports saved to:")
print(REPORT_DIR)


print(
    "\nSTEP 08 - CHRONOLOGICAL TRAIN / "
    "VALIDATION / TEST SPLIT COMPLETE"
)

print("=" * 100)