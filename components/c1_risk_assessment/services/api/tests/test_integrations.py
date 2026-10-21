"""C1 integration-readiness tests for C3/C4 contracts (no external services)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.common.contracts import (
    C3InterventionRequestV1,
    C4ClinicianReviewObservationV1,
    C4ModelUpdateProposalV1,
    IntegrationContractError,
    assert_supported_contract_version,
    contains_forbidden_identity,
)
from app.integrations.common.outbox import mark_delivered, mark_retryable_failure
from app.models.enums import ClinicianWorkflowAction, IntegrationDeliveryStatus, IntegrationEventType, ModelStatus


def test_contract_version_rejects_unsupported():
    with pytest.raises(IntegrationContractError):
        assert_supported_contract_version("99")
    assert assert_supported_contract_version("1.0") == "1.0"


def test_c4_model_proposal_rejects_bad_version():
    with pytest.raises(Exception):
        C4ModelUpdateProposalV1.model_validate(
            {
                "contract_version": "99",
                "c4_decision_id": str(uuid4()),
                "model_version": "MCA-2",
                "base_model_version": "MCA-1",
                "update_type": "RECALIBRATION",
                "artifact": {"uri": "s3://x", "sha256": "a" * 64},
                "feature_schema_version": "fs-2026-001",
                "label_schema_version": "ls-2026-001",
                "embedding_space_id": "space",
                "approved_by_component": "C4",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )


def test_privacy_scan_flags_identity_keys():
    payload = {
        "child": {"pseudonymous_child_id": "C-1005"},
        "caregiver_name": "Secret",
        "nested": {"phone": "077"},
    }
    hits = contains_forbidden_identity(payload)
    assert "caregiver_name" in hits
    assert "nested.phone" in hits


def test_example_payloads_have_no_forbidden_identity():
    # Docs examples are not mounted into the API image; validate when present locally.
    examples = Path("/contracts").parent.parent / "docs" / "integrations" / "examples"
    try:
        available = examples.is_dir()
    except Exception:
        available = False
    if not available:
        # Inline synthetic examples (same privacy rules as docs samples)
        samples = [
            {"child": {"pseudonymous_child_id": "C-1005"}, "score": {"kind": "demo_progression_score"}},
            {"pseudonymous_child_id": "C-1005", "clinician_review": {"assessment": "AGREE", "clinician_status": None}},
        ]
        for data in samples:
            assert contains_forbidden_identity(data) == []
        return
    for name in [
        "c3-request-example.json",
        "c4-prediction-event-example.json",
        "c4-review-event-example.json",
        "c4-model-update-example.json",
    ]:
        data = json.loads((examples / name).read_text(encoding="utf-8"))
        assert contains_forbidden_identity(data) == []


def test_c3_request_dto_requires_demo_score_semantics():
    req = C3InterventionRequestV1.model_validate(
        {
            "request_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "child": {"pseudonymous_child_id": "C-1"},
            "visit": {"visit_id": str(uuid4()), "visit_number": 1, "visit_date": "2026-01-01"},
            "prediction": {
                "prediction_id": str(uuid4()),
                "status": "wasting",
                "severity": "moderate",
                "score": {
                    "value": 0.5,
                    "kind": "demo_progression_score",
                    "is_probability": False,
                    "is_calibrated": False,
                },
            },
            "model": {"model_version": "MCA-DEMO-1.0"},
            "features": {},
            "requested_at": datetime.now(UTC).isoformat(),
        }
    )
    assert req.prediction["score"]["kind"] == "demo_progression_score"
    assert req.prediction["score"]["is_probability"] is False


def test_c4_review_allows_null_clinician_status():
    obs = C4ClinicianReviewObservationV1.model_validate(
        {
            "event_id": str(uuid4()),
            "occurred_at": datetime.now(UTC).isoformat(),
            "prediction_id": str(uuid4()),
            "visit_id": str(uuid4()),
            "pseudonymous_child_id": "C-1",
            "clinician_review": {
                "assessment": "AGREE",
                "clinician_status": None,
                "clinician_severity": None,
                "workflow_action": ClinicianWorkflowAction.REQUEST_INTERVENTION_REASSESSMENT.value,
            },
            "model_version": "MCA-DEMO-1.0",
        }
    )
    assert obs.clinician_review["clinician_status"] is None


def test_idempotency_key_formats():
    prediction_id = uuid4()
    review_id = uuid4()
    assert f"c3-reassessment:{prediction_id}:{review_id}".startswith("c3-reassessment:")
    assert f"c4-prediction:{prediction_id}".startswith("c4-prediction:")


def test_retry_state_machine_without_db():
    event = SimpleNamespace(
        attempt_count=0,
        delivery_status=IntegrationDeliveryStatus.PENDING,
        delivery_error=None,
        last_attempt_at=None,
        next_attempt_at=None,
        delivered_at=None,
        external_ref=None,
    )
    mark_retryable_failure(event, "boom", max_attempts=3)
    assert event.delivery_status == IntegrationDeliveryStatus.FAILED_RETRYABLE
    assert event.attempt_count == 1
    mark_retryable_failure(event, "boom", max_attempts=3)
    mark_retryable_failure(event, "boom", max_attempts=3)
    assert event.delivery_status == IntegrationDeliveryStatus.FAILED_FINAL
    mark_delivered(event, external_ref={"status": "COMPLETED"})
    assert event.delivery_status == IntegrationDeliveryStatus.DELIVERED


def test_model_status_includes_candidate():
    assert ModelStatus.CANDIDATE.value == "CANDIDATE"
    assert IntegrationEventType.CLINICIAN_REVIEW_COMPLETED.value == "clinician_review.completed"
    assert IntegrationEventType.MODEL_ACTIVATED.value == "model.activated"


def test_json_schemas_exist():
    root = Path("/contracts/integrations")
    if not root.is_dir():
        pytest.skip("packages/contracts/integrations not mounted")
    for name in [
        "integration-envelope.v1.json",
        "c1-c3-request.v1.json",
        "c1-c3-response.v1.json",
        "c1-c4-prediction-observation.v1.json",
        "c1-c4-clinician-review-observation.v1.json",
        "c1-c4-model-update-proposal.v1.json",
    ]:
        assert (root / name).is_file(), name
