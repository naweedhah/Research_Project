"""Replaceable predictor boundary; synthetic implementation is for software tests only."""
from typing import Protocol

from .schemas import Category, ChildFeatures


class Predictor(Protocol):
    model_id: str

    def predict_category(self, child: ChildFeatures) -> Category: ...


class SyntheticTestPredictor:
    model_id = "synthetic_test_v1"

    def predict_category(self, child: ChildFeatures) -> Category:
        # Arbitrary, deterministic software-test rule; no clinical interpretation.
        score = child.meals_per_day + child.dietary_diversity
        return "lower_concern" if score >= 7 else "higher_concern"


class SyntheticSklearnPredictor:
    """Separate DiCE-compatible test adapter trained only on the synthetic design grid."""

    model_id = "synthetic_sklearn_grid_v1"

    def __init__(self) -> None:
        import pandas as pd
        from sklearn.tree import DecisionTreeClassifier

        from .synthetic_data import synthetic_reference_points

        points = synthetic_reference_points()
        frame = pd.DataFrame(points, columns=["meals_per_day", "dietary_diversity"])
        target = [int(meals + diversity >= 7) for meals, diversity in points]
        self.model = DecisionTreeClassifier(random_state=17).fit(frame, target)
        if list(self.model.predict(frame)) != target:
            raise RuntimeError("synthetic classifier did not reproduce its test labels")

    def predict_category(self, child: ChildFeatures) -> Category:
        import pandas as pd

        frame = pd.DataFrame([{"meals_per_day": child.meals_per_day,
                               "dietary_diversity": child.dietary_diversity}])
        return "lower_concern" if int(self.model.predict(frame)[0]) == 1 else "higher_concern"
