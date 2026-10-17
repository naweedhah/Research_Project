# ============================================================
# STEP 21 - FINAL 2025 LOCKBOX TEST
# Childhood Malnutrition Forecasting Research
#
# PURPOSE
# -------
# Run the ONE-TIME final evaluation on the untouched 2025
# test lockbox using ONLY the forecasting strategy frozen in
# Step 20.
#
# Frozen point-forecast strategy:
#   H1 -> Tuned Random Forest (Step 20 frozen configuration)
#   H3 -> Tuned Random Forest (Step 20 frozen configuration)
#   H6 -> Tuned Random Forest (Step 20 frozen configuration)
#
# STRICT EVALUATION RULE
# ----------------------
# At every forecast origin:
#   Forecast_Target_Date <= Forecast_Origin_Date
#
# Therefore, only labels that would already be known at that
# origin may enter the training history.
#
# IMPORTANT
# ---------
# - NO hyperparameter tuning is allowed in this step.
# - NO model selection is allowed in this step.
# - NO changing H1/H3/H6 models after viewing 2025 results.
# - Imputation and district encoding are re-fitted separately
#   at each forecast origin.
# - The Step 20 frozen settings are treated as immutable.
# ============================================================


from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor


# ============================================================
# 1. SETTINGS
# ============================================================

warnings.filterwarnings("ignore")

RANDOM_STATE = 42

HORIZONS = [1, 3, 6]

TARGET = "Forecast_Target"

EXPECTED_FEATURE_COUNT = 153

EXPECTED_TEST_ROWS_PER_HORIZON = 300

EXPECTED_FINAL_MODEL = "Tuned Random Forest"

EXPECTED_BASE_MODEL = "Random Forest"


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


FROZEN_STRATEGY_PATH = (
    REPORT_DIR
    / "20_final_forecasting_strategy.json"
)

FROZEN_STRATEGY_CSV_PATH = (
    REPORT_DIR
    / "20_final_forecasting_strategy.csv"
)

VALIDATION_METRICS_PATH = (
    REPORT_DIR
    / "20_selected_model_2024_validation_metrics.csv"
)


# ============================================================
# 3. INTRODUCTION
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "STEP 21 - FINAL 2025 LOCKBOX TEST"
)

print(
    "=" * 120
)

print(
    "\nLOCKBOX RULES:"
)

print(
    "- Final strategy was frozen in Step 20 before opening 2025"
)

print(
    "- No tuning is performed in Step 21"
)

print(
    "- No model selection is performed in Step 21"
)

print(
    "- Step 20 model family and hyperparameters cannot be changed"
)

print(
    "- Strict rolling-origin label availability is enforced"
)

print(
    "- 2025 is used only for the final one-time test"
)


# ============================================================
# 4. METRIC FUNCTIONS
# ============================================================

def calculate_mae(
    y_true,
    y_pred,
):
    return float(
        np.mean(
            np.abs(
                y_true
                -
                y_pred
            )
        )
    )


def calculate_rmse(
    y_true,
    y_pred,
):
    return float(
        np.sqrt(
            np.mean(
                (
                    y_true
                    -
                    y_pred
                ) ** 2
            )
        )
    )


def calculate_wape(
    y_true,
    y_pred,
):
    denominator = np.sum(
        np.abs(
            y_true
        )
    )

    if denominator == 0:
        return np.nan

    return float(
        np.sum(
            np.abs(
                y_true
                -
                y_pred
            )
        )
        /
        denominator
        *
        100
    )


def calculate_smape(
    y_true,
    y_pred,
):
    denominator = (
        np.abs(
            y_true
        )
        +
        np.abs(
            y_pred
        )
    )

    valid = (
        denominator
        !=
        0
    )

    if valid.sum() == 0:
        return np.nan

    return float(
        np.mean(
            2
            *
            np.abs(
                y_true[valid]
                -
                y_pred[valid]
            )
            /
            denominator[valid]
        )
        *
        100
    )


def calculate_r2(
    y_true,
    y_pred,
):
    ss_res = np.sum(
        (
            y_true
            -
            y_pred
        ) ** 2
    )

    ss_tot = np.sum(
        (
            y_true
            -
            np.mean(
                y_true
            )
        ) ** 2
    )

    if ss_tot == 0:
        return np.nan

    return float(
        1
        -
        ss_res
        /
        ss_tot
    )


def calculate_metric_row(
    dataframe,
    horizon,
):
    y_true = (
        dataframe[
            "Actual_Target"
        ]
        .to_numpy(
            dtype=float
        )
    )

    y_pred = (
        dataframe[
            "Prediction"
        ]
        .to_numpy(
            dtype=float
        )
    )

    return {
        "Horizon_Months":
            int(
                horizon
            ),

        "Model":
            EXPECTED_FINAL_MODEL,

        "Test_Rows":
            len(
                dataframe
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

        "Mean_Error":
            float(
                np.mean(
                    y_pred
                    -
                    y_true
                )
            ),

        "Median_Absolute_Error":
            float(
                np.median(
                    np.abs(
                        y_true
                        -
                        y_pred
                    )
                )
            ),
    }


# ============================================================
# 5. LOAD AND VERIFY FROZEN STEP 20 STRATEGY
# ============================================================

if not FROZEN_STRATEGY_PATH.exists():

    raise FileNotFoundError(
        "Frozen Step 20 strategy JSON was not found:\n"
        f"{FROZEN_STRATEGY_PATH}"
    )


with open(
    FROZEN_STRATEGY_PATH,
    "r",
    encoding="utf-8",
) as file:

    frozen_strategy = json.load(
        file
    )


if (
    frozen_strategy.get(
        "status"
    )
    !=
    "FROZEN"
):

    raise ValueError(
        "Step 20 strategy status is not FROZEN."
    )


point_strategy = (
    frozen_strategy.get(
        "point_forecast_strategy",
        {}
    )
)


def get_frozen_horizon_strategy(
    horizon,
):

    horizon_key = (
        f"H{horizon}"
    )

    if (
        horizon_key
        not in
        point_strategy
    ):

        raise KeyError(
            f"Frozen strategy does not contain {horizon_key}."
        )

    strategy = (
        point_strategy[
            horizon_key
        ]
    )

    if (
        strategy.get(
            "model"
        )
        !=
        EXPECTED_FINAL_MODEL
    ):

        raise ValueError(
            f"{horizon_key}: frozen model is "
            f"{strategy.get('model')}, expected "
            f"{EXPECTED_FINAL_MODEL}."
        )

    if (
        strategy.get(
            "base_model"
        )
        !=
        EXPECTED_BASE_MODEL
    ):

        raise ValueError(
            f"{horizon_key}: frozen base model is "
            f"{strategy.get('base_model')}, expected "
            f"{EXPECTED_BASE_MODEL}."
        )

    parameters = (
        strategy.get(
            "parameters"
        )
    )

    if not isinstance(
        parameters,
        dict,
    ):

        raise ValueError(
            f"{horizon_key}: frozen parameters are missing."
        )

    return strategy


print(
    "\nFrozen Step 20 strategy:"
)

for horizon in HORIZONS:

    strategy = (
        get_frozen_horizon_strategy(
            horizon
        )
    )

    print(
        f"- H{horizon}: "
        f"{strategy['model']} "
        f"| Config_ID={strategy.get('config_id')}"
    )


# ============================================================
# 6. STRICT ORIGIN-SPECIFIC PREPROCESSING
# ============================================================

def build_model_matrices(
    training_dataframe,
    prediction_dataframe,
    feature_columns,
):
    # --------------------------------------------------------
    # Median imputation is learned only from history available
    # at the current forecast origin.
    # --------------------------------------------------------

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
        .astype(
            float
        )
        .reset_index(
            drop=True
        )
    )


    X_prediction_numeric = (
        prediction_dataframe[
            feature_columns
        ]
        .fillna(
            medians
        )
        .astype(
            float
        )
        .reset_index(
            drop=True
        )
    )


    # --------------------------------------------------------
    # District one-hot encoding is also fitted only from the
    # available training history.
    # --------------------------------------------------------

    train_dummies = (
        pd.get_dummies(
            training_dataframe[
                "District"
            ],
            prefix=
                "District",
            dtype=
                float,
        )
        .reset_index(
            drop=True
        )
    )


    prediction_dummies = (
        pd.get_dummies(
            prediction_dataframe[
                "District"
            ],
            prefix=
                "District",
            dtype=
                float,
        )
        .reindex(
            columns=
                train_dummies.columns,
            fill_value=
                0,
        )
        .reset_index(
            drop=True
        )
    )


    X_train = (
        pd.concat(
            [
                X_train_numeric,
                train_dummies,
            ],
            axis=1,
        )
        .to_numpy(
            dtype=float
        )
    )


    X_prediction = (
        pd.concat(
            [
                X_prediction_numeric,
                prediction_dummies,
            ],
            axis=1,
        )
        .to_numpy(
            dtype=float
        )
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
# 7. FINAL RANDOM FOREST FACTORY
# ============================================================

def create_frozen_random_forest(
    parameters,
):

    required_parameter_names = {
        "n_estimators",
        "max_depth",
        "min_samples_split",
        "min_samples_leaf",
        "max_features",
        "bootstrap",
    }

    missing_parameters = (
        required_parameter_names
        -
        set(
            parameters.keys()
        )
    )

    if missing_parameters:

        raise ValueError(
            "Frozen Random Forest parameters are missing: "
            f"{sorted(missing_parameters)}"
        )


    return RandomForestRegressor(
        n_estimators=
            int(
                parameters[
                    "n_estimators"
                ]
            ),

        max_depth=
            (
                None
                if
                parameters[
                    "max_depth"
                ]
                is None
                else
                int(
                    parameters[
                        "max_depth"
                    ]
                )
            ),

        min_samples_split=
            int(
                parameters[
                    "min_samples_split"
                ]
            ),

        min_samples_leaf=
            int(
                parameters[
                    "min_samples_leaf"
                ]
            ),

        max_features=
            parameters[
                "max_features"
            ],

        bootstrap=
            bool(
                parameters[
                    "bootstrap"
                ]
            ),

        random_state=
            RANDOM_STATE,

        n_jobs=
            -1,
    )


# ============================================================
# 8. LOAD TRAIN + VALIDATION + 2025 TEST SPLITS
# ============================================================

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
                "Required Step 21 input file not found:\n"
                f"{path}"
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


    # --------------------------------------------------------
    # HARD TEST-YEAR CHECK
    # --------------------------------------------------------

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

        invalid_years = sorted(
            test_df[
                "Forecast_Target_Date"
            ]
            .dt
            .year
            .unique()
            .tolist()
        )

        raise AssertionError(
            f"H{horizon}: test target dates are not exclusively "
            f"in 2025. Years found: {invalid_years}"
        )


    if (
        len(
            test_df
        )
        !=
        EXPECTED_TEST_ROWS_PER_HORIZON
    ):

        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_TEST_ROWS_PER_HORIZON} test rows, "
            f"found {len(test_df)}."
        )


    feature_columns = (
        manifest_df[
            "Feature"
        ]
        .tolist()
    )


    if (
        len(
            feature_columns
        )
        !=
        EXPECTED_FEATURE_COUNT
    ):

        raise ValueError(
            f"H{horizon}: expected {EXPECTED_FEATURE_COUNT} "
            f"features, found {len(feature_columns)}."
        )


    # --------------------------------------------------------
    # Combine all available labeled history.
    #
    # IMPORTANT:
    # Test rows are included in the pool ONLY so that a 2025
    # label may become available to later 2025 origins AFTER
    # its target date has occurred.
    #
    # The strict filter below guarantees:
    # Forecast_Target_Date <= Forecast_Origin_Date
    # --------------------------------------------------------

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
        "train":
            train_df,

        "validation":
            validation_df,

        "test":
            test_df,

        "all_history":
            all_history_df,

        "features":
            feature_columns,
    }


    print(
        f"\nH{horizon}: "
        f"train={len(train_df)}, "
        f"validation={len(validation_df)}, "
        f"test={len(test_df)}, "
        f"features={len(feature_columns)}"
    )

    print(
        f"H{horizon} test target range: "
        f"{test_df['Forecast_Target_Date'].min().date()} "
        f"to "
        f"{test_df['Forecast_Target_Date'].max().date()}"
    )


