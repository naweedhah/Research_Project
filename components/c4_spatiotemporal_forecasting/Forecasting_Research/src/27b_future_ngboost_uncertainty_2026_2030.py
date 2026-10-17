# ============================================================
# STEP 27B - FUTURE NGBOOST UNCERTAINTY (2026-2030)
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Add the validated NGBoost uncertainty layer to the already
# generated Step 27 Random Forest future forecasts.
#
# FINAL SYSTEM DESIGN
# -------------------
# Random Forest:
#   -> final point forecast for malnutrition cases
#
# NGBoost:
#   -> probabilistic predictive distribution
#   -> predicted standard deviation
#   -> 95% prediction interval
#   -> Low / Moderate / High uncertainty label
#
# IMPORTANT METHODOLOGY RULES
# ---------------------------
# 1. Step 27 Random Forest forecasts are NOT changed.
# 2. Step 21B NGBoost uncertainty configuration is reused.
# 3. NO tuning or model selection is done using 2026-2030.
# 4. NGBoost is retrained only on labels genuinely available
#    through 2025-12, after the 2025 lockbox evaluation is frozen.
# 5. Future predictor values are the SAME Step 27 projected
#    predictor values.
# 6. Future target-lag / rolling state is the SAME Step 27
#    H1 Random Forest recursive trajectory.
# 7. Low / Moderate / High uncertainty thresholds are the
#    SAME thresholds frozen from 2024 in Step 21B.
# 8. 2026-2030 actual outcomes are not available, so these
#    intervals are future uncertainty estimates, not observed
#    future coverage measurements.
#
# REQUIRED PREVIOUS OUTPUTS
# -------------------------
# Step 21B:
#   outputs/reports/21b_ngboost_2025_uncertainty_methodology.json
#   outputs/reports/21b_uncertainty_level_thresholds_from_2024.csv
#   outputs/reports/21b_ngboost_2025_uncertainty_metrics.csv
#
# Step 27:
#   outputs/reports/27_future_forecasts_2026_2030.csv
#   outputs/reports/27_future_predictor_projection.csv
#
# MAIN OUTPUT
# -----------
# outputs/reports/
#   27b_future_forecasts_with_ngboost_uncertainty_2026_2030.csv
#
# Example dashboard output:
#   RF Predicted Cases      : 145
#   NGBoost Predictive Mean : 148
#   NGBoost 95% Range       : 121 - 176
#   Uncertainty             : Moderate Uncertainty
#   Confidence              : Moderate Confidence
#
# NOTE:
# The NGBoost interval is a probabilistic NGBoost prediction
# interval. It must NOT be described as a formal Random Forest
# confidence interval.
# ============================================================

from pathlib import Path
import json
import warnings

import joblib
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

TARGET = "Malnutrition_Cases"
DISTRICT_COL = "District"
DATE_COL = "Date"

ORIGIN_DATE_COL = "Forecast_Origin_Date"
TARGET_DATE_COL = "Forecast_Target_Date"
MODEL_TARGET_COL = "Forecast_Target"

EXPECTED_ENGINEERED_FEATURES = 153
EXPECTED_DISTRICTS = 25

ACTUAL_CUTOFF = pd.Timestamp("2025-12-01")

FUTURE_TARGET_START = pd.Timestamp("2026-01-01")
FUTURE_TARGET_END = pd.Timestamp("2030-12-01")

ENGINE_ORIGIN_START = ACTUAL_CUTOFF
ENGINE_ORIGIN_END = FUTURE_TARGET_END - pd.DateOffset(months=1)

PREDICTOR_LAGS = [1, 3, 6, 12]
TARGET_LAGS = [1, 3, 6, 12]
ROLLING_WINDOWS = [3, 6, 12]

Z95 = float(
    norm.ppf(0.975)
)

