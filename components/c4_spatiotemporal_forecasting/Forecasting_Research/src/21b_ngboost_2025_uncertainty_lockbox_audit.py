# ============================================================
# STEP 21B - FINAL 2025 NGBOOST UNCERTAINTY LOCKBOX AUDIT
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Complete the uncertainty-validation part promised in the
# proposal by evaluating NGBoost prediction intervals on the
# unseen 2025 lockbox period.
#
# POINT FORECAST STRATEGY
# -----------------------
# The final point forecast remains the frozen Random Forest
# strategy selected before opening 2025.
#
# UNCERTAINTY STRATEGY
# --------------------
# NGBoost is used as a separate probabilistic uncertainty model:
#
#   H1 -> NGB_A
#   H3 -> NGB_A
#   H6 -> NGB_A (the pre-2025 uncertainty-oriented H6 candidate)
#
# These choices are based ONLY on pre-2025 evidence:
# - H1/H3 NGB_A came from train-only tuning.
# - H6 NGB_A was explicitly evaluated in Step 17 as the
#   uncertainty-oriented candidate and achieved 2024 95%
#   coverage close to nominal coverage.
#
# STRICT RULE
# -----------
# At every 2025 forecast origin:
#
#   Forecast_Target_Date <= Forecast_Origin_Date
#
# Only labels already available at the origin may be used for
# NGBoost training.
#
# IMPORTANT
# ---------
# - NO hyperparameter tuning on 2025
# - NO model selection on 2025
# - NO changing the final Random Forest point-forecast strategy
# - 2025 actual values are used ONLY after prediction to audit:
#       * 95% interval coverage
#       * interval width
#       * Gaussian NLL
#       * NGBoost point metrics
# - Uncertainty levels are defined using 2024 validation
#   interval-width thresholds, NOT 2025.
# ============================================================

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import norm
from sklearn.tree import DecisionTreeRegressor

from ngboost import NGBRegressor
from ngboost.distns import Normal
from ngboost.scores import LogScore


# ============================================================
# 1. SETTINGS
# ============================================================

warnings.filterwarnings("ignore")

RANDOM_STATE = 42

HORIZONS = [1, 3, 6]

TARGET = "Forecast_Target"

EXPECTED_FEATURE_COUNT = 153
EXPECTED_DISTRICTS = 25
EXPECTED_TEST_ROWS_PER_HORIZON = 300

Z95 = float(norm.ppf(0.975))

# Frozen uncertainty configuration.
# NGB_A was chosen before opening 2025:
# H1/H3 -> train-only selected config.
# H6 -> Step 17 uncertainty-oriented candidate.
FROZEN_UNCERTAINTY_PARAMS = {
    1: {
        "Config_ID": "NGB_A",
        "n_estimators": 200,
        "learning_rate": 0.03,
        "tree_depth": 2,
        "min_samples_leaf": 10,
    },
    3: {
        "Config_ID": "NGB_A",
        "n_estimators": 200,
        "learning_rate": 0.03,
        "tree_depth": 2,
        "min_samples_leaf": 10,
    },
    6: {
        "Config_ID": "NGB_A",
        "n_estimators": 200,
        "learning_rate": 0.03,
        "tree_depth": 2,
        "min_samples_leaf": 10,
    },
}

VALIDATION_MODEL_LABELS = {
    1: "Tuned NGBoost",
    3: "Tuned NGBoost",
    6: "NGBoost H6 Uncertainty Candidate",
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

FIGURE_DIR = (
    BASE_DIR
    / "outputs"
    / "figures"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

STEP17_NGB_PREDICTIONS = (
    REPORT_DIR
    / "17_tuned_ngboost_validation_predictions.csv"
)

STEP21_RF_PREDICTIONS = (
    REPORT_DIR
    / "21_final_2025_lockbox_predictions.csv"
)


# ============================================================
# 3. METRIC FUNCTIONS
# ============================================================

def calculate_mae(y_true, y_pred):
    return float(
        np.mean(
            np.abs(
                y_true - y_pred
            )
        )
    )


def calculate_rmse(y_true, y_pred):
    return float(
        np.sqrt(
            np.mean(
                (y_true - y_pred) ** 2
            )
        )
    )


def calculate_wape(y_true, y_pred):
    denominator = np.sum(
        np.abs(y_true)
    )

    if denominator == 0:
        return np.nan

    return float(
        (
            np.sum(
                np.abs(
                    y_true - y_pred
                )
            )
            /
            denominator
        )
        * 100.0
    )


def calculate_smape(y_true, y_pred):
    denominator = (
        np.abs(y_true)
        +
        np.abs(y_pred)
    )

    valid = denominator > 0

    if not np.any(valid):
        return np.nan

    return float(
        np.mean(
            (
                2.0
                *
                np.abs(
                    y_pred[valid]
                    -
                    y_true[valid]
                )
            )
            /
            denominator[valid]
        )
        * 100.0
    )


def calculate_r2(y_true, y_pred):
    ss_res = np.sum(
        (y_true - y_pred) ** 2
    )

    ss_tot = np.sum(
        (
            y_true
            -
            np.mean(y_true)
        ) ** 2
    )

    if ss_tot == 0:
        return np.nan

    return float(
        1.0
        -
        ss_res
        /
        ss_tot
    )


# ============================================================
# 4. MODEL / PREPROCESSING HELPERS
# ============================================================

def create_ngboost_model(params):

    base_learner = DecisionTreeRegressor(
        criterion="friedman_mse",
        max_depth=params[
            "tree_depth"
        ],
        min_samples_leaf=params[
            "min_samples_leaf"
        ],
        random_state=RANDOM_STATE,
    )

    return NGBRegressor(
        Dist=Normal,
        Score=LogScore,
        Base=base_learner,
        natural_gradient=True,
        n_estimators=params[
            "n_estimators"
        ],
        learning_rate=params[
            "learning_rate"
        ],
        minibatch_frac=1.0,
        col_sample=1.0,
        verbose=False,
        random_state=RANDOM_STATE,
    )


def build_model_matrices(
    training_dataframe,
    prediction_dataframe,
    feature_columns,
):

    # Train-origin-only median imputation.
    medians = (
        training_dataframe[
            feature_columns
        ]
        .median()
    )

    all_missing_features = (
        medians[
            medians.isna()
        ]
        .index
        .tolist()
    )

    if all_missing_features:
        medians.loc[
            all_missing_features
        ] = 0.0

    X_train_numeric = (
        training_dataframe[
            feature_columns
        ]
        .fillna(
            medians
        )
        .astype(float)
        .reset_index(drop=True)
    )

    X_prediction_numeric = (
        prediction_dataframe[
            feature_columns
        ]
        .fillna(
            medians
        )
        .astype(float)
        .reset_index(drop=True)
    )

    # District encoding derived only from the training pool.
    train_dummies = pd.get_dummies(
        training_dataframe[
            "District"
        ],
        prefix="District",
        dtype=float,
    ).reset_index(drop=True)

    prediction_dummies = pd.get_dummies(
        prediction_dataframe[
            "District"
        ],
        prefix="District",
        dtype=float,
    )

    prediction_dummies = (
        prediction_dummies
        .reindex(
            columns=train_dummies.columns,
            fill_value=0,
        )
        .reset_index(drop=True)
    )

    X_train = pd.concat(
        [
            X_train_numeric,
            train_dummies,
        ],
        axis=1,
    )

    X_prediction = pd.concat(
        [
            X_prediction_numeric,
            prediction_dummies,
        ],
        axis=1,
    )

    y_train = (
        training_dataframe[
            TARGET
        ]
        .to_numpy(
            dtype=float
        )
    )

    return (
        X_train,
        y_train,
        X_prediction,
        all_missing_features,
    )


# ============================================================
# 5. INTRODUCTION
# ============================================================

print(
    "\n"
    +
    "=" * 120
)

print(
    "STEP 21B - FINAL 2025 NGBOOST UNCERTAINTY LOCKBOX AUDIT"
)

print(
    "=" * 120
)

print(
    "\nResearch-method protection:"
)

print(
    "- Final Random Forest point-forecast strategy is NOT changed"
)

print(
    "- NGBoost is evaluated only as the probabilistic uncertainty component"
)

print(
    "- NGBoost configuration was fixed using pre-2025 evidence"
)

print(
    "- 2025 is NOT used for tuning or selecting NGBoost parameters"
)

print(
    "- Strict rolling-origin label availability is enforced"
)

print(
    "- 2024 validation widths define uncertainty-level thresholds"
)


# ============================================================
# 6. INPUT CHECKS
# ============================================================

if not STEP17_NGB_PREDICTIONS.exists():
    raise FileNotFoundError(
        "Step 17 NGBoost validation predictions were not found:\n"
        f"{STEP17_NGB_PREDICTIONS}"
    )

if not STEP21_RF_PREDICTIONS.exists():
    raise FileNotFoundError(
        "Step 21 final RF predictions were not found:\n"
        f"{STEP21_RF_PREDICTIONS}"
    )


# ============================================================
# 7. FREEZE UNCERTAINTY-LEVEL THRESHOLDS FROM 2024
# ============================================================

print(
    "\n"
    +
    "=" * 120
)

print(
    "FREEZE UNCERTAINTY THRESHOLDS FROM PRE-2025 VALIDATION"
)

print(
    "=" * 120
)

validation_ngb_df = pd.read_csv(
    STEP17_NGB_PREDICTIONS
)

required_validation_columns = {
    "Model",
    "Horizon_Months",
    "Prediction",
    "Predicted_SD",
    "Lower_95",
    "Upper_95",
}

missing_validation_columns = (
    required_validation_columns
    -
    set(
        validation_ngb_df.columns
    )
)

if missing_validation_columns:
    raise ValueError(
        "Step 17 prediction file is missing columns: "
        f"{sorted(missing_validation_columns)}"
    )

uncertainty_thresholds = {}

threshold_records = []

for horizon in HORIZONS:

    model_label = (
        VALIDATION_MODEL_LABELS[
            horizon
        ]
    )

    calibration_df = (
        validation_ngb_df[
            (
                validation_ngb_df[
                    "Horizon_Months"
                ]
                ==
                horizon
            )
            &
            (
                validation_ngb_df[
                    "Model"
                ]
                ==
                model_label
            )
        ]
        .copy()
    )

    if len(calibration_df) != 300:
        raise ValueError(
            f"H{horizon}: expected 300 pre-2025 NGBoost "
            f"validation predictions for '{model_label}', "
            f"found {len(calibration_df)}."
        )

    calibration_df[
        "Interval_Width"
    ] = (
        calibration_df[
            "Upper_95"
        ]
        -
        calibration_df[
            "Lower_95"
        ]
    )

    calibration_df[
        "Relative_Interval_Width"
    ] = (
        calibration_df[
            "Interval_Width"
        ]
        /
        np.maximum(
            np.abs(
                calibration_df[
                    "Prediction"
                ]
                .to_numpy(
                    dtype=float
                )
            ),
            1.0,
        )
    )

    q33 = float(
        calibration_df[
            "Relative_Interval_Width"
        ]
        .quantile(
            1.0 / 3.0
        )
    )

    q67 = float(
        calibration_df[
            "Relative_Interval_Width"
        ]
        .quantile(
            2.0 / 3.0
        )
    )

    uncertainty_thresholds[
        horizon
    ] = {
        "Low_to_Moderate":
            q33,
        "Moderate_to_High":
            q67,
    }

    threshold_records.append({
        "Horizon_Months":
            horizon,
        "Validation_Model":
            model_label,
        "Validation_Rows":
            len(
                calibration_df
            ),
        "Low_to_Moderate_RelativeWidth_Threshold":
            q33,
        "Moderate_to_High_RelativeWidth_Threshold":
            q67,
    })

    print(
        f"H{horizon} | model={model_label} "
        f"| q33={q33:.4f} | q67={q67:.4f}"
    )


threshold_df = pd.DataFrame(
    threshold_records
)

threshold_path = (
    REPORT_DIR
    / "21b_uncertainty_level_thresholds_from_2024.csv"
)

threshold_df.to_csv(
    threshold_path,
    index=False,
)


# ============================================================
# 8. LOAD TRAIN / VALIDATION / 2025 TEST DATA
# ============================================================

print(
    "\n"
    +
    "=" * 120
)

print(
    "LOAD 2025 LOCKBOX DATA"
)

print(
    "=" * 120
)

horizon_data = {}

for horizon in HORIZONS:

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

    manifest_path = (
        REPORT_DIR
        / f"09_h{horizon}_usable_feature_manifest.csv"
    )

    for path in [
        train_path,
        validation_path,
        test_path,
        manifest_path,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                path
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

    manifest_df = pd.read_csv(
        manifest_path
    )

    for dataframe in [
        train_df,
        validation_df,
        test_df,
    ]:

        dataframe[
            "Forecast_Origin_Date"
        ] = pd.to_datetime(
            dataframe[
                "Forecast_Origin_Date"
            ]
        )

        dataframe[
            "Forecast_Target_Date"
        ] = pd.to_datetime(
            dataframe[
                "Forecast_Target_Date"
            ]
        )

    train_df = (
        train_df[
            train_df[
                TARGET
            ]
            .notna()
        ]
        .copy()
    )

    validation_df = (
        validation_df[
            validation_df[
                TARGET
            ]
            .notna()
        ]
        .copy()
    )

    test_df = (
        test_df[
            test_df[
                TARGET
            ]
            .notna()
        ]
        .copy()
    )

    if len(test_df) != EXPECTED_TEST_ROWS_PER_HORIZON:
        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_TEST_ROWS_PER_HORIZON} test rows, "
            f"found {len(test_df)}."
        )

    if (
        test_df[
            "District"
        ]
        .nunique()
        !=
        EXPECTED_DISTRICTS
    ):
        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_DISTRICTS} districts."
        )

    if not (
        test_df[
            "Forecast_Target_Date"
        ]
        .dt
        .year
        .eq(
            2025
        )
        .all()
    ):
        raise AssertionError(
            f"H{horizon}: target dates are not exclusively 2025."
        )

    feature_columns = (
        manifest_df[
            "Feature"
        ]
        .tolist()
    )

    if len(feature_columns) != EXPECTED_FEATURE_COUNT:
        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_FEATURE_COUNT} features, "
            f"found {len(feature_columns)}."
        )

    all_history_df = (
        pd.concat(
            [
                train_df,
                validation_df,
                test_df,
            ],
            ignore_index=True,
        )
        .sort_values(
            [
                "Forecast_Origin_Date",
                "District",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    horizon_data[
        horizon
    ] = {
        "test":
            test_df,
        "all_history":
            all_history_df,
        "features":
            feature_columns,
    }

    print(
        f"H{horizon}: "
        f"test={len(test_df)}, "
        f"features={len(feature_columns)}"
    )


# ============================================================
# 9. LOAD FINAL RF PREDICTIONS FOR SIDE-BY-SIDE OUTPUT
# ============================================================

rf_prediction_df = pd.read_csv(
    STEP21_RF_PREDICTIONS
)

for date_col in [
    "Forecast_Origin_Date",
    "Forecast_Target_Date",
]:
    if date_col in rf_prediction_df.columns:
        rf_prediction_df[
            date_col
        ] = pd.to_datetime(
            rf_prediction_df[
                date_col
            ]
        )

rf_prediction_column = None

for candidate in [
    "Prediction",
    "Predicted_Cases",
    "Final_Prediction",
]:
    if candidate in rf_prediction_df.columns:
        rf_prediction_column = (
            candidate
        )
        break

if rf_prediction_column is None:
    print(
        "\nWARNING: Could not identify RF prediction column in "
        "Step 21 output. NGBoost audit will continue without "
        "side-by-side RF values."
    )


# ============================================================
# 10. FINAL 2025 STRICT NGBOOST UNCERTAINTY TEST
# ============================================================

print(
    "\n"
    +
    "=" * 120
)

print(
    "RUN 2025 NGBOOST UNCERTAINTY LOCKBOX TEST"
)

print(
    "=" * 120
)

prediction_records = []
origin_audit_records = []

for horizon in HORIZONS:

    print(
        "\n"
        +
        "-" * 120
    )

    print(
        f"H{horizon} - FROZEN NGBOOST UNCERTAINTY MODEL"
    )

    print(
        "-" * 120
    )

    data = horizon_data[
        horizon
    ]

    test_df = (
        data[
            "test"
        ]
        .copy()
    )

    all_history_df = (
        data[
            "all_history"
        ]
        .copy()
    )

    feature_columns = (
        data[
            "features"
        ]
    )

    params = (
        FROZEN_UNCERTAINTY_PARAMS[
            horizon
        ]
    )

    print(
        f"Config: {params['Config_ID']}"
    )

    origins = sorted(
        test_df[
            "Forecast_Origin_Date"
        ]
        .unique()
    )

    for origin_number, origin_date in enumerate(
        origins,
        start=1,
    ):

        origin_date = pd.Timestamp(
            origin_date
        )

        prediction_rows = (
            test_df[
                test_df[
                    "Forecast_Origin_Date"
                ]
                ==
                origin_date
            ]
            .copy()
            .sort_values(
                "District"
            )
            .reset_index(
                drop=True
            )
        )

        training_pool = (
            all_history_df[
                (
                    all_history_df[
                        TARGET
                    ]
                    .notna()
                )
                &
                (
                    all_history_df[
                        "Forecast_Target_Date"
                    ]
                    <=
                    origin_date
                )
            ]
            .copy()
            .sort_values(
                [
                    "Forecast_Origin_Date",
                    "District",
                ]
            )
            .reset_index(
                drop=True
            )
        )

        if training_pool.empty:
            raise ValueError(
                f"H{horizon} {origin_date.date()}: "
                "empty training pool."
            )

        if (
            training_pool[
                "Forecast_Target_Date"
            ]
            .max()
            >
            origin_date
        ):
            raise AssertionError(
                f"H{horizon} {origin_date.date()}: "
                "future label leakage detected."
            )

        (
            X_train,
            y_train,
            X_prediction,
            all_missing_features,
        ) = build_model_matrices(
            training_pool,
            prediction_rows,
            feature_columns,
        )

        model = create_ngboost_model(
            params
        )

        model.fit(
            X_train,
            y_train,
        )

        predictive_distribution = (
            model.pred_dist(
                X_prediction
            )
        )

        predicted_mean = np.asarray(
            predictive_distribution
            .params[
                "loc"
            ],
            dtype=float,
        )

        predicted_sd = np.asarray(
            predictive_distribution
            .params[
                "scale"
            ],
            dtype=float,
        )

        predicted_sd = np.maximum(
            predicted_sd,
            1e-8,
        )

        raw_lower_95 = (
            predicted_mean
            -
            Z95
            *
            predicted_sd
        )

        upper_95 = (
            predicted_mean
            +
            Z95
            *
            predicted_sd
        )

        # Malnutrition case counts cannot be negative.
        lower_95 = np.maximum(
            raw_lower_95,
            0.0,
        )

        y_true = (
            prediction_rows[
                TARGET
            ]
            .to_numpy(
                dtype=float
            )
        )

        covered_by_95 = (
            (y_true >= lower_95)
            &
            (y_true <= upper_95)
        )

        interval_width = (
            upper_95
            -
            lower_95
        )

        relative_interval_width = (
            interval_width
            /
            np.maximum(
                np.abs(
                    predicted_mean
                ),
                1.0,
            )
        )

        gaussian_nll_row = (
            -
            norm.logpdf(
                y_true,
                loc=predicted_mean,
                scale=predicted_sd,
            )
        )

        print(
            f"H{horizon} origin "
            f"{origin_number}/{len(origins)} "
            f"| {origin_date.date()} "
            f"| train={len(training_pool)}"
        )

        origin_audit_records.append({
            "Horizon_Months":
                horizon,
            "Config_ID":
                params[
                    "Config_ID"
                ],
            "Forecast_Origin_Date":
                origin_date,
            "Training_Rows":
                len(
                    training_pool
                ),
            "Prediction_Rows":
                len(
                    prediction_rows
                ),
            "Latest_Training_Target_Date":
                training_pool[
                    "Forecast_Target_Date"
                ]
                .max(),
            "All_Missing_Train_Features":
                len(
                    all_missing_features
                ),
            "Leakage_Check_Passed":
                True,
        })

        q33 = (
            uncertainty_thresholds[
                horizon
            ][
                "Low_to_Moderate"
            ]
        )

        q67 = (
            uncertainty_thresholds[
                horizon
            ][
                "Moderate_to_High"
            ]
        )

        for row_number, row in (
            prediction_rows
            .iterrows()
        ):

            relative_width_value = float(
                relative_interval_width[
                    row_number
                ]
            )

            if relative_width_value <= q33:
                uncertainty_level = (
                    "Low Uncertainty"
                )
                confidence_label = (
                    "Higher Confidence"
                )

            elif relative_width_value <= q67:
                uncertainty_level = (
                    "Moderate Uncertainty"
                )
                confidence_label = (
                    "Moderate Confidence"
                )

            else:
                uncertainty_level = (
                    "High Uncertainty"
                )
                confidence_label = (
                    "Lower Confidence"
                )

            record = {
                "Model":
                    "NGBoost",
                "Uncertainty_Config":
                    params[
                        "Config_ID"
                    ],
                "Horizon_Months":
                    horizon,
                "District":
                    row[
                        "District"
                    ],
                "Forecast_Origin_Date":
                    origin_date,
                "Forecast_Target_Date":
                    row[
                        "Forecast_Target_Date"
                    ],
                "Actual_Target":
                    float(
                        y_true[
                            row_number
                        ]
                    ),
                "NGBoost_Mean":
                    float(
                        predicted_mean[
                            row_number
                        ]
                    ),
                "Predicted_SD":
                    float(
                        predicted_sd[
                            row_number
                        ]
                    ),
                "Lower_95":
                    float(
                        lower_95[
                            row_number
                        ]
                    ),
                "Upper_95":
                    float(
                        upper_95[
                            row_number
                        ]
                    ),
                "Raw_Lower_95":
                    float(
                        raw_lower_95[
                            row_number
                        ]
                    ),
                "Interval_Width":
                    float(
                        interval_width[
                            row_number
                        ]
                    ),
                "Relative_Interval_Width":
                    relative_width_value,
                "Covered_By_95":
                    bool(
                        covered_by_95[
                            row_number
                        ]
                    ),
                "Gaussian_NLL":
                    float(
                        gaussian_nll_row[
                            row_number
                        ]
                    ),
                "Uncertainty_Level":
                    uncertainty_level,
                "Confidence_Label":
                    confidence_label,
            }

            prediction_records.append(
                record
            )


prediction_df = pd.DataFrame(
    prediction_records
)

origin_audit_df = pd.DataFrame(
    origin_audit_records
)


# ============================================================
# 11. MERGE FINAL RF POINT FORECASTS
# ============================================================

if rf_prediction_column is not None:

    rf_merge_columns = [
        "Horizon_Months",
        "District",
        "Forecast_Origin_Date",
        "Forecast_Target_Date",
        rf_prediction_column,
    ]

    missing_rf_merge = [
        c
        for c in rf_merge_columns
        if c not in rf_prediction_df.columns
    ]

    if not missing_rf_merge:

        rf_side = (
            rf_prediction_df[
                rf_merge_columns
            ]
            .copy()
            .rename(
                columns={
                    rf_prediction_column:
                        "Final_RF_Point_Prediction"
                }
            )
        )

        prediction_df = (
            prediction_df
            .merge(
                rf_side,
                on=[
                    "Horizon_Months",
                    "District",
                    "Forecast_Origin_Date",
                    "Forecast_Target_Date",
                ],
                how="left",
                validate="one_to_one",
            )
        )

        prediction_df[
            "RF_Point_Inside_NGBoost_95"
        ] = (
            (
                prediction_df[
                    "Final_RF_Point_Prediction"
                ]
                >=
                prediction_df[
                    "Lower_95"
                ]
            )
            &
            (
                prediction_df[
                    "Final_RF_Point_Prediction"
                ]
                <=
                prediction_df[
                    "Upper_95"
                ]
            )
        )


# ============================================================
# 12. FINAL 2025 UNCERTAINTY METRICS
# ============================================================

print(
    "\n"
    +
    "=" * 120
)

print(
    "FINAL 2025 NGBOOST UNCERTAINTY RESULTS"
)

print(
    "=" * 120
)

metric_records = []

for horizon in HORIZONS:

    horizon_df = (
        prediction_df[
            prediction_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
        .copy()
    )

    if len(horizon_df) != EXPECTED_TEST_ROWS_PER_HORIZON:
        raise ValueError(
            f"H{horizon}: expected 300 uncertainty rows, "
            f"found {len(horizon_df)}."
        )

    y_true = (
        horizon_df[
            "Actual_Target"
        ]
        .to_numpy(
            dtype=float
        )
    )

    y_pred = (
        horizon_df[
            "NGBoost_Mean"
        ]
        .to_numpy(
            dtype=float
        )
    )

    coverage = float(
        horizon_df[
            "Covered_By_95"
        ]
        .mean()
        *
        100.0
    )

    mean_width = float(
        horizon_df[
            "Interval_Width"
        ]
        .mean()
    )

    median_width = float(
        horizon_df[
            "Interval_Width"
        ]
        .median()
    )

    mean_relative_width = float(
        horizon_df[
            "Relative_Interval_Width"
        ]
        .mean()
    )

    gaussian_nll = float(
        horizon_df[
            "Gaussian_NLL"
        ]
        .mean()
    )

    negative_raw_lower = int(
        (
            horizon_df[
                "Raw_Lower_95"
            ]
            <
            0
        )
        .sum()
    )

    metric_records.append({
        "Model":
            "NGBoost",
        "Horizon_Months":
            horizon,
        "Config_ID":
            FROZEN_UNCERTAINTY_PARAMS[
                horizon
            ][
                "Config_ID"
            ],
        "Test_Rows":
            len(
                horizon_df
            ),
        "MAE":
            calculate_mae(
                y_true,
                y_pred,
            ),
        "RMSE":
            calculate_rmse(
                y_true,
                y_pred,
            ),
        "WAPE_Percentage":
            calculate_wape(
                y_true,
                y_pred,
            ),
        "sMAPE_Percentage":
            calculate_smape(
                y_true,
                y_pred,
            ),
        "R2":
            calculate_r2(
                y_true,
                y_pred,
            ),
        "Nominal_Coverage_Percentage":
            95.0,
        "Observed_Coverage_Percentage":
            coverage,
        "Coverage_Error_Percentage_Points":
            abs(
                coverage
                -
                95.0
            ),
        "Mean_Interval_Width":
            mean_width,
        "Median_Interval_Width":
            median_width,
        "Mean_Relative_Interval_Width":
            mean_relative_width,
        "Gaussian_NLL":
            gaussian_nll,
        "Negative_Raw_Lower_Bounds":
            negative_raw_lower,
        "Low_Uncertainty_Rows":
            int(
                (
                    horizon_df[
                        "Uncertainty_Level"
                    ]
                    ==
                    "Low Uncertainty"
                )
                .sum()
            ),
        "Moderate_Uncertainty_Rows":
            int(
                (
                    horizon_df[
                        "Uncertainty_Level"
                    ]
                    ==
                    "Moderate Uncertainty"
                )
                .sum()
            ),
        "High_Uncertainty_Rows":
            int(
                (
                    horizon_df[
                        "Uncertainty_Level"
                    ]
                    ==
                    "High Uncertainty"
                )
                .sum()
            ),
    })


metrics_df = pd.DataFrame(
    metric_records
)

print(
    metrics_df
    .round(4)
    .to_string(
        index=False
    )
)


# ============================================================
# 13. MONTH-LEVEL UNCERTAINTY AUDIT
# ============================================================

prediction_df[
    "Target_Year"
] = (
    prediction_df[
        "Forecast_Target_Date"
    ]
    .dt
    .year
)

prediction_df[
    "Target_Month"
] = (
    prediction_df[
        "Forecast_Target_Date"
    ]
    .dt
    .month
)

prediction_df[
    "Target_Year_Month"
] = (
    prediction_df[
        "Forecast_Target_Date"
    ]
    .dt
    .strftime(
        "%Y-%m"
    )
)

month_records = []

for (
    horizon,
    target_month,
), group in (
    prediction_df
    .groupby(
        [
            "Horizon_Months",
            "Target_Year_Month",
        ]
    )
):

    month_records.append({
        "Horizon_Months":
            horizon,
        "Target_Year_Month":
            target_month,
        "Rows":
            len(
                group
            ),
        "Observed_Coverage_Percentage":
            float(
                group[
                    "Covered_By_95"
                ]
                .mean()
                *
                100.0
            ),
        "Mean_Interval_Width":
            float(
                group[
                    "Interval_Width"
                ]
                .mean()
            ),
        "Mean_Relative_Interval_Width":
            float(
                group[
                    "Relative_Interval_Width"
                ]
                .mean()
            ),
        "Mean_Gaussian_NLL":
            float(
                group[
                    "Gaussian_NLL"
                ]
                .mean()
            ),
    })


month_metrics_df = pd.DataFrame(
    month_records
)


# ============================================================
# 14. DISTRICT-LEVEL UNCERTAINTY AUDIT
# ============================================================

district_records = []

for (
    horizon,
    district,
), group in (
    prediction_df
    .groupby(
        [
            "Horizon_Months",
            "District",
        ]
    )
):

    district_records.append({
        "Horizon_Months":
            horizon,
        "District":
            district,
        "Rows":
            len(
                group
            ),
        "Observed_Coverage_Percentage":
            float(
                group[
                    "Covered_By_95"
                ]
                .mean()
                *
                100.0
            ),
        "Mean_Interval_Width":
            float(
                group[
                    "Interval_Width"
                ]
                .mean()
            ),
        "Mean_Relative_Interval_Width":
            float(
                group[
                    "Relative_Interval_Width"
                ]
                .mean()
            ),
        "Mean_Gaussian_NLL":
            float(
                group[
                    "Gaussian_NLL"
                ]
                .mean()
            ),
        "High_Uncertainty_Months":
            int(
                (
                    group[
                        "Uncertainty_Level"
                    ]
                    ==
                    "High Uncertainty"
                )
                .sum()
            ),
    })


district_metrics_df = pd.DataFrame(
    district_records
)


# ============================================================
# 15. SAVE REPORTS
# ============================================================

prediction_path = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_predictions.csv"
)

metrics_path = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_metrics.csv"
)

month_metrics_path = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_by_month.csv"
)

district_metrics_path = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_by_district.csv"
)

origin_audit_path = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_origin_audit.csv"
)

methodology_path = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_methodology.json"
)

prediction_df.to_csv(
    prediction_path,
    index=False,
)

metrics_df.to_csv(
    metrics_path,
    index=False,
)

month_metrics_df.to_csv(
    month_metrics_path,
    index=False,
)

district_metrics_df.to_csv(
    district_metrics_path,
    index=False,
)

origin_audit_df.to_csv(
    origin_audit_path,
    index=False,
)

methodology = {
    "step":
        "21B",
    "purpose":
        "Final 2025 NGBoost uncertainty lockbox audit",
    "point_forecast_model":
        "Frozen Random Forest from Step 20/21",
    "uncertainty_model":
        "NGBoost Normal predictive distribution",
    "uncertainty_configs": {
        f"H{h}":
            FROZEN_UNCERTAINTY_PARAMS[h]
        for h in HORIZONS
    },
    "h6_selection_basis":
        (
            "NGB_A was the uncertainty-oriented H6 candidate "
            "evaluated on 2024 before opening the 2025 lockbox."
        ),
    "test_period":
        "2025",
    "strict_label_rule":
        "Forecast_Target_Date <= Forecast_Origin_Date",
    "nominal_interval":
        95.0,
    "uncertainty_level_basis":
        (
            "Relative 95% interval-width tertiles frozen from "
            "the corresponding 2024 validation predictions."
        ),
    "interpretation":
        (
            "Low/Moderate/High uncertainty describes predictive "
            "interval width relative to the model mean. It is not "
            "a probability that the forecast is correct."
        ),
}

with open(
    methodology_path,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        methodology,
        file,
        indent=2,
        default=str,
    )


# ============================================================
# 16. FIGURES
# ============================================================

for horizon in HORIZONS:

    h_df = (
        prediction_df[
            prediction_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
        .copy()
    )

    monthly_plot_df = (
        h_df
        .groupby(
            "Forecast_Target_Date",
            as_index=False,
        )
        .agg(
            Actual_Target=(
                "Actual_Target",
                "mean",
            ),
            NGBoost_Mean=(
                "NGBoost_Mean",
                "mean",
            ),
            Lower_95=(
                "Lower_95",
                "mean",
            ),
            Upper_95=(
                "Upper_95",
                "mean",
            ),
        )
        .sort_values(
            "Forecast_Target_Date"
        )
    )

    fig, ax = plt.subplots(
        figsize=(12, 6)
    )

    ax.plot(
        monthly_plot_df[
            "Forecast_Target_Date"
        ],
        monthly_plot_df[
            "Actual_Target"
        ],
        marker="o",
        label="Actual 2025",
    )

    ax.plot(
        monthly_plot_df[
            "Forecast_Target_Date"
        ],
        monthly_plot_df[
            "NGBoost_Mean"
        ],
        marker="o",
        label="NGBoost mean",
    )

    ax.fill_between(
        monthly_plot_df[
            "Forecast_Target_Date"
        ],
        monthly_plot_df[
            "Lower_95"
        ],
        monthly_plot_df[
            "Upper_95"
        ],
        alpha=0.2,
        label="Mean district 95% interval",
    )

    ax.set_title(
        f"2025 NGBoost Uncertainty Audit - H{horizon}"
    )

    ax.set_xlabel(
        "Forecast target month"
    )

    ax.set_ylabel(
        "Mean malnutrition cases across districts"
    )

    ax.legend()

    fig.autofmt_xdate()

    fig.tight_layout()

    fig.savefig(
        FIGURE_DIR
        /
        f"21b_ngboost_2025_h{horizon}_uncertainty.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# ============================================================
# 17. FINAL HARD AUDIT
# ============================================================

print(
    "\n"
    +
    "=" * 120
)

print(
    "FINAL HARD AUDIT"
)

print(
    "=" * 120
)

expected_total_rows = (
    EXPECTED_TEST_ROWS_PER_HORIZON
    *
    len(HORIZONS)
)

if len(prediction_df) != expected_total_rows:
    raise ValueError(
        f"Expected {expected_total_rows} total rows, "
        f"found {len(prediction_df)}."
    )

if not (
    origin_audit_df[
        "Leakage_Check_Passed"
    ]
    .all()
):
    raise AssertionError(
        "At least one origin failed the leakage audit."
    )

for horizon in HORIZONS:

    h_df = (
        prediction_df[
            prediction_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
    )

    if (
        h_df[
            "District"
        ]
        .nunique()
        !=
        EXPECTED_DISTRICTS
    ):
        raise ValueError(
            f"H{horizon}: district coverage failed."
        )

    if not (
        h_df[
            "Forecast_Target_Date"
        ]
        .dt
        .year
        .eq(
            2025
        )
        .all()
    ):
        raise AssertionError(
            f"H{horizon}: non-2025 target found."
        )

    if (
        h_df[
            "Lower_95"
        ]
        >
        h_df[
            "Upper_95"
        ]
    ).any():
        raise AssertionError(
            f"H{horizon}: invalid prediction interval."
        )

print(
    f"Total 2025 uncertainty predictions : "
    f"{len(prediction_df)} [PASS]"
)

print(
    "Strict rolling-origin leakage check : PASS"
)

print(
    "25 districts per horizon             : PASS"
)

print(
    "H1/H3/H6 2025 target coverage        : PASS"
)


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

print(
    "\n"
    +
    "=" * 120
)

print(
    "STEP 21B COMPLETE"
)

print(
    "=" * 120
)

print(
    "\nThis step completes the final unseen-2025 "
    "uncertainty validation promised in the proposal."
)

print(
    "\nInterpretation:"
)

print(
    "- Random Forest remains the final point-forecast model."
)

print(
    "- NGBoost provides a separate probabilistic forecast "
    "distribution and 95% prediction interval."
)

print(
    "- Covered_By_95 shows whether the actual unseen 2025 "
    "value fell inside the NGBoost interval."
)

print(
    "- Narrower relative intervals are labelled lower "
    "uncertainty; wider intervals are labelled higher uncertainty."
)

print(
    "- Those uncertainty thresholds were frozen from 2024 "
    "validation, not chosen using 2025."
)

print(
    "- The confidence label is a communication aid, not a "
    "guaranteed probability that the RF forecast is correct."
)

print(
    "\nSaved:"
)

for path in [
    prediction_path,
    metrics_path,
    month_metrics_path,
    district_metrics_path,
    origin_audit_path,
    threshold_path,
    methodology_path,
]:
    print(
        f"- {path}"
    )

print(
    f"- Figures: {FIGURE_DIR}"
)

print(
    "\nNEXT AFTER THIS PASSES:"
)

print(
    "Add the validated NGBoost uncertainty component to "
    "the 2026-2030 future forecast pipeline before SHAP/risk/"
    "resource/alert dashboard integration."
)

print(
    "\nSTEP 21B - FINAL 2025 NGBOOST UNCERTAINTY "
    "LOCKBOX AUDIT COMPLETE"
)
