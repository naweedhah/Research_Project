# ============================================================

# STEP 22 - FINAL RANDOM FOREST SHAP EXPLAINABILITY

# Childhood Malnutrition Forecasting Research

#

# IMPORTANT:

# This file mirrors STEP 21 exactly for:

# - input split files

# - 153-feature manifest

# - frozen Step 20 strategy JSON

# - rolling-origin training history

# - origin-specific median imputation

# - district one-hot encoding

# - Random Forest construction

#

# STEP 22 only adds SHAP explanation.

# It does NOT tune or re-select the model.

# ============================================================



from pathlib import Path

import json

import warnings



import numpy as np

import pandas as pd

import matplotlib.pyplot as plt



from sklearn.ensemble import RandomForestRegressor



try:

    import shap

except ImportError as exc:

    raise ImportError(

        "\nSHAP is not installed.\n"

        "Run:\n"

        "python -m pip install shap\n"

    ) from exc





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



TOP_GLOBAL = 20



TOP_LOCAL = 10

SHAP_ADDITIVITY_TOLERANCE = 1e-5





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



STEP21_PREDICTION_PATH = (

    REPORT_DIR

    / "21_final_2025_lockbox_predictions.csv"

)





# ============================================================

# 3. INTRODUCTION

# ============================================================



print(

    "\n"

    + "=" * 120

)



print(

    "STEP 22 - FINAL RANDOM FOREST SHAP EXPLAINABILITY"

)



print(

    "=" * 120

)



print(

    "\nMethodology protection:"

)



print(

    "- Exact Step 21 data-loading logic is reused"

)



print(

    "- Exact Step 21 preprocessing logic is reused"

)



print(

    "- Exact Step 20 frozen model strategy is reused"

)



print(

    "- No hyperparameter tuning is performed"

)



print(

    "- No model selection is performed"

)



print(

    "- 2025 is used only for final explanation/evaluation"

)



print(

    "- Step 22 predictions MUST reproduce Step 21"

)





# ============================================================

# ============================================================

# 3B. SHAP HELPERS

# ============================================================


def normalize_shap_array(values, expected_rows, expected_features):

    array = np.asarray(values, dtype=float)

    if array.ndim == 3 and array.shape[-1] == 1:
        array = array[:, :, 0]

    if array.ndim != 2:
        raise ValueError(
            f"Unexpected SHAP output shape: {array.shape}"
        )

    if array.shape != (expected_rows, expected_features):
        raise ValueError(
            "SHAP shape mismatch. "
            f"Expected {(expected_rows, expected_features)}, "
            f"found {array.shape}."
        )

    return array


def scalar_expected_value(expected_value):

    return float(
        np.asarray(
            expected_value,
            dtype=float,
        ).reshape(-1)[0]
    )


# 4. LOAD + VERIFY FROZEN STEP 20 STRATEGY

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

# 5. EXACT STEP 21 PREPROCESSING

# ============================================================



