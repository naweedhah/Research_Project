# ============================================================
# STEP 28 - FUTURE RANDOM FOREST SHAP EXPLAINABILITY
# 2026-2030
#
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Explain every final Random Forest future point forecast
# generated in Step 27, while keeping the Step 27B NGBoost
# uncertainty information alongside the explanation.
#
# FINAL FUTURE OUTPUT FOR EACH FORECAST
# -------------------------------------
# - RF Predicted Cases
# - NGBoost 95% Prediction Range
# - Uncertainty Level
# - Confidence Label
# - SHAP local explanation / top drivers
#
# IMPORTANT METHODOLOGY RULES
# ---------------------------
# 1. Random Forest remains the final POINT forecast model.
# 2. NGBoost remains the separate uncertainty model.
# 3. SHAP explains the Random Forest prediction only.
# 4. No model tuning or model selection is done here.
# 5. No 2026-2030 actual target values are used.
# 6. The exact Step 27 future feature state is reconstructed.
# 7. The exact saved Step 27 Random Forest model bundles are used.
# 8. Step 27 predictions must be reproduced before SHAP results
#    are accepted.
# 9. SHAP additivity is audited:
#
#       RF prediction ~= SHAP baseline + sum(SHAP values)
#
# MAIN INPUT
# ----------
# outputs/reports/
#   27b_future_forecasts_with_ngboost_uncertainty_2026_2030.csv
#
# MAIN OUTPUT
# -----------
# outputs/reports/
#   28_future_explainable_forecasts_2026_2030.csv
#
# Additional detailed SHAP outputs are also saved.
# ============================================================

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import shap
except ImportError as exc:
    raise ImportError(
        "The 'shap' package is required for Step 28.\n"
        "Install it in your active environment with:\n"
        "pip install shap"
    ) from exc


# ============================================================
# 1. SETTINGS
# ============================================================

warnings.filterwarnings("ignore")

HORIZONS = [1, 3, 6]

TARGET = "Malnutrition_Cases"
DISTRICT_COL = "District"
DATE_COL = "Date"

ORIGIN_DATE_COL = "Forecast_Origin_Date"
TARGET_DATE_COL = "Forecast_Target_Date"

ACTUAL_CUTOFF = pd.Timestamp("2025-12-01")
FUTURE_TARGET_START = pd.Timestamp("2026-01-01")
FUTURE_TARGET_END = pd.Timestamp("2030-12-01")

PREDICTOR_LAGS = [1, 3, 6, 12]
TARGET_LAGS = [1, 3, 6, 12]
ROLLING_WINDOWS = [3, 6, 12]

EXPECTED_DISTRICTS = 25

EXPECTED_FUTURE_ROWS = {
    1: 1500,
    3: 1450,
    6: 1375,
}

EXPECTED_TOTAL_ROWS = sum(
    EXPECTED_FUTURE_ROWS.values()
)

TOP_LOCAL_DRIVERS = 5
TOP_GLOBAL_FEATURES_PLOT = 20

# Prediction reproduction tolerance.
PREDICTION_TOLERANCE = 1e-6

# SHAP additivity tolerance.
SHAP_ADDITIVITY_TOLERANCE = 1e-5

# SHAP is calculated in batches so memory use stays controlled.
SHAP_BATCH_SIZE = 250


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
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

