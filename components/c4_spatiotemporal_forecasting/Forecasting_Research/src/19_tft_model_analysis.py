# ============================================================
# STEP 19 - TEMPORAL FUSION TRANSFORMER (TFT) MODEL ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# INITIAL CANDIDATE MODEL - NOT TUNED YET
#
# Core train       : 2015-2022
# Internal val     : 2023
# Final refit      : 2015-2023
# External val     : 2024
# Final test 2025  : NOT USED
#
# Encoder history  : 12 months
# Forecast horizon : up to 6 months
# Report horizons  : H1, H3, H6
# ============================================================


from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import torch

from lightning.pytorch import (
    Trainer,
    seed_everything
)

from lightning.pytorch.callbacks import (
    EarlyStopping,
    ModelCheckpoint
)

from pytorch_forecasting import (
    TimeSeriesDataSet,
    TemporalFusionTransformer
)

from pytorch_forecasting.data import (
    GroupNormalizer,
    NaNLabelEncoder
)

from pytorch_forecasting.metrics import (
    QuantileLoss
)


warnings.filterwarnings("ignore")


# ============================================================
# 1. SETTINGS
# ============================================================

RANDOM_STATE = 42


MAX_ENCODER_LENGTH = 12

MAX_PREDICTION_LENGTH = 6


HORIZONS = [
    1,
    3,
    6
]


QUANTILES = [
    0.025,
    0.50,
    0.975
]


BATCH_SIZE = 64

MAX_EPOCHS = 50


LEARNING_RATE = 0.01

HIDDEN_SIZE = 16

ATTENTION_HEAD_SIZE = 2

HIDDEN_CONTINUOUS_SIZE = 8

DROPOUT = 0.10


TARGET = "Malnutrition_Cases"

DISTRICT = "District"

DATE = "Date"

TIME_INDEX = "Time_Index"

SERIES_ID = "Series_ID"

MONTH_CAT = "Month_Cat"


seed_everything(
    RANDOM_STATE,
    workers=True
)


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = (

    Path(__file__)
    .resolve()
    .parent
    .parent
)


TFT_DATA_DIR = (

    BASE_DIR
    / "data"
    / "model_ready"
    / "tft"
)


REPORT_DIR = (

    BASE_DIR
    / "outputs"
    / "reports"
)


MODEL_DIR = (

    BASE_DIR
    / "models"
    / "candidates"
)


CHECKPOINT_DIR = (

    MODEL_DIR
    / "tft_internal_checkpoints"
)


REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


CHECKPOINT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


CORE_TRAIN_PATH = (

    TFT_DATA_DIR
    / "18_tft_core_train_2015_2022.csv"
)


FULL_TRAIN_PATH = (

    TFT_DATA_DIR
    / "18_tft_full_train_2015_2023.csv"
)


INTERNAL_CONTEXT_PATH = (

    TFT_DATA_DIR
    / "18_tft_internal_validation_context_through_2023.csv"
)


EXTERNAL_CONTEXT_PATH = (

    TFT_DATA_DIR
    / "18_tft_external_validation_context_through_2024.csv"
)


# ============================================================
# 3. INTRODUCTION
# ============================================================

print(
    "\n"
    +
    "=" * 115
)


print(
    "STEP 19 - TEMPORAL FUSION TRANSFORMER MODEL ANALYSIS"
)


print(
    "=" * 115
)


print(
    "\nTraining strategy:"
)


print(
    "- Core model training: 2015-2022"
)


print(
    "- 2023 used for INTERNAL epoch selection only"
)


print(
    "- Final TFT refitted using 2015-2023"
)


print(
    "- 2024 used for EXTERNAL validation"
)


print(
    "- 2025 final test data is NOT loaded"
)


print(
    "- One multi-horizon TFT model forecasts up to 6 months"
)


print(
    "- H1, H3 and H6 evaluated separately"
)


print(
    "- Hyperparameter tuning is NOT performed yet"
)


# ============================================================
# 4. REQUIRED FILE CHECK
# ============================================================

