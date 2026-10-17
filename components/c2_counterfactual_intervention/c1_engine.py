"""C1-shaped counterfactual pathway; synthetic demo and real HTTP are isolated."""
import hashlib
import json
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .c1_compat import C1Output, C1Snapshot, DIVERSITY, FEATURES, MEALS, next_categories
from .c1_predictors import C1PredictionUnavailable, RealC1HttpPredictor, SimulatedC1Predictor
from .food_feasibility import assess_food_alternative
from .food_resources import FoodPlanningContext
from .schemas import Change, ChildFeatures, FeasibilityContext
from .feasibility import check_feasibility


class C1ResearchPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy_id: str = Field(min_length=1)
    approved_for_research: bool = False
    allowed_type_transitions: list[tuple[str, str]] = Field(default_factory=list)
    allow_severity_improvement: bool = False
    require_condition_nonworsening: bool = True
    reject_uncertainty: bool = True
    minimum_probability_change: float | None = Field(default=None, ge=0, le=1)


class C1Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["simulated", "real"]
    method: Literal["bounded_search", "dice", "face_graph"] = "bounded_search"
    simulator_case: Literal["favorable", "unchanged", "worsening", "uncertain"] = "favorable"
    snapshot: C1Snapshot
    context: FeasibilityContext
    policy: C1ResearchPolicy
    food_planning: FoodPlanningContext | None = None
    max_cards: int = Field(default=5, ge=1, le=10)


class C1Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str
    method: str
    banner: str
    baseline: dict
    candidates: list[dict]
    cards: list[dict]
    rejected_or_unresolved: list[dict]
    message: str
    c1_integrated: bool = False
    clinical_use: bool = False


def _display(output: C1Output) -> dict:
    """Public comparison contains labels and provenance, never probability claims."""
    return {"predicted_malnutrition_type": output.predicted_malnutrition_type,
            "acute_status": output.acute_status, "severity": output.severity,
            "uncertainty_flag": output.uncertainty_flag,
            "prediction_source": output.prediction_source, "model_version": output.model_version,
            "data_limitations": output.data_limitations}


def _synthetic_child(snapshot: C1Snapshot) -> ChildFeatures:
    return ChildFeatures(age_months=int(snapshot.historical_baseline["age_months"]), sex="female",
                         household_income_band="unknown",
                         meals_per_day=MEALS.index(snapshot.ga_rgca_context["meal_frequency"]) + 2,
                         dietary_diversity=DIVERSITY.index(snapshot.ga_rgca_context["dietary_diversity"]))


