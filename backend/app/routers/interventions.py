"""Intervention recommendations endpoints. Owner: Component 2."""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from components.c2_counterfactual_intervention.engine import recommend
from components.c2_counterfactual_intervention.schemas import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/interventions", tags=["Intervention recommendations"])


@router.get("/status")
def status() -> dict:
    return {"component": 2, "test_engine_ready": True, "c1_integrated": False,
            "clinical_ready": False, "methods": ["bounded_search", "dice", "face_graph"]}


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendations(request: RecommendationRequest) -> RecommendationResponse:
    try:
        return recommend(request)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Requested method dependency unavailable: {exc}") from exc
