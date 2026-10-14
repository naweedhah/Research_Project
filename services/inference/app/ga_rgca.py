"""GA-RGCA v3 inference.

Architecture matches Chanodya_Component1_FINAL_GA_RGCA_v3 (FAST_MODE off:
d_model 72, hidden 112). Weights, the fitted preprocessor, and the binary
calibrators are loaded from disk. They are not stored in the notebook.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from app.malnutrition_type import derive_predicted_malnutrition_type

logger = logging.getLogger("uvicorn.error")

D_MODEL = 72
HIDDEN = 112
DROPOUT = 0.12
MODALITY_DROPOUT = 0.15

ACUTE_NAMES = ("Normal", "MAM", "SAM")
SEVERITY_NAMES = ("none", "moderate", "severe")
BINARY_NAMES = ("underweight", "stunting")

REQUIRED_FILES = (
    "ga_rgca_v3_states.pt",
    "multimodal_preprocessor.joblib",
    "binary_calibrators.joblib",
)


def artifact_dir() -> Path | None:
    candidates = []
    env = __import__("os").environ.get("GA_RGCA_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("/artifacts/ga-rgca"))
    candidates.append(Path("/ml/artifacts/ga_rgca_v3"))
    here = Path(__file__).resolve()
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / "ml" / "artifacts" / "ga_rgca_v3")
    for path in candidates:
        if path.is_dir() and all((path / name).is_file() for name in REQUIRED_FILES):
            return path
    return None


def embedding_dim(cardinality: int) -> int:
    return int(min(24, max(4, round(4 * (cardinality**0.25)))))


class ViewEncoder(nn.Module):
    def __init__(self, num_dim, cat_cardinalities, d_model=D_MODEL, hidden=HIDDEN, dropout=DROPOUT):
        super().__init__()
        self.embeddings = nn.ModuleList(
            [nn.Embedding(card, embedding_dim(card)) for card in cat_cardinalities]
        )
        emb_total = sum(e.embedding_dim for e in self.embeddings)
        input_dim = 2 * num_dim + emb_total
        if input_dim == 0:
            input_dim = 1
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
        )

    def forward(self, num, num_missing, cat):
        parts = []
        if num.shape[1] > 0:
            parts.extend([num, num_missing])
        for j, emb in enumerate(self.embeddings):
            parts.append(emb(cat[:, j]))
        x = torch.cat(parts, dim=1) if parts else torch.ones((num.shape[0], 1), device=num.device)
        return self.net(x)


class OrdinalSeverityHead(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        self.fc = nn.Linear(in_dim, 2)

    def forward(self, x):
        raw = self.fc(x)
        p_ge_moderate = torch.sigmoid(raw[:, 0])
        p_cond_severe = torch.sigmoid(raw[:, 1])
        p_severe = p_ge_moderate * p_cond_severe
        return torch.stack(
            [1.0 - p_ge_moderate, p_ge_moderate - p_severe, p_severe],
            dim=1,
        )


class MultimodalPreprocessor:
    """Unpickle target for the notebook's fitted preprocessor.

    The saved object already holds medians, scales, and category vocabularies.
    transform_record applies that fitted state without refitting.
    """


class GrowthAnchoredRGCA(nn.Module):
    def __init__(self, prep, view_specs, reliability=True, modality_dropout=MODALITY_DROPOUT):
        super().__init__()
        self.view_names = list(view_specs.keys())
        self.context_names = [v for v in self.view_names if v != "history"]
        self.reliability = reliability
        self.modality_dropout = modality_dropout
        self.encoders = nn.ModuleDict(
            {
                v: ViewEncoder(prep.num_dims[v], prep.cardinalities[v])
                for v in self.view_names
            }
        )
        self.gate_mlps = nn.ModuleDict(
            {
                v: nn.Sequential(nn.Linear(3, 16), nn.GELU(), nn.Linear(16, 1))
                for v in self.view_names
            }
        )
        self.k_proj = nn.ModuleDict({v: nn.Linear(D_MODEL, D_MODEL) for v in self.context_names})
        self.v_proj = nn.ModuleDict({v: nn.Linear(D_MODEL, D_MODEL) for v in self.context_names})
        self.null_key = nn.Parameter(torch.randn(1, D_MODEL) * 0.02)
        self.null_value = nn.Parameter(torch.randn(1, D_MODEL) * 0.02)
        self.task_tokens = nn.Parameter(torch.randn(4, D_MODEL) * 0.02)
        self.task_q = nn.ModuleList([nn.Linear(D_MODEL, D_MODEL) for _ in range(4)])
        self.context_out = nn.ModuleList([nn.Linear(D_MODEL, D_MODEL) for _ in range(4)])
        self.task_norm = nn.ModuleList([nn.LayerNorm(D_MODEL) for _ in range(4)])
        self.task_tower = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(D_MODEL, HIDDEN),
                    nn.GELU(),
                    nn.Dropout(DROPOUT),
                    nn.Linear(HIDDEN, D_MODEL),
                    nn.GELU(),
                )
                for _ in range(4)
            ]
        )
        self.binary_heads = nn.ModuleList([nn.Linear(D_MODEL, 1) for _ in range(2)])
        self.acute_head = nn.Linear(D_MODEL, 3)
        self.severity_head = OrdinalSeverityHead(D_MODEL)

    @staticmethod
    def direct_quality(q):
        return q[:, 0:1] * torch.sqrt(torch.clamp(q[:, 1:2] * q[:, 2:3], 0, 1) + 1e-8)

    def forward(self, views):
        h = {}
        gates = {}
        for v in self.view_names:
            x = views[v]
            h[v] = self.encoders[v](x["num"], x["num_missing"], x["cat"])
            if self.reliability:
                direct = self.direct_quality(x["quality"])
                learned = torch.sigmoid(self.gate_mlps[v](x["quality"]))
                gate = 0.80 * direct + 0.20 * learned
            else:
                gate = torch.ones((len(h[v]), 1), device=h[v].device)
            gates[v] = gate
        anchor = h["history"] * gates["history"]
        batch_size = len(anchor)
        keys, values = [], []
        for v in self.context_names:
            keys.append(self.k_proj[v](h[v]) * gates[v])
            values.append(self.v_proj[v](h[v]) * gates[v])
        keys.append(self.null_key.expand(batch_size, -1))
        values.append(self.null_value.expand(batch_size, -1))
        k = torch.stack(keys, dim=1)
        v = torch.stack(values, dim=1)
        reps = []
        for t in range(4):
            q = self.task_q[t](anchor + self.task_tokens[t].unsqueeze(0))
            scores = (q.unsqueeze(1) * k).sum(dim=-1) / math.sqrt(D_MODEL)
            attn = torch.softmax(scores, dim=1)
            ctx = (attn.unsqueeze(-1) * v).sum(dim=1)
            rep = self.task_norm[t](anchor + self.context_out[t](ctx))
            reps.append(rep + self.task_tower[t](rep))
        binary_logits = torch.cat([self.binary_heads[j](reps[j]) for j in range(2)], dim=1)
        acute_logits = self.acute_head(reps[2])
        severity_prob = self.severity_head(reps[3])
        return binary_logits, acute_logits, severity_prob, gates


def _finite(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def age_band(age: float | None) -> str | None:
    if age is None:
        return None
    cuts = (6, 12, 24, 36, 48, 60)
    labels = ("0-5", "6-11", "12-23", "24-35", "36-47", "48-60")
    for limit, label in zip(cuts, labels):
        if age < limit:
            return label
    return None


def transform_record(prep, row: dict) -> dict:
    output = {}
    ranges = getattr(prep, "valid_ranges", None) or {}
    for view, spec in prep.view_specs.items():
        num_cols = spec["num"]
        cat_cols = spec["cat"]
        num = np.zeros((1, len(num_cols)), dtype=np.float32)
        num_missing = np.zeros_like(num)
        cat = np.zeros((1, len(cat_cols)), dtype=np.int64)
        observed_count = 0.0
        valid_count = 0.0
        total_fields = max(1, len(num_cols) + len(cat_cols))
        for j, column in enumerate(num_cols):
            raw = _finite(row.get(column))
            observed = raw is not None
            num_missing[0, j] = 0.0 if observed else 1.0
            if observed:
                observed_count += 1.0
            stats = prep.num_stats[view][column]
            filled = raw if observed else float(stats["median"])
            num[0, j] = (filled - float(stats["mean"])) / float(stats["std"])
            if observed and column in ranges:
                lo, hi = ranges[column]
                if lo <= raw <= hi:
                    valid_count += 1.0
            elif observed:
                valid_count += 1.0
        for j, column in enumerate(cat_cols):
            raw = row.get(column)
            text = "" if raw is None else str(raw).strip()
            observed = text not in {"", "Unknown", "<NA>", "None", "nan"}
            if observed:
                observed_count += 1.0
                valid_count += 1.0
            token = text if observed else "Unknown"
            vocab = prep.cat_vocab[view][column]
            cat[0, j] = int(vocab.get(token, 0))
        availability = 1.0 if observed_count > 0 else 0.0
        completeness = float(np.clip(observed_count / total_fields, 0, 1))
        validity = valid_count / observed_count if observed_count else 0.0
        quality = np.array([[availability, completeness, validity]], dtype=np.float32)
        output[view] = {
            "num": num,
            "num_missing": num_missing,
            "cat": cat,
            "quality": quality,
        }
    return output


def _views_to_torch(views: dict) -> dict:
    return {
        name: {key: torch.from_numpy(value) for key, value in block.items()}
        for name, block in views.items()
    }


def apply_binary_calibrators(calibrators, logits: np.ndarray) -> np.ndarray:
    out = np.zeros_like(logits, dtype=float)
    for j, calibrator in enumerate(calibrators):
        column = logits[:, j : j + 1]
        if calibrator is None:
            out[:, j] = 1 / (1 + np.exp(-column[:, 0]))
        else:
            out[:, j] = calibrator.predict_proba(column)[:, 1]
    return out


SEX_VALUES = {"Female", "Male"}
EDUCATION_VALUES = {
    "No formal education",
    "Below O/ Level",
    "O/L passed",
    "A/ Level passes",
    "Degree/ diploma",
}
INCOME_VALUES = {
    "Less than Rs. 20,000",
    "Rs.20,000 to Rs. 50,000",
    "Rs. 50,000 to Rs. 100,000",
    "More than Rs. 100,000",
}
FATHER_OCCUPATION_VALUES = {
    "Abroad",
    "Government worker",
    "Manual worker",
    "No job",
    "Private sector worker",
    "Self-employed",
}
MOTHER_OCCUPATION_VALUES = {
    "Government worker",
    "Housewife",
    "Private sector worker",
    "Self-employed",
}
YES_NO = {"Yes", "No"}
BREASTFEEDING_DURATION_VALUES = {"Less than 6 months", "More than 6 months"}
COMPLEMENTARY_TIMING_VALUES = {"Before 6 months", "After 6 months"}
MEAL_VALUES = {"2 meals/day", "3 meals/day", "4+ meals/day"}
DIVERSITY_VALUES = {"Less than 2 varieties", "2 to 5 varieties", "More than 5 varieties"}
TRIPOSHA_VALUES = {"No", "Yes - irregular use", "Yes - regular use"}
STATUS_VALUES = {"Normal", "Moderate", "Severe"}


def _exact(value, allowed: set[str]) -> str | None:
    """Keep a value only when it is one of the trained category strings."""
    if value is None:
        return None
    text = str(value).strip()
    if text in allowed:
        return text
    return None


def _sex(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    mapped = {"female": "Female", "male": "Male", "f": "Female", "m": "Male"}.get(text.lower())
    if mapped:
        return mapped
    return text if text in SEX_VALUES else None


def _binary_flag(value) -> int | None:
    if value in (0, 1):
        return int(value)
    if isinstance(value, float) and value in (0.0, 1.0):
        return int(value)
    if isinstance(value, str) and value.strip() in {"0", "1"}:
        return int(value.strip())
    return None


def _nested(payload: dict, key: str) -> dict:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def build_feature_row(payload: dict) -> tuple[dict, list[str]]:
    """Map the visit being entered onto the training feature names.

    Names containing 2025 are the baseline column names from training.
    They are this visit's measurements. Unmatched categories stay missing.
    Previous model output is never used as a clinical label.
    """
    limitations: list[str] = []
    anthro = _nested(payload, "anthropometric") or payload
    socio = _nested(payload, "socioeconomic")
    context = _nested(payload, "ga_rgca_context")
    clinical = _nested(payload, "baseline_clinical")
    height = _finite(anthro.get("height_cm"))
    weight = _finite(anthro.get("weight_kg"))
    age = _finite(anthro.get("age_months"))
    birth_kg = _finite(anthro.get("birth_weight_kg"))
    bmi = None
    if height and weight and height > 0:
        bmi = weight / ((height / 100) ** 2)
    education = _exact(context.get("maternal_education"), EDUCATION_VALUES)
    if education is None and "maternal_education" not in context:
        education = _exact(socio.get("maternal_education"), EDUCATION_VALUES)
    occupation = _exact(context.get("mother_occupation"), MOTHER_OCCUPATION_VALUES)
    if occupation is None and "mother_occupation" not in context:
        occupation = _exact(socio.get("maternal_employment"), MOTHER_OCCUPATION_VALUES)
    row = {
        "Hist_2025_Age_months": age,
        "Hist_2025_Height_cm": height,
        "Hist_2025_Weight_kg": weight,
        "Hist_2025_BMI": bmi,
        "Birth_Weight_g": None if birth_kg is None else birth_kg * 1000,
        "Hist_2025_MAM": _binary_flag(clinical.get("mam")),
        "Hist_2025_SAM": _binary_flag(clinical.get("sam")),
        "Sex": _sex(anthro.get("sex")),
        "Hist_Age_Band": age_band(age),
        "Hist_2025_Underweight": _exact(clinical.get("underweight"), STATUS_VALUES),
        "Hist_2025_Stunting": _exact(clinical.get("stunting"), STATUS_VALUES),
        "Maternal_Age_2025_years": _finite(context.get("maternal_age_years")),
        "Family_Size": _finite(socio.get("household_size")),
        "Maternal_Education": education,
        "Household_Income_Range": _exact(context.get("household_income_range"), INCOME_VALUES),
        "Father_Occupation": _exact(context.get("father_occupation"), FATHER_OCCUPATION_VALUES),
        "Mother_Occupation": occupation,
        "Exclusive_Breastfeeding": _exact(context.get("exclusive_breastfeeding"), YES_NO),
        "Breastfeeding_Duration": _exact(context.get("breastfeeding_duration"), BREASTFEEDING_DURATION_VALUES),
        "Complementary_Feeding_Timing": _exact(context.get("complementary_feeding_timing"), COMPLEMENTARY_TIMING_VALUES),
        "Meal_Frequency_per_Day": _exact(context.get("meal_frequency"), MEAL_VALUES),
        "Dietary_Diversity": _exact(context.get("dietary_diversity"), DIVERSITY_VALUES),
        "Triposha_Supplementation": _exact(context.get("triposha_supplementation"), TRIPOSHA_VALUES),
        "Vitamin_Supplementation": _exact(context.get("vitamin_supplementation"), YES_NO),
    }
    if not clinical:
        limitations.append("baseline_clinical_status_not_recorded")
    for column, value in row.items():
        if value is None:
            limitations.append(f"{column}_not_recorded")
    if age is not None and age < 12:
        limitations.append("baseline_age_below_12_months")
    limitations.append("baseline_is_the_visit_being_entered")
    return row, limitations


class GaRgcaModel:
    name = "GA-RGCA-v3"

    def __init__(self, directory: Path):
        import __main__
        import joblib

        __main__.MultimodalPreprocessor = MultimodalPreprocessor
        self.directory = directory
        logger.info("GA-RGCA v3 artifacts found")
        self.prep = joblib.load(directory / "multimodal_preprocessor.joblib")
        logger.info("GA-RGCA v3 preprocessor loaded")
        self.calibrators = joblib.load(directory / "binary_calibrators.joblib")
        if not isinstance(self.calibrators, list) or len(self.calibrators) != 2:
            raise RuntimeError("binary_calibrators.joblib must contain two calibrators")
        logger.info("GA-RGCA v3 binary calibrators loaded")
        states = torch.load(directory / "ga_rgca_v3_states.pt", map_location="cpu", weights_only=False)
        if not isinstance(states, list) or len(states) == 0:
            raise RuntimeError("ga_rgca_v3_states.pt must contain a list of state dictionaries")
        metadata_path = directory / "metadata.json"
        if not metadata_path.is_file():
            raise RuntimeError("metadata.json is missing")
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self._require_metadata()
        logger.info("GA-RGCA v3 metadata loaded")
        thresholds = self.metadata["binary_thresholds"]
        self.thresholds = np.asarray(
            [float(thresholds["Underweight"]), float(thresholds["Stunting"])],
            dtype=float,
        )
        self.acute_temperature = float(self.metadata["acute_temperature"])
        self.severity_temperature = float(self.metadata["severity_temperature"])
        self.uncertainty_q95 = float(self.metadata["uncertainty_binary_variance_q95"])
        specs = self.prep.view_specs
        self.models = []
        for state in states:
            model = GrowthAnchoredRGCA(self.prep, specs)
            model.load_state_dict(state, strict=True)
            model.eval()
            self.models.append(model)
        logger.info("GA-RGCA v3 ensemble members loaded: %s", len(self.models))

    def _require_metadata(self) -> None:
        missing: list[str] = []
        thresholds = self.metadata.get("binary_thresholds")
        if not isinstance(thresholds, dict) or "Underweight" not in thresholds or "Stunting" not in thresholds:
            missing.append("binary_thresholds.Underweight and binary_thresholds.Stunting")
        for key in ("acute_temperature", "severity_temperature", "uncertainty_binary_variance_q95", "model_version"):
            if self.metadata.get(key) is None:
                missing.append(key)
        rules = (self.metadata.get("triage") or {}).get("rules") or {}
        order = (self.metadata.get("triage") or {}).get("evaluation_order")
        if not isinstance(order, list) or not order:
            missing.append("triage.evaluation_order")
        for name in ("SAM", "MAM", "binary_positive", "uncertainty", "routine"):
            label = (rules.get(name) or {}).get("label")
            if not label:
                missing.append(f"triage.rules.{name}.label")
        if missing:
            raise RuntimeError("metadata.json is missing required values: " + ", ".join(missing))

    def predict_prior(self, payload: dict) -> dict:
        row, limitations = build_feature_row(payload)
        missing_growth = [
            name
            for name, key in (
                ("height_cm", "Hist_2025_Height_cm"),
                ("weight_kg", "Hist_2025_Weight_kg"),
            )
            if row[key] is None
        ]
        if missing_growth:
            raise IncompleteBaseline(missing_growth, row)
        logger.info("GA-RGCA feature row (no identifiers): %s", json.dumps(row, default=str))
        views = _views_to_torch(transform_record(self.prep, row))
        binary_logits = []
        acute_logits = []
        severity = []
        gate_values: dict[str, list[float]] = {}
        with torch.no_grad():
            for model in self.models:
                binary, acute, severe, gates = model(views)
                binary_logits.append(binary.numpy())
                acute_logits.append(acute.numpy())
                severity.append(severe.numpy())
                for name, gate in gates.items():
                    gate_values.setdefault(name, []).append(float(gate.detach().mean()))
        mean_logits = np.mean(binary_logits, axis=0)
        mean_acute_logits = np.mean(acute_logits, axis=0)[0]
        mean_severity = np.mean(severity, axis=0)[0]
        acute_scaled = _temperature_softmax(mean_acute_logits, self.acute_temperature)
        severity_scaled = _temperature_probabilities(mean_severity, self.severity_temperature)
        binary_prob = apply_binary_calibrators(self.calibrators, mean_logits)[0]
        binary_pred = binary_prob >= self.thresholds
        variance = float(np.stack([1 / (1 + np.exp(-x)) for x in binary_logits], axis=0).var(axis=0).mean())
        uncertainty_flag = bool(variance > self.uncertainty_q95)
        acute_index = int(np.argmax(acute_scaled))
        severity_index = int(np.argmax(severity_scaled))
        severity_names = self.metadata.get("severity_output") or {}
        acute_names = self.metadata.get("acute_output") or {}
        severity_label = severity_names.get(str(severity_index), SEVERITY_NAMES[severity_index])
        acute_status = acute_names.get(str(acute_index), ACUTE_NAMES[acute_index])
        underweight_status = "Positive" if binary_pred[0] else "Normal"
        stunting_status = "Positive" if binary_pred[1] else "Normal"
        triage = _triage_label(
            self.metadata,
            acute_index=acute_index,
            underweight_positive=bool(binary_pred[0]),
            stunting_positive=bool(binary_pred[1]),
            uncertainty_flag=uncertainty_flag,
        )
        reliability = {
            name: round(float(np.mean(values)), 4)
            for name, values in gate_values.items()
        }
        underweight_probability = round(float(binary_prob[0]), 4)
        stunting_probability = round(float(binary_prob[1]), 4)
        interpretation = derive_predicted_malnutrition_type(
            underweight_probability=underweight_probability,
            stunting_probability=stunting_probability,
            underweight_threshold=float(self.thresholds[0]),
            stunting_threshold=float(self.thresholds[1]),
            acute_status=acute_status,
        )
        uncertainty_label = (
            "Clinician review recommended because prediction uncertainty is elevated"
            if uncertainty_flag
            else "Low / no elevated model uncertainty"
        )
        return {
            "architecture": self.metadata.get("architecture", "GA-RGCA v3"),
            "prediction_task": "twelve_month_nutritional_risk",
            "clinical_use": False,
            "disclaimer": self.metadata.get("disclaimer"),
            "underweight_probability": underweight_probability,
            "stunting_probability": stunting_probability,
            "underweight_positive": interpretation["underweight_positive"],
            "stunting_positive": interpretation["stunting_positive"],
            "predicted_malnutrition_type": interpretation["predicted_malnutrition_type"],
            "detected_conditions": interpretation["detected_conditions"],
            "uw_decision_strength": interpretation["uw_decision_strength"],
            "st_decision_strength": interpretation["st_decision_strength"],
            "underweight_status": underweight_status,
            "stunting_status": stunting_status,
            "mam_probability": round(float(acute_scaled[1]), 4),
            "sam_probability": round(float(acute_scaled[2]), 4),
            "normal_acute_probability": round(float(acute_scaled[0]), 4),
            "acute_status": acute_status,
            "acute_probability": round(float(acute_scaled[acute_index]), 4),
            "severity": severity_label,
            "severity_probabilities": {
                "normal": round(float(severity_scaled[0]), 4),
                "moderate": round(float(severity_scaled[1]), 4),
                "severe": round(float(severity_scaled[2]), 4),
            },
            "ensemble_seeds": len(self.models),
            "binary_variance": round(variance, 6),
            "uncertainty_threshold": self.uncertainty_q95,
            "uncertainty_flag": uncertainty_flag,
            "uncertainty_label": uncertainty_label,
            "triage": triage,
            "modality_reliability": reliability,
            "model_version": self.metadata.get("model_version", self.name),
            "prediction_source": "GA-RGCA-v3",
            "binary_thresholds": {
                "Underweight": float(self.thresholds[0]),
                "Stunting": float(self.thresholds[1]),
            },
            "binary_probabilities_calibrated": True,
            "acute_probabilities_temperature_scaled": True,
            "severity_probabilities_temperature_scaled": True,
            "data_limitations": limitations,
            "feature_row": row,
            "latent_output": [round(float(v), 4) for v in (*mean_logits[0], *acute_scaled)],
        }


class IncompleteBaseline(Exception):
    def __init__(self, missing: list[str], row: dict):
        self.missing = missing
        self.row = row
        super().__init__(", ".join(missing))


def _temperature_softmax(logits: np.ndarray, temperature: float) -> np.ndarray:
    scaled = np.exp((logits - np.max(logits)) / float(temperature))
    return scaled / scaled.sum()


def _temperature_probabilities(probs: np.ndarray, temperature: float) -> np.ndarray:
    clipped = np.clip(probs, 1e-8, 1.0)
    powered = np.exp(np.log(clipped) / float(temperature))
    return powered / powered.sum()


def _triage_label(
    metadata: dict,
    *,
    acute_index: int,
    underweight_positive: bool,
    stunting_positive: bool,
    uncertainty_flag: bool,
) -> str:
    triage = metadata["triage"]
    rules = triage["rules"]
    for key in triage["evaluation_order"]:
        if key == "SAM" and acute_index == 2:
            return rules["SAM"]["label"]
        if key == "MAM" and acute_index == 1:
            return rules["MAM"]["label"]
        if key == "binary_positive" and (underweight_positive or stunting_positive):
            return rules["binary_positive"]["label"]
        if key == "uncertainty" and uncertainty_flag:
            return rules["uncertainty"]["label"]
        if key == "routine":
            return rules["routine"]["label"]
    return rules["routine"]["label"]


def load_ga_rgca() -> tuple[GaRgcaModel | None, str | None]:
    directory = artifact_dir()
    if directory is None:
        logger.error("GA-RGCA v3 artifacts were not found")
        return None, "GA-RGCA v3 artifact files are not on this machine"
    try:
        model = GaRgcaModel(directory)
    except Exception as exc:  # noqa: BLE001 — surface the load error to model-info
        logger.exception("GA-RGCA v3 failed to load: %s", exc)
        return None, f"GA-RGCA v3 artifacts were found but could not be loaded: {exc}"
    logger.info("GA-RGCA v3 ready")
    return model, None