def _method_candidates(request: C1Request) -> list[dict[str, str]]:
    allowed = next_categories(request.snapshot)
    if request.method == "bounded_search" or not allowed:
        return allowed
    # These method paths use only the 3x3 simulated ordinal category grid.
    # Real C1 DiCE/FACE require a governed classifier/reference handoff.
    if request.mode == "real":
        if request.food_planning is None:
            raise C1PredictionUnavailable("real C1 proposals require reviewed food and LKR affordability evidence")
        raise C1PredictionUnavailable("real DiCE/FACE model and reference data are unavailable")
    child = _synthetic_child(request.snapshot)
    from .contracts import LabelTransition, PredictorContract, TargetContract, SYNTHETIC_FEATURES
    from .schemas import Change

    class Facade:
        contract = PredictorContract(interface_version="c2-predictor-v2", output_mode="type_severity",
            model_id="c1-shaped-simulator-method-fixture", model_version="1", mode="test",
            features=SYNTHETIC_FEATURES,
            type_targets=tuple(TargetContract(code=x, definition="simulated test label") for x in
                ("Normal", "Underweight", "Stunting", "MAM", "SAM")),
            severity_targets=tuple(TargetContract(code=x, definition="simulated test label") for x in
                ("Normal", "Moderate", "Severe")),
            severity_order=("Normal", "Moderate", "Severe"),
            accepted_type_transitions=tuple(LabelTransition(from_label=a, to_label=b) for a in
                ("SAM", "MAM", "Underweight", "Stunting") for b in
                ("MAM", "Underweight", "Normal") if a != b))

        def predict_outcomes(self, point):
            from .contracts import ModelPrediction
            changes = {"meal_frequency": MEALS[point.meals_per_day - 2],
                       "dietary_diversity": DIVERSITY[point.dietary_diversity]}
            output = SimulatedC1Predictor().predict(request.snapshot, changes)
            return ModelPrediction(type_label=output.predicted_malnutrition_type,
                                   severity_label=output.severity)

        def reference_points(self):
            return tuple((m, d) for m in range(2, 5) for d in range(3))

    facade = Facade()
    if request.method == "face_graph":
        from .face_graph import generate_face_candidates
        generated = generate_face_candidates(child, request.context, facade, 2,
                                             reference=facade.reference_points())
    else:
        # Official DiCE uses a fitted *synthetic fixture* classifier, never C1 weights.
        import pandas as pd
        from sklearn.tree import DecisionTreeClassifier
        from .dice_method import generate_dice_candidates
        frame = pd.DataFrame(facade.reference_points(), columns=["meals_per_day", "dietary_diversity"])
        labels = {}
        for m, d in facade.reference_points():
            output = facade.predict_outcomes(ChildFeatures(age_months=24, sex="female",
                household_income_band="unknown", meals_per_day=m, dietary_diversity=d))
            labels[(m, d)] = (output.type_label, output.severity_label)
        classes = sorted(set(labels.values()))
        frame["outcome"] = [classes.index(labels[(m, d)]) for m, d in facade.reference_points()]
        model = DecisionTreeClassifier(random_state=17).fit(frame[["meals_per_day", "dietary_diversity"]], frame["outcome"])
        # The two-class fixture represents only a method smoke test. Final C1-shaped
        # predictions are independently checked by the shared Phase 6 policy below.
        class DiceFacade(Facade):
            dice_model = model
            dice_outcome_name = "outcome"
            dice_target_label = classes.index(("Normal", "Normal"))

            def dice_reference_data(self):
                return frame

            def dice_query(self, point):
                return {"meals_per_day": point.meals_per_day,
                        "dietary_diversity": point.dietary_diversity}

            def dice_prediction(self, label):
                from .contracts import ModelPrediction
                kind, severity = classes[int(label)]
                return ModelPrediction(type_label=kind, severity_label=severity)

            def predict_outcomes(self, point):
                import pandas as pd
                label = self.dice_model.predict(pd.DataFrame([self.dice_query(point)]))[0]
                return self.dice_prediction(label)
        # Existing DiCE agreement guard correctly refuses this independent fixture
        # when its classes do not match the C1-shaped simulator. No hidden fallback.
        generated = generate_dice_candidates(child, DiceFacade(), 2)
    result = []
    for group in generated:
        if any(c.to_value < 2 or c.to_value > 4 for c in group if c.feature == "meals_per_day") or any(
                c.to_value < 0 or c.to_value > 2 for c in group if c.feature == "dietary_diversity"):
            continue
        mapped = {"meal_frequency" if c.feature == "meals_per_day" else "dietary_diversity":
                  MEALS[c.to_value - 2] if c.feature == "meals_per_day" else DIVERSITY[c.to_value]
                  for c in group}
        if mapped in allowed and mapped not in result:
            result.append(mapped)
    return result


def _policy_reason(base: C1Output, candidate: C1Output, policy: C1ResearchPolicy) -> str | None:
    if not policy.approved_for_research:
        return "acceptance policy has not been approved for research"
    return _model_policy_reason(base, candidate, policy)


def _model_policy_reason(base: C1Output, candidate: C1Output, policy: C1ResearchPolicy) -> str | None:
    """Evaluate model-only rules; never grants research authorization by itself."""
    if policy.reject_uncertainty and (base.uncertainty_flag or candidate.uncertainty_flag):
        return "model uncertainty requires review"
    order = {"Normal": 0, "Moderate": 1, "Severe": 2}
    if order[candidate.severity] > order[base.severity]:
        return "predicted severity worsens"
    if policy.require_condition_nonworsening:
        for name in ("underweight_probability", "stunting_probability"):
            if getattr(candidate, name) > getattr(base, name) + 1e-9:
                return f"{name} worsens"
        for name in ("MAM", "SAM"):
            if candidate.acute_probabilities[name] > base.acute_probabilities[name] + 1e-9:
                return f"{name} probability worsens"
    changed_type = candidate.predicted_malnutrition_type != base.predicted_malnutrition_type
    if changed_type and (base.predicted_malnutrition_type, candidate.predicted_malnutrition_type) not in policy.allowed_type_transitions:
        return "type transition not approved"
    improved_severity = order[candidate.severity] < order[base.severity]
    if not changed_type and not (policy.allow_severity_improvement and improved_severity):
        return "no approved categorical improvement"
    if policy.minimum_probability_change is not None:
        delta = max(base.underweight_probability - candidate.underweight_probability,
                    base.stunting_probability - candidate.stunting_probability)
        if delta < policy.minimum_probability_change:
            return "approved minimum model change not met"
    return None


