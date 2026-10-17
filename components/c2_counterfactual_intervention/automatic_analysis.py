"""Automatic, non-prescriptive C1 sensitivity research on synthetic demonstration cases.

This is deliberately separate from the authorized real recommendation endpoint.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .c1_compat import C1Snapshot, next_categories
from .c1_predictors import C1PredictionUnavailable, RealC1HttpPredictor
from .educational_baskets import shopping_examples
from .guideline_references import research_guidance_for_age
from .official_prices import bundled_history, price_state
from .real_model_validation import _prediction, validation_snapshot


class AutomaticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: Literal["synthetic_5m", "synthetic_24m", "synthetic_59m"] = "synthetic_24m"
    budget_lkr: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_period: Literal["daily", "weekly", "monthly"] = "weekly"


def demonstration_snapshot(case_id: str) -> C1Snapshot:
    """Three invented age cases; no clinical record or user import is implied."""
    ages = {"synthetic_5m": 5, "synthetic_24m": 24, "synthetic_59m": 59}
    if case_id not in ages:
        raise ValueError("unsupported synthetic demonstration case")
    data = validation_snapshot().model_dump()
    age = ages[case_id]
    data["child_pseudonymous_id"] = f"SYNTHETIC-C2-{age}M"
    data["historical_baseline"]["age_months"] = age
    data["anthropometric"]["age_months"] = age
    data["provenance"] = "fully synthetic C2 demonstration input; not an observed child record"
    return C1Snapshot.model_validate(data)


def _guidance(age: int) -> dict:
    return research_guidance_for_age(age)


def _nonworsening_reasons(base, candidate) -> list[str]:
    reasons = []
    order = {"Normal": 0, "Moderate": 1, "Severe": 2}
    if order[candidate.severity] > order[base.severity]:
        reasons.append("predicted severity worsens")
    for name in ("underweight_probability", "stunting_probability"):
        if getattr(candidate, name) > getattr(base, name) + 1e-9:
            reasons.append(f"{name} increases")
    for name in ("MAM", "SAM"):
        if candidate.acute_probabilities[name] > base.acute_probabilities[name] + 1e-9:
            reasons.append(f"{name} model probability increases")
    return reasons


def load_automatic_baseline(case_id: str, predictor: RealC1HttpPredictor | None = None) -> dict:
    snapshot = demonstration_snapshot(case_id)
    if snapshot.historical_baseline["age_months"] < 6:
        return {"case_id": case_id, "snapshot_provenance": snapshot.provenance,
                "age_months": snapshot.historical_baseline["age_months"],
                "original_feeding": {}, "baseline": None,
                "guidance": _guidance(snapshot.historical_baseline["age_months"]),
                "clinical_use": False}
    predictor = predictor or RealC1HttpPredictor()
    if getattr(predictor, "source", None) != "GA-RGCA-v3":
        raise C1PredictionUnavailable("genuine C1 predictor required")
    output = predictor.predict(snapshot)
    if output.prediction_source != "GA-RGCA-v3" or output.mode != "PYTORCH" or output.clinical_use:
        raise C1PredictionUnavailable("genuine, nonclinical C1 baseline required")
    return {"case_id": case_id, "snapshot_provenance": snapshot.provenance,
            "age_months": snapshot.historical_baseline["age_months"],
            "original_feeding": {key: snapshot.ga_rgca_context[key] for key in ("meal_frequency", "dietary_diversity")},
            "baseline": _prediction(output), "guidance": _guidance(snapshot.historical_baseline["age_months"]),
            "clinical_use": False}


def run_automatic_analysis(request: AutomaticRequest, predictor: RealC1HttpPredictor | None = None) -> dict:
    """Score bounded hypothetical inputs with C1; never promote them to interventions."""
    snapshot = demonstration_snapshot(request.case_id)
    age = snapshot.historical_baseline["age_months"]
    if age < 6:
        return {
            "mode": "unsupported_age_no_prediction", "case_id": request.case_id,
            "snapshot_provenance": snapshot.provenance, "age_months": age,
            "model_version": None, "original_feeding": {}, "baseline": None,
            "candidates": [], "approved_intervention_cards": [],
            "budget": {"amount_lkr": str(request.budget_lkr) if request.budget_lkr is not None else None,
                       "period": request.budget_period, "affordability": "unresolved"},
            "guidance": _guidance(age), "published_price_examples": [],
            "shopping_examples": [],
            "methods": [{"name": name, "status": "not_run_age_inapplicable"}
                        for name in ("bounded_search", "dice", "face_graph")],
            "research_test_runs": [],
            "limitations": ["The required C1 meal-frequency category is inapplicable to this under-six-month demonstration case.",
                            "No C1 prediction or complementary-feeding counterfactual was generated.",
                            "Professional review is required."],
            "clinical_use": False,
        }
    predictor = predictor or RealC1HttpPredictor()
    if getattr(predictor, "source", None) != "GA-RGCA-v3":
        raise C1PredictionUnavailable("genuine C1 predictor required for automatic analysis")
    baseline = predictor.predict(snapshot)
    if baseline.prediction_source != "GA-RGCA-v3" or baseline.mode != "PYTORCH" or baseline.clinical_use:
        raise C1PredictionUnavailable("genuine, nonclinical C1 baseline required")
    guidance = _guidance(age)
    candidates = []
    seen = set()
    for changes in next_categories(snapshot):
        identity = tuple(sorted(changes.items()))
        if identity in seen:
            continue
        seen.add(identity)
        candidate = predictor.predict(snapshot, changes)
        if candidate.prediction_source != "GA-RGCA-v3" or candidate.mode != "PYTORCH" or candidate.clinical_use:
            raise C1PredictionUnavailable("genuine, nonclinical C1 candidate required")
        worsening = _nonworsening_reasons(baseline, candidate)
        unresolved = ["real-mode research authorization has not been supplied",
                      "local availability and clinical suitability are unknown",
                      "individual feeding practice and quantity require guideline review"]
        if baseline.uncertainty_flag or candidate.uncertainty_flag:
            unresolved.append("model uncertainty requires professional review")
        if request.budget_lkr is None:
            unresolved.append("family food budget is unknown")
        else:
            unresolved.append("reviewed intervention quantities and treatment-specific cost are unavailable; shopping examples do not establish intervention affordability")
        if candidate.predicted_malnutrition_type == baseline.predicted_malnutrition_type:
            unresolved.append("no categorical type change")
        food_options = []
        if "dietary_diversity" in changes:
            # Published category examples only; never a serving or approved meal plan.
            for row in bundled_history():
                if row.food_group in guidance["food_groups"] and row.evidence_status == "source_checked":
                    food_options.append({"food_name": row.food_name, "food_group": row.food_group,
                                         "guideline_section": guidance["reference"]["section"],
                                         "guideline_url": guidance["reference"]["url"],
                                         "status": "provisional_group_example_not_intervention",
                                         "quantity": None})
            food_options = food_options[:5]
        candidates.append({
            "changes": {key: {"from": snapshot.ga_rgca_context[key], "to": value} for key, value in changes.items()},
            "prediction": _prediction(candidate),
            "comparison": {"type_changed": candidate.predicted_malnutrition_type != baseline.predicted_malnutrition_type,
                           "severity_changed": candidate.severity != baseline.severity,
                           "underweight_probability_delta": round(candidate.underweight_probability - baseline.underweight_probability, 6),
                           "stunting_probability_delta": round(candidate.stunting_probability - baseline.stunting_probability, 6)},
            "disposition": "rejected_model_worsening" if worsening else "unresolved_for_intervention",
            "reasons": worsening + unresolved,
            "method": "bounded_search", "rank": None,
            "food_options": food_options, "indicative_incremental_cost_lkr": None,
            "affordability": "unresolved", "availability": "unknown",
            "professional_review_required": True,
        })
    # Ranking applies only to exploratory comparisons that pass model non-worsening.
    # Unknown policy/food evidence remains unresolved irrespective of rank.
    eligible = [item for item in candidates if item["disposition"] == "unresolved_for_intervention"]
    eligible.sort(key=lambda item: (len(item["changes"]), tuple(sorted((key, value["to"]) for key, value in item["changes"].items()))))
    for rank, item in enumerate(eligible, 1):
        item["rank"] = rank
    candidates.sort(key=lambda item: (item["rank"] is None, item["rank"] or 999,
                                      tuple(sorted(item["changes"]))))
    # DiCE and FACE execute only against the independent synthetic method facade.
    # An unapproved policy prevents their output from becoming cards. Their outputs
    # are never merged into the genuine C1 candidate list.
    from .c1_engine import run_c1
    from .supervisor_demo import demo_request
    research_test_runs = []
    for method in ("dice", "face_graph"):
        test_request = demo_request(method=method)
        test_request.snapshot = snapshot
        test_request.policy.approved_for_research = False
        test_request.food_planning = None
        try:
            test_result = run_c1(test_request)
            research_test_runs.append({"method": method, "status": "completed_test_only",
                                       "prediction_source": test_result.baseline["prediction_source"],
                                       "candidate_count": len(test_result.candidates) + len(test_result.rejected_or_unresolved),
                                       "approved_cards": 0,
                                       "note": "Synthetic method facade on the same invented input; no C1 model integration or research approval."})
        except (ImportError, C1PredictionUnavailable, ValueError) as exc:
            research_test_runs.append({"method": method, "status": "unavailable_test_only",
                                       "prediction_source": "SIMULATED_TEST_ONLY", "candidate_count": 0,
                                       "approved_cards": 0, "note": str(exc)})
    prices = bundled_history()
    return {
        "mode": "genuine_c1_model_comparison_only", "case_id": request.case_id,
        "snapshot_provenance": snapshot.provenance,
        "age_months": age, "model_version": baseline.model_version,
        "original_feeding": {key: snapshot.ga_rgca_context[key] for key in ("meal_frequency", "dietary_diversity")},
        "baseline": _prediction(baseline), "candidates": candidates,
        "approved_intervention_cards": [],
        "budget": {"amount_lkr": str(request.budget_lkr) if request.budget_lkr is not None else None,
                   "period": request.budget_period, "affordability": "unresolved"},
        "guidance": guidance,
        "shopping_examples": shopping_examples(age, guidance, request.budget_lkr, request.budget_period),
        "published_price_examples": [{"food_id": row.food_id, "food_name": row.food_name,
                                      "food_group": row.food_group, "amount_lkr": str(row.amount_lkr),
                                      "quantity": str(row.quantity), "unit": row.unit,
                                      "source_url": row.report_url, "source_locator": row.source_locator,
                                      "market_coverage": row.market_coverage,
                                      "observation_start": row.observation_start.isoformat(),
                                      "observation_end": row.observation_end.isoformat(),
                                      "reference_status": price_state(row)} for row in prices
                                     if row.evidence_status == "source_checked" and row.price_class == "retail"],
        "methods": [{"name": "bounded_search", "status": "genuine_C1_evaluation"},
                    {"name": "dice", "status": "research_test_only_not_integrated_with_C1"},
                    {"name": "face_graph", "status": "research_test_only_not_integrated_with_C1"}],
        "research_test_runs": research_test_runs,
        "limitations": ["Synthetic case inputs are not observed research records.",
                        "Model differences do not establish treatment effects.",
                        "Shopping examples have period-matched indicative costs, but no reviewed age-specific child quantities or approved treatment costs are available.",
                        "DCS prices are Colombo references, not verified Kalmunai prices.",
                        "Authorization, clinical suitability and local availability remain unresolved."],
        "clinical_use": False,
    }
