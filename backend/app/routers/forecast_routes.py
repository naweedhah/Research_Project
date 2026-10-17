from fastapi import APIRouter, HTTPException, Query

from app.services.forecast_service import (
    get_forecast,
    get_available_districts,
    get_available_origins,
    get_forecast_by_selected_month,
)


router = APIRouter(
    tags=["Forecasts"],
)


@router.get("/")
def forecast(
    year: int = Query(..., ge=2025, le=2030),
    month: int = Query(..., ge=1, le=12),
    district: str = Query(..., min_length=1),
):
    try:
        result = get_forecast(
            year=year,
            month=month,
            district=district,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Forecast not found for the selected "
                "year, month and district."
            ),
        )

    return result


@router.get("/by-selected-month")
def forecast_by_selected_month(
    year: int = Query(
        ...,
        ge=2026,
        le=2030,
        description="Year selected by the doctor",
    ),
    month: int = Query(
        ...,
        ge=1,
        le=12,
        description="Month selected by the doctor",
    ),
    district: str = Query(
        ...,
        min_length=1,
    ),
):
    try:
        result = get_forecast_by_selected_month(
            year=year,
            month=month,
            district=district,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Forecast not found for the selected "
                "year, month and district."
            ),
        )

    return result


@router.get("/districts")
def districts():
    try:
        return {
            "districts": get_available_districts(),
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@router.get("/origins")
def forecast_origins():
    try:
        return {
            "origins": get_available_origins(),
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )