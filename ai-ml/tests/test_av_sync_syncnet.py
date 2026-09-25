"""
TruthLens AI/ML — Module 08: SyncNet Architecture & Evaluator Unit Tests
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from services.av_sync.syncnet import (
    SyncNetVisualNet,
    SyncNetAudioNet,
    SyncNetDualModel,
    SyncNetEvaluator,
)


def test_visual_net_forward():
    """Visual stream processes 5-frame 96x96 grayscale visemes to 128-d unit vector."""
    net = SyncNetVisualNet(embedding_dim=128)
    net.eval()
    x = torch.randn(2, 5, 96, 96)
    with torch.no_grad():
        out = net(x)
    assert out.shape == (2, 128)
    # Check L2 unit normalization
    norms = torch.norm(out, p=2, dim=-1)
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5)


def test_audio_net_forward():
    """Audio stream processes 80-mel x 20-frame spectrograms to 128-d unit vector."""
    net = SyncNetAudioNet(embedding_dim=128)
    net.eval()
    x = torch.randn(2, 1, 80, 20)
    with torch.no_grad():
        out = net(x)
    assert out.shape == (2, 128)
    # Check L2 unit normalization
    norms = torch.norm(out, p=2, dim=-1)
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5)


def test_syncnet_dual_model_metric_distance():
    """Dual model computes Euclidean distance between visual and audio embeddings in [0, 2]."""
    model = SyncNetDualModel(embedding_dim=128)
    model.eval()
    v_in = torch.randn(3, 5, 96, 96)
    a_in = torch.randn(3, 1, 80, 20)

    with torch.no_grad():
        v_emb, a_emb = model(v_in, a_in)
        dist = model.euclidean_distance(v_emb, a_emb)

    assert dist.shape == (3,)
    assert (dist >= 0.0).all()
    assert (dist <= 2.0 + 1e-4).all()


def test_syncnet_evaluator_dev_mode():
    """Evaluator initializes deterministically without checkpoint in development mode."""
    evaluator = SyncNetEvaluator(checkpoint_path=None, require_checkpoint=False)
    assert evaluator.is_production_checkpoint is False
    assert "-dev" in evaluator.model_version
    assert evaluator.model is not None


def test_syncnet_evaluator_strict_mode_fails_fast():
    """Strict mode raises FileNotFoundError when required checkpoint is missing."""
    with pytest.raises(FileNotFoundError, match="Strict mode enabled"):
        SyncNetEvaluator(checkpoint_path="nonexistent_checkpoint.pt", require_checkpoint=True)


def test_syncnet_evaluator_inference():
    """Evaluator runs shift search over mouth crops and log-Mel spectrogram."""
    evaluator = SyncNetEvaluator(checkpoint_path=None, require_checkpoint=False)

    # 10 mouth crops (each 96x96 uint8)
    mouth_crops = [np.full((96, 96), 128, dtype=np.uint8) for _ in range(10)]
    # (80, 50) log-Mel spectrogram
    log_mel = np.random.randn(80, 50).astype(np.float32)

    res = evaluator.evaluate_video_audio(mouth_crops, log_mel, fps=25.0, max_shift_frames=4)

    assert "best_shift_frames" in res
    assert "best_offset_ms" in res
    assert "min_distance" in res
    assert "confidence" in res
    assert 0.0 <= res["min_distance"] <= 2.0
    assert 0.0 <= res["confidence"] <= 1.0
    assert len(res["shift_distances"]) == 9  # -4 to +4
