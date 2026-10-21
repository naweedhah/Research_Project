"""Explicit software-test counterfactual target over four selected shopping examples.

Target means: select exactly one catalogue option with an indicative cost within
the supplied budget and no explicitly excluded or unavailable listed food.
It says nothing about nutrient adequacy, individual safety or health benefit.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from itertools import product


def eligible_ids(candidates: list[dict], household) -> list[str]:
    if household.budget_lkr is None:
        return []
    allowed = []
    for card in candidates:
        foods = {item["food_id"] for item in card["items"]}
        if (card["reference_budget_fit"] == "within_budget"
                and not foods.intersection(household.excluded_food_ids)
                and not any(household.local_availability.get(food) is False for food in foods)):
            allowed.append(card["candidate_id"])
    return allowed


def dice_test_candidates(candidates: list[dict], allowed: list[str]) -> tuple[list[str], dict]:
    """Run official dice-ml against a labelled, non-clinical one-hot fixture."""
    if not allowed:
        return [], {"reason": "No catalogue option meets the engineering test target"}
    import dice_ml
    import pandas as pd
    from sklearn.tree import DecisionTreeClassifier

    columns = [f"option_{i}" for i in range(len(candidates))]
    allowed_indexes = {i for i, card in enumerate(candidates) if card["candidate_id"] in allowed}
    frame = pd.DataFrame(list(product((0, 1), repeat=len(candidates))), columns=columns)
    frame["eligible"] = [int(bits.index(1) in allowed_indexes) if sum(bits) == 1 else 0
                         for bits in frame[columns].itertuples(index=False, name=None)]
    frame[columns] = frame[columns].astype(str)
    classifier = DecisionTreeClassifier(random_state=17).fit(frame[columns], frame["eligible"])
    if (classifier.predict(frame[columns]) != frame["eligible"]).any():
        return [], {"reason": "Software-test surrogate disagrees with its reference labels"}
    data = dice_ml.Data(dataframe=frame, continuous_features=[], outcome_name="eligible")
    model = dice_ml.Model(model=classifier, backend="sklearn", model_type="classifier")
    query = pd.DataFrame([["0"] * len(columns)], columns=columns)
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        explained = dice_ml.Dice(data, model, method="random").generate_counterfactuals(
            query, total_CFs=len(allowed), desired_class=1, features_to_vary=columns,
            random_seed=17, verbose=False)
    table = explained.cf_examples_list[0].final_cfs_df
    generated = []
    for row in [] if table is None else table[columns].itertuples(index=False, name=None):
        bits = tuple(int(value) for value in row)
        if sum(bits) != 1 or classifier.predict(pd.DataFrame([bits], columns=columns))[0] != 1:
            continue
        identifier = candidates[bits.index(1)]["candidate_id"]
        if identifier in allowed and identifier not in generated:
            generated.append(identifier)
    return generated, {"reference_rows": len(frame), "surrogate_training_agreement": 1.0,
                       "surrogate_kind": "software-test decision tree; no clinical or nutrition validity"}


def wachter_test_candidates(candidates: list[dict], allowed: list[str]) -> tuple[list[str], dict]:
    """Bounded continuous optimization with a relaxed one-hot action vector."""
    import numpy as np
    from scipy.optimize import minimize

    if not allowed:
        return [], {"reason": "No catalogue option meets the engineering test target"}
    target = np.asarray([int(card["candidate_id"] in allowed) for card in candidates], dtype=float)
    costs = np.asarray([float(card["reference_cost_lkr"] or 1e9) for card in candidates])
    scale = max(float(costs[costs < 1e9].max()), 1.0)

    def objective(x):
        attainment = max(0.0, 1.0 - float(target @ x))
        return 20 * attainment**2 + 4 * (float(x.sum()) - 1)**2 + 0.01 * float(costs @ x) / scale

    runs = [minimize(objective, np.asarray(start), method="L-BFGS-B",
                     bounds=[(0, 1)] * len(candidates), options={"maxiter": 120, "ftol": 1e-10})
            for start in ([0.0] * len(candidates), *[[float(i == j) for i in range(len(candidates))]
                                                    for j in range(len(candidates))])]
    best = min(runs, key=lambda row: (float(row.fun), tuple(row.x)))
    index = int(np.argmax(best.x))
    identifier = candidates[index]["candidate_id"]
    accepted = identifier in allowed and bool(best.success)
    return ([identifier] if accepted else []), {
        "objective_value": round(float(best.fun), 6), "converged": bool(best.success),
        "iterations": int(best.nit), "initializations": len(runs),
        "discrete_candidate_independently_matches_test_target": accepted,
        "objective_kind": "software-test relaxed one-hot selection; no nutrition or C1 outcome objective"}
