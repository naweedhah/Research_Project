# ============================================================
# STEP 15 - STRICT ROLLING-ORIGIN REVALIDATION
# Childhood Malnutrition Forecasting Research
#
# Models:
#   1. SARIMA
#   2. XGBoost
#   3. Random Forest
#   4. LightGBM
#   5. LSTM
#   6. NGBoost
#
# Main purpose:
# - Remove subtle future-information leakage
# - At each forecast origin, use only labels/information
#   available up to that origin
# - Refit preprocessing using only the available history
# - Evaluate H1, H3 and H6 on 2024
#
# IMPORTANT:
# - 2025 TEST data is NOT loaded
# - Hyperparameter tuning is NOT performed here
# - This step validates the initial candidate models
#   using a stricter walk-forward / rolling-origin design
# - TFT is intentionally NOT included here.
#   It should be validated separately in Step 15B.
# ============================================================

from pathlib import Path
import warnings
import random
import copy

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import norm

from statsmodels.tsa.statespace.sarimax import SARIMAX

from xgboost import XGBRegressor

from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import StandardScaler

try:
    from lightgbm import LGBMRegressor
except ImportError:
    LGBMRegressor = None

from ngboost import NGBRegressor
from ngboost.distns import Normal
from ngboost.scores import LogScore

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader


# ============================================================
# 1. GENERAL SETTINGS
# ============================================================

warnings.filterwarnings("ignore")

RANDOM_STATE = 42

HORIZONS = [1, 3, 6]

TARGET = "Forecast_Target"
RAW_TARGET = "Malnutrition_Cases"
SEQUENCE_LENGTH = 12

# LSTM settings
LSTM_HIDDEN_SIZE = 64
LSTM_BATCH_SIZE = 64
LSTM_MAX_EPOCHS = 30
LSTM_PATIENCE = 5
LSTM_LEARNING_RATE = 0.001


# ============================================================
# 2. REPRODUCIBILITY
# ============================================================

def set_random_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


set_random_seed(RANDOM_STATE)
DEVICE = torch.device("cpu")


# ============================================================
# 3. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SPLIT_DIR = BASE_DIR / "data" / "splits"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "outputs" / "reports"
FIGURE_DIR = BASE_DIR / "outputs" / "figures"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

BASE_DATA_PATH = PROCESSED_DIR / "malnutrition_preprocessed_base.csv"


# ============================================================
# 4. INTRODUCTION
# ============================================================

print("\n" + "=" * 115)
print("STEP 15 - STRICT ROLLING-ORIGIN REVALIDATION")
print("=" * 115)

print("\nLeakage-control rule:")
print("- For every forecast origin, training labels must have")
print("  Forecast_Target_Date <= Forecast_Origin_Date")
print("- Imputation is fitted only on the history available")
print("  at that forecast origin")
print("- Models are retrained as the forecast origin moves")
print("- 2024 is the validation period")
print("- 2025 test data is NOT loaded")
print("- Hyperparameter tuning is NOT performed in Step 15")
print("- Random Forest and LightGBM are added in this updated version")
print("- TFT should be handled separately in Step 15B")


# ============================================================
# 5. METRICS
# ============================================================

def calculate_mae(y_true, y_pred):
    return float(np.mean(np.abs(y_true - y_pred)))


def calculate_rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def calculate_wape(y_true, y_pred):
    denominator = np.sum(np.abs(y_true))
    if denominator == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denominator * 100)


def calculate_smape(y_true, y_pred):
    denominator = np.abs(y_true) + np.abs(y_pred)
    numerator = 2 * np.abs(y_true - y_pred)
    valid = denominator != 0
    if valid.sum() == 0:
        return np.nan
    return float(np.mean(numerator[valid] / denominator[valid]) * 100)


