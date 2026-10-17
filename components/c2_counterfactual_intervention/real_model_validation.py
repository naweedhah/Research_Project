"""Read-only GA-RGCA sensitivity check using a fixed, fully synthetic C2 fixture.

This workflow never evaluates intervention feasibility or issues recommendation cards.
It requires the genuine C1 HTTP adapter and rejects demo model responses.
"""

import argparse
import hashlib
import json

from .c1_compat import C1Snapshot, next_categories
from .c1_predictors import C1PredictionUnavailable, RealC1HttpPredictor


def validation_snapshot() -> C1Snapshot:
    """Invented values matching C1's deployment-test categories, not a child record."""
    return C1Snapshot(
        child_pseudonymous_id="SYNTHETIC-C2-MODEL-VALIDATION",
        visit_number=1,
        visit_date="2025-06-01",
        anthropometric={"age_months": 24, "sex": "Female", "height_cm": 80,
                        "weight_kg": 10, "birth_weight_kg": 2.8},
        socioeconomic={"household_size": 4},
        historical_baseline={"source": "baseline_assessment",
                             "assessment_date": "2025-06-01T00:00:00",
                             "horizon_end_date": "2026-06-01T00:00:00",
                             "age_months": 24, "sex": "Female", "height_cm": 80,
                             "weight_kg": 10, "birth_weight_kg": 2.8},
        ga_rgca_context={
            "maternal_age_years": 28, "maternal_education": "O/L passed",
            "household_income_range": "Rs.20,000 to Rs. 50,000",
            "father_occupation": "Manual worker", "mother_occupation": "Housewife",
            "exclusive_breastfeeding": "Yes", "breastfeeding_duration": "More than 6 months",
            "complementary_feeding_timing": "After 6 months",
            "meal_frequency": "3 meals/day", "dietary_diversity": "2 to 5 varieties",
            "triposha_supplementation": "No", "vitamin_supplementation": "Yes",
        },
        provenance="fully synthetic C2 model-validation fixture; values adapted from C1 deployment test",
    )


def standalone_snapshot(case_id: str) -> C1Snapshot:
    """One immutable C1-shaped context shared by standalone and real comparisons."""
    ages = {"synthetic_5m": 5, "synthetic_24m": 24, "synthetic_59m": 59}
    if case_id not in ages:
        raise ValueError("unsupported standalone demonstration case")
    age = ages[case_id]
    data = validation_snapshot().model_dump()
    data["child_pseudonymous_id"] = f"SYNTHETIC-C2-{age}M"
    data["historical_baseline"]["age_months"] = age
    data["anthropometric"]["age_months"] = age
    data["ga_rgca_context"]["dietary_diversity"] = "2 to 5 varieties"
    data["provenance"] = "invented C2 standalone software fixture; no observed child record"
    return C1Snapshot.model_validate(data)


def standalone_input_fingerprint(case_id: str) -> str:
    payload = standalone_snapshot(case_id).predict_payload()
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _prediction(output) -> dict:
    if (output.prediction_source != "GA-RGCA-v3" or output.model_version != "GA-RGCA-v3"
            or output.mode != "PYTORCH" or output.clinical_use):
        raise ValueError("genuine, nonclinical GA-RGCA-v3 output required")
    return {
        "predicted_malnutrition_type": output.predicted_malnutrition_type,
        "acute_status": output.acute_status,
        "severity": output.severity,
        "underweight_probability": output.underweight_probability,
        "stunting_probability": output.stunting_probability,
        "acute_probabilities": output.acute_probabilities,
        "severity_probabilities": output.severity_probabilities,
        "uncertainty_flag": output.uncertainty_flag,
        "model_version": output.model_version,
        "prediction_source": output.prediction_source,
        "prediction_task": output.prediction_task,
        "clinical_use": output.clinical_use,
        "data_limitations": output.data_limitations,
    }


def run_validation(predictor: RealC1HttpPredictor | None = None) -> dict:
    """Call C1 for the baseline and each bounded feeding variant, with no fallback."""
    snapshot = validation_snapshot()
    predictor = predictor or RealC1HttpPredictor()
    if predictor.source != "GA-RGCA-v3":
        raise ValueError("genuine GA-RGCA predictor required")
    original = snapshot.ga_rgca_context
    baseline = predictor.predict(snapshot)
    variants = []
    for changes in next_categories(snapshot):
        candidate = predictor.predict(snapshot, changes)
        flags = ["Research authorization and food feasibility have not been established"]
        if baseline.uncertainty_flag or candidate.uncertainty_flag:
            flags.append("Model uncertainty requires professional review")
        if candidate.predicted_malnutrition_type == baseline.predicted_malnutrition_type:
            flags.append("No categorical type change")
        if candidate.underweight_probability > baseline.underweight_probability:
            flags.append("Underweight model probability increased")
        if candidate.stunting_probability > baseline.stunting_probability:
            flags.append("Stunting model probability increased")
        for category in ("MAM", "SAM"):
            if candidate.acute_probabilities[category] > baseline.acute_probabilities[category]:
                flags.append(f"{category} model probability increased")
        variants.append({
            "changes": {name: {"from": original[name], "to": value} for name, value in changes.items()},
            "prediction": _prediction(candidate),
            "comparison": {
                "type_changed": candidate.predicted_malnutrition_type != baseline.predicted_malnutrition_type,
                "severity_changed": candidate.severity != baseline.severity,
                "underweight_probability_delta": round(candidate.underweight_probability - baseline.underweight_probability, 6),
                "stunting_probability_delta": round(candidate.stunting_probability - baseline.stunting_probability, 6),
            },
            "disposition": "unresolved_for_intervention",
            "reasons": flags,
        })
    return {
        "banner": "GENUINE C1 MODEL VALIDATION ON SYNTHETIC INPUTS - NOT AN INTERVENTION RECOMMENDATION",
        "fixture_provenance": snapshot.provenance,
        "original_feeding": {key: original[key] for key in ("meal_frequency", "dietary_diversity")},
        "baseline": _prediction(baseline),
        "variants": variants,
        "intervention_cards": [],
        "clinical_use": False,
        "limitations": [
            "Hypothetical inputs and model outputs do not establish treatment effects.",
            "No approved C2 real-mode policy, local availability, clinical suitability or household affordability is implied.",
        ],
    }


def _standalone_policy_reasons(baseline, candidate) -> tuple[list[str], list[str]]:
    """Mirror the existing C2 non-worsening and category rules, without approval."""
    from .automatic_analysis import _nonworsening_reasons

    rejected = _nonworsening_reasons(baseline, candidate)
    unresolved = []
    if baseline.uncertainty_flag or candidate.uncertainty_flag:
        unresolved.append("model uncertainty requires review")
    from .c1_engine import C1ResearchPolicy, _model_policy_reason
    # No real research policy is supplied. Model-only comparison cannot issue cards.
    comparison_policy = C1ResearchPolicy(
        policy_id="MODEL-COMPARISON-ONLY", approved_for_research=False,
        allowed_type_transitions=[("Underweight", "Normal"), ("MAM", "Underweight"),
                                  ("MAM", "Normal"), ("SAM", "MAM"),
                                  ("Stunting", "MAM")],
    )
    model_reason = _model_policy_reason(baseline, candidate, comparison_policy)
    if candidate.predicted_malnutrition_type == baseline.predicted_malnutrition_type:
        rejected.append("no approved categorical improvement")
    elif (baseline.predicted_malnutrition_type, candidate.predicted_malnutrition_type) not in comparison_policy.allowed_type_transitions:
        rejected.append("type transition not approved")
    if model_reason and "uncertainty" not in model_reason and model_reason not in rejected:
        rejected.append(model_reason)
    unresolved.extend([
        "real-mode research authorization has not been supplied",
        "individual clinical suitability and local availability are unknown",
        "reviewed feeding practice and intervention affordability are unavailable",
    ])
    return rejected, unresolved


def run_standalone_validation(case_id: str, predictor: RealC1HttpPredictor | None = None) -> dict:
    """Optional genuine C1 comparison of the exact standalone profile; no cards."""
    snapshot = standalone_snapshot(case_id)
    age = snapshot.historical_baseline["age_months"]
    if age < 6:
        return {"connection": "not_attempted_age_inapplicable", "case_id": case_id,
                "input_fingerprint": standalone_input_fingerprint(case_id),
                "profile": {"test_id": snapshot.child_pseudonymous_id, "age_months": age},
                "baseline": None, "candidates": [], "model_version": None,
                "prediction_source": None, "clinical_use": False,
                "limitations": ["No complementary-feeding model comparison below six months."]}
    predictor = predictor or RealC1HttpPredictor()
    if getattr(predictor, "source", None) != "GA-RGCA-v3":
        raise C1PredictionUnavailable("genuine C1 predictor required")
    original_payload = snapshot.predict_payload()
    if original_payload["allow_demo"] is not False:
        raise ValueError("demo predictions must remain disabled")
    baseline = predictor.predict(snapshot)
    base_display = _prediction(baseline)
    variants = []
    for changes in next_categories(snapshot):
        candidate_payload = snapshot.predict_payload(changes)
        expected = dict(original_payload)
        expected["ga_rgca_context"] = {**original_payload["ga_rgca_context"], **changes}
        if candidate_payload != expected or candidate_payload["allow_demo"] is not False:
            raise ValueError("hypothetical input changed non-feeding context")
        candidate = predictor.predict(snapshot, changes)
        display = _prediction(candidate)
        rejected, unresolved = _standalone_policy_reasons(baseline, candidate)
        variants.append({
            "changes": {name: {"from": snapshot.ga_rgca_context[name], "to": value}
                        for name, value in changes.items()},
            "prediction": display,
            "probability_delta": {
                "underweight": round(candidate.underweight_probability - baseline.underweight_probability, 6),
                "stunting": round(candidate.stunting_probability - baseline.stunting_probability, 6),
                "acute": {name: round(candidate.acute_probabilities[name] - baseline.acute_probabilities[name], 6)
                          for name in ("Normal", "MAM", "SAM")},
            },
            "model_policy_result": "rejected" if rejected else "unresolved",
            "rejected_reasons": rejected,
            "unresolved_reasons": unresolved,
            "only_feeding_fields_changed": True,
        })
    return {"connection": "verified", "case_id": case_id,
            "input_fingerprint": standalone_input_fingerprint(case_id),
            "profile": {"test_id": snapshot.child_pseudonymous_id, "age_months": age,
                        "historical_baseline": snapshot.historical_baseline,
                        "original_feeding": {key: snapshot.ga_rgca_context[key]
                                             for key in ("meal_frequency", "dietary_diversity")}},
            "baseline": base_display, "candidates": variants,
            "model_version": baseline.model_version, "prediction_source": baseline.prediction_source,
            "clinical_use": False,
            "limitations": ["Invented child profile; genuine model inference is not external validation.",
                            "Model differences do not establish treatment effects or approve intervention cards.",
                            "Research authorization, suitability, local availability and intervention costs remain unresolved."]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Genuine C1 model validation on a fixed synthetic C2 fixture")
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(run_validation(), indent=args.indent))


if __name__ == "__main__":
    main()
