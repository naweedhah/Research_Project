"""Run every invented case through genuine C1, then the existing C2 engine.

Usage: python -m components.c2_counterfactual_intervention.live_case_validation_v2
Requires C1_INFERENCE_URL and loaded GA-RGCA-v3 artifacts. No demo fallback.
"""

from __future__ import annotations

import json
import sys
import hashlib

from .c1_predictors import C1PredictionUnavailable, RealC1HttpPredictor
from .live_case_library_v2 import live_case_library
from .manual_c1_validation import ManualC1Request, manual_snapshot
from .nutrition_scenarios_v2 import OriginalAssessment, ScenarioRequest, generate_scenarios


CATEGORIES = ("Normal", "Underweight", "Stunting", "MAM", "SAM")


def run_live_cases(predictor: RealC1HttpPredictor | None = None) -> dict:
    predictor = predictor or RealC1HttpPredictor()
    if getattr(predictor, "source", None) != "GA-RGCA-v3":
        raise C1PredictionUnavailable("genuine GA-RGCA-v3 predictor required")
    rows = []
    for case in live_case_library()["cases"]:
        request = ManualC1Request.model_validate(case["input"])
        snapshot = manual_snapshot(request)
        payload = snapshot.predict_payload()
        if payload["allow_demo"] is not False:
            raise ValueError("C1 demo fallback must be disabled")
        prediction = predictor.predict(snapshot)
        assessment = OriginalAssessment(
            model_version=prediction.model_version,
            prediction_source=prediction.prediction_source,
            predicted_malnutrition_type=prediction.predicted_malnutrition_type,
            severity=prediction.severity,
            uncertainty_flag=prediction.uncertainty_flag,
            clinical_use=False,
            input_fingerprint=hashlib.sha256(json.dumps(payload, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest(),
            provenance="live_c1_baseline",
        )
        scenario = ScenarioRequest.model_validate({
            "contract_version": "c2-diet-scenarios-v2",
            "age_months": request.age_months,
            "original_c1": assessment.model_dump(),
            "feeding": {"meal_frequency": request.meal_frequency,
                        "dietary_diversity": request.dietary_diversity,
                        "food_groups": case["food_groups"], "provenance": "unverified"},
            "household": {"budget_lkr": request.budget_lkr,
                          "budget_period": request.budget_period,
                          "budget_provenance": "user_reported" if request.budget_lkr is not None else "unknown",
                          "allergy_status": "unknown", "excluded_food_ids": [],
                          "preparation": "unknown", "local_availability": {}},
            "method": "compare_all", "research_algorithm_demo": True,
        })
        result = generate_scenarios(scenario)
        if result["original_c1"] != assessment.model_dump(mode="json") or result["c1_candidate_calls"] != 0:
            raise ValueError("C2 changed the original C1 assessment or made untracked candidate calls")
        rows.append({"case_id": case["case_id"], "input_name": case["name"],
                     "model_version": prediction.model_version,
                     "prediction_source": prediction.prediction_source,
                     "c1_predicted_category": prediction.predicted_malnutrition_type,
                     "c1_severity": prediction.severity,
                     "c1_uncertainty_flag": prediction.uncertainty_flag,
                     "assessment_review_needed": (
                         prediction.predicted_malnutrition_type != "Normal"
                         or prediction.severity == "Severe"
                         or prediction.uncertainty_flag
                     ),
                     "c2_candidate_count": result["candidate_count"],
                     "c2_research_test_rank_count": len(result.get("software_test_ranked", [])),
                     "c2_verified_feasible_count": len(result["ranked_cards"]),
                     "c2_status": "research_test; individual suitability and local availability unresolved"})
    observed = sorted({row["c1_predicted_category"] for row in rows})
    return {"mode": "live_c1_invented_case_validation", "c1_calls": len(rows),
            "allow_demo": False, "cases": rows,
            "observed_categories": observed,
            "unobserved_categories": sorted(set(CATEGORIES) - set(observed)),
            "clinical_use": False}


def main() -> int:
    try:
        report = run_live_cases()
    except (C1PredictionUnavailable, ValueError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
