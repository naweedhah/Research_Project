"""Integrated API: one router per research component, plus shared login, email and assistant routes."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import forecast, interventions, maintenance, risk
from app.routers.ai_routes import router as ai_router
from app.routers.auth_routes import router as auth_router
from app.routers.email_routes import router as email_router

app = FastAPI(
    title="Childhood Malnutrition Decision Support API",
    description="Integrated backend API for the childhood malnutrition decision-support research system.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (5173, 5174, 4173)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Components 1-4
for module in (risk, interventions, maintenance, forecast):
    app.include_router(module.router)

# Shared system routes
app.include_router(auth_router)
app.include_router(email_router)
app.include_router(ai_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