def run_c1(request: C1Request, predictor=None) -> C1Result:
    if request.mode == "real" and request.method != "bounded_search":
        raise C1PredictionUnavailable("real DiCE/FACE requires approved model/reference handoff")
    if request.mode == "real":
        if request.food_planning is None:
            raise C1PredictionUnavailable("real C1 proposals require reviewed food and LKR affordability evidence")
        configured_hash = os.getenv("C1_REAL_POLICY_SHA256", "")
        canonical = json.dumps(request.policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        policy_hash = hashlib.sha256(canonical.encode()).hexdigest()
        if not request.policy.approved_for_research or configured_hash != policy_hash:
            raise C1PredictionUnavailable("server-approved real C1 acceptance policy is unavailable")
    predictor = predictor or (SimulatedC1Predictor(request.simulator_case) if request.mode == "simulated" else RealC1HttpPredictor())
    if (request.mode == "real" and getattr(predictor, "source", None) != "GA-RGCA-v3") or (
        request.mode == "simulated" and getattr(predictor, "source", None) != "SIMULATED_TEST_ONLY"):
        raise C1PredictionUnavailable("predictor mode mismatch")
    baseline = predictor.predict(request.snapshot)
    cards, other, comparisons = [], [], []
    for changes in _method_candidates(request):
        item = {"changes": changes}
        try:
            candidate = predictor.predict(request.snapshot, changes)
            item["candidate"] = _display(candidate)
            reason = _policy_reason(baseline, candidate, request.policy)
            if reason:
                other.append({**item, "status": "unresolved" if "uncertainty" in reason or "not been approved" in reason else "rejected", "reasons": [reason]})
                continue
            child = _synthetic_child(request.snapshot)
            mapped = tuple(Change(feature="meals_per_day" if f == "meal_frequency" else "dietary_diversity",
                                  from_value=getattr(child, "meals_per_day" if f == "meal_frequency" else "dietary_diversity"),
                                  to_value=MEALS.index(v)+2 if f == "meal_frequency" else DIVERSITY.index(v))
                           for f, v in changes.items())
            if request.mode == "simulated":
                feasibility_status, feasibility_reasons = check_feasibility(mapped, request.context)
            else:
                rejected, unresolved = [], []
                for change in mapped:
                    for name in ("available", "practical", "age_suitable", "eligible",
                                 "clinically_suitable", "transition_justified"):
                        value = getattr(request.context, name).get(change.feature)
                        if value is False:
                            rejected.append(f"{change.feature}: {name} false")
                        elif value is None:
                            unresolved.append(f"{change.feature}: {name} unknown")
                feasibility_status = "rejected" if rejected else "unresolved" if unresolved else "feasible"
                feasibility_reasons = rejected + unresolved
            if feasibility_status != "feasible":
                other.append({**item, "status": feasibility_status, "reasons": feasibility_reasons})
                continue
            card = {"rank": len(cards) + 1, "changes": changes,
                    "explanation": ("Hypothetical simulator output" if request.mode == "simulated" else "Research model output") +
                                   " passed the supplied research policy; no treatment benefit is established.",
                    "professional_review_required": True, "feasibility_status": (
                        "feasible under supplied test assertions" if request.mode == "simulated"
                        else "research-feasible under supplied evidence; professional review required")}
            if request.food_planning:
                matching = [a for a in request.food_planning.alternatives if
                            {(c.feature, c.from_value, c.to_value) for c in a.changes} ==
                            {(c.feature, c.from_value, c.to_value) for c in mapped}]
                if not matching:
                    other.append({**item, "status": "unresolved", "reasons": ["no reviewed food proposal matches change"]})
                    continue
                assessment = assess_food_alternative(matching[0], request.food_planning, "test" if request.mode == "simulated" else "real")
                if assessment.status != "feasible":
                    other.append({**item, "status": assessment.status, "reasons": list(assessment.reasons)})
                    continue
                card.update(incremental_cost_lkr=str(assessment.cost_lkr), affordability=assessment.affordability,
                            affordability_scope=assessment.affordability_scope, availability=assessment.availability)
            cards.append(card)
            comparisons.append(item)
        except C1PredictionUnavailable as exc:
            other.append({**item, "status": "unresolved", "reasons": [str(exc)]})
    from decimal import Decimal
    cards.sort(key=lambda card: (len(card["changes"]), Decimal(card.get("incremental_cost_lkr", "0")),
                                 tuple(sorted(card["changes"]))))
    for index, card in enumerate(cards[:request.max_cards], 1):
        card["rank"] = index
    return C1Result(mode=request.mode, method=request.method,
                    banner="SIMULATED MODEL - NOT FOR CLINICAL USE" if request.mode == "simulated" else "RESEARCH MODEL - PROFESSIONAL REVIEW REQUIRED",
                    baseline=_display(baseline), candidates=comparisons, cards=cards[:request.max_cards],
                    rejected_or_unresolved=other,
                    message=("Research-test candidates require professional review" if cards else
                             "No approved, feasible counterfactual under the supplied policy and evidence"),
                    c1_integrated=False)