required_files = [

    CORE_TRAIN_PATH,

    FULL_TRAIN_PATH,

    INTERNAL_CONTEXT_PATH,

    EXTERNAL_CONTEXT_PATH
]


for file_path in required_files:

    if not file_path.exists():

        raise FileNotFoundError(

            f"Required TFT file not found:\n"
            f"{file_path}"
        )


# ============================================================
# 5. LOAD DATA
# ============================================================

core_train = pd.read_csv(
    CORE_TRAIN_PATH
)


full_train = pd.read_csv(
    FULL_TRAIN_PATH
)


internal_context = pd.read_csv(
    INTERNAL_CONTEXT_PATH
)


external_context = pd.read_csv(
    EXTERNAL_CONTEXT_PATH
)


for dataframe in [

    core_train,

    full_train,

    internal_context,

    external_context

]:

    dataframe[
        DATE
    ] = pd.to_datetime(

        dataframe[
            DATE
        ]
    )


print(
    "\n"
    +
    "-" * 115
)


print(
    "1. LOAD TFT MODEL-READY DATA"
)


print(
    "-" * 115
)


print(
    f"Core train rows       : "
    f"{len(core_train)}"
)


print(
    f"Full train rows       : "
    f"{len(full_train)}"
)


print(
    f"Internal context rows : "
    f"{len(internal_context)}"
)


print(
    f"External context rows : "
    f"{len(external_context)}"
)


print(
    f"Districts             : "
    f"{full_train[DISTRICT].nunique()}"
)


print(
    f"Series segments       : "
    f"{full_train[SERIES_ID].nunique()}"
)


# ============================================================
# 6. SAFETY CHECKS
# ============================================================

if (

    full_train[
        DATE
    ].max()

    >
    pd.Timestamp(
        "2023-12-01"
    )
):

    raise ValueError(

        "2024 entered full TFT training data."
    )


if (

    external_context[
        DATE
    ].max()

    >
    pd.Timestamp(
        "2024-12-01"
    )
):

    raise ValueError(

        "2025 entered TFT development data."
    )


if core_train[
    TARGET
].isna().any():

    raise ValueError(

        "Missing targets detected in "
        "core training data."
    )


if full_train[
    TARGET
].isna().any():

    raise ValueError(

        "Missing targets detected in "
        "full training data."
    )


print(
    "\n2025 leakage check: PASS"
)


print(
    "Target missing-value check: PASS"
)


# ============================================================
# 7. DATA TYPE PREPARATION
# ============================================================

for dataframe in [

    core_train,

    full_train,

    internal_context,

    external_context

]:

    dataframe[
        DISTRICT
    ] = (

        dataframe[
            DISTRICT
        ]
        .astype(str)
    )


    dataframe[
        SERIES_ID
    ] = (

        dataframe[
            SERIES_ID
        ]
        .astype(str)
    )


    dataframe[
        MONTH_CAT
    ] = (

        dataframe[
            MONTH_CAT
        ]
        .astype(str)
    )


    dataframe[
        TIME_INDEX
    ] = (

        dataframe[
            TIME_INDEX
        ]
        .astype(int)
    )


    dataframe[
        TARGET
    ] = (

        dataframe[
            TARGET
        ]
        .astype(float)
    )


# ============================================================
# 8. IDENTIFY HISTORICAL PREDICTORS
# ============================================================

metadata_columns = {

    SERIES_ID,

    DISTRICT,

    DATE,

    "TFT_Split",

    "Segment_Number",

    TIME_INDEX,

    MONTH_CAT,

    "Month_Sin_TFT",

    "Month_Cos_TFT",

    TARGET
}


historical_predictors = [

    column

    for column
    in full_train.columns

    if (

        column
        not in metadata_columns

        and

        pd.api.types.is_numeric_dtype(
            full_train[
                column
            ]
        )
    )
]


for dataframe in [

    core_train,

    full_train,

    internal_context,

    external_context

]:

    for column in historical_predictors:

        dataframe[
            column
        ] = (

            pd.to_numeric(

                dataframe[
                    column
                ],

                errors="coerce"
            )

            .astype(float)
        )


