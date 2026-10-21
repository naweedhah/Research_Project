import torch

from ml.models.cross_attention import CrossModalAttentionFusion
from ml.models.multimodal import MultimodalConfig, MultimodalCrossAttention


def test_cross_attention_forward_shapes():
    fusion = CrossModalAttentionFusion(embedding_dim=128, num_heads=4)
    tokens = torch.randn(2, 4, 128)
    fused, weights = fusion(tokens)
    assert fused.shape == (2, 128)
    assert weights.shape[-1] == 4


def test_multimodal_embedding_dimension_configurable():
    for dim in (64, 128):
        cfg = MultimodalConfig(embedding_dim=dim, num_heads=4)
        model = MultimodalCrossAttention(cfg)
        batch = {
            "anthropometric": torch.randn(3, cfg.anthro_dim),
            "socioeconomic": torch.randn(3, cfg.socio_dim),
            "dietary": torch.randn(3, cfg.diet_dim),
            "maternal_child_health": torch.randn(3, cfg.health_dim),
        }
        out = model(batch)
        assert out["embedding"].shape == (3, dim)
        assert out["status_logits"].shape[-1] == 4
        assert out["severity_logits"].shape[-1] == 4
        assert out["risk"].min() >= 0 and out["risk"].max() <= 1


def test_ablation_without_cross_attention_still_runs():
    cfg = MultimodalConfig(embedding_dim=64, num_heads=4, use_cross_attention=True)
    model = MultimodalCrossAttention(cfg)
    batch = {
        "anthropometric": torch.randn(1, cfg.anthro_dim),
        "socioeconomic": torch.randn(1, cfg.socio_dim),
        "dietary": torch.randn(1, cfg.diet_dim),
        "maternal_child_health": torch.randn(1, cfg.health_dim),
    }
    out = model(batch, ablation="no_cross_attention")
    assert out["embedding"].shape[-1] == 64
