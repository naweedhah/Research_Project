"""Model reliability and maintenance endpoints. Owner: Component 3.

GET  /maintenance/status              active model, thresholds, last cycle
GET  /maintenance/scenarios           shift scenarios available for demonstration cycles
POST /maintenance/cycle               run one maintenance cycle (optionally under a shift and with context)
GET  /maintenance/context             external context signals (disasters, food prices, inflation)
GET  /maintenance/history             model version history (promotions, rejections, approvals, rollbacks)
POST /maintenance/approve | /reject-pending | /rollback | /reset
GET  /maintenance/dashboard           model-health page
"""

from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.c3.service import scenarios, service

router = APIRouter(prefix="/maintenance", tags=["Model reliability and maintenance"])


class CycleRequest(BaseModel):
    family: str = "none"
    strength: float = 0.0
    with_labels: bool = True
    context_start: date | None = None
    context_end: date | None = None
    offline_context: bool = True
    require_approval: bool = False


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(503, f"C3 data not available: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/status")
def status() -> dict:
    return service.status()


@router.get("/scenarios")
def list_scenarios() -> list[dict]:
    return scenarios()


@router.post("/cycle")
def run_cycle(request: CycleRequest) -> dict:
    return _call(service.run_cycle, **request.model_dump())


@router.get("/context")
def context(start: date, end: date, offline: bool = False) -> dict:
    return service.context(start, end, offline)


@router.get("/history")
def history() -> list[dict]:
    return _call(service.history)


@router.post("/approve")
def approve(approver: str = "reviewer") -> dict:
    return _call(service.approve, approver)


@router.post("/reject-pending")
def reject_pending(reason: str = "rejected by reviewer") -> dict:
    return _call(service.reject_pending, reason)


@router.post("/rollback")
def rollback() -> dict:
    return _call(service.rollback)


@router.post("/reset")
def reset() -> dict:
    return _call(service.reset)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return (Path(__file__).resolve().parents[1] / "c3" / "dashboard.html").read_text()
