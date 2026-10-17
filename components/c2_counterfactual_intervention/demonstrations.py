"""Six deterministic, synthetic-only C2 demonstrations; no clinical or price evidence."""
import json

from .engine import MissingRealPredictorError, recommend
from .evaluation import synthetic_request
from .schemas import RecommendationRequest


EVIDENCE = {"kind": "synthetic_test", "source": "Phase 5 software demonstration",
            "observed_on": "2026-01-01"}


def _request(meals: int = 3, diversity: int = 3) -> dict:
    raw = synthetic_request(meals, diversity, "bounded_search").model_dump(mode="json")
    raw["food_planning"] = {
        "catalog": [{"food_id": "test-food", "name": "Synthetic fixture food",
                     "food_group": "synthetic test group",
                     "price": {"amount_lkr": "60", "quantity": "2", "unit": "piece", "evidence": EVIDENCE},
                     "locally_available": True, "availability_evidence": EVIDENCE}],
        "budget": {"amount_lkr": "100", "period": "day", "evidence": EVIDENCE},
        "alternatives": [{"alternative_id": "test-option", "title": "Synthetic feeding-practice option",
                          "reason": "Software fixture matching a permitted feature transition",
                          "changes": [{"feature": "meals_per_day", "from_value": meals,
                                       "to_value": meals + 1}],
                          "foods": [{"food_id": "test-food", "quantity": "2", "unit": "piece",
                                     "serving_assumption": "synthetic one-day incremental amount"}],
                          "period": "day", "practice_evidence": EVIDENCE, "practice_reviewed": True,
                          "suitability_evidence": EVIDENCE, "age_suitable": True,
                          "clinically_suitable": True, "caregiver_practical": True}]}
    return raw


def demonstrate() -> dict:
    scenarios = {}
    for name in ("A_success", "B_unaffordable", "C_unavailable", "D_unknown_clinical",
                 "E_no_model_supported", "F_real_model_missing"):
        raw = _request(1, 1) if name == "E_no_model_supported" else _request()
        if name == "B_unaffordable":
            raw["food_planning"]["budget"]["amount_lkr"] = "50"
        elif name == "C_unavailable":
            raw["food_planning"]["catalog"][0]["locally_available"] = False
        elif name == "D_unknown_clinical":
            raw["food_planning"]["alternatives"][0]["clinically_suitable"] = None
        elif name == "F_real_model_missing":
            raw.update(mode="real", predictor="unregistered-c1", predictor_version="1")
        try:
            response = recommend(RecommendationRequest.model_validate(raw))
            scenarios[name] = {
                "cards": [card.model_dump(mode="json", exclude_none=True) for card in response.cards],
                "other": [item.model_dump(mode="json", exclude_none=True)
                          for item in response.rejected_or_unresolved],
                "message": response.message,
            }
        except MissingRealPredictorError as exc:
            scenarios[name] = {"cards": [], "error": str(exc)}
    return {"synthetic_test_only": True, "clinical_validation": False, "scenarios": scenarios}


if __name__ == "__main__":
    print(json.dumps(demonstrate(), indent=2))
