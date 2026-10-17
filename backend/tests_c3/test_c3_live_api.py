"""API tests for Component 3's live workflow and results endpoints. Run from backend/: python -m pytest tests_c3

A small synthetic deployment (two numeric inputs and sex) stands in for the real model, so these tests run anywhere;
the last test uses the real data when C3_DATA_DIR holds it."""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.c3.live import LiveService, LiveSetup
from app.main import app
from app.routers import maintenance
from component3.experiments.run_comparison import fit_initial_model
from component3.experiments.run_real import evaluate, thresholds_from_baseline
from component3.interfaces import FeatureSchema, FeatureSpec

client = TestClient(app)
SCHEMA = FeatureSchema((FeatureSpec("x1", "numeric"), FeatureSpec("x2", "numeric"),
                        FeatureSpec("Sex", "categorical", "object")))
DATA = Path(os.environ.get("C3_DATA_DIR", Path.home() / "Downloads" / "clean_malnutrition_data"))


def factory():
    pre = ColumnTransformer([("num", "passthrough", ["x1", "x2"]),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), ["Sex"])])
    return Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=500))])


def make_data(n, seed, cut=1.0):
    """y = 1 when x1 is high; `cut` moves the line, so the same model misses new cases (a harmful shift)."""
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"x1": rng.normal(size=n), "x2": rng.normal(size=n),
                      "Sex": rng.choice(["Male", "Female"], size=n).astype(object)})
    y = (X["x1"] + 0.3 * rng.normal(size=n) > cut).astype(int).to_numpy()
    return X, y


def synthetic_setup():
    def initial():
        X, y = make_data(400, seed=0)
        model = fit_initial_model(factory, X, y, SCHEMA)
        baseline = evaluate(model, *make_data(400, seed=1))
        thresholds, criteria = thresholds_from_baseline(baseline)
        return {"model": model, "X_ref": X, "y_ref": y, "baseline": baseline, "thresholds": thresholds,
                "criteria": criteria}

    return LiveSetup("synthetic", SCHEMA, factory, None, None, initial)


def records(X, prefix):
    return [{"record_id": f"{prefix}{i}", **row} for i, row in enumerate(X.to_dict("records"))]


def outcomes(y, prefix):
    return {f"{prefix}{i}": int(v) for i, v in enumerate(y)}


@pytest.fixture
def svc(tmp_path, monkeypatch):
    service = LiveService(synthetic_setup, directory=tmp_path)
    monkeypatch.setattr(maintenance, "live", service)
    return service


def test_status_starts_from_initial_model(svc):
    s = client.get("/maintenance/live/status").json()
    assert s["ready"] and s["active_model"]["version"] == "v1.0" and s["batches"] == 0


