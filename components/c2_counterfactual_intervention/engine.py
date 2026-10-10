"""Counterfactual search orchestration with no clinical outcome claims."""
from .candidate_generation import generate_candidates
from .contracts import PredictorCompatibilityError, PredictorContract
from .dice_method import generate_dice_candidates
from .face_graph import generate_face_candidates
from .feature_policy import validate_changes
from .feasibility import check_feasibility
from .predictor import DiceCompatiblePredictor, Predictor, SyntheticSklearnPredictor, SyntheticTestPredictor
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
    if request.method == "dice" and not isinstance(predictor, DiceCompatiblePredictor):
        raise PredictorCompatibilityError("DiCE requires a compatible model and reference-data adapter")
    if request.mode == "real" and request.method == "face_graph":
        if not contract.reference_data_id or not callable(getattr(predictor, "reference_points", None)):
            raise PredictorCompatibilityError("real graph search requires versioned reference data")
    return predictor


def checked_category(predictor: Predictor, child) -> str:
    category = predictor.predict_category(child)
    if category not in {target.code for target in predictor.contract.targets}:
        raise PredictorCompatibilityError("predictor returned an undeclared category")
    return category


def generate_method_candidates(request: RecommendationRequest, predictor: Predictor) -> list:
    if request.method == "bounded_search":
        generated = generate_candidates(request.child, request.max_changes)
    elif request.method == "dice":
        generated = generate_dice_candidates(request.child, predictor, request.max_changes)
    elif request.method == "face_graph":
        reference = predictor.reference_points() if request.mode == "real" else None
        generated = generate_face_candidates(request.child, request.context, predictor, request.max_changes,
                                             reference=reference)
    else:
        raise ValueError(f"unsupported method: {request.method}")
    unique = []
    seen = set()
    for changes in generated:
        key = tuple(sorted((change.feature, change.to_value) for change in changes))
        if key not in seen:
            seen.add(key)
            unique.append(changes)
    return unique


def run_pipeline(request: RecommendationRequest, predictor: Predictor | None = None) -> tuple[RecommendationResponse, list]:
    predictor = resolve_predictor(request, predictor)
    baseline = checked_category(predictor, request.child)
    target = predictor.contract.desired_category
    accepted = []
    other: list[CandidateInfo] = []
    generated = generate_method_candidates(request, predictor)
    for changes in generated:
        invalid = validate_changes(request.child, changes)
        if invalid:
            other.append(CandidateInfo(changes=list(changes), status="rejected", reasons=invalid))
            continue
        candidate = request.child.model_validate({**request.child.model_dump(), **{c.feature: c.to_value for c in changes}})
        predicted = checked_category(predictor, candidate)
        if baseline == target or predicted != target:
            other.append(CandidateInfo(changes=list(changes), status="rejected",
                                       reasons=["no favorable category change in predictor"]))
            continue
        status, reasons = check_feasibility(changes, request.context)
        if status != "feasible":
            other.append(CandidateInfo(changes=list(changes), status=status, reasons=reasons))
            continue
        accepted.append((changes, True, reasons))
    selected = select_diverse(accepted, request.max_cards)
    cards = [InterventionCard(rank=i, changes=list(changes),
                              explanation="The predictor changes category for this proposed input; this does not establish a treatment effect.",
                              feasibility_reasons=reasons)
             for i, (changes, _, reasons) in enumerate(selected, 1)]
    empty_message = ("No feasible graph path found in synthetic reference data" if request.method == "face_graph"
                     else "No feasible favorable candidate found under supplied constraints")
    provenance = (f"{predictor.contract.model_id}@{predictor.contract.model_version}: "
                  f"{request.mode} model; no clinical validation")
    response = RecommendationResponse(child_id=request.child_id, condition_category=baseline,
                                      cards=cards, rejected_or_unresolved=other,
                                      message="Test-only candidates for professional review" if cards else
                                      empty_message,
                                      method=request.method,
                                      mode=request.mode, provenance=provenance)
    return response, generated


def recommend(request: RecommendationRequest, predictor: Predictor | None = None) -> RecommendationResponse:
    return run_pipeline(request, predictor)[0]
