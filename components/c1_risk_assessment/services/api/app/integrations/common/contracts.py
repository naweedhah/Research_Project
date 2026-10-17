"""Versioned integration DTOs for C1 ↔ C3 / C4. Runtime source of truth; JSON schemas under packages/contracts/integrations/."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_CONTRACT_VERSION = "1.0"
FORBIDDEN_IDENTITY_KEYS = frozenset(
    {
        "full_name",
        "name",
        "caregiver_name",
        "caregiver_phone",
        "phone",
        "phone_number",
        "external_patient_id",
        "mrn",
        "nic",
        "national_id",
        "address",
        "exact_address",
        "email",
        "encrypted_identity",
        "identity_ciphertext",
    }
)


class IntegrationContractError(ValueError):
    pass


def assert_supported_contract_version(version: str | None) -> str:
    if version != SUPPORTED_CONTRACT_VERSION:
        raise IntegrationContractError(
            f"Unsupported contract_version={version!r}; C1 accepts only '{SUPPORTED_CONTRACT_VERSION}'"
        )
    return version


class ScoreSemanticsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float
    kind: str
    label: str | None = None
    is_probability: bool = False
    is_calibrated: bool = False
    calibration_version: str | None = None


class IntegrationEnvelopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = "1.0"
    event_id: UUID
    correlation_id: UUID
    source_component: Literal["C1", "C2", "C3", "C4"] = "C1"
    event_type: str
    occurred_at: datetime
    idempotency_key: str | None = None
    payload: dict[str, Any]


class C3InterventionRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = "1.0"
    request_id: UUID
    correlation_id: UUID
    source: Literal["C1"] = "C1"
    child: dict[str, Any]
    visit: dict[str, Any]
    prediction: dict[str, Any]
    longitudinal: dict[str, Any] | None = None
    alerts: list[str] = Field(default_factory=list)
    model: dict[str, Any]
    features: dict[str, Any]
    data_quality: dict[str, Any] = Field(default_factory=dict)
    explanation_context_ref: str | None = None
    requested_by: dict[str, Any] | None = None
    requested_at: datetime


class C3InterventionResponseV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    contract_version: Literal["1.0"] = "1.0"
    request_id: UUID
    status: Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
    component: Literal["C3"] = "C3"
    result_id: str | None = None
    result_url: str | None = None
    generated_at: datetime | None = None
    message: str | None = None

    @field_validator("contract_version")
    @classmethod
    def _version(cls, v: str) -> str:
        return assert_supported_contract_version(v)


class C4PredictionObservationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = "1.0"
    event_id: UUID
    event_type: Literal["c1.prediction.completed"] = "c1.prediction.completed"
    occurred_at: datetime
    correlation_id: UUID | None = None
    child: dict[str, Any]
    visit: dict[str, Any]
    features: dict[str, Any]
    prediction: dict[str, Any]
    model: dict[str, Any]
    quality: dict[str, Any] = Field(default_factory=dict)
    longitudinal: dict[str, Any] | None = None


class C4ClinicianReviewObservationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = "1.0"
    event_id: UUID
    event_type: Literal["c1.clinician_review.completed"] = "c1.clinician_review.completed"
    occurred_at: datetime
    correlation_id: UUID | None = None
    prediction_id: UUID
    visit_id: UUID
    pseudonymous_child_id: str
    clinician_review: dict[str, Any]
    model_version: str


class C4ModelUpdateProposalV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = "1.0"
    c4_decision_id: UUID
    model_version: str
    base_model_version: str
    update_type: Literal["RECALIBRATION", "RETRAIN", "HOTFIX"]
    artifact: dict[str, Any]
    feature_schema_version: str
    label_schema_version: str
    calibration_version: str | None = None
    embedding_space_id: str
    embedding_dimension: int | None = None
    validation_summary_ref: str | None = None
    approved_by_component: Literal["C4"] = "C4"
    created_at: datetime
    notes: str | None = None

    @field_validator("contract_version")
    @classmethod
    def _version(cls, v: str) -> str:
        return assert_supported_contract_version(v)


def contains_forbidden_identity(payload: Any, *, path: str = "") -> list[str]:
    """Return dotted paths of forbidden identity keys found in a nested payload."""
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_l = str(key).lower()
            here = f"{path}.{key}" if path else str(key)
            if key_l in FORBIDDEN_IDENTITY_KEYS:
                hits.append(here)
            hits.extend(contains_forbidden_identity(value, path=here))
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            hits.extend(contains_forbidden_identity(item, path=f"{path}[{i}]"))
    return hits
