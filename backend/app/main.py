"""Integrated API: one router per research component."""

from fastapi import FastAPI

from app.routers import forecast, interventions, maintenance, risk

app = FastAPI(title="Childhood Malnutrition Decision Support API")

for module in (risk, interventions, maintenance, forecast):
    app.include_router(module.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