remaining_training_nans = int(

    full_train[
        historical_predictors
    ]
    .isna()
    .sum()
    .sum()
)


remaining_external_nans = int(

    external_context[
        historical_predictors
    ]
    .isna()
    .sum()
    .sum()
)


if remaining_training_nans != 0:

    raise ValueError(

        "Predictor NaNs remain in "
        "TFT training data."
    )


if remaining_external_nans != 0:

    raise ValueError(

        "Predictor NaNs remain in "
        "TFT external validation context."
    )


print(
    "\n"
    +
    "-" * 115
)


print(
    "2. TFT VARIABLE ROLES"
)


print(
    "-" * 115
)


print(
    f"Historical numeric predictors : "
    f"{len(historical_predictors)}"
)


print(
    "Static categorical           : District"
)


print(
    "Known categorical            : Month_Cat"
)


print(
    "Known reals                  : "
    "Time_Index, Month_Sin_TFT, Month_Cos_TFT"
)


print(
    f"Unknown historical reals     : "
    f"{len(historical_predictors) + 1} "
    f"(including target)"
)


# ============================================================
# 9. TFT DATASET FACTORY
# ============================================================
#
# IMPORTANT FIX:
#
# GroupNormalizer uses District.
#
# Therefore District MUST also be included
# inside TimeSeriesDataSet group_ids.
#
# Series_ID continues to protect the continuous
# sequence segments created in Step 18.
#
# ============================================================

def create_tft_dataset(
    data
):

    dataset = TimeSeriesDataSet(

        data=data,

        time_idx=
            TIME_INDEX,

        target=
            TARGET,

        # ----------------------------------------------------
        # CORRECTED GROUP IDS
        # ----------------------------------------------------

        group_ids=[

            DISTRICT,

            SERIES_ID
        ],

        # ----------------------------------------------------

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

        time_varying_known_categoricals=[

            MONTH_CAT
        ],

        time_varying_known_reals=[

            TIME_INDEX,

            "Month_Sin_TFT",

            "Month_Cos_TFT"
        ],

        time_varying_unknown_reals=(

            [
                TARGET
            ]

            +

            historical_predictors
        ),

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

            SERIES_ID:
                NaNLabelEncoder(
                    add_nan=True
                ),

            MONTH_CAT:
                NaNLabelEncoder(
                    add_nan=True
                )
        },

        add_relative_time_idx=True,

        add_target_scales=True,

        add_encoder_length=True,

        allow_missing_timesteps=False,

        randomize_length=False
    )


    return dataset


# ============================================================
# 10. CORE TRAINING DATASET
# ============================================================

print(
    "\n"
    +
    "=" * 115
)


print(
    "3. BUILD CORE TRAINING DATASET"
)


print(
    "=" * 115
)


core_dataset = create_tft_dataset(
    core_train
)


core_loader = (

    core_dataset
    .to_dataloader(

        train=True,

        batch_size=
            BATCH_SIZE,

        num_workers=0
    )
)


print(
    f"Core training sequences: "
    f"{len(core_dataset)}"
)


# ============================================================
# 11. INTERNAL 2023 VALIDATION
# ============================================================

jan_2023_rows = (

    internal_context[

        internal_context[
            DATE
        ]

        ==

        pd.Timestamp(
            "2023-01-01"
        )
    ]
)


if jan_2023_rows.empty:

    raise ValueError(

        "January 2023 not found "
        "in internal context."
    )


JAN_2023_TIME_INDEX = int(

    jan_2023_rows[
        TIME_INDEX
    ]
    .iloc[0]
)


internal_validation_dataset = (

    TimeSeriesDataSet
    .from_dataset(

        core_dataset,

        internal_context,

        min_prediction_idx=
            JAN_2023_TIME_INDEX,

        stop_randomization=True
    )
)


internal_val_loader = (

    internal_validation_dataset
    .to_dataloader(

        train=False,

        batch_size=
            BATCH_SIZE,

        num_workers=0
    )
)


