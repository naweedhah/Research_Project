# ============================================================
# STEP 27 - FINAL FUTURE FORECAST GENERATION (2026-2030)
# Childhood Malnutrition Forecasting Research
#
# Purpose
# -------
# - Use the FINAL FROZEN Random Forest strategy selected in Step 20
# - Retrain the frozen models on all labels genuinely available up to 2025-12
# - Generate real future district-level forecasts from 2026 to 2030
# - Preserve the same H1 / H3 / H6 meaning used during validation/testing:
#       origin month t -> H1 target t+1
#       origin month t -> H3 target t+3
#       origin month t -> H6 target t+6
# - Use H1 recursively to maintain future Malnutrition_Cases history
# - Use a transparent 12-month seasonal-naive assumption for future
#   non-target predictors because their true future values are not known.
#
# IMPORTANT METHODOLOGY RULES
# ---------------------------
# 1. NO model re-selection is done here.
# 2. NO hyperparameter tuning is done here.
# 3. Frozen Step 20 model configurations are retained:
#       H1 -> RF_B
#       H3 -> RF_BASE
#       H6 -> RF_BASE
# 4. The final lockbox evaluation remains Step 21.
# 5. After the Step 21 lockbox evaluation is frozen, retraining the already
#    selected model on all available historical labels is allowed for deployment.
# 6. Forecasts beyond the observed 2025 data are projections. Predictor values
#    after 2025-12 are generated using a documented seasonal-naive assumption.
#
# Dashboard interpretation example
# --------------------------------
# If the doctor selects:
#       Forecast Origin = 2027-06
# the system returns:
#       H1 -> 2027-07
#       H3 -> 2027-09
#       H6 -> 2027-12
#
# Forecast TARGET coverage is capped at:
#       2026-01 to 2030-12
#
# Therefore near the end of 2030, only horizons whose target date still falls
# inside 2030 are included.
# ============================================================

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


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

# Last month of observed/actual data.
ACTUAL_CUTOFF = pd.Timestamp("2025-12-01")

# Final future TARGET coverage.
FUTURE_TARGET_START = pd.Timestamp("2026-01-01")
FUTURE_TARGET_END = pd.Timestamp("2030-12-01")

# To produce Jan-2026 with H1, recursion must start from Dec-2025.
ENGINE_ORIGIN_START = ACTUAL_CUTOFF

# H1 from Nov-2030 produces Dec-2030.
ENGINE_ORIGIN_END = FUTURE_TARGET_END - pd.DateOffset(months=1)

PREDICTOR_LAGS = [1, 3, 6, 12]
TARGET_LAGS = [1, 3, 6, 12]
ROLLING_WINDOWS = [3, 6, 12]

PREDICTOR_PROJECTION_METHOD = "SEASONAL_NAIVE_12_MONTH"

# Final frozen Step 20 Random Forest strategy.
RF_CONFIGS = {
    1: {
        "Config_ID": "RF_B",
        "n_estimators": 400,
        "max_depth": 20,
        "min_samples_split": 4,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
        "bootstrap": True,
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    },
    3: {
        "Config_ID": "RF_BASE",
        "n_estimators": 300,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
        "bootstrap": True,
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    },
    6: {
        "Config_ID": "RF_BASE",
        "n_estimators": 300,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
        "bootstrap": True,
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    },
}


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "outputs" / "reports"
MODEL_DIR = BASE_DIR / "outputs" / "models"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

BASE_DATA_PATH = PROCESSED_DIR / "malnutrition_preprocessed_base.csv"

FEATURE_FILES = {
    1: PROCESSED_DIR / "malnutrition_features_h1.csv",
    3: PROCESSED_DIR / "malnutrition_features_h3.csv",
    6: PROCESSED_DIR / "malnutrition_features_h6.csv",
}

FORECAST_OUTPUT_PATH = REPORT_DIR / "27_future_forecasts_2026_2030.csv"
AUDIT_OUTPUT_PATH = REPORT_DIR / "27_future_forecast_audit.csv"
PREDICTOR_OUTPUT_PATH = REPORT_DIR / "27_future_predictor_projection.csv"
METHODOLOGY_OUTPUT_PATH = REPORT_DIR / "27_future_forecast_methodology.json"


