"""Supplied food evidence and practice proposals; no built-in clinical or price data."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


Unit = Literal["g", "kg", "ml", "l", "piece", "serving"]
Period = Literal["day", "week", "month"]
EvidenceKind = Literal["synthetic_test", "verified_source", "authorized_input"]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: EvidenceKind
    source: str = Field(min_length=1)
    observed_on: date


class Price(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_lkr: Decimal = Field(ge=0)
    quantity: Decimal = Field(gt=0)
    unit: Unit
    evidence: Evidence


class FoodResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    food_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    food_group: str = Field(min_length=1)
    price: Price | None = None
    locally_available: StrictBool | None = None
    availability_evidence: Evidence | None = None


class FoodQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    food_id: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit: Unit
    serving_assumption: str = Field(min_length=1)


class FoodBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_lkr: Decimal | None = Field(default=None, ge=0)
    period: Period
    evidence: Evidence | None = None


class PracticeChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: Literal["meals_per_day", "dietary_diversity"]
    from_value: int
    to_value: int


class FoodAlternative(BaseModel):
    """Externally supplied, reviewed proposal matching an exact model-tested change."""
    model_config = ConfigDict(extra="forbid")
    alternative_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    changes: list[PracticeChange] = Field(min_length=1, max_length=2)
    foods: list[FoodQuantity] = Field(min_length=1)
    period: Period
    practice_evidence: Evidence | None = None
    practice_reviewed: StrictBool | None = None
    suitability_evidence: Evidence | None = None
    age_suitable: StrictBool | None = None
    clinically_suitable: StrictBool | None = None
    programme_eligible: StrictBool | None = None
    programme_required: StrictBool = False
    caregiver_practical: StrictBool | None = None

    @model_validator(mode="after")
    def unique_changes(self):
        if len({change.feature for change in self.changes}) != len(self.changes):
            raise ValueError("duplicate practice feature")
        return self


class ReferralPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trigger_categories: list[str] = Field(min_length=1)
    evidence: Evidence
    message: str = Field(min_length=1)


class FoodPlanningContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog: list[FoodResource]
    budget: FoodBudget
    alternatives: list[FoodAlternative]
    referral_policy: ReferralPolicy | None = None

    @model_validator(mode="after")
    def unique_ids(self):
        if len({food.food_id for food in self.catalog}) != len(self.catalog):
            raise ValueError("duplicate food ID")
        if len({alternative.alternative_id for alternative in self.alternatives}) != len(self.alternatives):
            raise ValueError("duplicate alternative ID")
        return self