print(
    f"Internal 2023 validation sequences: "
    f"{len(internal_validation_dataset)}"
)


# ============================================================
# 12. INITIAL TFT MODEL
# ============================================================

loss_function = QuantileLoss(

    quantiles=
        QUANTILES
)


initial_tft = (

    TemporalFusionTransformer
    .from_dataset(

        core_dataset,

        learning_rate=
            LEARNING_RATE,

        hidden_size=
            HIDDEN_SIZE,

        attention_head_size=
            ATTENTION_HEAD_SIZE,

        dropout=
            DROPOUT,

        hidden_continuous_size=
            HIDDEN_CONTINUOUS_SIZE,

        output_size=
            len(
                QUANTILES
            ),

        loss=
            loss_function,

        optimizer=
            "adam",

        reduce_on_plateau_patience=4,

        log_interval=-1
    )
)


print(
    f"\nTFT trainable parameters: "
    f"{initial_tft.size():,}"
)


# ============================================================
# 13. INTERNAL EARLY STOPPING
# ============================================================

checkpoint_callback = ModelCheckpoint(

    dirpath=
        CHECKPOINT_DIR,

    filename=
        "tft-internal-{epoch:02d}-{val_loss:.4f}",

    monitor=
        "val_loss",

    mode=
        "min",

    save_top_k=1
)


early_stopping = EarlyStopping(

    monitor=
        "val_loss",

    min_delta=
        0.0001,

    patience=
        6,

    mode=
        "min"
)


trainer = Trainer(

    max_epochs=
        MAX_EPOCHS,

    accelerator=
        "cpu",

    devices=1,

    gradient_clip_val=
        0.1,

    callbacks=[

        checkpoint_callback,

        early_stopping
    ],

    logger=False,

    enable_model_summary=False,

    enable_progress_bar=True
)


print(
    "\nTraining initial TFT..."
)


print(
    "2023 is used only to select "
    "the training epoch."
)


trainer.fit(

    initial_tft,

    train_dataloaders=
        core_loader,

    val_dataloaders=
        internal_val_loader
)


# ============================================================
# 14. SELECT BEST EPOCH
# ============================================================

best_checkpoint_path = (
    checkpoint_callback
    .best_model_path
)


if best_checkpoint_path == "":

    raise RuntimeError(

        "TFT best checkpoint "
        "was not created."
    )


checkpoint_data = torch.load(

    best_checkpoint_path,

    map_location=
        "cpu",

    weights_only=False
)


selected_epoch = (

    int(
        checkpoint_data[
            "epoch"
        ]
    )

    +

    1
)


best_internal_loss = float(

    checkpoint_callback
    .best_model_score
    .detach()
    .cpu()
    .item()
)


print(
    "\n"
    +
    "=" * 115
)


print(
    "4. INTERNAL MODEL SELECTION"
)


print(
    "=" * 115
)


print(
    f"Selected epoch    : "
    f"{selected_epoch}"
)


print(
    f"Best 2023 val loss: "
    f"{best_internal_loss:.6f}"
)


# ============================================================
# 15. REFIT USING FULL 2015-2023 TRAINING
# ============================================================

print(
    "\n"
    +
    "=" * 115
)


print(
    "5. REFIT TFT USING FULL 2015-2023 TRAINING"
)


print(
    "=" * 115
)


full_training_dataset = (
    create_tft_dataset(
        full_train
    )
)


full_train_loader = (

    full_training_dataset
    .to_dataloader(

        train=True,

        batch_size=
            BATCH_SIZE,

        num_workers=0
    )
)


seed_everything(
    RANDOM_STATE,
    workers=True
)


