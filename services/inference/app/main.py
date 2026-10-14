from __future__ import annotations

import hashlib
import time
from pathlib import Path

import numpy as np
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.demo_outcomes import demo_confidence, get_demo_outcome
from app.ga_rgca import REQUIRED_FILES, IncompleteBaseline, load_ga_rgca

CONTRACTS = Path("/contracts") if Path("/contracts").exists() else Path(__file__).resolve().parents[3] / "packages" / "contracts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    model_mode: str = "demo"
    model_artifact_path: str = "/artifacts/active"
    embedding_dim: int = 128


settings = Settings()
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
    score_kind: str = "demo_progression_score"
    score_is_probability: bool = False
    score_is_calibrated: bool = False
    prediction_task: str = "current_status_demo"
    clinical_use: bool = False
    data_limitations: list[str] = Field(default_factory=list)
    prediction_source: str = "DEMO"


def _embedding(pid: str, visit_number: int, risk: float, dim: int) -> list[float]:
    """Deterministic demo embedding. visit_number must be DB 1-based."""
    seed = sum(ord(c) for c in pid) + visit_number * 17
    return [round(((seed * (i + 3)) % 1000) / 1000.0 - 0.5 + (1 - risk) * 0.2, 4) for i in range(dim)]


def _temperature_scale(prob: float, temperature: float = 1.2) -> float:
    # Simple calibration stand-in for the demo adapter.
    prob = min(max(prob, 1e-6), 1 - 1e-6)
    logit = np.log(prob / (1 - prob)) / temperature
    calibrated = 1 / (1 + np.exp(-logit))
    return float(np.clip(calibrated, 0.01, 0.99))


def _tri_state_contribution(value, *, true_delta: float, false_delta: float = 0.0) -> tuple[float, bool]:
    """Return (contribution, was_unknown). Unknown/None is excluded — never treated as False."""
    if value is True:
        return true_delta, False
    if value is False:
        return false_delta, False
    return 0.0, True


