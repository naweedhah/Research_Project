# ============================================================
# STEP 16B - TFT TRAIN-ONLY TEMPORAL HYPERPARAMETER TUNING
# Childhood Malnutrition Forecasting Research
#
# PURPOSE
# -------
# Tune the Temporal Fusion Transformer (TFT) separately from the
# row-based regression models because TFT is a direct multi-horizon
# deep-learning model.
#
# STRICT TEMPORAL DESIGN
# ----------------------
# Historical tuning folds:
#
#   Fold 2021:
#       model fitting history <= 2020-12
#       forecast origins       = 2021-01 ... 2021-06
#       evaluated horizons     = H1, H3, H6
#
#   Fold 2022:
#       model fitting history <= 2021-12
#       forecast origins       = 2022-01 ... 2022-06
#
#   Fold 2023:
#       model fitting history <= 2022-12
#       forecast origins       = 2023-01 ... 2023-06
#
# Why Jan-Jun origins?
# - H6 from a June origin ends in December of the same fold year.
# - Therefore every evaluated target remains inside the historical
#   tuning fold.
#
# IMPORTANT
# ---------
# - 2024 is NOT loaded into this tuning script.
# - 2025 is NOT loaded into this tuning script.
# - Target values after each forecast origin are never supplied as
#   encoder history.
# - Future-unknown predictor values are never supplied using actual
#   future observations.
# - Predictor medians are fitted only from model-fitting history.
# - Epoch selection uses only an internal historical split contained
#   inside the model-fitting history.
# - One TFT configuration is selected globally because TFT forecasts
#   all horizons jointly.
# ============================================================

from pathlib import Path
import warnings
import random
import json

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
# 1. SETTINGS
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

TUNING_YEARS = [2021, 2022, 2023]

# We evaluate six monthly forecast origins per tuning year.
# This lets H6 remain within the same tuning year.
TUNING_ORIGIN_MONTHS = [1, 2, 3, 4, 5, 6]

BATCH_SIZE = 64

MAX_EPOCHS_INTERNAL = 50
EARLY_STOPPING_PATIENCE = 6

# ============================================================
# TFT SEARCH SPACE
# ============================================================
#
# TFT_BASE = exact initial candidate configuration used in Step 19
# and matched in corrected Step 15B.
#
# Other configurations are deliberately modest alternatives so the
# tuning search remains research-manageable and does not become an
# excessively large deep-learning search.
# ============================================================

TFT_CONFIGS = [
    {
        "Config_ID": "TFT_BASE",
        "learning_rate": 0.01,
        "hidden_size": 16,
        "attention_head_size": 2,
        "dropout": 0.10,
        "hidden_continuous_size": 8,
    },
    {
        "Config_ID": "TFT_A",
        "learning_rate": 0.005,
        "hidden_size": 16,
        "attention_head_size": 2,
        "dropout": 0.10,
        "hidden_continuous_size": 8,
    },
    {
        "Config_ID": "TFT_B",
        "learning_rate": 0.01,
        "hidden_size": 32,
        "attention_head_size": 4,
        "dropout": 0.10,
        "hidden_continuous_size": 16,
    },
    {
        "Config_ID": "TFT_C",
        "learning_rate": 0.005,
        "hidden_size": 32,
        "attention_head_size": 4,
        "dropout": 0.20,
        "hidden_continuous_size": 16,
    },
]


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
MODEL_DIR = BASE_DIR / "models" / "tuning" / "16b_tft"
LOG_DIR = BASE_DIR / "outputs" / "logs" / "16b_tft"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

BASE_DATA_PATH = (
    PROCESSED_DIR
    / "malnutrition_preprocessed_base.csv"
)


# ============================================================
# 4. METRICS
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
        np.sum(
            np.abs(
                y_true - y_pred
            )
        )
        /
        denominator
        *
        100
    )


def calculate_smape(y_true, y_pred):
    denominator = (
        np.abs(y_true)
        +
        np.abs(y_pred)
    )

    valid = denominator != 0

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
        1
        -
        ss_res
        /
        ss_tot
    )


def pinball_loss(y_true, y_pred, quantile):
    error = y_true - y_pred

    return float(
        np.mean(
            np.maximum(
                quantile * error,
                (quantile - 1) * error,
            )
        )
    )


# ============================================================
# 5. TFT-SAFE COLUMN NAMES
# ============================================================

def make_tft_safe_column_names(dataframe):
    rename_map = {}

    for column in dataframe.columns:
        rename_map[column] = (
            str(column)
            .replace(".", "_")
        )

    safe_names = list(
        rename_map.values()
    )

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

    return (
        dataframe.rename(
            columns=rename_map
        ),
        rename_map,
    )


# ============================================================
# 6. LOAD HISTORICAL DATA ONLY
# ============================================================

print("\n" + "=" * 120)
print("STEP 16B - TFT TRAIN-ONLY TEMPORAL HYPERPARAMETER TUNING")
print("=" * 120)

print("\nStrict design:")
print("- Historical tuning years: 2021, 2022, 2023")
print("- Each fold fits only on data before that tuning year")
print("- Origins January to June are evaluated")
print("- H1, H3 and H6 remain inside each tuning year")
print("- 2024 is NOT loaded")
print("- 2025 is NOT loaded")
print("- Future-unknown observed values are never used in decoder rows")

if not BASE_DATA_PATH.exists():
    raise FileNotFoundError(
        f"Base data file not found:\n{BASE_DATA_PATH}"
    )

base_df = pd.read_csv(
    BASE_DATA_PATH
)

base_df, COLUMN_RENAME_MAP = (
    make_tft_safe_column_names(
        base_df
    )
)

base_df[DATE_COLUMN] = pd.to_datetime(
    base_df[DATE_COLUMN]
)

# HARD LOCK: remove 2024 and 2025 before tuning.
base_df = (
    base_df[
        base_df[DATE_COLUMN]
        <
        pd.Timestamp("2024-01-01")
    ]
    .copy()
)

if base_df.empty:
    raise ValueError(
        "No historical rows are available before 2024."
    )

if (
    base_df[DATE_COLUMN].max()
    >=
    pd.Timestamp("2024-01-01")
):
    raise AssertionError(
        "2024+ data entered Step 16B."
    )

print(
    f"\nRows loaded through 2023 : "
    f"{len(base_df)}"
)

print(
    f"Date range               : "
    f"{base_df[DATE_COLUMN].min().date()} "
    f"to "
    f"{base_df[DATE_COLUMN].max().date()}"
)

print(
    f"Districts                : "
    f"{base_df[DISTRICT].nunique()}"
)


# ============================================================
# 7. IDENTIFY HISTORICAL NUMERIC PREDICTORS
# ============================================================

EXCLUDED_COLUMNS = {
    TARGET,
    DISTRICT,
    DATE_COLUMN,

    # These are calendar/metadata columns from the base table,
    # not historical unknown predictors. Step 19 uses the
    # dedicated TFT calendar variables instead.
    "Year",
    "Month",
}

HISTORICAL_PREDICTORS = []

for column in base_df.columns:

    if column in EXCLUDED_COLUMNS:
        continue

    converted = pd.to_numeric(
        base_df[column],
        errors="coerce"
    )

    if converted.notna().sum() > 0:
        base_df[column] = converted
        HISTORICAL_PREDICTORS.append(
            column
        )

print(
    f"Historical numeric predictors: "
    f"{len(HISTORICAL_PREDICTORS)}"
)

# Research consistency check:
# Step 19 / corrected Step 15B use exactly 35 historical
# numeric predictors. Stop immediately if the schema changes.
EXPECTED_HISTORICAL_PREDICTORS = 35

if len(HISTORICAL_PREDICTORS) != EXPECTED_HISTORICAL_PREDICTORS:
    raise ValueError(
        "TFT predictor-schema mismatch: expected "
        f"{EXPECTED_HISTORICAL_PREDICTORS} historical numeric "
        f"predictors, found {len(HISTORICAL_PREDICTORS)}. "
        "Do not continue until the TFT feature schema matches "
        "Step 19 / Step 15B."
    )


# ============================================================
# 8. CALENDAR FEATURES
# ============================================================

global_start_period = pd.Period(
    base_df[DATE_COLUMN].min(),
    freq="M",
)


