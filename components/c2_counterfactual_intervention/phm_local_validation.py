"""Opt-in local review of private, de-identified PHM model comparisons.

The registry path is supplied via C2_PHM_VALIDATION_PATH and is never bundled
with the application. Every selected case is re-scored against the live C1 API.
No model-only pass is promoted to an authorized intervention.
"""

from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .c1_compat import C1Snapshot
from .c1_predictors import RealC1HttpPredictor
from .guideline_references import research_guidance_for_age
from .phm_discovery import compare
from .standalone_demo import _food_plans


class LocalValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=r"^PHM-LOCAL-\d{4}$")
    budget_lkr: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_period: str = Field(default="weekly", pattern=r"^(daily|weekly|monthly)$")


def _registry() -> dict:
    path = os.getenv("C2_PHM_VALIDATION_PATH")
    if not path:
        raise FileNotFoundError("local PHM validation registry is not configured")
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError("local PHM validation registry is unavailable")
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data.get("cases"), list) or not data.get("source_sha256"):
        raise ValueError("invalid private validation registry")
    return data


def local_profiles() -> dict:
    data = _registry()
    cases = data["cases"]
    selected: list[dict] = []
    seen: set[str] = set()
    categories = (
        ("model_rule_signal", lambda c: any(x["model_rule_pass"] for x in c["candidates"]), 3),
        ("mixed_tradeoff", lambda c: any(x["mixed_tradeoff"] for x in c["candidates"]), 1),
        ("uncertain", lambda c: any("model uncertainty requires review" in x["reasons"]
                                    for x in c["candidates"]), 1),
        ("rejected", lambda c: all(not x["model_rule_pass"] for x in c["candidates"]), 1),
    )
    for label, matches, maximum in categories:
        added = 0
        for case in cases:
            if case["case_id"] in seen or not matches(case):
                continue
            age = case["snapshot"]["historical_baseline"]["age_months"]
            selected.append({"case_id": case["case_id"], "age_months": age,
                             "model_status": label, "source_label": "Linked PHM 2025 research record",
                             "feeding_provenance": "direct observation unverified"})
            seen.add(case["case_id"])
            added += 1
            if added >= maximum:
                break
    return {"available": True, "source_sha256": data["source_sha256"],
            "scanned_profiles": len(cases), "profiles": selected,
            "limitations": "Local de-identified research inputs. Feeding observation provenance, authorization, suitability and local availability are unverified."}


def review_local_case(request: LocalValidationRequest,
                      predictor: RealC1HttpPredictor | None = None) -> dict:
    data = _registry()
    stored = next((case for case in data["cases"] if case["case_id"] == request.case_id), None)
    if stored is None:
        raise LookupError("local validation case is unavailable")
    snapshot = C1Snapshot.model_validate(stored["snapshot"])
    predictor = predictor or RealC1HttpPredictor()
    if getattr(predictor, "source", None) != "GA-RGCA-v3":
        raise ValueError("genuine C1 predictor required")
    fresh = compare(snapshot, predictor)
    if fresh["model_version"] != stored["model_version"] or fresh["baseline"] != stored["baseline"]:
        raise ValueError("live C1 baseline differs from stored evidence")
    by_change = {json.dumps(candidate["changes"], sort_keys=True): candidate
                 for candidate in stored["candidates"]}
    for candidate in fresh["candidates"]:
        expected = by_change.get(json.dumps(candidate["changes"], sort_keys=True))
        if expected is None or candidate["prediction"] != expected["prediction"]:
            raise ValueError("live C1 candidate differs from stored evidence")
    age = int(snapshot.historical_baseline["age_months"])
    guidance = research_guidance_for_age(age)
    plans = _food_plans(age, guidance, request.budget_lkr, request.budget_period)
    passing = [candidate for candidate in fresh["candidates"] if candidate["model_rule_pass"]]
    passing.sort(key=lambda candidate: (len(candidate["changes"]),
                                         tuple(sorted((key, value["to"]) for key, value in candidate["changes"].items()))))
    cards = [{"rank": index, "candidate": candidate, "food_plans": plans,
              "status": "Passed model comparison only — feasibility and authorization unresolved"}
             for index, candidate in enumerate(passing, 1)]
    fingerprint = hashlib.sha256(json.dumps(snapshot.predict_payload(), sort_keys=True,
                                            separators=(",", ":")).encode()).hexdigest()
    return {"mode": "local_phm_model_validation", "case_id": request.case_id,
            "source_sha256": data["source_sha256"], "input_fingerprint": fingerprint,
            "profile": {"age_months": age, "sex": snapshot.historical_baseline.get("sex"),
                        "historical_height_cm": snapshot.historical_baseline.get("height_cm"),
                        "historical_weight_kg": snapshot.historical_baseline.get("weight_kg"),
                        "original_feeding": {key: snapshot.ga_rgca_context[key]
                                             for key in ("meal_frequency", "dietary_diversity")},
                        "provenance": snapshot.provenance},
            "baseline": fresh["baseline"], "candidates": fresh["candidates"],
            "model_version": fresh["model_version"], "prediction_source": "GA-RGCA-v3",
            "cards": cards, "food_plans": plans, "guidance": guidance,
            "budget": {"amount_lkr": str(request.budget_lkr) if request.budget_lkr is not None else None,
                       "period": request.budget_period,
                       "provenance": "user-entered demonstration amount; not verified household evidence"},
            "research_authorized": False, "clinical_use": False,
            "limitations": ["Live C1 outputs matched private source-labelled research evidence.",
                            "Source feeding field observation provenance is unverified.",
                            "Model comparison cannot establish causal benefit or authorize intervention.",
                            "Individual suitability and local availability remain unknown.",
                            "DCS prices are Colombo references, not verified Kalmunai prices."]}
