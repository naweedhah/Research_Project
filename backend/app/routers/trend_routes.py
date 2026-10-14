from fastapi import APIRouter, HTTPException, Query

from app.services.trend_service import (
    get_clinical_trend_by_selected_month,
)


router = APIRouter(
    prefix="/trends",
    tags=["Trend Analysis"],
)


@router.get("/clinical/by-selected-month")
def clinical_trend_by_selected_month(
    year: int = Query(..., ge=2026, le=2030),
    month: int = Query(..., ge=1, le=12),
    district: str = Query(..., min_length=1),
):
    try:
        result = get_clinical_trend_by_selected_month(
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
            detail=(
                "Clinical trend data not found for the selected "
                "district, year and month."
            ),
        )

    return result