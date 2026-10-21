"""Intervention recommendations endpoints. Owner: Component 2."""

from fastapi import APIRouter, HTTPException, Request
import hmac
import os
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
from components.c2_counterfactual_intervention.c1_engine import C1Request, C1Result, run_c1
from components.c2_counterfactual_intervention.c1_predictors import C1PredictionUnavailable
from components.c2_counterfactual_intervention.real_model_validation import run_validation, run_standalone_validation
from components.c2_counterfactual_intervention.automatic_analysis import AutomaticRequest, load_automatic_baseline, run_automatic_analysis
from components.c2_counterfactual_intervention.standalone_demo import StandaloneRequest, run_standalone
from components.c2_counterfactual_intervention.phm_local_validation import LocalValidationRequest, local_profiles, review_local_case
from components.c2_counterfactual_intervention.manual_c1_validation import ManualC1Request, run_manual_c1
from components.c2_counterfactual_intervention.manual_c1_validation import manual_snapshot
from components.c2_counterfactual_intervention.c1_predictors import RealC1HttpPredictor
from components.c2_counterfactual_intervention.real_model_validation import _prediction
from components.c2_counterfactual_intervention.nutrition_scenarios_v2 import ScenarioRequest, generate_scenarios
from components.c2_counterfactual_intervention.live_case_library_v2 import live_case_library
from components.c2_counterfactual_intervention.live_case_validation_v2 import run_live_cases
from components.c2_counterfactual_intervention.official_prices import bundled_history, price_state
from datetime import date

router = APIRouter(prefix="/interventions", tags=["Intervention recommendations"])


@router.get("/live-case-library-v2")
def list_live_cases_v2(http_request: Request) -> dict:
    """Invented inputs only; no precomputed or claimed C1 outcomes."""
    _require_local_review(http_request)
    return live_case_library()


@router.get("/live-case-validation-v2")
def verify_live_cases_v2(http_request: Request) -> dict:
    """Re-score the bounded invented catalogue with genuine C1; no saved outputs."""
    _require_local_review(http_request)
    try:
        return run_live_cases()
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/baseline-c1-v2")
def baseline_c1_v2(request: ManualC1Request, http_request: Request) -> dict:
    """One genuine C1 call for an invented local assessment; never a candidate call."""
    import hashlib
    import json
    _require_local_review(http_request)
    snapshot = manual_snapshot(request)
    payload = snapshot.predict_payload()
    try:
        prediction = RealC1HttpPredictor().predict(snapshot)
        display = _prediction(prediction)
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                             separators=(",", ":")).encode()).hexdigest()
    return {"assessment": {"model_version": prediction.model_version,
                           "prediction_source": prediction.prediction_source,
                           "predicted_malnutrition_type": prediction.predicted_malnutrition_type,
                           "severity": prediction.severity,
                           "uncertainty_flag": prediction.uncertainty_flag,
                           "clinical_use": False, "input_fingerprint": fingerprint,
                           "provenance": "live_c1_baseline"},
            "prediction": display, "c1_calls": 1,
            "feeding_provenance": "unverified",
            "limitations": ["Manually entered invented inputs are not observed child records.",
                            "This prediction is model context, not a diagnosis or treatment outcome."]}


@router.post("/diet-scenarios-v2")
def diet_scenarios_v2(request: ScenarioRequest, http_request: Request) -> dict:
    """Generate food counterfactuals without importing or contacting C1."""
    _require_local_review(http_request)
    return generate_scenarios(request)


@router.post("/standalone-analysis")
def standalone_analysis(request: StandaloneRequest) -> dict:
    """Synthetic C2 demonstration; no C1 connection or real-mode policy bypass."""
    return run_standalone(request)


@router.get("/standalone-validation")
def standalone_validation(case_id: str = "synthetic_24m") -> dict:
    """Optional genuine model evidence for the standalone fixture; never cards."""
    if case_id not in {"synthetic_5m", "synthetic_24m", "synthetic_59m"}:
        raise HTTPException(status_code=422, detail="unsupported demonstration case")
    try:
        return run_standalone_validation(case_id)
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _require_local_review(request: Request) -> None:
    if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="private research validation is local-only")


@router.post("/manual-c1-validation")
def manual_c1_validation(request: ManualC1Request, http_request: Request) -> dict:
    """Score manually entered invented inputs with genuine C1; issue no cards."""
    _require_local_review(http_request)
    try:
        return run_manual_c1(request)
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/local-validation-profiles")
def local_validation_profiles(http_request: Request) -> dict:
    """List only de-identified local review aliases; no raw source rows."""
    _require_local_review(http_request)
    try:
        return local_profiles()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/local-validation")
def local_validation(request: LocalValidationRequest, http_request: Request) -> dict:
    """Re-run genuine C1 for an opt-in local case; never issue approved cards."""
    _require_local_review(http_request)
    try:
        return review_local_case(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/automatic-baseline")
def automatic_baseline(case_id: str = "synthetic_24m") -> dict:
    """Load a genuine C1 baseline for a selectable invented demonstration case."""
    if case_id not in {"synthetic_5m", "synthetic_24m", "synthetic_59m"}:
        raise HTTPException(status_code=422, detail="unsupported synthetic demonstration case")
    try:
        return load_automatic_baseline(case_id)
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/automatic-analysis")
def automatic_analysis(request: AutomaticRequest) -> dict:
    """Genuine C1 comparison of fixed synthetic cases; never an authorized recommendation."""
    try:
        return run_automatic_analysis(request)
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/c1-validation")
def c1_validation() -> dict:
    """Fixed synthetic fixture, genuine C1 outputs, no recommendation cards."""
    try:
        return run_validation()
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/price-references")
def price_references() -> dict:
    """Published Colombo retail references; no local quote or food recommendation."""
    today = date.today()
    rows = bundled_history()
    return {
        "as_of": today.isoformat(),
        "banner": "OFFICIAL COLOMBO PRICE REFERENCES - NOT VERIFIED KALMUNAI PRICES",
        "records": [{
            "food_id": row.food_id, "commodity": row.published_commodity,
            "amount_lkr": str(row.amount_lkr), "quantity": str(row.quantity),
            "unit": row.unit, "source_institution": row.source_institution,
            "source_url": row.report_url, "source_locator": row.source_locator,
            "publication_date": row.publication_date.isoformat() if row.publication_date else None,
            "observation_start": row.observation_start.isoformat(),
            "observation_end": row.observation_end.isoformat(),
            "period_date_basis": row.period_date_basis,
            "market_coverage": row.market_coverage,
            "reference_status": price_state(row, as_of=today),
        } for row in rows if row.evidence_status == "source_checked" and row.price_class == "retail"],
        "limitations": "No Kalmunai market price, household budget, local availability, clinical suitability or serving size is verified by these records.",
    }


@router.post("/c1-research", response_model=C1Result)
def c1_research(request: C1Request, http_request: Request) -> C1Result:
    """Explicit C1-shaped simulator or fail-closed real HTTP path."""
    if request.mode == "real":
        token = os.getenv("C2_REAL_API_TOKEN")
        supplied = http_request.headers.get("authorization", "")
        if not token:
            raise HTTPException(status_code=503, detail="real C2 access is not configured")
        if not hmac.compare_digest(supplied, "Bearer " + token):
            raise HTTPException(status_code=401, detail="unauthorized")
    try:
        return run_c1(request)
    except C1PredictionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
