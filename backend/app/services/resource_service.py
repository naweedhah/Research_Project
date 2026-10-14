import pandas as pd

from app.config import RESOURCE_FILE


def load_resource_data():
    if not RESOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Resource planning file not found: {RESOURCE_FILE}"
        )

    return pd.read_csv(RESOURCE_FILE)


def get_resource_plan(
    year: int,
    month: int,
    district: str,
):
    df = load_resource_data()

    required_columns = [
        "District",
        "Forecast_Origin_Date",
        "Forecast_Target_Date",
        "Horizon_Months",
        "RF_Predicted_Cases",
        "Priority_Level",
        "DMBI_Score",
        "Estimated_Triposha_Packets_Planning",
        "Triposha_Packets_Lower_95",
        "Triposha_Packets_Upper_95",
        "Uncertainty_Level",
        "Confidence_Label",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df["Forecast_Origin_Date"] = pd.to_datetime(
        df["Forecast_Origin_Date"],
        errors="coerce",
    )

    df["Forecast_Target_Date"] = pd.to_datetime(
        df["Forecast_Target_Date"],
        errors="coerce",
    )

    district_clean = district.strip().lower()

    filtered = df[
        (df["Forecast_Origin_Date"].dt.year == year)
        & (df["Forecast_Origin_Date"].dt.month == month)
        & (
            df["District"]
            .astype(str)
            .str.strip()
            .str.lower()
            == district_clean
        )
    ].copy()

    if filtered.empty:
        return None

    filtered = filtered.sort_values(
        "Horizon_Months"
    )

    resource_plan = {}

    for _, row in filtered.iterrows():
        horizon = int(row["Horizon_Months"])
        horizon_key = f"h{horizon}"

        target_date = row["Forecast_Target_Date"]

        resource_plan[horizon_key] = {
            "horizon": horizon,

            "target_date": (
                target_date.strftime("%Y-%m-%d")
                if pd.notna(target_date)
                else None
            ),

            "target_month": (
                target_date.strftime("%Y-%m")
                if pd.notna(target_date)
                else None
            ),

            "predicted_cases": (
                float(row["RF_Predicted_Cases"])
                if pd.notna(row["RF_Predicted_Cases"])
                else None
            ),

            "priority_level": (
                str(row["Priority_Level"])
                if pd.notna(row["Priority_Level"])
                else None
            ),

            "dmbi_score": (
                float(row["DMBI_Score"])
                if pd.notna(row["DMBI_Score"])
                else None
            ),

            "triposha_packets": (
                int(row["Estimated_Triposha_Packets_Planning"])
                if pd.notna(
                    row["Estimated_Triposha_Packets_Planning"]
                )
                else None
            ),

            "triposha_lower_95": (
                int(row["Triposha_Packets_Lower_95"])
                if pd.notna(row["Triposha_Packets_Lower_95"])
                else None
            ),

            "triposha_upper_95": (
                int(row["Triposha_Packets_Upper_95"])
                if pd.notna(row["Triposha_Packets_Upper_95"])
                else None
            ),

            "uncertainty_level": (
                str(row["Uncertainty_Level"])
                if pd.notna(row["Uncertainty_Level"])
                else None
            ),

            "confidence_label": (
                str(row["Confidence_Label"])
                if pd.notna(row["Confidence_Label"])
                else None
            ),
        }

    return {
        "district": str(
            filtered.iloc[0]["District"]
        ),

        "forecast_origin": (
            filtered.iloc[0]["Forecast_Origin_Date"]
            .strftime("%Y-%m-%d")
        ),

        "year": year,
        "month": month,

        "available_horizons": sorted(
            [
                int(value)
                for value in filtered["Horizon_Months"].unique()
            ]
        ),

        "resource_plan": resource_plan,
    }


def get_resource_plan_by_selected_month(
    year: int,
    month: int,
    district: str,
):
    # Doctor-selected month is the H1 target month.
    # Forecast origin is one month before it.

    if month == 1:
        origin_year = year - 1
        origin_month = 12
    else:
        origin_year = year
        origin_month = month - 1

    result = get_resource_plan(
        year=origin_year,
        month=origin_month,
        district=district,
    )

    if result is None:
        return None

    return {
        "district": result["district"],
        "selected_year": year,
        "selected_month": month,
        "forecast_origin": result["forecast_origin"],
        "origin_year": origin_year,
        "origin_month": origin_month,
        "available_horizons": result["available_horizons"],
        "resource_plan": result["resource_plan"],
    }