def calculate_r2(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return np.nan
    return float(1 - ss_res / ss_tot)


def calculate_metric_record(dataframe, model_name, horizon):
    valid_df = dataframe[dataframe["Prediction"].notna()].copy()

    if len(valid_df) == 0:
        return {
            "Horizon_Months": horizon,
            "Model": model_name,
            "Total_Validation_Rows": len(dataframe),
            "Evaluated_Rows": 0,
            "Coverage_Percentage": 0,
            "MAE": np.nan,
            "RMSE": np.nan,
            "WAPE_Percentage": np.nan,
            "sMAPE_Percentage": np.nan,
            "R2": np.nan,
        }

    y_true = valid_df["Actual_Target"].to_numpy(dtype=float)
    y_pred = valid_df["Prediction"].to_numpy(dtype=float)

    return {
        "Horizon_Months": horizon,
        "Model": model_name,
        "Total_Validation_Rows": len(dataframe),
        "Evaluated_Rows": len(valid_df),
        "Coverage_Percentage": len(valid_df) / len(dataframe) * 100,
        "MAE": calculate_mae(y_true, y_pred),
        "RMSE": calculate_rmse(y_true, y_pred),
        "WAPE_Percentage": calculate_wape(y_true, y_pred),
        "sMAPE_Percentage": calculate_smape(y_true, y_pred),
        "R2": calculate_r2(y_true, y_pred),
    }


# ============================================================
# 6. LOAD HORIZON DATA
# ============================================================

horizon_data = {}

for horizon in HORIZONS:
    train_path = SPLIT_DIR / f"h{horizon}_train.csv"
    validation_path = SPLIT_DIR / f"h{horizon}_validation.csv"
    manifest_path = REPORT_DIR / f"09_h{horizon}_usable_feature_manifest.csv"

    if not train_path.exists():
        raise FileNotFoundError(train_path)
    if not validation_path.exists():
        raise FileNotFoundError(validation_path)
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    train_df = pd.read_csv(train_path)
    validation_df = pd.read_csv(validation_path)
    feature_manifest = pd.read_csv(manifest_path)

    for df in [train_df, validation_df]:
        df["Forecast_Origin_Date"] = pd.to_datetime(df["Forecast_Origin_Date"])
        df["Forecast_Target_Date"] = pd.to_datetime(df["Forecast_Target_Date"])

        if "Data_Split" not in df.columns:
            df["Data_Split"] = "TRAIN" if df is train_df else "VALIDATION"

    train_df = train_df[train_df[TARGET].notna()].copy()
    validation_df = validation_df[validation_df[TARGET].notna()].copy()

    all_df = pd.concat([train_df, validation_df], ignore_index=True)
    all_df = all_df.sort_values(["Forecast_Origin_Date", "District"]).reset_index(drop=True)

    feature_columns = feature_manifest["Feature"].tolist()

    horizon_data[horizon] = {
        "train": train_df,
        "validation": validation_df,
        "all": all_df,
        "features": feature_columns,
    }

    print(f"\nH{horizon}: train={len(train_df)}, validation={len(validation_df)}, features={len(feature_columns)}")


# ============================================================
# 7. FIND EARLIEST VALIDATION FORECAST ORIGIN
# ============================================================

all_validation_origins = []
for horizon in HORIZONS:
    all_validation_origins.extend(horizon_data[horizon]["validation"]["Forecast_Origin_Date"].tolist())

earliest_validation_origin = min(all_validation_origins)
sarima_order_calibration_cutoff = earliest_validation_origin - pd.DateOffset(months=1)

print("\nEarliest validation forecast origin:")
print(earliest_validation_origin)
print("SARIMA order calibration cutoff:")
print(sarima_order_calibration_cutoff)


# ============================================================
# 8. TRAIN-ONLY MEDIAN IMPUTATION
# ============================================================

def fit_feature_medians(dataframe, feature_columns):
    medians = dataframe[feature_columns].median()
    all_missing_features = medians[medians.isna()].index.tolist()
    if all_missing_features:
        medians.loc[all_missing_features] = 0.0
    return medians, all_missing_features


def build_tree_matrices(training_dataframe, prediction_dataframe, feature_columns):
    medians, all_missing_features = fit_feature_medians(training_dataframe, feature_columns)

    X_train_numeric = training_dataframe[feature_columns].fillna(medians).astype(float).reset_index(drop=True)
    X_prediction_numeric = prediction_dataframe[feature_columns].fillna(medians).astype(float).reset_index(drop=True)

    train_dummies = pd.get_dummies(training_dataframe["District"], prefix="District", dtype=float).reset_index(drop=True)
    prediction_dummies = pd.get_dummies(prediction_dataframe["District"], prefix="District", dtype=float)
    prediction_dummies = prediction_dummies.reindex(columns=train_dummies.columns, fill_value=0).reset_index(drop=True)

    X_train = pd.concat([X_train_numeric, train_dummies], axis=1)
    X_prediction = pd.concat([X_prediction_numeric, prediction_dummies], axis=1)
    y_train = training_dataframe[TARGET].to_numpy(dtype=float)

    return X_train, y_train, X_prediction, all_missing_features


def run_strict_tree_model(model_name, model_builder, output_file_name):
    predictions = []

    print("\n" + "=" * 115)
    print(f"STRICT {model_name.upper()} REVALIDATION")
    print("=" * 115)

    for horizon in HORIZONS:
        print(f"\nH{horizon} {model_name}")

        all_df = horizon_data[horizon]["all"].copy()
        validation_df = horizon_data[horizon]["validation"].copy()
        feature_columns = horizon_data[horizon]["features"]

        origins = sorted(validation_df["Forecast_Origin_Date"].unique())

        for origin_counter, origin_date in enumerate(origins, start=1):
            prediction_rows = validation_df[validation_df["Forecast_Origin_Date"] == origin_date].copy()
            training_pool = all_df[all_df["Forecast_Target_Date"] <= origin_date].copy()

            if len(training_pool) == 0:
                continue

            X_train, y_train, X_prediction, _ = build_tree_matrices(
                training_pool,
                prediction_rows,
                feature_columns,
            )

            model = model_builder()

            # Convert pandas feature matrices to NumPy arrays.
            # XGBoost does not allow feature names containing [, ] or <.
            # This keeps the same feature values and feature order, while
            # avoiding feature-name restrictions in XGBoost/LightGBM.
            X_train_model = np.asarray(X_train, dtype=np.float32)
            X_prediction_model = np.asarray(X_prediction, dtype=np.float32)
            y_train_model = np.asarray(y_train, dtype=np.float32).ravel()

            model.fit(X_train_model, y_train_model)
            horizon_predictions = model.predict(X_prediction_model)

            print(
                f"H{horizon} origin {origin_counter}/{len(origins)} "
                f"| {pd.Timestamp(origin_date).date()} | train={len(training_pool)}"
            )

            for row_index, (_, row) in enumerate(prediction_rows.iterrows()):
                predictions.append({
                    "Model": model_name,
                    "Horizon_Months": horizon,
                    "District": row["District"],
                    "Forecast_Origin_Date": origin_date,
                    "Forecast_Target_Date": row["Forecast_Target_Date"],
                    "Actual_Target": float(row[TARGET]),
                    "Prediction": float(horizon_predictions[row_index]),
                })

    prediction_df = pd.DataFrame(predictions)
    prediction_df.to_csv(REPORT_DIR / output_file_name, index=False)
    return prediction_df


# ============================================================
# 9. SARIMA STRICT ROLLING VALIDATION
# ============================================================

print("\n" + "=" * 115)
print("1. STRICT SARIMA REVALIDATION")
print("=" * 115)

if not BASE_DATA_PATH.exists():
    raise FileNotFoundError(BASE_DATA_PATH)

base_df = pd.read_csv(BASE_DATA_PATH)
base_df["Date"] = pd.to_datetime(base_df["Date"])
base_df = base_df.sort_values(["District", "Date"])

SARIMA_ORDERS = [
    (1, 0, 0),
    (0, 0, 1),
    (0, 1, 0),
    (1, 1, 0),
    (0, 1, 1),
    (1, 1, 1),
]

SARIMA_SEASONAL_ORDERS = [
    (0, 0, 0, 12),
    (1, 0, 0, 12),
    (0, 0, 1, 12),
    (1, 0, 1, 12),
    (1, 1, 0, 12),
    (0, 1, 1, 12),
]

selected_sarima_orders = []
districts = sorted(base_df["District"].unique())

print("\nSelecting fixed SARIMA structure using data only up to:")
print(sarima_order_calibration_cutoff)

for district in districts:
    district_history = base_df[
        (base_df["District"] == district)
        & (base_df["Date"] <= sarima_order_calibration_cutoff)
    ][["Date", RAW_TARGET]].copy()

    district_history = district_history.set_index("Date")[RAW_TARGET].astype(float)

    best_aic = np.inf
    best_order = None
    best_seasonal_order = None

    for order in SARIMA_ORDERS:
        for seasonal_order in SARIMA_SEASONAL_ORDERS:
            try:
                model = SARIMAX(
                    district_history,
                    order=order,
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                result = model.fit(disp=False, maxiter=100)

                if np.isfinite(result.aic) and result.aic < best_aic:
                    best_aic = result.aic
                    best_order = order
                    best_seasonal_order = seasonal_order
            except Exception:
                continue

    if best_order is None:
        best_order = (0, 1, 1)
        best_seasonal_order = (0, 1, 1, 12)

    selected_sarima_orders.append({
        "District": district,
        "Order": best_order,
        "Seasonal_Order": best_seasonal_order,
        "Calibration_AIC": best_aic,
    })

    print(f"{district:15s} -> SARIMA{best_order}x{best_seasonal_order}")

sarima_order_df = pd.DataFrame(selected_sarima_orders)
sarima_order_df.to_csv(REPORT_DIR / "15_strict_sarima_selected_orders.csv", index=False)

sarima_order_lookup = {
    row["District"]: (row["Order"], row["Seasonal_Order"])
    for row in selected_sarima_orders
}

sarima_requests = []
for horizon in HORIZONS:
    validation_df = horizon_data[horizon]["validation"].copy()
    validation_df["Horizon_Months"] = horizon
    sarima_requests.append(validation_df)

sarima_requests = pd.concat(sarima_requests, ignore_index=True)
sarima_predictions = []
grouped_requests = list(sarima_requests.groupby(["District", "Forecast_Origin_Date"]))

print(f"\nSARIMA rolling-origin groups: {len(grouped_requests)}")

for counter, ((district, origin_date), request_group) in enumerate(grouped_requests, start=1):
    if counter == 1 or counter % 25 == 0:
        print(f"Processing SARIMA origin {counter}/{len(grouped_requests)}")

    order, seasonal_order = sarima_order_lookup[district]

    history = base_df[
        (base_df["District"] == district)
        & (base_df["Date"] <= origin_date)
    ][["Date", RAW_TARGET]].copy()

    history = history.set_index("Date")[RAW_TARGET].astype(float)
    max_horizon = int(request_group["Horizon_Months"].max())

    predictions = None
    try:
        model = SARIMAX(
            history,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        result = model.fit(disp=False, maxiter=100)
        predictions = np.asarray(result.forecast(steps=max_horizon), dtype=float)
    except Exception:
        predictions = None

    for _, request in request_group.iterrows():
        horizon = int(request["Horizon_Months"])
        if predictions is not None and len(predictions) >= horizon:
            prediction = float(predictions[horizon - 1])
        else:
            prediction = np.nan

        sarima_predictions.append({
            "Model": "SARIMA",
            "Horizon_Months": horizon,
            "District": district,
            "Forecast_Origin_Date": origin_date,
            "Forecast_Target_Date": request["Forecast_Target_Date"],
            "Actual_Target": float(request[TARGET]),
            "Prediction": prediction,
        })

sarima_prediction_df = pd.DataFrame(sarima_predictions)
sarima_prediction_df.to_csv(REPORT_DIR / "15_strict_sarima_predictions.csv", index=False)


# ============================================================
# 10. STRICT XGBOOST VALIDATION
# ============================================================

xgboost_prediction_df = run_strict_tree_model(
    model_name="XGBoost",
    model_builder=lambda: XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        max_depth=6,
        learning_rate=0.3,
        subsample=1.0,
        colsample_bytree=1.0,
        reg_lambda=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        tree_method="hist",
    ),
    output_file_name="15_strict_xgboost_predictions.csv",
)


# ============================================================
# 11. STRICT RANDOM FOREST VALIDATION
# ============================================================

random_forest_prediction_df = run_strict_tree_model(
    model_name="Random Forest",
    model_builder=lambda: RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features="sqrt",
        bootstrap=True,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    ),
    output_file_name="15_strict_random_forest_predictions.csv",
)


# ============================================================
# 12. STRICT LIGHTGBM VALIDATION
# ============================================================

if LGBMRegressor is None:
    raise ImportError(
        "lightgbm is not installed. Install it before running Step 15: pip install lightgbm"
    )

lightgbm_prediction_df = run_strict_tree_model(
    model_name="LightGBM",
    model_builder=lambda: LGBMRegressor(
        objective="regression",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        subsample=1.0,
        colsample_bytree=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=-1,
    ),
    output_file_name="15_strict_lightgbm_predictions.csv",
)


# ============================================================
# 13. STRICT NGBOOST VALIDATION
# ============================================================

print("\n" + "=" * 115)
print("STRICT NGBOOST REVALIDATION")
print("=" * 115)

ngboost_predictions = []

for horizon in HORIZONS:
    print(f"\nH{horizon} NGBoost")

    all_df = horizon_data[horizon]["all"].copy()
    validation_df = horizon_data[horizon]["validation"].copy()
    feature_columns = horizon_data[horizon]["features"]

    origins = sorted(validation_df["Forecast_Origin_Date"].unique())

    for origin_counter, origin_date in enumerate(origins, start=1):
        prediction_rows = validation_df[validation_df["Forecast_Origin_Date"] == origin_date].copy()
        training_pool = all_df[all_df["Forecast_Target_Date"] <= origin_date].copy()

        if len(training_pool) == 0:
            continue

        X_train, y_train, X_prediction, _ = build_tree_matrices(
            training_pool,
            prediction_rows,
            feature_columns,
        )

        base_learner = DecisionTreeRegressor(
            criterion="friedman_mse",
            max_depth=3,
            min_samples_leaf=10,
            random_state=RANDOM_STATE,
        )

        model = NGBRegressor(
            Dist=Normal,
            Score=LogScore,
            Base=base_learner,
            natural_gradient=True,
            n_estimators=300,
            learning_rate=0.03,
            minibatch_frac=1.0,
            col_sample=1.0,
            verbose=False,
            random_state=RANDOM_STATE,
        )

        model.fit(X_train, y_train)
        point_predictions = model.predict(X_prediction)
        distribution = model.pred_dist(X_prediction)

        predicted_mean = np.asarray(distribution.params["loc"], dtype=float)
        predicted_sd = np.asarray(distribution.params["scale"], dtype=float)
        predicted_sd = np.maximum(predicted_sd, 1e-8)

        z_95 = norm.ppf(0.975)
        lower_95 = predicted_mean - z_95 * predicted_sd
        upper_95 = predicted_mean + z_95 * predicted_sd

        print(
            f"H{horizon} origin {origin_counter}/{len(origins)} "
            f"| {pd.Timestamp(origin_date).date()} | train={len(training_pool)}"
        )

        for row_index, (_, row) in enumerate(prediction_rows.iterrows()):
            actual = float(row[TARGET])
            ngboost_predictions.append({
                "Model": "NGBoost",
                "Horizon_Months": horizon,
                "District": row["District"],
                "Forecast_Origin_Date": origin_date,
                "Forecast_Target_Date": row["Forecast_Target_Date"],
                "Actual_Target": actual,
                "Prediction": float(point_predictions[row_index]),
                "Predicted_SD": float(predicted_sd[row_index]),
                "Lower_95": float(lower_95[row_index]),
                "Upper_95": float(upper_95[row_index]),
                "Covered_By_95": bool(actual >= lower_95[row_index] and actual <= upper_95[row_index]),
            })

ngboost_prediction_df = pd.DataFrame(ngboost_predictions)
ngboost_prediction_df.to_csv(REPORT_DIR / "15_strict_ngboost_predictions.csv", index=False)


# ============================================================
# 14. LSTM MODEL
# ============================================================

class LSTMRegressor(nn.Module):
    def __init__(self, input_size, hidden_size=64):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )
        self.dropout = nn.Dropout(0.20)
        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x):
        sequence_output, _ = self.lstm(x)
        final_hidden = sequence_output[:, -1, :]
        final_hidden = self.dropout(final_hidden)
        return self.output_layer(final_hidden)


# ============================================================
# 15. LSTM SEQUENCE HELPERS
# ============================================================

def consecutive_months(date_series):
    periods = pd.Series(date_series).dt.to_period("M").astype(int).to_numpy()
    if len(periods) <= 1:
        return True
    return bool(np.all(np.diff(periods) == 1))


def build_all_sequences(dataframe, feature_columns):
    x_values = []
    y_values = []
    metadata = []

    for district, district_df in dataframe.groupby("District"):
        district_df = district_df.sort_values("Forecast_Origin_Date").reset_index(drop=True)

        for index in range(SEQUENCE_LENGTH - 1, len(district_df)):
            window = district_df.iloc[index - SEQUENCE_LENGTH + 1 : index + 1]
            current_row = district_df.iloc[index]

            if not consecutive_months(window["Forecast_Origin_Date"]):
                continue

            x_window = window[feature_columns].to_numpy(dtype=np.float32)
            x_values.append(x_window)
            y_values.append(float(current_row[TARGET]))
            metadata.append({
                "District": district,
                "Forecast_Origin_Date": current_row["Forecast_Origin_Date"],
                "Forecast_Target_Date": current_row["Forecast_Target_Date"],
                "Data_Split": current_row.get("Data_Split", "UNKNOWN"),
            })

    return (
        np.asarray(x_values, dtype=np.float32),
        np.asarray(y_values, dtype=np.float32),
        pd.DataFrame(metadata),
    )