final_tft = (

    TemporalFusionTransformer
    .from_dataset(

        full_training_dataset,

        learning_rate=
            LEARNING_RATE,

        hidden_size=
            HIDDEN_SIZE,

        attention_head_size=
            ATTENTION_HEAD_SIZE,

        dropout=
            DROPOUT,

        hidden_continuous_size=
            HIDDEN_CONTINUOUS_SIZE,

        output_size=
            len(
                QUANTILES
            ),

        loss=
            QuantileLoss(
                quantiles=
                    QUANTILES
            ),

        optimizer=
            "adam",

        reduce_on_plateau_patience=
            1000,

        log_interval=-1
    )
)


refit_trainer = Trainer(

    max_epochs=
        selected_epoch,

    accelerator=
        "cpu",

    devices=1,

    gradient_clip_val=
        0.1,

    logger=False,

    enable_checkpointing=False,

    enable_model_summary=False,

    enable_progress_bar=True
)


print(
    f"Refitting for fixed "
    f"{selected_epoch} epoch(s)..."
)


refit_trainer.fit(

    final_tft,

    train_dataloaders=
        full_train_loader
)


FINAL_MODEL_PATH = (

    MODEL_DIR
    /
    "19_tft_candidate.ckpt"
)


refit_trainer.save_checkpoint(
    FINAL_MODEL_PATH
)


print(
    f"\nCandidate model saved: "
    f"{FINAL_MODEL_PATH.name}"
)


# ============================================================
# 16. CREATE 2024 EXTERNAL VALIDATION WINDOWS
# ============================================================

print(
    "\n"
    +
    "=" * 115
)


print(
    "6. BUILD 2024 EXTERNAL VALIDATION WINDOWS"
)


print(
    "=" * 115
)


aug_2023_rows = (

    external_context[

        external_context[
            DATE
        ]

        ==

        pd.Timestamp(
            "2023-08-01"
        )
    ]
)


if aug_2023_rows.empty:

    raise ValueError(

        "August 2023 not found "
        "in external validation context."
    )


AUG_2023_TIME_INDEX = int(

    aug_2023_rows[
        TIME_INDEX
    ]
    .iloc[0]
)


external_validation_dataset = (

    TimeSeriesDataSet
    .from_dataset(

        full_training_dataset,

        external_context,

        min_prediction_idx=
            AUG_2023_TIME_INDEX,

        stop_randomization=True
    )
)


external_loader = (

    external_validation_dataset
    .to_dataloader(

        train=False,

        batch_size=
            BATCH_SIZE,

        num_workers=0
    )
)


print(
    f"External validation sequences: "
    f"{len(external_validation_dataset)}"
)


# ============================================================
# 17. QUANTILE PREDICTIONS
# ============================================================

print(
    "\nGenerating TFT quantile forecasts..."
)


prediction_result = final_tft.predict(

    external_loader,

    mode="quantiles",

    return_index=True,

    return_decoder_lengths=True,

    trainer_kwargs={

        "accelerator":
            "cpu",

        "devices":
            1
    }
)


quantile_predictions = (
    prediction_result.output
)


if isinstance(
    quantile_predictions,
    torch.Tensor
):

    quantile_predictions = (

        quantile_predictions
        .detach()
        .cpu()
        .numpy()
    )


prediction_index = (

    prediction_result
    .index
    .copy()
    .reset_index(
        drop=True
    )
)


decoder_lengths = (
    prediction_result
    .decoder_lengths
)


if isinstance(
    decoder_lengths,
    torch.Tensor
):

    decoder_lengths = (

        decoder_lengths
        .detach()
        .cpu()
        .numpy()
    )


print(
    f"Prediction windows generated: "
    f"{len(prediction_index)}"
)


# ============================================================
# 18. ACTUAL TARGET LOOKUP
# ============================================================

actual_lookup = (

    external_context[

        [
            DISTRICT,
            SERIES_ID,
            TIME_INDEX,
            DATE,
            TARGET
        ]
    ]

    .drop_duplicates(

        subset=[

            DISTRICT,

            SERIES_ID,

            TIME_INDEX
        ]
    )

    .set_index(

        [
            DISTRICT,

            SERIES_ID,

            TIME_INDEX
        ]
    )
)


# ============================================================
# 19. EXTRACT H1 / H3 / H6
# ============================================================

prediction_records = []


for row_position in range(
    len(
        prediction_index
    )
):

    district = str(

        prediction_index
        .iloc[
            row_position
        ][
            DISTRICT
        ]
    )


    series_id = str(

        prediction_index
        .iloc[
            row_position
        ][
            SERIES_ID
        ]
    )


    first_decoder_time = int(

        prediction_index
        .iloc[
            row_position
        ][
            TIME_INDEX
        ]
    )


    available_length = int(

        decoder_lengths[
            row_position
        ]
    )


    for horizon in HORIZONS:

        if available_length < horizon:

            continue


        target_time_index = (

            first_decoder_time

            +

            horizon

            -

            1
        )


        lookup_key = (

            district,

            series_id,

            target_time_index
        )


        if lookup_key not in actual_lookup.index:

            continue


        actual_row = (

            actual_lookup
            .loc[
                lookup_key
            ]
        )


        target_date = pd.Timestamp(

            actual_row[
                DATE
            ]
        )


        # -----------------------------------------------
        # EXTERNAL VALIDATION ONLY:
        # target date must be in 2024.
        # -----------------------------------------------

        if target_date.year != 2024:

            continue


        lower_prediction = float(

            quantile_predictions[

                row_position,

                horizon - 1,

                0
            ]
        )


        median_prediction = float(

            quantile_predictions[

                row_position,

                horizon - 1,

                1
            ]
        )


        upper_prediction = float(

            quantile_predictions[

                row_position,

                horizon - 1,

                2
            ]
        )


        prediction_records.append({

            "District":
                district,

            "Series_ID":
                series_id,

            "Horizon_Months":
                horizon,

            "Forecast_Target_Date":
                target_date,

            "Actual_Target":
                float(
                    actual_row[
                        TARGET
                    ]
                ),

            "Lower_2_5":
                lower_prediction,

            "Median_Prediction":
                median_prediction,

            "Upper_97_5":
                upper_prediction
        })


prediction_df = pd.DataFrame(
    prediction_records
)


if prediction_df.empty:

    raise RuntimeError(

        "No 2024 TFT predictions "
        "were extracted."
    )


prediction_df = (

    prediction_df

    .sort_values(

        [
            "Horizon_Months",

            "District",

            "Forecast_Target_Date"
        ]
    )

    .drop_duplicates(

        subset=[

            "Horizon_Months",

            "District",

            "Forecast_Target_Date"
        ],

        keep="first"
    )

    .reset_index(
        drop=True
    )
)


# ============================================================
# 20. METRIC FUNCTIONS
# ============================================================

def calculate_mae(
    y_true,
    y_pred
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
    y_pred
):

    return float(

        np.sqrt(

            np.mean(

                (
                    y_true
                    -
                    y_pred
                )

                ** 2
            )
        )
    )


def calculate_wape(
    y_true,
    y_pred
):

    denominator = np.sum(

        np.abs(
            y_true
        )
    )


    if denominator == 0:

        return np.nan


    return float(

        (

            np.sum(

                np.abs(

                    y_true
                    -
                    y_pred
                )
            )

            /

            denominator
        )

        *
        100
    )


