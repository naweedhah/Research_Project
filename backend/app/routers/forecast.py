"""Burden forecasting endpoints. Owner: Component 4."""

from fastapi import APIRouter

router = APIRouter(prefix="/forecast", tags=["Burden forecasting"])


@router.get("/status")
def status() -> dict:
    return {"component": 4, "ready": False}
