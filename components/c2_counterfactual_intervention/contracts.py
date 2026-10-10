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


class LabelTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    from_label: str = Field(min_length=1)
    to_label: str = Field(min_length=1)


class ModelPrediction(BaseModel):
    """Internal C1 output; optional probabilities are never included in cards."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    type_label: str = Field(min_length=1)
    severity_label: str | None = None
    type_probabilities: dict[str, float] | None = None
    severity_probabilities: dict[str, float] | None = None

    @model_validator(mode="after")
    def probability_bounds(self):
        for probabilities in (self.type_probabilities, self.severity_probabilities):
            if probabilities is not None and any(not 0 <= value <= 1 for value in probabilities.values()):
                raise ValueError("probabilities must be between zero and one")
        return self


class PredictorContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    interface_version: Literal["c2-predictor-v1", "c2-predictor-v2"] = "c2-predictor-v1"
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    mode: Literal["test", "real"]
    features: tuple[FeatureContract, ...] = Field(min_length=1)
    targets: tuple[TargetContract, ...] = ()
    desired_category: str | None = None
    output_mode: Literal["category", "type_severity"] = "category"
    type_targets: tuple[TargetContract, ...] = ()
    severity_targets: tuple[TargetContract, ...] = ()
    accepted_type_transitions: tuple[LabelTransition, ...] = ()
    severity_order: tuple[str, ...] = ()  # least to most severe, supplied by C1 review
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
        if self.output_mode == "category":
            if len(codes) < 2 or len(codes) != len(set(codes)) or self.desired_category not in codes:
                raise ValueError("target codes must be unique and include desired_category")
            if self.interface_version != "c2-predictor-v1":
                raise ValueError("category mode requires the v1 interface")
        else:
            types = [target.code for target in self.type_targets]
            severities = [target.code for target in self.severity_targets]
            if self.interface_version != "c2-predictor-v2" or self.targets or self.desired_category:
                raise ValueError("two-output mode requires the v2 interface without category targets")
            if len(types) < 2 or len(types) != len(set(types)):
                raise ValueError("two-output mode requires unique type labels")
            if len(severities) < 2 or len(severities) != len(set(severities)):
                raise ValueError("two-output mode requires unique severity labels")
            if set(self.severity_order) != set(severities) or len(self.severity_order) != len(severities):
                raise ValueError("severity order must contain every declared severity exactly once")
            pairs = [(item.from_label, item.to_label) for item in self.accepted_type_transitions]
            if len(pairs) != len(set(pairs)) or any(a not in types or b not in types or a == b for a, b in pairs):
                raise ValueError("type transitions must be unique, declared, and non-identity")
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
