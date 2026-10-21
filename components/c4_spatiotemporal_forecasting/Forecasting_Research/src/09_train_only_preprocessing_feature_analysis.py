# ============================================================
# STEP 09 - TRAIN-ONLY PREPROCESSING + FEATURE ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# IMPORTANT:
# - Feature analysis uses TRAIN data only
# - Missing-value statistics are learned from TRAIN only
# - Validation/Test never determine preprocessing values
# - Test target is not analysed
# - No model is trained in this step
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 1. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SPLIT_DIR = (
    BASE_DIR
    / "data"
    / "splits"
)

MODEL_READY_DIR = (
    BASE_DIR
    / "data"
    / "model_ready"
)

REPORT_DIR = (
    BASE_DIR
    / "outputs"
    / "reports"
)

MODEL_READY_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. SETTINGS
# ============================================================

HORIZONS = [1, 3, 6]

TARGET = "Forecast_Target"

HIGH_MISSING_THRESHOLD = 40.0

HIGH_CORRELATION_THRESHOLD = 0.98


# Columns used for identification / metadata.
# These are not treated as ordinary numerical predictors.

METADATA_COLUMNS = [
    "District",
    "Forecast_Origin_Date",
    "Year",
    "Month",
    "Forecast_Target_Date",
    "Forecast_Target",
    "Forecast_Horizon_Months",
    "Data_Split"
]


print("\n" + "=" * 105)
print("STEP 09 - TRAIN-ONLY PREPROCESSING + FEATURE ANALYSIS")
print("=" * 105)

print(
    "\nIMPORTANT:"
)

print(
    "All feature-quality decisions and imputation "
    "statistics are learned from TRAINING DATA ONLY."
)

print(
    "Validation and test sets do not influence "
    "preprocessing decisions."
)


# ============================================================
# 3. STORAGE FOR OVERALL SUMMARY
# ============================================================

overall_summary = []


# ============================================================
# 4. PROCESS EACH FORECAST HORIZON
# ============================================================

