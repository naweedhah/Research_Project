import pandas as pd

from app.config import DATASET_FILE

from app.services.forecast_service import (
    get_forecast_by_selected_month,
)


def load_dataset():
    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dashboard dataset file not found: {DATASET_FILE}"
        )

    return pd.read_csv(DATASET_FILE)


def _get_origin_from_selected_month(
    year: int,
    month: int,
):
    if month == 1:
        return year - 1, 12

    return year, month - 1


def _filter_district(
    df: pd.DataFrame,
    district: str,
):
    district_clean = district.strip().lower()

    filtered = df[
        df["District"]
        .astype(str)
        .str.strip()
        .str.lower()
        == district_clean
    ].copy()

    if filtered.empty:
        return None

    filtered["Year"] = pd.to_numeric(
        filtered["Year"],
        errors="coerce",
    )

    filtered["Month"] = pd.to_numeric(
        filtered["Month"],
        errors="coerce",
    )

    filtered = filtered.dropna(
        subset=["Year", "Month"]
    )

    filtered["Year"] = filtered["Year"].astype(int)
    filtered["Month"] = filtered["Month"].astype(int)

    return filtered.sort_values(
        ["Year", "Month"]
    )


def get_district_details(
    district: str,
):
    df = load_dataset()

    district_df = _filter_district(
        df=df,
        district=district,
    )

    if district_df is None:
        return None

    latest = district_df.iloc[-1]

    annual = (
        district_df
        .groupby("Year", as_index=False)
        .agg(
            total_cases=(
                "Malnutrition_Cases",
                "sum",
            ),
            mean_monthly_cases=(
                "Malnutrition_Cases",
                "mean",
            ),
            observations=(
                "Malnutrition_Cases",
                "count",
            ),
        )
    )

    annual_trend = []

    for _, row in annual.iterrows():
        annual_trend.append(
            {
                "year": int(row["Year"]),
                "total_cases": float(
                    row["total_cases"]
                ),
                "mean_monthly_cases": float(
                    row["mean_monthly_cases"]
                ),
                "observations": int(
                    row["observations"]
                ),
            }
        )

    return {
        "district": str(
            district_df.iloc[0]["District"]
        ),

        "period": {
            "start_year": int(
                district_df["Year"].min()
            ),
            "end_year": int(
                district_df["Year"].max()
            ),
            "observations": int(
                len(district_df)
            ),
        },

        "latest_observation": _row_to_details(
            latest
        ),

        "annual_trend": annual_trend,
    }


def _row_to_details(row):
    return {
        "year": int(row["Year"]),
        "month": int(row["Month"]),
        "month_name": str(
            row["Month_Name"]
        ),

        "malnutrition_cases": (
            float(row["Malnutrition_Cases"])
            if pd.notna(
                row["Malnutrition_Cases"]
            )
            else None
        ),

        "under_5_population": (
            int(row["Under 5 Population"])
            if pd.notna(
                row["Under 5 Population"]
            )
            else None
        ),

        "live_birth": (
            int(row["Live Birth"])
            if pd.notna(
                row["Live Birth"]
            )
            else None
        ),

        "triposha_packets_distributed": (
            int(
                row[
                    "Triposha_Packets_Distributed"
                ]
            )
            if pd.notna(
                row[
                    "Triposha_Packets_Distributed"
                ]
            )
            else None
        ),

        "poverty_line_rs_monthly": (
            float(
                row[
                    "Poverty_Line_Rs_Monthly"
                ]
            )
            if pd.notna(
                row[
                    "Poverty_Line_Rs_Monthly"
                ]
            )
            else None
        ),

        "low_birth_weight_cases": (
            float(
                row[
                    "Low_Birth_Weight_Cases"
                ]
            )
            if pd.notna(
                row[
                    "Low_Birth_Weight_Cases"
                ]
            )
            else None
        ),

        "temperature": (
            float(row["T2M"])
            if pd.notna(row["T2M"])
            else None
        ),

        "precipitation": (
            float(row["PRECTOTCORR"])
            if pd.notna(
                row["PRECTOTCORR"]
            )
            else None
        ),

        "relative_humidity": (
            float(row["RH2M"])
            if pd.notna(row["RH2M"])
            else None
        ),

        "household_income": (
            float(
                row["Household_Income"]
            )
            if pd.notna(
                row["Household_Income"]
            )
            else None
        ),
    }


def get_district_monthly_trend(
    district: str,
):
    df = load_dataset()

    filtered = _filter_district(
        df=df,
        district=district,
    )

    if filtered is None:
        return None

    records = []

    for _, row in filtered.iterrows():
        records.append(
            {
                "year": int(row["Year"]),
                "month": int(row["Month"]),
                "month_name": str(
                    row["Month_Name"]
                ),
                "malnutrition_cases": (
                    float(
                        row[
                            "Malnutrition_Cases"
                        ]
                    )
                    if pd.notna(
                        row[
                            "Malnutrition_Cases"
                        ]
                    )
                    else None
                ),
            }
        )

    return {
        "district": str(
            filtered.iloc[0]["District"]
        ),
        "count": len(records),
        "trend": records,
    }


