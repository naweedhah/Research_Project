"""Intervention recommendations endpoints. Owner: Component 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/interventions", tags=["Intervention recommendations"])


@router.get("/status")
def status() -> dict:
    return {"component": 2, "ready": False}
