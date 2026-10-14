"""Train the multimodal cross-attention model. Training is separate from production inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import yaml
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from ml.models.multimodal import MultimodalConfig, MultimodalCrossAttention

ROOT = Path(__file__).resolve().parents[2]


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def synthetic_batch(n: int, cfg: MultimodalConfig, seed: int = 0):
    g = torch.Generator().manual_seed(seed)
    batch = {
        "anthropometric": torch.randn(n, cfg.anthro_dim, generator=g),
        "socioeconomic": torch.randn(n, cfg.socio_dim, generator=g),
        "dietary": torch.randn(n, cfg.diet_dim, generator=g),
        "maternal_child_health": torch.randn(n, cfg.health_dim, generator=g),
    }
    status = torch.randint(0, cfg.n_status, (n,), generator=g)
    severity = torch.randint(0, cfg.n_severity, (n,), generator=g)
    risk = torch.rand(n, generator=g)
    return batch, status, severity, risk


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "ml/configs/multimodal.yaml"))
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()
    raw = yaml.safe_load(Path(args.config).read_text())
    set_seed(raw["seed"])
    cfg = MultimodalConfig(
        embedding_dim=raw["embedding_dim"],
        num_heads=raw["num_heads"],
        dropout=raw["dropout"],
        dietary_encoder=raw["modalities"]["dietary"]["encoder"],
        anthro_dim=raw["modalities"]["anthropometric"]["input_dim"],
        socio_dim=raw["modalities"]["socioeconomic"]["input_dim"],
        diet_dim=raw["modalities"]["dietary"]["input_dim"],
        health_dim=raw["modalities"]["maternal_child_health"]["input_dim"],
        n_status=raw["heads"]["status"],
        n_severity=raw["heads"]["severity"],
    )
    model = MultimodalCrossAttention(cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=raw["training"]["lr"], weight_decay=raw["training"]["weight_decay"])
    ce = nn.CrossEntropyLoss()
    bce = nn.BCELoss()
    epochs = args.epochs or min(raw["training"]["epochs"], 8)
    history = []
    for epoch in range(epochs):
        model.train()
        batch, status, severity, risk = synthetic_batch(64, cfg, seed=raw["seed"] + epoch)
        out = model(batch)
        loss = ce(out["status_logits"], status) + ce(out["severity_logits"], severity) + bce(out["risk"], risk)
        opt.zero_grad()
        loss.backward()
        opt.step()
        history.append({"epoch": epoch, "loss": float(loss.detach())})
    out_dir = ROOT / raw["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = {"state_dict": model.state_dict(), "config": cfg.__dict__, "history": history, "seed": raw["seed"]}
    torch.save(ckpt, out_dir / "multimodal.pt")
    (out_dir / "train_log.json").write_text(json.dumps(history, indent=2))
    print(json.dumps({"saved": str(out_dir / "multimodal.pt"), "last_loss": history[-1]["loss"]}))


if __name__ == "__main__":
    main()