def calculate_smape(
    y_true,
    y_pred
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


    numerator = (

        2

        *

        np.abs(

            y_true
            -
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

            numerator[
                valid
            ]

            /

            denominator[
                valid
            ]
        )

        *
        100
    )


def calculate_r2(
    y_true,
    y_pred
):

    ss_res = np.sum(

        (
            y_true
            -
            y_pred
        )

        ** 2
    )


    ss_tot = np.sum(

        (
            y_true

            -

            np.mean(
                y_true
            )
        )

        ** 2
    )


    if ss_tot == 0:

        return np.nan


    return float(

        1

        -

        (
            ss_res
            /
            ss_tot
        )
    )


def calculate_pinball_loss(
    y_true,
    y_pred,
    quantile
):

    error = (

        y_true
        -
        y_pred
    )


    return float(

        np.mean(

            np.maximum(

                quantile
                *
                error,

                (
                    quantile
                    -
                    1
                )
                *
                error
            )
        )
    )


# ============================================================
# 21. EVALUATE H1 / H3 / H6
# ============================================================

print(
    "\n"
    +
    "=" * 115
)


print(
    "TFT 2024 VALIDATION RESULTS"
)


print(
    "=" * 115
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


    if horizon_df.empty:

        print(
            f"\nWARNING: "
            f"No predictions available for H{horizon}"
        )

        continue


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
            "Median_Prediction"
        ]

        .to_numpy(
            dtype=float
        )
    )


    lower = (

        horizon_df[
            "Lower_2_5"
        ]

        .to_numpy(
            dtype=float
        )
    )


    upper = (

        horizon_df[
            "Upper_97_5"
        ]

        .to_numpy(
            dtype=float
        )
    )


    mae_value = calculate_mae(
        y_true,
        y_pred
    )


    rmse_value = calculate_rmse(
        y_true,
        y_pred
    )


    wape_value = calculate_wape(
        y_true,
        y_pred
    )


    smape_value = calculate_smape(
        y_true,
        y_pred
    )


    r2_value = calculate_r2(
        y_true,
        y_pred
    )


    negative_count = int(

        (
            y_pred
            <
            0
        )
        .sum()
    )


    coverage = float(

        np.mean(

            (
                y_true
                >=
                lower
            )

            &

            (
                y_true
                <=
                upper
            )
        )

        *
        100
    )


    mean_interval_width = float(

        np.mean(

            upper
            -
            lower
        )
    )


    quantile_crossings = int(

        (

            (
                lower
                >
                y_pred
            )

            |

            (
                y_pred
                >
                upper
            )
        )

        .sum()
    )


    lower_pinball = calculate_pinball_loss(

        y_true,

        lower,

        0.025
    )


    median_pinball = calculate_pinball_loss(

        y_true,

        y_pred,

        0.50
    )


    upper_pinball = calculate_pinball_loss(

        y_true,

        upper,

        0.975
    )


    mean_pinball = float(

        np.mean(

            [
                lower_pinball,
                median_pinball,
                upper_pinball
            ]
        )
    )


    print(
        f"\nH{horizon}"
    )


    print(
        f"Validation rows           : "
        f"{len(horizon_df)}"
    )


    print(
        f"MAE                       : "
        f"{mae_value:.4f}"
    )


    print(
        f"RMSE                      : "
        f"{rmse_value:.4f}"
    )


    print(
        f"WAPE                      : "
        f"{wape_value:.4f}%"
    )


    print(
        f"sMAPE                     : "
        f"{smape_value:.4f}%"
    )


    print(
        f"R²                        : "
        f"{r2_value:.4f}"
    )


    print(
        f"Negative predictions      : "
        f"{negative_count}"
    )


    print(
        f"95% interval coverage     : "
        f"{coverage:.2f}%"
    )


    print(
        f"Mean interval width       : "
        f"{mean_interval_width:.4f}"
    )


    print(
        f"Mean pinball loss         : "
        f"{mean_pinball:.4f}"
    )


    print(
        f"Quantile crossings        : "
        f"{quantile_crossings}"
    )


    metric_records.append({

        "Horizon_Months":
            horizon,

        "Model":
            "TFT",

        "Validation_Rows":
            len(
                horizon_df
            ),

        "MAE":
            mae_value,

        "RMSE":
            rmse_value,

        "WAPE_Percentage":
            wape_value,

        "sMAPE_Percentage":
            smape_value,

        "R2":
            r2_value,

        "Negative_Predictions":
            negative_count,

        "Interval_Coverage_Percentage":
            coverage,

        "Mean_Interval_Width":
            mean_interval_width,

        "Mean_Pinball_Loss":
            mean_pinball,

        "Quantile_Crossings":
            quantile_crossings,

        "Selected_Epoch":
            selected_epoch
    })


    horizon_df.to_csv(

        REPORT_DIR
        /
        f"19_tft_h{horizon}_validation_predictions.csv",

        index=False
    )


