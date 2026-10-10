"""Public request and response contract for the synthetic C2 baseline."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator
from .food_resources import FoodPlanningContext


Category = Literal["higher_concern", "lower_concern"]
Feature = Literal["meals_per_day", "dietary_diversity"]
Method = Literal["bounded_search", "dice", "face_graph"]
Mode = Literal["test", "real"]


class ChildFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_months: StrictInt = Field(ge=0, le=59)
    sex: Literal["female", "male"]
    birth_weight_kg: float | None = Field(default=None, gt=0)
    historical_exclusive_breastfeeding: bool | None = None
    household_income_band: Literal["low", "middle", "high", "unknown"]
    meals_per_day: StrictInt = Field(ge=1, le=5)
    dietary_diversity: StrictInt = Field(ge=0, le=5)
    supplement_use: StrictBool | None = None


class FeasibilityContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_units: int | None = Field(default=None, ge=0)
    supplement_access: StrictBool | None = None
    supplement_programme_eligible: StrictBool | None = None
    supplement_clinically_suitable: StrictBool | None = None
    available: dict[Feature, bool | None] = Field(default_factory=dict)
    practical: dict[Feature, bool | None] = Field(default_factory=dict)
    age_suitable: dict[Feature, bool | None] = Field(default_factory=dict)
    eligible: dict[Feature, bool | None] = Field(default_factory=dict)
    clinically_suitable: dict[Feature, bool | None] = Field(default_factory=dict)
    transition_justified: dict[Feature, bool | None] = Field(default_factory=dict)


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    child_id: str = Field(min_length=1, max_length=100)
    mode: Mode
    child: ChildFeatures
    context: FeasibilityContext
    max_changes: Literal[1, 2] = 2
    max_cards: int = Field(default=5, ge=1, le=20)
    predictor: str | None = None
    predictor_version: str | None = None
    method: Method = "bounded_search"
    food_planning: FoodPlanningContext | None = None

    @model_validator(mode="after")
    def compatible_predictor(self):
        test_ids = {"synthetic_test_v1", "synthetic_sklearn_grid_v1"}
        if self.mode == "test":
            if self.predictor is not None and self.predictor not in test_ids:
                raise ValueError("test mode accepts only registered synthetic predictors")
            if self.predictor_version not in (None, "1"):
                raise ValueError("synthetic predictor version must be 1")
            if self.method == "dice" and self.predictor == "synthetic_test_v1":
                raise ValueError("DiCE requires the synthetic sklearn adapter")
        elif not self.predictor or not self.predictor_version:
            raise ValueError("real mode requires predictor ID and version")
        elif self.predictor in test_ids:
            raise ValueError("synthetic predictor cannot be selected in real mode")
        return self


class Change(BaseModel):
    feature: str
    from_value: int | bool
    to_value: int | bool


class CandidateInfo(BaseModel):
    changes: list[Change]
    status: Literal["rejected", "unresolved"]
    reasons: list[str]
    alternative_id: str | None = None


class InterventionCard(BaseModel):
    rank: int
    changes: list[Change]
    explanation: str
    feasibility_status: Literal["feasible"] = "feasible"
    feasibility_reasons: list[str]
    professional_review_required: bool = True
    title: str | None = None
    reason: str | None = None
    food_options: list[str] | None = None
    required_resources: list[str] | None = None
    incremental_cost_lkr: str | None = None
    cost_period: str | None = None
    affordability: str | None = None
    availability: str | None = None
    alternative_id: str | None = None


class RecommendationResponse(BaseModel):
    child_id: str
    condition_category: str
    cards: list[InterventionCard]
    rejected_or_unresolved: list[CandidateInfo]
    message: str
    provenance: str = "synthetic_test_v1: deterministic test-only predictor; no clinical validation"
    professional_review_required: bool = True
    method: Method = "bounded_search"
    mode: Mode
    professional_referral_recommended: bool = False
    referral_message: str | None = None