def build_model_matrices_with_names(

    training_dataframe,

    prediction_dataframe,

    feature_columns,

):

    """

    This mirrors STEP 21 build_model_matrices exactly,

    but also returns feature names for SHAP plotting.

    """



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





    X_train_df = (

        pd.concat(

            [

                X_train_numeric,

                train_dummies,

            ],

            axis=1,

        )

    )





    X_prediction_df = (

        pd.concat(

            [

                X_prediction_numeric,

                prediction_dummies,

            ],

            axis=1,

        )

    )





    X_train = (

        X_train_df

        .to_numpy(

            dtype=float

        )

    )





    X_prediction = (

        X_prediction_df

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





    feature_names = (

        X_train_df

        .columns

        .tolist()

    )





    return (

        X_train,

        y_train,

        X_prediction,

        all_missing_features,

        feature_names,

        X_prediction_df,

    )





# ============================================================

# 6. EXACT STEP 21 RANDOM FOREST FACTORY

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

# 7. LOAD EXACT STEP 21 INPUTS

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

                "Required Step 22 input file not found:\n"

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

            f"H{horizon}: test target dates are not exclusively 2025."

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

            f"H{horizon}: expected "

            f"{EXPECTED_FEATURE_COUNT} features, "

            f"found {len(feature_columns)}."

        )





    missing_feature_columns = [

        feature

        for feature in feature_columns

        if feature not in train_df.columns

    ]



    if missing_feature_columns:



        raise ValueError(

            f"H{horizon}: feature manifest contains columns "

            f"missing from split data:\n"

            f"{missing_feature_columns}"

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

# 8. STRICT 2025 SHAP EXPLANATION

# ============================================================



print(

    "\n"

    + "=" * 120

)



print(

    "FINAL RANDOM FOREST - 2025 STRICT SHAP EXPLANATION"

)



print(

    "=" * 120

)





prediction_records = []



origin_audit_records = []

shap_additivity_audit_records = []



full_shap_records = []



local_driver_records = []



global_accumulator = {

    horizon: []

    for horizon in HORIZONS

}



plot_data = {}





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

        f"H{horizon} SHAP "

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





    horizon_plot_shap = []



    horizon_plot_x = []



    horizon_plot_feature_names = None





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

            model_feature_names,

            X_prediction_df,

        ) = build_model_matrices_with_names(

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





        # ----------------------------------------------------
        # SHAP + STRICT ADDITIVITY AUDIT
        # ----------------------------------------------------

        explainer = shap.TreeExplainer(
            model
        )

        try:
            raw_shap_values = explainer.shap_values(
                X_prediction,
                check_additivity=False,
            )
        except TypeError:
            raw_shap_values = explainer.shap_values(
                X_prediction
            )

        shap_values = normalize_shap_array(
            raw_shap_values,
            expected_rows=len(X_prediction),
            expected_features=len(model_feature_names),
        )

        expected_value = scalar_expected_value(
            explainer.expected_value
        )

        shap_reconstructed_predictions = (
            expected_value
            + shap_values.sum(axis=1)
        )

        shap_additivity_difference = np.abs(
            shap_reconstructed_predictions
            - predictions
        )

        max_shap_additivity_difference = float(
            shap_additivity_difference.max()
        )

        mean_shap_additivity_difference = float(
            shap_additivity_difference.mean()
        )

        shap_additivity_mismatch_count = int(
            (
                shap_additivity_difference
                > SHAP_ADDITIVITY_TOLERANCE
            ).sum()
        )

        shap_additivity_pass = (
            shap_additivity_mismatch_count == 0
        )

        shap_additivity_audit_records.append({
            "Horizon_Months": horizon,
            "Config_ID": config_id,
            "Forecast_Origin_Date": origin_date,
            "Prediction_Rows": len(prediction_rows),
            "SHAP_Baseline": expected_value,
            "Additivity_Tolerance": SHAP_ADDITIVITY_TOLERANCE,
            "Max_Absolute_Additivity_Difference":
                max_shap_additivity_difference,
            "Mean_Absolute_Additivity_Difference":
                mean_shap_additivity_difference,
            "Mismatch_Count": shap_additivity_mismatch_count,
            "Status": "PASS" if shap_additivity_pass else "FAIL",
        })

        if not shap_additivity_pass:

            diagnostic_df = prediction_rows[
                [
                    "District",
                    "Forecast_Origin_Date",
                    "Forecast_Target_Date",
                ]
            ].copy()

            diagnostic_df["RF_Prediction"] = predictions
            diagnostic_df["SHAP_Baseline"] = expected_value
            diagnostic_df["Sum_SHAP"] = shap_values.sum(axis=1)

            diagnostic_df[
                "SHAP_Reconstructed_Prediction"
            ] = shap_reconstructed_predictions

            diagnostic_df[
                "Absolute_Additivity_Difference"
            ] = shap_additivity_difference

            diagnostic_path = (
                REPORT_DIR
                / (
                    f"22_h{horizon}_"
                    f"{origin_date.strftime('%Y%m')}_"
                    "shap_additivity_failure.csv"
                )
            )

            diagnostic_df.to_csv(
                diagnostic_path,
                index=False,
            )

            raise RuntimeError(
                f"H{horizon} {origin_date.date()}: "
                "SHAP additivity failed. "
                f"Max difference="
                f"{max_shap_additivity_difference:.12f}; "
                f"mismatches="
                f"{shap_additivity_mismatch_count}. "
                f"Diagnostic saved to: {diagnostic_path}"
            )


        horizon_plot_shap.append(

            shap_values

        )



        horizon_plot_x.append(

            X_prediction

        )



        horizon_plot_feature_names = (

            model_feature_names

        )





        print(

            f"H{horizon} origin "

            f"{origin_number}/{len(origins)} "

            f"| {origin_date.date()} "

            f"| train={len(training_pool)} "

            f"| predict={len(prediction_rows)} "

            f"| SHAP additivity max diff={max_shap_additivity_difference:.12f} | PASS"

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



            "Model_Feature_Count":

                len(

                    model_feature_names

                ),

            "SHAP_Additivity_Max_Difference":
                max_shap_additivity_difference,

            "SHAP_Additivity_Mismatch_Count":
                shap_additivity_mismatch_count,

            "SHAP_Additivity_Status":
                "PASS" if shap_additivity_pass else "FAIL",

        })





        for row_number, (

            _,

            row,

        ) in enumerate(

            prediction_rows.iterrows()

        ):



            actual_target = float(

                row[

                    TARGET

                ]

            )



            prediction = float(

                predictions[

                    row_number

                ]

            )



            district = str(

                row[

                    "District"

                ]

            )



            target_date = row[

                "Forecast_Target_Date"

            ]



            row_shap = (

                shap_values[

                    row_number

                ]

            )



            row_feature_values = (

                X_prediction[

                    row_number

                ]

            )





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

                    district,



                "Forecast_Origin_Date":

                    origin_date,



                "Forecast_Target_Date":

                    target_date,



                "Actual_Target":

                    actual_target,



                "Prediction":

                    prediction,



                "Absolute_Error":

                    abs(

                        actual_target

                        -

                        prediction

                    ),



                "Signed_Error":

                    prediction

                    -

                    actual_target,



                "Expected_Value":

                    expected_value,

            })





            local_df = pd.DataFrame({

                "Feature":

                    model_feature_names,



                "Feature_Value":

                    row_feature_values,



                "SHAP_Value":

                    row_shap,

            })



            local_df[

                "Abs_SHAP_Value"

            ] = (

                local_df[

                    "SHAP_Value"

                ]

                .abs()

            )





            for _, local_row in (

                local_df

                .sort_values(

                    "Abs_SHAP_Value",

                    ascending=False

                )

                .head(

                    TOP_LOCAL

                )

                .reset_index(

                    drop=True

                )

                .iterrows()

            ):



                rank = (

                    int(

                        _

                    )

                    +

                    1

                )



                local_driver_records.append({

                    "Horizon_Months":

                        horizon,



                    "Config_ID":

                        config_id,



                    "District":

                        district,



                    "Forecast_Origin_Date":

                        origin_date,



                    "Forecast_Target_Date":

                        target_date,



                    "Actual_Target":

                        actual_target,



                    "Prediction":

                        prediction,



                    "Expected_Value":

                        expected_value,



                    "Rank":

                        rank,



                    "Feature":

                        local_row[

                            "Feature"

                        ],



                    "Feature_Value":

                        float(

                            local_row[

                                "Feature_Value"

                            ]

                        ),



                    "SHAP_Value":

                        float(

                            local_row[

                                "SHAP_Value"

                            ]

                        ),



                    "Abs_SHAP_Value":

                        float(

                            local_row[

                                "Abs_SHAP_Value"

                            ]

                        ),



                    "Direction":

                        (

                            "Pushes prediction higher"

                            if

                            local_row[

                                "SHAP_Value"

                            ]

                            >=

                            0

                            else

                            "Pushes prediction lower"

                        ),

                })





            for feature_index, feature_name in enumerate(

                model_feature_names

            ):



                shap_value = float(

                    row_shap[

                        feature_index

                    ]

                )



                full_shap_records.append({

                    "Horizon_Months":

                        horizon,



                    "Config_ID":

                        config_id,



                    "District":

                        district,



                    "Forecast_Origin_Date":

                        origin_date,



                    "Forecast_Target_Date":

                        target_date,



                    "Feature":

                        feature_name,



                    "Feature_Value":

                        float(

                            row_feature_values[

                                feature_index

                            ]

                        ),



                    "SHAP_Value":

                        shap_value,



                    "Abs_SHAP_Value":

                        abs(

                            shap_value

                        ),

                })





    plot_data[

        horizon

    ] = {

        "shap":

            np.vstack(

                horizon_plot_shap

            ),



        "x":

            np.vstack(

                horizon_plot_x

            ),



        "feature_names":

            horizon_plot_feature_names,

    }





