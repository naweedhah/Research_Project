from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from app.api import admin, alerts, auth, care, children, dashboard, export, integrations, research, trajectory, visits
from app.core.config import get_settings
from app.core.db import engine
from app.core.logging import configure_logging, new_request_id
from app.core.policy import load_product

settings = get_settings()
configure_logging(json_logs=settings.log_json, level=settings.log_level)
product = load_product()

REQUESTS = Counter("cnip_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("cnip_http_request_seconds", "HTTP latency", ["method", "path"])

app = FastAPI(
    title=product["name"],
    description=f"{product['subtitle']}. {product['disclaimer']}",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

_cors_kwargs: dict = {
    "allow_origins": settings.cors_origins,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.is_dev:
    # Local Next.js often runs on alternate ports (3001, 3002, …) when 3000 is taken.
    _cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

app.add_middleware(CORSMiddleware, **_cors_kwargs)


@app.middleware("http")
async def request_context(request: Request, call_next: Callable):
    rid = new_request_id()
    start = time.perf_counter()
    response: Response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    LATENCY.labels(request.method, path).observe(elapsed)
    response.headers["X-Request-ID"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


app.include_router(auth.router)
app.include_router(children.router)
app.include_router(visits.router)
app.include_router(dashboard.router)
app.include_router(alerts.router)
app.include_router(care.router)
app.include_router(trajectory.router)
app.include_router(research.router)
app.include_router(admin.router)
app.include_router(integrations.router)
app.include_router(export.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "api", "product": product["shortName"]}


@app.get("/ready")
def ready():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "not_ready", "error": str(exc)}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def root():
    return {
        "name": product["name"],
        "subtitle": product["subtitle"],
        "disclaimer": product["disclaimer"],
        "docs": "/docs",
    }