# ============================================================
# 22. SAVE VALIDATION METRICS
# ============================================================

metrics_df = pd.DataFrame(
    metric_records
)


if metrics_df.empty:

    raise RuntimeError(

        "No TFT validation metrics "
        "were generated."
    )


metrics_output_path = (

    REPORT_DIR
    /
    "19_tft_validation_metrics.csv"
)


metrics_df.to_csv(

    metrics_output_path,

    index=False
)


print(
    "\n"
    +
    "=" * 115
)


print(
    "TFT VALIDATION METRIC SUMMARY"
)


print(
    "=" * 115
)


print(

    metrics_df
    .round(4)
    .to_string(
        index=False
    )
)


# ============================================================
# 23. SAVE ALL VALIDATION PREDICTIONS
# ============================================================

prediction_df.to_csv(

    REPORT_DIR
    /
    "19_tft_all_validation_predictions.csv",

    index=False
)


# ============================================================
# 24. SAVE MODEL CONFIGURATION
# ============================================================

configuration_df = pd.DataFrame([{

    "Model":
        "Temporal Fusion Transformer",

    "Encoder_Length":
        MAX_ENCODER_LENGTH,

    "Maximum_Prediction_Length":
        MAX_PREDICTION_LENGTH,

    "Learning_Rate":
        LEARNING_RATE,

    "Hidden_Size":
        HIDDEN_SIZE,

    "Attention_Heads":
        ATTENTION_HEAD_SIZE,

    "Hidden_Continuous_Size":
        HIDDEN_CONTINUOUS_SIZE,

    "Dropout":
        DROPOUT,

    "Batch_Size":
        BATCH_SIZE,

    "Maximum_Epochs":
        MAX_EPOCHS,

    "Selected_Epoch":
        selected_epoch,

    "Internal_Validation_Loss":
        best_internal_loss,

    "Historical_Predictor_Count":
        len(
            historical_predictors
        ),

    "Quantiles":
        str(
            QUANTILES
        ),

    "Hyperparameter_Tuned":
        False,

    "Final_Test_2025_Used":
        False
}])


configuration_df.to_csv(

    REPORT_DIR
    /
    "19_tft_model_configuration.csv",

    index=False
)


# ============================================================
# 25. FINAL SUMMARY
# ============================================================

print(
    "\n"
    +
    "=" * 115
)


print(
    "STEP 19 SUMMARY"
)


print(
    "=" * 115
)


print(
    "Temporal Fusion Transformer "
    "initial candidate analysis completed."
)


print(
    "\nMethodology:"
)


print(
    "- 12-month encoder history used"
)


print(
    "- One TFT predicts up to 6 months ahead"
)


print(
    "- H1, H3 and H6 evaluated separately"
)


print(
    "- District used as static categorical variable"
)


print(
    "- District + Series_ID used as dataset group IDs"
)


print(
    "- District-level target normalization used"
)


print(
    "- Calendar variables used as known-future inputs"
)


print(
    "- Target and historical predictors treated "
    "as future-unknown variables"
)


print(
    "- 2023 used only for internal epoch selection"
)


print(
    "- Final candidate refitted using 2015-2023"
)


print(
    "- 2024 used for external validation"
)


print(
    "- 2025 was NOT used"
)


print(
    "- Median quantile used as point prediction"
)


print(
    "- 2.5% and 97.5% quantiles used "
    "for 95% prediction interval"
)


print(
    "- Hyperparameters have NOT been tuned yet"
)


print(
    "\nIMPORTANT:"
)


print(
    "Do NOT choose the final model yet."
)


print(
    "Strict temporal revalidation and fair "
    "hyperparameter tuning are still required."
)


print(
    "\nCandidate TFT model saved to:"
)


print(
    FINAL_MODEL_PATH
)


print(
    "\nMetrics saved to:"
)


print(
    metrics_output_path
)


print(
    "\nSTEP 19 - TFT MODEL ANALYSIS COMPLETE"
)


print(
    "=" * 115
)