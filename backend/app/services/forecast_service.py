import json

from app.config import FORECAST_LOOKUP_FILE


def load_forecasts():
    if not FORECAST_LOOKUP_FILE.exists():
        raise FileNotFoundError(
            f"Forecast lookup file not found: {FORECAST_LOOKUP_FILE}"
        )

    with open(
        FORECAST_LOOKUP_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_forecast(year: int, month: int, district: str):
    data = load_forecasts()

    district_clean = district.strip().lower()

    for record in data:
        if (
            int(record["year"]) == year
            and int(record["month"]) == month
            and record["district"].strip().lower() == district_clean
        ):
            return record

    return None


def get_available_districts():
    data = load_forecasts()

    return sorted(
        {
            record["district"]
            for record in data
        }
    )


def get_available_origins():
    data = load_forecasts()

    origins = {}

    for record in data:
        year = int(record["year"])
        month = int(record["month"])

        origins[(year, month)] = {
            "year": year,
            "month": month,
            "month_name": record["month_name"],
            "forecast_origin": record["forecast_origin"],
        }

    return sorted(
        origins.values(),
        key=lambda x: (
            x["year"],
            x["month"],
        ),
    )


def get_forecast_by_selected_month(
    year: int,
    month: int,
    district: str,
):
    if month == 1:
        origin_year = year - 1
        origin_month = 12
    else:
        origin_year = year
        origin_month = month - 1

    result = get_forecast(
        year=origin_year,
        month=origin_month,
        district=district,
    )

    if result is None:
        return None

    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    return {
        "district": result["district"],
        "selected_year": year,
        "selected_month": month,
        "selected_month_name": month_names[month],
        "forecast_origin": result["forecast_origin"],
        "origin_year": origin_year,
        "origin_month": origin_month,
        "origin_month_name": month_names[origin_month],
        "available_horizons": result["available_horizons"],
        "forecasts": result["forecasts"],
    }