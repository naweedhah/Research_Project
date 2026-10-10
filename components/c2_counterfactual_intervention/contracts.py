"""Versioned model handoff metadata; no C1 model is supplied here."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictorCompatibilityError(ValueError):
    pass


class FeatureContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(min_length=1)
    source_field: str = Field(min_length=1)
    dtype: Literal["integer", "number", "boolean", "category"]
    unit: str | None = None
    categories: tuple[str, ...] = ()
    preprocessing: str = Field(min_length=1)
    missing_value_policy: str = Field(min_length=1)

    @model_validator(mode="after")
    def category_rules(self):
        if self.dtype == "category" and not self.categories:
            raise ValueError("categorical features require allowed categories")
        if self.dtype != "category" and self.categories:
            raise ValueError("noncategorical features cannot declare categories")
        return self


class TargetContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str = Field(min_length=1)
    definition: str = Field(min_length=1)


class PredictorContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    interface_version: Literal["c2-predictor-v1"] = "c2-predictor-v1"
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    mode: Literal["test", "real"]
    features: tuple[FeatureContract, ...] = Field(min_length=1)
    targets: tuple[TargetContract, ...] = Field(min_length=2)
    desired_category: str = Field(min_length=1)
    artifact_id: str | None = None
    artifact_sha256: str | None = None
    reference_data_id: str | None = None

    @model_validator(mode="after")
    def completeness(self):
        names = [feature.name for feature in self.features]
        sources = [feature.source_field for feature in self.features]
        codes = [target.code for target in self.targets]
        if len(names) != len(set(names)) or len(sources) != len(set(sources)):
            raise ValueError("feature names and source fields must be unique")
        if len(codes) != len(set(codes)) or self.desired_category not in codes:
            raise ValueError("target codes must be unique and include desired_category")
        if self.mode == "real" and (not self.artifact_id or not self.artifact_sha256):
            raise ValueError("real model contract requires artifact ID and SHA-256")
        if self.mode == "real" and (len(self.artifact_sha256) != 64 or
                                    any(char not in "0123456789abcdefABCDEF" for char in self.artifact_sha256)):
            raise ValueError("artifact SHA-256 must contain 64 hexadecimal characters")
        return self


SYNTHETIC_FEATURES = (
    FeatureContract(name="meals_per_day", source_field="meals_per_day", dtype="integer",
                    unit="synthetic count", preprocessing="identity", missing_value_policy="reject"),
    FeatureContract(name="dietary_diversity", source_field="dietary_diversity", dtype="integer",
                    unit="synthetic test score", preprocessing="identity", missing_value_policy="reject"),
)
SYNTHETIC_TARGETS = (
    TargetContract(code="higher_concern", definition="arbitrary test sum below 7"),
    TargetContract(code="lower_concern", definition="arbitrary test sum at least 7"),
)


def synthetic_contract(model_id: str) -> PredictorContract:
    return PredictorContract(model_id=model_id, model_version="1", mode="test",
                             features=SYNTHETIC_FEATURES, targets=SYNTHETIC_TARGETS,
                             desired_category="lower_concern", reference_data_id="synthetic-grid-v1")
