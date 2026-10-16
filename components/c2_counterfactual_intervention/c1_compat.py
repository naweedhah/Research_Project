"""Versioned C1 wire contract. Categories are ordinal labels, never measured scores."""
from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MEALS = ("2 meals/day", "3 meals/day", "4+ meals/day")
DIVERSITY = ("Less than 2 varieties", "2 to 5 varieties", "More than 5 varieties")
FEATURES = {"meal_frequency": MEALS, "dietary_diversity": DIVERSITY}


class C1Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["c2-c1-snapshot-v1"] = "c2-c1-snapshot-v1"
    child_pseudonymous_id: str = Field(min_length=1)
    visit_number: int = Field(ge=0)
    visit_date: str | None = None
    anthropometric: dict[str, Any] = Field(default_factory=dict)
    socioeconomic: dict[str, Any] = Field(default_factory=dict)
    dietary: dict[str, Any] = Field(default_factory=dict)
    maternal_child_health: dict[str, Any] = Field(default_factory=dict)
    historical_baseline: dict[str, Any]
    ga_rgca_context: dict[str, Any]
    model_version: str = "GA-RGCA-v3"
    feature_schema_version: str = "ga-rgca-v3-current-visit-baseline"
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_feeding_and_history(self):
        baseline = self.historical_baseline
        if baseline.get("height_cm") is None or baseline.get("weight_kg") is None:
            raise ValueError("verified historical height and weight are required")
        age = baseline.get("age_months")
        if age is None or isinstance(age, bool) or not isinstance(age, (int, float)) or not 0 <= age <= 59:
            raise ValueError("historical age must be within the 0-59 month cohort")
        for feature, categories in FEATURES.items():
            if self.ga_rgca_context.get(feature) not in categories:
                raise ValueError(f"{feature} must be an exact C1 category")
        return self

    def predict_payload(self, changes: dict[str, str] | None = None) -> dict[str, Any]:
        """Only the two feeding strings may differ between hypothetical calls."""
        payload = deepcopy(self.model_dump(exclude={"contract_version", "model_version", "feature_schema_version", "provenance"}))
        for feature, value in (changes or {}).items():
            if feature not in FEATURES or value not in FEATURES[feature]:
                raise ValueError("unsupported feeding change")
            payload["ga_rgca_context"][feature] = value
        payload["allow_demo"] = False
        return payload


class C1Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["c2-c1-output-v3"] = "c2-c1-output-v3"
    underweight_probability: float = Field(ge=0, le=1)
    stunting_probability: float = Field(ge=0, le=1)
    acute_probabilities: dict[Literal["Normal", "MAM", "SAM"], float]
    predicted_malnutrition_type: Literal["Normal", "Underweight", "Stunting", "MAM", "SAM"]
    acute_status: Literal["Normal", "MAM", "SAM"]
    severity: Literal["Normal", "Moderate", "Severe"]
    severity_probabilities: dict[Literal["normal", "moderate", "severe"], float]
    uncertainty_flag: bool
    model_version: str
    calibration_version: str
    feature_schema_version: str
    prediction_source: str
    prediction_task: Literal["twelve_month_nutritional_risk"]
    score_kind: str
    score_is_probability: bool
    score_is_calibrated: bool
    clinical_use: bool
    data_limitations: list[str]
    mode: str
    input_snapshot: dict[str, Any] | None = None

    @model_validator(mode="after")
    def complete_distributions(self):
        if set(self.acute_probabilities) != {"Normal", "MAM", "SAM"} or set(self.severity_probabilities) != {"normal", "moderate", "severe"}:
            raise ValueError("incomplete acute or severity distribution")
        if any(not 0 <= p <= 1 for p in (*self.acute_probabilities.values(), *self.severity_probabilities.values())):
            raise ValueError("probability outside [0,1]")
        if abs(sum(self.acute_probabilities.values()) - 1) > .02 or abs(sum(self.severity_probabilities.values()) - 1) > .02:
            raise ValueError("probability distribution does not sum to one")
        if self.clinical_use or not self.score_kind:
            raise ValueError("unsupported score semantics")
        return self


def next_categories(snapshot: C1Snapshot) -> list[dict[str, str]]:
    if snapshot.historical_baseline["age_months"] < 6:
        return []
    options = []
    for feature, labels in FEATURES.items():
        current = snapshot.ga_rgca_context[feature]
        index = labels.index(current)
        if index + 1 < len(labels):
            options.append({feature: labels[index + 1]})
    if len(options) == 2:
        options.append({**options[0], **options[1]})
    return options
