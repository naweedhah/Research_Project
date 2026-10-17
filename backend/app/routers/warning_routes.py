from fastapi import APIRouter, HTTPException, Query

from app.services.warning_service import (
    get_warning_summary,
    get_warnings,
)


router = APIRouter(
    prefix="/warnings",
    tags=["Early Warnings"],
)


@router.get("/summary")
def warning_summary():
    try:
        return get_warning_summary()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@router.get("/")
def warnings(
    severity: str | None = Query(
        default=None,
        description="Filter by HIGH or CRITICAL",
    ),
    district: str | None = Query(
        default=None,
    ),
    horizon: int | None = Query(
        default=None,
        ge=1,
        le=6,
        description="Use 1, 3 or 6",
    ),
):
    if horizon is not None and horizon not in [1, 3, 6]:
        raise HTTPException(
            status_code=400,
            detail="Horizon must be 1, 3 or 6.",
        )

    try:
        return get_warnings(
            severity=severity,
            district=district,
            horizon=horizon,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )