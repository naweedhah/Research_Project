"""Local, non-prescriptive C1 sensitivity audit on linked PHM research rows.

The source workbook is read in memory. Names, source identifiers, and raw rows
are never written to the report. A private result file is optional and must
remain outside Git; it contains de-identified model inputs for local review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .automatic_analysis import _nonworsening_reasons
from .c1_compat import C1Snapshot, DIVERSITY, MEALS
from .c1_engine import C1ResearchPolicy, _model_policy_reason
from .c1_predictors import C1PredictionUnavailable, RealC1HttpPredictor

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_TRANSITIONS = [("Underweight", "Normal"), ("MAM", "Underweight"),
                ("MAM", "Normal"), ("SAM", "MAM"), ("Stunting", "MAM")]


def linked_rows(path: Path) -> list[dict[str, str | None]]:
    """Read only the linked, name-free PHM sheet using Python's standard library."""
    with zipfile.ZipFile(path) as archive:
        strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in item.findall(".//m:t", _NS))
                       for item in root.findall("m:si", _NS)]
        rows: list[dict[str, str | None]] = []
        with archive.open("xl/worksheets/sheet1.xml") as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                if not element.tag.endswith("}row"):
                    continue
                row: dict[str, str | None] = {}
                for cell in element.findall("m:c", _NS):
                    address = cell.attrib.get("r", "")
                    match = re.match(r"[A-Z]+", address)
                    if not match:
                        continue
                    value = cell.find("m:v", _NS)
                    inline = cell.find("m:is", _NS)
                    if cell.attrib.get("t") == "s" and value is not None:
                        parsed = strings[int(value.text or "0")]
                    elif inline is not None:
                        parsed = "".join(t.text or "" for t in inline.findall(".//m:t", _NS))
                    else:
                        parsed = value.text if value is not None else None
                    row[match.group()] = parsed
                rows.append(row)
                element.clear()
    if not rows:
        raise ValueError("linked workbook has no header")
    header = rows[0]
    required = {"Link_Quality", "Age_months_2025", "Height_cm_2025", "Weight_kg_2025",
                "Meal_Frequency_per_Day_2025", "Dietary_Diversity_2025"}
    if not required.issubset(set(header.values())):
        raise ValueError("linked workbook does not have the expected PHM 2025 columns")
    return [{name: row.get(column) for column, name in header.items() if name}
            for row in rows[1:]]


def _number(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (ValueError, TypeError):
        return None


def eligibility_reasons(row: dict[str, str | None]) -> list[str]:
    reasons = []
    age = _number(row.get("Age_months_2025"))
    if age is None or not 6 <= age <= 59:
        reasons.append("age_outside_6_59_or_missing")
    if row.get("Link_Quality") != "Good":
        reasons.append("link_not_good")
    if any((_number(row.get(name)) or 0) <= 0 for name in ("Height_cm_2025", "Weight_kg_2025")):
        reasons.append("historical_growth_missing")
    if row.get("Implausible_Z_Flag_2025") not in (None, "0"):
        reasons.append("implausible_historical_growth")
    if row.get("Meal_Frequency_per_Day_2025") not in MEALS or row.get("Dietary_Diversity_2025") not in DIVERSITY:
        reasons.append("feeding_category_incompatible")
    if (row.get("Meal_Frequency_per_Day_2025") == MEALS[-1]
            and row.get("Dietary_Diversity_2025") == DIVERSITY[-1]):
        reasons.append("no_upward_feeding_category")
    return reasons


def _recorded(value: str | None) -> str | None:
    return value if value not in (None, "", "Unknown", "Not applicable") else None


def snapshot_from_row(row: dict[str, str | None], case_id: str) -> C1Snapshot:
    """Map only source values; missing clinical/context fields remain missing."""
    if eligibility_reasons(row):
        raise ValueError("PHM row is not eligible for model comparison")
    age = _number(row.get("Age_months_2025"))
    height = _number(row.get("Height_cm_2025"))
    weight = _number(row.get("Weight_kg_2025"))
    acute = _recorded(row.get("Acute_Malnutrition_2025"))
    birth_g = _number(row.get("Birth_Weight_g"))
    history = {
        "source": "linked_phm_2025_research_record",
        "age_months": age, "height_cm": height, "weight_kg": weight,
        "sex": _recorded(row.get("Sex")),
        "birth_weight_kg": birth_g / 1000 if birth_g is not None else None,
        "underweight": _recorded(row.get("Underweight_2025")),
        "stunting": _recorded(row.get("Stunting_2025")),
        "mam": None if acute is None else int(acute == "MAM"),
        "sam": None if acute is None else int(acute == "SAM"),
    }
    context = {
        "maternal_age_years": _number(row.get("Maternal_Age_years_2025")),
        "maternal_education": _recorded(row.get("Maternal_Education")),
        "household_income_range": _recorded(row.get("Household_Income_Range_2025")),
        "father_occupation": _recorded(row.get("Father_Occupation")),
        "mother_occupation": _recorded(row.get("Mother_Occupation")),
        "exclusive_breastfeeding": _recorded(row.get("Exclusive_Breastfeeding")),
        "breastfeeding_duration": _recorded(row.get("Breastfeeding_Duration_2025")),
        "complementary_feeding_timing": _recorded(row.get("Complementary_Feeding_Timing_2025")),
        "meal_frequency": row["Meal_Frequency_per_Day_2025"],
        "dietary_diversity": row["Dietary_Diversity_2025"],
        "triposha_supplementation": _recorded(row.get("Triposha_Supplementation_2025")),
        "vitamin_supplementation": _recorded(row.get("Vitamin_Supplementation_2025")),
    }
    return C1Snapshot(
        child_pseudonymous_id=case_id, visit_number=0,
        anthropometric={"age_months": age, "sex": history["sex"],
                        "height_cm": height, "weight_kg": weight,
                        "birth_weight_kg": history["birth_weight_kg"]},
        socioeconomic={"household_size": _number(row.get("Family_Size_2025"))},
        historical_baseline=history, ga_rgca_context=context,
        provenance="linked PHM research workbook; 2025 baseline; feeding field observation provenance unverified",
    )


def upward_candidates(snapshot: C1Snapshot) -> list[tuple[dict[str, str], bool]]:
    """Evaluate all upward categories; mark non-adjacent paths as exploratory."""
    meals = snapshot.ga_rgca_context["meal_frequency"]
    diversity = snapshot.ga_rgca_context["dietary_diversity"]
    meal_options = MEALS[MEALS.index(meals) + 1:]
    diversity_options = DIVERSITY[DIVERSITY.index(diversity) + 1:]
    groups = [{"meal_frequency": m} for m in meal_options]
    groups += [{"dietary_diversity": d} for d in diversity_options]
    groups += [{"meal_frequency": m, "dietary_diversity": d}
               for m in meal_options for d in diversity_options]
    return [(group, all((MEALS.index(value) - MEALS.index(meals) == 1 if key == "meal_frequency"
                         else DIVERSITY.index(value) - DIVERSITY.index(diversity) == 1)
                        for key, value in group.items())) for group in groups]


def compare(snapshot: C1Snapshot, predictor: RealC1HttpPredictor) -> dict:
    from .real_model_validation import _prediction

    baseline = predictor.predict(snapshot)
    policy = C1ResearchPolicy(policy_id="MODEL-COMPARISON-ONLY", approved_for_research=False,
                              allowed_type_transitions=_TRANSITIONS)
    original = snapshot.predict_payload()
    candidates = []
    for changes, adjacent in upward_candidates(snapshot):
        changed = snapshot.predict_payload(changes)
        expected = {**original, "ga_rgca_context": {**original["ga_rgca_context"], **changes}}
        if changed != expected or changed["allow_demo"] is not False:
            raise ValueError("non-feeding input changed")
        output = predictor.predict(snapshot, changes)
        deltas = {
            "underweight": round(output.underweight_probability - baseline.underweight_probability, 6),
            "stunting": round(output.stunting_probability - baseline.stunting_probability, 6),
            "MAM": round(output.acute_probabilities["MAM"] - baseline.acute_probabilities["MAM"], 6),
            "SAM": round(output.acute_probabilities["SAM"] - baseline.acute_probabilities["SAM"], 6),
        }
        worsening = _nonworsening_reasons(baseline, output)
        policy_reason = _model_policy_reason(baseline, output, policy)
        reasons = list(worsening)
        if policy_reason and policy_reason not in reasons:
            reasons.append(policy_reason)
        if not adjacent:
            reasons.append("non-adjacent transition is exploratory, outside existing C2 candidate policy")
        candidates.append({
            "changes": {key: {"from": original["ga_rgca_context"][key], "to": value}
                        for key, value in changes.items()},
            "prediction": _prediction(output), "probability_delta": deltas,
            "model_rule_pass": not reasons, "reasons": reasons,
            "improvement_signal": any(value < 0 for value in deltas.values()),
            "mixed_tradeoff": any(value < 0 for value in deltas.values()) and any(value > 0 for value in deltas.values()),
            "worsening_signal": any(value > 0 for value in deltas.values()),
            "adjacent_policy_transition": adjacent,
            "only_feeding_fields_changed": True,
            "research_authorized": False, "clinical_use": False,
        })
    return {"case_id": snapshot.child_pseudonymous_id, "snapshot": snapshot.model_dump(mode="json"),
            "baseline": _prediction(baseline), "candidates": candidates,
            "model_version": baseline.model_version,
            "input_provenance": snapshot.provenance,
            "research_authorized": False, "clinical_use": False}


def compare_with_retry(snapshot: C1Snapshot, predictor: RealC1HttpPredictor) -> dict:
    """Retry a transient C1 transport failure; never reuse a partial comparison."""
    for attempt in range(3):
        try:
            return compare(snapshot, predictor)
        except C1PredictionUnavailable:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def discover(source: Path, *, limit: int | None = None, at_risk_first: bool = False,
             predictor: RealC1HttpPredictor | None = None,
             prior_cases: list[dict] | None = None, progress=None,
             workers: int = 1) -> dict:
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    rows = linked_rows(source)
    exclusions: Counter[str] = Counter()
    eligible = []
    for row in rows:
        reasons = eligibility_reasons(row)
        if reasons:
            exclusions.update(reasons)
        else:
            eligible.append(row)
    if at_risk_first:
        eligible.sort(key=lambda row: row.get("Malnutrition_Type_2025") in (None, "Normal"))
    predictor = predictor or RealC1HttpPredictor()
    if getattr(predictor, "source", None) != "GA-RGCA-v3":
        raise ValueError("genuine C1 predictor required for PHM discovery")
    selected = eligible[:limit] if limit is not None else eligible
    cases = list(prior_cases or [])
    if len(cases) > len(selected):
        raise ValueError("resume file has more cases than selected profiles")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for offset in range(len(cases), len(selected), workers):
            batch = selected[offset:offset + workers]
            futures = [pool.submit(compare_with_retry, snapshot_from_row(row, f"PHM-LOCAL-{offset + position + 1:04d}"), predictor)
                       for position, row in enumerate(batch)]
            for future in futures:
                cases.append(future.result())
                if progress is not None and len(cases) % 10 == 0:
                    progress(cases)
                print(f"Compared {len(cases)}/{len(selected)} eligible profiles", flush=True)
    all_candidates = [candidate for case in cases for candidate in case["candidates"]]
    profiles_with_pass = sum(any(candidate["model_rule_pass"] for candidate in case["candidates"])
                             for case in cases)
    counts = {
        "total_linked_profiles": len(rows), "technically_eligible_profiles": len(eligible),
        "profiles_examined_with_c1": len(cases), "genuine_c1_baselines": len(cases),
        "candidates_evaluated": len(all_candidates),
        "improvement_signals": sum(c["improvement_signal"] for c in all_candidates),
        "model_rule_passing": sum(c["model_rule_pass"] for c in all_candidates),
        "profiles_with_model_rule_pass": profiles_with_pass,
        "mixed_tradeoffs": sum(c["mixed_tradeoff"] for c in all_candidates),
        "worsening_signals": sum(c["worsening_signal"] for c in all_candidates),
        "uncertainty_exclusions": sum("model uncertainty requires review" in c["reasons"] for c in all_candidates),
        "research_authorized": 0,
        "unresolved_feasibility": len(all_candidates),
    }
    return {"source_name": source.name, "source_sha256": source_hash,
            "scan_order": "2025 source risk first" if at_risk_first else "source row order",
            "complete_cohort_scan": len(cases) == len(eligible), "exclusions": dict(exclusions),
            "counts": counts,
            "scanned_candidate_pass_rate": (counts["model_rule_passing"] / len(all_candidates)
                                            if all_candidates else None),
            "whole_cohort_pass_rate": (counts["model_rule_passing"] / len(all_candidates)
                                       if all_candidates and len(cases) == len(eligible) else None),
            "whole_cohort_profile_pass_rate": (profiles_with_pass / len(eligible)
                                               if eligible and len(cases) == len(eligible) else None),
            "feeding_provenance": "source workbook does not verify direct observation; do not present as measured",
            "cases": cases}


def public_report(result: dict) -> str:
    """Publish aggregate evidence only; keep de-identified inputs in local storage."""
    counts = result["counts"]
    cases = result["cases"]
    pairs = [(case, candidate) for case in cases for candidate in case["candidates"]]
    candidate_rate = result["scanned_candidate_pass_rate"]
    profile_rate = result.get("whole_cohort_profile_pass_rate")
    lines = [
        "# PHM / GA-RGCA-v3 model comparison audit", "",
        "Research model sensitivity only; no intervention or clinical approval.",
        "The source workbook does not establish direct observation of the feeding fields.", "",
        f"- Source: `{result['source_name']}`; SHA-256 `{result['source_sha256']}`.",
        f"- Scan order: {result['scan_order']}; complete eligible cohort: {result['complete_cohort_scan']}.",
        f"- Linked profiles: {counts['total_linked_profiles']}; technically eligible: {counts['technically_eligible_profiles']}.",
        f"- Genuine C1 baselines: {counts['genuine_c1_baselines']}; candidates: {counts['candidates_evaluated']}.",
        f"- Improvement signals: {counts['improvement_signals']}; model-rule passes: {counts['model_rule_passing']} across {counts['profiles_with_model_rule_pass']} profiles.",
        f"- Mixed trade-offs: {counts['mixed_tradeoffs']}; candidates with worsening: {counts['worsening_signals']}.",
        f"- Uncertainty exclusions: {counts['uncertainty_exclusions']}; research-authorized: 0; feasibility unresolved: {counts['unresolved_feasibility']}.",
        f"- Candidate model-rule pass rate: {candidate_rate:.4%}; denominator {counts['candidates_evaluated']} evaluated candidates."
        if candidate_rate is not None else "- Candidate model-rule pass rate: no candidates evaluated.",
        f"- Eligible-profile model-rule pass rate: {profile_rate:.4%} across {counts['technically_eligible_profiles']} eligible profiles."
        if profile_rate is not None else
        "- Eligible-profile model-rule pass rate: pending the complete cohort scan.",
        "- Exclusion counts can overlap: " + json.dumps(result["exclusions"], sort_keys=True) + ".",
        "", "## Reproducible comparison examples", "",
    ]

    def example(label: str, matches: list[tuple[dict, dict]], maximum: int = 1) -> None:
        lines.append(f"### {label}")
        lines.append("")
        if not matches:
            lines.append("No matching case in the examined profiles.")
        for case, candidate in matches[:maximum]:
            base = case["baseline"]
            changed = candidate["prediction"]
            lines.extend([
                f"- Case alias: `{case['case_id']}`; model `{case['model_version']}`; source feeding observation status **unverified**.",
                "- Feeding change: " + json.dumps(candidate["changes"], sort_keys=True) + ".",
                "- Baseline probabilities (underweight, stunting, MAM, SAM): " +
                str((base["underweight_probability"], base["stunting_probability"],
                     base["acute_probabilities"]["MAM"], base["acute_probabilities"]["SAM"])) + ".",
                "- Candidate probabilities (same order): " +
                str((changed["underweight_probability"], changed["stunting_probability"],
                     changed["acute_probabilities"]["MAM"], changed["acute_probabilities"]["SAM"])) + ".",
                f"- Type / severity / uncertainty: {base['predicted_malnutrition_type']} / {base['severity']} / {base['uncertainty_flag']}"
                f" → {changed['predicted_malnutrition_type']} / {changed['severity']} / {changed['uncertainty_flag']}.",
                "- Probability deltas: " + json.dumps(candidate["probability_delta"], sort_keys=True) + ".",
                f"- Model-rule pass: {candidate['model_rule_pass']}; reasons: " +
                ("; ".join(candidate["reasons"]) or "none at model-comparison stage") + ".",
                "- Research authorization, individual suitability, local availability and household affordability remain unresolved.",
            ])
        lines.append("")

    example("TC01 — model-rule-passing candidate, if found",
            [(case, c) for case, c in pairs if c["model_rule_pass"]], maximum=3)
    example("TC02 — mixed risk trade-off",
            [(case, c) for case, c in pairs if c["mixed_tradeoff"]])
    example("TC03 — worsening without an improvement signal",
            [(case, c) for case, c in pairs if c["worsening_signal"] and not c["improvement_signal"]])
    example("TC04 — uncertain model comparison",
            [(case, c) for case, c in pairs if "model uncertainty requires review" in c["reasons"]])
    lines.extend([
        "## Additional existing software checks", "",
        "- TC05: The standalone budget sensitivity test changes illustrative food affordability without changing model input or prediction.",
        "- TC06: The five-month fixture is excluded from complementary-feeding candidate generation and C1 comparison.",
        "- Full input snapshots and outputs are retained only in the local private JSON supplied to the discovery command; no source names, identifiers, or raw rows are published here.",
        "- `allow_demo=false`; each candidate request preserves every non-feeding input. The C1 adapter checks GA-RGCA-v3/PYTORCH provenance and returned feeding/history fields.",
        "- This audit does not establish a causal feeding benefit, independently observed feeding inputs, authorized research use, clinical suitability, or Kalmunai affordability.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Local PHM/C1 model comparison, never clinical approval")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--at-risk-first", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-report", type=Path)
    arguments = parser.parse_args()
    if arguments.limit is not None and arguments.limit < 1:
        parser.error("--limit must be positive")
    if not 1 <= arguments.workers <= 4:
        parser.error("--workers must be between 1 and 4")
    arguments.private_output.parent.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(arguments.source.read_bytes()).hexdigest()
    order = "2025 source risk first" if arguments.at_risk_first else "source row order"
    prior = []
    if arguments.resume and arguments.private_output.exists():
        saved = json.loads(arguments.private_output.read_text(encoding="utf-8"))
        if saved.get("source_sha256") != source_hash or saved.get("scan_order") != order:
            raise ValueError("private resume file has a different source or scan order")
        prior = saved.get("cases", [])

    def save(cases: list[dict]) -> None:
        temporary = arguments.private_output.with_suffix(arguments.private_output.suffix + ".tmp")
        temporary.write_text(json.dumps({"source_sha256": source_hash,
                                         "scan_order": order, "cases": cases}), encoding="utf-8")
        temporary.replace(arguments.private_output)

    result = discover(arguments.source, limit=arguments.limit,
                      at_risk_first=arguments.at_risk_first,
                      prior_cases=prior, progress=save, workers=arguments.workers)
    temporary = arguments.private_output.with_suffix(arguments.private_output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    temporary.replace(arguments.private_output)
    if arguments.public_report is not None:
        arguments.public_report.write_text(public_report(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
