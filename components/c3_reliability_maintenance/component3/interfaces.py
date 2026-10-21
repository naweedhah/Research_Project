"""The C1 boundary: everything Component 3 assumes about the prediction model it maintains.

Component 1 does not exist in this repo yet. This module defines the contract a real
C1 artifact must satisfy to be managed by C3 — nothing downstream of this file may
assume anything about malnutrition-specific features, labels or thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Protocol, runtime_checkable

import numpy as np
import pandas as pd

FeatureKind = Literal["numeric", "categorical"]


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    kind: FeatureKind
    dtype: str = "float64"


@dataclass(frozen=True)
class FeatureSchema:
    """Describes the columns a model/monitor expects, independent of their meaning.

    Built from a plain list so the real C1 feature set can be dropped in later by
    changing configuration, not code.
    """

    features: tuple[FeatureSpec, ...]

    @staticmethod
    def from_dicts(specs: list[dict]) -> "FeatureSchema":
        return FeatureSchema(tuple(FeatureSpec(**s) for s in specs))

    @property
    def numeric_columns(self) -> list[str]:
        return [f.name for f in self.features if f.kind == "numeric"]

    @property
    def categorical_columns(self) -> list[str]:
        return [f.name for f in self.features if f.kind == "categorical"]

    @property
    def columns(self) -> list[str]:
        return [f.name for f in self.features]

    @staticmethod
    def infer_from_dataframe(df: pd.DataFrame) -> "FeatureSchema":
        """Best-effort schema inference for generic/test data, not for production use."""
        specs = []
        for col in df.columns:
            kind: FeatureKind = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else "categorical"
            specs.append(FeatureSpec(name=col, kind=kind, dtype=str(df[col].dtype)))
        return FeatureSchema(tuple(specs))


@dataclass(frozen=True)
class ModelMetadata:
    version: str
    trained_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    classes: tuple = ()
    parent_version: str | None = None
    action: str = "initial"
    schema: FeatureSchema | None = None
    # Binary models only: P(positive) at or above this value is predicted positive. Clinical models are run at a
    # chosen operating point (e.g. >= 80% sensitivity), not at argmax, which would miss most rare positives.
    decision_threshold: float | None = None


@runtime_checkable
class ModelArtifact(Protocol):
    """Contract a C1 model (or any candidate C3 produces) must satisfy."""

    version: str
    metadata: ModelMetadata

    def predict(self, X: pd.DataFrame) -> np.ndarray: ...

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray: ...
