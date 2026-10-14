"""Authoritative doctor-facing malnutrition type for GA-RGCA v3.

Acute status is only the Normal / MAM / SAM head. It must not be copied
into the overall malnutrition type.
"""

from __future__ import annotations

import json
from pathlib import Path

PREDICTED_MALNUTRITION_TYPES = ("Normal", "Underweight", "Stunting", "MAM", "SAM")
ACUTE_STATUSES = ("Normal", "MAM", "SAM")


def derive_predicted_malnutrition_type(
    *,
    underweight_probability: float,
    stunting_probability: float,
    underweight_threshold: float,
    stunting_threshold: float,
    acute_status: str,
) -> dict:
    """Return the single doctor-facing type and the overlapping conditions.

    Thresholds come from the caller (metadata.json or the stored prediction).
    Comparison uses >=. Normal is returned only when acute status is Normal
    and both binary heads are below threshold.
    """
    underweight_probability = float(underweight_probability)
    stunting_probability = float(stunting_probability)
    underweight_threshold = float(underweight_threshold)
    stunting_threshold = float(stunting_threshold)
    acute = str(acute_status)

    underweight_positive = underweight_probability >= underweight_threshold
    stunting_positive = stunting_probability >= stunting_threshold
    uw_decision_strength = (underweight_probability - underweight_threshold) / max(
        1e-8, 1.0 - underweight_threshold
    )
    st_decision_strength = (stunting_probability - stunting_threshold) / max(
        1e-8, 1.0 - stunting_threshold
    )

    if acute == "SAM":
        predicted = "SAM"
    elif acute == "MAM":
        predicted = "MAM"
    elif underweight_positive and stunting_positive:
        if st_decision_strength > uw_decision_strength:
            predicted = "Stunting"
        elif uw_decision_strength > st_decision_strength:
            predicted = "Underweight"
        else:
            predicted = "Stunting"
    elif stunting_positive:
        predicted = "Stunting"
    elif underweight_positive:
        predicted = "Underweight"
    else:
        predicted = "Normal"

    if predicted == "Normal" and (
        underweight_positive or stunting_positive or acute != "Normal"
    ):
        raise ValueError(
            "Normal is only valid when acute status is Normal and neither Underweight nor Stunting is positive"
        )
    if predicted not in PREDICTED_MALNUTRITION_TYPES:
        raise ValueError(f"Unsupported predicted malnutrition type: {predicted}")

    detected: list[str] = []
    if underweight_positive:
        detected.append("Underweight")
    if stunting_positive:
        detected.append("Stunting")
    if acute == "MAM":
        detected.append("MAM")
    if acute == "SAM":
        detected.append("SAM")

    return {
        "predicted_malnutrition_type": predicted,
        "underweight_positive": underweight_positive,
        "stunting_positive": stunting_positive,
        "detected_conditions": detected,
        "uw_decision_strength": uw_decision_strength,
        "st_decision_strength": st_decision_strength,
    }


def load_binary_thresholds() -> tuple[float, float] | None:
    """Read Underweight and Stunting thresholds from metadata.json."""
    for path in _metadata_candidates():
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        thresholds = data.get("binary_thresholds") or {}
        if "Underweight" in thresholds and "Stunting" in thresholds:
            return float(thresholds["Underweight"]), float(thresholds["Stunting"])
    return None


def _metadata_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    candidates = [
        Path("/ml/artifacts/ga_rgca_v3/metadata.json"),
        Path("/artifacts/ga-rgca/metadata.json"),
    ]
    for parent in here.parents:
        candidates.append(parent / "ml" / "artifacts" / "ga_rgca_v3" / "metadata.json")
    return candidates
