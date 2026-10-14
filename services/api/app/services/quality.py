from __future__ import annotations

from dataclasses import dataclass, field

from app.core.policy import ClinicalPolicy
from app.models.enums import DataQualityFlag


@dataclass
class QualityIssue:
    field: str
    flag: DataQualityFlag
    message: str
    blocking: bool = False


@dataclass
class QualityReport:
    complete: bool
    blocking_errors: list[QualityIssue] = field(default_factory=list)
    warnings: list[QualityIssue] = field(default_factory=list)
    optional_missing: int = 0

    def as_dict(self) -> dict:
        return {
            "complete": self.complete,
            "blocking_errors": [i.__dict__ for i in self.blocking_errors],
            "warnings": [i.__dict__ for i in self.warnings],
            "optional_missing": self.optional_missing,
        }


REQUIRED_ANTHRO = ["age_months", "sex", "height_cm", "weight_kg"]
FIELD_LABELS = {
    "age_months": "Age (months)",
    "sex": "Sex",
    "weight_kg": "Weight (kg)",
    "height_cm": "Height (cm)",
    "muac_cm": "MUAC (cm)",
    "birth_weight_kg": "Birth weight (kg)",
    "head_circumference_cm": "Head circumference (cm)",
    "maternal_bmi": "Maternal BMI",
    "gestational_age_weeks": "Gestational age (weeks)",
    "household_size": "Household size",
    "dietary_diversity_score": "Dietary diversity score",
}
OPTIONAL_FIELDS = [
    ("muac_cm", "anthropometric"),
    ("birth_weight_kg", "anthropometric"),
    ("head_circumference_cm", "anthropometric"),
    ("maternal_bmi", "maternal"),
    ("dietary_diversity_score", "dietary"),
]


def _in_range(value: float | None, spec: dict | None) -> bool:
    if value is None or spec is None:
        return True
    return spec["min"] <= value <= spec["max"]


def validate_visit_payload(payload: dict, policy: ClinicalPolicy, socioeconomic_stale: bool = False) -> QualityReport:
    issues: list[QualityIssue] = []
    warnings: list[QualityIssue] = []
    anthro = payload.get("anthropometric") or {}
    ranges = policy.measurement_ranges

    for field in REQUIRED_ANTHRO:
        if anthro.get(field) in (None, ""):
            label = FIELD_LABELS.get(field, field)
            issues.append(
                QualityIssue(
                    field,
                    DataQualityFlag.MODEL_INPUT_INCOMPLETE,
                    f"{label} is required before an assessment can be run.",
                    blocking=True,
                )
            )

    numeric_map = {
        "age_months": anthro.get("age_months"),
        "weight_kg": anthro.get("weight_kg"),
        "height_cm": anthro.get("height_cm"),
        "muac_cm": anthro.get("muac_cm"),
        "birth_weight_kg": anthro.get("birth_weight_kg"),
        "head_circumference_cm": anthro.get("head_circumference_cm"),
        "maternal_bmi": (payload.get("maternal_child_health") or {}).get("maternal_bmi"),
        "household_size": (payload.get("socioeconomic") or {}).get("household_size"),
        "gestational_age_weeks": (payload.get("maternal_child_health") or {}).get("gestational_age_weeks"),
    }
    for key, value in numeric_map.items():
        if value is None:
            continue
        spec = ranges.get(key)
        if not _in_range(float(value), spec):
            label = FIELD_LABELS.get(key, key)
            span = f" ({spec['min']}–{spec['max']})" if spec else ""
            issues.append(
                QualityIssue(
                    key,
                    DataQualityFlag.OUTLIER_REVIEW_REQUIRED,
                    f"{label} {value} is outside the accepted range{span}.",
                    blocking=True,
                )
            )

    optional_missing = 0
    for field, _group in OPTIONAL_FIELDS:
        source = anthro if field in anthro or field in {"muac_cm", "birth_weight_kg", "head_circumference_cm"} else (payload.get("maternal_child_health") or payload.get("dietary") or {})
        if field == "maternal_bmi":
            source = payload.get("maternal_child_health") or {}
        if field == "dietary_diversity_score":
            source = payload.get("dietary") or {}
        if source.get(field) in (None, ""):
            optional_missing += 1
            warnings.append(
                QualityIssue(field, DataQualityFlag.MISSING_OPTIONAL_DATA, f"Optional field {field} unavailable", False)
            )

    if socioeconomic_stale:
        warnings.append(
            QualityIssue(
                "socioeconomic",
                DataQualityFlag.STALE_SOCIOECONOMIC_PROFILE,
                "Household information was carried forward from the previous visit.",
                False,
            )
        )

    return QualityReport(
        complete=len(issues) == 0,
        blocking_errors=issues,
        warnings=warnings,
        optional_missing=optional_missing,
    )
