from __future__ import annotations

import numpy as np
import torch
from torch import nn


class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.log_temp = nn.Parameter(torch.zeros(1))

    @property
    def temperature(self) -> torch.Tensor:
        return self.log_temp.exp()

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperature

    def fit(self, logits: torch.Tensor, targets: torch.Tensor, max_iter: int = 200) -> float:
        opt = torch.optim.LBFGS([self.log_temp], lr=0.1, max_iter=max_iter)
        nll = nn.CrossEntropyLoss()

        def closure():
            opt.zero_grad()
            loss = nll(self.forward(logits), targets)
            loss.backward()
            return loss

        opt.step(closure)
        with torch.no_grad():
            return float(nll(self.forward(logits), targets))
