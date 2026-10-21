import json
import pandas as pd

from app.config import (
    GIS_PRIORITY_FILE,
    DISTRICT_BOUNDARIES_FILE,
)


def load_gis_priority():
    if not GIS_PRIORITY_FILE.exists():
        raise FileNotFoundError(
            f"GIS priority file not found: {GIS_PRIORITY_FILE}"
        )

    return pd.read_csv(GIS_PRIORITY_FILE)


def load_boundaries():
    if not DISTRICT_BOUNDARIES_FILE.exists():
        raise FileNotFoundError(
            f"District boundaries file not found: {DISTRICT_BOUNDARIES_FILE}"
        )

    with open(
        DISTRICT_BOUNDARIES_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_priority_map(
    year: int,
    month: int,
    horizon: int,
):
    df = load_gis_priority()

    filtered = df[
        (df["Forecast_Year"] == year)
        & (df["Forecast_Month"] == month)
        & (df["Horizon_Months"] == horizon)
    ].copy()

    if filtered.empty:
        return None

    filtered = filtered.sort_values(
        "Priority_Rank"
    )

    records = []

    for _, row in filtered.iterrows():
        records.append(
            {
                "district": row["District"],
                "forecast_origin": row["Forecast_Origin_Date"],
                "target_date": row["Forecast_Target_Date"],
                "horizon": int(row["Horizon_Months"]),

                "predicted_cases": float(
                    row["RF_Predicted_Cases"]
                ),

                "cases_per_1000_u5": float(
                    row["Forecasted_Cases_per_1000_U5"]
                ),

                "yoy_growth_percent": float(
                    row["Forecasted_YoY_Burden_Growth_Percent"]
                ),

                "dmbi_score": float(
                    row["DMBI_Score"]
                ),

                "priority_rank": int(
                    row["Priority_Rank"]
                ),

                "priority_level": row["Priority_Level"],

                "priority_code": int(
                    row["Priority_Code"]
                ),

                "uncertainty_level": row[
                    "Uncertainty_Level"
                ],

                "confidence_label": row[
                    "Confidence_Label"
                ],

                "lower_95": float(
                    row["NGBoost_Lower_95"]
                ),

                "upper_95": float(
                    row["NGBoost_Upper_95"]
                ),

                "priority_interpretation": row[
                    "Priority_Interpretation"
                ],

                "uncertainty_interpretation": row[
                    "Uncertainty_Interpretation"
                ],
            }
        )

    return {
        "year": year,
        "month": month,
        "horizon": horizon,
        "count": len(records),
        "districts": records,
    }


def add_months(
    year: int,
    month: int,
    months_to_add: int,
):
    total_months = (
        year * 12
        + (month - 1)
        + months_to_add
    )

    new_year = total_months // 12
    new_month = (total_months % 12) + 1

    return new_year, new_month


def get_priority_maps_by_selected_month(
    year: int,
    month: int,
):
    # Doctor-selected month is the H1 target month.
    # Forecast origin is one month before the selected month.

    if month == 1:
        origin_year = year - 1
        origin_month = 12
    else:
        origin_year = year
        origin_month = month - 1

    priority_maps = {}

    # Selected month itself is H1.
    # H3 is 2 months after selected month.
    # H6 is 5 months after selected month.
    horizon_offsets = {
        1: 0,
        3: 2,
        6: 5,
    }

    for horizon, offset in horizon_offsets.items():
        target_year, target_month = add_months(
            year=year,
            month=month,
            months_to_add=offset,
        )

        result = get_priority_map(
            year=target_year,
            month=target_month,
            horizon=horizon,
        )

        if result is not None:
            priority_maps[f"h{horizon}"] = {
                "horizon": horizon,
                "target_year": target_year,
                "target_month": target_month,
                "count": result["count"],
                "districts": result["districts"],
            }

    if not priority_maps:
        return None

    return {
        "selected_year": year,
        "selected_month": month,
        "forecast_origin": (
            f"{origin_year:04d}-{origin_month:02d}-01"
        ),
        "origin_year": origin_year,
        "origin_month": origin_month,
        "available_horizons": [
            1,
            3,
            6,
        ],
        "priority_maps": priority_maps,
    }


def get_boundaries():
    return load_boundaries()