# ============================================================
# 16. LSTM IMPUTATION
# ============================================================

def fit_sequence_medians(x):
    flattened = x.reshape(-1, x.shape[-1])
    medians = np.nanmedian(flattened, axis=0)
    medians = np.where(np.isnan(medians), 0.0, medians)
    return medians


def apply_sequence_medians(x, medians):
    result = x.copy()
    for feature_index in range(result.shape[-1]):
        values = result[:, :, feature_index]
        missing_mask = np.isnan(values)
        values[missing_mask] = medians[feature_index]
        result[:, :, feature_index] = values
    return result.astype(np.float32)


def fit_sequence_scaler(x):
    scaler = StandardScaler()
    flattened = x.reshape(-1, x.shape[-1])
    scaler.fit(flattened)
    return scaler


def apply_sequence_scaler(x, scaler):
    original_shape = x.shape
    flattened = x.reshape(-1, x.shape[-1])
    scaled = scaler.transform(flattened)
    return scaled.reshape(original_shape).astype(np.float32)


# ============================================================
# 17. LSTM EARLY STOPPING
# ============================================================

def train_lstm_with_early_stopping(x_train, y_train, x_validation, y_validation, input_size, seed):
    set_random_seed(seed)

    model = LSTMRegressor(input_size=input_size, hidden_size=LSTM_HIDDEN_SIZE).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LSTM_LEARNING_RATE)
    criterion = nn.MSELoss()

    train_dataset = TensorDataset(
        torch.tensor(x_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32).reshape(-1, 1),
    )
    train_loader = DataLoader(train_dataset, batch_size=LSTM_BATCH_SIZE, shuffle=True)

    validation_x_tensor = torch.tensor(x_validation, dtype=torch.float32, device=DEVICE)
    validation_y_tensor = torch.tensor(y_validation, dtype=torch.float32, device=DEVICE).reshape(-1, 1)

    best_state = None
    best_loss = np.inf
    best_epoch = 1
    no_improvement = 0

    for epoch in range(1, LSTM_MAX_EPOCHS + 1):
        model.train()
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(DEVICE)
            batch_y = batch_y.to(DEVICE)
            optimizer.zero_grad()
            prediction = model(batch_x)
            loss = criterion(prediction, batch_y)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            validation_prediction = model(validation_x_tensor)
            validation_loss = criterion(validation_prediction, validation_y_tensor).item()

        if validation_loss < best_loss:
            best_loss = validation_loss
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            no_improvement = 0
        else:
            no_improvement += 1

        if no_improvement >= LSTM_PATIENCE:
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, best_epoch