# ============================================================
# 9. ONE-TIME FINAL 2025 LOCKBOX EVALUATION
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "FINAL RANDOM FOREST - 2025 STRICT LOCKBOX EVALUATION"
)

print(
    "=" * 120
)


prediction_records = []

origin_audit_records = []


for horizon in HORIZONS:

    data = (
        horizon_data[
            horizon
        ]
    )


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


    frozen_horizon_strategy = (
        get_frozen_horizon_strategy(
            horizon
        )
    )


    parameters = (
        frozen_horizon_strategy[
            "parameters"
        ]
    )


    config_id = (
        frozen_horizon_strategy.get(
            "config_id",
            parameters.get(
                "Config_ID",
                "UNKNOWN",
            ),
        )
    )


    print(
        "\n"
        + "-" * 120
    )

    print(
        f"H{horizon} FINAL TEST "
        f"| Frozen config = {config_id}"
    )

    print(
        "-" * 120
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
        )


        # ----------------------------------------------------
        # STRICT KNOWN-LABEL RULE
        # ----------------------------------------------------

        training_pool = (
            all_history_df[
                all_history_df[
                    "Forecast_Target_Date"
                ]
                <=
                origin_date
            ]
            .copy()
        )


        if training_pool.empty:

            raise ValueError(
                f"H{horizon}: empty training pool at "
                f"{origin_date.date()}."
            )


        # ----------------------------------------------------
        # Safety check:
        # No label later than origin may enter training.
        # ----------------------------------------------------

        latest_training_target_date = (
            training_pool[
                "Forecast_Target_Date"
            ]
            .max()
        )


        if (
            latest_training_target_date
            >
            origin_date
        ):

            raise AssertionError(
                f"H{horizon}: future label leakage detected "
                f"at origin {origin_date.date()}."
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


        model = (
            create_frozen_random_forest(
                parameters
            )
        )


        model.fit(
            X_train,
            y_train,
        )


        predictions = (
            model.predict(
                X_prediction
            )
        )


        if (
            len(
                predictions
            )
            !=
            len(
                prediction_rows
            )
        ):

            raise RuntimeError(
                f"H{horizon}: prediction-row mismatch "
                f"at {origin_date.date()}."
            )


        print(
            f"H{horizon} origin "
            f"{origin_number}/{len(origins)} "
            f"| {origin_date.date()} "
            f"| train={len(training_pool)} "
            f"| predict={len(prediction_rows)}"
        )


        origin_audit_records.append({
            "Horizon_Months":
                horizon,

            "Config_ID":
                config_id,

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
                latest_training_target_date,

            "Future_Label_Leakage":
                False,

            "All_Missing_Features_Count":
                len(
                    all_missing_features
                ),

            "All_Missing_Features":
                ";".join(
                    all_missing_features
                ),
        })


        for row_number, (
            _,
            row,
        ) in enumerate(
            prediction_rows.iterrows()
        ):

            prediction_records.append({
                "Model":
                    EXPECTED_FINAL_MODEL,

                "Base_Model":
                    EXPECTED_BASE_MODEL,

                "Horizon_Months":
                    horizon,

                "Config_ID":
                    config_id,

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
                        row[
                            TARGET
                        ]
                    ),

                "Prediction":
                    float(
                        predictions[
                            row_number
                        ]
                    ),

                "Absolute_Error":
                    float(
                        abs(
                            float(
                                row[
                                    TARGET
                                ]
                            )
                            -
                            float(
                                predictions[
                                    row_number
                                ]
                            )
                        )
                    ),

                "Signed_Error":
                    float(
                        float(
                            predictions[
                                row_number
                            ]
                        )
                        -
                        float(
                            row[
                                TARGET
                            ]
                        )
                    ),
            })