# ============================================================
# 3. DISPLAY HELPERS
# ============================================================

def print_header(title, width=118):
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def print_subheader(title, width=118):
    print("\n" + "-" * width)
    print(title)
    print("-" * width)


# ============================================================
# 4. BASIC HELPERS
# ============================================================

def safe_float(value):
    try:
        if pd.isna(value):
            return np.nan
        return float(value)
    except Exception:
        return np.nan


def month_distance(start, end):
    """Number of whole calendar months from start to end."""
    return (end.year - start.year) * 12 + (end.month - start.month)


def determine_feature_columns(df, horizon):
    """
    Match the exact Step 22 / final-model feature selection logic.
    """
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

    feature_cols = [
        c
        for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]

    if len(feature_cols) != EXPECTED_ENGINEERED_FEATURES:
        raise ValueError(
            f"H{horizon}: expected {EXPECTED_ENGINEERED_FEATURES} "
            f"numeric engineered features, found {len(feature_cols)}.\n"
            "Confirm that the corrected Step 07 feature files are being used."
        )

    return feature_cols


def identify_monthly_predictor_columns(base_df):
    """
    Match corrected Step 07 logic:
    all numeric columns except target/helper/output columns are monthly predictors.
    """
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
        base_df.select_dtypes(include=[np.number]).columns.tolist()
    )

    predictor_columns = [
        c for c in numeric_columns
        if c not in excluded_numeric
    ]

    return predictor_columns


# ============================================================
# 5. LOAD AND VALIDATE BASE DATA
# ============================================================

print_header("STEP 27 - FINAL FUTURE FORECAST GENERATION 2026-2030")

if not BASE_DATA_PATH.exists():
    raise FileNotFoundError(
        f"Missing preprocessed base data:\n{BASE_DATA_PATH}"
    )

for h, path in FEATURE_FILES.items():
    if not path.exists():
        raise FileNotFoundError(
            f"Missing H{h} feature file:\n{path}"
        )

base_df = pd.read_csv(BASE_DATA_PATH)
base_df.columns = [c.strip() for c in base_df.columns]

required_base_columns = {DISTRICT_COL, DATE_COL, TARGET}
missing_base = required_base_columns.difference(base_df.columns)

if missing_base:
    raise ValueError(
        f"Base data is missing required columns: {sorted(missing_base)}"
    )

base_df[DATE_COL] = pd.to_datetime(base_df[DATE_COL], errors="coerce")

if base_df[DATE_COL].isna().any():
    raise ValueError("Base data contains invalid Date values.")

base_df = (
    base_df
    .sort_values([DISTRICT_COL, DATE_COL])
    .reset_index(drop=True)
)

duplicate_count = int(
    base_df.duplicated([DISTRICT_COL, DATE_COL]).sum()
)

if duplicate_count != 0:
    raise ValueError(
        f"Duplicate District-Date rows found: {duplicate_count}"
    )

districts = sorted(
    base_df[DISTRICT_COL].astype(str).dropna().unique().tolist()
)

if len(districts) != 25:
    raise ValueError(
        f"Expected 25 districts, found {len(districts)}."
    )

observed_max_date = base_df[DATE_COL].max()

if observed_max_date < ACTUAL_CUTOFF:
    raise ValueError(
        f"Observed data ends at {observed_max_date.date()}, "
        f"but Step 27 requires data through {ACTUAL_CUTOFF.date()}."
    )

# Do not allow any observations after the documented final cutoff to enter.
base_df = base_df[
    base_df[DATE_COL] <= ACTUAL_CUTOFF
].copy()

minimum_date = base_df[DATE_COL].min()

print(f"\nObserved data used : {minimum_date.date()} to {ACTUAL_CUTOFF.date()}")
print(f"Districts          : {len(districts)}")


# ============================================================
# 6. IDENTIFY RAW MONTHLY PREDICTORS
# ============================================================

monthly_predictors = identify_monthly_predictor_columns(base_df)

print(f"Monthly predictors : {len(monthly_predictors)}")

if len(monthly_predictors) != 35:
    print(
        "WARNING: corrected Step 07 previously identified 35 monthly "
        f"predictors, but this file currently contains {len(monthly_predictors)}."
    )

