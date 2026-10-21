"""Repeatable, nonclinical standalone plus genuine-C1 evidence report."""
from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from .c1_predictors import C1PredictionUnavailable
from .real_model_validation import run_standalone_validation
from .standalone_demo import StandaloneRequest, run_standalone


def build_report(case_id: str = "synthetic_24m", budget_lkr: Decimal = Decimal("1500")) -> str:
    standalone = run_standalone(StandaloneRequest(case_id=case_id, budget_lkr=budget_lkr))
    lines = ["# C2 supervisor validation report", "",
             "Research demonstration only. All child inputs are invented software fixtures.",
             "Genuine C1 inference is separate from simulated C2 acceptance; neither is clinical validation.", "",
             "## Standalone algorithms", "",
             f"- Case: {case_id}; test ID: {standalone['profile']['test_id']}; budget: LKR {budget_lkr} weekly.",
             f"- Exact model-input SHA-256: `{standalone['input_fingerprint']}`; budget is excluded from model input.",
             f"- Research-test cards: {len(standalone['cards'])}; genuine C1 required: {standalone['c1_required']}."]
    for method in standalone["methods"]:
        lines.append(f"- {method['name']}: {method['eligible_count']} test-eligible, {method['rejected_count']} rejected or unresolved; source {method['mode']}.")
    for card in standalone["cards"]:
        lines.append(f"- Rank {card['rank']}: {card['changes']}; methods {', '.join(card['supporting_methods'])}; {card['status']} only.")
    lines.extend(["", "## Food cost and schedule", "",
                  "Shopping quantities are household price scenarios, not child portions or treatment plans."])
    for plan in standalone["food_plans"]:
        lines.append(f"- #{plan['rank']} {plan['title']}: LKR {plan['estimated_total_lkr']} / {plan['cost_period']}; {plan['budget_fit']}; {len(plan['schedule'])} illustrative days; {plan['group_count']} reviewed food groups.")
    lines.extend(["- Prices: DCS Colombo District reference records; Kalmunai prices and local availability are unverified.",
                  "", "## Genuine GA-RGCA-v3 inference", ""])
    try:
        real = run_standalone_validation(case_id)
    except C1PredictionUnavailable as exc:
        lines.append(f"- C1 status: UNAVAILABLE ({exc}). Standalone cards above remain research-test only.")
    else:
        if real["input_fingerprint"] != standalone["input_fingerprint"]:
            raise ValueError("standalone and genuine C1 input fingerprints disagree")
        lines.append(f"- C1 status: {real['connection']}; model: {real['model_version']}; source: {real['prediction_source']}; clinical use: {real['clinical_use']}.")
        if real["baseline"]:
            baseline = real["baseline"]
            lines.append(f"- Baseline: {baseline['predicted_malnutrition_type']}; severity {baseline['severity']}; uncertainty {baseline['uncertainty_flag']}; underweight {baseline['underweight_probability']:.6f}; stunting {baseline['stunting_probability']:.6f}; acute {baseline['acute_probabilities']}.")
        for index, item in enumerate(real["candidates"], 1):
            prediction = item["prediction"]
            lines.extend([f"- Candidate {index}: {item['changes']}; only feeding fields changed: {item['only_feeding_fields_changed']}.",
                          f"  - Actual prediction: {prediction['predicted_malnutrition_type']}; severity {prediction['severity']}; uncertainty {prediction['uncertainty_flag']}; underweight {prediction['underweight_probability']:.6f}; stunting {prediction['stunting_probability']:.6f}; acute {prediction['acute_probabilities']}.",
                          f"  - Probability deltas: {item['probability_delta']}.",
                          f"  - Model-policy result: {item['model_policy_result']}; reasons: {'; '.join(item['rejected_reasons']) or 'none'}.",
                          f"  - Unresolved evidence: {'; '.join(item['unresolved_reasons'])}."])
    lines.extend(["", "## Remaining research boundaries", "",
                  "- No real-mode C2 research authorization or treatment-effect evidence was supplied.",
                  "- Individual clinical suitability, programme eligibility, feeding practice, local availability and household affordability require independent review.",
                  "- Run verification: `py -m pytest components/c2_counterfactual_intervention/tests -q`; in the dashboard run `npm.cmd test -- --run` and `npm.cmd run build`.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create nonclinical C2 supervisor evidence report")
    parser.add_argument("--case-id", choices=("synthetic_5m", "synthetic_24m", "synthetic_59m"), default="synthetic_24m")
    parser.add_argument("--budget-lkr", type=Decimal, default=Decimal("1500"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.case_id, args.budget_lkr)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(args.output)
    else:
        print(report)


if __name__ == "__main__":
    main()
