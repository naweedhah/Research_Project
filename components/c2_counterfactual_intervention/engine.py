"""Counterfactual search orchestration with no clinical outcome claims."""
from .candidate_generation import generate_candidates
from .dice_method import generate_dice_candidates
from .face_graph import generate_face_candidates
from .feature_policy import validate_changes
from .feasibility import check_feasibility
from .predictor import Predictor, SyntheticSklearnPredictor, SyntheticTestPredictor
from .ranking import select_diverse
from .schemas import CandidateInfo, InterventionCard, RecommendationRequest, RecommendationResponse


def generate_method_candidates(request: RecommendationRequest, predictor: Predictor) -> list:
    if request.method == "bounded_search":
        generated = generate_candidates(request.child, request.max_changes)
    elif request.method == "dice":
        generated = generate_dice_candidates(request.child, predictor, request.max_changes)
    elif request.method == "face_graph":
        generated = generate_face_candidates(request.child, request.context, predictor, request.max_changes)
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
    predictor = predictor or (SyntheticSklearnPredictor() if request.method == "dice" or
                              request.predictor == "synthetic_sklearn_grid_v1" else SyntheticTestPredictor())
    baseline = predictor.predict_category(request.child)
    accepted = []
    other: list[CandidateInfo] = []
    generated = generate_method_candidates(request, predictor)
    for changes in generated:
        invalid = validate_changes(request.child, changes)
        if invalid:
            other.append(CandidateInfo(changes=list(changes), status="rejected", reasons=invalid))
            continue
        candidate = request.child.model_validate({**request.child.model_dump(), **{c.feature: c.to_value for c in changes}})
        predicted = predictor.predict_category(candidate)
        if baseline == "lower_concern" or predicted != "lower_concern":
            other.append(CandidateInfo(changes=list(changes), status="rejected",
                                       reasons=["no favorable category change in test predictor"]))
            continue
        status, reasons = check_feasibility(changes, request.context)
        if status != "feasible":
            other.append(CandidateInfo(changes=list(changes), status=status, reasons=reasons))
            continue
        accepted.append((changes, True, reasons))
    selected = select_diverse(accepted, request.max_cards)
    cards = [InterventionCard(rank=i, changes=list(changes),
                              explanation="Test predictor changes category for this proposed input; this does not establish a treatment effect.",
                              feasibility_reasons=reasons)
             for i, (changes, _, reasons) in enumerate(selected, 1)]
    empty_message = ("No feasible graph path found in synthetic reference data" if request.method == "face_graph"
                     else "No feasible favorable candidate found under supplied constraints")
    response = RecommendationResponse(child_id=request.child_id, condition_category=baseline,
                                      cards=cards, rejected_or_unresolved=other,
                                      message="Test-only candidates for professional review" if cards else
                                      empty_message,
                                      method=request.method,
                                      provenance=f"{predictor.model_id}: synthetic test-only predictor; no clinical validation")
    return response, generated


def recommend(request: RecommendationRequest, predictor: Predictor | None = None) -> RecommendationResponse:
    return run_pipeline(request, predictor)[0]
