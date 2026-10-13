"""API tests for Component 3's endpoints. Run from backend/: python -m pytest tests_c3
Cycle tests need the real data folder (C3_DATA_DIR) and are skipped without it."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
DATA = Path(os.environ.get("C3_DATA_DIR", Path.home() / "Downloads" / "clean_malnutrition_data"))
needs_data = pytest.mark.skipif(not (DATA / "PHM_prediction_2025_to_2026.csv").exists(), reason="C3 data not available")


def test_context_offline_reports_ditwah_alert():
    r = client.get("/maintenance/context", params={"start": "2025-12-01", "end": "2025-12-31", "offline": True})
    assert r.status_code == 200 and r.json()["heightened"] is True


def test_dashboard_served():
    r = client.get("/maintenance/dashboard")
    assert r.status_code == 200 and "Model Health" in r.text


def test_scenarios_listed():
    assert any(s["family"] == "prevalence" for s in client.get("/maintenance/scenarios").json())


@needs_data
def test_cycle_and_controls():
    assert client.post("/maintenance/reset").json()["ready"] is True
    c = client.post("/maintenance/cycle", json={"family": "missing_weight", "strength": 0.75,
                                                "context_start": "2025-12-01", "context_end": "2025-12-31"}).json()
    assert c["decision"] in {"no_action", "recalibrate", "retrain", "hold"}
    assert c["context"]["heightened"] is True and c["validation"] is not None
    pending = client.post("/maintenance/cycle", json={"family": "prevalence", "strength": 0.4,
                                                      "require_approval": True}).json()
    assert "decision" in pending
    history = client.get("/maintenance/history").json()
    assert history[0]["action"] == "initial"