# ============================================================

# 9. SAVE PREDICTIONS + SHAP TABLES

# ============================================================



prediction_df = pd.DataFrame(

    prediction_records

)



origin_audit_df = pd.DataFrame(

    origin_audit_records

)



full_shap_df = pd.DataFrame(

    full_shap_records

)



local_driver_df = pd.DataFrame(

    local_driver_records

)

shap_additivity_audit_df = pd.DataFrame(

    shap_additivity_audit_records

)





prediction_output_path = (

    REPORT_DIR

    / "22_final_rf_shap_predictions.csv"

)



origin_audit_output_path = (

    REPORT_DIR

    / "22_final_rf_shap_origin_audit.csv"

)



full_shap_output_path = (

    REPORT_DIR

    / "22_final_rf_shap_values_long.csv"

)



local_driver_output_path = (

    REPORT_DIR

    / "22_final_rf_local_top_drivers.csv"

)

shap_additivity_audit_output_path = (

    REPORT_DIR

    / "22_final_rf_shap_additivity_audit.csv"

)





prediction_df.to_csv(

    prediction_output_path,

    index=False,

)



origin_audit_df.to_csv(

    origin_audit_output_path,

    index=False,

)



full_shap_df.to_csv(

    full_shap_output_path,

    index=False,

)



