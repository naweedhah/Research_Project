"""GA-RGCA v4 Rolling SuperLearner runtime.

The neural class, preprocessor, and fusion functions are the deployment path
from Chanodya_Component1_FINAL_GA_RGCA_v4_Rolling_SuperLearner (FAST_MODE off:
d_model 96, hidden 144, 4 heads). Weights are loaded strictly. This module
does not retrain or alter thresholds.
"""

from __future__ import annotations

import json
import logging
import math
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.special import expit, softmax
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)

V4_MODEL_VERSION = "GA-RGCA-v4-Rolling-RSL"
V4_HORIZON_MONTHS = 12
V4_D_MODEL = 96
V4_HIDDEN = 144
V4_HEADS = 4
V4_DROPOUT = 0.15
V4_MODALITY_DROPOUT = 0.20
V4_BATCH_SIZE = 64
V4_CONFORMAL_ALPHA = 0.10
DEVICE = torch.device("cpu")

REQUIRED_FILES = (
    "ga_rgca_v4_states.pt",
    "multimodal_preprocessor_v4.joblib",
    "binary_calibrators_v4.joblib",
    "rolling_tree_experts_v4.joblib",
    "superlearner_policy_v4.joblib",
    "metadata_v4.json",
)
EXPERT_NAMES = ("LogisticRegression", "RandomForest", "XGBoost", "LightGBM", "GA_RGCA_v4")
TASK_NAMES = ("Underweight", "Stunting", "Acute", "Severity")
BINARY_NAMES = ["Underweight", "Stunting"]
ACUTE_NAMES = {0: "Normal", 1: "MAM", 2: "SAM"}
SEVERITY_NAMES = {0: "Normal", 1: "Moderate", 2: "Severe"}
FORBIDDEN_ROLLING_INPUTS = {
    "Hist_2025_MAM",
    "Hist_2025_SAM",
    "Hist_2025_Underweight",
    "Hist_2025_Stunting",
    "Target_Underweight",
    "Target_Stunting",
    "Target_Acute",
    "Target_Severity",
    "MAM",
    "SAM",
    "Underweight",
    "Stunting",
    "Malnutrition_Type",
    "Malnutrition_Severity",
}
ROLLING_VIEW_SPECS = {
    "history": {
        "num": [
            "Baseline_Age_months",
            "Baseline_Height_cm",
            "Baseline_Weight_kg",
            "Baseline_BMI",
            "Birth_Weight_g",
        ],
        "cat": ["Sex", "Baseline_Age_Band"],
    },
    "socioeconomic": {
        "num": ["Baseline_Maternal_Age_years", "Family_Size"],
        "cat": [
            "Maternal_Education",
            "Household_Income_Range",
            "Father_Occupation",
            "Mother_Occupation",
        ],
    },
    "feeding": {
        "num": [],
        "cat": [
            "Exclusive_Breastfeeding",
            "Breastfeeding_Duration",
            "Complementary_Feeding_Timing",
            "Meal_Frequency_per_Day",
            "Dietary_Diversity",
        ],
    },
    "supplementation": {
        "num": [],
        "cat": ["Triposha_Supplementation", "Vitamin_Supplementation"],
    },
}
ROLLING_VALID_RANGES = {
    "Baseline_Age_months": (0, 60),
    "Baseline_Height_cm": (40, 125),
    "Baseline_Weight_kg": (1, 40),
    "Baseline_BMI": (5, 40),
    "Birth_Weight_g": (400, 6500),
    "Baseline_Maternal_Age_years": (14, 60),
    "Family_Size": (1, 30),
}
RESEARCH_LIMITATIONS = [
    "Research decision-support prototype. Clinician confirmation is required.",
    "One historical 12-month prediction origin is validated. Repeated rolling-origin prospective validation is still required.",
    "External prospective validation is still required.",
    "Contextual predictor timing should be verified where those fields were not independently timestamped.",
    "Incident SAM validation remains underpowered.",
    "The latent-distance flag is an applicability reference against the training latent distribution. It is not externally validated out-of-distribution detection.",
]

# Frontend / API aliases. A value is used only when the mapped token is in the
# saved vocabulary for that column. Anything else stays missing (Unknown).
CATEGORY_ALIASES: dict[str, dict[str, str]] = {
    "Sex": {"female": "Female", "male": "Male", "f": "Female", "m": "Male"},
    "Exclusive_Breastfeeding": {"yes": "Yes", "no": "No"},
    "Vitamin_Supplementation": {"yes": "Yes", "no": "No"},
    "Breastfeeding_Duration": {
        "less than 6 months": "Less than 6 months",
        "more than 6 months": "More than 6 months",
    },
    "Complementary_Feeding_Timing": {
        "before 6 months": "Before 6 months",
        "after 6 months": "After 6 months",
    },
    "Meal_Frequency_per_Day": {
        "2": "2 meals/day",
        "3": "3 meals/day",
        "4": "4+ meals/day",
        "2 meals/day": "2 meals/day",
        "3 meals/day": "3 meals/day",
        "4+ meals/day": "4+ meals/day",
    },
    "Dietary_Diversity": {
        "less than 2 varieties": "Less than 2 varieties",
        "2 to 5 varieties": "2 to 5 varieties",
        "more than 5 varieties": "More than 5 varieties",
    },
    "Triposha_Supplementation": {
        "no": "No",
        "yes - irregular use": "Yes - irregular use",
        "yes - regular use": "Yes - regular use",
    },
}


class IncompleteVisit(Exception):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(", ".join(missing))


