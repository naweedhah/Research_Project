from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    rng = np.random.default_rng(42)
    embeddings = rng.normal(size=(80, 128))
    # PCA reference projection
    x = embeddings - embeddings.mean(axis=0)
    u, s, vt = np.linalg.svd(x, full_matrices=False)
    pca = x @ vt[:2].T
    try:
        import umap

        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42)
        umap_emb = reducer.fit_transform(embeddings)
    except Exception as exc:  # noqa: BLE001
        umap_emb = None
        umap_error = str(exc)
    else:
        umap_error = None
    out = ROOT / "ml/artifacts/trajectory"
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "pca": pca.tolist(),
        "umap": None if umap_emb is None else umap_emb.tolist(),
        "umap_error": umap_error,
        "notes": "2D projections are exploratory. Operational alerts must not use UMAP coordinates.",
    }
    (out / "projection.json").write_text(json.dumps(payload))
    print(f"Wrote {out / 'projection.json'}")


if __name__ == "__main__":
    main()
