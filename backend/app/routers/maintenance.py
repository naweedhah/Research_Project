"""Model reliability and maintenance endpoints. Owner: Component 3.

Live workflow (real batches; state saved under C3_STATE_DIR):
GET  /maintenance/live/status                      active model, pending approval, batches, last cycle
POST /maintenance/live/batches                     submit a screening batch -> validation, drift, label-free warning
GET  /maintenance/live/batches[/{batch_id}]        submitted batches and their results (no child records)
POST /maintenance/live/batches/{batch_id}/outcomes outcomes arrive -> post-deployment check, assess, adapt, verify
GET  /maintenance/live/history                     model version history
POST /maintenance/live/approve | /reject-pending | /rollback | /reset?confirm=true

Demonstration sandbox (simulated shifts on held-out data; in memory, used by the dashboard):
GET  /maintenance/status | /scenarios | /history     POST /maintenance/cycle | /approve | /reject-pending | /rollback | /reset
GET  /maintenance/dashboard                          model-health page

Shared:
GET  /maintenance/context                          external context signals (disasters, food prices, inflation)
GET  /maintenance/context/dashboard                each source's fetch status and time series (external-context page)
GET  /maintenance/results[/{run}/report | /{run}/figures/{name}]   experiment results
"""

from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.c3 import results
from app.c3.context_view import context_dashboard
from app.c3.live import Conflict, NotFound, live
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


class BatchRequest(BaseModel):
    records: list[dict[str, Any]] = Field(
        description="One entry per child: a pseudonymous record_id plus every model input field (null if not "
                    "recorded). No names or other identifiers.")
    batch_id: str | None = Field(None, description="Generated if omitted. Letters, digits, '.', '_' and '-'.")
    area: str | None = Field(None, description="e.g. the PHM area the batch comes from")
    collected_from: date | None = None
    collected_to: date | None = None
    context: Literal["live", "offline", "none"] = Field(
        "live", description="External context for the collection dates: live sources, bundled samples, or none")


class OutcomesRequest(BaseModel):
    labels: dict[str, int] = Field(description="record_id -> observed outcome (1 = condition present, 0 = not)")
    require_approval: bool = Field(True, description="A verified candidate waits for a person instead of deploying")


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(503, f"C3 data not available: {exc}") from exc
    except (NotFound, LookupError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# ---------------------------------------------------------------- live workflow
@router.get("/live/status")
def live_status() -> dict:
    return _call(live.status)


@router.post("/live/batches")
def submit_batch(request: BatchRequest) -> dict:
    return _call(live.submit_batch, **request.model_dump())


@router.get("/live/batches")
def list_batches() -> list[dict]:
    return _call(live.batches)


@router.get("/live/batches/{batch_id}")
def get_batch(batch_id: str) -> dict:
    return _call(live.batch, batch_id)


@router.post("/live/batches/{batch_id}/outcomes")
def submit_outcomes(batch_id: str, request: OutcomesRequest) -> dict:
    return _call(live.submit_outcomes, batch_id, request.labels, request.require_approval)


@router.get("/live/history")
def live_history() -> list[dict]:
    return _call(live.history)


@router.post("/live/approve")
def live_approve(approver: str = "reviewer") -> dict:
    return _call(live.approve, approver)


@router.post("/live/reject-pending")
def live_reject_pending(reason: str = "rejected by reviewer") -> dict:
    return _call(live.reject_pending, reason)


@router.post("/live/rollback")
def live_rollback() -> dict:
    return _call(live.rollback)


@router.post("/live/reset")
def live_reset(confirm: bool = False) -> dict:
    if not confirm:
        raise HTTPException(400, "this deletes all live models, history and batches; repeat with confirm=true")
    return _call(live.reset)


# ---------------------------------------------------------------- demonstration sandbox
@router.get("/status")
def status() -> dict:
    return service.status()


@router.get("/scenarios")
def list_scenarios() -> list[dict]:
    return scenarios()


@router.post("/cycle")
def run_cycle(request: CycleRequest) -> dict:
    return _call(service.run_cycle, **request.model_dump())


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


# ---------------------------------------------------------------- shared
@router.get("/context")
def context(start: date, end: date, offline: bool = False) -> dict:
    return service.context(start, end, offline)


@router.get("/context/dashboard")
def context_dashboard_view(start: date, end: date, offline: bool = False, refresh: bool = False) -> dict:
    """Every external source for one window: fetch status, time series for charts, and the signals C3 derives."""
    if start > end:
        raise HTTPException(400, "start is after end")
    return context_dashboard(start, end, offline, refresh)


@router.get("/results")
def list_results() -> list[dict]:
    return results.runs()


@router.get("/results/{run}/report", response_class=PlainTextResponse)
def results_report(run: str) -> str:
    return _call(results.report, run)


@router.get("/results/{run}/figures/{name}")
def results_figure(run: str, name: str) -> FileResponse:
    return FileResponse(_call(results.figure, run, name), media_type="image/png")
