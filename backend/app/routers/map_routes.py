from fastapi import APIRouter, HTTPException, Query

from app.services.map_service import (
    get_priority_maps_by_selected_month,
    get_boundaries,
)


router = APIRouter(
    prefix="/map",
    tags=["GIS Map"],
)


@router.get("/priority/by-selected-month")
def priority_map_by_selected_month(
    year: int = Query(..., ge=2026, le=2030),
    month: int = Query(..., ge=1, le=12),
):
    try:
        result = get_priority_maps_by_selected_month(
            year=year,
            month=month,
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
            detail=(
                "GIS priority data not found for the "
                "selected year and month."
            ),
        )

    return result


@router.get("/boundaries")
def boundaries():
    try:
        return get_boundaries()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )