"""Adapter for Component 1's final model (GA-RGCA v3, by Chanodya) so C3 can monitor and maintain it.

The deployment bundle exported by C1's notebook holds:
  multimodal_preprocessor.joblib  scaling statistics and category vocabularies (plain data)
  ga_rgca_v3_states.pt            weights of the 3-network ensemble
  binary_calibrators.joblib       Platt calibrators (logistic regression) for the Underweight and Stunting outputs
  metadata.json                   features, thresholds, network sizes
The network and preprocessing code below are copied from C1's notebook (cells 15 and 17) so that the bundle can be
loaded without running the notebook. Pickles are read with restricted unpicklers (only the expected classes), and the
weights with PyTorch's weights-only loader, so loading the bundle cannot run code from the files.

C3 passes data with its own column names (component3.data); `to_c1_frame` maps them to C1's names. WHO statuses
(underweight/stunting Moderate/Severe, MAM/SAM) are derived from the 2025 z-scores, so stress scenarios that change
measurements change them consistently. Requires PyTorch (`pip install torch`).
"""

from __future__ import annotations

import json
import math
import os
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from joblib.numpy_pickle import NumpyUnpickler
from scipy.special import expit

from component3.interfaces import ModelMetadata

TARGET_INDEX = {"underweight": 0, "stunting": 1}
FATHER_OCCUPATION = {"Working abroad": "Abroad", "Unemployed": "No job"}


def model_dir() -> Path:
    return Path(os.environ.get("C1_MODEL_DIR", Path(__file__).resolve().parents[2] / "external_models" / "ga_rgca_v3"))


# ---------------------------------------------------------------- safe loading
class _SavedPreprocessor:
    """Receives the attributes of C1's MultimodalPreprocessor; `transform` is C1's code (notebook cell 15)."""

    def transform(self, frame: pd.DataFrame) -> dict:
        output = {}
        for view, spec in self.view_specs.items():
            n = len(frame)
            num = np.zeros((n, len(spec["num"])), dtype=np.float32)
            num_missing = np.zeros_like(num, dtype=np.float32)
            cat = np.zeros((n, len(spec["cat"])), dtype=np.int64)
            observed_count = np.zeros(n, dtype=np.float32)
            valid_count = np.zeros(n, dtype=np.float32)
            total_fields = max(1, len(spec["num"]) + len(spec["cat"]))
            for j, c in enumerate(spec["num"]):
                s = pd.to_numeric(frame[c], errors="coerce")
                observed = s.notna().to_numpy()
                num_missing[:, j] = (~observed).astype(np.float32)
                observed_count += observed.astype(np.float32)
                stats = self.num_stats[view][c]
                vals = s.fillna(stats["median"]).to_numpy(dtype=np.float32)
                num[:, j] = (vals - stats["mean"]) / stats["std"]
                if c in self.valid_ranges:
                    lo, hi = self.valid_ranges[c]
                    valid = observed & s.between(lo, hi, inclusive="both").to_numpy()
                else:
                    valid = observed
                valid_count += valid.astype(np.float32)
            for j, c in enumerate(spec["cat"]):
                s = frame[c].astype("string").fillna("Unknown").str.strip()
                observed = (~s.isin(["", "Unknown", "<NA>"])).to_numpy()
                observed_count += observed.astype(np.float32)
                valid_count += observed.astype(np.float32)
                vocab = self.cat_vocab[view][c]
                cat[:, j] = np.array([vocab.get(str(v), 0) for v in s], dtype=np.int64)
            availability = (observed_count > 0).astype(np.float32)
            completeness = np.clip(observed_count / total_fields, 0, 1)
            validity = np.divide(valid_count, np.maximum(observed_count, 1), out=np.zeros_like(valid_count),
                                 where=np.maximum(observed_count, 1) > 0).astype(np.float32)
            output[view] = {"num": num, "num_missing": num_missing, "cat": cat,
                            "quality": np.stack([availability, completeness, validity], axis=1).astype(np.float32)}
        return output


class _PreprocessorUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) == ("__main__", "MultimodalPreprocessor"):
            return _SavedPreprocessor
        raise pickle.UnpicklingError(f"unexpected object in preprocessor file: {module}.{name}")


class _CalibratorUnpickler(NumpyUnpickler):
    ALLOWED = {("sklearn.linear_model._logistic", "LogisticRegression"), ("joblib.numpy_pickle", "NumpyArrayWrapper"),
               ("numpy", "ndarray"), ("numpy", "dtype")}

    def find_class(self, module, name):
        if (module, name) in self.ALLOWED or (module.startswith("numpy") and name in ("_reconstruct", "scalar")):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"unexpected object in calibrator file: {module}.{name}")


def _load_preprocessor(path: Path) -> _SavedPreprocessor:
    with open(path, "rb") as f:
        return _PreprocessorUnpickler(f).load()


def _load_calibrators(path: Path) -> list[tuple[float, float] | None]:
    """Platt calibrators reduced to (slope, intercept), so scikit-learn versions do not matter afterwards."""
    with open(path, "rb") as f, warnings.catch_warnings():
        warnings.simplefilter("ignore")  # saved with an older scikit-learn; only coef_/intercept_ are read
        calibrators = _CalibratorUnpickler(str(path), f, ensure_native_byte_order=True).load()
    return [None if c is None else (float(c.coef_[0, 0]), float(c.intercept_[0])) for c in calibrators]


# ---------------------------------------------------------------- network (C1 notebook cell 17)
def _embedding_dim(cardinality: int) -> int:
    return int(min(24, max(4, round(4 * (cardinality ** 0.25)))))


class _ViewEncoder(nn.Module):
    def __init__(self, num_dim, cat_cardinalities, d_model, hidden, dropout):
        super().__init__()
        self.embeddings = nn.ModuleList([nn.Embedding(card, _embedding_dim(card)) for card in cat_cardinalities])
        input_dim = 2 * num_dim + sum(e.embedding_dim for e in self.embeddings) or 1
        self.net = nn.Sequential(nn.Linear(input_dim, hidden), nn.GELU(), nn.Dropout(dropout),
                                 nn.Linear(hidden, d_model), nn.LayerNorm(d_model), nn.GELU())

    def forward(self, num, num_missing, cat):
        parts = [num, num_missing] if num.shape[1] > 0 else []
        parts += [emb(cat[:, j]) for j, emb in enumerate(self.embeddings)]
        x = torch.cat(parts, dim=1) if parts else torch.ones((num.shape[0], 1), device=num.device)
        return self.net(x)