# Important correction retained from Step 07.
for required_monthly in [
    "SAM_Cases_Annual",
    "MAM_Wasting_Cases_Annual",
]:
    if required_monthly in base_df.columns and required_monthly not in monthly_predictors:
        raise ValueError(
            f"{required_monthly} must be treated as a MONTHLY predictor."
        )


# ============================================================
# 7. PROJECT FUTURE RAW PREDICTORS
# ============================================================

print_header("PROJECT FUTURE NON-TARGET PREDICTORS")

print(
    "\nFuture predictor assumption:\n"
    "- True predictor values after 2025-12 are unknown.\n"
    "- Each future predictor uses a 12-month seasonal-naive projection.\n"
    "- Example: January 2026 predictor <- January 2025 value.\n"
    "- January 2027 then uses the projected January 2026 value.\n"
    "- Missing seasonal references use same-month historical median,\n"
    "  then district median, then global median."
)

# Long-form lookup:
# key = (district, timestamp, predictor)
predictor_lookup = {}

for _, row in base_df.iterrows():
    district = str(row[DISTRICT_COL])
    date = pd.Timestamp(row[DATE_COL])

    for predictor in monthly_predictors:
        predictor_lookup[(district, date, predictor)] = safe_float(row[predictor])

# Historical fallback statistics are calculated ONLY from observed data.
district_month_medians = {}
district_medians = {}
global_medians = {}

for predictor in monthly_predictors:
    global_medians[predictor] = safe_float(
        base_df[predictor].median(skipna=True)
    )

    for district in districts:
        ddf = base_df[
            base_df[DISTRICT_COL].astype(str) == district
        ]

        district_medians[(district, predictor)] = safe_float(
            ddf[predictor].median(skipna=True)
        )

        for month in range(1, 13):
            same_month = ddf[
                ddf[DATE_COL].dt.month == month
            ][predictor]

            district_month_medians[
                (district, month, predictor)
            ] = safe_float(
                same_month.median(skipna=True)
            )

future_predictor_dates = pd.date_range(
    start=FUTURE_TARGET_START,
    end=FUTURE_TARGET_END,
    freq="MS",
)

predictor_projection_records = []
fallback_counter = {
    "SEASONAL_12": 0,
    "DISTRICT_MONTH_MEDIAN": 0,
    "DISTRICT_MEDIAN": 0,
    "GLOBAL_MEDIAN": 0,
    "ZERO": 0,
}

for date in future_predictor_dates:
    seasonal_source_date = date - pd.DateOffset(months=12)

    for district in districts:
        output_row = {
            DISTRICT_COL: district,
            DATE_COL: date,
        }

        for predictor in monthly_predictors:
            value = predictor_lookup.get(
                (district, seasonal_source_date, predictor),
                np.nan,
            )

            source_method = "SEASONAL_12"

            if pd.isna(value):
                value = district_month_medians.get(
                    (district, date.month, predictor),
                    np.nan,
                )
                source_method = "DISTRICT_MONTH_MEDIAN"

            if pd.isna(value):
                value = district_medians.get(
                    (district, predictor),
                    np.nan,
                )
                source_method = "DISTRICT_MEDIAN"

            if pd.isna(value):
                value = global_medians.get(
                    predictor,
                    np.nan,
                )
                source_method = "GLOBAL_MEDIAN"

            if pd.isna(value):
                value = 0.0
                source_method = "ZERO"

            value = float(value)

            predictor_lookup[
                (district, date, predictor)
            ] = value

            output_row[predictor] = value
            fallback_counter[source_method] += 1

        predictor_projection_records.append(output_row)

future_predictor_df = pd.DataFrame(
    predictor_projection_records
)

future_predictor_df.to_csv(
    PREDICTOR_OUTPUT_PATH,
    index=False,
)

print(f"\nFuture predictor rows saved : {len(future_predictor_df)}")
print(f"Output                    : {PREDICTOR_OUTPUT_PATH}")


# ============================================================
# 8. CREATE TARGET HISTORY STATE
# ============================================================

print_header("CREATE TARGET HISTORY STATE")

