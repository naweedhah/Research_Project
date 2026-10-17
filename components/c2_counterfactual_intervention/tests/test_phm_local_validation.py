"""Private-registry controls; genuine C1 inference is verified separately live."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from components.c2_counterfactual_intervention.phm_local_validation import local_profiles


def test_registry_unconfigured_fails_closed(monkeypatch):
    monkeypatch.delenv("C2_PHM_VALIDATION_PATH", raising=False)
    with pytest.raises(FileNotFoundError):
        local_profiles()
    # The test client is not a loopback TCP peer; private routes refuse it.
    client = TestClient(app)
    assert client.get("/interventions/local-validation-profiles").status_code == 403
    assert client.post("/interventions/local-validation", json={"case_id": "PHM-LOCAL-0001"}).status_code == 403


def test_local_selector_exposes_aliases_without_private_input(tmp_path, monkeypatch):
    private = tmp_path / "research-input.json"
    private.write_text(json.dumps({"source_sha256": "abc", "cases": [
        {"case_id": "PHM-LOCAL-0001", "snapshot": {"historical_baseline": {
            "age_months": 16, "private_field": "DO-NOT-EXPOSE"}},
         "candidates": [{"model_rule_pass": True, "mixed_tradeoff": False, "reasons": []}]},
    ]}), encoding="utf-8")
    monkeypatch.setenv("C2_PHM_VALIDATION_PATH", str(private))
    result = local_profiles()
    assert result["profiles"][0]["model_status"] == "model_rule_signal"
    assert result["profiles"][0]["case_id"] == "PHM-LOCAL-0001"
    assert "DO-NOT-EXPOSE" not in json.dumps(result)
