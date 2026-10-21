# ============================================================
# STEP 15B - TFT STRICT ROLLING-ORIGIN REVALIDATION
# Childhood Malnutrition Forecasting Research
#
# Model:
#   Temporal Fusion Transformer (TFT)
#
# Purpose:
# - Apply the same strict rolling-origin principle used in Step 15
# - Rebuild preprocessing using only information available at each origin
# - Retrain TFT as the forecast origin moves
# - Evaluate H1, H3 and H6 separately on 2024 targets
# - Keep 2025 observed data out of evaluation/model fitting
#
# IMPORTANT:
# - This is NOT hyperparameter tuning.
# - TFT is a direct multi-horizon model, therefore it is handled
#   separately from Step 15.
# - Future-unknown variables are NEVER supplied as real future values.
#   Decoder rows use only known calendar variables; unknown predictors
#   receive neutral train-derived placeholder values.
# ============================================================

from pathlib import Path
import warnings
import random
import copy
import math

import numpy as np
import pandas as pd

import torch

import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger

from pytorch_forecasting import (
    TimeSeriesDataSet,
    TemporalFusionTransformer,
)
from pytorch_forecasting.data import GroupNormalizer, NaNLabelEncoder
from pytorch_forecasting.metrics import QuantileLoss


# ============================================================
# 1. GENERAL SETTINGS
# ============================================================

warnings.filterwarnings("ignore")

RANDOM_STATE = 42

TARGET = "Malnutrition_Cases"
DISTRICT = "District"
DATE_COLUMN = "Date"

MAX_ENCODER_LENGTH = 12
MAX_PREDICTION_LENGTH = 6

HORIZONS = [1, 3, 6]
QUANTILES = [0.025, 0.50, 0.975]

# Internal epoch-selection settings.
# This is model training control, NOT hyperparameter tuning.
MAX_EPOCHS_INTERNAL = 50
EARLY_STOPPING_PATIENCE = 6

BATCH_SIZE = 64

# Exact initial TFT configuration from Step 19.
# Keep these fixed throughout Step 15B.
TFT_LEARNING_RATE = 0.01
TFT_HIDDEN_SIZE = 16
TFT_ATTENTION_HEAD_SIZE = 2
TFT_DROPOUT = 0.10
TFT_HIDDEN_CONTINUOUS_SIZE = 8

VALIDATION_START = pd.Timestamp("2024-01-01")
VALIDATION_END = pd.Timestamp("2024-12-01")

# Earliest origin required to produce a 6-month-ahead Jan-2024 forecast.
FIRST_STRICT_ORIGIN = pd.Timestamp("2023-07-01")

# Latest origin required to produce a 1-month-ahead Dec-2024 forecast.
LAST_STRICT_ORIGIN = pd.Timestamp("2024-11-01")


# ============================================================
# 2. REPRODUCIBILITY
# ============================================================

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    pl.seed_everything(seed, workers=True)


set_seed(RANDOM_STATE)


# ============================================================
# 3. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "outputs" / "reports"
MODEL_DIR = BASE_DIR / "models" / "candidates"
LOG_DIR = BASE_DIR / "outputs" / "logs" / "15b_tft"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

BASE_DATA_PATH = PROCESSED_DIR / "malnutrition_preprocessed_base.csv"


# ============================================================
# 4. METRICS
# ============================================================

def calculate_mae(y_true, y_pred):
    return float(np.mean(np.abs(y_true - y_pred)))


def calculate_rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def calculate_wape(y_true, y_pred):
    denominator = np.sum(np.abs(y_true))
    if denominator == 0:
        return np.nan
    return float(
        np.sum(np.abs(y_true - y_pred))
        / denominator
        * 100
    )


def calculate_smape(y_true, y_pred):
    denominator = np.abs(y_true) + np.abs(y_pred)
    valid = denominator != 0

    if valid.sum() == 0:
        return np.nan

    return float(
        np.mean(
            2
            * np.abs(y_true[valid] - y_pred[valid])
            / denominator[valid]
        )
        * 100
    )


