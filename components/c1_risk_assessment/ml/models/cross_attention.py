from __future__ import annotations

import torch
from torch import nn


class CrossModalAttentionFusion(nn.Module):
    """Learnable fusion query attending over modality embeddings.

    Anthropometric, socioeconomic, dietary and health embeddings are treated as
    tokens. A learnable query token performs multi-head attention over them and
    yields fused embedding e_t. This is a technically defensible cross-modal
    design; whether it outperforms concatenation is an empirical question.
    """

    def __init__(self, embedding_dim: int = 128, num_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        if embedding_dim % num_heads != 0:
            raise ValueError("embedding_dim must be divisible by num_heads")
        self.fusion_query = nn.Parameter(torch.randn(1, 1, embedding_dim) * 0.02)
        self.attn = nn.MultiheadAttention(embedding_dim, num_heads, dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(embedding_dim)
        self.ff = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim * 4, embedding_dim),
        )
        self.norm2 = nn.LayerNorm(embedding_dim)

    def forward(self, modality_tokens: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        modality_tokens: [batch, n_modalities, embedding_dim]
        returns fused e_t [batch, embedding_dim], attn weights [batch, 1, n_modalities]
        """
        batch = modality_tokens.size(0)
        query = self.fusion_query.expand(batch, -1, -1)
        fused, weights = self.attn(query, modality_tokens, modality_tokens, need_weights=True)
        fused = self.norm1(fused + query)
        fused = self.norm2(fused + self.ff(fused))
        return fused.squeeze(1), weights
