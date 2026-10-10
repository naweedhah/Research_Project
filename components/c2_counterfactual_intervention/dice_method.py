"""Official DiCE model-agnostic random explainer; no bounded-search fallback."""
from .feature_policy import ACTIONABLE
from .predictor import SyntheticSklearnPredictor
from .schemas import Change, ChildFeatures
from .synthetic_data import synthetic_reference_points


def generate_dice_candidates(child: ChildFeatures, predictor: SyntheticSklearnPredictor,
                             max_changes: int, total_cfs: int = 20, seed: int = 17) -> list[tuple[Change, ...]]:
    import dice_ml
    import pandas as pd
    import io
    from contextlib import redirect_stderr, redirect_stdout
    from raiutils.exceptions import UserConfigValidationException

    if not isinstance(predictor, SyntheticSklearnPredictor):
        raise TypeError("DiCE requires the synthetic sklearn test adapter in Phase 2")
    frame = pd.DataFrame(synthetic_reference_points(), columns=list(ACTIONABLE))
    frame["outcome"] = (frame["meals_per_day"] + frame["dietary_diversity"] >= 7).astype(int)
    data = dice_ml.Data(dataframe=frame, continuous_features=list(ACTIONABLE), outcome_name="outcome")
    model = dice_ml.Model(model=predictor.model, backend="sklearn", model_type="classifier")
    explainer = dice_ml.Dice(data, model, method="random")
    query = pd.DataFrame([{"meals_per_day": child.meals_per_day,
                           "dietary_diversity": child.dietary_diversity}])
    ranges = {feature: [getattr(child, feature), min(getattr(child, feature) + 1, 5)]
              for feature in ACTIONABLE}
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = explainer.generate_counterfactuals(
                query, total_CFs=total_cfs, desired_class=1, features_to_vary=list(ACTIONABLE),
                permitted_range=ranges, random_seed=seed, verbose=False)
    except UserConfigValidationException as exc:
        if "No counterfactuals found" in str(exc):
            return []
        raise
    candidates = []
    seen = set()
    for row in result.cf_examples_list[0].final_cfs_df.to_dict("records") if result.cf_examples_list[0].final_cfs_df is not None else []:
        if any(not float(row[f]).is_integer() for f in ACTIONABLE):
            continue
        changes = tuple(Change(feature=f, from_value=getattr(child, f), to_value=int(row[f]))
                        for f in ACTIONABLE if row[f] != getattr(child, f))
        key = tuple((c.feature, c.to_value) for c in changes)
        if key and len(changes) <= max_changes and key not in seen:
            seen.add(key)
            candidates.append(changes)
    return candidates