def get_district_details_by_selected_month(
    year: int,
    month: int,
    district: str,
):
    df = load_dataset()

    district_df = _filter_district(
        df=df,
        district=district,
    )

    if district_df is None:
        return None

    origin_year, origin_month = (
        _get_origin_from_selected_month(
            year=year,
            month=month,
        )
    )

    historical = district_df[
        (
            district_df["Year"]
            < origin_year
        )
        |
        (
            (
                district_df["Year"]
                == origin_year
            )
            &
            (
                district_df["Month"]
                <= origin_month
            )
        )
    ].copy()

    if historical.empty:
        return None

    latest = historical.iloc[-1]

    annual = (
        historical
        .groupby("Year", as_index=False)
        .agg(
            total_cases=(
                "Malnutrition_Cases",
                "sum",
            ),
            mean_monthly_cases=(
                "Malnutrition_Cases",
                "mean",
            ),
            observations=(
                "Malnutrition_Cases",
                "count",
            ),
        )
    )

    annual_trend = []

    for _, row in annual.iterrows():
        annual_trend.append(
            {
                "year": int(row["Year"]),
                "total_cases": float(
                    row["total_cases"]
                ),
                "mean_monthly_cases": round(
                    float(
                        row[
                            "mean_monthly_cases"
                        ]
                    ),
                    2,
                ),
                "observations": int(
                    row["observations"]
                ),
            }
        )

    forecast = (
        get_forecast_by_selected_month(
            year=year,
            month=month,
            district=district,
        )
    )

    return {
        "district": str(
            historical.iloc[0]["District"]
        ),

        "selected_year": year,
        "selected_month": month,

        "forecast_origin": (
            f"{origin_year:04d}-"
            f"{origin_month:02d}-01"
        ),

        "latest_known_observation": (
            _row_to_details(latest)
        ),

        "historical_period": {
            "start_year": int(
                historical["Year"].min()
            ),
            "end_year": int(
                historical["Year"].max()
            ),
            "observations": int(
                len(historical)
            ),
        },

        "annual_trend": annual_trend,

        "forecast_outlook": (
            {
                "available_horizons": forecast[
                    "available_horizons"
                ],
                "h1": forecast[
                    "forecasts"
                ].get("h1"),
                "h3": forecast[
                    "forecasts"
                ].get("h3"),
                "h6": forecast[
                    "forecasts"
                ].get("h6"),
            }
            if forecast
            else None
        ),
    }


def get_district_trend_by_selected_month(
    year: int,
    month: int,
    district: str,
):
    df = load_dataset()

    district_df = _filter_district(
        df=df,
        district=district,
    )

    if district_df is None:
        return None

    origin_year, origin_month = (
        _get_origin_from_selected_month(
            year=year,
            month=month,
        )
    )

    historical = district_df[
        (
            district_df["Year"]
            < origin_year
        )
        |
        (
            (
                district_df["Year"]
                == origin_year
            )
            &
            (
                district_df["Month"]
                <= origin_month
            )
        )
    ].copy()

    if historical.empty:
        return None

    # Only the most recent 12 observed months
    recent = historical.tail(12)

    observed_points = []

    for _, row in recent.iterrows():
        observed_points.append(
            {
                "year": int(row["Year"]),
                "month": int(row["Month"]),
                "month_name": str(
                    row["Month_Name"]
                ),
                "malnutrition_cases": (
                    float(
                        row[
                            "Malnutrition_Cases"
                        ]
                    )
                    if pd.notna(
                        row[
                            "Malnutrition_Cases"
                        ]
                    )
                    else None
                ),
            }
        )

    forecast = (
        get_forecast_by_selected_month(
            year=year,
            month=month,
            district=district,
        )
    )

    forecast_points = None

    if forecast:
        forecast_points = {
            "h1": forecast[
                "forecasts"
            ].get("h1"),
            "h3": forecast[
                "forecasts"
            ].get("h3"),
            "h6": forecast[
                "forecasts"
            ].get("h6"),
        }

    return {
        "district": str(
            historical.iloc[0]["District"]
        ),

        "selected_year": year,
        "selected_month": month,

        "forecast_origin": (
            f"{origin_year:04d}-"
            f"{origin_month:02d}-01"
        ),

        "observed_months_count": len(
            observed_points
        ),

        "recent_observed_trend": (
            observed_points
        ),

        "forecast_points": (
            forecast_points
        ),
    }