class DemoModelAdapter:
    name = "MCA-2026-001"

    def predict(self, req: PredictRequest) -> PredictionResult:
        t0 = time.perf_counter()
        limitations: list[str] = []
        canonical = get_demo_outcome(req.child_pseudonymous_id, req.visit_number)
        if canonical is not None:
            status, severity, risk = canonical
            calibrated = risk
        else:
            status, severity, risk, limitations = self._from_measurements(req)
            calibrated = _temperature_scale(risk)
        raw_risk = min(0.99, risk + 0.03)
        status_probs = {k: 0.08 for k in ("normal", "stunting", "wasting", "underweight")}
        status_probs[status] = max(0.55, calibrated)
        total = sum(status_probs.values())
        status_probs = {k: round(v / total, 4) for k, v in status_probs.items()}
        dim = settings.embedding_dim
        elapsed = (time.perf_counter() - t0) * 1000
        return PredictionResult(
            status=status,
            severity=severity,
            raw_probabilities={"status": status_probs, "risk": raw_risk},
            calibrated_probabilities={"status": status_probs, "risk": calibrated},
            risk_score=round(float(calibrated), 4),
            confidence=demo_confidence(),
            latent_embedding=_embedding(req.child_pseudonymous_id, req.visit_number, float(calibrated), dim),
            model_version=self.name,
            calibration_version="demo-temp-v1",
            feature_schema_version="fs-2026-001",
            inference_ms=round(elapsed, 2),
            mode="DEMO",
            score_kind="demo_progression_score",
            score_is_probability=False,
            score_is_calibrated=False,
            prediction_task="current_status_demo",
            clinical_use=False,
            data_limitations=limitations,
            prediction_source="DEMO",
        )

    def _from_measurements(self, req: PredictRequest) -> tuple[str, str, float, list[str]]:
        anthro = req.anthropometric
        diet = req.dietary
        mch = req.maternal_child_health
        weight = anthro.get("weight_kg")
        height = anthro.get("height_cm")
        muac = anthro.get("muac_cm")
        if weight is None or height is None:
            raise ValueError("Anthropometric weight and height are required for assessment")
        weight = float(weight)
        height = float(height)
        muac = float(muac) if muac is not None else None
        diversity_raw = diet.get("dietary_diversity_score")
        diversity = int(diversity_raw) if diversity_raw is not None else None
        limitations: list[str] = []
        diarrhoea_delta, diarrhoea_unknown = _tri_state_contribution(
            mch.get("recent_diarrhoea"), true_delta=0.08, false_delta=0.0
        )
        if diarrhoea_unknown:
            limitations.append("recent_diarrhoea_unknown")
        resp_delta, resp_unknown = _tri_state_contribution(
            mch.get("recent_respiratory_illness"), true_delta=0.04, false_delta=0.0
        )
        if resp_unknown:
            limitations.append("recent_respiratory_illness_unknown")
        hosp_delta, hosp_unknown = _tri_state_contribution(
            mch.get("recent_hospitalization"), true_delta=0.05, false_delta=0.0
        )
        if hosp_unknown:
            limitations.append("recent_hospitalization_unknown")
        bmi_like = weight / ((height / 100) ** 2) if height else 14
        digest = hashlib.sha256(
            f"{req.child_pseudonymous_id}:{req.visit_number}:{weight}:{height}:{muac}".encode()
        ).hexdigest()
        noise = int(digest[:4], 16) / 65535 * 0.04
        risk = 0.15 + max(0, (16 - bmi_like) * 0.06)
        if muac is not None:
            risk += max(0, (12.5 - muac) * 0.05)
        else:
            limitations.append("muac_unknown")
        if diversity is not None:
            risk += (4 - diversity) * 0.03
        else:
            limitations.append("dietary_diversity_unknown")
        # Unknown flags contribute 0 (excluded), distinct from False which also adds 0 but is recorded as known-negative.
        risk += diarrhoea_delta + resp_delta + hosp_delta + noise
        risk = float(np.clip(risk, 0.08, 0.92))
        if risk >= 0.75:
            return "wasting", "severe", risk, limitations
        if risk >= 0.55:
            return "wasting", "moderate", risk, limitations
        if risk >= 0.4:
            return "underweight", "mild", risk, limitations
        if risk >= 0.28:
            return "stunting", "mild", risk, limitations
        return "normal", "none", risk, limitations


class SklearnModelAdapter:
    def __init__(self, path: str):
        self.path = path
        self._model = None

    def predict(self, req: PredictRequest) -> PredictionResult:
        import joblib

        if self._model is None:
            self._model = joblib.load(self.path)
        raise HTTPException(503, "Sklearn adapter loaded but feature vector assembly from visit payload is not bound to a trained artifact yet")


class PyTorchMultimodalAdapter:
    def __init__(self, path: str):
        self.path = path
        self._model = None

    def predict(self, req: PredictRequest) -> PredictionResult:
        import torch
        from models.multimodal import MultimodalCrossAttention  # type: ignore  # noqa: I001

        if self._model is None:
            ckpt = torch.load(self.path, map_location="cpu")
            self._model = MultimodalCrossAttention.from_config(ckpt.get("config", {}))
            self._model.load_state_dict(ckpt["state_dict"])
            self._model.eval()
        # Feature tensors are assembled by the training pipeline schema.
        raise HTTPException(503, "PyTorch artifact is registered but live tensor assembly requires a trained checkpoint bound to MODEL_ARTIFACT_PATH")


class OnnxModelAdapter:
    def __init__(self, path: str):
        self.path = path

    def predict(self, req: PredictRequest) -> PredictionResult:
        raise HTTPException(503, "ONNX adapter has no active artifact")


GA_MODEL, GA_LOAD_ERROR = load_ga_rgca()


