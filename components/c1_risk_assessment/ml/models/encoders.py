from __future__ import annotations

import torch
from torch import nn


class ModalityEncoder(nn.Module):
    """Dense → LayerNorm → GELU → Dropout → Dense."""

    def __init__(self, input_dim: int, embedding_dim: int = 128, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embedding_dim),
            nn.LayerNorm(embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TabNetStyleDietaryEncoder(nn.Module):
    """Attentive feature transformer approximating a TabNet-style dietary branch.

    This is an experimental architecture option, not a claim of TabNet superiority.
    """

    def __init__(self, input_dim: int, embedding_dim: int = 128, n_steps: int = 3, dropout: float = 0.1):
        super().__init__()
        self.bn = nn.BatchNorm1d(input_dim)
        self.steps = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(input_dim, embedding_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                )
                for _ in range(n_steps)
            ]
        )
        self.attn = nn.Sequential(nn.Linear(input_dim, n_steps), nn.Softmax(dim=-1))
        self.out = nn.Sequential(nn.Linear(embedding_dim, embedding_dim), nn.LayerNorm(embedding_dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.size(0) > 1:
            x = self.bn(x)
        weights = self.attn(x)
        acc = 0
        for i, step in enumerate(self.steps):
            acc = acc + weights[:, i : i + 1] * step(x)
        return self.out(acc)
