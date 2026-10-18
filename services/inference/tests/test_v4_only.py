"""The inference service has one model and no legacy fallback."""

from pathlib import Path

import pytest

from app.ga_rgca_v4 import REQUIRED_FILES, V4_MODEL_VERSION
from app.main import EXPECTED_MODEL_VERSION, V4_MODEL

REPO = Path(__file__).resolve().parents[3]


def test_only_v4_is_configured():
    assert EXPECTED_MODEL_VERSION == "ga_rgca_v4_rsl"
    assert V4_MODEL is not None
    assert V4_MODEL.name == V4_MODEL_VERSION


def test_v4_artifact_files_exist_and_v3_directory_does_not():
    directory = REPO / "ml" / "artifacts" / "ga_rgca_v4_rsl"
    for name in REQUIRED_FILES:
        assert (directory / name).is_file(), name
    assert not (REPO / "ml" / "artifacts" / "ga_rgca_v3").exists()
    assert not (REPO / "services" / "inference" / "app" / "ga_rgca.py").exists()
    assert not (REPO / "services" / "inference" / "app" / "demo_outcomes.py").exists()


def test_invalid_model_version_refuses_to_start():
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["C1_MODEL_VERSION"] = "ga_rgca_v3"
    env.pop("GA_RGCA_V4_DIR", None)
    completed = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=REPO / "services" / "inference",
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "ga_rgca_v4_rsl" in (completed.stderr + completed.stdout)
