"""Risk assessment endpoints. Owner: Component 1."""

from fastapi import APIRouter

router = APIRouter(prefix="/risk", tags=["Risk assessment"])


@router.get("/status")
def status() -> dict:
    return {"component": 1, "ready": False}