def artifact_dir() -> Path | None:
    """Resolve v4 weights from the repository, then an optional override.

    A blank GA_RGCA_V4_DIR uses <repo>/ml/artifacts/ga_rgca_v4_rsl so the same
    checkout works for any Windows user. Relative overrides are also from the
    repository root, not the current working directory.
    """
    import os

    here = Path(__file__).resolve()
    repo = here.parents[3]
    candidates: list[Path] = []
    configured = os.environ.get("GA_RGCA_V4_DIR", "").strip()
    if configured:
        override = Path(configured)
        candidates.append(override if override.is_absolute() else repo / override)
    candidates.append(repo / "ml" / "artifacts" / "ga_rgca_v4_rsl")
    candidates.append(Path("/artifacts/ga-rgca-v4"))
    for path in candidates:
        if path.is_dir() and all((path / name).is_file() for name in REQUIRED_FILES):
            return path
    return None


def flatten_features(view_specs: dict) -> list[str]:
    columns: list[str] = []
    for spec in view_specs.values():
        columns.extend(spec["num"])
        columns.extend(spec["cat"])
    return list(dict.fromkeys(columns))


def make_age_band(age):
    return pd.cut(
        age,
        bins=[-0.01, 5, 11, 23, 35, 47, 60],
        labels=["0-5", "6-11", "12-23", "24-35", "36-47", "48-60"],
        include_lowest=True,
    ).astype("string")


def v4_embedding_dim(cardinality: int) -> int:
    return int(min(24, max(4, round(4 * (cardinality**0.25)))))


class MultimodalPreprocessor:
    """Exact training preprocessor. Joblib instances resolve to this class."""

    def __init__(self, view_specs, valid_ranges=None):
        self.view_specs = deepcopy(view_specs)
        self.valid_ranges = valid_ranges or {}

    def fit(self, frame):
        self.num_stats = {}
        self.cat_vocab = {}
        self.cardinalities = {}
        self.num_dims = {}
        for view, spec in self.view_specs.items():
            self.num_stats[view] = {}
            self.cat_vocab[view] = {}
            self.cardinalities[view] = []
            self.num_dims[view] = len(spec["num"])
            for column in spec["num"]:
                series = pd.to_numeric(frame[column], errors="coerce")
                median = float(series.median()) if series.notna().any() else 0.0
                filled = series.fillna(median)
                mean = float(filled.mean())
                std = float(filled.std(ddof=0))
                if not np.isfinite(std) or std < 1e-8:
                    std = 1.0
                self.num_stats[view][column] = {"median": median, "mean": mean, "std": std}
            for column in spec["cat"]:
                series = frame[column].astype("string").fillna("Unknown").str.strip()
                values = sorted(value for value in series.unique().tolist() if value not in {"<UNK>", "Unknown", "<NA>", ""})
                vocab = {"<UNK>": 0, "Unknown": 1}
                for value in values:
                    if value not in vocab:
                        vocab[value] = len(vocab)
                self.cat_vocab[view][column] = vocab
                self.cardinalities[view].append(len(vocab))
        return self

    def transform(self, frame):
        output = {}
        for view, spec in self.view_specs.items():
            n = len(frame)
            num = np.zeros((n, len(spec["num"])), dtype=np.float32)
            num_missing = np.zeros_like(num, dtype=np.float32)
            cat = np.zeros((n, len(spec["cat"])), dtype=np.int64)
            observed_count = np.zeros(n, dtype=np.float32)
            valid_count = np.zeros(n, dtype=np.float32)
            total_fields = max(1, len(spec["num"]) + len(spec["cat"]))
            for j, column in enumerate(spec["num"]):
                series = pd.to_numeric(frame[column], errors="coerce")
                observed = series.notna().to_numpy()
                num_missing[:, j] = (~observed).astype(np.float32)
                observed_count += observed.astype(np.float32)
                stats = self.num_stats[view][column]
                values = series.fillna(stats["median"]).to_numpy(dtype=np.float32)
                num[:, j] = (values - stats["mean"]) / stats["std"]
                if column in self.valid_ranges:
                    lo, hi = self.valid_ranges[column]
                    valid = observed & series.between(lo, hi, inclusive="both").to_numpy()
                else:
                    valid = observed
                valid_count += valid.astype(np.float32)
            for j, column in enumerate(spec["cat"]):
                series = frame[column].astype("string").fillna("Unknown").str.strip()
                observed = (~series.isin(["", "Unknown", "<NA>"])).to_numpy()
                observed_count += observed.astype(np.float32)
                valid_count += observed.astype(np.float32)
                vocab = self.cat_vocab[view][column]
                cat[:, j] = np.array([vocab.get(str(value), 0) for value in series], dtype=np.int64)
            availability = (observed_count > 0).astype(np.float32)
            completeness = np.clip(observed_count / total_fields, 0, 1)
            validity = np.divide(
                valid_count,
                np.maximum(observed_count, 1),
                out=np.zeros_like(valid_count),
                where=np.maximum(observed_count, 1) > 0,
            ).astype(np.float32)
            quality = np.stack([availability, completeness, validity], axis=1).astype(np.float32)
            output[view] = {"num": num, "num_missing": num_missing, "cat": cat, "quality": quality}
        return output


