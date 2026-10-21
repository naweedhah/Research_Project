from fastapi import APIRouter, HTTPException, Query

from app.services.explainability_service import (
    get_explanations_by_selected_month,
)


router = APIRouter(
    prefix="/explainability",
    tags=["Explainable AI"],
)


@router.get("/by-selected-month")
def explainability_by_selected_month(
    year: int = Query(..., ge=2026, le=2030),
    month: int = Query(..., ge=1, le=12),
    district: str = Query(..., min_length=1),
):
    try:
        result = get_explanations_by_selected_month(
            year=year,
            month=month,
            district=district,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=(
                "Explainability result not found for the selected "
                "year, month and district."
            ),
        )

    return result