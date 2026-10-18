from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ga_rgca_v4 import REQUIRED_FILES as V4_REQUIRED_FILES
from app.ga_rgca_v4 import V4_MODEL_VERSION, IncompleteVisit, load_ga_rgca_v4

_REPO = Path(__file__).resolve().parents[3]
EXPECTED_MODEL_VERSION = "ga_rgca_v4_rsl"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_REPO / ".env"), extra="ignore")
    embedding_dim: int = 96
    c1_model_version: str = EXPECTED_MODEL_VERSION
    ga_rgca_v4_dir: str = ""


settings = Settings()
if settings.c1_model_version.strip().lower() != EXPECTED_MODEL_VERSION:
    raise RuntimeError(
        "C1_MODEL_VERSION must be ga_rgca_v4_rsl. "
        f"Received {settings.c1_model_version!r}. The service will not start and will not fall back to another model."
    )

app = FastAPI(title="CNIP Inference Service", version="0.1.0")


class PredictRequest(BaseModel):
    child_pseudonymous_id: str
    visit_number: int = 0
    visit_date: str | None = None
    anthropometric: dict = Field(default_factory=dict)
    socioeconomic: dict = Field(default_factory=dict)
    dietary: dict = Field(default_factory=dict)
    maternal_child_health: dict = Field(default_factory=dict)
    prior_visit: dict | None = None
    ga_rgca_context: dict | None = None
    baseline_clinical: dict | None = None
    historical_baseline: dict | None = None
    model_mode: str | None = None
    allow_demo: bool = False


class PredictionResult(BaseModel):
    status: str
    severity: str
    raw_probabilities: dict
    calibrated_probabilities: dict
    risk_score: float
    confidence: str
    latent_embedding: list[float]
    model_version: str
    calibration_version: str
    feature_schema_version: str
    inference_ms: float
    mode: str
    score_kind: str = "highest_condition_probability"
    score_is_probability: bool = True
    score_is_calibrated: bool = True
    prediction_task: str = "twelve_month_nutritional_risk"
    clinical_use: bool = False
    data_limitations: list[str] = Field(default_factory=list)
    prediction_source: str = V4_MODEL_VERSION


V4_MODEL, V4_LOAD_ERROR = load_ga_rgca_v4()


class GaRgcaV4Adapter:
    """Current visit is the rolling 12-month origin."""

    name = V4_MODEL_VERSION

    def predict(self, req: PredictRequest) -> PredictionResult:
        if V4_MODEL is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_NOT_AVAILABLE",
                    "message": V4_LOAD_ERROR or "GA-RGCA v4 Rolling SuperLearner is not loaded",
                    "prediction_source": None,
                },
            )
        t0 = time.perf_counter()
        try:
            heads = V4_MODEL.predict_payload(req.model_dump())
        except IncompleteVisit as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "REAL_MODEL_INPUT_INCOMPLETE",
                    "message": "GA-RGCA v4 needs the current visit age, sex, height, and weight. No substitute score was used.",
                    "missing": exc.missing,
                    "prediction_source": None,
                },
            ) from exc
        elapsed = (time.perf_counter() - t0) * 1000
        acute = heads["acute_probabilities"]
        condition_risk = max(
            heads["underweight_probability"],
            heads["stunting_probability"],
            heads["mam_probability"],
            heads["sam_probability"],
        )
        stored = {key: value for key, value in heads.items() if key != "latent"}
        stored["input_snapshot"] = {
            "values": heads["input_snapshot"],
            "missing_features": heads["missing_features"],
            "model_version": V4_MODEL_VERSION,
            "calibration_version": "ga-rgca-v4-superlearner",
            "feature_schema_version": "ga-rgca-v4-rolling-current-visit",
            "binary_thresholds": heads["binary_thresholds"],
            "acute_temperature": heads["acute_temperature"],
            "severity_temperature": heads["severity_temperature"],
            "uncertainty_threshold": heads["uncertainty_threshold"],
            "rolling_origin": True,
        }
        return PredictionResult(
            status=heads["predicted_malnutrition_type"],
            severity=heads["severity"],
            raw_probabilities={"acute": acute, "ga_rgca": stored},
            calibrated_probabilities={"acute": acute, "risk": condition_risk, "ga_rgca": stored},
            risk_score=round(float(condition_risk), 4),
            confidence="elevated" if heads["uncertainty_flag"] else "low",
            latent_embedding=heads["latent"] or [],
            model_version=V4_MODEL_VERSION,
            calibration_version="ga-rgca-v4-superlearner",
            feature_schema_version="ga-rgca-v4-rolling-current-visit",
            inference_ms=round(elapsed, 2),
            mode="PYTORCH",
            score_kind="highest_condition_probability",
            score_is_probability=True,
            score_is_calibrated=True,
            prediction_task="twelve_month_nutritional_risk",
            clinical_use=False,
            data_limitations=heads["data_limitations"],
            prediction_source=V4_MODEL_VERSION,
        )


ADAPTER = GaRgcaV4Adapter()


def _status_payload() -> dict:
    loaded = V4_MODEL is not None
    weights = V4_MODEL.policy["stack_weights"] if loaded else None
    return {
        "status": "ok" if loaded else "unavailable",
        "service": "inference",
        "c1_model_version": EXPECTED_MODEL_VERSION,
        "mode": EXPECTED_MODEL_VERSION,
        "active_model": V4_MODEL_VERSION if loaded else None,
        "adapter": ADAPTER.__class__.__name__,
        "model_loaded": loaded,
        "model_version": V4_MODEL_VERSION if loaded else None,
        "architecture": "GA-RGCA v4 Rolling SuperLearner",
        "rolling_origin": True,
        "prediction_horizon_months": 12,
        "superlearner": loaded,
        "experts": list(V4_MODEL.policy["candidate_names"]) if loaded else [],
        "neural_ensemble_members": len(V4_MODEL.models) if loaded else 0,
        "artifact_path": str(V4_MODEL.directory) if loaded else None,
        "stack_weights": weights,
        "prediction_source": V4_MODEL_VERSION if loaded else None,
        "prediction_type": "twelve_month_nutritional_risk",
        "outputs": ["Underweight", "Stunting", "MAM", "SAM", "Severity"],
        "uncertainty_method": "neural ensemble variance",
        "clinical_use": False,
        "external_validation_complete": False,
        "clinically_validated": False,
        "repeated_origin_prospective_validation": False,
        "demo": False,
        "ga_rgca_loaded": loaded,
        "ga_rgca_error": V4_LOAD_ERROR,
        "ga_rgca_required_files": list(V4_REQUIRED_FILES),
        "ga_rgca_task": "twelve_month_nutritional_risk" if loaded else None,
        "ensemble_members": len(V4_MODEL.models) if loaded else 0,
    }


@app.get("/health")
def health():
    payload = _status_payload()
    return {
        "status": payload["status"],
        "service": "inference",
        "c1_model_version": payload["c1_model_version"],
        "mode": payload["mode"],
        "active_model": payload["active_model"],
        "model_loaded": payload["model_loaded"],
        "ga_rgca_loaded": payload["ga_rgca_loaded"],
    }


@app.get("/model-info")
def model_info():
    return _status_payload()


@app.post("/predict", response_model=PredictionResult)
def predict(req: PredictRequest):
    return ADAPTER.predict(req)