def calculate_r2(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

    if ss_tot == 0:
        return np.nan

    return float(1 - ss_res / ss_tot)


def pinball_loss(y_true, y_pred, quantile):
    error = y_true - y_pred
    return float(
        np.mean(
            np.maximum(
                quantile * error,
                (quantile - 1) * error
            )
        )
    )


# ============================================================
# 4B. TFT-SAFE COLUMN NAMES
# ============================================================

def make_tft_safe_column_names(dataframe):
    """
    PyTorch Forecasting does not allow '.' characters in column names.

    Example source columns:
        BMI <18.5 (%)
        Hb 7–10.9 g/dL (%)

    We only replace '.' in names. Data values are NOT changed.
    A uniqueness check prevents accidental duplicate names after replacement.
    """

    rename_map = {}

    for column in dataframe.columns:
        safe_name = str(column).replace(".", "_")

        rename_map[column] = safe_name

    safe_names = list(rename_map.values())

    if len(safe_names) != len(set(safe_names)):
        duplicates = sorted({
            name
            for name in safe_names
            if safe_names.count(name) > 1
        })

        raise ValueError(
            "Column-name sanitization created duplicate names: "
            f"{duplicates}"
        )

    return dataframe.rename(columns=rename_map), rename_map


# ============================================================
# 5. LOAD BASE DATA
# ============================================================

print("\n" + "=" * 120)
print("STEP 15B - TFT STRICT ROLLING-ORIGIN REVALIDATION")
print("=" * 120)

print("\nMethodology:")
print("- One TFT model is trained separately at every rolling forecast origin")
print("- Only target information known by that origin is used for training")
print("- Predictor medians are re-fitted at each origin")
print("- Internal epoch selection uses historical data only")
print("- Final TFT is refitted on all history available at that origin")
print("- H1, H3 and H6 are evaluated on 2024")
print("- Future-unknown predictors are NOT supplied using future observed values")
print("- Hyperparameter tuning is NOT performed")
print("- TFT architecture/hyperparameters match the Step 19 initial candidate")

if not BASE_DATA_PATH.exists():
    raise FileNotFoundError(
        f"Base data file not found:\n{BASE_DATA_PATH}"
    )

base_df = pd.read_csv(BASE_DATA_PATH)

# PyTorch Forecasting rejects '.' in variable names.
# Sanitize names before any feature identification.
base_df, TFT_COLUMN_RENAME_MAP = make_tft_safe_column_names(
    base_df
)

base_df[DATE_COLUMN] = pd.to_datetime(
    base_df[DATE_COLUMN]
)

renamed_columns = {
    old_name: new_name
    for old_name, new_name in TFT_COLUMN_RENAME_MAP.items()
    if old_name != new_name
}

if renamed_columns:
    print("\nTFT-safe column-name replacements:")
    for old_name, new_name in renamed_columns.items():
        print(f"- {old_name} -> {new_name}")

# IMPORTANT:
# The source CSV contains 2015-2025, but 2025 observations are removed
# immediately and are never used in model fitting, preprocessing or scoring.
base_df = (
    base_df[
        base_df[DATE_COLUMN]
        <= VALIDATION_END
    ]
    .copy()
)

base_df = (
    base_df
    .sort_values(
        [DISTRICT, DATE_COLUMN]
    )
    .reset_index(drop=True)
)

print(f"\nRows available through 2024 : {len(base_df)}")
print(f"Districts                  : {base_df[DISTRICT].nunique()}")
print(
    f"Date range                 : "
    f"{base_df[DATE_COLUMN].min().date()} to "
    f"{base_df[DATE_COLUMN].max().date()}"
)

if TARGET not in base_df.columns:
    raise KeyError(
        f"Target column '{TARGET}' is missing."
    )


# ============================================================
# 6. IDENTIFY HISTORICAL NUMERIC PREDICTORS
# ============================================================

# Columns that must NOT become historical predictors.
EXCLUDED_COLUMNS = {
    TARGET,
    "Year",
    "Month",
    "Month_Number",
    "Record_ID",
    "Data_Split",
    "Time_Index",
    "Month_Cat",
    "Month_Sin_TFT",
    "Month_Cos_TFT",
    "Series_ID",
}

candidate_numeric_columns = []

for column in base_df.columns:
    if column in EXCLUDED_COLUMNS:
        continue

    if column in [DISTRICT, DATE_COLUMN]:
        continue

    converted = pd.to_numeric(
        base_df[column],
        errors="coerce"
    )

    # Use source columns that contain at least some numeric information.
    if converted.notna().sum() > 0:
        candidate_numeric_columns.append(
            column
        )

        base_df[column] = converted


HISTORICAL_PREDICTORS = candidate_numeric_columns

print(
    f"Historical numeric predictors: "
    f"{len(HISTORICAL_PREDICTORS)}"
)

if len(HISTORICAL_PREDICTORS) == 0:
    raise ValueError(
        "No historical numeric predictors were identified."
    )

if len(HISTORICAL_PREDICTORS) != 35:
    print(
        "WARNING: current pipeline previously used 35 historical "
        f"numeric predictors, but Step 15B identified "
        f"{len(HISTORICAL_PREDICTORS)}."
    )
    print(
        "The script will continue using the dynamically identified "
        "source numeric predictors."
    )


# ============================================================
# 7. CALENDAR FEATURES
# ============================================================

global_start_period = pd.Period(
    base_df[DATE_COLUMN].min(),
    freq="M"
)


def add_calendar_features(dataframe):
    df = dataframe.copy()

    period = df[DATE_COLUMN].dt.to_period("M")

    df["Time_Index"] = (
        (period.dt.year - global_start_period.year) * 12
        +
        (period.dt.month - global_start_period.month)
    ).astype(int)

    df["Month_Cat"] = (
        df[DATE_COLUMN]
        .dt.month
        .astype(str)
    )

    month_number = (
        df[DATE_COLUMN]
        .dt.month
        .astype(float)
    )

    df["Month_Sin_TFT"] = np.sin(
        2 * np.pi * month_number / 12.0
    )

    df["Month_Cos_TFT"] = np.cos(
        2 * np.pi * month_number / 12.0
    )

    df[DISTRICT] = (
        df[DISTRICT]
        .astype(str)
    )

    return df


base_df = add_calendar_features(
    base_df
)


# ============================================================
# 8. BUILD CONTINUOUS TARGET SERIES SEGMENTS
# ============================================================

def assign_series_segments(dataframe):
    """
    Create a separate Series_ID whenever observed target continuity breaks.

    This prevents TFT encoder windows from crossing a missing-target gap.
    """

    output_frames = []

    for district, district_df in dataframe.groupby(
        DISTRICT,
        sort=True
    ):
        district_df = (
            district_df
            .sort_values(DATE_COLUMN)
            .copy()
        )

        observed = district_df[
            district_df[TARGET].notna()
        ].copy()

        if observed.empty:
            continue

        periods = (
            observed[DATE_COLUMN]
            .dt.to_period("M")
            .astype(int)
            .to_numpy()
        )

        segment_numbers = np.ones(
            len(observed),
            dtype=int
        )

        current_segment = 1

        for i in range(1, len(observed)):
            if periods[i] - periods[i - 1] != 1:
                current_segment += 1

            segment_numbers[i] = current_segment

        observed["Segment_Number"] = segment_numbers

        observed["Series_ID"] = (
            observed[DISTRICT].astype(str)
            +
            "__S"
            +
            observed["Segment_Number"].astype(str)
        )

        output_frames.append(
            observed
        )

    if len(output_frames) == 0:
        raise ValueError(
            "No continuous observed target segments could be created."
        )

    result = pd.concat(
        output_frames,
        ignore_index=True
    )

    result = (
        result
        .sort_values(
            [DISTRICT, DATE_COLUMN]
        )
        .reset_index(drop=True)
    )

    return result


observed_df = assign_series_segments(
    base_df
)

print(
    f"Observed target rows          : "
    f"{len(observed_df)}"
)

print(
    f"Continuous TFT series        : "
    f"{observed_df['Series_ID'].nunique()}"
)


# ============================================================
# 9. ORIGIN-SPECIFIC PREPROCESSING
# ============================================================

def fit_predictor_medians(
    dataframe,
    predictor_columns
):
    medians = (
        dataframe[
            predictor_columns
        ]
        .median()
    )

    all_missing = (
        medians[
            medians.isna()
        ]
        .index
        .tolist()
    )

    if all_missing:
        medians.loc[
            all_missing
        ] = 0.0

    return medians, all_missing


def apply_predictor_medians(
    dataframe,
    predictor_columns,
    medians
):
    result = dataframe.copy()

    for column in predictor_columns:
        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(
                medians[column]
            )
            .astype(float)
        )

    return result