class MultiViewDataset(Dataset):
    def __init__(self, transformed, y_binary=None, y_acute=None, y_sev=None):
        self.views = transformed
        self.n = len(next(iter(transformed.values()))["quality"])
        self.y_binary = np.zeros((self.n, 2), dtype=np.float32) if y_binary is None else np.asarray(y_binary, dtype=np.float32)
        self.y_acute = np.zeros(self.n, dtype=np.int64) if y_acute is None else np.asarray(y_acute, dtype=np.int64)
        self.y_sev = np.zeros(self.n, dtype=np.int64) if y_sev is None else np.asarray(y_sev, dtype=np.int64)

    def __len__(self):
        return self.n

    def __getitem__(self, index):
        views = {}
        for view, data in self.views.items():
            views[view] = {
                "num": torch.tensor(data["num"][index], dtype=torch.float32),
                "num_missing": torch.tensor(data["num_missing"][index], dtype=torch.float32),
                "cat": torch.tensor(data["cat"][index], dtype=torch.long),
                "quality": torch.tensor(data["quality"][index], dtype=torch.float32),
            }
        return {
            "views": views,
            "y_binary": torch.tensor(self.y_binary[index], dtype=torch.float32),
            "y_acute": torch.tensor(self.y_acute[index], dtype=torch.long),
            "y_sev": torch.tensor(self.y_sev[index], dtype=torch.long),
        }


def move_batch(batch):
    return {
        "views": {view: {key: value.to(DEVICE) for key, value in payload.items()} for view, payload in batch["views"].items()},
        "y_binary": batch["y_binary"].to(DEVICE),
        "y_acute": batch["y_acute"].to(DEVICE),
        "y_sev": batch["y_sev"].to(DEVICE),
    }


def make_loader_v4(prep, frame, y_binary=None, y_acute=None, y_sev=None, training=False):
    transformed = prep.transform(frame)
    dataset = MultiViewDataset(transformed, y_binary, y_acute, y_sev)
    return DataLoader(dataset, batch_size=V4_BATCH_SIZE, shuffle=bool(training), num_workers=0, pin_memory=False, drop_last=False)


@torch.no_grad()
def predict_loader(model, loader):
    model.eval()
    binary_logits_all, acute_prob_all, sev_prob_all = [], [], []
    extras_acc: dict[str, list] = {}
    for batch in loader:
        batch = move_batch(batch)
        binary_logits, acute_prob, sev_prob, extras = model(batch["views"])
        binary_logits_all.append(binary_logits.cpu().numpy())
        acute_prob_all.append(acute_prob.cpu().numpy())
        sev_prob_all.append(sev_prob.cpu().numpy())
        for key, value in extras.items():
            extras_acc.setdefault(key, []).append(value.detach().cpu().numpy())
    return (
        np.concatenate(binary_logits_all, axis=0),
        np.concatenate(acute_prob_all, axis=0),
        np.concatenate(sev_prob_all, axis=0),
        {key: np.concatenate(value, axis=0) for key, value in extras_acc.items()},
    )


def apply_binary_calibrators(calibrators, logits):
    out = np.zeros_like(logits, dtype=float)
    for j, calibrator in enumerate(calibrators):
        if calibrator is None:
            out[:, j] = expit(logits[:, j])
        else:
            out[:, j] = calibrator.predict_proba(logits[:, j : j + 1])[:, 1]
    return out


def apply_temperature_to_probs(prob, temperature):
    prob = np.clip(np.asarray(prob, dtype=float), 1e-8, 1.0)
    return softmax(np.log(prob) / temperature, axis=1)


def _make_sklearn_safe_frame(frame_part, view_specs):
    frame = frame_part.copy()
    for column in flatten_features(view_specs):
        if column not in frame.columns:
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
        else:
            series = frame[column].astype(object)
            missing = pd.isna(series)
            series = series.astype(object)
            series.loc[missing] = np.nan
            series = series.replace({"": np.nan, "NA": np.nan, "N/A": np.nan, "NaN": np.nan, "nan": np.nan, "None": np.nan, "<NA>": np.nan})
            frame[column] = series
    return frame


def _align_multiclass_probabilities(model, probabilities, n_classes=3):
    aligned = np.zeros((probabilities.shape[0], n_classes), dtype=float)
    model_classes = np.asarray(model.classes_, dtype=int)
    aligned[:, model_classes] = probabilities
    aligned = np.clip(aligned, 1e-8, 1.0)
    return aligned / aligned.sum(axis=1, keepdims=True)


def _aps_sets_local(prob, qhat):
    order = np.argsort(-prob, axis=1)
    sorted_p = np.take_along_axis(prob, order, axis=1)
    cumulative = np.cumsum(sorted_p, axis=1)
    sets = []
    for i in range(len(prob)):
        k = int(np.searchsorted(cumulative[i], qhat, side="left"))
        k = min(k, prob.shape[1] - 1)
        sets.append(set(order[i, : k + 1].tolist()))
    return sets


class ViewEncoderV4(nn.Module):
    def __init__(self, num_dim, cat_cardinalities):
        super().__init__()
        self.embeddings = nn.ModuleList([nn.Embedding(card, v4_embedding_dim(card)) for card in cat_cardinalities])
        emb_total = sum(embedding.embedding_dim for embedding in self.embeddings)
        input_dim = 2 * num_dim + emb_total
        if input_dim == 0:
            input_dim = 1
        self.net = nn.Sequential(
            nn.Linear(input_dim, V4_HIDDEN),
            nn.GELU(),
            nn.LayerNorm(V4_HIDDEN),
            nn.Dropout(V4_DROPOUT),
            nn.Linear(V4_HIDDEN, V4_D_MODEL),
            nn.GELU(),
            nn.LayerNorm(V4_D_MODEL),
        )

    def forward(self, num, num_missing, cat):
        parts = []
        if num.shape[1] > 0:
            parts.extend([num, num_missing])
        for j, embedding in enumerate(self.embeddings):
            parts.append(embedding(cat[:, j]))
        if parts:
            hidden = torch.cat(parts, dim=1)
        else:
            hidden = torch.ones((num.shape[0], 1), device=num.device)
        return self.net(hidden)


class MonotonicOrdinalSeverityHeadV4(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        self.score = nn.Linear(in_dim, 1)
        self.cut0 = nn.Parameter(torch.tensor(-0.5))
        self.cut_gap_raw = nn.Parameter(torch.tensor(0.0))

    def forward(self, hidden):
        score = self.score(hidden).squeeze(1)
        cut1 = self.cut0
        cut2 = self.cut0 + F.softplus(self.cut_gap_raw) + 1e-3
        p_ge_mod = torch.sigmoid(score - cut1)
        p_ge_sev = torch.sigmoid(score - cut2)
        p0 = 1.0 - p_ge_mod
        p2 = p_ge_sev
        p1 = torch.clamp(p_ge_mod - p_ge_sev, min=1e-7)
        probabilities = torch.stack([p0, p1, p2], dim=1)
        return probabilities / probabilities.sum(dim=1, keepdim=True).clamp_min(1e-7)


class GrowthAnchoredRGCAV4(nn.Module):
    def __init__(self, prep, view_specs, reliability=True, modality_dropout=V4_MODALITY_DROPOUT):
        super().__init__()
        self.view_names = list(view_specs.keys())
        if "history" not in self.view_names:
            raise ValueError("GA-RGCA v4 requires a history growth-anchor view.")
        self.context_names = [view for view in self.view_names if view != "history"]
        self.reliability = reliability
        self.modality_dropout = modality_dropout
        self.encoders = nn.ModuleDict({view: ViewEncoderV4(prep.num_dims[view], prep.cardinalities[view]) for view in self.view_names})
        self.gate_mlps = nn.ModuleDict({
            view: nn.Sequential(nn.Linear(6, 24), nn.GELU(), nn.Dropout(0.05), nn.Linear(24, 1)) for view in self.view_names
        })
        self.k_proj = nn.ModuleDict({view: nn.Linear(V4_D_MODEL, V4_D_MODEL) for view in self.context_names})
        self.v_proj = nn.ModuleDict({view: nn.Linear(V4_D_MODEL, V4_D_MODEL) for view in self.context_names})
        self.missing_tokens = nn.ParameterDict({view: nn.Parameter(torch.randn(1, V4_D_MODEL) * 0.02) for view in self.context_names})
        self.null_token = nn.Parameter(torch.randn(1, 1, V4_D_MODEL) * 0.02)
        self.task_tokens = nn.Parameter(torch.randn(4, V4_D_MODEL) * 0.02)
        self.task_q = nn.ModuleList([nn.Linear(V4_D_MODEL, V4_D_MODEL) for _ in range(4)])
        self.task_attn = nn.ModuleList([
            nn.MultiheadAttention(embed_dim=V4_D_MODEL, num_heads=V4_HEADS, dropout=0.05, batch_first=True) for _ in range(4)
        ])
        self.task_norm1 = nn.ModuleList([nn.LayerNorm(V4_D_MODEL) for _ in range(4)])
        self.task_ff = nn.ModuleList([
            nn.Sequential(nn.Linear(V4_D_MODEL, V4_HIDDEN), nn.GELU(), nn.Dropout(V4_DROPOUT), nn.Linear(V4_HIDDEN, V4_D_MODEL))
            for _ in range(4)
        ])
        self.task_norm2 = nn.ModuleList([nn.LayerNorm(V4_D_MODEL) for _ in range(4)])
        self.binary_heads = nn.ModuleList([nn.Linear(V4_D_MODEL, 1) for _ in range(2)])
        self.acute_head = nn.Linear(V4_D_MODEL, 3)
        self.severity_head = MonotonicOrdinalSeverityHeadV4(V4_D_MODEL)

    @staticmethod
    def _direct_quality(quality):
        return quality[:, 0:1] * torch.sqrt(torch.clamp(quality[:, 1:2] * quality[:, 2:3], 0, 1) + 1e-8)

    def forward(self, views):
        encoded = {view: self.encoders[view](views[view]["num"], views[view]["num_missing"], views[view]["cat"]) for view in self.view_names}
        anchor_raw = encoded["history"]
        anchor_norm = torch.norm(anchor_raw, dim=1, keepdim=True) / math.sqrt(V4_D_MODEL)
        gates = {}
        reliability_gates = {}
        for view in self.view_names:
            quality = views[view]["quality"]
            direct = self._direct_quality(quality)
            if self.reliability:
                if view == "history":
                    compatibility = torch.ones_like(direct)
                else:
                    compatibility = F.cosine_similarity(encoded[view], anchor_raw, dim=1).unsqueeze(1)
                    compatibility = (compatibility + 1.0) / 2.0
                view_norm = torch.norm(encoded[view], dim=1, keepdim=True) / math.sqrt(V4_D_MODEL)
                gate_input = torch.cat([quality, compatibility, view_norm, anchor_norm], dim=1)
                learned = torch.sigmoid(self.gate_mlps[view](gate_input))
                gate = torch.clamp(0.55 * direct + 0.45 * learned, 0.0, 1.0)
            else:
                gate = torch.ones_like(direct)
            reliability_gates[view] = gate
            if self.training and view != "history" and self.modality_dropout > 0:
                keep = (torch.rand_like(gate) >= self.modality_dropout).float()
                gate = gate * keep
            gates[view] = gate
        anchor = anchor_raw * gates["history"]
        context_tokens = []
        for view in self.context_names:
            gate = gates[view]
            projected = self.v_proj[view](encoded[view])
            token = gate * projected + (1.0 - gate) * self.missing_tokens[view].expand(len(encoded[view]), -1)
            context_tokens.append(token)
        context = torch.stack(context_tokens, dim=1)
        context = torch.cat([context, self.null_token.expand(len(anchor), -1, -1)], dim=1)
        representations, attention = [], []
        for task in range(4):
            query = self.task_q[task](anchor + self.task_tokens[task].unsqueeze(0)).unsqueeze(1)
            attended, weights = self.task_attn[task](query, context, context, need_weights=True)
            hidden = self.task_norm1[task](query.squeeze(1) + attended.squeeze(1))
            hidden = self.task_norm2[task](hidden + self.task_ff[task](hidden))
            representations.append(hidden)
            attention.append(weights.squeeze(1))
        binary_logits = torch.cat([self.binary_heads[j](representations[j]) for j in range(2)], dim=1)
        acute_logits = self.acute_head(representations[2])
        acute_prob = torch.softmax(acute_logits, dim=1)
        severity_prob = self.severity_head(representations[3])
        fused_latent = torch.stack(representations, dim=1).mean(dim=1)
        extras = {
            "gates": torch.cat([gates[view] for view in self.view_names], dim=1),
            "reliability_gates": torch.cat([reliability_gates[view] for view in self.view_names], dim=1),
            "attention": torch.stack(attention, dim=1),
            "latent": fused_latent,
            "acute_logits": acute_logits,
        }
        return binary_logits, acute_prob, severity_prob, extras


def _predict_tree_expert_v4(bundle, frame):
    safe = _make_sklearn_safe_frame(frame, ROLLING_VIEW_SPECS)
    features = bundle["preprocessor"].transform(safe)
    raw_binary = np.column_stack([model.predict_proba(features)[:, 1] for model in bundle["binary_models"]])
    from scipy.special import logit

    logits = logit(np.clip(raw_binary, 1e-6, 1 - 1e-6))
    binary = np.zeros_like(raw_binary)
    for j, calibrator in enumerate(bundle["binary_calibrators"]):
        binary[:, j] = expit(logits[:, j]) if calibrator is None else calibrator.predict_proba(logits[:, j : j + 1])[:, 1]
    raw_acute = _align_multiclass_probabilities(bundle["acute_model"], bundle["acute_model"].predict_proba(features), 3)
    acute = apply_temperature_to_probs(raw_acute, bundle["acute_temperature"])
    raw_severity = _align_multiclass_probabilities(bundle["severity_model"], bundle["severity_model"].predict_proba(features), 3)
    severity = apply_temperature_to_probs(raw_severity, bundle["severity_temperature"])
    return {"binary": binary, "acute": acute, "severity": severity}


@torch.no_grad()
def _predict_neural_core_v4(bundle, frame):
    loader = make_loader_v4(bundle["prep"], frame, training=False)
    binary_logits, acute_raw, severity_raw, extras = [], [], [], []
    member_condition_probs = []
    for model in bundle["models"]:
        logits, acute, severity, extra = predict_loader(model, loader)
        binary_logits.append(logits)
        acute_raw.append(acute)
        severity_raw.append(severity)
        extras.append(extra)
        member_condition_probs.append(np.column_stack([expit(logits), acute[:, 1], acute[:, 2]]))
    mean_logits = np.mean(binary_logits, axis=0)
    binary = apply_binary_calibrators(bundle["binary_calibrators"], mean_logits)
    acute = apply_temperature_to_probs(np.mean(acute_raw, axis=0), bundle["acute_temperature"])
    severity = apply_temperature_to_probs(np.mean(severity_raw, axis=0), bundle["severity_temperature"])
    out_extras = {}
    for key in ["reliability_gates", "gates", "attention", "latent"]:
        values = [item[key] for item in extras if key in item]
        if values:
            out_extras[key] = np.mean(values, axis=0)
    variance = np.var(np.stack(member_condition_probs, axis=0), axis=0).mean(axis=1)
    return {"binary": binary, "acute": acute, "severity": severity, "variance": variance, "extras": out_extras}


def _derive_primary_type_v4(binary_prob, thresholds, acute_prob):
    underweight = bool(binary_prob[0] >= thresholds[0])
    stunting = bool(binary_prob[1] >= thresholds[1])
    acute = int(np.argmax(acute_prob))
    detected = []
    if underweight:
        detected.append("Underweight")
    if stunting:
        detected.append("Stunting")
    if acute == 1:
        detected.append("MAM")
    if acute == 2:
        detected.append("SAM")
    if acute == 2:
        primary = "SAM"
    elif acute == 1:
        primary = "MAM"
    elif underweight and stunting:
        underweight_strength = (binary_prob[0] - thresholds[0]) / max(1 - thresholds[0], 1e-8)
        stunting_strength = (binary_prob[1] - thresholds[1]) / max(1 - thresholds[1], 1e-8)
        primary = "Stunting" if stunting_strength >= underweight_strength else "Underweight"
    elif stunting:
        primary = "Stunting"
    elif underweight:
        primary = "Underweight"
    else:
        primary = "Normal"
    return primary, detected, underweight, stunting, acute


def predict_v4_deployment_bundle(bundle, snapshot_frame):
    """Notebook deployment function: neural core, tabular experts, then policy fusion."""
    leaked = sorted(set(snapshot_frame.columns).intersection(FORBIDDEN_ROLLING_INPUTS))
    if leaked:
        raise RuntimeError(f"Forbidden target leakage in the rolling snapshot: {leaked}")
    neural = _predict_neural_core_v4(bundle["neural"], snapshot_frame)
    expert = {"GA_RGCA_v4": neural}
    for name, tree_bundle in bundle["trees"].items():
        expert[name] = _predict_tree_expert_v4(tree_bundle, snapshot_frame)
    names = bundle["candidate_names"]
    binary = np.zeros((len(snapshot_frame), 2), dtype=float)
    for j, task in enumerate(BINARY_NAMES):
        weights = np.array([bundle["stack_weights"][task][name] for name in names])
        binary[:, j] = np.sum(np.stack([expert[name]["binary"][:, j] for name in names], axis=1) * weights[None, :], axis=1)
    acute_weights = np.array([bundle["stack_weights"]["Acute"][name] for name in names])
    acute = np.sum(np.stack([expert[name]["acute"] for name in names], axis=1) * acute_weights[None, :, None], axis=1)
    acute = acute / np.maximum(acute.sum(axis=1, keepdims=True), 1e-12)
    severity_weights = np.array([bundle["stack_weights"]["Severity"][name] for name in names])
    severity = np.sum(np.stack([expert[name]["severity"] for name in names], axis=1) * severity_weights[None, :, None], axis=1)
    severity = severity / np.maximum(severity.sum(axis=1, keepdims=True), 1e-12)
    results = []
    for i in range(len(snapshot_frame)):
        primary, detected, underweight, stunting, acute_index = _derive_primary_type_v4(binary[i], bundle["binary_thresholds"], acute[i])
        uncertain = bool(neural["variance"][i] > bundle["uncertainty_binary_variance_q95"])
        out_of_distribution = False
        latent_distance = None
        latent = neural["extras"].get("latent")
        if latent is not None and bundle["latent_mean"] is not None and bundle["latent_precision"] is not None and bundle["latent_q99"] is not None:
            difference = latent[i] - bundle["latent_mean"]
            latent_distance = float(difference @ bundle["latent_precision"] @ difference)
            out_of_distribution = bool(latent_distance > bundle["latent_q99"])
        if acute_index == 2:
            triage = "Priority clinical assessment — SAM risk"
        elif acute_index == 1:
            triage = "Priority clinical assessment — MAM risk"
        elif underweight or stunting:
            triage = "Priority clinical assessment"
        elif uncertain or out_of_distribution:
            triage = "Clinician review / closer monitoring"
        else:
            triage = "Routine monitoring"
        conformal = _aps_sets_local(acute[i : i + 1], bundle["acute_conformal_qhat"])[0]
        reliability = None
        if "reliability_gates" in neural["extras"]:
            reliability = {view: float(neural["extras"]["reliability_gates"][i, j]) for j, view in enumerate(ROLLING_VIEW_SPECS.keys())}
        results.append(
            {
                "predicted_malnutrition_type": primary,
                "detected_conditions": detected,
                "underweight_probability": float(binary[i, 0]),
                "stunting_probability": float(binary[i, 1]),
                "mam_probability": float(acute[i, 1]),
                "sam_probability": float(acute[i, 2]),
                "acute_probabilities": {
                    "Normal": float(acute[i, 0]),
                    "MAM": float(acute[i, 1]),
                    "SAM": float(acute[i, 2]),
                },
                "underweight_positive": underweight,
                "stunting_positive": stunting,
                "acute_status": ACUTE_NAMES[acute_index],
                "severity": SEVERITY_NAMES[int(np.argmax(severity[i]))],
                "severity_probabilities": {SEVERITY_NAMES[k]: float(severity[i, k]) for k in range(3)},
                "uncertainty_flag": uncertain,
                "ensemble_variance": float(neural["variance"][i]),
                "out_of_distribution_flag": out_of_distribution,
                "latent_distance": latent_distance,
                "latent": None if latent is None else [float(value) for value in latent[i]],
                "acute_conformal_prediction_set": [ACUTE_NAMES[k] for k in sorted(conformal)],
                "triage": triage,
                "model_version": bundle["model_version"],
                "prediction_horizon_months": bundle["horizon_months"],
                "modality_reliability": reliability,
            }
        )
    return results


def _finite(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _nested(payload: dict, key: str) -> dict:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


class GaRgcaV4Model:
    name = V4_MODEL_VERSION

    def __init__(self, directory: Path):
        import __main__
        import joblib

        __main__.MultimodalPreprocessor = MultimodalPreprocessor
        self.directory = directory
        missing = [name for name in REQUIRED_FILES if not (directory / name).is_file()]
        if missing:
            raise RuntimeError(f"GA-RGCA v4 artifacts missing: {missing}")
        self.metadata = json.loads((directory / "metadata_v4.json").read_text(encoding="utf-8"))
        self._require_metadata()
        self.prep = joblib.load(directory / "multimodal_preprocessor_v4.joblib")
        if not hasattr(self.prep, "transform") or not hasattr(self.prep, "view_specs"):
            raise RuntimeError("multimodal_preprocessor_v4.joblib is not the trained preprocessor")
        self.neural_calibrators = joblib.load(directory / "binary_calibrators_v4.joblib")
        if not isinstance(self.neural_calibrators, list) or len(self.neural_calibrators) != 2:
            raise RuntimeError("binary_calibrators_v4.joblib must contain two calibrators")
        states = torch.load(directory / "ga_rgca_v4_states.pt", map_location="cpu", weights_only=False)
        if not isinstance(states, list) or not states:
            raise RuntimeError("ga_rgca_v4_states.pt must contain a list of state dictionaries")
        self.models = []
        for index, state in enumerate(states):
            model = GrowthAnchoredRGCAV4(self.prep, self.prep.view_specs)
            incompatible = model.load_state_dict(state, strict=True)
            if incompatible.missing_keys or incompatible.unexpected_keys:
                raise RuntimeError(
                    f"Strict load failed for ensemble member {index}: "
                    f"missing={incompatible.missing_keys} unexpected={incompatible.unexpected_keys}"
                )
            model.eval()
            self.models.append(model)
        self.trees = joblib.load(directory / "rolling_tree_experts_v4.joblib")
        self.policy = joblib.load(directory / "superlearner_policy_v4.joblib")
        self._require_policy()
        thresholds = np.asarray(self.policy["binary_thresholds"], dtype=float)
        self.bundle = {
            "model_version": V4_MODEL_VERSION,
            "horizon_months": V4_HORIZON_MONTHS,
            "candidate_names": list(self.policy["candidate_names"]),
            "neural": {
                "models": self.models,
                "prep": self.prep,
                "binary_calibrators": self.neural_calibrators,
                "acute_temperature": float(self.metadata["acute_temperature_core"]),
                "severity_temperature": float(self.metadata["severity_temperature_core"]),
            },
            "trees": self.trees,
            "stack_weights": self.policy["stack_weights"],
            "binary_thresholds": thresholds,
            "uncertainty_binary_variance_q95": float(self.policy["uncertainty_binary_variance_q95"]),
            "latent_mean": self.policy["latent_mean"],
            "latent_precision": self.policy["latent_precision"],
            "latent_q99": self.policy["latent_q99"],
            "acute_conformal_qhat": float(self.policy["acute_conformal_qhat"]),
            "acute_conformal_alpha": float(self.policy["acute_conformal_alpha"]),
        }
        logger.info("GA-RGCA v4 Rolling SuperLearner loaded from %s (%s members)", directory, len(self.models))

    def _require_metadata(self) -> None:
        required = [
            "model_version",
            "acute_temperature_core",
            "severity_temperature_core",
            "uncertainty_binary_variance_q95",
            "binary_thresholds_final_superlearner",
            "superlearner_final_policy_weights",
        ]
        missing = [key for key in required if key not in self.metadata]
        if missing:
            raise RuntimeError(f"metadata_v4.json is missing {missing}")
        if self.metadata["model_version"] != V4_MODEL_VERSION:
            raise RuntimeError(f"Unexpected model version {self.metadata['model_version']}")

    def _require_policy(self) -> None:
        names = list(self.policy.get("candidate_names") or [])
        if names != list(EXPERT_NAMES):
            raise RuntimeError(f"SuperLearner experts are {names}, expected {list(EXPERT_NAMES)}")
        weights = self.policy.get("stack_weights") or {}
        for task in TASK_NAMES:
            task_weights = weights.get(task) or {}
            missing = [name for name in EXPERT_NAMES if name not in task_weights]
            if missing:
                raise RuntimeError(f"SuperLearner weights for {task} are missing {missing}")
        for key in ("binary_thresholds", "uncertainty_binary_variance_q95", "latent_mean", "latent_precision", "latent_q99", "acute_conformal_qhat", "acute_conformal_alpha"):
            if self.policy.get(key) is None:
                raise RuntimeError(f"superlearner_policy_v4.joblib is missing {key}")
        for name in EXPERT_NAMES[:-1]:
            bundle = self.trees.get(name)
            if not isinstance(bundle, dict):
                raise RuntimeError(f"Tree expert {name} is missing")
            for key in ("preprocessor", "binary_models", "acute_model", "severity_model", "binary_calibrators", "acute_temperature", "severity_temperature"):
                if key not in bundle:
                    raise RuntimeError(f"Tree expert {name} is missing {key}")

    def category_token(self, column: str, value):
        if value is None or value == "":
            return None
        text = str(value).strip()
        vocab = None
        for view, spec in ROLLING_VIEW_SPECS.items():
            if column in spec["cat"]:
                vocab = self.prep.cat_vocab[view][column]
                break
        if vocab is None:
            return None
        if text in vocab and text not in {"<UNK>", ""}:
            return text
        alias = CATEGORY_ALIASES.get(column, {}).get(text.lower())
        if alias and alias in vocab:
            return alias
        return None

    def snapshot_frame(self, payload: dict) -> tuple[pd.DataFrame, list[str], list[str]]:
        """Current visit becomes Baseline_*. Earlier-visit growth is not used."""
        anthro = _nested(payload, "anthropometric")
        socio = _nested(payload, "socioeconomic")
        context = _nested(payload, "ga_rgca_context")
        age = _finite(anthro.get("age_months"))
        height = _finite(anthro.get("height_cm"))
        weight = _finite(anthro.get("weight_kg"))
        sex = self.category_token("Sex", anthro.get("sex"))
        missing = []
        if age is None:
            missing.append("age_months")
        if height is None or height <= 0:
            missing.append("height_cm")
        if weight is None or weight <= 0:
            missing.append("weight_kg")
        if sex is None:
            missing.append("sex")
        if missing:
            raise IncompleteVisit(missing)
        birth_kg = _finite(anthro.get("birth_weight_kg"))
        bmi = weight / ((height / 100.0) ** 2)
        maternal_age = _finite(context.get("maternal_age_years"))
        family_size = _finite(socio.get("household_size"))
        education = self.category_token("Maternal_Education", context.get("maternal_education") or socio.get("maternal_education"))
        income = self.category_token("Household_Income_Range", context.get("household_income_range"))
        father = self.category_token("Father_Occupation", context.get("father_occupation"))
        mother = self.category_token("Mother_Occupation", context.get("mother_occupation") or socio.get("maternal_employment"))
        exclusive = self.category_token("Exclusive_Breastfeeding", context.get("exclusive_breastfeeding"))
        duration = self.category_token("Breastfeeding_Duration", context.get("breastfeeding_duration"))
        complementary = self.category_token("Complementary_Feeding_Timing", context.get("complementary_feeding_timing"))
        meals = self.category_token("Meal_Frequency_per_Day", context.get("meal_frequency"))
        diversity = self.category_token("Dietary_Diversity", context.get("dietary_diversity"))
        triposha = self.category_token("Triposha_Supplementation", context.get("triposha_supplementation"))
        vitamin = self.category_token("Vitamin_Supplementation", context.get("vitamin_supplementation"))
        row = {
            "Baseline_Age_months": age,
            "Baseline_Height_cm": height,
            "Baseline_Weight_kg": weight,
            "Baseline_BMI": bmi,
            "Birth_Weight_g": None if birth_kg is None else birth_kg * 1000.0,
            "Sex": sex,
            "Baseline_Age_Band": str(make_age_band(pd.Series([age])).iloc[0]),
            "Baseline_Maternal_Age_years": maternal_age,
            "Family_Size": family_size,
            "Maternal_Education": education,
            "Household_Income_Range": income,
            "Father_Occupation": father,
            "Mother_Occupation": mother,
            "Exclusive_Breastfeeding": exclusive,
            "Breastfeeding_Duration": duration,
            "Complementary_Feeding_Timing": complementary,
            "Meal_Frequency_per_Day": meals,
            "Dietary_Diversity": diversity,
            "Triposha_Supplementation": triposha,
            "Vitamin_Supplementation": vitamin,
            "Prediction_Horizon_months": V4_HORIZON_MONTHS,
        }
        unmapped = []
        for column, raw in (
            ("Maternal_Education", context.get("maternal_education") or socio.get("maternal_education")),
            ("Household_Income_Range", context.get("household_income_range")),
            ("Father_Occupation", context.get("father_occupation")),
            ("Mother_Occupation", context.get("mother_occupation") or socio.get("maternal_employment")),
            ("Exclusive_Breastfeeding", context.get("exclusive_breastfeeding")),
            ("Breastfeeding_Duration", context.get("breastfeeding_duration")),
            ("Complementary_Feeding_Timing", context.get("complementary_feeding_timing")),
            ("Meal_Frequency_per_Day", context.get("meal_frequency")),
            ("Dietary_Diversity", context.get("dietary_diversity")),
            ("Triposha_Supplementation", context.get("triposha_supplementation")),
            ("Vitamin_Supplementation", context.get("vitamin_supplementation")),
        ):
            if raw not in (None, "") and row[column] is None:
                unmapped.append(column)
        limitations = list(RESEARCH_LIMITATIONS)
        limitations.append("rolling_origin:current_visit")
        baseline = payload.get("historical_baseline")
        if isinstance(baseline, dict) and (_finite(baseline.get("height_cm")) is not None or _finite(baseline.get("weight_kg")) is not None):
            limitations.append("historical_baseline_growth_ignored_for_rolling_origin")
        for column, value in row.items():
            if column != "Prediction_Horizon_months" and value is None:
                limitations.append(f"{column}_not_recorded")
        frame = pd.DataFrame([row])
        leaked = set(frame.columns).intersection(FORBIDDEN_ROLLING_INPUTS)
        if leaked:
            raise RuntimeError(f"Forbidden target leakage in the rolling snapshot: {sorted(leaked)}")
        return frame, limitations, unmapped

    def predict_payload(self, payload: dict) -> dict:
        frame, limitations, unmapped = self.snapshot_frame(payload)
        result = predict_v4_deployment_bundle(self.bundle, frame)[0]
        result["input_snapshot"] = {column: _json_value(frame.iloc[0][column]) for column in frame.columns}
        result["missing_features"] = [column for column, value in result["input_snapshot"].items() if value is None]
        result["unmapped_categories"] = unmapped
        result["data_limitations"] = limitations
        result["binary_thresholds"] = {
            "Underweight": float(self.bundle["binary_thresholds"][0]),
            "Stunting": float(self.bundle["binary_thresholds"][1]),
        }
        result["uncertainty_threshold"] = float(self.bundle["uncertainty_binary_variance_q95"])
        result["acute_temperature"] = float(self.bundle["neural"]["acute_temperature"])
        result["severity_temperature"] = float(self.bundle["neural"]["severity_temperature"])
        result["prediction_source"] = V4_MODEL_VERSION
        result["binary_variance"] = result["ensemble_variance"]
        return result


def _json_value(value):
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    return str(value)


def load_ga_rgca_v4(directory: Path | None = None) -> tuple[GaRgcaV4Model | None, str | None]:
    path = directory or artifact_dir()
    if path is None:
        return None, "GA-RGCA v4 Rolling SuperLearner artifacts are not available"
    try:
        return GaRgcaV4Model(path), None
    except Exception as exc:
        logger.exception("GA-RGCA v4 failed to load")
        return None, f"GA-RGCA v4 artifacts were found but could not be loaded: {exc}"
