"""Intervention recommendations endpoints. Owner: Component 2."""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from components.c2_counterfactual_intervention.engine import recommend
from components.c2_counterfactual_intervention.engine import MissingRealPredictorError
from components.c2_counterfactual_intervention.contracts import PredictorCompatibilityError
from components.c2_counterfactual_intervention.registry import c1_integration_verified, get_real_predictor
from components.c2_counterfactual_intervention.schemas import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/interventions", tags=["Intervention recommendations"])


@router.get("/status")
def status() -> dict:
    registered = get_real_predictor() is not None
    return {"component": 2, "test_engine_ready": True, "c1_integrated": c1_integration_verified(),
            "real_model_registered": registered, "clinical_ready": False,
            "methods": ["bounded_search", "dice", "face_graph"]}


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendations(request: RecommendationRequest) -> RecommendationResponse:
    try:
        predictor = get_real_predictor() if request.mode == "real" else None
        return recommend(request, predictor)
    except MissingRealPredictorError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PredictorCompatibilityError as exc:
        raise HTTPException(status_code=503, detail=f"Predictor incompatible: {exc}") from exc
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Requested method dependency unavailable: {exc}") from exc
