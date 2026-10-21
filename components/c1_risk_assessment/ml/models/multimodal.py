from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from ml.models.cross_attention import CrossModalAttentionFusion
from ml.models.encoders import ModalityEncoder, TabNetStyleDietaryEncoder


@dataclass
class MultimodalConfig:
    embedding_dim: int = 128
    num_heads: int = 4
    dropout: float = 0.1
    anthro_dim: int = 7
    socio_dim: int = 8
    diet_dim: int = 10
    health_dim: int = 7
    n_status: int = 4
    n_severity: int = 4
    dietary_encoder: str = "mlp"
    use_cross_attention: bool = True


class ConcatenationMLP(nn.Module):
    """Neural baseline that concatenates raw (or encoded) features without attention."""

    def __init__(self, input_dim: int, embedding_dim: int = 128, n_status: int = 4, n_severity: int = 4, dropout: float = 0.2):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, embedding_dim),
            nn.GELU(),
        )
        self.status_head = nn.Linear(embedding_dim, n_status)
        self.severity_head = nn.Linear(embedding_dim, n_severity)
        self.risk_head = nn.Linear(embedding_dim, 1)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.backbone(x)
        return {
            "embedding": h,
            "status_logits": self.status_head(h),
            "severity_logits": self.severity_head(h),
            "risk": torch.sigmoid(self.risk_head(h)).squeeze(-1),
        }


class MultimodalCrossAttention(nn.Module):
    def __init__(self, cfg: MultimodalConfig):
        super().__init__()
        self.cfg = cfg
        d = cfg.embedding_dim
        self.anthro = ModalityEncoder(cfg.anthro_dim, d, dropout=cfg.dropout)
        self.socio = ModalityEncoder(cfg.socio_dim, d, dropout=cfg.dropout)
        if cfg.dietary_encoder == "tabnet_style":
            self.diet = TabNetStyleDietaryEncoder(cfg.diet_dim, d, dropout=cfg.dropout)
        else:
            self.diet = ModalityEncoder(cfg.diet_dim, d, dropout=cfg.dropout)
        self.health = ModalityEncoder(cfg.health_dim, d, dropout=cfg.dropout)
        self.fusion = CrossModalAttentionFusion(d, cfg.num_heads, cfg.dropout)
        self.concat_proj = nn.Sequential(nn.Linear(d * 4, d), nn.GELU())
        self.status_head = nn.Linear(d, cfg.n_status)
        self.severity_head = nn.Linear(d, cfg.n_severity)
        self.risk_head = nn.Linear(d, 1)
        self.use_cross_attention = cfg.use_cross_attention

    @classmethod
    def from_config(cls, raw: dict) -> "MultimodalCrossAttention":
        cfg = MultimodalConfig(**{k: v for k, v in raw.items() if k in MultimodalConfig.__dataclass_fields__})
        return cls(cfg)

    def encode_modalities(self, batch: dict[str, torch.Tensor]) -> list[torch.Tensor]:
        return [
            self.anthro(batch["anthropometric"]),
            self.socio(batch["socioeconomic"]),
            self.diet(batch["dietary"]),
            self.health(batch["maternal_child_health"]),
        ]

    def forward(self, batch: dict[str, torch.Tensor], ablation: str | None = None) -> dict[str, torch.Tensor]:
        tokens = self.encode_modalities(batch)
        if ablation == "no_anthropometric":
            tokens[0] = torch.zeros_like(tokens[0])
        elif ablation == "no_socioeconomic":
            tokens[1] = torch.zeros_like(tokens[1])
        elif ablation == "no_dietary":
            tokens[2] = torch.zeros_like(tokens[2])
        elif ablation == "no_maternal_health":
            tokens[3] = torch.zeros_like(tokens[3])
        stacked = torch.stack(tokens, dim=1)
        if self.use_cross_attention and ablation != "no_cross_attention":
            fused, attn = self.fusion(stacked)
        else:
            fused = self.concat_proj(torch.cat(tokens, dim=-1))
            attn = None
        return {
            "embedding": fused,
            "attention": attn,
            "status_logits": self.status_head(fused),
            "severity_logits": self.severity_head(fused),
            "risk": torch.sigmoid(self.risk_head(fused)).squeeze(-1),
        }