for horizon in HORIZONS:

    print("\n" + "=" * 105)

    print(
        f"H{horizon} - {horizon}-MONTH AHEAD FORECAST"
    )

    print("=" * 105)


    # ========================================================
    # 4.1 LOAD TRAIN / VALIDATION / TEST
    # ========================================================

    train_path = (
        SPLIT_DIR
        / f"h{horizon}_train.csv"
    )

    validation_path = (
        SPLIT_DIR
        / f"h{horizon}_validation.csv"
    )

    test_path = (
        SPLIT_DIR
        / f"h{horizon}_test.csv"
    )


    for path in [
        train_path,
        validation_path,
        test_path
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Required split file not found: {path}"
            )


    train_df = pd.read_csv(
        train_path
    )

    validation_df = pd.read_csv(
        validation_path
    )

    test_df = pd.read_csv(
        test_path
    )


    print(
        f"\nTRAIN rows      : {len(train_df)}"
    )

    print(
        f"VALIDATION rows : {len(validation_df)}"
    )

    print(
        f"TEST rows       : {len(test_df)}"
    )


    # ========================================================
    # 4.2 DATE CONVERSION
    # ========================================================

    for dataset in [
        train_df,
        validation_df,
        test_df
    ]:

        dataset[
            "Forecast_Origin_Date"
        ] = pd.to_datetime(
            dataset[
                "Forecast_Origin_Date"
            ],
            errors="coerce"
        )

        dataset[
            "Forecast_Target_Date"
        ] = pd.to_datetime(
            dataset[
                "Forecast_Target_Date"
            ],
            errors="coerce"
        )


    # ========================================================
    # 4.3 DATA SPLIT LABEL CHECK
    # ========================================================

    train_label_ok = (
        train_df["Data_Split"]
        .eq("TRAIN")
        .all()
    )

    validation_label_ok = (
        validation_df["Data_Split"]
        .eq("VALIDATION")
        .all()
    )

    test_label_ok = (
        test_df["Data_Split"]
        .eq("TEST")
        .all()
    )


    if not (
        train_label_ok
        and validation_label_ok
        and test_label_ok
    ):

        raise ValueError(
            f"H{horizon}: Data split label check failed."
        )


    print(
        "\nSplit labels verified."
    )


    # ========================================================
    # 4.4 SCHEMA CONSISTENCY CHECK
    # ========================================================

    train_columns = set(
        train_df.columns
    )

    validation_columns = set(
        validation_df.columns
    )

    test_columns = set(
        test_df.columns
    )


    schema_match = (
        train_columns
        ==
        validation_columns
        ==
        test_columns
    )


    print(
        f"Schema match across splits: "
        f"{schema_match}"
    )


    if not schema_match:

        raise ValueError(
            f"H{horizon}: Train/Validation/Test "
            f"schemas are different."
        )


    # ========================================================
    # 5. DEFINE CANDIDATE MODEL FEATURES
    # ========================================================

    print("\n" + "-" * 105)
    print("1. CANDIDATE FEATURE DEFINITION")
    print("-" * 105)


    candidate_features = [

        column
        for column in train_df.columns

        if column not in METADATA_COLUMNS
    ]


    # Ensure features are numeric.
    candidate_numeric_features = [

        column
        for column in candidate_features

        if pd.api.types.is_numeric_dtype(
            train_df[column]
        )
    ]


    print(
        f"Candidate numeric features: "
        f"{len(candidate_numeric_features)}"
    )


    # ========================================================
    # 6. TRAIN-ONLY FEATURE QUALITY ANALYSIS
    # ========================================================

    print("\n" + "-" * 105)
    print("2. TRAIN-ONLY FEATURE QUALITY ANALYSIS")
    print("-" * 105)


    feature_quality_records = []


    for feature in candidate_numeric_features:

        series = (
            train_df[feature]
        )

        non_missing_count = (
            series
            .notna()
            .sum()
        )

        missing_count = (
            series
            .isna()
            .sum()
        )

        missing_percentage = (
            missing_count
            /
            len(train_df)
            *
            100
        )

        unique_count = (
            series
            .dropna()
            .nunique()
        )


        feature_quality_records.append({

            "Feature":
                feature,

            "Train_Non_Missing_Count":
                non_missing_count,

            "Train_Missing_Count":
                missing_count,

            "Train_Missing_Percentage":
                round(
                    missing_percentage,
                    2
                ),

            "Train_Unique_Count":
                unique_count,

            "All_Missing_In_Train":
                non_missing_count == 0,

            "Constant_In_Train":
                (
                    non_missing_count > 0
                    and
                    unique_count <= 1
                ),

            "High_Missingness_Flag":
                (
                    missing_percentage
                    >
                    HIGH_MISSING_THRESHOLD
                )
        })


    feature_quality_df = pd.DataFrame(
        feature_quality_records
    )


    feature_quality_df = (
        feature_quality_df
        .sort_values(
            [
                "Train_Missing_Percentage",
                "Feature"
            ],
            ascending=[
                False,
                True
            ]
        )
    )


    print(
        feature_quality_df
        .head(30)
        .to_string(index=False)
    )


    feature_quality_df.to_csv(
        REPORT_DIR
        / f"09_h{horizon}_train_feature_quality.csv",
        index=False
    )


    # ========================================================
    # 7. REMOVE ONLY OBJECTIVELY UNUSABLE FEATURES
    # ========================================================

    print("\n" + "-" * 105)
    print("3. OBJECTIVE FEATURE FILTERING")
    print("-" * 105)


    all_missing_features = (
        feature_quality_df.loc[
            feature_quality_df[
                "All_Missing_In_Train"
            ],
            "Feature"
        ]
        .tolist()
    )


    constant_features = (
        feature_quality_df.loc[
            feature_quality_df[
                "Constant_In_Train"
            ],
            "Feature"
        ]
        .tolist()
    )


    automatically_removed_features = sorted(
        set(
            all_missing_features
            +
            constant_features
        )
    )


    usable_features = [

        feature
        for feature in candidate_numeric_features

        if feature
        not in automatically_removed_features
    ]


    print(
        f"All-missing training features : "
        f"{len(all_missing_features)}"
    )

    print(
        f"Constant training features    : "
        f"{len(constant_features)}"
    )

    print(
        f"Automatically removed         : "
        f"{len(automatically_removed_features)}"
    )

    print(
        f"Remaining usable features     : "
        f"{len(usable_features)}"
    )


    # ========================================================
    # 8. TRAIN-ONLY TARGET CORRELATION ANALYSIS
    # ========================================================

    print("\n" + "-" * 105)
    print("4. TRAIN-ONLY TARGET ASSOCIATION ANALYSIS")
    print("-" * 105)


    correlation_records = []


    for feature in usable_features:

        valid_pair = (
            train_df[
                [
                    feature,
                    TARGET
                ]
            ]
            .dropna()
        )


        if (
            len(valid_pair) >= 3
            and
            valid_pair[feature].nunique() > 1
        ):

            pearson_correlation = (
                valid_pair[feature]
                .corr(
                    valid_pair[TARGET],
                    method="pearson"
                )
            )


            spearman_correlation = (
                valid_pair[feature]
                .corr(
                    valid_pair[TARGET],
                    method="spearman"
                )
            )

        else:

            pearson_correlation = np.nan
            spearman_correlation = np.nan


        correlation_records.append({

            "Feature":
                feature,

            "Valid_Training_Pairs":
                len(valid_pair),

            "Pearson_Correlation":
                pearson_correlation,

            "Spearman_Correlation":
                spearman_correlation
        })


    target_correlation_df = pd.DataFrame(
        correlation_records
    )


    target_correlation_df[
        "Absolute_Pearson"
    ] = (
        target_correlation_df[
            "Pearson_Correlation"
        ]
        .abs()
    )


    target_correlation_df = (
        target_correlation_df
        .sort_values(
            "Absolute_Pearson",
            ascending=False
        )
    )


    print(
        target_correlation_df
        .head(25)
        .round(4)
        .to_string(index=False)
    )


    target_correlation_df.to_csv(
        REPORT_DIR
        / f"09_h{horizon}_train_target_correlations.csv",
        index=False
    )


    print(
        "\nIMPORTANT:"
    )

    print(
        "Correlation is used for feature understanding only."
    )

    print(
        "Features are NOT automatically selected or removed "
        "based only on target correlation."
    )


    # ========================================================
    # 9. TRAIN-ONLY INTER-FEATURE CORRELATION ANALYSIS
    # ========================================================

    print("\n" + "-" * 105)
    print("5. TRAIN-ONLY INTER-FEATURE REDUNDANCY ANALYSIS")
    print("-" * 105)


    train_feature_matrix = (
        train_df[
            usable_features
        ]
    )


    feature_correlation_matrix = (
        train_feature_matrix
        .corr(
            method="pearson"
        )
    )


    high_corr_pairs = []


    for i in range(
        len(usable_features)
    ):

        for j in range(
            i + 1,
            len(usable_features)
        ):

            feature_a = (
                usable_features[i]
            )

            feature_b = (
                usable_features[j]
            )


            correlation = (
                feature_correlation_matrix
                .loc[
                    feature_a,
                    feature_b
                ]
            )


            if (
                pd.notna(correlation)
                and
                abs(correlation)
                >= HIGH_CORRELATION_THRESHOLD
            ):

                high_corr_pairs.append({

                    "Feature_A":
                        feature_a,

                    "Feature_B":
                        feature_b,

                    "Pearson_Correlation":
                        correlation,

                    "Absolute_Correlation":
                        abs(correlation)
                })


    high_corr_pairs_df = pd.DataFrame(
        high_corr_pairs
    )


    if not high_corr_pairs_df.empty:

        high_corr_pairs_df = (
            high_corr_pairs_df
            .sort_values(
                "Absolute_Correlation",
                ascending=False
            )
        )


        print(
            high_corr_pairs_df
            .head(30)
            .round(4)
            .to_string(index=False)
        )

    else:

        print(
            "No feature pairs exceeded the "
            f"{HIGH_CORRELATION_THRESHOLD} threshold."
        )


    high_corr_pairs_df.to_csv(
        REPORT_DIR
        / f"09_h{horizon}_high_feature_correlations.csv",
        index=False
    )


    print(
        "\nHighly correlated feature pairs are flagged only."
    )

    print(
        "They are NOT automatically removed because "
        "tree-based models can handle redundancy differently "
        "from linear models."
    )


    # ========================================================
    # 10. TRAIN-ONLY MEDIAN IMPUTATION STATISTICS
    # ========================================================

    print("\n" + "-" * 105)
    print("6. TRAIN-ONLY IMPUTATION STATISTICS")
    print("-" * 105)


    train_medians = (
        train_df[
            usable_features
        ]
        .median(
            numeric_only=True
        )
    )


    if train_medians.isna().any():

        problematic_features = (
            train_medians[
                train_medians.isna()
            ]
            .index
            .tolist()
        )

        raise ValueError(
            f"H{horizon}: Median could not be calculated "
            f"for: {problematic_features}"
        )


    train_median_report = pd.DataFrame({

        "Feature":
            train_medians.index,

        "Train_Median":
            train_medians.values
    })


    train_median_report.to_csv(
        REPORT_DIR
        / f"09_h{horizon}_train_imputation_medians.csv",
        index=False
    )


    print(
        f"Train-only medians learned for "
        f"{len(train_medians)} features."
    )


    # ========================================================
    # 11. APPLY TRAIN-LEARNED IMPUTATION TO ALL SPLITS
    # ========================================================

    print("\n" + "-" * 105)
    print("7. APPLY TRAIN-LEARNED IMPUTATION")
    print("-" * 105)


    train_processed = (
        train_df.copy()
    )

    validation_processed = (
        validation_df.copy()
    )

    test_processed = (
        test_df.copy()
    )


    # Remove unusable features from all datasets.

    train_processed.drop(
        columns=automatically_removed_features,
        inplace=True,
        errors="ignore"
    )

    validation_processed.drop(
        columns=automatically_removed_features,
        inplace=True,
        errors="ignore"
    )

    test_processed.drop(
        columns=automatically_removed_features,
        inplace=True,
        errors="ignore"
    )


    # Apply TRAIN medians.
    # Validation/Test statistics are never used.

    train_processed[
        usable_features
    ] = (
        train_processed[
            usable_features
        ]
        .fillna(
            train_medians
        )
    )


    validation_processed[
        usable_features
    ] = (
        validation_processed[
            usable_features
        ]
        .fillna(
            train_medians
        )
    )


    test_processed[
        usable_features
    ] = (
        test_processed[
            usable_features
        ]
        .fillna(
            train_medians
        )
    )


    # ========================================================
    # 12. CHECK REMAINING FEATURE MISSINGNESS
    # ========================================================

    train_remaining_missing = (
        train_processed[
            usable_features
        ]
        .isna()
        .sum()
        .sum()
    )


    validation_remaining_missing = (
        validation_processed[
            usable_features
        ]
        .isna()
        .sum()
        .sum()
    )


    test_remaining_missing = (
        test_processed[
            usable_features
        ]
        .isna()
        .sum()
        .sum()
    )


    print(
        f"Remaining TRAIN feature NaNs      : "
        f"{train_remaining_missing}"
    )

    print(
        f"Remaining VALIDATION feature NaNs : "
        f"{validation_remaining_missing}"
    )

    print(
        f"Remaining TEST feature NaNs       : "
        f"{test_remaining_missing}"
    )


    if (
        train_remaining_missing > 0
        or
        validation_remaining_missing > 0
        or
        test_remaining_missing > 0
    ):

        raise ValueError(
            f"H{horizon}: Missing values remain "
            f"after train-only median imputation."
        )


    # ========================================================
    # 13. DISTRICT CATEGORY CHECK
    # ========================================================

    print("\n" + "-" * 105)
    print("8. DISTRICT CATEGORY CHECK")
    print("-" * 105)


    train_districts = set(
        train_processed[
            "District"
        ]
        .dropna()
        .unique()
    )


    validation_districts = set(
        validation_processed[
            "District"
        ]
        .dropna()
        .unique()
    )


    test_districts = set(
        test_processed[
            "District"
        ]
        .dropna()
        .unique()
    )


    unseen_validation_districts = (
        validation_districts
        -
        train_districts
    )


    unseen_test_districts = (
        test_districts
        -
        train_districts
    )


    print(
        f"Training districts          : "
        f"{len(train_districts)}"
    )

    print(
        f"Unseen validation districts : "
        f"{len(unseen_validation_districts)}"
    )

    print(
        f"Unseen test districts       : "
        f"{len(unseen_test_districts)}"
    )


    # District is deliberately NOT encoded here.
    #
    # Later:
    # - Linear / Random Forest / XGBoost can use
    #   training-fitted One-Hot Encoding.
    #
    # - CatBoost can use District as a native
    #   categorical feature.


    # ========================================================
    # 14. SAVE USABLE FEATURE MANIFEST
    # ========================================================

    feature_manifest_df = pd.DataFrame({

        "Feature":
            usable_features
    })


    feature_manifest_df.to_csv(
        REPORT_DIR
        / f"09_h{horizon}_usable_feature_manifest.csv",
        index=False
    )


    # ========================================================
    # 15. SAVE PREPROCESSED SPLITS
    # ========================================================

    train_output_path = (
        MODEL_READY_DIR
        / f"h{horizon}_train_preprocessed.csv"
    )


    validation_output_path = (
        MODEL_READY_DIR
        / f"h{horizon}_validation_preprocessed.csv"
    )


    test_output_path = (
        MODEL_READY_DIR
        / f"h{horizon}_test_preprocessed.csv"
    )


    train_processed.to_csv(
        train_output_path,
        index=False
    )


    validation_processed.to_csv(
        validation_output_path,
        index=False
    )


    test_processed.to_csv(
        test_output_path,
        index=False
    )


    print(
        "\nPreprocessed split files saved."
    )


    # ========================================================
    # 16. HORIZON SUMMARY
    # ========================================================

    overall_summary.append({

        "Horizon_Months":
            horizon,

        "Train_Rows":
            len(train_processed),

        "Validation_Rows":
            len(validation_processed),

        "Test_Rows":
            len(test_processed),

        "Initial_Numeric_Features":
            len(candidate_numeric_features),

        "All_Missing_Features_Removed":
            len(all_missing_features),

        "Constant_Features_Removed":
            len(constant_features),

        "Usable_Features":
            len(usable_features),

        "High_Correlation_Pairs_Flagged":
            len(high_corr_pairs_df),

        "Unseen_Validation_Districts":
            len(
                unseen_validation_districts
            ),

        "Unseen_Test_Districts":
            len(
                unseen_test_districts
            )
    })