# ============================================================
# 10. TFT DATASET BUILDER
# ============================================================

KNOWN_CATEGORICALS = [
    "Month_Cat"
]

KNOWN_REALS = [
    "Time_Index",
    "Month_Sin_TFT",
    "Month_Cos_TFT",
]

UNKNOWN_REALS = [
    TARGET,
    *HISTORICAL_PREDICTORS,
]


def build_training_dataset(
    dataframe
):
    """
    TFT training dataset.

    Series_ID is the group ID so target-missing gaps are not crossed.
    District remains a static categorical input.
    """

    dataset = TimeSeriesDataSet(
        dataframe,
        time_idx="Time_Index",
        target=TARGET,

        group_ids=[
            DISTRICT,
            "Series_ID"
        ],

        min_encoder_length=
            MAX_ENCODER_LENGTH,

        max_encoder_length=
            MAX_ENCODER_LENGTH,

        min_prediction_length=1,
        max_prediction_length=
            MAX_PREDICTION_LENGTH,

        static_categoricals=[
            DISTRICT
        ],

        time_varying_known_categoricals=
            KNOWN_CATEGORICALS,

        time_varying_known_reals=
            KNOWN_REALS,

        time_varying_unknown_reals=
            UNKNOWN_REALS,

        target_normalizer=
            GroupNormalizer(
                groups=[
                    DISTRICT
                ]
            ),

        categorical_encoders={
            DISTRICT:
                NaNLabelEncoder(
                    add_nan=True
                ),

            "Series_ID":
                NaNLabelEncoder(
                    add_nan=True
                ),

            "Month_Cat":
                NaNLabelEncoder(
                    add_nan=True
                )
        },

        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
        allow_missing_timesteps=False,
    )

    return dataset