# key = (district, date)
target_state = {}

for _, row in base_df.iterrows():
    district = str(row[DISTRICT_COL])
    date = pd.Timestamp(row[DATE_COL])
    target_state[(district, date)] = safe_float(row[TARGET])

print(
    "Observed Malnutrition_Cases history loaded through "
    f"{ACTUAL_CUTOFF.date()}."
)


# ============================================================
# 9. FEATURE BUILDING FOR A FUTURE ORIGIN
# ============================================================

def get_target_value(district, date):
    return target_state.get(
        (district, pd.Timestamp(date)),
        np.nan,
    )


def get_predictor_value(district, date, predictor):
    return predictor_lookup.get(
        (district, pd.Timestamp(date), predictor),
        np.nan,
    )


def build_future_feature_row(district, origin_date):
    """
    Recreate the corrected Step 07 feature logic for one district/origin.
    """
    origin_date = pd.Timestamp(origin_date)

    row = {}

    # Calendar features: known in advance.
    row["Time_Index"] = month_distance(
        minimum_date,
        origin_date,
    )

    row["Month_Sin"] = float(
        np.sin(
            2 * np.pi * origin_date.month / 12
        )
    )

    row["Month_Cos"] = float(
        np.cos(
            2 * np.pi * origin_date.month / 12
        )
    )

    # Historical target lags.
    for lag in TARGET_LAGS:
        lag_date = origin_date - pd.DateOffset(months=lag)
        row[f"Malnutrition_Lag_{lag}"] = get_target_value(
            district,
            lag_date,
        )

    # Historical target rolling features.
    # Exactly matches Step 07 shift(1).rolling(window).
    for window in ROLLING_WINDOWS:
        previous_dates = [
            origin_date - pd.DateOffset(months=i)
            for i in range(1, window + 1)
        ]

        values = np.asarray(
            [
                get_target_value(district, d)
                for d in previous_dates
            ],
            dtype=float,
        )

        if np.isnan(values).any():
            rolling_mean = np.nan
            rolling_std = np.nan
        else:
            rolling_mean = float(np.mean(values))

            # pandas Series.std() defaults to ddof=1.
            rolling_std = (
                float(np.std(values, ddof=1))
                if len(values) > 1
                else np.nan
            )

        row[
            f"Malnutrition_Rolling_Mean_{window}"
        ] = rolling_mean

        row[
            f"Malnutrition_Rolling_STD_{window}"
        ] = rolling_std

    # Lagged raw predictors.
    for predictor in monthly_predictors:
        for lag in PREDICTOR_LAGS:
            lag_date = origin_date - pd.DateOffset(months=lag)

            row[
                f"{predictor}_Lag_{lag}"
            ] = get_predictor_value(
                district,
                lag_date,
                predictor,
            )

    return row


# ============================================================
# 10. FIT FINAL FROZEN MODELS ON ALL AVAILABLE LABELS
# ============================================================

print_header("RETRAIN FROZEN FINAL MODELS ON ALL AVAILABLE LABELS")

model_bundle = {}
training_audit_records = []