class GaRgcaAdapter:
    """Score the visit being entered as the baseline for a later-risk prediction.

    Demo scores are returned only when the request sets allow_demo.
    """

    name = "GA-RGCA-v3"

    def predict(self, req: PredictRequest) -> PredictionResult:
        if req.allow_demo:
            demo = DemoModelAdapter().predict(req)
            demo.prediction_source = "DEMO"
            return demo
        if GA_MODEL is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_NOT_AVAILABLE",
                    "message": GA_LOAD_ERROR or "GA-RGCA v3 is not loaded",
                    "prediction_source": None,
                },
            )
        payload = req.model_dump()
        t0 = time.perf_counter()
        try:
            heads = GA_MODEL.predict_prior(payload)
        except IncompleteBaseline as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "REAL_MODEL_INPUT_INCOMPLETE",
                    "message": "GA-RGCA v3 needs the current visit height and weight. No demo score was substituted.",
                    "missing": exc.missing,
                    "prediction_source": None,
                },
            ) from exc
        elapsed = (time.perf_counter() - t0) * 1000
        acute = {
            "Normal": heads["normal_acute_probability"],
            "MAM": heads["mam_probability"],
            "SAM": heads["sam_probability"],
        }
        condition_risk = max(
            heads["underweight_probability"],
            heads["stunting_probability"],
            heads["mam_probability"],
            heads["sam_probability"],
        )
        stored = {key: value for key, value in heads.items() if key != "feature_row"}
        return PredictionResult(
            status=heads["predicted_malnutrition_type"],
            severity=heads["severity"],
            raw_probabilities={"acute": acute, "ga_rgca": stored},
            calibrated_probabilities={"acute": acute, "risk": condition_risk, "ga_rgca": stored},
            risk_score=round(float(condition_risk), 4),
            confidence="elevated" if heads["uncertainty_flag"] else "low",
            latent_embedding=heads["latent_output"],
            model_version=heads["model_version"],
            calibration_version="ga-rgca-v3-binary-calibrators",
            feature_schema_version="ga-rgca-v3-current-visit-baseline",
            inference_ms=round(elapsed, 2),
            mode="PYTORCH",
            score_kind="highest_condition_probability",
            score_is_probability=True,
            score_is_calibrated=False,
            prediction_task="twelve_month_nutritional_risk",
            clinical_use=False,
            data_limitations=heads["data_limitations"],
            prediction_source="GA-RGCA-v3",
        )


def get_adapter():
    mode = settings.model_mode.lower()
    path = settings.model_artifact_path
    if mode == "sklearn":
        return SklearnModelAdapter(path)
    if mode == "onnx":
        return OnnxModelAdapter(path)
    if mode == "pytorch" and GA_MODEL is None:
        return PyTorchMultimodalAdapter(path)
    if GA_MODEL is not None:
        return GaRgcaAdapter()
    return GaRgcaAdapter()


ADAPTER = get_adapter()


@app.get("/health")
def health():
    loaded = GA_MODEL is not None
    return {
        "status": "ok",
        "service": "inference",
        "configured_model_mode": settings.model_mode,
        "mode": settings.model_mode,
        "active_model": "GA-RGCA-v3" if loaded else None,
        "ga_rgca_loaded": loaded,
    }


@app.get("/model-info")
def model_info():
    loaded = GA_MODEL is not None
    return {
        "configured_model_mode": settings.model_mode,
        "mode": settings.model_mode,
        "active_model": "GA-RGCA-v3" if loaded else None,
        "adapter": ADAPTER.__class__.__name__,
        "model_version": "GA-RGCA-v3" if loaded else None,
        "prediction_source": "GA-RGCA-v3" if loaded else None,
        "ensemble_members": len(GA_MODEL.models) if loaded else 0,
        "artifact_directory": str(GA_MODEL.directory) if loaded else None,
        "embedding_dim": settings.embedding_dim,
        "clinically_validated": False,
        "demo": False,
        "ga_rgca_loaded": loaded,
        "ga_rgca_error": GA_LOAD_ERROR,
        "ga_rgca_required_files": list(REQUIRED_FILES),
        "ga_rgca_task": "twelve_month_nutritional_risk" if loaded else None,
    }


@app.post("/predict", response_model=PredictionResult)
def predict(req: PredictRequest):
    return ADAPTER.predict(req)
