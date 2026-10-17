import json
from datetime import date

from app.config import SHAP_FILE


def load_shap_explanations():
    if not SHAP_FILE.exists():
        raise FileNotFoundError(
            f"SHAP explanation file not found: {SHAP_FILE}"
        )

    with open(
        SHAP_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_explanations(
    year: int,
    month: int,
    district: str,
):
    data = load_shap_explanations()

    district_clean = district.strip().lower()

    results = []

    for item in data:
        origin = item.get("forecast_origin")

        if not origin:
            continue

        origin_year = int(origin[:4])
        origin_month = int(origin[5:7])

        if (
            origin_year == year
            and origin_month == month
            and item["district"].strip().lower() == district_clean
        ):
            results.append(item)

    results = sorted(
        results,
        key=lambda x: x["horizon"],
    )

    return results


def get_explanations_by_selected_month(
    year: int,
    month: int,
    district: str,
):
    # Doctor-selected month is the H1 target month.
    # Therefore forecast origin is one month before the selected month.

    if month == 1:
        origin_year = year - 1
        origin_month = 12
    else:
        origin_year = year
        origin_month = month - 1

    results = get_explanations(
        year=origin_year,
        month=origin_month,
        district=district,
    )

    if not results:
        return None

    selected_month_name = date(
        year,
        month,
        1,
    ).strftime("%B")

    origin_month_name = date(
        origin_year,
        origin_month,
        1,
    ).strftime("%B")

    return {
        "district": district,
        "selected_year": year,
        "selected_month": month,
        "selected_month_name": selected_month_name,
        "forecast_origin": f"{origin_year:04d}-{origin_month:02d}-01",
        "origin_year": origin_year,
        "origin_month": origin_month,
        "origin_month_name": origin_month_name,
        "explanations": results,
    }