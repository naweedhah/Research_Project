from fastapi import APIRouter, HTTPException, Query

from app.services.district_service import (
    get_district_details_by_selected_month,
    get_district_trend_by_selected_month,
)


router = APIRouter(
    prefix="/districts",
    tags=["District Details"],
)


@router.get("/details/by-selected-month")
def district_details_by_selected_month(
    year: int = Query(..., ge=2026, le=2030),
    month: int = Query(..., ge=1, le=12),
    district: str = Query(..., min_length=1),
):
    try:
        result = get_district_details_by_selected_month(
            year=year,
            month=month,
            district=district,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="District details not found.",
        )

    return result


@router.get("/trend/by-selected-month")
def district_trend_by_selected_month(
    year: int = Query(..., ge=2026, le=2030),
    month: int = Query(..., ge=1, le=12),
    district: str = Query(..., min_length=1),
):
    try:
        result = get_district_trend_by_selected_month(
            year=year,
            month=month,
            district=district,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="District trend data not found.",
        )

    return result