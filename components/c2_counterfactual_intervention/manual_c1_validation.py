"""Manual invented-input comparison against genuine C1 inference.

This local research workflow does not issue or authorize intervention cards.
Only feeding categories differ between a baseline and its hypothetical calls.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .c1_compat import C1Snapshot, next_categories
from .c1_predictors import C1PredictionUnavailable, RealC1HttpPredictor
from .real_model_validation import _prediction, _standalone_policy_reasons, validation_snapshot


class ManualC1Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: str = Field(pattern=r"^TEST-[0-9]{4}$")
    age_months: int = Field(ge=6, le=59)
    sex: Literal["Female", "Male"]
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    birth_weight_kg: float = Field(gt=0)
    household_size: int = Field(gt=0)
    maternal_age_years: int = Field(gt=0)
    maternal_education: Literal["No formal education", "Below O/ Level", "O/L passed", "A/ Level passes", "Degree/ diploma"]
    household_income_range: Literal["Less than Rs. 20,000", "Rs.20,000 to Rs. 50,000", "Rs. 50,000 to Rs. 100,000", "More than Rs. 100,000"]
    father_occupation: Literal["Abroad", "Government worker", "Manual worker", "No job", "Private sector worker", "Self-employed"]
    mother_occupation: Literal["Government worker", "Housewife", "Private sector worker", "Self-employed"]
    exclusive_breastfeeding: Literal["Yes", "No"]
    breastfeeding_duration: Literal["Less than 6 months", "More than 6 months"]
    complementary_feeding_timing: Literal["Before 6 months", "After 6 months"]
    meal_frequency: Literal["2 meals/day", "3 meals/day", "4+ meals/day"]
    dietary_diversity: Literal["Less than 2 varieties", "2 to 5 varieties", "More than 5 varieties"]
    triposha_supplementation: Literal["No", "Yes - irregular use", "Yes - regular use"]
    vitamin_supplementation: Literal["Yes", "No"]
    historical_mam: bool | None = None
    historical_sam: bool | None = None
    historical_underweight: Literal["Normal", "Moderate", "Severe"] | None = None
    historical_stunting: Literal["Normal", "Moderate", "Severe"] | None = None
    budget_lkr: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_period: Literal["daily", "weekly", "monthly"] = "weekly"

    @model_validator(mode="after")
    def coherent_history(self):
        if self.historical_mam is True and self.historical_sam is True:
            raise ValueError("historical MAM and SAM flags cannot both be true")
        return self


def manual_snapshot(request: ManualC1Request) -> C1Snapshot:
    """Build an explicit C1 snapshot from the user's invented test values."""
    data = validation_snapshot().model_dump()
    data["child_pseudonymous_id"] = request.test_id
    data["anthropometric"].update(age_months=request.age_months, sex=request.sex,
                                  height_cm=request.height_cm, weight_kg=request.weight_kg,
                                  birth_weight_kg=request.birth_weight_kg)
    data["historical_baseline"].update(age_months=request.age_months, sex=request.sex,
                                       height_cm=request.height_cm, weight_kg=request.weight_kg,
                                       birth_weight_kg=request.birth_weight_kg)
    data["historical_baseline"].update(
        mam=request.historical_mam, sam=request.historical_sam,
        underweight=request.historical_underweight,
        stunting=request.historical_stunting,
    )
    data["socioeconomic"]["household_size"] = request.household_size
    data["ga_rgca_context"].update({
        name: getattr(request, name) for name in (
            "maternal_age_years", "maternal_education", "household_income_range",
            "father_occupation", "mother_occupation", "exclusive_breastfeeding",
            "breastfeeding_duration", "complementary_feeding_timing", "meal_frequency",
            "dietary_diversity", "triposha_supplementation", "vitamin_supplementation")
    })
    data["provenance"] = "manually entered invented C2 research input; not an observed child record"
    return C1Snapshot.model_validate(data)


