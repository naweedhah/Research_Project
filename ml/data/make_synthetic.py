from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

STATUS = ["normal", "stunting", "wasting", "underweight"]


def write_synthetic(path: Path, n_children: int = 40, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_children):
        child = f"S-{1000 + i}"
        n_visits = int(rng.integers(3, 6))
        for v in range(n_visits):
            status = STATUS[int(rng.integers(0, 4))]
            rows.append(
                {
                    "child_id": child,
                    "visit_date": f"2026-{1 + v:02d}-15",
                    "age_months": float(rng.integers(4, 48)),
                    "weight_kg": float(rng.uniform(5, 16)),
                    "height_cm": float(rng.uniform(55, 100)),
                    "muac_cm": float(rng.uniform(10, 16)),
                    "wealth_proxy": rng.choice(["lowest", "second", "middle", "fourth", "highest"]),
                    "maternal_education": rng.choice(["none", "primary", "secondary", "higher"]),
                    "dietary_diversity_score": int(rng.integers(1, 8)),
                    "recent_diarrhoea": int(rng.integers(0, 2)),
                    "status": status,
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