def train_lstm_fixed_epochs(x_train, y_train, input_size, epochs, seed):
    set_random_seed(seed)

    model = LSTMRegressor(input_size=input_size, hidden_size=LSTM_HIDDEN_SIZE).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LSTM_LEARNING_RATE)
    criterion = nn.MSELoss()

    dataset = TensorDataset(
        torch.tensor(x_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32).reshape(-1, 1),
    )
    loader = DataLoader(dataset, batch_size=LSTM_BATCH_SIZE, shuffle=True)

    for _ in range(epochs):
        model.train()
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(DEVICE)
            batch_y = batch_y.to(DEVICE)
            optimizer.zero_grad()
            prediction = model(batch_x)
            loss = criterion(prediction, batch_y)
            loss.backward()
            optimizer.step()

    return model


def predict_lstm(model, x):
    model.eval()
    with torch.no_grad():
        tensor = torch.tensor(x, dtype=torch.float32, device=DEVICE)
        prediction = model(tensor)
    return prediction.cpu().numpy().reshape(-1)


# ============================================================
# 18. STRICT LSTM VALIDATION
# ============================================================

print("\n" + "=" * 115)
print("STRICT LSTM REVALIDATION")
print("=" * 115)

lstm_predictions = []
lstm_training_summary = []

for horizon in HORIZONS:
    print(f"\nPreparing H{horizon} LSTM sequences...")

    all_df = horizon_data[horizon]["all"].copy()
    validation_df = horizon_data[horizon]["validation"].copy()
    numeric_features = horizon_data[horizon]["features"]

    district_dummies = pd.get_dummies(all_df["District"], prefix="District", dtype=float)
    all_augmented = pd.concat([all_df.reset_index(drop=True), district_dummies.reset_index(drop=True)], axis=1)
    model_features = numeric_features + district_dummies.columns.tolist()

    all_sequences, all_sequence_targets, sequence_metadata = build_all_sequences(all_augmented, model_features)

    sequence_metadata["Forecast_Origin_Date"] = pd.to_datetime(sequence_metadata["Forecast_Origin_Date"])
    sequence_metadata["Forecast_Target_Date"] = pd.to_datetime(sequence_metadata["Forecast_Target_Date"])

    origins = sorted(validation_df["Forecast_Origin_Date"].unique())

    for origin_counter, origin_date in enumerate(origins, start=1):
        training_mask = sequence_metadata["Forecast_Target_Date"] <= origin_date
        prediction_mask = (
            (sequence_metadata["Forecast_Origin_Date"] == origin_date)
            & (sequence_metadata["Data_Split"] == "VALIDATION")
        )

        x_train_all = all_sequences[training_mask.to_numpy()]
        y_train_all = all_sequence_targets[training_mask.to_numpy()]
        train_meta = sequence_metadata[training_mask].reset_index(drop=True)
        x_prediction = all_sequences[prediction_mask.to_numpy()]
        prediction_meta = sequence_metadata[prediction_mask].reset_index(drop=True)

        if len(x_train_all) == 0 or len(x_prediction) == 0:
            print(f"H{horizon} {origin_date}: insufficient LSTM sequences")
            continue
        unique_target_dates = train_meta["Forecast_Target_Date"].sort_values().drop_duplicates().tolist()
        if len(unique_target_dates) < 24:
            raise ValueError(f"H{horizon}: not enough historical months for internal LSTM validation.")

        internal_validation_dates = set(unique_target_dates[-12:])
        internal_validation_mask = train_meta["Forecast_Target_Date"].isin(internal_validation_dates)
        core_training_mask = ~internal_validation_mask

        x_core = x_train_all[core_training_mask.to_numpy()]
        y_core = y_train_all[core_training_mask.to_numpy()]
        x_internal_validation = x_train_all[internal_validation_mask.to_numpy()]
        y_internal_validation = y_train_all[internal_validation_mask.to_numpy()]

        core_medians = fit_sequence_medians(x_core)
        x_core_imputed = apply_sequence_medians(x_core, core_medians)
        x_internal_imputed = apply_sequence_medians(x_internal_validation, core_medians)

        core_feature_scaler = fit_sequence_scaler(x_core_imputed)
        x_core_scaled = apply_sequence_scaler(x_core_imputed, core_feature_scaler)
        x_internal_scaled = apply_sequence_scaler(x_internal_imputed, core_feature_scaler)

        core_target_scaler = StandardScaler()
        y_core_scaled = core_target_scaler.fit_transform(y_core.reshape(-1, 1)).reshape(-1).astype(np.float32)
        y_internal_scaled = core_target_scaler.transform(y_internal_validation.reshape(-1, 1)).reshape(-1).astype(np.float32)

        seed = int(pd.Timestamp(origin_date).strftime("%Y%m")) + horizon
        _, best_epoch = train_lstm_with_early_stopping(
            x_core_scaled,
            y_core_scaled,
            x_internal_scaled,
            y_internal_scaled,
            input_size=len(model_features),
            seed=seed,
        )

        full_medians = fit_sequence_medians(x_train_all)
        x_train_imputed = apply_sequence_medians(x_train_all, full_medians)
        x_prediction_imputed = apply_sequence_medians(x_prediction, full_medians)

        full_feature_scaler = fit_sequence_scaler(x_train_imputed)
        x_train_scaled = apply_sequence_scaler(x_train_imputed, full_feature_scaler)
        x_prediction_scaled = apply_sequence_scaler(x_prediction_imputed, full_feature_scaler)

        target_scaler = StandardScaler()
        y_train_scaled = target_scaler.fit_transform(y_train_all.reshape(-1, 1)).reshape(-1).astype(np.float32)

        final_model = train_lstm_fixed_epochs(
            x_train_scaled,
            y_train_scaled,
            input_size=len(model_features),
            epochs=best_epoch,
            seed=seed,
        )

        scaled_prediction = predict_lstm(final_model, x_prediction_scaled)
        predictions = target_scaler.inverse_transform(scaled_prediction.reshape(-1, 1)).reshape(-1)

        print(
            f"H{horizon} origin {origin_counter}/{len(origins)} "
            f"| {pd.Timestamp(origin_date).date()} | sequences={len(x_train_all)} | epoch={best_epoch}"
        )

        lstm_training_summary.append({
            "Horizon_Months": horizon,
            "Forecast_Origin_Date": origin_date,
            "Training_Sequences": len(x_train_all),
            "Best_Epoch": best_epoch,
        })

        prediction_indices = np.where(prediction_mask.to_numpy())[0]

        for row_index in range(len(prediction_meta)):
            row = prediction_meta.iloc[row_index]
            lstm_predictions.append({
                "Model": "LSTM",
                "Horizon_Months": horizon,
                "District": row["District"],
                "Forecast_Origin_Date": row["Forecast_Origin_Date"],
                "Forecast_Target_Date": row["Forecast_Target_Date"],
                "Actual_Target": float(all_sequence_targets[prediction_indices[row_index]]),
                "Prediction": float(predictions[row_index]),
            })

