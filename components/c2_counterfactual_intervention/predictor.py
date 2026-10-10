"""Replaceable predictor boundary; synthetic implementation is for software tests only."""
from typing import Any, Protocol, runtime_checkable

from .contracts import PredictorContract, synthetic_contract
from .schemas import Category, ChildFeatures


class Predictor(Protocol):
    contract: PredictorContract

    def predict_category(self, child: ChildFeatures) -> str: ...


@runtime_checkable
class DiceCompatiblePredictor(Predictor, Protocol):
    dice_model: Any
    dice_outcome_name: str
    dice_target_label: int | str

    def dice_reference_data(self) -> Any: ...

    def dice_query(self, child: ChildFeatures) -> dict[str, Any]: ...

    def dice_category(self, label: Any) -> str: ...


class SyntheticTestPredictor:
    model_id = "synthetic_test_v1"
    contract = synthetic_contract(model_id)

    def predict_category(self, child: ChildFeatures) -> Category:
        # Arbitrary, deterministic software-test rule; no clinical interpretation.
        score = child.meals_per_day + child.dietary_diversity
        return "lower_concern" if score >= 7 else "higher_concern"


class SyntheticSklearnPredictor:
    """Separate DiCE-compatible test adapter trained only on the synthetic design grid."""

    model_id = "synthetic_sklearn_grid_v1"
    contract = synthetic_contract(model_id)
    dice_outcome_name = "outcome"
    dice_target_label = 1

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

    @property
    def dice_model(self):
        return self.model

    def dice_reference_data(self):
        import pandas as pd

        from .synthetic_data import synthetic_reference_points

        frame = pd.DataFrame(synthetic_reference_points(), columns=["meals_per_day", "dietary_diversity"])
        frame[self.dice_outcome_name] = self.model.predict(frame)
        return frame

    def dice_query(self, child: ChildFeatures) -> dict[str, int]:
        return {"meals_per_day": child.meals_per_day, "dietary_diversity": child.dietary_diversity}

    def dice_category(self, label) -> str:
        return "lower_concern" if int(label) == 1 else "higher_concern"

    def predict_category(self, child: ChildFeatures) -> Category:
        import pandas as pd

        frame = pd.DataFrame([self.dice_query(child)])
        return self.dice_category(self.model.predict(frame)[0])
