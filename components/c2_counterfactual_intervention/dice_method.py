"""Official DiCE model-agnostic random explainer; no bounded-search fallback."""
from .contracts import PredictorCompatibilityError
from .feature_policy import ACTIONABLE
from .predictor import DiceCompatiblePredictor
from .schemas import Change, ChildFeatures


def generate_dice_candidates(child: ChildFeatures, predictor: DiceCompatiblePredictor,
                             max_changes: int, total_cfs: int = 20, seed: int = 17) -> list[tuple[Change, ...]]:
    import dice_ml
    import pandas as pd
    import io
    from contextlib import redirect_stderr, redirect_stdout
    from raiutils.exceptions import UserConfigValidationException

    if not isinstance(predictor, DiceCompatiblePredictor):
        raise PredictorCompatibilityError("DiCE adapter is incomplete")
    frame = predictor.dice_reference_data()
    outcome = predictor.dice_outcome_name
    features = [column for column in frame.columns if column != outcome]
    if outcome not in frame or not set(ACTIONABLE).issubset(features):
        raise PredictorCompatibilityError("DiCE reference data lacks required columns")
    if list(predictor.dice_model.predict(frame[features])) != list(frame[outcome]):
        raise PredictorCompatibilityError("DiCE reference labels disagree with generation model")
    row = predictor.dice_query(child)
    if set(row) != set(features):
        raise PredictorCompatibilityError("DiCE query features differ from reference data")
    query = pd.DataFrame([row], columns=features)
    model_prediction = predictor.dice_model.predict(query)[0]
    if (predictor.dice_category(model_prediction) != predictor.predict_category(child)
            or predictor.dice_category(predictor.dice_target_label) != predictor.contract.desired_category):
        raise PredictorCompatibilityError("DiCE generation and validation predictors disagree")
    data = dice_ml.Data(dataframe=frame, continuous_features=list(ACTIONABLE), outcome_name=outcome)
    model = dice_ml.Model(model=predictor.dice_model, backend="sklearn", model_type="classifier")
    explainer = dice_ml.Dice(data, model, method="random")
    ranges = {feature: [getattr(child, feature), min(getattr(child, feature) + 1, 5)]
              for feature in ACTIONABLE}
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = explainer.generate_counterfactuals(
                query, total_CFs=total_cfs, desired_class=predictor.dice_target_label,
                features_to_vary=list(ACTIONABLE),
                permitted_range=ranges, random_seed=seed, verbose=False)
    except UserConfigValidationException as exc:
        if "No counterfactuals found" in str(exc):
            return []
        raise
    candidates = []
    seen = set()
    for row in result.cf_examples_list[0].final_cfs_df.to_dict("records") if result.cf_examples_list[0].final_cfs_df is not None else []:
        if any(row[feature] != query.iloc[0][feature] for feature in features if feature not in ACTIONABLE):
            continue
        if any(not float(row[f]).is_integer() for f in ACTIONABLE):
            continue
        changes = tuple(Change(feature=f, from_value=getattr(child, f), to_value=int(row[f]))
                        for f in ACTIONABLE if row[f] != getattr(child, f))
        candidate = child.model_validate({**child.model_dump(), **{c.feature: c.to_value for c in changes}})
        candidate_query = pd.DataFrame([predictor.dice_query(candidate)], columns=features)
        direct = predictor.dice_category(predictor.dice_model.predict(candidate_query)[0])
        if direct != predictor.predict_category(candidate):
            raise PredictorCompatibilityError("DiCE generation and validation predictors disagree")
        key = tuple((c.feature, c.to_value) for c in changes)
        if key and len(changes) <= max_changes and key not in seen:
            seen.add(key)
            candidates.append(changes)
    return candidates