lstm_prediction_df = pd.DataFrame(lstm_predictions)
lstm_prediction_df.to_csv(REPORT_DIR / "15_strict_lstm_predictions.csv", index=False)

pd.DataFrame(lstm_training_summary).to_csv(
    REPORT_DIR / "15_strict_lstm_training_summary.csv",
    index=False,
)


# ============================================================
# 19. COMBINE STRICT PREDICTIONS
# ============================================================

all_prediction_frames = [
    sarima_prediction_df,
    xgboost_prediction_df,
    random_forest_prediction_df,
    lightgbm_prediction_df,
    ngboost_prediction_df,
    lstm_prediction_df,
]

all_predictions_df = pd.concat(all_prediction_frames, ignore_index=True, sort=False)
all_predictions_df.to_csv(REPORT_DIR / "15_strict_all_model_predictions.csv", index=False)


# ============================================================
# 20. CALCULATE STRICT MODEL METRICS
# ============================================================

metric_records = []

model_names = [
    "SARIMA",
    "XGBoost",
    "Random Forest",
    "LightGBM",
    "LSTM",
    "NGBoost",
]

for model_name in model_names:
    for horizon in HORIZONS:
        model_horizon_df = all_predictions_df[
            (all_predictions_df["Model"] == model_name)
            & (all_predictions_df["Horizon_Months"] == horizon)
        ].copy()

        metric_records.append(
            calculate_metric_record(
                model_horizon_df,
                model_name,
                horizon,
            )
        )