for horizon in HORIZONS:
    feature_path = FEATURE_FILES[horizon]
    df = pd.read_csv(feature_path)

    required_cols = {
        DISTRICT_COL,
        ORIGIN_DATE_COL,
        TARGET_DATE_COL,
        MODEL_TARGET_COL,
    }

    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        raise ValueError(
            f"H{horizon}: missing required columns: "
            f"{sorted(missing_cols)}"
        )

    df[ORIGIN_DATE_COL] = pd.to_datetime(
        df[ORIGIN_DATE_COL],
        errors="coerce",
    )

    df[TARGET_DATE_COL] = pd.to_datetime(
        df[TARGET_DATE_COL],
        errors="coerce",
    )

    feature_cols = determine_feature_columns(
        df,
        horizon,
    )

    # All labels genuinely known by 2025-12 can now be used
    # for deployment retraining AFTER final evaluation is frozen.
    train_df = df[
        df[MODEL_TARGET_COL].notna()
        & (df[TARGET_DATE_COL] <= ACTUAL_CUTOFF)
    ].copy()

    if train_df.empty:
        raise ValueError(
            f"H{horizon}: no deployment training rows found."
        )

    medians = (
        train_df[feature_cols]
        .median(numeric_only=True)
        .fillna(0.0)
    )

    x_train_num = (
        train_df[feature_cols]
        .copy()
        .fillna(medians)
        .astype(float)
        .reset_index(drop=True)
    )

    district_categories = sorted(
        train_df[DISTRICT_COL]
        .astype(str)
        .dropna()
        .unique()
        .tolist()
    )

    if district_categories != districts:
        raise ValueError(
            f"H{horizon}: deployment-training district set does not "
            "match base-data district set."
        )

    train_cat = pd.Categorical(
        train_df[DISTRICT_COL].astype(str),
        categories=district_categories,
    )

    x_train_dummies = pd.get_dummies(
        train_cat,
        prefix="District",
        dtype=float,
    ).reset_index(drop=True)

    x_train = pd.concat(
        [x_train_num, x_train_dummies],
        axis=1,
    )

    y_train = (
        train_df[MODEL_TARGET_COL]
        .astype(float)
        .to_numpy()
    )

    params = {
        k: v
        for k, v in RF_CONFIGS[horizon].items()
        if k != "Config_ID"
    }

    model = RandomForestRegressor(**params)
    model.fit(x_train, y_train)

    model_path = (
        MODEL_DIR
        / f"27_final_future_rf_h{horizon}.joblib"
    )

    joblib.dump(
        {
            "model": model,
            "horizon": horizon,
            "config_id": RF_CONFIGS[horizon]["Config_ID"],
            "feature_columns": feature_cols,
            "model_columns": x_train.columns.tolist(),
            "feature_medians": medians.to_dict(),
            "district_categories": district_categories,
            "actual_cutoff": str(ACTUAL_CUTOFF.date()),
        },
        model_path,
    )

    model_bundle[horizon] = {
        "model": model,
        "feature_columns": feature_cols,
        "model_columns": x_train.columns.tolist(),
        "medians": medians,
        "district_categories": district_categories,
        "model_path": model_path,
    }

    training_audit_records.append({
        "Horizon_Months": horizon,
        "Config_ID": RF_CONFIGS[horizon]["Config_ID"],
        "Training_Rows": len(train_df),
        "First_Training_Origin": train_df[ORIGIN_DATE_COL].min(),
        "Last_Training_Origin": train_df[ORIGIN_DATE_COL].max(),
        "First_Training_Target": train_df[TARGET_DATE_COL].min(),
        "Last_Training_Target": train_df[TARGET_DATE_COL].max(),
        "Engineered_Feature_Count": len(feature_cols),
        "Final_Model_Feature_Count": len(x_train.columns),
        "Model_Path": str(model_path),
    })

    print(
        f"H{horizon} | {RF_CONFIGS[horizon]['Config_ID']} "
        f"| train={len(train_df)} "
        f"| features={len(feature_cols)} "
        f"| model saved"
    )


# ============================================================
# 11. FUTURE PREDICTION MATRIX TRANSFORM
# ============================================================

def transform_future_rows(
    future_rows,
    horizon,
):
    bundle = model_bundle[horizon]

    feature_cols = bundle["feature_columns"]
    medians = bundle["medians"]
    district_categories = bundle["district_categories"]
    model_columns = bundle["model_columns"]

    missing_generated_features = [
        c
        for c in feature_cols
        if c not in future_rows.columns
    ]

    if missing_generated_features:
        raise ValueError(
            f"H{horizon}: future feature generation is missing "
            f"{len(missing_generated_features)} required features.\n"
            f"Examples: {missing_generated_features[:10]}"
        )

    x_num = (
        future_rows[feature_cols]
        .copy()
        .fillna(medians)
        .astype(float)
        .reset_index(drop=True)
    )

    future_cat = pd.Categorical(
        future_rows[DISTRICT_COL].astype(str),
        categories=district_categories,
    )

    x_dummies = pd.get_dummies(
        future_cat,
        prefix="District",
        dtype=float,
    ).reset_index(drop=True)

    x_pred = pd.concat(
        [x_num, x_dummies],
        axis=1,
    )

    x_pred = x_pred.reindex(
        columns=model_columns,
        fill_value=0.0,
    )

    return x_pred