MODEL_DIR = (
    BASE_DIR
    / "outputs"
    / "models"
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

BASE_DATA_PATH = (
    PROCESSED_DIR
    / "malnutrition_preprocessed_base.csv"
)

STEP27_PREDICTOR_PATH = (
    REPORT_DIR
    / "27_future_predictor_projection.csv"
)

STEP27B_FUTURE_PATH = (
    REPORT_DIR
    / "27b_future_forecasts_with_ngboost_uncertainty_2026_2030.csv"
)

RF_MODEL_PATHS = {
    1:
        MODEL_DIR
        / "27_final_future_rf_h1.joblib",

    3:
        MODEL_DIR
        / "27_final_future_rf_h3.joblib",

    6:
        MODEL_DIR
        / "27_final_future_rf_h6.joblib",
}

PREDICTION_REPRODUCTION_PATH = (
    REPORT_DIR
    / "28_future_rf_shap_prediction_reproduction.csv"
)

SHAP_LONG_PATH = (
    REPORT_DIR
    / "28_future_rf_shap_values_long.csv"
)

LOCAL_TOP_DRIVERS_PATH = (
    REPORT_DIR
    / "28_future_rf_local_top_drivers.csv"
)

GLOBAL_IMPORTANCE_PATH = (
    REPORT_DIR
    / "28_future_rf_global_feature_importance.csv"
)

DISTRICT_SHAP_SUMMARY_PATH = (
    REPORT_DIR
    / "28_future_rf_district_shap_summary.csv"
)

DISTRICT_TOP10_PATH = (
    REPORT_DIR
    / "28_future_rf_district_top10_drivers.csv"
)

ENRICHED_FORECAST_PATH = (
    REPORT_DIR
    / "28_future_explainable_forecasts_2026_2030.csv"
)

AUDIT_PATH = (
    REPORT_DIR
    / "28_future_rf_shap_audit.csv"
)

METHODOLOGY_PATH = (
    REPORT_DIR
    / "28_future_rf_shap_methodology.json"
)


# ============================================================
# 3. DISPLAY HELPERS
# ============================================================

def print_header(
    title,
    width=120,
):
    print(
        "\n"
        +
        "=" * width
    )

    print(
        title
    )

    print(
        "=" * width
    )


def print_subheader(
    title,
    width=120,
):
    print(
        "\n"
        +
        "-" * width
    )

    print(
        title
    )

    print(
        "-" * width
    )


# ============================================================
# 4. BASIC HELPERS
# ============================================================

def safe_float(
    value
):
    try:
        if pd.isna(
            value
        ):
            return np.nan

        return float(
            value
        )

    except Exception:
        return np.nan


def month_distance(
    start,
    end,
):
    return (
        (
            end.year
            -
            start.year
        )
        *
        12
        +
        (
            end.month
            -
            start.month
        )
    )


def identify_monthly_predictor_columns(
    base_dataframe
):
    excluded_numeric = {
        TARGET,
        "Year",
        "Month",
        "Time_Index",
        "Month_Sin",
        "Month_Cos",
        "Forecast_Horizon",
        "Forecast_Target",
        "Forecast_Target_H1",
        "Forecast_Target_H3",
        "Forecast_Target_H6",
    }

    numeric_columns = (
        base_dataframe
        .select_dtypes(
            include=[
                np.number
            ]
        )
        .columns
        .tolist()
    )

    return [
        column
        for column in numeric_columns
        if column not in excluded_numeric
    ]


def feature_direction(
    shap_value
):
    if shap_value > 0:
        return "Increases Prediction"

    if shap_value < 0:
        return "Decreases Prediction"

    return "No Material Direction"


def explanation_text(
    feature_name,
    shap_value,
):
    magnitude = abs(
        float(
            shap_value
        )
    )

    if shap_value > 0:
        return (
            f"{feature_name} increased the RF forecast "
            f"by approximately {magnitude:.2f} cases "
            f"relative to the SHAP baseline."
        )

    if shap_value < 0:
        return (
            f"{feature_name} decreased the RF forecast "
            f"by approximately {magnitude:.2f} cases "
            f"relative to the SHAP baseline."
        )

    return (
        f"{feature_name} had approximately no local "
        f"effect on the RF forecast."
    )


def scalar_expected_value(
    expected_value
):
    array = np.asarray(
        expected_value,
        dtype=float,
    )

    return float(
        array.reshape(-1)[0]
    )


def normalize_shap_array(
    values,
    expected_rows,
    expected_features,
):
    array = np.asarray(
        values,
        dtype=float,
    )

    # Some SHAP versions can return an extra final singleton
    # output dimension for regression.
    if (
        array.ndim == 3
        and
        array.shape[-1] == 1
    ):
        array = array[:, :, 0]

    if (
        array.ndim != 2
    ):
        raise ValueError(
            "Unexpected SHAP output shape: "
            f"{array.shape}"
        )

    if (
        array.shape[0]
        !=
        expected_rows
        or
        array.shape[1]
        !=
        expected_features
    ):
        raise ValueError(
            "SHAP shape mismatch. "
            f"Expected ({expected_rows}, {expected_features}), "
            f"found {array.shape}."
        )

    return array


def get_shap_values_batched(
    explainer,
    x_data,
):
    batch_arrays = []

    total_rows = len(
        x_data
    )

    for start in range(
        0,
        total_rows,
        SHAP_BATCH_SIZE,
    ):
        end = min(
            start + SHAP_BATCH_SIZE,
            total_rows,
        )

        x_batch = (
            x_data
            .iloc[
                start:end
            ]
        )

        try:
            batch_values = (
                explainer.shap_values(
                    x_batch,
                    check_additivity=False,
                )
            )

        except TypeError:
            # Compatibility with older SHAP versions.
            batch_values = (
                explainer.shap_values(
                    x_batch
                )
            )

        batch_values = (
            normalize_shap_array(
                batch_values,
                len(
                    x_batch
                ),
                x_data.shape[1],
            )
        )

        batch_arrays.append(
            batch_values
        )

        print(
            f"    SHAP rows {start + 1}-{end} "
            f"of {total_rows}"
        )

    return np.vstack(
        batch_arrays
    )


# ============================================================
# 5. START
# ============================================================

print_header(
    "STEP 28 - FUTURE RANDOM FOREST SHAP EXPLAINABILITY 2026-2030"
)

print(
    "\nResearch-method protection:"
)

print(
    "- Random Forest remains the final point-forecast model"
)

print(
    "- NGBoost uncertainty from Step 27B is preserved, not replaced"
)

print(
    "- SHAP explains Random Forest predictions only"
)

print(
    "- No model tuning is performed"
)

print(
    "- No 2026-2030 actual target values are used"
)

print(
    "- Step 27 RF predictions must be reproduced before explanations are accepted"
)


# ============================================================
# 6. REQUIRED FILE CHECK
# ============================================================

required_paths = [
    BASE_DATA_PATH,
    STEP27_PREDICTOR_PATH,
    STEP27B_FUTURE_PATH,
]

required_paths.extend(
    RF_MODEL_PATHS.values()
)

for path in required_paths:

    if not (
        path.exists()
    ):
        raise FileNotFoundError(
            f"Required file not found:\n{path}"
        )


# ============================================================
# 7. LOAD BASE OBSERVED DATA
# ============================================================

print_header(
    "LOAD OBSERVED DATA AND STEP 27 FUTURE STATE"
)

base_df = pd.read_csv(
    BASE_DATA_PATH
)

base_df.columns = [
    column.strip()
    for column in base_df.columns
]

required_base_columns = {
    DISTRICT_COL,
    DATE_COL,
    TARGET,
}

missing_base_columns = (
    required_base_columns
    -
    set(
        base_df.columns
    )
)

if missing_base_columns:
    raise ValueError(
        "Base data is missing columns: "
        f"{sorted(missing_base_columns)}"
    )

base_df[
    DATE_COL
] = pd.to_datetime(
    base_df[
        DATE_COL
    ],
    errors="coerce",
)

if (
    base_df[
        DATE_COL
    ]
    .isna()
    .any()
):
    raise ValueError(
        "Invalid dates detected in base data."
    )

base_df = (
    base_df[
        base_df[
            DATE_COL
        ]
        <=
        ACTUAL_CUTOFF
    ]
    .copy()
)

base_df = (
    base_df
    .sort_values(
        [
            DISTRICT_COL,
            DATE_COL,
        ]
    )
    .reset_index(
        drop=True
    )
)

districts = sorted(
    base_df[
        DISTRICT_COL
    ]
    .astype(str)
    .dropna()
    .unique()
    .tolist()
)

if (
    len(
        districts
    )
    !=
    EXPECTED_DISTRICTS
):
    raise ValueError(
        f"Expected {EXPECTED_DISTRICTS} districts, "
        f"found {len(districts)}."
    )

minimum_date = (
    base_df[
        DATE_COL
    ]
    .min()
)

observed_max_date = (
    base_df[
        DATE_COL
    ]
    .max()
)

if (
    observed_max_date
    !=
    ACTUAL_CUTOFF
):
    raise ValueError(
        "Observed data must end at 2025-12-01. "
        f"Found {observed_max_date.date()}."
    )

monthly_predictors = (
    identify_monthly_predictor_columns(
        base_df
    )
)

print(
    f"Observed period     : "
    f"{minimum_date.date()} to "
    f"{observed_max_date.date()}"
)

print(
    f"Districts          : "
    f"{len(districts)}"
)

print(
    f"Monthly predictors : "
    f"{len(monthly_predictors)}"
)


# ============================================================
# 8. LOAD STEP 27 PREDICTOR PROJECTION
# ============================================================

future_predictor_df = pd.read_csv(
    STEP27_PREDICTOR_PATH
)

if (
    DATE_COL
    not in
    future_predictor_df.columns
    or
    DISTRICT_COL
    not in
    future_predictor_df.columns
):
    raise ValueError(
        "Step 27 future predictor projection must "
        "contain District and Date."
    )

future_predictor_df[
    DATE_COL
] = pd.to_datetime(
    future_predictor_df[
        DATE_COL
    ],
    errors="coerce",
)

if (
    future_predictor_df[
        DATE_COL
    ]
    .isna()
    .any()
):
    raise ValueError(
        "Invalid dates in Step 27 future predictor projection."
    )

missing_projected_predictors = [
    predictor
    for predictor in monthly_predictors
    if predictor not in future_predictor_df.columns
]

if missing_projected_predictors:
    raise ValueError(
        "Step 27 future predictor projection is missing "
        f"{len(missing_projected_predictors)} predictors. "
        f"Examples: {missing_projected_predictors[:10]}"
    )

expected_predictor_rows = (
    60
    *
    EXPECTED_DISTRICTS
)

if (
    len(
        future_predictor_df
    )
    !=
    expected_predictor_rows
):
    raise ValueError(
        f"Expected {expected_predictor_rows} future "
        f"predictor rows, found {len(future_predictor_df)}."
    )

print(
    f"Future predictor rows: "
    f"{len(future_predictor_df)}"
)


# ============================================================
# 9. LOAD STEP 27B UNCERTAINTY-ENRICHED FUTURE FORECASTS
# ============================================================

future_df = pd.read_csv(
    STEP27B_FUTURE_PATH
)

required_future_columns = {
    "Point_Forecast_Model",
    "Uncertainty_Model",
    "Horizon_Months",
    DISTRICT_COL,
    ORIGIN_DATE_COL,
    TARGET_DATE_COL,
    "RF_Predicted_Cases",
    "NGBoost_Mean",
    "NGBoost_Lower_95",
    "NGBoost_Upper_95",
    "Uncertainty_Level",
    "Confidence_Label",
}

missing_future_columns = (
    required_future_columns
    -
    set(
        future_df.columns
    )
)

if missing_future_columns:
    raise ValueError(
        "Step 27B future output is missing columns: "
        f"{sorted(missing_future_columns)}"
    )

future_df[
    ORIGIN_DATE_COL
] = pd.to_datetime(
    future_df[
        ORIGIN_DATE_COL
    ],
    errors="coerce",
)

future_df[
    TARGET_DATE_COL
] = pd.to_datetime(
    future_df[
        TARGET_DATE_COL
    ],
    errors="coerce",
)

if (
    future_df[
        [
            ORIGIN_DATE_COL,
            TARGET_DATE_COL,
        ]
    ]
    .isna()
    .any()
    .any()
):
    raise ValueError(
        "Invalid dates detected in Step 27B future output."
    )

if (
    len(
        future_df
    )
    !=
    EXPECTED_TOTAL_ROWS
):
    raise ValueError(
        f"Expected {EXPECTED_TOTAL_ROWS} Step 27B rows, "
        f"found {len(future_df)}."
    )

if not (
    future_df[
        TARGET_DATE_COL
    ]
    .between(
        FUTURE_TARGET_START,
        FUTURE_TARGET_END,
    )
    .all()
):
    raise ValueError(
        "Step 27B contains target dates outside 2026-2030."
    )

for horizon, expected_rows in (
    EXPECTED_FUTURE_ROWS.items()
):

    horizon_rows = int(
        (
            future_df[
                "Horizon_Months"
            ]
            ==
            horizon
        )
        .sum()
    )

    if (
        horizon_rows
        !=
        expected_rows
    ):
        raise ValueError(
            f"H{horizon}: expected {expected_rows} rows, "
            f"found {horizon_rows}."
        )

future_df[
    "Forecast_ID"
] = np.arange(
    1,
    len(
        future_df
    )
    +
    1,
    dtype=int,
)

print(
    f"Step 27B future rows: "
    f"{len(future_df)} [PASS]"
)


# ============================================================
# 10. LOAD SAVED STEP 27 RF MODEL BUNDLES
# ============================================================

print_header(
    "LOAD SAVED STEP 27 RANDOM FOREST MODELS"
)

rf_bundles = {}

for horizon in HORIZONS:

    model_path = (
        RF_MODEL_PATHS[
            horizon
        ]
    )

    bundle = joblib.load(
        model_path
    )

    required_bundle_keys = {
        "model",
        "horizon",
        "config_id",
        "feature_columns",
        "model_columns",
        "feature_medians",
        "district_categories",
    }

    missing_bundle_keys = (
        required_bundle_keys
        -
        set(
            bundle.keys()
        )
    )

    if missing_bundle_keys:
        raise ValueError(
            f"H{horizon} model bundle is missing keys: "
            f"{sorted(missing_bundle_keys)}"
        )

    if (
        int(
            bundle[
                "horizon"
            ]
        )
        !=
        horizon
    ):
        raise ValueError(
            f"H{horizon}: saved bundle horizon mismatch."
        )

    if (
        len(
            bundle[
                "district_categories"
            ]
        )
        !=
        EXPECTED_DISTRICTS
    ):
        raise ValueError(
            f"H{horizon}: expected 25 district categories."
        )

    rf_bundles[
        horizon
    ] = bundle

    print(
        f"H{horizon} | "
        f"config={bundle['config_id']} "
        f"| engineered features="
        f"{len(bundle['feature_columns'])} "
        f"| final model columns="
        f"{len(bundle['model_columns'])}"
    )


# ============================================================
# 11. BUILD PREDICTOR LOOKUP
# ============================================================

predictor_lookup = {}

# Historical predictor values.
for _, row in (
    base_df
    .iterrows()
):

    district = str(
        row[
            DISTRICT_COL
        ]
    )

    date = pd.Timestamp(
        row[
            DATE_COL
        ]
    )

    for predictor in monthly_predictors:

        predictor_lookup[
            (
                district,
                date,
                predictor,
            )
        ] = safe_float(
            row[
                predictor
            ]
        )


# Future predictor projection from Step 27.
for _, row in (
    future_predictor_df
    .iterrows()
):

    district = str(
        row[
            DISTRICT_COL
        ]
    )

    date = pd.Timestamp(
        row[
            DATE_COL
        ]
    )

    for predictor in monthly_predictors:

        predictor_lookup[
            (
                district,
                date,
                predictor,
            )
        ] = safe_float(
            row[
                predictor
            ]
        )


# ============================================================
# 12. BUILD EXACT STEP 27 TARGET STATE
# ============================================================

target_state = {}

# Historical actual target values through 2025-12.
for _, row in (
    base_df
    .iterrows()
):

    district = str(
        row[
            DISTRICT_COL
        ]
    )

    date = pd.Timestamp(
        row[
            DATE_COL
        ]
    )

    target_state[
        (
            district,
            date,
        )
    ] = safe_float(
        row[
            TARGET
        ]
    )


# Step 27 recursive future target state uses ONLY H1 RF forecasts.
h1_future_df = (
    future_df[
        future_df[
            "Horizon_Months"
        ]
        ==
        1
    ]
    .copy()
)

if (
    len(
        h1_future_df
    )
    !=
    EXPECTED_FUTURE_ROWS[
        1
    ]
):
    raise ValueError(
        "Step 27B H1 future state is incomplete."
    )

for _, row in (
    h1_future_df
    .iterrows()
):

    district = str(
        row[
            DISTRICT_COL
        ]
    )

    target_date = pd.Timestamp(
        row[
            TARGET_DATE_COL
        ]
    )

    target_state[
        (
            district,
            target_date,
        )
    ] = float(
        row[
            "RF_Predicted_Cases"
        ]
    )

print(
    "Step 27 future predictor state reconstructed."
)

print(
    "Step 27 H1 recursive RF target state reconstructed."
)


# ============================================================
# 13. FEATURE STATE HELPERS
# ============================================================

def get_target_value(
    district,
    date,
):
    return target_state.get(
        (
            district,
            pd.Timestamp(
                date
            ),
        ),
        np.nan,
    )


def get_predictor_value(
    district,
    date,
    predictor,
):
    return predictor_lookup.get(
        (
            district,
            pd.Timestamp(
                date
            ),
            predictor,
        ),
        np.nan,
    )


def build_future_feature_row(
    district,
    origin_date,
):
    origin_date = pd.Timestamp(
        origin_date
    )

    row = {}

    # Calendar features.
    row[
        "Time_Index"
    ] = month_distance(
        minimum_date,
        origin_date,
    )

    row[
        "Month_Sin"
    ] = float(
        np.sin(
            2
            *
            np.pi
            *
            origin_date.month
            /
            12
        )
    )

    row[
        "Month_Cos"
    ] = float(
        np.cos(
            2
            *
            np.pi
            *
            origin_date.month
            /
            12
        )
    )

    # Target lags.
    for lag in TARGET_LAGS:

        lag_date = (
            origin_date
            -
            pd.DateOffset(
                months=lag
            )
        )

        row[
            f"Malnutrition_Lag_{lag}"
        ] = get_target_value(
            district,
            lag_date,
        )

    # Target rolling statistics.
    # Matches the prior leakage-safe feature design:
    # shift(1).rolling(window).
    for window in ROLLING_WINDOWS:

        previous_dates = [
            (
                origin_date
                -
                pd.DateOffset(
                    months=i
                )
            )
            for i in range(
                1,
                window + 1
            )
        ]

        values = np.asarray(
            [
                get_target_value(
                    district,
                    date,
                )
                for date in previous_dates
            ],
            dtype=float,
        )

        if np.isnan(
            values
        ).any():

            rolling_mean = np.nan
            rolling_std = np.nan

        else:

            rolling_mean = float(
                np.mean(
                    values
                )
            )

            rolling_std = (
                float(
                    np.std(
                        values,
                        ddof=1,
                    )
                )
                if
                len(
                    values
                )
                >
                1
                else
                np.nan
            )

        row[
            f"Malnutrition_Rolling_Mean_{window}"
        ] = rolling_mean

        row[
            f"Malnutrition_Rolling_STD_{window}"
        ] = rolling_std

    # Predictor lags.
    for predictor in monthly_predictors:

        for lag in PREDICTOR_LAGS:

            lag_date = (
                origin_date
                -
                pd.DateOffset(
                    months=lag
                )
            )

            row[
                f"{predictor}_Lag_{lag}"
            ] = get_predictor_value(
                district,
                lag_date,
                predictor,
            )

    return row


# ============================================================
# 14. TRANSFORM INTO EXACT RF MODEL MATRIX
# ============================================================

def build_model_matrix(
    metadata_df,
    horizon,
):
    bundle = (
        rf_bundles[
            horizon
        ]
    )

    feature_columns = list(
        bundle[
            "feature_columns"
        ]
    )

    model_columns = list(
        bundle[
            "model_columns"
        ]
    )

    district_categories = list(
        bundle[
            "district_categories"
        ]
    )

    median_dict = dict(
        bundle[
            "feature_medians"
        ]
    )

    feature_records = []

    for _, meta_row in (
        metadata_df
        .iterrows()
    ):

        district = str(
            meta_row[
                DISTRICT_COL
            ]
        )

        origin_date = pd.Timestamp(
            meta_row[
                ORIGIN_DATE_COL
            ]
        )

        feature_record = (
            build_future_feature_row(
                district,
                origin_date,
            )
        )

        feature_record[
            DISTRICT_COL
        ] = district

        feature_records.append(
            feature_record
        )

    generated_df = pd.DataFrame(
        feature_records
    )

    missing_features = [
        feature
        for feature in feature_columns
        if feature not in generated_df.columns
    ]

    if missing_features:
        raise ValueError(
            f"H{horizon}: generated future state is missing "
            f"{len(missing_features)} model features. "
            f"Examples: {missing_features[:10]}"
        )

    x_numeric = (
        generated_df[
            feature_columns
        ]
        .copy()
    )

    medians = pd.Series(
        {
            feature:
                safe_float(
                    median_dict.get(
                        feature,
                        0.0,
                    )
                )
            for feature in feature_columns
        }
    )

    medians = (
        medians
        .fillna(
            0.0
        )
    )

    x_numeric = (
        x_numeric
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

    categorical = pd.Categorical(
        generated_df[
            DISTRICT_COL
        ]
        .astype(str),

        categories=
            district_categories,
    )

    x_district = (
        pd.get_dummies(
            categorical,
            prefix="District",
            dtype=float,
        )
        .reset_index(
            drop=True
        )
    )

    x_model = pd.concat(
        [
            x_numeric,
            x_district,
        ],
        axis=1,
    )

    x_model = (
        x_model
        .reindex(
            columns=model_columns,
            fill_value=0.0,
        )
    )

    if (
        x_model
        .isna()
        .any()
        .any()
    ):
        raise ValueError(
            f"H{horizon}: missing values remain "
            "after model-matrix reconstruction."
        )

    return x_model


# ============================================================
# 15. REPRODUCE STEP 27 RF PREDICTIONS
# ============================================================

print_header(
    "REPRODUCE STEP 27 RANDOM FOREST FUTURE PREDICTIONS"
)

horizon_objects = {}

prediction_audit_records = []

for horizon in HORIZONS:

    print_subheader(
        f"H{horizon} - RECONSTRUCT MODEL MATRIX"
    )

    horizon_meta = (
        future_df[
            future_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
        .copy()
        .sort_values(
            [
                ORIGIN_DATE_COL,
                DISTRICT_COL,
            ]
        )
        .reset_index(
            drop=True
        )
    )

    x_model = (
        build_model_matrix(
            horizon_meta,
            horizon,
        )
    )

    model = (
        rf_bundles[
            horizon
        ][
            "model"
        ]
    )

    reproduced_predictions = np.asarray(
        model.predict(
            x_model
        ),
        dtype=float,
    )

    saved_predictions = (
        horizon_meta[
            "RF_Predicted_Cases"
        ]
        .astype(float)
        .to_numpy()
    )

    absolute_difference = np.abs(
        reproduced_predictions
        -
        saved_predictions
    )

    max_difference = float(
        absolute_difference.max()
    )

    mean_difference = float(
        absolute_difference.mean()
    )

    mismatch_count = int(
        (
            absolute_difference
            >
            PREDICTION_TOLERANCE
        )
        .sum()
    )

    reproduction_pass = (
        mismatch_count
        ==
        0
    )

    print(
        f"H{horizon} rows                 : "
        f"{len(horizon_meta)}"
    )

    print(
        f"H{horizon} max prediction diff  : "
        f"{max_difference:.12f}"
    )

    print(
        f"H{horizon} reproduction status  : "
        f"{'PASS' if reproduction_pass else 'FAIL'}"
    )

    prediction_audit_records.append({
        "Audit_Type":
            "PREDICTION_REPRODUCTION",

        "Horizon_Months":
            horizon,

        "Rows":
            len(
                horizon_meta
            ),

        "Model_Config":
            rf_bundles[
                horizon
            ][
                "config_id"
            ],

        "Prediction_Tolerance":
            PREDICTION_TOLERANCE,

        "Max_Absolute_Prediction_Difference":
            max_difference,

        "Mean_Absolute_Prediction_Difference":
            mean_difference,

        "Mismatch_Count":
            mismatch_count,

        "Status":
            (
                "PASS"
                if
                reproduction_pass
                else
                "FAIL"
            ),
    })

    if not reproduction_pass:
        raise RuntimeError(
            f"H{horizon}: Step 27 RF predictions were not "
            "reproduced exactly enough for safe SHAP analysis. "
            f"Max difference={max_difference:.12f}; "
            f"mismatches={mismatch_count}."
        )

    reproduction_df = (
        horizon_meta[
            [
                "Forecast_ID",
                DISTRICT_COL,
                ORIGIN_DATE_COL,
                TARGET_DATE_COL,
                "Horizon_Months",
                "RF_Predicted_Cases",
            ]
        ]
        .copy()
    )

    reproduction_df[
        "Reproduced_RF_Prediction"
    ] = reproduced_predictions

    reproduction_df[
        "Absolute_Prediction_Difference"
    ] = absolute_difference

    horizon_objects[
        horizon
    ] = {
        "metadata":
            horizon_meta,

        "x_model":
            x_model,

        "reproduced_predictions":
            reproduced_predictions,

        "reproduction_df":
            reproduction_df,
    }


# ============================================================
# 16. CALCULATE SHAP
# ============================================================

print_header(
    "CALCULATE TREE SHAP VALUES FOR ALL FUTURE RF FORECASTS"
)

shap_long_frames = []

local_top_frames = []

global_importance_frames = []

district_summary_frames = []

district_top10_frames = []

enriched_driver_frames = []

shap_audit_records = []

for horizon in HORIZONS:

    print_subheader(
        f"H{horizon} - TREE SHAP"
    )

    metadata_df = (
        horizon_objects[
            horizon
        ][
            "metadata"
        ]
        .copy()
    )

    x_model = (
        horizon_objects[
            horizon
        ][
            "x_model"
        ]
    )

    model = (
        rf_bundles[
            horizon
        ][
            "model"
        ]
    )

    rf_predictions = (
        horizon_objects[
            horizon
        ][
            "reproduced_predictions"
        ]
    )

    explainer = shap.TreeExplainer(
        model
    )

    baseline = scalar_expected_value(
        explainer.expected_value
    )

    print(
        f"H{horizon} SHAP baseline: "
        f"{baseline:.6f}"
    )

    shap_values = (
        get_shap_values_batched(
            explainer,
            x_model,
        )
    )

    # --------------------------------------------------------
    # Additivity audit.
    # --------------------------------------------------------

    shap_reconstructed_prediction = (
        baseline
        +
        shap_values.sum(
            axis=1
        )
    )

    additivity_difference = np.abs(
        shap_reconstructed_prediction
        -
        rf_predictions
    )

    max_additivity_difference = float(
        additivity_difference.max()
    )

    mean_additivity_difference = float(
        additivity_difference.mean()
    )

    additivity_mismatch_count = int(
        (
            additivity_difference
            >
            SHAP_ADDITIVITY_TOLERANCE
        )
        .sum()
    )

    additivity_pass = (
        additivity_mismatch_count
        ==
        0
    )

    print(
        f"H{horizon} max SHAP additivity diff : "
        f"{max_additivity_difference:.12f}"
    )

    print(
        f"H{horizon} SHAP additivity status   : "
        f"{'PASS' if additivity_pass else 'FAIL'}"
    )

    shap_audit_records.append({
        "Audit_Type":
            "SHAP_ADDITIVITY",

        "Horizon_Months":
            horizon,

        "Rows":
            len(
                metadata_df
            ),

        "SHAP_Baseline":
            baseline,

        "Additivity_Tolerance":
            SHAP_ADDITIVITY_TOLERANCE,

        "Max_Absolute_Additivity_Difference":
            max_additivity_difference,

        "Mean_Absolute_Additivity_Difference":
            mean_additivity_difference,

        "Mismatch_Count":
            additivity_mismatch_count,

        "Status":
            (
                "PASS"
                if
                additivity_pass
                else
                "FAIL"
            ),
    })

    if not additivity_pass:
        raise RuntimeError(
            f"H{horizon}: SHAP additivity audit failed. "
            f"Max difference="
            f"{max_additivity_difference:.12f}; "
            f"mismatches="
            f"{additivity_mismatch_count}."
        )

    # --------------------------------------------------------
    # Save complete long-form SHAP values.
    # --------------------------------------------------------

    feature_names = (
        x_model.columns
        .tolist()
    )

    feature_values_array = (
        x_model
        .to_numpy(
            dtype=float
        )
    )

    n_rows = len(
        metadata_df
    )

    n_features = len(
        feature_names
    )

    long_frame = pd.DataFrame({
        "Forecast_ID":
            np.repeat(
                metadata_df[
                    "Forecast_ID"
                ]
                .to_numpy(),
                n_features,
            ),

        "Horizon_Months":
            np.repeat(
                horizon,
                n_rows
                *
                n_features,
            ),

        DISTRICT_COL:
            np.repeat(
                metadata_df[
                    DISTRICT_COL
                ]
                .astype(str)
                .to_numpy(),
                n_features,
            ),

        ORIGIN_DATE_COL:
            np.repeat(
                metadata_df[
                    ORIGIN_DATE_COL
                ]
                .to_numpy(),
                n_features,
            ),

        TARGET_DATE_COL:
            np.repeat(
                metadata_df[
                    TARGET_DATE_COL
                ]
                .to_numpy(),
                n_features,
            ),

        "Feature":
            np.tile(
                np.asarray(
                    feature_names,
                    dtype=object,
                ),
                n_rows,
            ),

        "Feature_Value":
            feature_values_array.reshape(
                -1
            ),

        "SHAP_Value":
            shap_values.reshape(
                -1
            ),
    })

    long_frame[
        "Absolute_SHAP_Value"
    ] = np.abs(
        long_frame[
            "SHAP_Value"
        ]
    )

    long_frame[
        "Direction"
    ] = np.where(
        long_frame[
            "SHAP_Value"
        ]
        >
        0,
        "Increases Prediction",
        np.where(
            long_frame[
                "SHAP_Value"
            ]
            <
            0,
            "Decreases Prediction",
            "No Material Direction",
        ),
    )

    shap_long_frames.append(
        long_frame
    )

    # --------------------------------------------------------
    # Top local drivers per forecast.
    # --------------------------------------------------------

    local_top = (
        long_frame
        .sort_values(
            [
                "Forecast_ID",
                "Absolute_SHAP_Value",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .groupby(
            "Forecast_ID",
            group_keys=False,
        )
        .head(
            TOP_LOCAL_DRIVERS
        )
        .copy()
    )

    local_top[
        "Driver_Rank"
    ] = (
        local_top
        .groupby(
            "Forecast_ID"
        )
        .cumcount()
        +
        1
    )

    local_top[
        "Explanation"
    ] = [
        explanation_text(
            feature_name,
            shap_value,
        )
        for feature_name, shap_value
        in zip(
            local_top[
                "Feature"
            ],
            local_top[
                "SHAP_Value"
            ],
        )
    ]

    local_top_frames.append(
        local_top
    )

    # --------------------------------------------------------
    # Global feature importance per horizon.
    # --------------------------------------------------------

    global_importance = (
        long_frame
        .groupby(
            "Feature",
            as_index=False,
        )
        .agg(
            Mean_Absolute_SHAP=(
                "Absolute_SHAP_Value",
                "mean",
            ),

            Mean_SHAP=(
                "SHAP_Value",
                "mean",
            ),

            Median_Absolute_SHAP=(
                "Absolute_SHAP_Value",
                "median",
            ),
        )
        .sort_values(
            "Mean_Absolute_SHAP",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    global_importance[
        "Global_Rank"
    ] = (
        np.arange(
            1,
            len(
                global_importance
            )
            +
            1,
            dtype=int,
        )
    )

    global_importance.insert(
        0,
        "Horizon_Months",
        horizon,
    )

    global_importance_frames.append(
        global_importance
    )

    # --------------------------------------------------------
    # District-level SHAP summary.
    # --------------------------------------------------------

    district_summary = (
        long_frame
        .groupby(
            [
                DISTRICT_COL,
                "Feature",
            ],
            as_index=False,
        )
        .agg(
            Mean_Absolute_SHAP=(
                "Absolute_SHAP_Value",
                "mean",
            ),

            Mean_SHAP=(
                "SHAP_Value",
                "mean",
            ),

            Forecast_Count=(
                "Forecast_ID",
                "nunique",
            ),
        )
    )

    district_summary.insert(
        0,
        "Horizon_Months",
        horizon,
    )

    district_summary_frames.append(
        district_summary
    )

    district_top10 = (
        district_summary
        .sort_values(
            [
                DISTRICT_COL,
                "Mean_Absolute_SHAP",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .groupby(
            DISTRICT_COL,
            group_keys=False,
        )
        .head(
            10
        )
        .copy()
    )

    district_top10[
        "District_Driver_Rank"
    ] = (
        district_top10
        .groupby(
            DISTRICT_COL
        )
        .cumcount()
        +
        1
    )

    district_top10_frames.append(
        district_top10
    )

    # --------------------------------------------------------
    # Top 3 local drivers as wide columns for dashboard/API.
    # --------------------------------------------------------

    top3 = (
        local_top[
            local_top[
                "Driver_Rank"
            ]
            <=
            3
        ]
        .copy()
    )

    wide_records = []

    for forecast_id, group in (
        top3
        .groupby(
            "Forecast_ID"
        )
    ):

        record = {
            "Forecast_ID":
                int(
                    forecast_id
                ),

            "SHAP_Baseline":
                baseline,
        }

        group = (
            group
            .sort_values(
                "Driver_Rank"
            )
        )

        for _, driver in (
            group
            .iterrows()
        ):

            rank = int(
                driver[
                    "Driver_Rank"
                ]
            )

            record[
                f"Top_Driver_{rank}_Feature"
            ] = driver[
                "Feature"
            ]

            record[
                f"Top_Driver_{rank}_Feature_Value"
            ] = float(
                driver[
                    "Feature_Value"
                ]
            )

            record[
                f"Top_Driver_{rank}_SHAP"
            ] = float(
                driver[
                    "SHAP_Value"
                ]
            )

            record[
                f"Top_Driver_{rank}_Direction"
            ] = driver[
                "Direction"
            ]

        wide_records.append(
            record
        )

    enriched_driver_frames.append(
        pd.DataFrame(
            wide_records
        )
    )

    # --------------------------------------------------------
    # Global SHAP bar plot.
    # --------------------------------------------------------

    plot_importance = (
        global_importance
        .head(
            TOP_GLOBAL_FEATURES_PLOT
        )
        .sort_values(
            "Mean_Absolute_SHAP",
            ascending=True,
        )
    )

    figure, axis = plt.subplots(
        figsize=(
            10,
            8,
        )
    )

    axis.barh(
        plot_importance[
            "Feature"
        ],

        plot_importance[
            "Mean_Absolute_SHAP"
        ],
    )

    axis.set_title(
        f"Future Random Forest SHAP Importance - H{horizon}"
    )

    axis.set_xlabel(
        "Mean absolute SHAP value"
    )

    axis.set_ylabel(
        "Feature"
    )

    figure.tight_layout()

    figure.savefig(
        FIGURE_DIR
        /
        f"28_future_rf_shap_global_bar_h{horizon}.png",

        dpi=300,

        bbox_inches="tight",
    )

    plt.close(
        figure
    )

    # --------------------------------------------------------
    # SHAP summary / beeswarm plot.
    # --------------------------------------------------------

    try:
        shap.summary_plot(
            shap_values,
            x_model,
            max_display=
                TOP_GLOBAL_FEATURES_PLOT,
            show=False,
        )

        current_figure = plt.gcf()

        current_figure.suptitle(
            f"Future Random Forest SHAP Summary - H{horizon}",
            y=1.02,
        )

        current_figure.tight_layout()

        current_figure.savefig(
            FIGURE_DIR
            /
            f"28_future_rf_shap_beeswarm_h{horizon}.png",

            dpi=300,

            bbox_inches="tight",
        )

        plt.close(
            current_figure
        )

    except Exception as plot_error:

        print(
            f"WARNING: H{horizon} SHAP summary plot "
            f"could not be created: {plot_error}"
        )

    print(
        f"H{horizon} SHAP rows generated: "
        f"{len(long_frame)}"
    )


# ============================================================
# 17. COMBINE SHAP OUTPUTS
# ============================================================

print_header(
    "COMBINE AND SAVE FUTURE EXPLAINABILITY OUTPUTS"
)

prediction_reproduction_df = pd.concat(
    [
        horizon_objects[
            horizon
        ][
            "reproduction_df"
        ]
        for horizon in HORIZONS
    ],
    ignore_index=True,
)

shap_long_df = pd.concat(
    shap_long_frames,
    ignore_index=True,
)

local_top_df = pd.concat(
    local_top_frames,
    ignore_index=True,
)

global_importance_df = pd.concat(
    global_importance_frames,
    ignore_index=True,
)

district_summary_df = pd.concat(
    district_summary_frames,
    ignore_index=True,
)

district_top10_df = pd.concat(
    district_top10_frames,
    ignore_index=True,
)

driver_wide_df = pd.concat(
    enriched_driver_frames,
    ignore_index=True,
)


# ============================================================
# 18. CREATE FINAL DASHBOARD/API-READY EXPLAINABLE FORECAST FILE
# ============================================================

enriched_future_df = (
    future_df
    .merge(
        driver_wide_df,
        on="Forecast_ID",
        how="left",
        validate="one_to_one",
    )
)

# Human-readable explanation using the top 3 local drivers.
def build_forecast_explanation(
    row
):
    parts = []

    for rank in [
        1,
        2,
        3,
    ]:

        feature = row.get(
            f"Top_Driver_{rank}_Feature"
        )

        shap_value = row.get(
            f"Top_Driver_{rank}_SHAP"
        )

        if (
            pd.isna(
                feature
            )
            or
            pd.isna(
                shap_value
            )
        ):
            continue

        if (
            float(
                shap_value
            )
            >
            0
        ):
            direction_text = (
                "increased"
            )

        elif (
            float(
                shap_value
            )
            <
            0
        ):
            direction_text = (
                "decreased"
            )

        else:
            direction_text = (
                "had little effect on"
            )

        if (
            direction_text
            ==
            "had little effect on"
        ):

            parts.append(
                f"{feature} {direction_text} the forecast"
            )

        else:

            parts.append(
                f"{feature} {direction_text} the forecast "
                f"by about {abs(float(shap_value)):.2f} cases"
            )

    if not parts:
        return (
            "No SHAP driver summary was available."
        )

    return (
        "; ".join(
            parts
        )
        +
        "."
    )


enriched_future_df[
    "SHAP_Explanation"
] = (
    enriched_future_df
    .apply(
        build_forecast_explanation,
        axis=1,
    )
)

# Reorder key dashboard columns near the front.
preferred_front_columns = [
    "Forecast_ID",
    "Point_Forecast_Model",
    "Uncertainty_Model",
    "Horizon_Months",
    DISTRICT_COL,
    ORIGIN_DATE_COL,
    TARGET_DATE_COL,
    "RF_Predicted_Cases",
    "NGBoost_Mean",
    "NGBoost_Lower_95",
    "NGBoost_Upper_95",
    "Uncertainty_Level",
    "Confidence_Label",
    "SHAP_Baseline",
    "Top_Driver_1_Feature",
    "Top_Driver_1_Feature_Value",
    "Top_Driver_1_SHAP",
    "Top_Driver_1_Direction",
    "Top_Driver_2_Feature",
    "Top_Driver_2_Feature_Value",
    "Top_Driver_2_SHAP",
    "Top_Driver_2_Direction",
    "Top_Driver_3_Feature",
    "Top_Driver_3_Feature_Value",
    "Top_Driver_3_SHAP",
    "Top_Driver_3_Direction",
    "SHAP_Explanation",
]

existing_front_columns = [
    column
    for column in preferred_front_columns
    if column in enriched_future_df.columns
]

remaining_columns = [
    column
    for column in enriched_future_df.columns
    if column not in existing_front_columns
]

enriched_future_df = (
    enriched_future_df[
        existing_front_columns
        +
        remaining_columns
    ]
)


# ============================================================
# 19. FINAL HARD AUDIT
# ============================================================

print_header(
    "FINAL STEP 28 HARD AUDIT"
)

if (
    len(
        enriched_future_df
    )
    !=
    EXPECTED_TOTAL_ROWS
):
    raise ValueError(
        "Enriched future output row count mismatch."
    )

if (
    enriched_future_df[
        "Forecast_ID"
    ]
    .nunique()
    !=
    EXPECTED_TOTAL_ROWS
):
    raise ValueError(
        "Forecast_ID is not unique in enriched output."
    )

if (
    enriched_future_df[
        "Top_Driver_1_Feature"
    ]
    .isna()
    .any()
):
    raise ValueError(
        "At least one future forecast is missing "
        "its top SHAP driver."
    )

expected_long_rows = int(
    sum(
        EXPECTED_FUTURE_ROWS[
            horizon
        ]
        *
        len(
            rf_bundles[
                horizon
            ][
                "model_columns"
            ]
        )
        for horizon in HORIZONS
    )
)

if (
    len(
        shap_long_df
    )
    !=
    expected_long_rows
):
    raise ValueError(
        f"Expected {expected_long_rows} long-form SHAP rows, "
        f"found {len(shap_long_df)}."
    )

expected_local_top_rows = (
    EXPECTED_TOTAL_ROWS
    *
    TOP_LOCAL_DRIVERS
)

if (
    len(
        local_top_df
    )
    !=
    expected_local_top_rows
):
    raise ValueError(
        f"Expected {expected_local_top_rows} local top-driver "
        f"rows, found {len(local_top_df)}."
    )

if not (
    pd.to_datetime(
        enriched_future_df[
            TARGET_DATE_COL
        ]
    )
    .between(
        FUTURE_TARGET_START,
        FUTURE_TARGET_END,
    )
    .all()
):
    raise ValueError(
        "Enriched output contains target dates "
        "outside 2026-2030."
    )

print(
    f"Total explainable forecasts       : "
    f"{len(enriched_future_df)} [PASS]"
)

print(
    f"Unique Forecast_ID values         : "
    f"{enriched_future_df['Forecast_ID'].nunique()} [PASS]"
)

print(
    f"Detailed SHAP feature rows        : "
    f"{len(shap_long_df)} [PASS]"
)

print(
    f"Top-{TOP_LOCAL_DRIVERS} local driver rows       : "
    f"{len(local_top_df)} [PASS]"
)

print(
    "Step 27 prediction reproduction  : PASS"
)

print(
    "SHAP additivity                  : PASS"
)

print(
    "2026-2030 target coverage        : PASS"
)

print(
    "Step 27B uncertainty preserved   : PASS"
)


# ============================================================
# 20. SAVE OUTPUTS
# ============================================================

prediction_reproduction_df.to_csv(
    PREDICTION_REPRODUCTION_PATH,
    index=False,
)

shap_long_df.to_csv(
    SHAP_LONG_PATH,
    index=False,
)

local_top_df.to_csv(
    LOCAL_TOP_DRIVERS_PATH,
    index=False,
)

global_importance_df.to_csv(
    GLOBAL_IMPORTANCE_PATH,
    index=False,
)

district_summary_df.to_csv(
    DISTRICT_SHAP_SUMMARY_PATH,
    index=False,
)

district_top10_df.to_csv(
    DISTRICT_TOP10_PATH,
    index=False,
)

enriched_future_df.to_csv(
    ENRICHED_FORECAST_PATH,
    index=False,
)

audit_df = pd.DataFrame(
    prediction_audit_records
    +
    shap_audit_records
)

audit_df.to_csv(
    AUDIT_PATH,
    index=False,
)


# ============================================================
# 21. METHODOLOGY RECORD
# ============================================================

methodology = {
    "step":
        "28",

    "purpose":
        (
            "Explain all 2026-2030 Random Forest future "
            "point forecasts using Tree SHAP while preserving "
            "the Step 27B NGBoost uncertainty outputs."
        ),

    "point_forecast_model":
        (
            "Frozen / saved Step 27 Random Forest models"
        ),

    "uncertainty_model":
        (
            "NGBoost output carried forward from Step 27B"
        ),

    "explainability_method":
        (
            "Tree SHAP"
        ),

    "explainability_target":
        (
            "Random Forest point forecast only"
        ),

    "future_period":
        (
            "2026-01 to 2030-12"
        ),

    "future_actual_targets_used":
        False,

    "future_feature_state":
        (
            "Reconstructed exactly from Step 27 projected "
            "predictors and Step 27 H1 recursive RF target state."
        ),

    "prediction_reproduction_required":
        True,

    "prediction_reproduction_tolerance":
        PREDICTION_TOLERANCE,

    "shap_additivity_required":
        True,

    "shap_additivity_tolerance":
        SHAP_ADDITIVITY_TOLERANCE,

    "local_driver_count":
        TOP_LOCAL_DRIVERS,

    "important_interpretation":
        (
            "Positive SHAP values push the Random Forest "
            "prediction above its baseline; negative SHAP "
            "values push it below the baseline. SHAP explains "
            "model behaviour and does not establish causality."
        ),

    "main_output":
        str(
            ENRICHED_FORECAST_PATH
        ),

    "detailed_outputs": {
        "prediction_reproduction":
            str(
                PREDICTION_REPRODUCTION_PATH
            ),

        "all_shap_values":
            str(
                SHAP_LONG_PATH
            ),

        "local_top_drivers":
            str(
                LOCAL_TOP_DRIVERS_PATH
            ),

        "global_feature_importance":
            str(
                GLOBAL_IMPORTANCE_PATH
            ),

        "district_shap_summary":
            str(
                DISTRICT_SHAP_SUMMARY_PATH
            ),

        "district_top10_drivers":
            str(
                DISTRICT_TOP10_PATH
            ),

        "audit":
            str(
                AUDIT_PATH
            ),
    },
}

with open(
    METHODOLOGY_PATH,
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
# 22. FINAL SUMMARY
# ============================================================

print_header(
    "STEP 28 COMPLETE"
)

print(
    "\nFuture explainability is now attached to the "
    "uncertainty-enriched forecasts."
)

print(
    "\nEach future forecast now contains:"
)

print(
    "- Random Forest predicted cases"
)

print(
    "- NGBoost 95% prediction range"
)

print(
    "- Uncertainty level / confidence label"
)

print(
    "- SHAP baseline"
)

print(
    "- Top 3 dashboard-ready SHAP drivers"
)

print(
    "- Human-readable SHAP explanation"
)

print(
    "\nSaved:"
)

print(
    f"- Main explainable future forecast:\n  "
    f"{ENRICHED_FORECAST_PATH}"
)

print(
    f"- Prediction reproduction audit data:\n  "
    f"{PREDICTION_REPRODUCTION_PATH}"
)

print(
    f"- Full SHAP values:\n  "
    f"{SHAP_LONG_PATH}"
)

print(
    f"- Local top drivers:\n  "
    f"{LOCAL_TOP_DRIVERS_PATH}"
)

print(
    f"- Global feature importance:\n  "
    f"{GLOBAL_IMPORTANCE_PATH}"
)

print(
    f"- District SHAP summary:\n  "
    f"{DISTRICT_SHAP_SUMMARY_PATH}"
)

print(
    f"- District top-10 drivers:\n  "
    f"{DISTRICT_TOP10_PATH}"
)

print(
    f"- Audit:\n  "
    f"{AUDIT_PATH}"
)

print(
    f"- Methodology:\n  "
    f"{METHODOLOGY_PATH}"
)

print(
    f"- Figures:\n  "
    f"{FIGURE_DIR}"
)

print(
    "\nNEXT AFTER THIS PASSES:"
)

print(
    "Use the Step 28 explainable future forecast as the "
    "input for future district risk prioritization, GIS map, "
    "resource-demand estimation and early-warning generation."
)

print(
    "\nSTEP 28 - FUTURE RANDOM FOREST SHAP EXPLAINABILITY "
    "2026-2030 COMPLETE"
)

print(
    "=" * 120
)
