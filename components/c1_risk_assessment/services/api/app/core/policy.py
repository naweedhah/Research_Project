from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.core.config import get_settings


@dataclass
class ClinicalPolicy:
    policy_id: str
    status: str
    disclaimer: str
    stagnation_threshold: float
    consecutive_followups: int
    deterioration_delta: float
    relapse_prior_improvement: float
    relapse_increase: float
    overdue_grace_days: int
    default_followup_days: int
    measurement_ranges: dict
    alert_severity_map: dict
    notes: str


def load_clinical_policy() -> ClinicalPolicy:
    path = get_settings().contracts_dir / "clinical_policy.yaml"
    data = yaml.safe_load(path.read_text())
    return ClinicalPolicy(
        policy_id=data["policy_id"],
        status=data["status"],
        disclaimer=data["disclaimer"],
        stagnation_threshold=float(data["stagnation"]["threshold"]),
        consecutive_followups=int(data["stagnation"]["consecutive_followups"]),
        deterioration_delta=float(data["deterioration"]["delta"]),
        relapse_prior_improvement=float(data["relapse"]["prior_improvement"]),
        relapse_increase=float(data["relapse"]["subsequent_increase"]),
        overdue_grace_days=int(data["missed_follow_up"]["grace_period_days"]),
        default_followup_days=int(data["follow_up"]["default_interval_days"]),
        measurement_ranges=data["measurement_ranges"],
        alert_severity_map=data["alert_severity_map"],
        notes=data.get("notes", "Research / Demo Configuration"),
    )


def load_product() -> dict:
    import json

    path = get_settings().contracts_dir / "product.json"
    return json.loads(path.read_text())


def load_label_schema() -> dict:
    path = get_settings().contracts_dir / "label_schema.yaml"
    return yaml.safe_load(path.read_text())


def load_feature_sets() -> dict:
    path = get_settings().contracts_dir / "feature_sets.yaml"
    return yaml.safe_load(path.read_text())


def load_registration_config() -> dict:
    import json

    path = get_settings().contracts_dir / "registration_config.json"
    return json.loads(path.read_text())