strict_metrics_df = pd.DataFrame(metric_records)


# ============================================================
# 21. NGBOOST STRICT UNCERTAINTY METRICS
# ============================================================

ngboost_uncertainty_records = []

for horizon in HORIZONS:
    horizon_df = ngboost_prediction_df[ngboost_prediction_df["Horizon_Months"] == horizon].copy()

    coverage = horizon_df["Covered_By_95"].mean() * 100
    interval_width = horizon_df["Upper_95"] - horizon_df["Lower_95"]
    negative_lower_bounds = int((horizon_df["Lower_95"] < 0).sum())

    ngboost_uncertainty_records.append({
        "Horizon_Months": horizon,
        "Nominal_Coverage_Percentage": 95.0,
        "Observed_Coverage_Percentage": coverage,
        "Mean_Interval_Width": interval_width.mean(),
        "Median_Interval_Width": interval_width.median(),
        "Negative_Lower_Bounds": negative_lower_bounds,
    })

ngboost_uncertainty_df = pd.DataFrame(ngboost_uncertainty_records)
ngboost_uncertainty_df.to_csv(
    REPORT_DIR / "15_strict_ngboost_uncertainty_metrics.csv",
    index=False,
)


# ============================================================
# 22. ADD SEASONAL NAIVE REFERENCE
# ============================================================

