"""Save and restore C3 state (the registry with every model version, plus any service state) across restarts.

Files are joblib pickles, which can run code when loaded: only load files this service wrote itself, from a folder
other people cannot write to. Writes are atomic (temporary file, then rename), so a crash never leaves half a file.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import joblib


def save_state(obj, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    os.close(fd)
    try:
        joblib.dump(obj, tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_state(path: Path):
    return joblib.load(Path(path))