# ============================================================
# 11. TFT MODEL BUILDER
# ============================================================

def build_tft_model(
    dataset
):
    model = TemporalFusionTransformer.from_dataset(
        dataset,

        learning_rate=
            TFT_LEARNING_RATE,

        hidden_size=
            TFT_HIDDEN_SIZE,

        attention_head_size=
            TFT_ATTENTION_HEAD_SIZE,

        dropout=
            TFT_DROPOUT,

        hidden_continuous_size=
            TFT_HIDDEN_CONTINUOUS_SIZE,

        output_size=
            len(QUANTILES),

        loss=
            QuantileLoss(
                quantiles=QUANTILES
            ),

        optimizer="adam",

        reduce_on_plateau_patience=4,

        log_interval=-1,
        log_val_interval=-1,
    )

    return model


# ============================================================
# 12. INTERNAL EPOCH SELECTION
# ============================================================

def select_epoch_historically(
    available_history,
    origin_date,
    origin_number
):
    """
    Use the last 12 available historical target months as internal validation.

    Preprocessing for this stage is fitted ONLY on the earlier core history.
    """

    unique_dates = (
        available_history[DATE_COLUMN]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    if len(unique_dates) < 36:
        raise ValueError(
            f"Not enough historical months for TFT internal validation "
            f"at origin {origin_date.date()}."
        )

    internal_dates = set(
        unique_dates[-12:]
    )

    core_df = available_history[
        ~available_history[DATE_COLUMN].isin(
            internal_dates
        )
    ].copy()

    validation_context = (
        available_history
        .copy()
    )

    # Core-only medians for internal model selection.
    core_medians, _ = fit_predictor_medians(
        core_df,
        HISTORICAL_PREDICTORS
    )

    core_df = apply_predictor_medians(
        core_df,
        HISTORICAL_PREDICTORS,
        core_medians
    )

    validation_context = apply_predictor_medians(
        validation_context,
        HISTORICAL_PREDICTORS,
        core_medians
    )

    core_dataset = build_training_dataset(
        core_df
    )

    min_internal_time_idx = int(
        validation_context[
            validation_context[DATE_COLUMN].isin(
                internal_dates
            )
        ]["Time_Index"].min()
    )

    validation_dataset = (
        TimeSeriesDataSet.from_dataset(
            core_dataset,
            validation_context,
            min_prediction_idx=
                min_internal_time_idx,
            stop_randomization=True,
        )
    )

    train_loader = core_dataset.to_dataloader(
        train=True,
        batch_size=BATCH_SIZE,
        num_workers=0,
    )

    validation_loader = (
        validation_dataset.to_dataloader(
            train=False,
            batch_size=BATCH_SIZE,
            num_workers=0,
        )
    )

    set_seed(
        RANDOM_STATE
        +
        origin_number
    )

    model = build_tft_model(
        core_dataset
    )

    origin_checkpoint_dir = (
        MODEL_DIR
        /
        "15b_tft_internal_checkpoints"
        /
        origin_date.strftime("%Y_%m")
    )

    origin_checkpoint_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    checkpoint_callback = ModelCheckpoint(
        dirpath=str(origin_checkpoint_dir),
        filename="tft-internal-{epoch:02d}-{val_loss:.4f}",
        monitor="val_loss",
        mode="min",
        save_top_k=1,
    )

    early_stopping = EarlyStopping(
        monitor="val_loss",
        min_delta=1e-4,
        patience=
            EARLY_STOPPING_PATIENCE,
        mode="min",
        verbose=False,
    )

    logger = CSVLogger(
        save_dir=str(LOG_DIR),
        name=(
            "internal_"
            +
            origin_date.strftime("%Y_%m")
        )
    )

    trainer = pl.Trainer(
        max_epochs=
            MAX_EPOCHS_INTERNAL,

        accelerator="cpu",
        devices=1,

        gradient_clip_val=0.1,

        callbacks=[
            checkpoint_callback,
            early_stopping
        ],

        logger=logger,

        enable_checkpointing=True,
        enable_model_summary=False,
        enable_progress_bar=False,
        deterministic=True,
    )

    trainer.fit(
        model,
        train_dataloaders=train_loader,
        val_dataloaders=validation_loader,
    )

    best_checkpoint_path = (
        checkpoint_callback
        .best_model_path
    )

    if best_checkpoint_path == "":
        raise RuntimeError(
            f"No internal TFT checkpoint was created for "
            f"origin {origin_date.date()}."
        )

    checkpoint_data = torch.load(
        best_checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    best_epoch = (
        int(
            checkpoint_data[
                "epoch"
            ]
        )
        +
        1
    )

    return best_epoch


# ============================================================
# 13. BUILD STRICT PREDICTION DATA
# ============================================================

def build_prediction_context(
    full_observed_history,
    training_dataset,
    origin_date,
    train_medians
):
    """
    Build one prediction window per currently active district/series.

    Encoder:
        actual observed history through the forecast origin.

    Decoder:
        six synthetic future rows.
        Only known calendar variables contain future information.
        Future-unknown predictors receive train-derived medians.
        Future target is a dummy placeholder and is not used as an input.
    """

    frames = []

    for district, district_df in full_observed_history.groupby(
        DISTRICT,
        sort=True
    ):
        district_df = (
            district_df[
                district_df[DATE_COLUMN]
                <=
                origin_date
            ]
            .copy()
            .sort_values(DATE_COLUMN)
        )

        if district_df.empty:
            continue

        # Use the latest continuous series segment active at origin.
        latest_row = district_df.iloc[-1]
        series_id = latest_row["Series_ID"]

        active_series = (
            district_df[
                district_df["Series_ID"]
                ==
                series_id
            ]
            .copy()
            .sort_values(DATE_COLUMN)
        )

        if len(active_series) < MAX_ENCODER_LENGTH:
            continue

        encoder = (
            active_series
            .tail(
                MAX_ENCODER_LENGTH
            )
            .copy()
        )

        # Require encoder to end exactly at origin.
        if (
            pd.Timestamp(
                encoder[DATE_COLUMN].max()
            )
            !=
            pd.Timestamp(
                origin_date
            )
        ):
            continue

        future_dates = pd.date_range(
            origin_date
            +
            pd.offsets.MonthBegin(1),
            periods=
                MAX_PREDICTION_LENGTH,
            freq="MS",
        )

        future = pd.DataFrame({
            DATE_COLUMN:
                future_dates,

            DISTRICT:
                str(district),

            "Series_ID":
                str(series_id),
        })

        future = add_calendar_features(
            future
        )

        # Decoder target is only a placeholder required by
        # TimeSeriesDataSet construction.
        future[TARGET] = 0.0

        # Future unknown predictors MUST NOT use observed future values.
        for column in HISTORICAL_PREDICTORS:
            future[column] = float(
                train_medians[column]
            )

        combined = pd.concat(
            [
                encoder,
                future
            ],
            ignore_index=True,
            sort=False,
        )

        # ----------------------------------------------------
        # IMPORTANT STRICT-ORIGIN IMPUTATION FIX
        # ----------------------------------------------------
        # The encoder can still contain historical predictor NaNs
        # (for example ALLSKY_KT). PyTorch Forecasting does not
        # allow NaN values in real-valued variables.
        #
        # Apply the medians learned ONLY from the history available
        # at this forecast origin to BOTH encoder and decoder rows.
        # This does not use any future information.
        combined = apply_predictor_medians(
            combined,
            HISTORICAL_PREDICTORS,
            train_medians,
        )

        frames.append(
            combined
        )

    if len(frames) == 0:
        raise ValueError(
            f"No TFT prediction contexts could be built for "
            f"{origin_date.date()}."
        )

    prediction_context = pd.concat(
        frames,
        ignore_index=True,
    )

    prediction_dataset = (
        TimeSeriesDataSet.from_dataset(
            training_dataset,
            prediction_context,
            predict=True,
            stop_randomization=True,
        )
    )

    return (
        prediction_context,
        prediction_dataset
    )


# ============================================================
# 14. PREDICTION OUTPUT HELPER
# ============================================================

def extract_prediction_object(
    prediction_result
):
    """
    Compatible handling for PyTorch Forecasting Prediction objects.
    """

    if hasattr(
        prediction_result,
        "output"
    ):
        output = prediction_result.output
    else:
        output = prediction_result[0]

    if hasattr(
        prediction_result,
        "index"
    ):
        index_df = prediction_result.index
    else:
        index_df = prediction_result[1]

    if torch.is_tensor(output):
        output = (
            output
            .detach()
            .cpu()
            .numpy()
        )
    else:
        output = np.asarray(
            output
        )

    index_df = pd.DataFrame(
        index_df
    ).copy()

    return output, index_df


# ============================================================
# 15. STRICT ROLLING-ORIGIN TFT
# ============================================================

origins = pd.date_range(
    FIRST_STRICT_ORIGIN,
    LAST_STRICT_ORIGIN,
    freq="MS",
)

all_prediction_records = []
training_summary_records = []

for origin_number, origin_date in enumerate(
    origins,
    start=1
):
    print("\n" + "-" * 120)
    print(
        f"TFT STRICT ORIGIN "
        f"{origin_number}/{len(origins)} "
        f"| {origin_date.date()}"
    )
    print("-" * 120)

    # --------------------------------------------------------
    # A. HISTORY AVAILABLE AT THIS ORIGIN
    # --------------------------------------------------------
    available_history = (
        observed_df[
            observed_df[DATE_COLUMN]
            <=
            origin_date
        ]
        .copy()
    )

    if available_history.empty:
        continue

    print(
        f"Available observed rows: "
        f"{len(available_history)}"
    )

    # --------------------------------------------------------
    # B. HISTORICAL-ONLY EPOCH SELECTION
    # --------------------------------------------------------
    selected_epoch = (
        select_epoch_historically(
            available_history,
            origin_date,
            origin_number,
        )
    )

    print(
        f"Selected historical epoch: "
        f"{selected_epoch}"
    )

    # --------------------------------------------------------
    # C. REFIT PREPROCESSING USING ALL HISTORY AT ORIGIN
    # --------------------------------------------------------
    train_medians, all_missing_predictors = (
        fit_predictor_medians(
            available_history,
            HISTORICAL_PREDICTORS,
        )
    )

    full_train = apply_predictor_medians(
        available_history,
        HISTORICAL_PREDICTORS,
        train_medians,
    )

    # --------------------------------------------------------
    # D. BUILD FULL TRAINING DATASET
    # --------------------------------------------------------
    full_training_dataset = (
        build_training_dataset(
            full_train
        )
    )

    full_train_loader = (
        full_training_dataset
        .to_dataloader(
            train=True,
            batch_size=BATCH_SIZE,
            num_workers=0,
        )
    )

    # --------------------------------------------------------
    # E. REFIT TFT FOR FIXED SELECTED EPOCH
    # --------------------------------------------------------
    set_seed(
        RANDOM_STATE
        +
        1000
        +
        origin_number
    )

    final_tft = TemporalFusionTransformer.from_dataset(
        full_training_dataset,

        learning_rate=
            TFT_LEARNING_RATE,

        hidden_size=
            TFT_HIDDEN_SIZE,

        attention_head_size=
            TFT_ATTENTION_HEAD_SIZE,

        dropout=
            TFT_DROPOUT,

        hidden_continuous_size=
            TFT_HIDDEN_CONTINUOUS_SIZE,

        output_size=
            len(QUANTILES),

        loss=
            QuantileLoss(
                quantiles=QUANTILES
            ),

        optimizer="adam",

        reduce_on_plateau_patience=1000,

        log_interval=-1,
    )

    final_logger = CSVLogger(
        save_dir=str(LOG_DIR),
        name=(
            "refit_"
            +
            origin_date.strftime("%Y_%m")
        )
    )

    # No validation-period decisions are made here.
    # selected_epoch is already determined using historical data.
    final_trainer = pl.Trainer(
        max_epochs=
            selected_epoch,

        accelerator="cpu",
        devices=1,

        gradient_clip_val=0.1,

        logger=
            final_logger,

        enable_checkpointing=False,
        enable_model_summary=False,
        enable_progress_bar=False,
        deterministic=True,
    )

    final_trainer.fit(
        final_tft,
        train_dataloaders=
            full_train_loader,
    )

    # --------------------------------------------------------
    # F. BUILD SIX-MONTH STRICT FUTURE WINDOW
    # --------------------------------------------------------
    (
        prediction_context,
        prediction_dataset
    ) = build_prediction_context(
        observed_df,
        full_training_dataset,
        origin_date,
        train_medians,
    )

    prediction_loader = (
        prediction_dataset
        .to_dataloader(
            train=False,
            batch_size=BATCH_SIZE,
            num_workers=0,
        )
    )

    # --------------------------------------------------------
    # G. QUANTILE FORECASTS
    # --------------------------------------------------------
    prediction_result = final_tft.predict(
        prediction_loader,
        mode="quantiles",
        return_index=True,
        trainer_kwargs={
            "accelerator": "cpu",
            "devices": 1,
            "enable_progress_bar": False,
            "logger": False,
        },
    )

    quantile_output, index_df = (
        extract_prediction_object(
            prediction_result
        )
    )

    # Expected:
    # [number_of_series, prediction_length, number_of_quantiles]
    if quantile_output.ndim != 3:
        raise ValueError(
            "Unexpected TFT quantile prediction shape: "
            f"{quantile_output.shape}"
        )

    # --------------------------------------------------------
    # H. MAP SERIES_ID TO DISTRICT
    # --------------------------------------------------------
    if "Series_ID" not in index_df.columns:
        raise KeyError(
            "Prediction index does not contain Series_ID."
        )

    series_to_district = (
        prediction_context[
            [
                "Series_ID",
                DISTRICT
            ]
        ]
        .drop_duplicates()
        .set_index(
            "Series_ID"
        )[DISTRICT]
        .to_dict()
    )

    # --------------------------------------------------------
    # I. STORE H1/H3/H6 2024 REQUESTS
    # --------------------------------------------------------
    for row_position in range(
        len(index_df)
    ):
        series_id = str(
            index_df.iloc[
                row_position
            ]["Series_ID"]
        )

        district = (
            series_to_district.get(
                series_id
            )
        )

        if district is None:
            continue

        for horizon in HORIZONS:
            target_date = (
                origin_date
                +
                pd.DateOffset(
                    months=horizon
                )
            )

            if not (
                VALIDATION_START
                <=
                target_date
                <=
                VALIDATION_END
            ):
                continue

            actual_rows = base_df[
                (base_df[DISTRICT].astype(str) == str(district))
                &
                (base_df[DATE_COLUMN] == target_date)
            ]

            if actual_rows.empty:
                continue

            actual = actual_rows.iloc[0][TARGET]

            if pd.isna(actual):
                continue

            q025 = float(
                quantile_output[
                    row_position,
                    horizon - 1,
                    0
                ]
            )

            q50 = float(
                quantile_output[
                    row_position,
                    horizon - 1,
                    1
                ]
            )

            q975 = float(
                quantile_output[
                    row_position,
                    horizon - 1,
                    2
                ]
            )

            all_prediction_records.append({
                "Model":
                    "TFT",

                "Horizon_Months":
                    horizon,

                "District":
                    district,

                "Forecast_Origin_Date":
                    origin_date,

                "Forecast_Target_Date":
                    target_date,

                "Actual_Target":
                    float(actual),

                "Prediction":
                    q50,

                "Lower_95":
                    q025,

                "Upper_95":
                    q975,

                "Covered_By_95":
                    bool(
                        float(actual)
                        >=
                        q025
                        and
                        float(actual)
                        <=
                        q975
                    ),

                "Interval_Width":
                    q975 - q025,

                "Pinball_Q025":
                    pinball_loss(
                        np.array(
                            [float(actual)]
                        ),
                        np.array(
                            [q025]
                        ),
                        0.025
                    ),

                "Pinball_Q50":
                    pinball_loss(
                        np.array(
                            [float(actual)]
                        ),
                        np.array(
                            [q50]
                        ),
                        0.50
                    ),

                "Pinball_Q975":
                    pinball_loss(
                        np.array(
                            [float(actual)]
                        ),
                        np.array(
                            [q975]
                        ),
                        0.975
                    ),

                "Quantile_Crossing":
                    int(
                        not (
                            q025
                            <=
                            q50
                            <=
                            q975
                        )
                    )
            })

    training_summary_records.append({
        "Forecast_Origin_Date":
            origin_date,

        "Training_Rows":
            len(full_train),

        "Training_Series":
            full_train[
                "Series_ID"
            ].nunique(),

        "Selected_Epoch":
            selected_epoch,

        "All_Missing_Predictors":
            ";".join(
                all_missing_predictors
            )
    })


# ============================================================
# 16. SAVE STRICT TFT PREDICTIONS
# ============================================================

prediction_df = pd.DataFrame(
    all_prediction_records
)

if prediction_df.empty:
    raise RuntimeError(
        "No strict TFT predictions were produced."
    )

prediction_df = (
    prediction_df
    .sort_values(
        [
            "Horizon_Months",
            "Forecast_Target_Date",
            "District"
        ]
    )
    .reset_index(drop=True)
)

prediction_path = (
    REPORT_DIR
    /
    "15b_tft_strict_predictions.csv"
)

prediction_df.to_csv(
    prediction_path,
    index=False
)

training_summary_df = pd.DataFrame(
    training_summary_records
)

training_summary_df.to_csv(
    REPORT_DIR
    /
    "15b_tft_training_summary.csv",
    index=False
)


# ============================================================
# 17. CALCULATE STRICT TFT METRICS
# ============================================================

metric_records = []

for horizon in HORIZONS:
    horizon_df = prediction_df[
        prediction_df[
            "Horizon_Months"
        ]
        ==
        horizon
    ].copy()

    valid_df = horizon_df[
        horizon_df[
            "Prediction"
        ].notna()
    ].copy()

    if valid_df.empty:
        metric_records.append({
            "Horizon_Months":
                horizon,

            "Model":
                "TFT",

            "Validation_Rows":
                0,

            "MAE":
                np.nan,

            "RMSE":
                np.nan,

            "WAPE_Percentage":
                np.nan,

            "sMAPE_Percentage":
                np.nan,

            "R2":
                np.nan,

            "Interval_Coverage_Percentage":
                np.nan,

            "Mean_Interval_Width":
                np.nan,

            "Mean_Pinball_Loss":
                np.nan,

            "Quantile_Crossings":
                np.nan,
        })

        continue

    y_true = (
        valid_df[
            "Actual_Target"
        ]
        .to_numpy(
            dtype=float
        )
    )

    y_pred = (
        valid_df[
            "Prediction"
        ]
        .to_numpy(
            dtype=float
        )
    )

    mean_pinball = float(
        valid_df[
            [
                "Pinball_Q025",
                "Pinball_Q50",
                "Pinball_Q975"
            ]
        ]
        .to_numpy()
        .mean()
    )

    metric_records.append({
        "Horizon_Months":
            horizon,

        "Model":
            "TFT",

        "Validation_Rows":
            len(valid_df),

        "MAE":
            calculate_mae(
                y_true,
                y_pred
            ),

        "RMSE":
            calculate_rmse(
                y_true,
                y_pred
            ),

        "WAPE_Percentage":
            calculate_wape(
                y_true,
                y_pred
            ),

        "sMAPE_Percentage":
            calculate_smape(
                y_true,
                y_pred
            ),

        "R2":
            calculate_r2(
                y_true,
                y_pred
            ),

        "Interval_Coverage_Percentage":
            float(
                valid_df[
                    "Covered_By_95"
                ]
                .mean()
                *
                100
            ),

        "Mean_Interval_Width":
            float(
                valid_df[
                    "Interval_Width"
                ]
                .mean()
            ),

        "Mean_Pinball_Loss":
            mean_pinball,

        "Quantile_Crossings":
            int(
                valid_df[
                    "Quantile_Crossing"
                ]
                .sum()
            ),
    })


metrics_df = pd.DataFrame(
    metric_records
)

metrics_path = (
    REPORT_DIR
    /
    "15b_tft_strict_metrics.csv"
)

metrics_df.to_csv(
    metrics_path,
    index=False
)


# ============================================================
# 18. PRINT RESULTS
# ============================================================

print("\n" + "=" * 120)
print("TFT STRICT ROLLING-ORIGIN VALIDATION RESULTS")
print("=" * 120)

print(
    metrics_df
    .round(4)
    .to_string(
        index=False
    )
)

print("\n" + "=" * 120)
print("STEP 15B SUMMARY")
print("=" * 120)

print("TFT strict rolling-origin revalidation completed.")
print("")
print("Leakage protection:")
print("- Each origin used only target history available by that origin")
print("- Predictor medians were re-fitted separately at each origin")
print("- Internal epoch selection used historical data only")
print("- Final TFT was refitted separately at each origin")
print("- Future-unknown variables were not supplied using observed future values")
print("- H1, H3 and H6 were evaluated only when the target date was in 2024")
print("- Hyperparameters were NOT tuned in Step 15B")
print("")
print("IMPORTANT:")
print("Do NOT choose the final model yet.")
print("Use Step 15 + Step 15B strict results before Step 16 tuning.")
print("")
print("Predictions saved to:")
print(prediction_path)
print("")
print("Metrics saved to:")
print(metrics_path)
print("")
print("STEP 15B - TFT STRICT ROLLING-ORIGIN REVALIDATION COMPLETE")
print("=" * 120)
