from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import forecast
from app.routers.auth_routes import router as auth_router
from app.routers.email_routes import router as email_router
from app.routers.ai_routes import router as ai_router


app = FastAPI(
    title="Childhood Malnutrition Decision Support API",
    description=(
        "Integrated backend API for the childhood "
        "malnutrition decision-support research system."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Component 4
app.include_router(forecast.router)

# Common system routes
app.include_router(auth_router)
app.include_router(email_router)
app.include_router(ai_router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
    }