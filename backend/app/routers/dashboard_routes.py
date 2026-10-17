from fastapi import APIRouter, HTTPException, Query

from app.services.dashboard_service import (
    get_dashboard_status,
    get_manifest,
    get_metadata,
    get_dashboard_summary,
)


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/status")
def dashboard_status():
    return get_dashboard_status()


@router.get("/manifest")
def dashboard_manifest():
    try:
        return get_manifest()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.get("/metadata")
def dashboard_metadata():
    try:
        return get_metadata()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.get("/summary/by-selected-month")
def dashboard_summary_by_selected_month(
    year: int = Query(..., ge=2026, le=2030),
    month: int = Query(..., ge=1, le=12),
    district: str = Query(..., min_length=1),
):
    try:
        return get_dashboard_summary(
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
            status_code=400,
            detail=str(exc),
        )