# ============================================================
# 10. SAVE FINAL PREDICTIONS + AUDIT
# ============================================================

prediction_df = pd.DataFrame(
    prediction_records
)


if prediction_df.empty:

    raise RuntimeError(
        "No 2025 lockbox predictions were produced."
    )


for horizon in HORIZONS:

    horizon_count = int(
        (
            prediction_df[
                "Horizon_Months"
            ]
            ==
            horizon
        )
        .sum()
    )

    if (
        horizon_count
        !=
        EXPECTED_TEST_ROWS_PER_HORIZON
    ):

        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_TEST_ROWS_PER_HORIZON} final predictions, "
            f"found {horizon_count}."
        )


prediction_path = (
    REPORT_DIR
    / "21_final_2025_lockbox_predictions.csv"
)


prediction_df.to_csv(
    prediction_path,
    index=False,
)


origin_audit_df = pd.DataFrame(
    origin_audit_records
)


origin_audit_path = (
    REPORT_DIR
    / "21_final_2025_origin_audit.csv"
)


origin_audit_df.to_csv(
    origin_audit_path,
    index=False,
)


# ============================================================
# 11. FINAL 2025 OVERALL METRICS
# ============================================================

metric_rows = []


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


    metric_rows.append(
        calculate_metric_row(
            horizon_df,
            horizon,
        )
    )


metrics_df = pd.DataFrame(
    metric_rows
)


metrics_path = (
    REPORT_DIR
    / "21_final_2025_lockbox_metrics.csv"
)


metrics_df.to_csv(
    metrics_path,
    index=False,
)


# ============================================================
# 12. DISTRICT-LEVEL FINAL TEST METRICS
# ============================================================

district_metric_rows = []


for horizon in HORIZONS:

    horizon_df = (
        prediction_df[
            prediction_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
    )


    for district, district_df in (
        horizon_df.groupby(
            "District"
        )
    ):

        y_true = (
            district_df[
                "Actual_Target"
            ]
            .to_numpy(
                dtype=float
            )
        )

        y_pred = (
            district_df[
                "Prediction"
            ]
            .to_numpy(
                dtype=float
            )
        )


        district_metric_rows.append({
            "Horizon_Months":
                horizon,

            "District":
                district,

            "Test_Rows":
                len(
                    district_df
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
        })


district_metrics_df = pd.DataFrame(
    district_metric_rows
)


district_metrics_path = (
    REPORT_DIR
    / "21_final_2025_district_metrics.csv"
)


district_metrics_df.to_csv(
    district_metrics_path,
    index=False,
)


# ============================================================
# 13. 2024 VALIDATION VS 2025 FINAL TEST
# ============================================================

generalization_rows = []


if VALIDATION_METRICS_PATH.exists():

    validation_metrics_df = pd.read_csv(
        VALIDATION_METRICS_PATH
    )


    for horizon in HORIZONS:

        validation_row = (
            validation_metrics_df[
                validation_metrics_df[
                    "Horizon_Months"
                ]
                ==
                horizon
            ]
        )


        test_row = (
            metrics_df[
                metrics_df[
                    "Horizon_Months"
                ]
                ==
                horizon
            ]
        )


        if (
            len(
                validation_row
            )
            ==
            1
            and
            len(
                test_row
            )
            ==
            1
        ):

            validation_row = (
                validation_row
                .iloc[0]
            )

            test_row = (
                test_row
                .iloc[0]
            )


            validation_mae = float(
                validation_row[
                    "MAE"
                ]
                if
                "MAE"
                in
                validation_row.index
                else
                validation_row[
                    "Validation_MAE_2024"
                ]
            )


            validation_rmse = float(
                validation_row[
                    "RMSE"
                ]
                if
                "RMSE"
                in
                validation_row.index
                else
                validation_row[
                    "Validation_RMSE_2024"
                ]
            )


            validation_wape = float(
                validation_row[
                    "WAPE_Percentage"
                ]
                if
                "WAPE_Percentage"
                in
                validation_row.index
                else
                validation_row[
                    "Validation_WAPE_2024"
                ]
            )


            test_mae = float(
                test_row[
                    "MAE"
                ]
            )

            test_rmse = float(
                test_row[
                    "RMSE"
                ]
            )

            test_wape = float(
                test_row[
                    "WAPE_Percentage"
                ]
            )


            generalization_rows.append({
                "Horizon_Months":
                    horizon,

                "Validation_MAE_2024":
                    validation_mae,

                "Final_Test_MAE_2025":
                    test_mae,

                "MAE_Change_2025_minus_2024":
                    test_mae
                    -
                    validation_mae,

                "Validation_RMSE_2024":
                    validation_rmse,

                "Final_Test_RMSE_2025":
                    test_rmse,

                "RMSE_Change_2025_minus_2024":
                    test_rmse
                    -
                    validation_rmse,

                "Validation_WAPE_2024":
                    validation_wape,

                "Final_Test_WAPE_2025":
                    test_wape,

                "WAPE_Change_2025_minus_2024":
                    test_wape
                    -
                    validation_wape,
            })


generalization_df = pd.DataFrame(
    generalization_rows
)


generalization_path = (
    REPORT_DIR
    / "21_2024_validation_vs_2025_test.csv"
)


generalization_df.to_csv(
    generalization_path,
    index=False,
)


# ============================================================
# 14. FINAL TEST FIGURE
# ============================================================

metric_plot_df = (
    metrics_df[
        [
            "Horizon_Months",
            "MAE",
            "RMSE",
        ]
    ]
    .set_index(
        "Horizon_Months"
    )
)


metric_plot_df.plot(
    kind="bar",
    figsize=(
        10,
        6,
    ),
)


plt.title(
    "Final 2025 Lockbox Test - Tuned Random Forest"
)

plt.xlabel(
    "Forecast Horizon (Months)"
)

plt.ylabel(
    "Error"
)

plt.xticks(
    rotation=0
)

plt.tight_layout()


figure_path = (
    FIGURE_DIR
    / "21_final_2025_lockbox_mae_rmse.png"
)


plt.savefig(
    figure_path,
    dpi=300,
    bbox_inches=
        "tight",
)


plt.close()


# ============================================================
# 15. HUMAN-READABLE FINAL TEST AUDIT
# ============================================================

audit_text_path = (
    REPORT_DIR
    / "21_final_2025_lockbox_audit.txt"
)


audit_lines = []

audit_lines.append(
    "STEP 21 - FINAL 2025 LOCKBOX TEST"
)

audit_lines.append(
    "=" * 72
)

audit_lines.append(
    ""
)

audit_lines.append(
    "Frozen strategy source:"
)

audit_lines.append(
    str(
        FROZEN_STRATEGY_PATH
    )
)

audit_lines.append(
    ""
)

audit_lines.append(
    "Methodology:"
)

audit_lines.append(
    "- Step 20 strategy used without retuning or reselection."
)

audit_lines.append(
    "- Strict rolling-origin evaluation was used."
)

audit_lines.append(
    "- Training labels satisfied Forecast_Target_Date <= "
    "Forecast_Origin_Date."
)

audit_lines.append(
    "- Imputation was fitted separately at each origin."
)

audit_lines.append(
    "- District encoding was fitted separately at each origin."
)

audit_lines.append(
    "- The 2025 test set was used only for final evaluation."
)

audit_lines.append(
    ""
)

audit_lines.append(
    "Final 2025 metrics:"
)


for _, row in (
    metrics_df
    .sort_values(
        "Horizon_Months"
    )
    .iterrows()
):

    audit_lines.append(
        (
            f"- H{int(row['Horizon_Months'])}: "
            f"MAE={row['MAE']:.4f}, "
            f"RMSE={row['RMSE']:.4f}, "
            f"WAPE={row['WAPE_Percentage']:.4f}%, "
            f"sMAPE={row['sMAPE_Percentage']:.4f}%, "
            f"R2={row['R2']:.4f}"
        )
    )


audit_lines.append(
    ""
)

audit_lines.append(
    "FINAL LOCKBOX POLICY:"
)

audit_lines.append(
    "These 2025 results are final test evidence. "
    "Do not change the frozen H1/H3/H6 model family or "
    "hyperparameters based on these results."
)


with open(
    audit_text_path,
    "w",
    encoding="utf-8",
) as file:

    file.write(
        "\n".join(
            audit_lines
        )
    )


# ============================================================
# 16. PRINT FINAL RESULTS
# ============================================================

print(
    "\n"
    + "=" * 120
)

print(
    "FINAL 2025 LOCKBOX TEST RESULTS"
)

print(
    "=" * 120
)


print(
    metrics_df
    .round(
        4
    )
    .to_string(
        index=False
    )
)


if not generalization_df.empty:

    print(
        "\n"
        + "=" * 120
    )

    print(
        "2024 VALIDATION VS 2025 FINAL TEST"
    )

    print(
        "=" * 120
    )


    print(
        generalization_df
        .round(
            4
        )
        .to_string(
            index=False
        )
    )


print(
    "\n"
    + "=" * 120
)

print(
    "STEP 21 SUMMARY"
)

print(
    "=" * 120
)

print(
    "- Final 2025 lockbox evaluation completed"
)

print(
    "- Frozen Step 20 Tuned Random Forest strategy was used"
)

print(
    "- H1/H3/H6 used their frozen Step 16 RF configurations"
)

print(
    "- Strict rolling-origin target availability was enforced"
)

print(
    "- No tuning was performed"
)

print(
    "- No model selection was performed"
)

print(
    "- 2025 results must NOT be used to change the frozen strategy"
)


print(
    "\nSaved reports:"
)

print(
    prediction_path
)

print(
    metrics_path
)

print(
    district_metrics_path
)

print(
    origin_audit_path
)

print(
    generalization_path
)

print(
    audit_text_path
)


print(
    "\nSaved figure:"
)

print(
    figure_path
)


print(
    "\nSTEP 21 - FINAL 2025 LOCKBOX TEST COMPLETE"
)

print(
    "=" * 120
)