class _OrdinalSeverityHead(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        self.fc = nn.Linear(in_dim, 2)

    def forward(self, x):
        raw = self.fc(x)
        p_ge_moderate = torch.sigmoid(raw[:, 0])
        p_severe = p_ge_moderate * torch.sigmoid(raw[:, 1])
        return torch.stack([1.0 - p_ge_moderate, p_ge_moderate - p_severe, p_severe], dim=1)


class _GrowthAnchoredRGCA(nn.Module):
    """Inference-only copy of C1's GrowthAnchoredRGCA (no modality dropout: that only applies in training)."""

    def __init__(self, prep, view_specs, d_model, hidden, dropout):
        super().__init__()
        self.view_names = list(view_specs.keys())
        self.context_names = [v for v in self.view_names if v != "history"]
        self.d_model = d_model
        self.encoders = nn.ModuleDict({v: _ViewEncoder(prep.num_dims[v], prep.cardinalities[v], d_model, hidden,
                                                       dropout) for v in self.view_names})
        self.gate_mlps = nn.ModuleDict({v: nn.Sequential(nn.Linear(3, 16), nn.GELU(), nn.Linear(16, 1))
                                        for v in self.view_names})
        self.k_proj = nn.ModuleDict({v: nn.Linear(d_model, d_model) for v in self.context_names})
        self.v_proj = nn.ModuleDict({v: nn.Linear(d_model, d_model) for v in self.context_names})
        self.null_key = nn.Parameter(torch.zeros(1, d_model))
        self.null_value = nn.Parameter(torch.zeros(1, d_model))
        self.task_tokens = nn.Parameter(torch.zeros(4, d_model))
        self.task_q = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(4)])
        self.context_out = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(4)])
        self.task_norm = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(4)])
        self.task_tower = nn.ModuleList([nn.Sequential(nn.Linear(d_model, hidden), nn.GELU(), nn.Dropout(dropout),
                                                       nn.Linear(hidden, d_model), nn.GELU()) for _ in range(4)])
        self.binary_heads = nn.ModuleList([nn.Linear(d_model, 1) for _ in range(2)])
        self.acute_head = nn.Linear(d_model, 3)
        self.severity_head = _OrdinalSeverityHead(d_model)

    def forward(self, views):
        h, gates = {}, {}
        for v in self.view_names:
            x = views[v]
            h[v] = self.encoders[v](x["num"], x["num_missing"], x["cat"])
            q = x["quality"]
            direct = q[:, 0:1] * torch.sqrt(torch.clamp(q[:, 1:2] * q[:, 2:3], 0, 1) + 1e-8)
            gates[v] = 0.80 * direct + 0.20 * torch.sigmoid(self.gate_mlps[v](q))
        anchor = h["history"] * gates["history"]
        n = len(anchor)
        K = torch.stack([self.k_proj[v](h[v]) * gates[v] for v in self.context_names]
                        + [self.null_key.expand(n, -1)], dim=1)
        V = torch.stack([self.v_proj[v](h[v]) * gates[v] for v in self.context_names]
                        + [self.null_value.expand(n, -1)], dim=1)
        reps = []
        for t in range(4):
            q = self.task_q[t](anchor + self.task_tokens[t].unsqueeze(0))
            attn = torch.softmax((q.unsqueeze(1) * K).sum(dim=-1) / math.sqrt(self.d_model), dim=1)
            rep = self.task_norm[t](anchor + self.context_out[t]((attn.unsqueeze(-1) * V).sum(dim=1)))
            reps.append(rep + self.task_tower[t](rep))
        binary_logits = torch.cat([self.binary_heads[j](reps[j]) for j in range(2)], dim=1)
        return binary_logits, torch.softmax(self.acute_head(reps[2]), dim=1), self.severity_head(reps[3])


# ---------------------------------------------------------------- column mapping
def _who_status(z: pd.Series) -> pd.Series:
    return pd.Series(np.where(z.isna(), None, np.where(z < -3, "Severe", np.where(z < -2, "Moderate", "Normal"))),
                     index=z.index, dtype=object)


def _age_band(age: pd.Series) -> pd.Series:
    return pd.cut(age, bins=[-0.01, 5, 11, 23, 35, 47, 60],
                  labels=["0-5", "6-11", "12-23", "24-35", "36-47", "48-60"], include_lowest=True).astype(object)


def to_c1_frame(X: pd.DataFrame) -> pd.DataFrame:
    """C3 / cleaned-dataset column names (2025 inputs) -> the names C1's model was trained with."""
    num = lambda c: pd.to_numeric(X[c], errors="coerce") if c in X else pd.Series(np.nan, index=X.index)
    col = lambda c: X[c] if c in X else pd.Series(np.nan, index=X.index, dtype=object)
    age, height, weight, whz = num("Age_months_2025"), num("Height_cm_2025"), num("Weight_kg_2025"), num("WHZ_2025")
    out = pd.DataFrame(index=X.index)
    out["Hist_2025_Age_months"] = age
    out["Hist_2025_Height_cm"] = height
    out["Hist_2025_Weight_kg"] = weight
    out["Hist_2025_BMI"] = weight / (height / 100) ** 2
    out["Birth_Weight_g"] = num("Birth_Weight_g")
    out["Hist_2025_MAM"] = np.where(whz.isna(), np.nan, ((whz >= -3) & (whz < -2)).astype(float))
    out["Hist_2025_SAM"] = np.where(whz.isna(), np.nan, (whz < -3).astype(float))
    out["Sex"] = col("Sex")
    out["Hist_Age_Band"] = _age_band(age)
    out["Hist_2025_Underweight"] = _who_status(num("WAZ_2025"))
    out["Hist_2025_Stunting"] = _who_status(num("HAZ_2025"))
    out["Maternal_Age_2025_years"] = num("Maternal_Age_years_2025")
    out["Family_Size"] = num("Family_Size_2025")
    out["Maternal_Education"] = col("Maternal_Education")
    out["Household_Income_Range"] = col("Household_Income_Range_2025")  # not a stand-in input; "Unknown" if absent
    out["Father_Occupation"] = col("Father_Occupation").replace(FATHER_OCCUPATION)
    out["Mother_Occupation"] = col("Mother_Occupation")
    for c1_name, name in [("Exclusive_Breastfeeding", "Exclusive_Breastfeeding"),
                          ("Breastfeeding_Duration", "Breastfeeding_Duration_2025"),
                          ("Complementary_Feeding_Timing", "Complementary_Feeding_Timing_2025"),
                          ("Meal_Frequency_per_Day", "Meal_Frequency_per_Day_2025"),
                          ("Dietary_Diversity", "Dietary_Diversity_2025"),
                          ("Triposha_Supplementation", "Triposha_Supplementation_2025"),
                          ("Vitamin_Supplementation", "Vitamin_Supplementation_2025")]:
        out[c1_name] = col(name)
    return out


# ---------------------------------------------------------------- the model C3 manages
class C1GaRgcaModel:
    """C1's GA-RGCA v3 as a C3 ModelArtifact for one binary output (underweight or stunting)."""

    def __init__(self, directory: Path | None = None, target: str = "underweight", version: str | None = None):
        directory = Path(directory or model_dir())
        meta = json.loads((directory / "metadata.json").read_text())
        cfg = meta["model_config"]
        self.prep = _load_preprocessor(directory / "multimodal_preprocessor.joblib")
        self.calibrators = _load_calibrators(directory / "binary_calibrators.joblib")
        states = torch.load(directory / "ga_rgca_v3_states.pt", map_location="cpu", weights_only=True)
        self.networks = []
        for state in states:
            net = _GrowthAnchoredRGCA(self.prep, self.prep.view_specs, cfg["D_MODEL"], cfg["HIDDEN"], cfg["DROPOUT"])
            net.load_state_dict(state, strict=True)
            self.networks.append(net.eval())
        self.bundle_metadata = meta
        self.target, self.index = target, TARGET_INDEX[target]
        self.name = f"C1 {meta['model_version']}"  # C1's own name; C3 numbers versions v<major>.<minor>
        self.version = version or "v1.0"
        threshold = float(meta["binary_thresholds"][meta["binary_outputs"][self.index]])
        self.metadata = ModelMetadata(version=self.version, classes=(0, 1), action="initial",
                                      decision_threshold=threshold)

    @torch.no_grad()
    def predict_heads(self, X: pd.DataFrame) -> dict:
        """All of C1's outputs: calibrated underweight/stunting probabilities, acute and severity probabilities."""
        views = self.prep.transform(to_c1_frame(X))
        tensors = {v: {k: torch.from_numpy(a) for k, a in d.items()} for v, d in views.items()}
        logits, acute, severity = zip(*[net(tensors) for net in self.networks])
        b_logits = torch.stack(logits).mean(0).numpy()
        binary = np.column_stack([expit(b_logits[:, j]) if cal is None else expit(cal[0] * b_logits[:, j] + cal[1])
                                  for j, cal in enumerate(self.calibrators)])
        acute_t, sev_t = self.bundle_metadata["acute_temperature"], self.bundle_metadata["severity_temperature"]
        temper = lambda p, t: (lambda z: z / z.sum(1, keepdims=True))(np.exp(np.log(np.clip(p, 1e-8, 1)) / t))
        return {"underweight": binary[:, 0], "stunting": binary[:, 1],
                "acute": temper(torch.stack(acute).mean(0).numpy(), acute_t),
                "severity": temper(torch.stack(severity).mean(0).numpy(), sev_t),
                "ensemble_variance": torch.sigmoid(torch.stack(logits)).var(0, unbiased=False).mean(1).numpy()}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = self.predict_heads(X)[self.target]
        return np.column_stack([1 - p, p])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= self.metadata.decision_threshold).astype(int)
