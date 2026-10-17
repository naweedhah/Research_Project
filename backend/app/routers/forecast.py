"""Burden forecasting endpoints. Owner: Component 4."""

from fastapi import APIRouter

from app.routers.forecast_routes import router as forecast_routes_router
from app.routers.warning_routes import router as warning_routes_router
from app.routers.dashboard_routes import router as dashboard_routes_router
from app.routers.explainability_routes import router as explainability_routes_router
from app.routers.resource_routes import router as resource_routes_router
from app.routers.map_routes import router as map_routes_router
from app.routers.trend_routes import router as trend_routes_router
from app.routers.district_routes import router as district_routes_router
from app.routers.dashboard_summary_routes import (
    router as dashboard_summary_routes_router,
)

router = APIRouter(
    prefix="/forecast",
)


router.include_router(forecast_routes_router)
router.include_router(warning_routes_router)
router.include_router(dashboard_routes_router)
router.include_router(explainability_routes_router)
router.include_router(resource_routes_router)
router.include_router(map_routes_router)
router.include_router(trend_routes_router)
router.include_router(district_routes_router)
router.include_router(dashboard_summary_routes_router)

@router.get(
    "/status",
    tags=["Component 4"],
)
def status() -> dict:
    return {
        "component": 4,
        "ready": True,
    }