baseline_path = REPORT_DIR / "10_baseline_validation_metrics.csv"
comparison_df = strict_metrics_df.copy()

if baseline_path.exists():
    baseline_df = pd.read_csv(baseline_path)
    seasonal_df = baseline_df[baseline_df["Baseline"] == "Seasonal Naive"].copy()

    seasonal_rows = []
    for _, row in seasonal_df.iterrows():
        seasonal_rows.append({
            "Horizon_Months": int(row["Horizon_Months"]),
            "Model": "Seasonal Naive",
            "Total_Validation_Rows": row.get("Total_Validation_Rows", np.nan),
            "Evaluated_Rows": row.get("Evaluated_Rows", np.nan),
            "Coverage_Percentage": row.get("Coverage_Percentage", 100.0),
            "MAE": row["MAE"],
            "RMSE": row["RMSE"],
            "WAPE_Percentage": row["WAPE_Percentage"],
            "sMAPE_Percentage": row["sMAPE_Percentage"],
            "R2": row["R2"],
        })

    comparison_df = pd.concat([comparison_df, pd.DataFrame(seasonal_rows)], ignore_index=True)

comparison_df = comparison_df.sort_values(["Horizon_Months", "MAE"]).reset_index(drop=True)


# ============================================================
# 23. PRINT RESULTS
# ============================================================

print("\n" + "=" * 115)
print("STRICT ROLLING-ORIGIN VALIDATION RESULTS")
print("=" * 115)
print(comparison_df.round(4).to_string(index=False))

strict_metrics_df.to_csv(REPORT_DIR / "15_strict_model_validation_metrics.csv", index=False)
comparison_df.to_csv(REPORT_DIR / "15_strict_model_comparison.csv", index=False)

print("\n" + "=" * 115)
print("STRICT NGBOOST UNCERTAINTY RESULTS")
print("=" * 115)
print(ngboost_uncertainty_df.round(4).to_string(index=False))


# ============================================================
# 24. MODEL COMPARISON FIGURE
# ============================================================

mae_pivot = comparison_df.pivot(index="Horizon_Months", columns="Model", values="MAE")
mae_pivot.plot(kind="bar", figsize=(12, 6))

plt.title("Strict Rolling-Origin Validation MAE")
plt.xlabel("Forecast Horizon (Months)")
plt.ylabel("MAE")
plt.xticks(rotation=0)
plt.legend(title="Model")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "15_strict_rolling_origin_mae_comparison.png", dpi=300)
plt.close()


# ============================================================
# 25. FINAL METHODOLOGY SUMMARY
# ============================================================

print("\n" + "=" * 115)
print("STEP 15 SUMMARY")
print("=" * 115)
print("Strict rolling-origin candidate-model revalidation completed.")

print("\nLeakage protection:")
print("- Every forecast was generated using only labels available by its forecast origin")
print("- Predictor imputation was re-fitted using the available historical training data")
print("- XGBoost, Random Forest, LightGBM and NGBoost were retrained at each forecast origin")
print("- LSTM preprocessing, scaling and epoch selection used historical data only")
print("- SARIMA structure was selected before the earliest validation forecast origin")
print("- SARIMA parameters were then re-fitted at each rolling forecast origin")
print("- H1, H3 and H6 were evaluated separately")
print("- 2024 remained the validation period")
print("- 2025 final test data was NOT loaded")

print("\nIMPORTANT:")
print("These results should replace the earlier initial candidate-model comparison when making the tuning decision.")

print("\nNEXT STEP:")
print("STEP 16 - Train-only temporal hyperparameter tuning")
print("TFT should be handled in separate Step 15B strict validation.")

print("\nReports saved to:")
print(REPORT_DIR)
print("\nFigures saved to:")
print(FIGURE_DIR)

print("\nSTEP 15 - STRICT ROLLING-ORIGIN REVALIDATION COMPLETE")
print("=" * 115)