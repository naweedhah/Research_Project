"""Counterfactual search orchestration with no clinical outcome claims."""
from .candidate_generation import generate_candidates
from .contracts import PredictorCompatibilityError, PredictorContract
from .dice_method import generate_dice_candidates
from .face_graph import generate_face_candidates
from .feature_policy import validate_changes
from .feasibility import check_feasibility
from .food_feasibility import assess_food_alternative
from .predictor import DiceCompatiblePredictor, Predictor, SyntheticSklearnPredictor, SyntheticTestPredictor
from .prediction_policy import acceptance_reason, checked_prediction
from .ranking import select_diverse
from .schemas import CandidateInfo, InterventionCard, RecommendationRequest, RecommendationResponse


class MissingRealPredictorError(RuntimeError):
    pass


def resolve_predictor(request: RecommendationRequest, predictor: Predictor | None) -> Predictor:
    if request.mode == "real":
        if predictor is None:
            raise MissingRealPredictorError("real mode has no registered C1 predictor")
    elif predictor is None:
        predictor = (SyntheticSklearnPredictor() if request.method == "dice" or
                     request.predictor == "synthetic_sklearn_grid_v1" else SyntheticTestPredictor())
    contract = getattr(predictor, "contract", None)
    if not isinstance(contract, PredictorContract):
        raise PredictorCompatibilityError("predictor lacks a versioned C2 contract")
    if contract.mode != request.mode:
        raise PredictorCompatibilityError("predictor mode does not match request mode")
    if request.predictor is not None and contract.model_id != request.predictor:
        raise PredictorCompatibilityError("predictor ID mismatch")
    if request.predictor_version is not None and contract.model_version != request.predictor_version:
        raise PredictorCompatibilityError("predictor version mismatch")
    sources = {feature.source_field for feature in contract.features}
    if not sources.issubset(set(type(request.child).model_fields)):
        raise PredictorCompatibilityError("predictor requires unmapped child fields")
    for feature in contract.features:
        value = getattr(request.child, feature.source_field)
        if value is None:
            if feature.missing_value_policy == "reject":
                raise PredictorCompatibilityError(f"required feature missing: {feature.source_field}")
            continue
        valid_type = {
            "integer": type(value) is int,
            "number": type(value) in (int, float),
            "boolean": type(value) is bool,
            "category": isinstance(value, str) and value in feature.categories,
        }[feature.dtype]
        if not valid_type:
            raise PredictorCompatibilityError(f"feature type/category mismatch: {feature.source_field}")
    if request.method == "dice":
        if not isinstance(predictor, DiceCompatiblePredictor) and contract.output_mode == "category":
            raise PredictorCompatibilityError("DiCE requires a compatible model and reference-data adapter")
        if contract.output_mode == "type_severity" and not all(
                hasattr(predictor, name) for name in
                ("dice_model", "dice_outcome_name", "dice_target_label", "dice_reference_data",
                 "dice_query", "dice_prediction")):
            raise PredictorCompatibilityError("two-output DiCE requires a joint-label adapter")
    if request.mode == "real" and request.method == "face_graph":
        if not contract.reference_data_id or not callable(getattr(predictor, "reference_points", None)):
            raise PredictorCompatibilityError("real graph search requires versioned reference data")
    return predictor


def checked_category(predictor: Predictor, child) -> str:
    """Legacy test helper; dual-output callers use checked_prediction instead."""
    return checked_prediction(predictor, child).type_label


def generate_method_candidates(request: RecommendationRequest, predictor: Predictor) -> list:
    if request.method == "bounded_search":
        generated = generate_candidates(request.child, request.max_changes)
    elif request.method == "dice":
        generated = generate_dice_candidates(request.child, predictor, request.max_changes)
    elif request.method == "face_graph":
        reference = predictor.reference_points() if request.mode == "real" else None
        if request.mode == "real" and reference is None:
            raise PredictorCompatibilityError("real graph reference data unavailable")
        generated = generate_face_candidates(request.child, request.context, predictor, request.max_changes,
                                             reference=reference)
    else:
        raise ValueError(f"unsupported method: {request.method}")
    unique = []
    seen = set()
    for changes in generated:
        key = tuple(sorted((change.feature, change.from_value, change.to_value) for change in changes))
        if key not in seen:
            seen.add(key)
            unique.append(changes)
    return unique