# ============================================================
# 17. OVERALL SUMMARY
# ============================================================

overall_summary_df = pd.DataFrame(
    overall_summary
)


print("\n" + "=" * 105)
print("STEP 09 OVERALL SUMMARY")
print("=" * 105)


print(
    overall_summary_df
    .to_string(index=False)
)


overall_summary_df.to_csv(
    REPORT_DIR
    / "09_train_only_preprocessing_summary.csv",
    index=False
)


# ============================================================
# 18. METHODOLOGY NOTES
# ============================================================

print("\n" + "=" * 105)
print("METHODOLOGY NOTES")
print("=" * 105)


print(
    "\n1. Feature analysis used TRAIN data only."
)

print(
    "2. Validation and test targets did not influence "
    "feature-quality decisions."
)

print(
    "3. Only objectively unusable features were "
    "automatically removed:"
)

print(
    "   - completely missing in training"
)

print(
    "   - constant in training"
)

print(
    "4. High missingness features were flagged, "
    "not automatically removed."
)

print(
    "5. High inter-feature correlations were flagged, "
    "not automatically removed."
)

print(
    "6. Target correlation was used only for "
    "understanding associations."
)

print(
    "7. Missing values were filled using medians "
    "calculated from TRAIN data only."
)

print(
    "8. The same TRAIN medians were applied to "
    "validation and test features."
)

print(
    "9. District encoding is postponed until "
    "model-specific pipelines."
)

print(
    "10. Scaling is postponed until model-specific "
    "pipelines because tree models do not require "
    "the same scaling as linear models."
)

print(
    "11. No model was trained in this step."
)

print(
    "12. The 2025 test target was not used to make "
    "any preprocessing or feature decisions."
)


print(
    "\nNEXT STEP:"
)

print(
    "Build and evaluate simple forecasting baselines "
    "before training advanced candidate models."
)


print("\nModel-ready datasets saved to:")
print(MODEL_READY_DIR)

print("\nReports saved to:")
print(REPORT_DIR)


print(
    "\nSTEP 09 - TRAIN-ONLY PREPROCESSING + "
    "FEATURE ANALYSIS COMPLETE"
)

print("=" * 105)