# ============================================================
# 12. ITERATIVE FUTURE FORECAST ENGINE
# ============================================================

print_header("GENERATE FUTURE FORECASTS")

future_prediction_records = []
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
    # Build ONE origin feature state for every district.
    future_feature_records = []

    for district in districts:
        feature_values = build_future_feature_row(
            district,
            origin_date,
        )

        feature_values[DISTRICT_COL] = district
        feature_values[ORIGIN_DATE_COL] = origin_date

        future_feature_records.append(
            feature_values
        )

    future_rows = pd.DataFrame(
        future_feature_records
    )

    if len(future_rows) != 25:
        raise ValueError(
            f"{origin_date.date()}: expected 25 district rows, "
            f"found {len(future_rows)}."
        )

    horizon_predictions = {}

    for horizon in HORIZONS:
        target_date = (
            origin_date
            + pd.DateOffset(months=horizon)
        )

        # We still need H1 at every loop step for target-state recursion.
        # H3/H6 are calculated only when the target remains inside 2030.
        should_predict = (
            horizon == 1
            or target_date <= FUTURE_TARGET_END
        )

        if not should_predict:
            continue

        x_pred = transform_future_rows(
            future_rows,
            horizon,
        )

        model = model_bundle[horizon]["model"]

        predictions = np.maximum(
            model.predict(x_pred),
            0.0,
        )

        horizon_predictions[horizon] = predictions

        # Save only genuine future targets in the defined coverage.
        if (
            target_date >= FUTURE_TARGET_START
            and target_date <= FUTURE_TARGET_END
        ):
            for row_position, district in enumerate(districts):
                prediction = float(
                    predictions[row_position]
                )

                future_prediction_records.append({
                    "Model": "Random Forest",
                    "Config_ID": RF_CONFIGS[horizon]["Config_ID"],
                    "Horizon_Months": horizon,
                    "District": district,
                    "Forecast_Origin_Date": origin_date,
                    "Forecast_Target_Date": target_date,
                    "Origin_Year": int(origin_date.year),
                    "Origin_Month": int(origin_date.month),
                    "Target_Year": int(target_date.year),
                    "Target_Month": int(target_date.month),
                    "Predicted_Cases": prediction,
                    "Forecast_Mode": "RECURSIVE_FUTURE_PROJECTION",
                    "Predictor_Projection_Method": PREDICTOR_PROJECTION_METHOD,
                    "Origin_State_Type": (
                        "LAST_ACTUAL_ORIGIN"
                        if origin_date == ACTUAL_CUTOFF
                        else "SIMULATED_FUTURE_ORIGIN"
                    ),
                    "Months_Beyond_Last_Actual_Target": int(
                        month_distance(
                            ACTUAL_CUTOFF,
                            target_date,
                        )
                    ),
                })

    # --------------------------------------------------------
    # CRITICAL RECURSION RULE
    # --------------------------------------------------------
    # Only H1 advances the month-by-month future target state.
    #
    # Example:
    # origin Dec-2025 -> H1 predicts Jan-2026
    # that Jan-2026 prediction becomes available for later
    # target lag/rolling features.
    # H3/H6 remain DIRECT horizon predictions and are NOT used
    # to overwrite the recursive monthly target state.
    # --------------------------------------------------------
    if 1 not in horizon_predictions:
        raise RuntimeError(
            f"H1 prediction missing at origin {origin_date.date()}."
        )

    h1_target_date = (
        origin_date
        + pd.DateOffset(months=1)
    )

    for row_position, district in enumerate(districts):
        target_state[
            (district, h1_target_date)
        ] = float(
            horizon_predictions[1][row_position]
        )

    origin_audit_records.append({
        "Forecast_Origin_Date": origin_date,
        "Origin_Number": origin_number,
        "Origin_State_Type": (
            "LAST_ACTUAL_ORIGIN"
            if origin_date == ACTUAL_CUTOFF
            else "SIMULATED_FUTURE_ORIGIN"
        ),
        "District_Rows": len(future_rows),
        "H1_Target_Date": h1_target_date,
        "H1_State_Updated": True,
        "H3_Within_Coverage": bool(
            origin_date + pd.DateOffset(months=3)
            <= FUTURE_TARGET_END
        ),
        "H6_Within_Coverage": bool(
            origin_date + pd.DateOffset(months=6)
            <= FUTURE_TARGET_END
        ),
    })

    print(
        f"Origin {origin_number:02d}/{len(origin_dates)} "
        f"| {origin_date.date()} "
        f"| H1->{(origin_date + pd.DateOffset(months=1)).date()} "
        f"| H3->{(origin_date + pd.DateOffset(months=3)).date()} "
        f"| H6->{(origin_date + pd.DateOffset(months=6)).date()}"
    )


