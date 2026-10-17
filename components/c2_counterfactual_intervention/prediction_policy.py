"""Contract-defined acceptance of category or joint type/severity predictions."""
from .contracts import ModelPrediction, PredictorCompatibilityError, PredictorContract


def checked_prediction(predictor, child) -> ModelPrediction:
    contract: PredictorContract = predictor.contract
    if contract.output_mode == "category":
        if not callable(getattr(predictor, "predict_category", None)):
            raise PredictorCompatibilityError("category predictor method missing")
        prediction = ModelPrediction(type_label=predictor.predict_category(child))
        if prediction.type_label not in {target.code for target in contract.targets}:
            raise PredictorCompatibilityError("predictor returned an undeclared category")
        return prediction
    if not callable(getattr(predictor, "predict_outcomes", None)):
        raise PredictorCompatibilityError("two-output predictor method missing")
    try:
        prediction = ModelPrediction.model_validate(predictor.predict_outcomes(child))
    except (TypeError, ValueError) as exc:
        raise PredictorCompatibilityError("two-output prediction missing or malformed") from exc
    if prediction.type_label not in {target.code for target in contract.type_targets}:
        raise PredictorCompatibilityError("predictor returned an undeclared type")
    if prediction.severity_label not in {target.code for target in contract.severity_targets}:
        raise PredictorCompatibilityError("predictor returned a missing or undeclared severity")
    if (prediction.type_probabilities is not None and
            set(prediction.type_probabilities) != {target.code for target in contract.type_targets}):
        raise PredictorCompatibilityError("type probability labels mismatch")
    if (prediction.severity_probabilities is not None and
            set(prediction.severity_probabilities) != {target.code for target in contract.severity_targets}):
        raise PredictorCompatibilityError("severity probability labels mismatch")
    return prediction


def acceptance_reason(baseline: ModelPrediction, candidate: ModelPrediction,
                      contract: PredictorContract) -> str | None:
    """None means acceptable progress under explicitly supplied, reviewed policy."""
    if contract.output_mode == "category":
        if baseline.type_label == contract.desired_category or candidate.type_label != contract.desired_category:
            return "no favorable category change in predictor"
        return None
    order = {label: index for index, label in enumerate(contract.severity_order)}
    if order[candidate.severity_label] > order[baseline.severity_label]:
        return "candidate severity worsens"
    type_changed = candidate.type_label != baseline.type_label
    permitted = {(transition.from_label, transition.to_label)
                 for transition in contract.accepted_type_transitions}
    if type_changed and (baseline.type_label, candidate.type_label) not in permitted:
        return "type transition is not approved"
    if not type_changed and order[candidate.severity_label] == order[baseline.severity_label]:
        return "no approved type or severity improvement"
    return None