def add_calendar_features(dataframe):
    df = dataframe.copy()

    period = (
        df[DATE_COLUMN]
        .dt
        .to_period("M")
    )

    df["Time_Index"] = (
        (
            period.dt.year
            -
            global_start_period.year
        )
        *
        12
        +
        (
            period.dt.month
            -
            global_start_period.month
        )
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
        2
        *
        np.pi
        *
        month_number
        /
        12.0
    )

    df["Month_Cos_TFT"] = np.cos(
        2
        *
        np.pi
        *
        month_number
        /
        12.0
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
# 9. BUILD CONTINUOUS TARGET SERIES SEGMENTS
# ============================================================

def assign_series_segments(dataframe):
    output_frames = []

    for district, district_df in dataframe.groupby(
        DISTRICT,
        sort=True,
    ):
        district_df = (
            district_df
            .sort_values(DATE_COLUMN)
            .copy()
        )

        observed = (
            district_df[
                district_df[TARGET].notna()
            ]
            .copy()
        )

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
            dtype=int,
        )

        current_segment = 1

        for i in range(
            1,
            len(observed),
        ):
            if (
                periods[i]
                -
                periods[i - 1]
                !=
                1
            ):
                current_segment += 1

            segment_numbers[i] = (
                current_segment
            )

        observed[
            "Segment_Number"
        ] = segment_numbers

        observed[
            "Series_ID"
        ] = (
            observed[DISTRICT].astype(str)
            +
            "__S"
            +
            observed[
                "Segment_Number"
            ].astype(str)
        )

        output_frames.append(
            observed
        )

    if len(output_frames) == 0:
        raise ValueError(
            "No continuous observed target series could be created."
        )

    result = pd.concat(
        output_frames,
        ignore_index=True,
    )

    result = (
        result
        .sort_values(
            [
                DISTRICT,
                DATE_COLUMN,
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return result


observed_df = assign_series_segments(
    base_df
)

print(
    f"Observed target rows       : "
    f"{len(observed_df)}"
)

print(
    f"Continuous TFT series     : "
    f"{observed_df['Series_ID'].nunique()}"
)


# ============================================================
# 10. ORIGIN/FOLD-SPECIFIC PREPROCESSING
# ============================================================

def fit_predictor_medians(
    dataframe,
    predictor_columns,
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

    return (
        medians,
        all_missing,
    )


def apply_predictor_medians(
    dataframe,
    predictor_columns,
    medians,
):
    result = dataframe.copy()

    for column in predictor_columns:
        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce",
            )
            .fillna(
                medians[column]
            )
            .astype(float)
        )

    return result


# ============================================================
# 11. TFT DATASET BUILDER
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
    dataframe,
):
    return TimeSeriesDataSet(
        dataframe,
        time_idx="Time_Index",
        target=TARGET,

        group_ids=[
            DISTRICT,
            "Series_ID",
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
                ),
        },

        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
        allow_missing_timesteps=False,
    )


# ============================================================
# 12. TFT MODEL BUILDER
# ============================================================

def build_tft_model(
    dataset,
    config,
    plateau_patience=4,
):
    return TemporalFusionTransformer.from_dataset(
        dataset,

        learning_rate=
            config[
                "learning_rate"
            ],

        hidden_size=
            config[
                "hidden_size"
            ],

        attention_head_size=
            config[
                "attention_head_size"
            ],

        dropout=
            config[
                "dropout"
            ],

        hidden_continuous_size=
            config[
                "hidden_continuous_size"
            ],

        output_size=
            len(QUANTILES),

        loss=
            QuantileLoss(
                quantiles=QUANTILES
            ),

        optimizer="adam",

        reduce_on_plateau_patience=
            plateau_patience,

        log_interval=-1,
        log_val_interval=-1,
    )


# ============================================================
# 13. HISTORICAL-ONLY EPOCH SELECTION
# ============================================================