local_driver_df.to_csv(

    local_driver_output_path,

    index=False,

)

shap_additivity_audit_df.to_csv(

    shap_additivity_audit_output_path,

    index=False,

)





# ============================================================

# 10. HARD SHAP ADDITIVITY AUDIT

# ============================================================


print(
    "\n"
    + "=" * 120
)

print(
    "SHAP ADDITIVITY AUDIT"
)

print(
    "=" * 120
)


if shap_additivity_audit_df.empty:

    raise RuntimeError(
        "No SHAP additivity audit rows were generated."
    )


if not shap_additivity_audit_df["Status"].eq("PASS").all():

    raise RuntimeError(
        "At least one SHAP additivity audit failed. "
        "Do NOT use Step 22 SHAP outputs."
    )


overall_max_shap_additivity_difference = float(

    shap_additivity_audit_df[
        "Max_Absolute_Additivity_Difference"
    ]
    .max()

)


print(
    "Origins audited                    : "
    f"{len(shap_additivity_audit_df)}"
)


print(
    "Maximum SHAP additivity difference : "
    f"{overall_max_shap_additivity_difference:.12f}"
)


print(
    "[PASS] SHAP baseline + sum(SHAP) reproduced "
    "the Random Forest predictions at every origin."
)


# ============================================================

# 11. HARD STEP 21 REPRODUCTION AUDIT

# ============================================================




print(

    "\n"

    + "=" * 120

)



print(

    "STEP 21 PREDICTION REPRODUCTION AUDIT"

)



print(

    "=" * 120

)





if not STEP21_PREDICTION_PATH.exists():



    raise FileNotFoundError(

        "Step 21 final prediction file was not found:\n"

        f"{STEP21_PREDICTION_PATH}"

    )





step21_df = pd.read_csv(

    STEP21_PREDICTION_PATH

)