def test_batch_is_monitored_without_returning_records(svc):
    X, _ = make_data(120, seed=2)
    rows = records(X, "a")
    rows[0]["Sex"], rows[1]["note"] = "male", "extra field"
    r = client.post("/maintenance/live/batches", json={"batch_id": "round-1", "area": "PHM-01", "records": rows,
                                                       "context": "none"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["records"] == 120 and body["status"] == "awaiting_outcomes"
    assert body["cycle"]["decision"] in {"no_action", "hold"} and body["cycle"]["labels_available"] is False
    assert body["unknown_categories"] == {"Sex": 1} and body["ignored_fields"] == ["note"]
    assert "a0" not in r.text  # no record-level data in responses
    assert client.get("/maintenance/live/batches").json()[0]["batch_id"] == "round-1"
    assert client.post("/maintenance/live/batches", json={"batch_id": "round-1", "records": rows}).status_code == 409


@pytest.mark.parametrize("change, message", [
    (lambda rows: rows[:10], "at least 30"),
    (lambda rows: [{k: v for k, v in r.items() if k != "x2"} for r in rows], "missing model input fields"),
    (lambda rows: [{**r, "x1": "high"} for r in rows], "must be a number"),
    (lambda rows: [{**r, "record_id": "same"} for r in rows], "duplicate record_id"),
])
def test_bad_batches_are_refused(svc, change, message):
    rows = records(make_data(60, seed=3)[0], "b")
    r = client.post("/maintenance/live/batches", json={"records": change(rows), "context": "none"})
    assert r.status_code == 400 and message in r.json()["detail"]


def test_outcomes_drive_maintenance_approval_and_post_deployment_check(svc):
    X, y = make_data(800, seed=4, cut=0.5)  # more children affected: the old model is now miscalibrated
    client.post("/maintenance/live/batches", json={"batch_id": "r1", "records": records(X, "c"), "context": "none"})
    r = client.post("/maintenance/live/batches/r1/outcomes", json={"labels": outcomes(y, "c")})
    assert r.status_code == 200, r.text
    cycle = r.json()["cycle"]
    assert cycle["decision"] in {"recalibrate", "retrain"} and cycle["candidate"]
    assert cycle["pending_approval"] and cycle["model_after"] == "v1.0"  # approval required by default
    assert client.post("/maintenance/live/batches/r1/outcomes", json={"labels": outcomes(y, "c")}).status_code == 409

    approved = client.post("/maintenance/live/approve", params={"approver": "MOH officer"}).json()
    status = client.get("/maintenance/live/status").json()
    assert status["active_model"]["version"] == approved["approved"] == cycle["candidate"]
    assert status["awaiting_post_deployment_check"] == cycle["candidate"]
    assert client.post("/maintenance/live/approve").status_code == 409

    X2, y2 = make_data(200, seed=5, cut=0.5)
    client.post("/maintenance/live/batches", json={"batch_id": "r2", "records": records(X2, "d"), "context": "none"})
    second = client.post("/maintenance/live/batches/r2/outcomes", json={"labels": outcomes(y2, "d")}).json()
    check = second["post_deployment_check"]
    assert check["checked"] and check["previous_version"] == "v1.0"
    actions = [h["action"] for h in client.get("/maintenance/live/history").json()]
    assert actions[:3] == ["initial", "pending_approval", "promoted"]


def test_state_survives_restart(svc, tmp_path, monkeypatch):
    X, y = make_data(400, seed=6, cut=0.2)
    client.post("/maintenance/live/batches", json={"batch_id": "r1", "records": records(X, "e"), "context": "none"})
    client.post("/maintenance/live/batches/r1/outcomes", json={"labels": outcomes(y, "e"), "require_approval": False})
    before = client.get("/maintenance/live/status").json()

    monkeypatch.setattr(maintenance, "live", LiveService(synthetic_setup, directory=tmp_path))  # a restart
    after = client.get("/maintenance/live/status").json()
    assert after["active_model"] == before["active_model"] and after["batches"] == 1
    assert len(client.get("/maintenance/live/history").json()) >= 2


def test_outcome_errors(svc):
    X, y = make_data(60, seed=7)
    client.post("/maintenance/live/batches", json={"batch_id": "r1", "records": records(X, "f"), "context": "none"})
    assert client.post("/maintenance/live/batches/nope/outcomes", json={"labels": {}}).status_code == 404
    bad_id = client.post("/maintenance/live/batches/r1/outcomes", json={"labels": {"zz": 1}})
    assert bad_id.status_code == 400 and "unknown record_id" in bad_id.json()["detail"]
    bad_value = client.post("/maintenance/live/batches/r1/outcomes", json={"labels": {**outcomes(y, "f"), "f0": 7}})
    assert bad_value.status_code == 400 and "must be one of" in bad_value.json()["detail"]


def test_reset_needs_confirmation(svc):
    X, _ = make_data(60, seed=8)
    client.post("/maintenance/live/batches", json={"records": records(X, "g"), "context": "none"})
    assert client.post("/maintenance/live/reset").status_code == 400
    s = client.post("/maintenance/live/reset", params={"confirm": True}).json()
    assert s["active_model"]["version"] == "v1.0" and s["batches"] == 0


def test_results_listed_and_served():
    runs = client.get("/maintenance/results").json()
    run = next(r for r in runs if r["run"] == "c3_underweight_calibrated")
    assert run["strategy_summary"] and run["suggested_thresholds"]
    assert client.get(run["figures"][0]).headers["content-type"] == "image/png"
    report = client.get(run["report"])
    assert report.status_code == 200 and report.text.startswith("#")
    assert client.get("/maintenance/results/c3_underweight/figures/..%2FREPORT.md").status_code == 404
    assert client.get("/maintenance/results/nope/report").status_code == 404


@pytest.mark.skipif(not (DATA / "PHM_prediction_2025_to_2026.csv").exists(), reason="C3 data not available")
def test_real_model_accepts_a_real_batch(tmp_path, monkeypatch):
    from component3.data import load_prediction_data

    monkeypatch.setattr(maintenance, "live", LiveService(directory=tmp_path))
    data = load_prediction_data("underweight")
    sample = data.X.sample(80, random_state=0).astype(object).where(data.X.notna().sample(80, random_state=0), None)
    r = client.post("/maintenance/live/batches", json={"records": records(sample, "p"), "context": "none"})
    assert r.status_code == 200, r.text
    assert r.json()["unknown_categories"] == {} and r.json()["cycle"]["validation"]["current"]["rows"] == 80