def run_pipeline(request: RecommendationRequest, predictor: Predictor | None = None) -> tuple[RecommendationResponse, list]:
    predictor = resolve_predictor(request, predictor)
    baseline = checked_prediction(predictor, request.child)
    accepted = []
    other: list[CandidateInfo] = []
    generated = generate_method_candidates(request, predictor)
    for changes in generated:
        invalid = validate_changes(request.child, changes)
        if invalid:
            other.append(CandidateInfo(changes=list(changes), status="rejected", reasons=invalid))
            continue
        candidate = request.child.model_validate({**request.child.model_dump(), **{c.feature: c.to_value for c in changes}})
        try:
            predicted = checked_prediction(predictor, candidate)
        except PredictorCompatibilityError as exc:
            other.append(CandidateInfo(changes=list(changes), status="unresolved",
                                       reasons=[str(exc)]))
            continue
        reason = acceptance_reason(baseline, predicted, predictor.contract)
        if reason:
            other.append(CandidateInfo(changes=list(changes), status="rejected",
                                       reasons=[reason]))
            continue
        status, reasons = check_feasibility(changes, request.context)
        if status != "feasible":
            other.append(CandidateInfo(changes=list(changes), status=status, reasons=reasons))
            continue
        accepted.append((changes, True, reasons))
    if request.food_planning is None:
        selected = select_diverse(accepted, request.max_cards)
        explanation = ("The predictor changes category for this proposed input; this does not establish a treatment effect."
                       if predictor.contract.output_mode == "category" else
                       "The predictor outputs satisfy the supplied type and severity policy; this does not establish a treatment effect.")
        cards = [InterventionCard(rank=i, changes=list(changes),
                                  explanation=explanation,
                                  feasibility_reasons=reasons)
                 for i, (changes, _, reasons) in enumerate(selected, 1)]
    else:
        # Supplied proposals must match an independently generated, predictor-tested change.
        planning = request.food_planning
        accepted_by_change = {
            frozenset((c.feature, c.from_value, c.to_value) for c in changes): (changes, reasons)
            for changes, _, reasons in accepted
        }
        feasible_alternatives = []
        for alternative in planning.alternatives:
            key = frozenset((c.feature, c.from_value, c.to_value) for c in alternative.changes)
            matched = accepted_by_change.get(key)
            if matched is None:
                other.append(CandidateInfo(changes=[c.model_dump() for c in alternative.changes], status="rejected",
                                           reasons=["proposal has no model-supported, baseline-feasible counterfactual"],
                                           alternative_id=alternative.alternative_id))
                continue
            assessment = assess_food_alternative(alternative, planning, request.mode)
            if assessment.status != "feasible":
                other.append(CandidateInfo(changes=[c.model_dump() for c in alternative.changes], status=assessment.status,
                                           reasons=list(assessment.reasons),
                                           alternative_id=alternative.alternative_id))
                continue
            feasible_alternatives.append((alternative, matched, assessment))
        feasible_alternatives.sort(key=lambda item: (
            len(item[1][0]), item[2].cost_lkr, len(item[0].foods), item[0].alternative_id))
        catalog = {food.food_id: food for food in planning.catalog}
        cards = []
        for i, (alternative, (changes, base_reasons), assessment) in enumerate(
                feasible_alternatives[:request.max_cards], 1):
            foods = [catalog[quantity.food_id].name for quantity in alternative.foods]
            resources = [f"{quantity.quantity} {quantity.unit} {catalog[quantity.food_id].name}"
                         for quantity in alternative.foods]
            cards.append(InterventionCard(
                rank=i, changes=list(changes), title=alternative.title, reason=alternative.reason,
                explanation=("This feeding proposal matches a favorable model category change; it does not establish a treatment effect or guarantee recovery."
                             if predictor.contract.output_mode == "category" else
                             "This feeding proposal satisfies the supplied type and severity policy; it does not establish a treatment effect or guarantee recovery."),
                feasibility_reasons=base_reasons + ["supplied food feasibility checks passed"],
                food_options=foods, required_resources=resources,
                incremental_cost_lkr=str(assessment.cost_lkr), cost_period=alternative.period,
                affordability=assessment.affordability, availability=assessment.availability,
                alternative_id=alternative.alternative_id))
    empty_message = ("No feasible graph path found in synthetic reference data" if request.method == "face_graph"
                     else "No feasible favorable candidate found under supplied constraints")
    provenance = (f"{predictor.contract.model_id}@{predictor.contract.model_version}: "
                  f"{request.mode} model; no clinical validation")
    referral = request.food_planning.referral_policy if request.food_planning else None
    referral_recommended = bool(referral and baseline.type_label in referral.trigger_categories and
                                (request.mode == "test" or referral.evidence.kind != "synthetic_test"))
    response = RecommendationResponse(child_id=request.child_id, condition_category=baseline.type_label,
                                      condition_severity=baseline.severity_label,
                                      cards=cards, rejected_or_unresolved=other,
                                      message=("Test-only candidates for professional review" if request.mode == "test"
                                               else "Candidates for professional review") if cards else
                                      empty_message,
                                      method=request.method,
                                      mode=request.mode, provenance=provenance,
                                      professional_referral_recommended=referral_recommended,
                                      referral_message=referral.message if referral_recommended else None)
    return response, generated


def recommend(request: RecommendationRequest, predictor: Predictor | None = None) -> RecommendationResponse:
    return run_pipeline(request, predictor)[0]