for dataframe in [

    prediction_df,

    step21_df,

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





comparison_keys = [

    "Horizon_Months",

    "District",

    "Forecast_Origin_Date",

    "Forecast_Target_Date",

]





comparison_df = (

    prediction_df[

        comparison_keys

        +

        [

            "Prediction"

        ]

    ]

    .rename(

        columns={

            "Prediction":

                "Step22_Prediction"

        }

    )

    .merge(

        step21_df[

            comparison_keys

            +

            [

                "Prediction"

            ]

        ]

        .rename(

            columns={

                "Prediction":

                    "Step21_Prediction"

            }

        ),

        on=

            comparison_keys,

        how=

            "outer",

        indicator=

            True,

    )

)





comparison_df[

    "Absolute_Prediction_Difference"

] = (

    comparison_df[

        "Step22_Prediction"

    ]

    -

    comparison_df[

        "Step21_Prediction"

    ]

).abs()





comparison_output_path = (

    REPORT_DIR

    / "22_step21_prediction_reproduction_audit.csv"

)





comparison_df.to_csv(

    comparison_output_path,

    index=False,

)





if not (

    comparison_df[

        "_merge"

    ]

    .eq(

        "both"

    )

    .all()

):



    raise AssertionError(

        "Step 21 / Step 22 prediction rows do not match."

    )





max_difference = float(

    comparison_df[

        "Absolute_Prediction_Difference"

    ]

    .max()

)





print(

    "Maximum absolute prediction difference: "

    f"{max_difference:.12f}"

)





if (

    max_difference

    >

    1e-10

):



    raise AssertionError(

        "\n[FAIL] Step 22 did not exactly reproduce Step 21.\n"

        "Do NOT interpret SHAP outputs yet.\n"

        f"Audit file:\n{comparison_output_path}"

    )





print(

    "[PASS] Step 22 reproduced Step 21 predictions exactly."

)





# ============================================================

# 12. GLOBAL SHAP SUMMARY

# ============================================================



global_summary = (

    full_shap_df

    .groupby(

        [

            "Horizon_Months",

            "Feature",

        ],

        as_index=False,

    )

    .agg(

        Mean_Abs_SHAP=(

            "Abs_SHAP_Value",

            "mean"

        ),



        Mean_SHAP=(

            "SHAP_Value",

            "mean"

        ),

    )

)





global_summary[

    "Rank"

] = (

    global_summary

    .groupby(

        "Horizon_Months"

    )[

        "Mean_Abs_SHAP"

    ]

    .rank(

        method="first",

        ascending=False

    )

    .astype(int)

)





global_summary = (

    global_summary

    .sort_values(

        [

            "Horizon_Months",

            "Rank",

        ]

    )

)





global_summary_path = (

    REPORT_DIR

    / "22_final_rf_global_shap_importance.csv"

)





global_summary.to_csv(

    global_summary_path,

    index=False,

)





# ============================================================

# 13. DISTRICT-LEVEL SHAP SUMMARY

# ============================================================



district_summary = (

    full_shap_df

    .groupby(

        [

            "Horizon_Months",

            "District",

            "Feature",

        ],

        as_index=False,

    )

    .agg(

        Mean_Abs_SHAP=(

            "Abs_SHAP_Value",

            "mean"

        ),



        Mean_SHAP=(

            "SHAP_Value",

            "mean"

        ),

    )

)





district_summary[

    "Rank_Within_District"

] = (

    district_summary

    .groupby(

        [

            "Horizon_Months",

            "District",

        ]

    )[

        "Mean_Abs_SHAP"

    ]

    .rank(

        method="first",

        ascending=False

    )

    .astype(int)

)





district_summary_path = (

    REPORT_DIR

    / "22_final_rf_district_shap_summary.csv"

)





district_summary.to_csv(

    district_summary_path,

    index=False,

)





district_top10_path = (

    REPORT_DIR

    / "22_final_rf_district_top10_drivers.csv"

)





district_summary[

    district_summary[

        "Rank_Within_District"

    ]

    <=

    10

].sort_values(

    [

        "Horizon_Months",

        "District",

        "Rank_Within_District",

    ]

).to_csv(

    district_top10_path,

    index=False,

)





# ============================================================

# 14. GLOBAL SHAP BAR FIGURES

# ============================================================



for horizon in HORIZONS:



    top_df = (

        global_summary[

            global_summary[

                "Horizon_Months"

            ]

            ==

            horizon

        ]

        .sort_values(

            "Rank"

        )

        .head(

            TOP_GLOBAL

        )

        .sort_values(

            "Mean_Abs_SHAP"

        )

    )





    plt.figure(

        figsize=(

            10,

            8,

        )

    )



    plt.barh(

        top_df[

            "Feature"

        ],

        top_df[

            "Mean_Abs_SHAP"

        ],

    )



    plt.title(

        f"H{horizon} Random Forest - Global SHAP Importance"

    )



    plt.xlabel(

        "Mean absolute SHAP value"

    )



    plt.ylabel(

        "Feature"

    )



    plt.tight_layout()





    figure_path = (

        FIGURE_DIR

        / f"22_rf_h{horizon}_shap_global_bar.png"

    )





    plt.savefig(

        figure_path,

        dpi=300,

        bbox_inches="tight",

    )



    plt.close()





# ============================================================

# 15. SHAP SUMMARY / BEESWARM FIGURES

# ============================================================



for horizon in HORIZONS:



    current_plot = (

        plot_data[

            horizon

        ]

    )





    plt.figure(

        figsize=(

            11,

            8,

        )

    )





    shap.summary_plot(

        current_plot[

            "shap"

        ],

        current_plot[

            "x"

        ],

        feature_names=

            current_plot[

                "feature_names"

            ],

        max_display=

            TOP_GLOBAL,

        show=

            False,

    )





    plt.title(

        f"H{horizon} Random Forest - SHAP Summary"

    )



    plt.tight_layout()





    figure_path = (

        FIGURE_DIR

        / f"22_rf_h{horizon}_shap_beeswarm.png"

    )





    plt.savefig(

        figure_path,

        dpi=300,

        bbox_inches="tight",

    )



    plt.close()





# ============================================================

# 16. PRINT FINAL GLOBAL RESULTS

# ============================================================



print(

    "\n"

    + "=" * 120

)



print(

    "FINAL GLOBAL SHAP SUMMARY"

)



print(

    "=" * 120

)





for horizon in HORIZONS:



    print(

        "\n"

        + "-" * 120

    )



    print(

        f"H{horizon} TOP 10 DRIVERS"

    )



    print(

        "-" * 120

    )





    horizon_top10 = (

        global_summary[

            global_summary[

                "Horizon_Months"

            ]

            ==

            horizon

        ]

        .sort_values(

            "Rank"

        )

        .head(

            10

        )

    )





    print(

        horizon_top10[

            [

                "Rank",

                "Feature",

                "Mean_Abs_SHAP",

                "Mean_SHAP",

            ]

        ]

        .round(

            6

        )

        .to_string(

            index=False

        )

    )





# ============================================================

# 17. FINAL SUMMARY

# ============================================================



print(

    "\n"

    + "=" * 120

)



print(

    "STEP 22 SUMMARY"

)



print(

    "=" * 120

)





print(

    "- Exact Step 21 split inputs were reused"

)



print(

    "- Exact Step 09 feature manifests were reused"

)



print(

    "- Exact Step 20 frozen parameters were reused"

)



print(

    "- Exact Step 21 rolling preprocessing was reused"

)



print(

    "- Step 21 predictions were reproduced exactly"

)

print(

    "- SHAP baseline + sum(SHAP) reproduced every RF prediction"

)



print(

    "- H1/H3/H6 SHAP explanations were generated"

)



print(

    "- Global and district-level SHAP summaries were generated"

)



print(

    "- No tuning or model reselection was performed"

)





print(

    "\nInterpretation:"

)



print(

    "- Positive SHAP = feature pushes prediction higher"

)



print(

    "- Negative SHAP = feature pushes prediction lower"

)



print(

    "- SHAP explains model contribution, NOT causal effect"

)





print(

    "\nReports saved to:"

)



print(

    REPORT_DIR

)





print(

    "\nFigures saved to:"

)



print(

    FIGURE_DIR

)





print(

    "\nSTEP 22 - FINAL RANDOM FOREST SHAP "

    "EXPLAINABILITY COMPLETE"

)



print(

    "=" * 120

)