EXPECTED_FUTURE_ROWS = {
    1: 1500,
    3: 1450,
    6: 1375,
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

MODEL_DIR.mkdir(
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

FEATURE_FILES = {
    1:
        PROCESSED_DIR
        / "malnutrition_features_h1.csv",

    3:
        PROCESSED_DIR
        / "malnutrition_features_h3.csv",

    6:
        PROCESSED_DIR
        / "malnutrition_features_h6.csv",
}

STEP21B_METHODOLOGY_PATH = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_methodology.json"
)

STEP21B_THRESHOLD_PATH = (
    REPORT_DIR
    / "21b_uncertainty_level_thresholds_from_2024.csv"
)

STEP21B_METRICS_PATH = (
    REPORT_DIR
    / "21b_ngboost_2025_uncertainty_metrics.csv"
)

STEP27_FORECAST_PATH = (
    REPORT_DIR
    / "27_future_forecasts_2026_2030.csv"
)

STEP27_PREDICTOR_PATH = (
    REPORT_DIR
    / "27_future_predictor_projection.csv"
)

FINAL_OUTPUT_PATH = (
    REPORT_DIR
    / "27b_future_forecasts_with_ngboost_uncertainty_2026_2030.csv"
)

SUMMARY_OUTPUT_PATH = (
    REPORT_DIR
    / "27b_future_ngboost_uncertainty_summary.csv"
)

AUDIT_OUTPUT_PATH = (
    REPORT_DIR
    / "27b_future_ngboost_uncertainty_audit.csv"
)

METHODOLOGY_OUTPUT_PATH = (
    REPORT_DIR
    / "27b_future_ngboost_uncertainty_methodology.json"
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


def determine_feature_columns(
    dataframe,
    horizon,
):
    excluded = {
        "Year",
        "Month",
        "Month_Name",
        DISTRICT_COL,
        DATE_COL,
        ORIGIN_DATE_COL,
        TARGET_DATE_COL,
        TARGET,
        "Horizon_Months",
        "Forecast_Horizon",
        "Forecast_Horizon_Months",
        MODEL_TARGET_COL,
    }

    feature_columns = [
        column
        for column in dataframe.columns
        if (
            column
            not in excluded
            and
            pd.api.types.is_numeric_dtype(
                dataframe[
                    column
                ]
            )
        )
    ]

    if (
        len(
            feature_columns
        )
        !=
        EXPECTED_ENGINEERED_FEATURES
    ):
        raise ValueError(
            f"H{horizon}: expected "
            f"{EXPECTED_ENGINEERED_FEATURES} "
            f"numeric engineered features, "
            f"found {len(feature_columns)}."
        )

    return feature_columns


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


# ============================================================
# 5. NGBOOST HELPERS
# ============================================================

def create_ngboost_model(
    params
):
    base_learner = (
        DecisionTreeRegressor(
            criterion="friedman_mse",

            max_depth=
                params[
                    "tree_depth"
                ],

            min_samples_leaf=
                params[
                    "min_samples_leaf"
                ],

            random_state=
                RANDOM_STATE,
        )
    )

    return NGBRegressor(
        Dist=Normal,
        Score=LogScore,
        Base=base_learner,
        natural_gradient=True,

        n_estimators=
            params[
                "n_estimators"
            ],

        learning_rate=
            params[
                "learning_rate"
            ],

        minibatch_frac=1.0,
        col_sample=1.0,
        verbose=False,
        random_state=RANDOM_STATE,
    )


# ============================================================
# 6. INTRODUCTION
# ============================================================

print_header(
    "STEP 27B - FUTURE NGBOOST UNCERTAINTY 2026-2030"
)

print(
    "\nSystem design:"
)

print(
    "- Random Forest remains the FINAL point-forecast model"
)

print(
    "- NGBoost is added as the probabilistic uncertainty layer"
)

print(
    "- Step 21B validated this uncertainty method on unseen 2025 data"
)

print(
    "- 2026-2030 forecasts themselves cannot yet be checked against actual outcomes"
)

print(
    "- No future actual values are used anywhere in this step"
)


# ============================================================
# 7. REQUIRED FILE CHECKS
# ============================================================

required_paths = [
    BASE_DATA_PATH,
    STEP21B_METHODOLOGY_PATH,
    STEP21B_THRESHOLD_PATH,
    STEP21B_METRICS_PATH,
    STEP27_FORECAST_PATH,
    STEP27_PREDICTOR_PATH,
]

required_paths.extend(
    FEATURE_FILES.values()
)

for required_path in (
    required_paths
):
    if not (
        required_path.exists()
    ):
        raise FileNotFoundError(
            f"Required file not found:\n"
            f"{required_path}"
        )


# ============================================================
# 8. LOAD STEP 21B FROZEN UNCERTAINTY DESIGN
# ============================================================

print_header(
    "LOAD VALIDATED STEP 21B UNCERTAINTY DESIGN"
)

with open(
    STEP21B_METHODOLOGY_PATH,
    "r",
    encoding="utf-8",
) as file:
    uncertainty_methodology = (
        json.load(
            file
        )
    )

if (
    "uncertainty_configs"
    not in uncertainty_methodology
):
    raise ValueError(
        "Step 21B methodology does not contain "
        "'uncertainty_configs'."
    )

uncertainty_configs = {}

for horizon in HORIZONS:

    key = (
        f"H{horizon}"
    )

    if (
        key
        not in uncertainty_methodology[
            "uncertainty_configs"
        ]
    ):
        raise ValueError(
            f"Step 21B methodology is missing "
            f"configuration {key}."
        )

    params = dict(
        uncertainty_methodology[
            "uncertainty_configs"
        ][
            key
        ]
    )

    required_param_keys = {
        "Config_ID",
        "n_estimators",
        "learning_rate",
        "tree_depth",
        "min_samples_leaf",
    }

    missing_params = (
        required_param_keys
        -
        set(
            params.keys()
        )
    )

    if missing_params:
        raise ValueError(
            f"H{horizon}: Step 21B uncertainty "
            f"configuration is missing "
            f"{sorted(missing_params)}."
        )

    uncertainty_configs[
        horizon
    ] = params

    print(
        f"H{horizon} uncertainty config: "
        f"{params['Config_ID']}"
    )


# ============================================================
# 9. LOAD 2024 UNCERTAINTY-LEVEL THRESHOLDS
# ============================================================

threshold_df = pd.read_csv(
    STEP21B_THRESHOLD_PATH
)

required_threshold_columns = {
    "Horizon_Months",
    "Low_to_Moderate_RelativeWidth_Threshold",
    "Moderate_to_High_RelativeWidth_Threshold",
}

missing_threshold_columns = (
    required_threshold_columns
    -
    set(
        threshold_df.columns
    )
)

if missing_threshold_columns:
    raise ValueError(
        "Step 21B threshold file is missing columns: "
        f"{sorted(missing_threshold_columns)}"
    )

uncertainty_thresholds = {}

for horizon in HORIZONS:

    row = (
        threshold_df[
            threshold_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
    )

    if (
        len(
            row
        )
        !=
        1
    ):
        raise ValueError(
            f"H{horizon}: expected exactly one "
            "uncertainty-threshold row."
        )

    uncertainty_thresholds[
        horizon
    ] = {
        "q33":
            float(
                row.iloc[0][
                    "Low_to_Moderate_RelativeWidth_Threshold"
                ]
            ),

        "q67":
            float(
                row.iloc[0][
                    "Moderate_to_High_RelativeWidth_Threshold"
                ]
            ),
    }

    print(
        f"H{horizon} thresholds | "
        f"q33={uncertainty_thresholds[horizon]['q33']:.4f} "
        f"| q67={uncertainty_thresholds[horizon]['q67']:.4f}"
    )


# ============================================================
# 10. LOAD 2025 FINAL UNCERTAINTY EVIDENCE
# ============================================================

metrics_2025_df = pd.read_csv(
    STEP21B_METRICS_PATH
)

required_metric_columns = {
    "Horizon_Months",
    "Nominal_Coverage_Percentage",
    "Observed_Coverage_Percentage",
}

missing_metric_columns = (
    required_metric_columns
    -
    set(
        metrics_2025_df.columns
    )
)

if missing_metric_columns:
    raise ValueError(
        "Step 21B metrics file is missing columns: "
        f"{sorted(missing_metric_columns)}"
    )

coverage_2025 = {}

for horizon in HORIZONS:

    row = (
        metrics_2025_df[
            metrics_2025_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
    )

    if len(
        row
    ) != 1:
        raise ValueError(
            f"H{horizon}: expected one Step 21B "
            "final uncertainty metric row."
        )

    coverage_2025[
        horizon
    ] = float(
        row.iloc[0][
            "Observed_Coverage_Percentage"
        ]
    )

    print(
        f"H{horizon} unseen-2025 observed coverage: "
        f"{coverage_2025[horizon]:.4f}%"
    )


# ============================================================
# 11. LOAD AND VALIDATE BASE DATA
# ============================================================

print_header(
    "LOAD OBSERVED DATA THROUGH 2025-12"
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
        "Base data is missing required columns: "
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
        "Base data contains invalid Date values."
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

duplicate_count = int(
    base_df
    .duplicated(
        [
            DISTRICT_COL,
            DATE_COL,
        ]
    )
    .sum()
)

if (
    duplicate_count
    !=
    0
):
    raise ValueError(
        f"Duplicate District-Date rows found: "
        f"{duplicate_count}"
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
        f"Observed data must end at "
        f"{ACTUAL_CUTOFF.date()}, "
        f"found {observed_max_date.date()}."
    )

monthly_predictors = (
    identify_monthly_predictor_columns(
        base_df
    )
)

print(
    f"Observed data used : "
    f"{minimum_date.date()} to "
    f"{ACTUAL_CUTOFF.date()}"
)

print(
    f"Districts          : "
    f"{len(districts)}"
)

print(
    f"Monthly predictors : "
    f"{len(monthly_predictors)}"
)

if (
    len(
        monthly_predictors
    )
    !=
    35
):
    print(
        "WARNING: Step 27 previously identified "
        "35 monthly predictors, but this file "
        f"currently contains {len(monthly_predictors)}."
    )


# ============================================================
# 12. LOAD STEP 27 FUTURE RF FORECASTS
# ============================================================

print_header(
    "LOAD STEP 27 RANDOM FOREST FUTURE FORECASTS"
)

rf_future_df = pd.read_csv(
    STEP27_FORECAST_PATH
)

required_rf_columns = {
    "Model",
    "Config_ID",
    "Horizon_Months",
    DISTRICT_COL,
    ORIGIN_DATE_COL,
    TARGET_DATE_COL,
    "Predicted_Cases",
}

missing_rf_columns = (
    required_rf_columns
    -
    set(
        rf_future_df.columns
    )
)

if missing_rf_columns:
    raise ValueError(
        "Step 27 forecast file is missing columns: "
        f"{sorted(missing_rf_columns)}"
    )

rf_future_df[
    ORIGIN_DATE_COL
] = pd.to_datetime(
    rf_future_df[
        ORIGIN_DATE_COL
    ],
    errors="coerce",
)

rf_future_df[
    TARGET_DATE_COL
] = pd.to_datetime(
    rf_future_df[
        TARGET_DATE_COL
    ],
    errors="coerce",
)

if (
    rf_future_df[
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
        "Step 27 forecast file contains "
        "invalid forecast dates."
    )

if not (
    rf_future_df[
        TARGET_DATE_COL
    ]
    .between(
        FUTURE_TARGET_START,
        FUTURE_TARGET_END,
    )
    .all()
):
    raise ValueError(
        "Step 27 forecast output contains targets "
        "outside 2026-01 to 2030-12."
    )

for horizon, expected_rows in (
    EXPECTED_FUTURE_ROWS.items()
):
    actual_rows = int(
        (
            rf_future_df[
                "Horizon_Months"
            ]
            ==
            horizon
        )
        .sum()
    )

    if (
        actual_rows
        !=
        expected_rows
    ):
        raise ValueError(
            f"H{horizon}: expected {expected_rows} "
            f"Step 27 rows, found {actual_rows}."
        )

print(
    f"Step 27 future rows: "
    f"{len(rf_future_df)}"
)

print(
    "H1/H3/H6 row counts: PASS"
)


# ============================================================
# 13. LOAD STEP 27 FUTURE PREDICTOR PROJECTION
# ============================================================

print_header(
    "LOAD STEP 27 FUTURE PREDICTOR PROJECTION"
)

future_predictor_df = pd.read_csv(
    STEP27_PREDICTOR_PATH
)

required_predictor_columns = {
    DISTRICT_COL,
    DATE_COL,
}

missing_predictor_columns = (
    required_predictor_columns
    -
    set(
        future_predictor_df.columns
    )
)

if missing_predictor_columns:
    raise ValueError(
        "Step 27 predictor projection is missing columns: "
        f"{sorted(missing_predictor_columns)}"
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
        "Future predictor projection contains invalid dates."
    )

expected_future_predictor_rows = (
    60
    *
    EXPECTED_DISTRICTS
)

if (
    len(
        future_predictor_df
    )
    !=
    expected_future_predictor_rows
):
    raise ValueError(
        f"Expected {expected_future_predictor_rows} "
        "future predictor rows, found "
        f"{len(future_predictor_df)}."
    )

missing_projected_predictors = [
    column
    for column in monthly_predictors
    if column not in future_predictor_df.columns
]

if missing_projected_predictors:
    raise ValueError(
        "Future predictor projection is missing "
        f"{len(missing_projected_predictors)} "
        "required predictors. Examples: "
        f"{missing_projected_predictors[:10]}"
    )

print(
    f"Future predictor rows: "
    f"{len(future_predictor_df)}"
)


# ============================================================
# 14. BUILD EXACT STEP 27 PREDICTOR LOOKUP
# ============================================================

print_header(
    "RECONSTRUCT STEP 27 FUTURE FEATURE STATE"
)

predictor_lookup = {}

# Actual observed predictor state.
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

    for predictor in (
        monthly_predictors
    ):
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


# Future projected predictor state from Step 27.
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

    for predictor in (
        monthly_predictors
    ):
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
# 15. BUILD EXACT STEP 27 TARGET STATE
# ============================================================

# Actual history first.
target_state = {}

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


# Step 27 rule:
# ONLY H1 RF predictions advance the recursive future
# Malnutrition_Cases state.
h1_rf_df = (
    rf_future_df[
        rf_future_df[
            "Horizon_Months"
        ]
        ==
        1
    ]
    .copy()
)

if (
    len(
        h1_rf_df
    )
    !=
    EXPECTED_FUTURE_ROWS[
        1
    ]
):
    raise ValueError(
        "Step 27 H1 future-state rows are incomplete."
    )

for _, row in (
    h1_rf_df
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
            "Predicted_Cases"
        ]
    )

print(
    "Observed target history loaded through 2025-12."
)

print(
    "Step 27 H1 RF predictions loaded as the "
    "future recursive target state through 2030-12."
)


# ============================================================
# 16. FEATURE-BUILDING FUNCTIONS
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

    # --------------------------------------------------------
    # Known calendar features.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Historical target lags.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Historical target rolling features.
    # Exactly matches Step 27 / corrected Step 07:
    # shift(1).rolling(window).
    # --------------------------------------------------------

    for window in (
        ROLLING_WINDOWS
    ):

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
                    date
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
                if len(
                    values
                )
                >
                1
                else np.nan
            )

        row[
            f"Malnutrition_Rolling_Mean_{window}"
        ] = rolling_mean

        row[
            f"Malnutrition_Rolling_STD_{window}"
        ] = rolling_std

    # --------------------------------------------------------
    # Historical predictor lags.
    # --------------------------------------------------------

    for predictor in (
        monthly_predictors
    ):

        for lag in (
            PREDICTOR_LAGS
        ):

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
# 17. FIT DEPLOYMENT NGBOOST MODELS ON ALL AVAILABLE LABELS
# ============================================================

print_header(
    "RETRAIN VALIDATED NGBOOST UNCERTAINTY MODELS THROUGH 2025-12"
)

model_bundle = {}

training_audit_records = []

for horizon in HORIZONS:

    feature_path = (
        FEATURE_FILES[
            horizon
        ]
    )

    dataframe = pd.read_csv(
        feature_path
    )

    required_feature_columns = {
        DISTRICT_COL,
        ORIGIN_DATE_COL,
        TARGET_DATE_COL,
        MODEL_TARGET_COL,
    }

    missing_feature_columns = (
        required_feature_columns
        -
        set(
            dataframe.columns
        )
    )

    if missing_feature_columns:
        raise ValueError(
            f"H{horizon}: feature file is missing "
            f"{sorted(missing_feature_columns)}"
        )

    dataframe[
        ORIGIN_DATE_COL
    ] = pd.to_datetime(
        dataframe[
            ORIGIN_DATE_COL
        ],
        errors="coerce",
    )

    dataframe[
        TARGET_DATE_COL
    ] = pd.to_datetime(
        dataframe[
            TARGET_DATE_COL
        ],
        errors="coerce",
    )

    feature_columns = (
        determine_feature_columns(
            dataframe,
            horizon,
        )
    )

    # After the final 2025 lockbox evaluation has been frozen,
    # all labels genuinely known through 2025-12 can be used
    # for deployment retraining.
    train_df = (
        dataframe[
            dataframe[
                MODEL_TARGET_COL
            ]
            .notna()
            &
            (
                dataframe[
                    TARGET_DATE_COL
                ]
                <=
                ACTUAL_CUTOFF
            )
        ]
        .copy()
    )

    if (
        train_df.empty
    ):
        raise ValueError(
            f"H{horizon}: no deployment training "
            "rows were found."
        )

    medians = (
        train_df[
            feature_columns
        ]
        .median(
            numeric_only=True
        )
        .fillna(
            0.0
        )
    )

    x_train_numeric = (
        train_df[
            feature_columns
        ]
        .copy()
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

    district_categories = sorted(
        train_df[
            DISTRICT_COL
        ]
        .astype(str)
        .dropna()
        .unique()
        .tolist()
    )

    if (
        district_categories
        !=
        districts
    ):
        raise ValueError(
            f"H{horizon}: deployment-training district "
            "set does not match base-data district set."
        )

    train_categories = pd.Categorical(
        train_df[
            DISTRICT_COL
        ]
        .astype(str),

        categories=
            district_categories,
    )

    x_train_dummies = (
        pd.get_dummies(
            train_categories,
            prefix="District",
            dtype=float,
        )
        .reset_index(
            drop=True
        )
    )

    x_train = pd.concat(
        [
            x_train_numeric,
            x_train_dummies,
        ],
        axis=1,
    )

    y_train = (
        train_df[
            MODEL_TARGET_COL
        ]
        .astype(float)
        .to_numpy()
    )

    params = (
        uncertainty_configs[
            horizon
        ]
    )

    model = (
        create_ngboost_model(
            params
        )
    )

    model.fit(
        x_train,
        y_train,
    )

    model_path = (
        MODEL_DIR
        /
        f"27b_final_future_ngboost_h{horizon}.joblib"
    )

    model_payload = {
        "model":
            model,

        "horizon":
            horizon,

        "config_id":
            params[
                "Config_ID"
            ],

        "feature_columns":
            feature_columns,

        "model_columns":
            x_train.columns.tolist(),

        "feature_medians":
            medians.to_dict(),

        "district_categories":
            district_categories,

        "actual_cutoff":
            str(
                ACTUAL_CUTOFF.date()
            ),

        "nominal_interval_percentage":
            95.0,

        "validated_2025_observed_coverage_percentage":
            coverage_2025[
                horizon
            ],

        "uncertainty_threshold_q33":
            uncertainty_thresholds[
                horizon
            ][
                "q33"
            ],

        "uncertainty_threshold_q67":
            uncertainty_thresholds[
                horizon
            ][
                "q67"
            ],
    }

    joblib.dump(
        model_payload,
        model_path,
    )

    model_bundle[
        horizon
    ] = {
        "model":
            model,

        "params":
            params,

        "feature_columns":
            feature_columns,

        "model_columns":
            x_train.columns.tolist(),

        "medians":
            medians,

        "district_categories":
            district_categories,

        "model_path":
            model_path,
    }

    training_audit_records.append({
        "Audit_Type":
            "DEPLOYMENT_TRAINING",

        "Horizon_Months":
            horizon,

        "Config_ID":
            params[
                "Config_ID"
            ],

        "Training_Rows":
            len(
                train_df
            ),

        "First_Training_Origin":
            train_df[
                ORIGIN_DATE_COL
            ]
            .min(),

        "Last_Training_Origin":
            train_df[
                ORIGIN_DATE_COL
            ]
            .max(),

        "First_Training_Target":
            train_df[
                TARGET_DATE_COL
            ]
            .min(),

        "Last_Training_Target":
            train_df[
                TARGET_DATE_COL
            ]
            .max(),

        "Engineered_Feature_Count":
            len(
                feature_columns
            ),

        "Final_Model_Feature_Count":
            len(
                x_train.columns
            ),

        "Model_Path":
            str(
                model_path
            ),
    })

    print(
        f"H{horizon} | "
        f"{params['Config_ID']} "
        f"| train={len(train_df)} "
        f"| features={len(feature_columns)} "
        f"| model saved"
    )


# ============================================================
# 18. FUTURE MATRIX TRANSFORM
# ============================================================

def transform_future_rows(
    future_rows,
    horizon,
):
    bundle = (
        model_bundle[
            horizon
        ]
    )

    feature_columns = (
        bundle[
            "feature_columns"
        ]
    )

    medians = (
        bundle[
            "medians"
        ]
    )

    district_categories = (
        bundle[
            "district_categories"
        ]
    )

    model_columns = (
        bundle[
            "model_columns"
        ]
    )

    missing_generated_features = [
        column
        for column in feature_columns
        if column not in future_rows.columns
    ]

    if (
        missing_generated_features
    ):
        raise ValueError(
            f"H{horizon}: future feature generation is "
            f"missing {len(missing_generated_features)} "
            "required features.\n"
            f"Examples: "
            f"{missing_generated_features[:10]}"
        )

    x_numeric = (
        future_rows[
            feature_columns
        ]
        .copy()
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

    future_categories = pd.Categorical(
        future_rows[
            DISTRICT_COL
        ]
        .astype(str),

        categories=
            district_categories,
    )

    x_dummies = (
        pd.get_dummies(
            future_categories,
            prefix="District",
            dtype=float,
        )
        .reset_index(
            drop=True
        )
    )

    x_prediction = pd.concat(
        [
            x_numeric,
            x_dummies,
        ],
        axis=1,
    )

    x_prediction = (
        x_prediction
        .reindex(
            columns=model_columns,
            fill_value=0.0,
        )
    )

    return x_prediction


# ============================================================
# 19. GENERATE FUTURE NGBOOST UNCERTAINTY
# ============================================================

print_header(
    "GENERATE 2026-2030 NGBOOST UNCERTAINTY"
)

future_uncertainty_records = []

origin_audit_records = []

origin_dates = pd.date_range(
    start=ENGINE_ORIGIN_START,
    end=ENGINE_ORIGIN_END,
    freq="MS",
)

for origin_number, origin_date in enumerate(
    origin_dates,
    start=1,
):

    future_feature_records = []

    for district in (
        districts
    ):

        feature_values = (
            build_future_feature_row(
                district,
                origin_date,
            )
        )

        feature_values[
            DISTRICT_COL
        ] = district

        feature_values[
            ORIGIN_DATE_COL
        ] = origin_date

        future_feature_records.append(
            feature_values
        )

    future_rows = pd.DataFrame(
        future_feature_records
    )

    if (
        len(
            future_rows
        )
        !=
        EXPECTED_DISTRICTS
    ):
        raise ValueError(
            f"{origin_date.date()}: expected "
            f"{EXPECTED_DISTRICTS} district rows, "
            f"found {len(future_rows)}."
        )

    generated_horizons = []

    for horizon in HORIZONS:

        target_date = (
            origin_date
            +
            pd.DateOffset(
                months=horizon
            )
        )

        if (
            target_date
            <
            FUTURE_TARGET_START
            or
            target_date
            >
            FUTURE_TARGET_END
        ):
            continue

        x_prediction = (
            transform_future_rows(
                future_rows,
                horizon,
            )
        )

        model = (
            model_bundle[
                horizon
            ][
                "model"
            ]
        )

        predictive_distribution = (
            model.pred_dist(
                x_prediction
            )
        )

        ngboost_mean = np.asarray(
            predictive_distribution
            .params[
                "loc"
            ],
            dtype=float,
        )

        ngboost_sd = np.asarray(
            predictive_distribution
            .params[
                "scale"
            ],
            dtype=float,
        )

        ngboost_sd = np.maximum(
            ngboost_sd,
            1e-8,
        )

        raw_lower_95 = (
            ngboost_mean
            -
            Z95
            *
            ngboost_sd
        )

        upper_95 = (
            ngboost_mean
            +
            Z95
            *
            ngboost_sd
        )

        # Counts cannot be negative.
        lower_95 = np.maximum(
            raw_lower_95,
            0.0,
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
                    ngboost_mean
                ),
                1.0,
            )
        )

        q33 = (
            uncertainty_thresholds[
                horizon
            ][
                "q33"
            ]
        )

        q67 = (
            uncertainty_thresholds[
                horizon
            ][
                "q67"
            ]
        )

        rf_slice = (
            rf_future_df[
                (
                    rf_future_df[
                        "Horizon_Months"
                    ]
                    ==
                    horizon
                )
                &
                (
                    rf_future_df[
                        ORIGIN_DATE_COL
                    ]
                    ==
                    origin_date
                )
                &
                (
                    rf_future_df[
                        TARGET_DATE_COL
                    ]
                    ==
                    target_date
                )
            ]
            .copy()
        )

        rf_lookup = dict(
            zip(
                rf_slice[
                    DISTRICT_COL
                ]
                .astype(str),

                rf_slice[
                    "Predicted_Cases"
                ]
                .astype(float),
            )
        )

        if (
            len(
                rf_lookup
            )
            !=
            EXPECTED_DISTRICTS
        ):
            raise ValueError(
                f"H{horizon} origin "
                f"{origin_date.date()}: "
                "could not match all 25 Step 27 "
                "Random Forest predictions."
            )

        generated_horizons.append(
            horizon
        )

        for row_position, district in enumerate(
            districts
        ):

            relative_width_value = float(
                relative_interval_width[
                    row_position
                ]
            )

            if (
                relative_width_value
                <=
                q33
            ):

                uncertainty_level = (
                    "Low Uncertainty"
                )

                confidence_label = (
                    "Higher Confidence"
                )

            elif (
                relative_width_value
                <=
                q67
            ):

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

            rf_prediction = float(
                rf_lookup[
                    district
                ]
            )

            ngb_mean_value = float(
                ngboost_mean[
                    row_position
                ]
            )

            lower_value = float(
                lower_95[
                    row_position
                ]
            )

            upper_value = float(
                upper_95[
                    row_position
                ]
            )

            rf_inside_ngboost_interval = bool(
                rf_prediction
                >=
                lower_value
                and
                rf_prediction
                <=
                upper_value
            )

            future_uncertainty_records.append({
                "Point_Forecast_Model":
                    "Random Forest",

                "Uncertainty_Model":
                    "NGBoost",

                "RF_Config_ID":
                    str(
                        rf_slice[
                            "Config_ID"
                        ]
                        .iloc[0]
                    ),

                "NGBoost_Config_ID":
                    uncertainty_configs[
                        horizon
                    ][
                        "Config_ID"
                    ],

                "Horizon_Months":
                    horizon,

                DISTRICT_COL:
                    district,

                ORIGIN_DATE_COL:
                    origin_date,

                TARGET_DATE_COL:
                    target_date,

                "Origin_Year":
                    int(
                        origin_date.year
                    ),

                "Origin_Month":
                    int(
                        origin_date.month
                    ),

                "Target_Year":
                    int(
                        target_date.year
                    ),

                "Target_Month":
                    int(
                        target_date.month
                    ),

                # Main system forecast.
                "RF_Predicted_Cases":
                    rf_prediction,

                # NGBoost probabilistic uncertainty output.
                "NGBoost_Mean":
                    ngb_mean_value,

                "NGBoost_Predicted_SD":
                    float(
                        ngboost_sd[
                            row_position
                        ]
                    ),

                "NGBoost_Lower_95":
                    lower_value,

                "NGBoost_Upper_95":
                    upper_value,

                "NGBoost_Raw_Lower_95":
                    float(
                        raw_lower_95[
                            row_position
                        ]
                    ),

                "NGBoost_Interval_Width":
                    float(
                        interval_width[
                            row_position
                        ]
                    ),

                "NGBoost_Relative_Interval_Width":
                    relative_width_value,

                "Uncertainty_Level":
                    uncertainty_level,

                "Confidence_Label":
                    confidence_label,

                "RF_Point_Inside_NGBoost_95":
                    rf_inside_ngboost_interval,

                "Nominal_Interval_Percentage":
                    95.0,

                "Validated_2025_Observed_Coverage_Percentage":
                    coverage_2025[
                        horizon
                    ],

                "Forecast_Mode":
                    "RECURSIVE_FUTURE_PROJECTION",

                "Predictor_Projection_Method":
                    (
                        "SEASONAL_NAIVE_12_MONTH"
                    ),

                "Target_State_Method":
                    (
                        "STEP27_H1_RANDOM_FOREST_RECURSION"
                    ),

                "Origin_State_Type":
                    (
                        "LAST_ACTUAL_ORIGIN"
                        if
                        origin_date
                        ==
                        ACTUAL_CUTOFF
                        else
                        "SIMULATED_FUTURE_ORIGIN"
                    ),

                "Months_Beyond_Last_Actual_Target":
                    int(
                        month_distance(
                            ACTUAL_CUTOFF,
                            target_date,
                        )
                    ),
            })

    origin_audit_records.append({
        "Audit_Type":
            "FUTURE_ORIGIN",

        "Forecast_Origin_Date":
            origin_date,

        "Origin_Number":
            origin_number,

        "District_Rows":
            len(
                future_rows
            ),

        "Generated_Horizons":
            ",".join(
                [
                    f"H{h}"
                    for h in generated_horizons
                ]
            ),

        "Feature_State_Source":
            (
                "STEP27_RF_H1_TARGET_STATE"
            ),

        "Predictor_State_Source":
            (
                "STEP27_FUTURE_PREDICTOR_PROJECTION"
            ),
    })

    h_text = (
        ", ".join(
            [
                f"H{h}"
                for h in generated_horizons
            ]
        )
    )

    print(
        f"Origin {origin_number:02d}/"
        f"{len(origin_dates)} "
        f"| {origin_date.date()} "
        f"| generated: {h_text}"
    )


# ============================================================
# 20. CREATE FINAL OUTPUT
# ============================================================

future_uncertainty_df = pd.DataFrame(
    future_uncertainty_records
)

if (
    future_uncertainty_df.empty
):
    raise RuntimeError(
        "No future NGBoost uncertainty "
        "predictions were generated."
    )

future_uncertainty_df = (
    future_uncertainty_df
    .sort_values(
        [
            ORIGIN_DATE_COL,
            "Horizon_Months",
            DISTRICT_COL,
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 21. HARD AUDIT
# ============================================================

print_header(
    "FINAL 27B HARD AUDIT"
)

expected_total_rows = int(
    sum(
        EXPECTED_FUTURE_ROWS.values()
    )
)

if (
    len(
        future_uncertainty_df
    )
    !=
    expected_total_rows
):
    raise ValueError(
        f"Expected {expected_total_rows} total rows, "
        f"found {len(future_uncertainty_df)}."
    )

# Exact origin + horizon mapping check.
expected_target_dates = (
    pd.to_datetime(
        future_uncertainty_df[
            ORIGIN_DATE_COL
        ]
    )
    +
    future_uncertainty_df[
        "Horizon_Months"
    ]
    .apply(
        lambda horizon:
            pd.DateOffset(
                months=int(
                    horizon
                )
            )
    )
)

mapping_mismatches = int(
    (
        pd.to_datetime(
            future_uncertainty_df[
                TARGET_DATE_COL
            ]
        )
        !=
        expected_target_dates
    )
    .sum()
)

if (
    mapping_mismatches
    !=
    0
):
    raise ValueError(
        f"Origin-target mapping mismatches: "
        f"{mapping_mismatches}"
    )

# Range validity.
invalid_intervals = int(
    (
        future_uncertainty_df[
            "NGBoost_Lower_95"
        ]
        >
        future_uncertainty_df[
            "NGBoost_Upper_95"
        ]
    )
    .sum()
)

if (
    invalid_intervals
    !=
    0
):
    raise ValueError(
        f"Invalid NGBoost intervals found: "
        f"{invalid_intervals}"
    )

# Saved lower bound must be non-negative.
negative_saved_lower = int(
    (
        future_uncertainty_df[
            "NGBoost_Lower_95"
        ]
        <
        0
    )
    .sum()
)

if (
    negative_saved_lower
    !=
    0
):
    raise ValueError(
        "Negative saved lower bounds remain "
        f"after clipping: {negative_saved_lower}"
    )

# District coverage per origin/horizon.
coverage_counts = (
    future_uncertainty_df
    .groupby(
        [
            ORIGIN_DATE_COL,
            "Horizon_Months",
        ]
    )[
        DISTRICT_COL
    ]
    .nunique()
)

bad_district_coverage = (
    coverage_counts[
        coverage_counts
        !=
        EXPECTED_DISTRICTS
    ]
)

if (
    len(
        bad_district_coverage
    )
    !=
    0
):
    raise ValueError(
        "Some future origin/horizon combinations "
        "do not contain all 25 districts."
    )

for horizon, expected_rows in (
    EXPECTED_FUTURE_ROWS.items()
):

    actual_rows = int(
        (
            future_uncertainty_df[
                "Horizon_Months"
            ]
            ==
            horizon
        )
        .sum()
    )

    if (
        actual_rows
        !=
        expected_rows
    ):
        raise ValueError(
            f"H{horizon}: expected {expected_rows} "
            f"rows, found {actual_rows}."
        )

print(
    f"Total future rows                 : "
    f"{len(future_uncertainty_df)} [PASS]"
)

print(
    f"Origin-target mapping mismatches : "
    f"{mapping_mismatches} [PASS]"
)

print(
    "25 districts per origin/horizon  : PASS"
)

print(
    "Prediction interval validity     : PASS"
)

print(
    "Negative saved lower bounds      : 0 [PASS]"
)


# ============================================================
# 22. SUMMARY
# ============================================================

summary_records = []

for horizon in HORIZONS:

    horizon_df = (
        future_uncertainty_df[
            future_uncertainty_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
        .copy()
    )

    summary_records.append({
        "Horizon_Months":
            horizon,

        "Rows":
            len(
                horizon_df
            ),

        "Origins":
            horizon_df[
                ORIGIN_DATE_COL
            ]
            .nunique(),

        "Districts":
            horizon_df[
                DISTRICT_COL
            ]
            .nunique(),

        "First_Target":
            horizon_df[
                TARGET_DATE_COL
            ]
            .min(),

        "Last_Target":
            horizon_df[
                TARGET_DATE_COL
            ]
            .max(),

        "Mean_RF_Predicted_Cases":
            float(
                horizon_df[
                    "RF_Predicted_Cases"
                ]
                .mean()
            ),

        "Mean_NGBoost_Mean":
            float(
                horizon_df[
                    "NGBoost_Mean"
                ]
                .mean()
            ),

        "Mean_95_Interval_Width":
            float(
                horizon_df[
                    "NGBoost_Interval_Width"
                ]
                .mean()
            ),

        "Median_95_Interval_Width":
            float(
                horizon_df[
                    "NGBoost_Interval_Width"
                ]
                .median()
            ),

        "Mean_Relative_Interval_Width":
            float(
                horizon_df[
                    "NGBoost_Relative_Interval_Width"
                ]
                .mean()
            ),

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

        "RF_Inside_NGBoost_95_Percentage":
            float(
                horizon_df[
                    "RF_Point_Inside_NGBoost_95"
                ]
                .mean()
                *
                100.0
            ),

        "Validated_2025_Observed_Coverage_Percentage":
            coverage_2025[
                horizon
            ],
    })


summary_df = pd.DataFrame(
    summary_records
)

print(
    "\nFuture uncertainty summary:"
)

print(
    summary_df
    .round(
        4
    )
    .to_string(
        index=False
    )
)


# ============================================================
# 23. SAVE OUTPUTS
# ============================================================

future_uncertainty_df.to_csv(
    FINAL_OUTPUT_PATH,
    index=False,
)

summary_df.to_csv(
    SUMMARY_OUTPUT_PATH,
    index=False,
)

training_audit_df = pd.DataFrame(
    training_audit_records
)

origin_audit_df = pd.DataFrame(
    origin_audit_records
)

combined_audit_df = pd.concat(
    [
        training_audit_df,
        origin_audit_df,
    ],
    ignore_index=True,
    sort=False,
)

combined_audit_df.to_csv(
    AUDIT_OUTPUT_PATH,
    index=False,
)


# ============================================================
# 24. METHODOLOGY RECORD
# ============================================================

methodology = {
    "step":
        "27B",

    "purpose":
        (
            "Add validated NGBoost probabilistic uncertainty "
            "to Step 27 Random Forest future forecasts."
        ),

    "future_target_period":
        (
            "2026-01 to 2030-12"
        ),

    "point_forecast_model":
        (
            "Random Forest from Step 27"
        ),

    "uncertainty_model":
        (
            "NGBoost Normal predictive distribution"
        ),

    "nominal_prediction_interval_percentage":
        95.0,

    "uncertainty_configs":
        {
            f"H{horizon}":
                uncertainty_configs[
                    horizon
                ]
            for horizon in HORIZONS
        },

    "uncertainty_level_threshold_source":
        (
            "Frozen 2024 relative interval-width thresholds "
            "created in Step 21B."
        ),

    "validated_2025_observed_coverage_percentage":
        {
            f"H{horizon}":
                coverage_2025[
                    horizon
                ]
            for horizon in HORIZONS
        },

    "deployment_training_rule":
        (
            "After final evaluation was frozen, NGBoost was "
            "retrained on all labels whose target date was "
            "available through 2025-12."
        ),

    "future_predictor_state":
        (
            "Exactly reuses Step 27 future predictor projection."
        ),

    "future_target_state":
        (
            "Exactly reuses Step 27 H1 Random Forest recursive "
            "future Malnutrition_Cases state."
        ),

    "important_interpretation":
        (
            "The NGBoost 95% interval is a probabilistic NGBoost "
            "prediction interval. It is not a formal Random Forest "
            "confidence interval and it does not guarantee that "
            "95% of 2026-2030 future observations will fall inside "
            "the interval."
        ),

    "future_validation_limitation":
        (
            "Actual 2026-2030 outcomes are not yet available. "
            "Therefore future observed interval coverage cannot "
            "be calculated now. Step 21B unseen-2025 coverage is "
            "retained as the latest empirical calibration evidence."
        ),

    "main_output":
        str(
            FINAL_OUTPUT_PATH
        ),
}

with open(
    METHODOLOGY_OUTPUT_PATH,
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
# 25. FIGURES
# ============================================================

# ------------------------------------------------------------
# Figure 1:
# Mean future RF prediction with mean NGBoost uncertainty band.
# ------------------------------------------------------------

for horizon in HORIZONS:

    horizon_df = (
        future_uncertainty_df[
            future_uncertainty_df[
                "Horizon_Months"
            ]
            ==
            horizon
        ]
        .copy()
    )

    monthly_df = (
        horizon_df
        .groupby(
            TARGET_DATE_COL,
            as_index=False,
        )
        .agg(
            Mean_RF_Predicted_Cases=(
                "RF_Predicted_Cases",
                "mean",
            ),

            Mean_NGBoost_Mean=(
                "NGBoost_Mean",
                "mean",
            ),

            Mean_NGBoost_Lower_95=(
                "NGBoost_Lower_95",
                "mean",
            ),

            Mean_NGBoost_Upper_95=(
                "NGBoost_Upper_95",
                "mean",
            ),
        )
        .sort_values(
            TARGET_DATE_COL
        )
    )

    figure, axis = plt.subplots(
        figsize=(
            13,
            6,
        )
    )

    axis.plot(
        monthly_df[
            TARGET_DATE_COL
        ],

        monthly_df[
            "Mean_RF_Predicted_Cases"
        ],

        label=
            "Random Forest mean point forecast",
    )

    axis.plot(
        monthly_df[
            TARGET_DATE_COL
        ],

        monthly_df[
            "Mean_NGBoost_Mean"
        ],

        label=
            "NGBoost predictive mean",
    )

    axis.fill_between(
        monthly_df[
            TARGET_DATE_COL
        ],

        monthly_df[
            "Mean_NGBoost_Lower_95"
        ],

        monthly_df[
            "Mean_NGBoost_Upper_95"
        ],

        alpha=0.2,

        label=
            "Mean NGBoost 95% prediction interval",
    )

    axis.set_title(
        f"Future Forecast with NGBoost Uncertainty - H{horizon}"
    )

    axis.set_xlabel(
        "Forecast target month"
    )

    axis.set_ylabel(
        "Mean predicted malnutrition cases across districts"
    )

    axis.legend()

    figure.autofmt_xdate()

    figure.tight_layout()

    figure.savefig(
        FIGURE_DIR
        /
        f"27b_future_ngboost_uncertainty_h{horizon}.png",

        dpi=300,

        bbox_inches="tight",
    )

    plt.close(
        figure
    )


# ------------------------------------------------------------
# Figure 2:
# Uncertainty-level counts by horizon.
# ------------------------------------------------------------

level_order = [
    "Low Uncertainty",
    "Moderate Uncertainty",
    "High Uncertainty",
]

count_table = (
    future_uncertainty_df
    .groupby(
        [
            "Horizon_Months",
            "Uncertainty_Level",
        ]
    )
    .size()
    .unstack(
        fill_value=0
    )
    .reindex(
        columns=level_order,
        fill_value=0,
    )
)

figure, axis = plt.subplots(
    figsize=(
        10,
        6,
    )
)

count_table.plot(
    kind="bar",
    ax=axis,
)

axis.set_title(
    "Future Forecast Uncertainty Levels by Horizon"
)

axis.set_xlabel(
    "Forecast horizon (months)"
)

axis.set_ylabel(
    "Number of district-month forecasts"
)

axis.tick_params(
    axis="x",
    rotation=0,
)

axis.legend(
    title="Uncertainty Level"
)

figure.tight_layout()

figure.savefig(
    FIGURE_DIR
    /
    "27b_future_uncertainty_level_counts.png",

    dpi=300,

    bbox_inches="tight",
)

plt.close(
    figure
)


# ============================================================
# 26. FINAL REPORT
# ============================================================

print_header(
    "STEP 27B COMPLETE"
)

print(
    "\nMain interpretation:"
)

print(
    "- Random Forest remains the main future predicted case count."
)

print(
    "- NGBoost now supplies a probabilistic 95% predictive range "
    "for every 2026-2030 district/month/horizon forecast."
)

print(
    "- Low / Moderate / High uncertainty uses thresholds "
    "frozen from 2024 before the 2025 final audit."
)

print(
    "- Step 21B unseen-2025 coverage is retained as the empirical "
    "evidence about how well the uncertainty method calibrated."
)

print(
    "- Future 2026-2030 coverage cannot be measured until actual "
    "future observations become available."
)

print(
    "\nSaved:"
)

print(
    f"- Main future uncertainty output:\n  "
    f"{FINAL_OUTPUT_PATH}"
)

print(
    f"- Summary:\n  "
    f"{SUMMARY_OUTPUT_PATH}"
)

print(
    f"- Audit:\n  "
    f"{AUDIT_OUTPUT_PATH}"
)

print(
    f"- Methodology:\n  "
    f"{METHODOLOGY_OUTPUT_PATH}"
)

print(
    f"- NGBoost model bundles:\n  "
    f"{MODEL_DIR}"
)

print(
    f"- Figures:\n  "
    f"{FIGURE_DIR}"
)

print(
    "\nNEXT STEP AFTER THIS PASSES:"
)

print(
    "Run / update Step 28 future SHAP, then future risk, "
    "map, resources and early-warning outputs using this "
    "uncertainty-enriched future forecast file."
)

print(
    "\nSTEP 27B - FUTURE NGBOOST UNCERTAINTY "
    "2026-2030 COMPLETE"
)

print(
    "=" * 120
)