# ============================================================
# 13. SAVE FUTURE FORECASTS
# ============================================================

future_forecast_df = pd.DataFrame(
    future_prediction_records
)

if future_forecast_df.empty:
    raise RuntimeError(
        "No future forecasts were generated."
    )

future_forecast_df = (
    future_forecast_df
    .sort_values(
        [
            "Forecast_Origin_Date",
            "Horizon_Months",
            "District",
        ]
    )
    .reset_index(drop=True)
)

future_forecast_df.to_csv(
    FORECAST_OUTPUT_PATH,
    index=False,
)

audit_df = pd.DataFrame(
    training_audit_records
)

origin_audit_df = pd.DataFrame(
    origin_audit_records
)

# Combine the two audit sections into one CSV-friendly table.
audit_df["Audit_Type"] = "DEPLOYMENT_TRAINING"

origin_audit_df["Audit_Type"] = "FUTURE_ORIGIN"

combined_audit = pd.concat(
    [
        audit_df,
        origin_audit_df,
    ],
    ignore_index=True,
    sort=False,
)

combined_audit.to_csv(
    AUDIT_OUTPUT_PATH,
    index=False,
)


# ============================================================
# 14. VALIDATION CHECKS ON GENERATED FUTURE OUTPUT
# ============================================================

print_header("FINAL FUTURE FORECAST AUDIT")

# Every saved prediction must be inside the requested target coverage.
if not (
    future_forecast_df[TARGET_DATE_COL].between(
        FUTURE_TARGET_START,
        FUTURE_TARGET_END,
    )
).all():
    raise ValueError(
        "Future forecast output contains target dates "
        "outside 2026-01 to 2030-12."
    )

# Target mapping must exactly match origin + horizon.
expected_target_dates = (
    pd.to_datetime(
        future_forecast_df[ORIGIN_DATE_COL]
    )
    + future_forecast_df["Horizon_Months"].apply(
        lambda h: pd.DateOffset(months=int(h))
    )
)

mapping_mismatches = int(
    (
        pd.to_datetime(
            future_forecast_df[TARGET_DATE_COL]
        )
        != expected_target_dates
    ).sum()
)

if mapping_mismatches != 0:
    raise ValueError(
        f"Forecast origin/target mapping mismatches: "
        f"{mapping_mismatches}"
    )

# Each origin-horizon request should have all 25 districts.
coverage_counts = (
    future_forecast_df
    .groupby(
        [
            ORIGIN_DATE_COL,
            "Horizon_Months",
        ]
    )[DISTRICT_COL]
    .nunique()
)

bad_coverage = coverage_counts[
    coverage_counts != 25
]

if len(bad_coverage) != 0:
    raise ValueError(
        "Some origin/horizon combinations do not contain "
        "all 25 districts."
    )

summary = (
    future_forecast_df
    .groupby("Horizon_Months")
    .agg(
        Rows=("Predicted_Cases", "size"),
        Origins=(ORIGIN_DATE_COL, "nunique"),
        Districts=(DISTRICT_COL, "nunique"),
        First_Target=(TARGET_DATE_COL, "min"),
        Last_Target=(TARGET_DATE_COL, "max"),
        Mean_Predicted_Cases=("Predicted_Cases", "mean"),
        Min_Predicted_Cases=("Predicted_Cases", "min"),
        Max_Predicted_Cases=("Predicted_Cases", "max"),
    )
    .reset_index()
)

print("\nFuture forecast summary:")
print(summary.to_string(index=False))

print(
    f"\nTotal future forecast rows: "
    f"{len(future_forecast_df)}"
)