def select_epoch_historically(
    fitting_history,
    config,
    fold_year,
    config_number,
):
    """
    Select the number of epochs using only data that is already
    inside the historical model-fitting period.

    The final 12 available historical months are used as an
    internal validation block. They are NOT part of the external
    tuning-year evaluation.
    """

    unique_dates = (
        fitting_history[
            DATE_COLUMN
        ]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    if len(unique_dates) < 36:
        raise ValueError(
            f"Not enough historical months for internal validation "
            f"before tuning year {fold_year}."
        )

    internal_dates = set(
        unique_dates[-12:]
    )

    core_df = (
        fitting_history[
            ~fitting_history[
                DATE_COLUMN
            ]
            .isin(
                internal_dates
            )
        ]
        .copy()
    )

    validation_context = (
        fitting_history
        .copy()
    )

    core_medians, _ = (
        fit_predictor_medians(
            core_df,
            HISTORICAL_PREDICTORS,
        )
    )

    core_df = (
        apply_predictor_medians(
            core_df,
            HISTORICAL_PREDICTORS,
            core_medians,
        )
    )

    validation_context = (
        apply_predictor_medians(
            validation_context,
            HISTORICAL_PREDICTORS,
            core_medians,
        )
    )

    core_dataset = (
        build_training_dataset(
            core_df
        )
    )

    min_internal_time_idx = int(
        validation_context[
            validation_context[
                DATE_COLUMN
            ]
            .isin(
                internal_dates
            )
        ][
            "Time_Index"
        ]
        .min()
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

    train_loader = (
        core_dataset
        .to_dataloader(
            train=True,
            batch_size=BATCH_SIZE,
            num_workers=0,
        )
    )

    validation_loader = (
        validation_dataset
        .to_dataloader(
            train=False,
            batch_size=BATCH_SIZE,
            num_workers=0,
        )
    )

    seed = (
        RANDOM_STATE
        +
        fold_year
        +
        100
        *
        config_number
    )

    set_seed(
        seed
    )

    model = build_tft_model(
        core_dataset,
        config,
        plateau_patience=4,
    )

    checkpoint_dir = (
        MODEL_DIR
        /
        "internal_checkpoints"
        /
        config[
            "Config_ID"
        ]
        /
        str(
            fold_year
        )
    )

    checkpoint_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint_callback = (
        ModelCheckpoint(
            dirpath=
                str(
                    checkpoint_dir
                ),

            filename=
                "tft-{epoch:02d}-{val_loss:.4f}",

            monitor=
                "val_loss",

            mode=
                "min",

            save_top_k=1,
        )
    )

    early_stopping = (
        EarlyStopping(
            monitor=
                "val_loss",

            min_delta=
                1e-4,

            patience=
                EARLY_STOPPING_PATIENCE,

            mode=
                "min",

            verbose=False,
        )
    )

    logger = CSVLogger(
        save_dir=
            str(
                LOG_DIR
            ),

        name=(
            "internal_"
            +
            config[
                "Config_ID"
            ]
            +
            "_"
            +
            str(
                fold_year
            )
        ),
    )

    trainer = pl.Trainer(
        max_epochs=
            MAX_EPOCHS_INTERNAL,

        accelerator=
            "cpu",

        devices=1,

        gradient_clip_val=
            0.1,

        callbacks=[
            checkpoint_callback,
            early_stopping,
        ],

        logger=
            logger,

        enable_checkpointing=
            True,

        enable_model_summary=
            False,

        enable_progress_bar=
            False,

        deterministic=
            True,
    )

    trainer.fit(
        model,
        train_dataloaders=
            train_loader,
        val_dataloaders=
            validation_loader,
    )

    best_path = (
        checkpoint_callback
        .best_model_path
    )

    if best_path == "":
        raise RuntimeError(
            f"No TFT checkpoint for "
            f"{config['Config_ID']} / {fold_year}."
        )

    checkpoint_data = torch.load(
        best_path,
        map_location="cpu",
        weights_only=False,
    )

    return (
        int(
            checkpoint_data[
                "epoch"
            ]
        )
        +
        1
    )


# ============================================================
# 14. BUILD STRICT PREDICTION CONTEXT
# ============================================================

def build_prediction_context(
    all_observed_history,
    training_dataset,
    origin_date,
    train_medians,
):
    frames = []

    for district, district_df in (
        all_observed_history.groupby(
            DISTRICT,
            sort=True,
        )
    ):
        district_df = (
            district_df[
                district_df[
                    DATE_COLUMN
                ]
                <=
                origin_date
            ]
            .copy()
            .sort_values(
                DATE_COLUMN
            )
        )

        if district_df.empty:
            continue

        latest_row = (
            district_df
            .iloc[-1]
        )

        series_id = (
            latest_row[
                "Series_ID"
            ]
        )

        active_series = (
            district_df[
                district_df[
                    "Series_ID"
                ]
                ==
                series_id
            ]
            .copy()
            .sort_values(
                DATE_COLUMN
            )
        )

        if (
            len(
                active_series
            )
            <
            MAX_ENCODER_LENGTH
        ):
            continue

        encoder = (
            active_series
            .tail(
                MAX_ENCODER_LENGTH
            )
            .copy()
        )

        if (
            pd.Timestamp(
                encoder[
                    DATE_COLUMN
                ]
                .max()
            )
            !=
            pd.Timestamp(
                origin_date
            )
        ):
            continue

        future_dates = (
            pd.date_range(
                origin_date
                +
                pd.offsets.MonthBegin(1),

                periods=
                    MAX_PREDICTION_LENGTH,

                freq="MS",
            )
        )

        future = pd.DataFrame({
            DATE_COLUMN:
                future_dates,

            DISTRICT:
                str(
                    district
                ),

            "Series_ID":
                str(
                    series_id
                ),
        })

        future = (
            add_calendar_features(
                future
            )
        )

        # Dummy placeholder only.
        future[TARGET] = 0.0

        # NEVER insert actual future unknown predictors.
        for column in HISTORICAL_PREDICTORS:
            future[column] = float(
                train_medians[
                    column
                ]
            )

        combined = pd.concat(
            [
                encoder,
                future,
            ],
            ignore_index=True,
            sort=False,
        )

        combined = (
            apply_predictor_medians(
                combined,
                HISTORICAL_PREDICTORS,
                train_medians,
            )
        )

        frames.append(
            combined
        )

    if len(frames) == 0:
        raise ValueError(
            f"No TFT prediction contexts for "
            f"{origin_date.date()}."
        )

    prediction_context = (
        pd.concat(
            frames,
            ignore_index=True,
        )
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
        prediction_dataset,
    )


# ============================================================
# 15. PREDICTION OUTPUT HELPER
# ============================================================

def extract_prediction_object(
    prediction_result,
):
    if hasattr(
        prediction_result,
        "output",
    ):
        output = (
            prediction_result
            .output
        )
    else:
        output = (
            prediction_result[0]
        )

    if hasattr(
        prediction_result,
        "index",
    ):
        index_df = (
            prediction_result
            .index
        )
    else:
        index_df = (
            prediction_result[1]
        )

    if torch.is_tensor(
        output
    ):
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

    index_df = (
        pd.DataFrame(
            index_df
        )
        .copy()
    )

    return (
        output,
        index_df,
    )


# ============================================================
# 16. RUN TFT TEMPORAL TUNING
# ============================================================

all_prediction_records = []
fold_training_records = []

for config_number, config in enumerate(
    TFT_CONFIGS,
    start=1,
):

    print("\n" + "=" * 120)
    print(
        f"TFT CONFIG "
        f"{config_number}/{len(TFT_CONFIGS)} "
        f"| {config['Config_ID']}"
    )
    print("=" * 120)

    print(
        json.dumps(
            config,
            indent=2,
        )
    )

    for fold_number, fold_year in enumerate(
        TUNING_YEARS,
        start=1,
    ):

        print("\n" + "-" * 120)
        print(
            f"{config['Config_ID']} "
            f"| TEMPORAL FOLD "
            f"{fold_number}/{len(TUNING_YEARS)} "
            f"| {fold_year}"
        )
        print("-" * 120)

        train_cutoff = (
            pd.Timestamp(
                year=
                    fold_year - 1,
                month=12,
                day=1,
            )
        )

        fitting_history = (
            observed_df[
                observed_df[
                    DATE_COLUMN
                ]
                <=
                train_cutoff
            ]
            .copy()
        )

        if fitting_history.empty:
            raise ValueError(
                f"No fitting history before {fold_year}."
            )

        print(
            f"Training cutoff        : "
            f"{train_cutoff.date()}"
        )

        print(
            f"Observed training rows : "
            f"{len(fitting_history)}"
        )

        # ----------------------------------------------------
        # A. HISTORICAL-ONLY EPOCH SELECTION
        # ----------------------------------------------------

        selected_epoch = (
            select_epoch_historically(
                fitting_history,
                config,
                fold_year,
                config_number,
            )
        )

        print(
            f"Selected epoch         : "
            f"{selected_epoch}"
        )

        # ----------------------------------------------------
        # B. FIT FOLD PREPROCESSING
        # ----------------------------------------------------

        train_medians, all_missing = (
            fit_predictor_medians(
                fitting_history,
                HISTORICAL_PREDICTORS,
            )
        )

        full_train = (
            apply_predictor_medians(
                fitting_history,
                HISTORICAL_PREDICTORS,
                train_medians,
            )
        )

        full_dataset = (
            build_training_dataset(
                full_train
            )
        )

        full_loader = (
            full_dataset
            .to_dataloader(
                train=True,
                batch_size=BATCH_SIZE,
                num_workers=0,
            )
        )

        # ----------------------------------------------------
        # C. REFIT TFT ON FULL FOLD HISTORY
        # ----------------------------------------------------

        set_seed(
            RANDOM_STATE
            +
            10000
            +
            100
            *
            config_number
            +
            fold_number
        )

        final_tft = build_tft_model(
            full_dataset,
            config,
            plateau_patience=1000,
        )

        logger = CSVLogger(
            save_dir=
                str(
                    LOG_DIR
                ),

            name=(
                "refit_"
                +
                config[
                    "Config_ID"
                ]
                +
                "_"
                +
                str(
                    fold_year
                )
            ),
        )

        trainer = pl.Trainer(
            max_epochs=
                selected_epoch,

            accelerator=
                "cpu",

            devices=1,

            gradient_clip_val=
                0.1,

            logger=
                logger,

            enable_checkpointing=
                False,

            enable_model_summary=
                False,

            enable_progress_bar=
                False,

            deterministic=
                True,
        )

        trainer.fit(
            final_tft,
            train_dataloaders=
                full_loader,
        )

        # ----------------------------------------------------
        # D. SIX STRICT ORIGINS INSIDE THE FOLD YEAR
        # ----------------------------------------------------

        fold_origins = [
            pd.Timestamp(
                year=
                    fold_year,
                month=
                    month,
                day=1,
            )
            for month
            in TUNING_ORIGIN_MONTHS
        ]

        for origin_number, origin_date in enumerate(
            fold_origins,
            start=1,
        ):

            print(
                f"  Origin "
                f"{origin_number}/{len(fold_origins)} "
                f"| {origin_date.date()}"
            )

            (
                prediction_context,
                prediction_dataset,
            ) = build_prediction_context(
                observed_df,
                full_dataset,
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

            prediction_result = (
                final_tft.predict(
                    prediction_loader,
                    mode="quantiles",
                    return_index=True,
                    trainer_kwargs={
                        "accelerator":
                            "cpu",

                        "devices":
                            1,

                        "enable_progress_bar":
                            False,

                        "logger":
                            False,
                    },
                )
            )

            (
                quantile_output,
                index_df,
            ) = extract_prediction_object(
                prediction_result
            )

            if quantile_output.ndim != 3:
                raise ValueError(
                    "Unexpected TFT quantile output shape: "
                    f"{quantile_output.shape}"
                )

            if (
                "Series_ID"
                not in
                index_df.columns
            ):
                raise KeyError(
                    "Prediction index does not contain Series_ID."
                )

            series_to_district = (
                prediction_context[
                    [
                        "Series_ID",
                        DISTRICT,
                    ]
                ]
                .drop_duplicates()
                .set_index(
                    "Series_ID"
                )[DISTRICT]
                .to_dict()
            )

            for row_position in range(
                len(
                    index_df
                )
            ):

                series_id = str(
                    index_df.iloc[
                        row_position
                    ][
                        "Series_ID"
                    ]
                )

                district = (
                    series_to_district
                    .get(
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
                            months=
                                horizon
                        )
                    )

                    # Every tuning target must stay in the
                    # same historical fold year.
                    if (
                        target_date.year
                        !=
                        fold_year
                    ):
                        continue

                    actual_rows = (
                        base_df[
                            (
                                base_df[
                                    DISTRICT
                                ]
                                .astype(str)
                                ==
                                str(
                                    district
                                )
                            )
                            &
                            (
                                base_df[
                                    DATE_COLUMN
                                ]
                                ==
                                target_date
                            )
                        ]
                    )

                    if actual_rows.empty:
                        continue

                    actual = (
                        actual_rows
                        .iloc[0][TARGET]
                    )

                    if pd.isna(
                        actual
                    ):
                        continue

                    q025 = float(
                        quantile_output[
                            row_position,
                            horizon - 1,
                            0,
                        ]
                    )

                    q50 = float(
                        quantile_output[
                            row_position,
                            horizon - 1,
                            1,
                        ]
                    )

                    q975 = float(
                        quantile_output[
                            row_position,
                            horizon - 1,
                            2,
                        ]
                    )

                    all_prediction_records.append({
                        "Model":
                            "TFT",

                        "Config_ID":
                            config[
                                "Config_ID"
                            ],

                        "Tuning_Year":
                            fold_year,

                        "Horizon_Months":
                            horizon,

                        "District":
                            district,

                        "Forecast_Origin_Date":
                            origin_date,

                        "Forecast_Target_Date":
                            target_date,

                        "Actual_Target":
                            float(
                                actual
                            ),

                        "Prediction":
                            q50,

                        "Lower_95":
                            q025,

                        "Upper_95":
                            q975,

                        "Covered_By_95":
                            bool(
                                q025
                                <=
                                float(
                                    actual
                                )
                                <=
                                q975
                            ),

                        "Interval_Width":
                            q975
                            -
                            q025,

                        "Pinball_Q025":
                            pinball_loss(
                                np.array(
                                    [
                                        float(
                                            actual
                                        )
                                    ]
                                ),
                                np.array(
                                    [
                                        q025
                                    ]
                                ),
                                0.025,
                            ),

                        "Pinball_Q50":
                            pinball_loss(
                                np.array(
                                    [
                                        float(
                                            actual
                                        )
                                    ]
                                ),
                                np.array(
                                    [
                                        q50
                                    ]
                                ),
                                0.50,
                            ),

                        "Pinball_Q975":
                            pinball_loss(
                                np.array(
                                    [
                                        float(
                                            actual
                                        )
                                    ]
                                ),
                                np.array(
                                    [
                                        q975
                                    ]
                                ),
                                0.975,
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
                            ),
                    })

        fold_training_records.append({
            "Config_ID":
                config[
                    "Config_ID"
                ],

            "Tuning_Year":
                fold_year,

            "Training_Cutoff":
                train_cutoff,

            "Training_Rows":
                len(
                    full_train
                ),

            "Training_Series":
                full_train[
                    "Series_ID"
                ]
                .nunique(),

            "Selected_Epoch":
                selected_epoch,

            "All_Missing_Predictors":
                ";".join(
                    all_missing
                ),
        })


# ============================================================
# 17. SAVE RAW TUNING PREDICTIONS
# ============================================================

prediction_df = pd.DataFrame(
    all_prediction_records
)

if prediction_df.empty:
    raise RuntimeError(
        "No TFT tuning predictions were produced."
    )

prediction_df = (
    prediction_df
    .sort_values(
        [
            "Config_ID",
            "Tuning_Year",
            "Horizon_Months",
            "Forecast_Target_Date",
            "District",
        ]
    )
    .reset_index(
        drop=True
    )
)

prediction_path = (
    REPORT_DIR
    /
    "16b_tft_temporal_tuning_predictions.csv"
)

prediction_df.to_csv(
    prediction_path,
    index=False,
)

training_summary_df = pd.DataFrame(
    fold_training_records
)

training_summary_path = (
    REPORT_DIR
    /
    "16b_tft_temporal_tuning_training_summary.csv"
)

training_summary_df.to_csv(
    training_summary_path,
    index=False,
)


# ============================================================
# 18. FOLD/HORIZON METRICS
# ============================================================

metric_records = []

for config in TFT_CONFIGS:

    config_id = (
        config[
            "Config_ID"
        ]
    )

    for tuning_year in TUNING_YEARS:

        for horizon in HORIZONS:

            subset = (
                prediction_df[
                    (
                        prediction_df[
                            "Config_ID"
                        ]
                        ==
                        config_id
                    )
                    &
                    (
                        prediction_df[
                            "Tuning_Year"
                        ]
                        ==
                        tuning_year
                    )
                    &
                    (
                        prediction_df[
                            "Horizon_Months"
                        ]
                        ==
                        horizon
                    )
                ]
                .copy()
            )

            if subset.empty:
                continue

            y_true = (
                subset[
                    "Actual_Target"
                ]
                .to_numpy(
                    dtype=float
                )
            )

            y_pred = (
                subset[
                    "Prediction"
                ]
                .to_numpy(
                    dtype=float
                )
            )

            mean_pinball = float(
                subset[
                    [
                        "Pinball_Q025",
                        "Pinball_Q50",
                        "Pinball_Q975",
                    ]
                ]
                .to_numpy(
                    dtype=float
                )
                .mean()
            )

            metric_records.append({
                "Config_ID":
                    config_id,

                "Tuning_Year":
                    tuning_year,

                "Horizon_Months":
                    horizon,

                "Rows":
                    len(
                        subset
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

                "Interval_Coverage_Percentage":
                    float(
                        subset[
                            "Covered_By_95"
                        ]
                        .mean()
                        *
                        100
                    ),

                "Mean_Interval_Width":
                    float(
                        subset[
                            "Interval_Width"
                        ]
                        .mean()
                    ),

                "Mean_Pinball_Loss":
                    mean_pinball,

                "Quantile_Crossings":
                    int(
                        subset[
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
    "16b_tft_temporal_tuning_fold_metrics.csv"
)

metrics_df.to_csv(
    metrics_path,
    index=False,
)


# ============================================================
# 19. CONFIGURATION SUMMARY
# ============================================================

summary_df = (
    metrics_df
    .groupby(
        "Config_ID"
    )
    .agg(
        Mean_MAE=(
            "MAE",
            "mean"
        ),

        SD_MAE=(
            "MAE",
            "std"
        ),

        Mean_RMSE=(
            "RMSE",
            "mean"
        ),

        Mean_WAPE=(
            "WAPE_Percentage",
            "mean"
        ),

        Mean_sMAPE=(
            "sMAPE_Percentage",
            "mean"
        ),

        Mean_R2=(
            "R2",
            "mean"
        ),

        Mean_95_Coverage=(
            "Interval_Coverage_Percentage",
            "mean"
        ),

        Mean_Interval_Width=(
            "Mean_Interval_Width",
            "mean"
        ),

        Mean_Pinball_Loss=(
            "Mean_Pinball_Loss",
            "mean"
        ),

        Total_Quantile_Crossings=(
            "Quantile_Crossings",
            "sum"
        ),
    )
    .reset_index()
    .sort_values(
        [
            "Mean_MAE",
            "Mean_RMSE",
        ]
    )
    .reset_index(
        drop=True
    )
)

summary_path = (
    REPORT_DIR
    /
    "16b_tft_temporal_tuning_summary.csv"
)

summary_df.to_csv(
    summary_path,
    index=False,
)


# ============================================================
# 20. HORIZON-SPECIFIC SUMMARY
# ============================================================

horizon_summary_df = (
    metrics_df
    .groupby(
        [
            "Config_ID",
            "Horizon_Months",
        ]
    )
    .agg(
        Mean_MAE=(
            "MAE",
            "mean"
        ),

        Mean_RMSE=(
            "RMSE",
            "mean"
        ),

        Mean_WAPE=(
            "WAPE_Percentage",
            "mean"
        ),

        Mean_sMAPE=(
            "sMAPE_Percentage",
            "mean"
        ),

        Mean_R2=(
            "R2",
            "mean"
        ),

        Mean_95_Coverage=(
            "Interval_Coverage_Percentage",
            "mean"
        ),

        Mean_Interval_Width=(
            "Mean_Interval_Width",
            "mean"
        ),

        Mean_Pinball_Loss=(
            "Mean_Pinball_Loss",
            "mean"
        ),
    )
    .reset_index()
    .sort_values(
        [
            "Horizon_Months",
            "Mean_MAE",
        ]
    )
)

horizon_summary_df.to_csv(
    REPORT_DIR
    /
    "16b_tft_temporal_tuning_horizon_summary.csv",
    index=False,
)


# ============================================================
# 21. SELECT ONE GLOBAL TFT CONFIGURATION
# ============================================================

best_row = (
    summary_df
    .iloc[0]
)

best_config_id = (
    best_row[
        "Config_ID"
    ]
)

best_config = next(
    config
    for config
    in TFT_CONFIGS
    if config[
        "Config_ID"
    ]
    ==
    best_config_id
)

selected_df = pd.DataFrame([
    {
        "Model":
            "TFT",

        "Config_ID":
            best_config_id,

        "Selection_Rule":
            "Lowest mean historical MAE across 2021-2023 and H1/H3/H6; RMSE secondary",

        "Mean_Tuning_MAE":
            best_row[
                "Mean_MAE"
            ],

        "Mean_Tuning_RMSE":
            best_row[
                "Mean_RMSE"
            ],

        "Mean_Tuning_WAPE":
            best_row[
                "Mean_WAPE"
            ],

        "Mean_Tuning_R2":
            best_row[
                "Mean_R2"
            ],

        "Mean_95_Coverage":
            best_row[
                "Mean_95_Coverage"
            ],

        "Mean_Pinball_Loss":
            best_row[
                "Mean_Pinball_Loss"
            ],

        "Selected_Parameters":
            json.dumps(
                best_config
            ),
    }
])

selected_path = (
    REPORT_DIR
    /
    "16b_tft_selected_hyperparameters.csv"
)

selected_df.to_csv(
    selected_path,
    index=False,
)


# ============================================================
# 22. PRINT FINAL RESULTS
# ============================================================

print("\n" + "=" * 120)
print("TFT TEMPORAL TUNING - HORIZON SUMMARY")
print("=" * 120)

print(
    horizon_summary_df
    .round(4)
    .to_string(
        index=False
    )
)

print("\n" + "=" * 120)
print("TFT TEMPORAL TUNING - CONFIGURATION SUMMARY")
print("=" * 120)

print(
    summary_df
    .round(4)
    .to_string(
        index=False
    )
)

print("\n" + "=" * 120)
print("SELECTED TFT HYPERPARAMETERS")
print("=" * 120)

print(
    selected_df
    .round(4)
    .to_string(
        index=False
    )
)


# ============================================================
# 23. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 120)
print("STEP 16B SUMMARY")
print("=" * 120)

print(
    "TFT train-only temporal hyperparameter tuning completed."
)

print("\nLeakage protection:")
print("- 2024 was NOT loaded")
print("- 2025 was NOT loaded")
print("- Each tuning fold fit the model only on earlier years")
print("- Internal epoch selection used only earlier historical data")
print("- Decoder future-unknown variables used train-derived medians")
print("- Actual target history was available only through each origin")

print("\nSelection:")
print(
    f"- Selected TFT configuration: "
    f"{best_config_id}"
)
print(
    "- One global TFT configuration was selected because "
    "TFT jointly forecasts H1/H3/H6."
)

print("\nNEXT STEP:")
print(
    "Update Step 17 to revalidate RF/XGBoost/LightGBM/NGBoost "
    "selected in Step 16 and the selected TFT configuration "
    "on untouched 2024 validation."
)

print("\nPredictions saved to:")
print(
    prediction_path
)

print("\nFold metrics saved to:")
print(
    metrics_path
)

print("\nConfiguration summary saved to:")
print(
    summary_path
)

print("\nSelected TFT parameters saved to:")
print(
    selected_path
)

print("\nSTEP 16B - TFT TEMPORAL HYPERPARAMETER TUNING COMPLETE")
print("=" * 120)