def run_manual_c1(request: ManualC1Request, predictor: RealC1HttpPredictor | None = None) -> dict:
    snapshot = manual_snapshot(request)
    predictor = predictor or RealC1HttpPredictor(timeout=10.0)
    if getattr(predictor, "source", None) != "GA-RGCA-v3":
        raise C1PredictionUnavailable("genuine C1 predictor required")
    original_payload = snapshot.predict_payload()
    if original_payload["allow_demo"] is not False:
        raise ValueError("C1 demo fallback must be disabled")
    baseline = predictor.predict(snapshot)
    baseline_display = _prediction(baseline)
    candidates = []
    for changes in next_categories(snapshot):
        candidate_payload = snapshot.predict_payload(changes)
        expected = dict(original_payload)
        expected["ga_rgca_context"] = {**original_payload["ga_rgca_context"], **changes}
        if candidate_payload != expected or candidate_payload["allow_demo"] is not False:
            raise ValueError("hypothetical input changed non-feeding context")
        comparison = {
            "changes": {name: {"from": snapshot.ga_rgca_context[name], "to": value}
                        for name, value in changes.items()},
            "only_feeding_fields_changed": True,
        }
        try:
            candidate = predictor.predict(snapshot, changes)
        except C1PredictionUnavailable as exc:
            candidates.append({**comparison, "prediction": None, "probability_delta": None,
                               "model_policy_result": "unresolved", "rejected_reasons": [],
                               "unresolved_reasons": [str(exc)]})
            continue
        rejected, unresolved = _standalone_policy_reasons(baseline, candidate)
        candidates.append({
            **comparison,
            "prediction": _prediction(candidate),
            "probability_delta": {
                "underweight": round(candidate.underweight_probability - baseline.underweight_probability, 6),
                "stunting": round(candidate.stunting_probability - baseline.stunting_probability, 6),
                "acute": {name: round(candidate.acute_probabilities[name] - baseline.acute_probabilities[name], 6)
                          for name in ("Normal", "MAM", "SAM")},
            },
            "model_policy_result": "rejected" if rejected else "unresolved",
            "rejected_reasons": rejected,
            "unresolved_reasons": unresolved,
        })
    # Rank model-rule-passing comparisons only. The order is a transparent
    # simplicity heuristic, never an estimated treatment effect.
    passing = [item for item in candidates if item["prediction"] is not None
               and not item["rejected_reasons"]]
    passing.sort(key=lambda item: (len(item["changes"]),
                                   tuple(sorted((key, value["to"]) for key, value in item["changes"].items()))))
    for rank, item in enumerate(passing, 1):
        item["rank"] = rank
    for item in candidates:
        item.setdefault("rank", None)
    from .guideline_references import research_guidance_for_age
    from .standalone_demo import _food_plans
    guidance = research_guidance_for_age(request.age_months)
    food_plans = _food_plans(request.age_months, guidance, request.budget_lkr,
                            request.budget_period) if passing else []
    fingerprint = hashlib.sha256(json.dumps(original_payload, sort_keys=True,
                                             separators=(",", ":")).encode()).hexdigest()
    return {
        "mode": "manual_genuine_c1_model_comparison",
        "submitted_input": request.model_dump(mode="json"),
        "input_fingerprint": fingerprint,
        "prediction_source": baseline.prediction_source,
        "model_version": baseline.model_version,
        "prediction_task": baseline.prediction_task,
        "baseline": baseline_display,
        "candidates": candidates,
        "ranked_model_comparisons": passing,
        "food_plans": food_plans,
        "budget": {"amount_lkr": str(request.budget_lkr) if request.budget_lkr is not None else None,
                   "period": request.budget_period,
                   "affordability": "unresolved"},
        "approved_intervention_cards": [],
        "clinical_use": False,
        "limitations": [
            "Manually entered invented inputs are not observed research records.",
            "Genuine C1 model outputs do not establish a causal treatment effect.",
            "Research authorization, individual suitability and local availability remain unresolved.",
        ],
    }
