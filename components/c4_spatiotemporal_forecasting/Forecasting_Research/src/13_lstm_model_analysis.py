# ============================================================
# STEP 13 - LSTM MODEL ANALYSIS
# Childhood Malnutrition Forecasting Research
#
# Strategy:
# - 12-month sequential inputs
# - H1, H3 and H6 trained separately
# - TRAIN period only used for model fitting
# - 2023 used as INTERNAL train-only validation
#   for epoch selection / early stopping
# - Model then retrained on full 2015-2023 TRAIN data
# - 2024 used only as EXTERNAL validation
# - 2025 TEST data is NOT loaded
#
# IMPORTANT:
# This is initial LSTM candidate analysis.
# Hyperparameter tuning is NOT performed yet.
# ============================================================

import copy
import random
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


# ============================================================
# 1. REPRODUCIBILITY
# ============================================================

RANDOM_STATE = 42

random.seed(
    RANDOM_STATE
)

np.random.seed(
    RANDOM_STATE
)

torch.manual_seed(
    RANDOM_STATE
)


# CPU is sufficient for this dataset and improves
# reproducibility across systems.

DEVICE = torch.device(
    "cpu"
)


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

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

FIGURE_DIR = (
    BASE_DIR
    / "outputs"
    / "figures"
)

MODEL_DIR = (
    BASE_DIR
    / "models"
    / "candidates"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

FIGURE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 3. SETTINGS
# ============================================================

HORIZONS = [
    1,
    3,
    6
]

TARGET = "Forecast_Target"

SEQUENCE_LENGTH = 12

HIDDEN_SIZE = 64

BATCH_SIZE = 64

MAX_EPOCHS = 100

PATIENCE = 10

LEARNING_RATE = 0.001


print("\n" + "=" * 110)
print("STEP 13 - LSTM MODEL ANALYSIS")
print("=" * 110)

print(
    f"\nDevice          : {DEVICE}"
)

print(
    f"Sequence length : {SEQUENCE_LENGTH} months"
)

print(
    f"Hidden units    : {HIDDEN_SIZE}"
)

print(
    f"Maximum epochs  : {MAX_EPOCHS}"
)

print(
    "\n2025 test data is NOT loaded."
)


# ============================================================
# 4. METRIC FUNCTIONS
# ============================================================

def calculate_mae(
    y_true,
    y_pred
):

    return np.mean(
        np.abs(
            y_true - y_pred
        )
    )


def calculate_rmse(
    y_true,
    y_pred
):

    return np.sqrt(
        np.mean(
            (
                y_true - y_pred
            ) ** 2
        )
    )


def calculate_wape(
    y_true,
    y_pred
):

    denominator = np.sum(
        np.abs(y_true)
    )

    if denominator == 0:

        return np.nan

    return (
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


def calculate_smape(
    y_true,
    y_pred
):

    denominator = (
        np.abs(y_true)
        +
        np.abs(y_pred)
    )

    numerator = (
        2
        *
        np.abs(
            y_true - y_pred
        )
    )

    valid = (
        denominator != 0
    )

    if valid.sum() == 0:

        return np.nan

    return (
        np.mean(
            numerator[valid]
            /
            denominator[valid]
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
            y_true - y_pred
        ) ** 2
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

    return (
        1
        -
        ss_res / ss_tot
    )


# ============================================================
# 5. LSTM MODEL
# ============================================================

class LSTMRegressor(
    nn.Module
):

    def __init__(
        self,
        input_size,
        hidden_size=64
    ):

        super().__init__()

        self.lstm = nn.LSTM(

            input_size=input_size,

            hidden_size=hidden_size,

            num_layers=1,

            batch_first=True
        )

        self.dropout = nn.Dropout(
            0.20
        )

        self.output_layer = nn.Linear(

            hidden_size,

            1
        )


    def forward(
        self,
        x
    ):

        lstm_output, _ = self.lstm(
            x
        )

        last_step = (
            lstm_output[
                :,
                -1,
                :
            ]
        )

        last_step = self.dropout(
            last_step
        )

        prediction = self.output_layer(
            last_step
        )

        return prediction


# ============================================================
# 6. CONSECUTIVE MONTH CHECK
# ============================================================

def consecutive_months(
    dates
):

    periods = (

        pd.Series(dates)
        .dt.to_period("M")
        .astype(int)
        .to_numpy()
    )

    if len(periods) <= 1:

        return True

    differences = np.diff(
        periods
    )

    return bool(
        np.all(
            differences == 1
        )
    )


# ============================================================
# 7. CREATE LSTM SEQUENCES
# ============================================================

def create_sequences(
    dataframe,
    feature_columns,
    sequence_length
):

    train_x = []
    train_y = []
    train_metadata = []

    validation_x = []
    validation_y = []
    validation_metadata = []

    dropped_nonconsecutive = 0


    for district, district_df in dataframe.groupby(
        "District"
    ):

        district_df = (

            district_df
            .sort_values(
                "Forecast_Origin_Date"
            )
            .reset_index(drop=True)
        )


        for i in range(
            sequence_length - 1,
            len(district_df)
        ):

            current_row = (
                district_df.iloc[i]
            )


            window = (

                district_df
                .iloc[
                    i
                    -
                    sequence_length
                    +
                    1
                    :
                    i
                    +
                    1
                ]
            )


            if not consecutive_months(
                window[
                    "Forecast_Origin_Date"
                ]
            ):

                dropped_nonconsecutive += 1

                continue


            x_window = (

                window[
                    feature_columns
                ]
                .to_numpy(
                    dtype=np.float32
                )
            )


            y_value = float(
                current_row[
                    TARGET
                ]
            )


            metadata = {

                "District":
                    district,

                "Forecast_Origin_Date":
                    current_row[
                        "Forecast_Origin_Date"
                    ],

                "Forecast_Target_Date":
                    current_row[
                        "Forecast_Target_Date"
                    ],

                "Data_Split":
                    current_row[
                        "Data_Split"
                    ]
            }


            # --------------------------------------------
            # TRAINING SAMPLE
            # --------------------------------------------

            if (
                current_row[
                    "Data_Split"
                ]
                == "TRAIN"
            ):

                # For training sequences, every input
                # row must come from TRAIN.

                if not (
                    window[
                        "Data_Split"
                    ]
                    == "TRAIN"
                ).all():

                    continue


                train_x.append(
                    x_window
                )

                train_y.append(
                    y_value
                )

                train_metadata.append(
                    metadata
                )


            # --------------------------------------------
            # EXTERNAL VALIDATION SAMPLE
            # --------------------------------------------

            elif (
                current_row[
                    "Data_Split"
                ]
                == "VALIDATION"
            ):

                # Validation sequence may include earlier
                # validation-origin observations because
                # rolling forecasting can use information
                # already available by the current origin.
                #
                # No target label is used as an input.

                validation_x.append(
                    x_window
                )

                validation_y.append(
                    y_value
                )

                validation_metadata.append(
                    metadata
                )


    return (

        np.asarray(
            train_x,
            dtype=np.float32
        ),

        np.asarray(
            train_y,
            dtype=np.float32
        ),

        pd.DataFrame(
            train_metadata
        ),

        np.asarray(
            validation_x,
            dtype=np.float32
        ),

        np.asarray(
            validation_y,
            dtype=np.float32
        ),

        pd.DataFrame(
            validation_metadata
        ),

        dropped_nonconsecutive
    )


# ============================================================
# 8. SCALE 3D SEQUENTIAL FEATURES
# ============================================================

def fit_feature_scaler(
    x
):

    scaler = StandardScaler()

    flattened = x.reshape(
        -1,
        x.shape[-1]
    )

    scaler.fit(
        flattened
    )

    return scaler


def apply_feature_scaler(
    x,
    scaler
):

    original_shape = (
        x.shape
    )

    flattened = x.reshape(
        -1,
        x.shape[-1]
    )

    scaled = scaler.transform(
        flattened
    )

    return (
        scaled
        .reshape(
            original_shape
        )
        .astype(
            np.float32
        )
    )


# ============================================================
# 9. TRAIN WITH INTERNAL EARLY STOPPING
# ============================================================

def train_with_early_stopping(
    x_train,
    y_train,
    x_internal_validation,
    y_internal_validation,
    input_size
):

    model = LSTMRegressor(

        input_size=input_size,

        hidden_size=HIDDEN_SIZE
    ).to(
        DEVICE
    )


    optimizer = torch.optim.Adam(

        model.parameters(),

        lr=LEARNING_RATE
    )


    criterion = nn.MSELoss()


    train_dataset = TensorDataset(

        torch.tensor(
            x_train,
            dtype=torch.float32
        ),

        torch.tensor(
            y_train,
            dtype=torch.float32
        ).reshape(
            -1,
            1
        )
    )


    train_loader = DataLoader(

        train_dataset,

        batch_size=BATCH_SIZE,

        shuffle=True
    )


    x_internal_tensor = torch.tensor(

        x_internal_validation,

        dtype=torch.float32,

        device=DEVICE
    )


    y_internal_tensor = torch.tensor(

        y_internal_validation,

        dtype=torch.float32,

        device=DEVICE
    ).reshape(
        -1,
        1
    )


    best_state = None

    best_validation_loss = np.inf

    best_epoch = 1

    epochs_without_improvement = 0

    training_history = []


    for epoch in range(
        1,
        MAX_EPOCHS + 1
    ):

        model.train()

        batch_losses = []


        for batch_x, batch_y in train_loader:

            batch_x = batch_x.to(
                DEVICE
            )

            batch_y = batch_y.to(
                DEVICE
            )


            optimizer.zero_grad()


            prediction = model(
                batch_x
            )


            loss = criterion(

                prediction,

                batch_y
            )


            loss.backward()

            optimizer.step()


            batch_losses.append(
                loss.item()
            )


        training_loss = float(
            np.mean(
                batch_losses
            )
        )


        model.eval()


        with torch.no_grad():

            internal_prediction = model(
                x_internal_tensor
            )


            internal_loss = criterion(

                internal_prediction,

                y_internal_tensor
            ).item()


        training_history.append({

            "Epoch":
                epoch,

            "Training_Loss":
                training_loss,

            "Internal_Validation_Loss":
                internal_loss
        })


        if internal_loss < best_validation_loss:

            best_validation_loss = (
                internal_loss
            )

            best_epoch = (
                epoch
            )

            best_state = copy.deepcopy(
                model.state_dict()
            )

            epochs_without_improvement = 0

        else:

            epochs_without_improvement += 1


        if (
            epoch == 1
            or
            epoch % 10 == 0
        ):

            print(
                f"Epoch {epoch:3d} | "
                f"Train Loss: {training_loss:.5f} | "
                f"Internal Val Loss: {internal_loss:.5f}"
            )


        if (
            epochs_without_improvement
            >= PATIENCE
        ):

            print(
                f"Early stopping at epoch "
                f"{epoch}"
            )

            break


    model.load_state_dict(
        best_state
    )


    return (
        model,
        best_epoch,
        pd.DataFrame(
            training_history
        )
    )


# ============================================================
# 10. RETRAIN FINAL CANDIDATE ON FULL TRAIN SET
# ============================================================

def train_fixed_epochs(
    x_train,
    y_train,
    input_size,
    epochs
):

    model = LSTMRegressor(

        input_size=input_size,

        hidden_size=HIDDEN_SIZE
    ).to(
        DEVICE
    )


    optimizer = torch.optim.Adam(

        model.parameters(),

        lr=LEARNING_RATE
    )


    criterion = nn.MSELoss()


    dataset = TensorDataset(

        torch.tensor(
            x_train,
            dtype=torch.float32
        ),

        torch.tensor(
            y_train,
            dtype=torch.float32
        ).reshape(
            -1,
            1
        )
    )


    loader = DataLoader(

        dataset,

        batch_size=BATCH_SIZE,

        shuffle=True
    )


    for _ in range(
        epochs
    ):

        model.train()


        for batch_x, batch_y in loader:

            batch_x = batch_x.to(
                DEVICE
            )

            batch_y = batch_y.to(
                DEVICE
            )


            optimizer.zero_grad()


            prediction = model(
                batch_x
            )


            loss = criterion(

                prediction,

                batch_y
            )


            loss.backward()

            optimizer.step()


    return model


# ============================================================
# 11. PREDICTION FUNCTION
# ============================================================

def predict_model(
    model,
    x
):

    model.eval()


    with torch.no_grad():

        tensor_x = torch.tensor(

            x,

            dtype=torch.float32,

            device=DEVICE
        )


        prediction = model(
            tensor_x
        )


    return (

        prediction
        .cpu()
        .numpy()
        .reshape(-1)
    )


# ============================================================
# 12. STORAGE
# ============================================================

metric_records = []

summary_records = []


# ============================================================
# 13. PROCESS EACH HORIZON
# ============================================================

for horizon in HORIZONS:

    print("\n" + "=" * 110)

    print(
        f"H{horizon} - "
        f"{horizon}-MONTH AHEAD LSTM"
    )

    print("=" * 110)


    # ========================================================
    # 13.1 LOAD TRAIN + VALIDATION ONLY
    # ========================================================

    train_path = (
        MODEL_READY_DIR
        / f"h{horizon}_train_preprocessed.csv"
    )

    validation_path = (
        MODEL_READY_DIR
        / f"h{horizon}_validation_preprocessed.csv"
    )

    manifest_path = (
        REPORT_DIR
        / f"09_h{horizon}_usable_feature_manifest.csv"
    )


    train_df = pd.read_csv(
        train_path
    )

    validation_df = pd.read_csv(
        validation_path
    )

    feature_manifest = pd.read_csv(
        manifest_path
    )


    for df in [
        train_df,
        validation_df
    ]:

        df[
            "Forecast_Origin_Date"
        ] = pd.to_datetime(
            df[
                "Forecast_Origin_Date"
            ]
        )

        df[
            "Forecast_Target_Date"
        ] = pd.to_datetime(
            df[
                "Forecast_Target_Date"
            ]
        )


    numeric_features = (
        feature_manifest[
            "Feature"
        ]
        .tolist()
    )


    print(
        f"\nTRAIN rows      : "
        f"{len(train_df)}"
    )

    print(
        f"VALIDATION rows : "
        f"{len(validation_df)}"
    )

    print(
        f"Numeric features: "
        f"{len(numeric_features)}"
    )


    # ========================================================
    # 13.2 DISTRICT ONE-HOT ENCODING
    # ========================================================

    train_dummies = pd.get_dummies(

        train_df[
            "District"
        ],

        prefix="District",

        dtype=float
    )


    validation_dummies = pd.get_dummies(

        validation_df[
            "District"
        ],

        prefix="District",

        dtype=float
    )


    validation_dummies = (

        validation_dummies
        .reindex(
            columns=train_dummies.columns,
            fill_value=0
        )
    )


    train_augmented = (

        pd.concat(
            [
                train_df.reset_index(drop=True),
                train_dummies.reset_index(drop=True)
            ],
            axis=1
        )
    )


    validation_augmented = (

        pd.concat(
            [
                validation_df.reset_index(drop=True),
                validation_dummies.reset_index(drop=True)
            ],
            axis=1
        )
    )


    model_features = (

        numeric_features
        +
        train_dummies.columns.tolist()
    )


    print(
        f"Total sequential features: "
        f"{len(model_features)}"
    )


    # ========================================================
    # 13.3 COMBINE TRAIN + VALIDATION FOR SEQUENCE HISTORY
    # ========================================================

    combined_df = pd.concat(

        [
            train_augmented,
            validation_augmented
        ],

        ignore_index=True
    )


    combined_df = (

        combined_df
        .sort_values(
            [
                "District",
                "Forecast_Origin_Date"
            ]
        )
        .reset_index(drop=True)
    )


    # ========================================================
    # 13.4 CREATE 12-MONTH SEQUENCES
    # ========================================================

    (
        x_train_all,
        y_train_all,
        train_metadata,
        x_external_validation,
        y_external_validation,
        validation_metadata,
        dropped_nonconsecutive
    ) = create_sequences(

        combined_df,

        model_features,

        SEQUENCE_LENGTH
    )


    print(
        f"\nTraining sequences        : "
        f"{len(x_train_all)}"
    )

    print(
        f"2024 validation sequences : "
        f"{len(x_external_validation)}"
    )

    print(
        f"Non-consecutive windows "
        f"dropped: "
        f"{dropped_nonconsecutive}"
    )


    if (
        len(x_train_all) == 0
        or
        len(x_external_validation) == 0
    ):

        raise ValueError(
            f"H{horizon}: Insufficient sequence data."
        )


    # ========================================================
    # 14. INTERNAL TRAIN-ONLY TEMPORAL VALIDATION
    # ========================================================

    print("\n" + "-" * 110)
    print("1. INTERNAL TRAIN-ONLY TEMPORAL VALIDATION")
    print("-" * 110)


    training_target_year = (

        train_metadata[
            "Forecast_Target_Date"
        ]
        .dt.year
    )


    core_train_mask = (
        training_target_year
        <= 2022
    )


    internal_validation_mask = (
        training_target_year
        == 2023
    )


    x_core_train = (
        x_train_all[
            core_train_mask.to_numpy()
        ]
    )


    y_core_train = (
        y_train_all[
            core_train_mask.to_numpy()
        ]
    )


    x_internal_validation = (
        x_train_all[
            internal_validation_mask.to_numpy()
        ]
    )


    y_internal_validation = (
        y_train_all[
            internal_validation_mask.to_numpy()
        ]
    )


    print(
        f"Core training sequences     : "
        f"{len(x_core_train)}"
    )

    print(
        f"Internal 2023 sequences     : "
        f"{len(x_internal_validation)}"
    )


    if (
        len(x_core_train) == 0
        or
        len(x_internal_validation) == 0
    ):

        raise ValueError(
            f"H{horizon}: Internal temporal "
            f"validation split failed."
        )


    # ========================================================
    # 15. TRAIN-ONLY SCALING FOR EARLY STOPPING
    # ========================================================

    feature_scaler_internal = (
        fit_feature_scaler(
            x_core_train
        )
    )


    x_core_scaled = (
        apply_feature_scaler(
            x_core_train,
            feature_scaler_internal
        )
    )


    x_internal_scaled = (
        apply_feature_scaler(
            x_internal_validation,
            feature_scaler_internal
        )
    )


    target_scaler_internal = (
        StandardScaler()
    )


    y_core_scaled = (

        target_scaler_internal
        .fit_transform(
            y_core_train.reshape(
                -1,
                1
            )
        )
        .reshape(-1)
        .astype(
            np.float32
        )
    )


    y_internal_scaled = (

        target_scaler_internal
        .transform(
            y_internal_validation.reshape(
                -1,
                1
            )
        )
        .reshape(-1)
        .astype(
            np.float32
        )
    )


    # ========================================================
    # 16. FIND TRAINING EPOCH USING 2023 ONLY
    # ========================================================

    print("\n" + "-" * 110)
    print("2. TRAIN LSTM WITH INTERNAL EARLY STOPPING")
    print("-" * 110)


    (
        internal_model,
        best_epoch,
        history_df
    ) = train_with_early_stopping(

        x_core_scaled,

        y_core_scaled,

        x_internal_scaled,

        y_internal_scaled,

        input_size=len(
            model_features
        )
    )


    print(
        f"\nSelected epoch from "
        f"TRAIN-only validation: "
        f"{best_epoch}"
    )


    history_df.to_csv(

        REPORT_DIR
        / f"13_lstm_h{horizon}_training_history.csv",

        index=False
    )


    # ========================================================
    # 17. REFIT SCALERS ON FULL 2015-2023 TRAINING DATA
    # ========================================================

    print("\n" + "-" * 110)
    print("3. REFIT USING FULL TRAINING PERIOD")
    print("-" * 110)


    feature_scaler_full = (
        fit_feature_scaler(
            x_train_all
        )
    )


    x_train_scaled = (
        apply_feature_scaler(
            x_train_all,
            feature_scaler_full
        )
    )


    x_external_scaled = (
        apply_feature_scaler(
            x_external_validation,
            feature_scaler_full
        )
    )


    target_scaler_full = (
        StandardScaler()
    )


    y_train_scaled = (

        target_scaler_full
        .fit_transform(
            y_train_all.reshape(
                -1,
                1
            )
        )
        .reshape(-1)
        .astype(
            np.float32
        )
    )


    # ========================================================
    # 18. FINAL CANDIDATE TRAINING
    # ========================================================

    final_model = train_fixed_epochs(

        x_train_scaled,

        y_train_scaled,

        input_size=len(
            model_features
        ),

        epochs=best_epoch
    )


    print(
        "Full training-period LSTM fitted."
    )


    # ========================================================
    # 19. EXTERNAL 2024 VALIDATION
    # ========================================================

    print("\n" + "-" * 110)
    print("4. 2024 EXTERNAL VALIDATION")
    print("-" * 110)


    scaled_prediction = predict_model(

        final_model,

        x_external_scaled
    )


    prediction = (

        target_scaler_full
        .inverse_transform(
            scaled_prediction.reshape(
                -1,
                1
            )
        )
        .reshape(-1)
    )


    negative_predictions = int(

        (
            prediction < 0
        ).sum()
    )


    validation_mae = calculate_mae(

        y_external_validation,

        prediction
    )


    validation_rmse = calculate_rmse(

        y_external_validation,

        prediction
    )


    validation_wape = calculate_wape(

        y_external_validation,

        prediction
    )


    validation_smape = calculate_smape(

        y_external_validation,

        prediction
    )


    validation_r2 = calculate_r2(

        y_external_validation,

        prediction
    )


    print(
        f"MAE   : {validation_mae:.4f}"
    )

    print(
        f"RMSE  : {validation_rmse:.4f}"
    )

    print(
        f"WAPE  : {validation_wape:.4f}%"
    )

    print(
        f"sMAPE : {validation_smape:.4f}%"
    )

    print(
        f"R²    : {validation_r2:.4f}"
    )

    print(
        f"Negative predictions: "
        f"{negative_predictions}"
    )


    metric_records.append({

        "Horizon_Months":
            horizon,

        "Model":
            "LSTM",

        "Sequence_Length":
            SEQUENCE_LENGTH,

        "Validation_Rows":
            len(
                y_external_validation
            ),

        "Best_Epoch":
            best_epoch,

        "MAE":
            validation_mae,

        "RMSE":
            validation_rmse,

        "WAPE_Percentage":
            validation_wape,

        "sMAPE_Percentage":
            validation_smape,

        "R2":
            validation_r2,

        "Negative_Predictions":
            negative_predictions
    })


    # ========================================================
    # 20. SAVE PREDICTIONS
    # ========================================================

    prediction_output = (
        validation_metadata.copy()
    )


    prediction_output[
        "Actual_Target"
    ] = y_external_validation


    prediction_output[
        "LSTM_Prediction"
    ] = prediction


    prediction_output[
        "Residual"
    ] = (

        prediction_output[
            "Actual_Target"
        ]
        -
        prediction_output[
            "LSTM_Prediction"
        ]
    )


    prediction_output[
        "Absolute_Error"
    ] = (

        prediction_output[
            "Residual"
        ]
        .abs()
    )


    prediction_output.to_csv(

        REPORT_DIR
        / f"13_lstm_h{horizon}_validation_predictions.csv",

        index=False
    )


    # ========================================================
    # 21. SAVE MODEL
    # ========================================================

    torch.save(

        {
            "model_state_dict":
                final_model.state_dict(),

            "input_size":
                len(model_features),

            "hidden_size":
                HIDDEN_SIZE,

            "sequence_length":
                SEQUENCE_LENGTH,

            "best_epoch":
                best_epoch,

            "feature_columns":
                model_features
        },

        MODEL_DIR
        / f"lstm_h{horizon}_candidate.pt"
    )


    # ========================================================
    # 22. VALIDATION TREND PLOT
    # ========================================================

    prediction_output[
        "Forecast_Target_Date"
    ] = pd.to_datetime(

        prediction_output[
            "Forecast_Target_Date"
        ]
    )


    monthly_plot = (

        prediction_output
        .groupby(
            "Forecast_Target_Date"
        )
        .agg(

            Actual_Mean=(
                "Actual_Target",
                "mean"
            ),

            LSTM_Mean=(
                "LSTM_Prediction",
                "mean"
            )
        )
        .reset_index()
    )


    plt.figure(
        figsize=(12, 6)
    )


    plt.plot(

        monthly_plot[
            "Forecast_Target_Date"
        ],

        monthly_plot[
            "Actual_Mean"
        ],

        marker="o",

        label="Actual"
    )


    plt.plot(

        monthly_plot[
            "Forecast_Target_Date"
        ],

        monthly_plot[
            "LSTM_Mean"
        ],

        marker="o",

        label="LSTM"
    )


    plt.title(
        f"LSTM Validation Forecast - H{horizon}"
    )

    plt.xlabel(
        "Target Month"
    )

    plt.ylabel(
        "Mean Malnutrition Cases"
    )

    plt.legend()

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()


    plt.savefig(

        FIGURE_DIR
        / f"13_lstm_h{horizon}_validation_trend.png",

        dpi=300
    )


    plt.close()


    summary_records.append({

        "Horizon_Months":
            horizon,

        "Training_Sequences":
            len(
                x_train_all
            ),

        "External_Validation_Sequences":
            len(
                x_external_validation
            ),

        "Sequence_Length":
            SEQUENCE_LENGTH,

        "Input_Features":
            len(
                model_features
            ),

        "Best_Epoch":
            best_epoch,

        "Dropped_Nonconsecutive_Windows":
            dropped_nonconsecutive
    })


# ============================================================
# 23. SAVE LSTM METRICS
# ============================================================

metrics_df = pd.DataFrame(
    metric_records
)


print("\n" + "=" * 110)
print("LSTM VALIDATION RESULTS")
print("=" * 110)


print(
    metrics_df
    .round(4)
    .to_string(index=False)
)


metrics_df.to_csv(

    REPORT_DIR
    / "13_lstm_validation_metrics.csv",

    index=False
)


summary_df = pd.DataFrame(
    summary_records
)


summary_df.to_csv(

    REPORT_DIR
    / "13_lstm_data_summary.csv",

    index=False
)


# ============================================================
# 24. COMPARE ALL MODELS SO FAR
# ============================================================

comparison_records = []


# LSTM
for _, row in metrics_df.iterrows():

    comparison_records.append({

        "Horizon_Months":
            int(
                row[
                    "Horizon_Months"
                ]
            ),

        "Model":
            "LSTM",

        "MAE":
            row["MAE"],

        "RMSE":
            row["RMSE"],

        "WAPE_Percentage":
            row[
                "WAPE_Percentage"
            ],

        "sMAPE_Percentage":
            row[
                "sMAPE_Percentage"
            ],

        "R2":
            row["R2"]
    })


# XGBoost
xgb_path = (
    REPORT_DIR
    / "12_xgboost_validation_metrics.csv"
)

if xgb_path.exists():

    xgb_df = pd.read_csv(
        xgb_path
    )

    for _, row in xgb_df.iterrows():

        comparison_records.append({

            "Horizon_Months":
                int(
                    row[
                        "Horizon_Months"
                    ]
                ),

            "Model":
                "XGBoost",

            "MAE":
                row["MAE"],

            "RMSE":
                row["RMSE"],

            "WAPE_Percentage":
                row[
                    "WAPE_Percentage"
                ],

            "sMAPE_Percentage":
                row[
                    "sMAPE_Percentage"
                ],

            "R2":
                row["R2"]
        })


# SARIMA
sarima_path = (
    REPORT_DIR
    / "11_sarima_validation_metrics.csv"
)

if sarima_path.exists():

    sarima_df = pd.read_csv(
        sarima_path
    )

    for _, row in sarima_df.iterrows():

        comparison_records.append({

            "Horizon_Months":
                int(
                    row[
                        "Horizon_Months"
                    ]
                ),

            "Model":
                "SARIMA",

            "MAE":
                row["MAE"],

            "RMSE":
                row["RMSE"],

            "WAPE_Percentage":
                row[
                    "WAPE_Percentage"
                ],

            "sMAPE_Percentage":
                row[
                    "sMAPE_Percentage"
                ],

            "R2":
                row["R2"]
        })


# Seasonal naive
baseline_path = (
    REPORT_DIR
    / "10_baseline_validation_metrics.csv"
)

if baseline_path.exists():

    baseline_df = pd.read_csv(
        baseline_path
    )

    seasonal_df = baseline_df[

        baseline_df[
            "Baseline"
        ]
        == "Seasonal Naive"
    ]


    for _, row in seasonal_df.iterrows():

        comparison_records.append({

            "Horizon_Months":
                int(
                    row[
                        "Horizon_Months"
                    ]
                ),

            "Model":
                "Seasonal Naive",

            "MAE":
                row["MAE"],

            "RMSE":
                row["RMSE"],

            "WAPE_Percentage":
                row[
                    "WAPE_Percentage"
                ],

            "sMAPE_Percentage":
                row[
                    "sMAPE_Percentage"
                ],

            "R2":
                row["R2"]
        })


comparison_df = pd.DataFrame(
    comparison_records
)


comparison_df = (

    comparison_df
    .sort_values(
        [
            "Horizon_Months",
            "MAE"
        ]
    )
)


print("\n" + "=" * 110)
print("MODEL COMPARISON AFTER LSTM")
print("=" * 110)


print(
    comparison_df
    .round(4)
    .to_string(index=False)
)


comparison_df.to_csv(

    REPORT_DIR
    / "13_model_comparison_after_lstm.csv",

    index=False
)


# ============================================================
# 25. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 110)
print("STEP 13 SUMMARY")
print("=" * 110)

print(
    "LSTM candidate-model analysis completed."
)

print(
    "\nMethodology:"
)

print(
    "- 12-month sequential inputs"
)

print(
    "- Separate H1, H3 and H6 models"
)

print(
    "- Input and target scaling learned from training data"
)

print(
    "- 2023 used only as internal train-period validation"
)

print(
    "- Epoch selection did not use 2024 external validation"
)

print(
    "- Model retrained using full 2015-2023 training period"
)

print(
    "- 2024 used as external candidate-model validation"
)

print(
    "- 2025 test data was NOT loaded"
)

print(
    "- LSTM hyperparameters are fixed initial values"
)

print(
    "- Proper tuning has NOT yet been performed"
)

print(
    "\nFinal model is NOT selected yet."
)

print(
    "Next candidate model: NGBoost."
)

print(
    "\nSTEP 13 - LSTM MODEL ANALYSIS COMPLETE"
)

print("=" * 110)