print(
    f"Origin-target mapping mismatches: "
    f"{mapping_mismatches}"
)

print(
    "District coverage per origin/horizon: PASS"
)

# Expected rows for target-capped 2026-2030 coverage:
# H1 = 60 origins * 25 = 1500
# H3 = 58 origins * 25 = 1450
# H6 = 55 origins * 25 = 1375
# Total = 4325
expected_rows = {
    1: 1500,
    3: 1450,
    6: 1375,
}

for horizon, expected in expected_rows.items():
    actual = int(
        (
            future_forecast_df[
                "Horizon_Months"
            ]
            == horizon
        ).sum()
    )

    if actual != expected:
        raise ValueError(
            f"H{horizon}: expected {expected} future rows, "
            f"found {actual}."
        )

print("Expected H1/H3/H6 row counts: PASS")


# ============================================================
# 15. SAVE METHODOLOGY METADATA
# ============================================================

methodology = {
    "step": 27,
    "title": "Final Future Forecast Generation 2026-2030",
    "actual_data_cutoff": str(ACTUAL_CUTOFF.date()),
    "future_target_start": str(FUTURE_TARGET_START.date()),
    "future_target_end": str(FUTURE_TARGET_END.date()),
    "horizons_months": HORIZONS,
    "forecast_mapping": {
        "H1": "origin + 1 month",
        "H3": "origin + 3 months",
        "H6": "origin + 6 months",
    },
    "frozen_random_forest_configs": {
        str(h): RF_CONFIGS[h]
        for h in HORIZONS
    },
    "future_target_state_method": (
        "H1 recursive monthly state update; "
        "H3 and H6 remain direct horizon predictions"
    ),
    "future_predictor_method": (
        "12-month seasonal-naive recursive projection "
        "with historical median fallbacks"
    ),
    "important_interpretation": (
        "Step 21 remains the final unseen 2025 lockbox evaluation. "
        "Step 27 retrains the frozen selected models on all labels "
        "available by 2025-12 only for deployment/future projection."
    ),
    "output_files": {
        "future_forecasts": str(FORECAST_OUTPUT_PATH),
        "future_predictor_projection": str(PREDICTOR_OUTPUT_PATH),
        "audit": str(AUDIT_OUTPUT_PATH),
    },
}

with open(
    METHODOLOGY_OUTPUT_PATH,
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        methodology,
        f,
        indent=2,
        default=str,
    )


# ============================================================
# 16. EXAMPLE DASHBOARD LOOKUP
# ============================================================

example_origin = pd.Timestamp("2027-06-01")

example = future_forecast_df[
    future_forecast_df[
        ORIGIN_DATE_COL
    ]
    == example_origin
][
    [
        "Horizon_Months",
        TARGET_DATE_COL,
    ]
].drop_duplicates().sort_values(
    "Horizon_Months"
)

print_header("DASHBOARD MAPPING EXAMPLE")

print("If doctor selects origin month: 2027-06")
print(example.to_string(index=False))


# ============================================================
# 17. FINAL SUMMARY
# ============================================================

print_header("STEP 27 COMPLETE")

print(
    "\nFinal frozen strategy:\n"
    "- H1 -> Random Forest RF_B\n"
    "- H3 -> Random Forest RF_BASE\n"
    "- H6 -> Random Forest RF_BASE\n"
)

print(
    "Future target coverage:\n"
    "- January 2026 to December 2030\n"
)

print(
    "Forecast behavior:\n"
    "- Same H1/H3/H6 origin -> target mapping used in testing\n"
    "- H1 recursively maintains future monthly target history\n"
    "- H3/H6 remain direct horizon models\n"
    "- Future non-target predictors use transparent seasonal-naive projection\n"
)

print("Saved:")
print(f"- {FORECAST_OUTPUT_PATH}")
print(f"- {PREDICTOR_OUTPUT_PATH}")
print(f"- {AUDIT_OUTPUT_PATH}")
print(f"- {METHODOLOGY_OUTPUT_PATH}")
print(f"- Models: {MODEL_DIR}")

print("\nSTEP 27 - FINAL FUTURE FORECAST GENERATION COMPLETE")
