import json

from app.config import (
    DASHBOARD_DIR,
    MANIFEST_FILE,
    METADATA_FILE,
)

from app.services.forecast_service import get_forecast_by_selected_month
from app.services.explainability_service import get_explanations_by_selected_month
from app.services.resource_service import get_resource_plan_by_selected_month
from app.services.map_service import get_priority_maps_by_selected_month
from app.services.trend_service import get_clinical_trend_by_selected_month
from app.services.district_service import (
    get_district_details_by_selected_month,
    get_district_trend_by_selected_month,
)


def get_dashboard_status():
    return {
        "dashboard_dir": str(DASHBOARD_DIR),
        "dashboard_dir_exists": DASHBOARD_DIR.exists(),
        "manifest_exists": MANIFEST_FILE.exists(),
        "metadata_exists": METADATA_FILE.exists(),
    }


def get_manifest():
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(
            f"Dashboard manifest not found: {MANIFEST_FILE}"
        )

    with open(
        MANIFEST_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_metadata():
    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {METADATA_FILE}"
        )

    with open(
        METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_dashboard_summary(
    year: int,
    month: int,
    district: str,
):
    """
    Build the dynamic dashboard payload using one doctor selection.

    Doctor selects only:
    - district
    - year
    - month

    H1, H3 and H6 are calculated automatically by the backend.

    Early-warning notifications are intentionally excluded because
    warnings use the current forecast origin independently of the
    doctor's selected month.
    """

    forecast = get_forecast_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    explainability = get_explanations_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    resources = get_resource_plan_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    gis = get_priority_maps_by_selected_month(
        year=year,
        month=month,
    )

    trend = get_clinical_trend_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    district_details = get_district_details_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    district_trend = get_district_trend_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    return {
        "selection": {
            "district": district,
            "year": year,
            "month": month,
        },
        "forecast_origin": forecast.get("forecast_origin"),
        "horizons": [1, 3, 6],
        "forecast": forecast,
        "explainability": explainability,
        "resource_planning": resources,
        "gis": gis,
        "trend_analysis": trend,
        "district_details": district_details,
        "district_trend": district_trend,
    }