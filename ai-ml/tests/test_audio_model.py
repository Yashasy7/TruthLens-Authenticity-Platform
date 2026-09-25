"""
TruthLens AI/ML — Module 07 Tests: AASIST Audio Classifier & Checkpoint Validation
"""

from pathlib import Path
import numpy as np
import pytest
import torch

from config.settings import settings
from services.audio_analysis.model import (
    AASISTAudioClassifier,
    format_log_mel_tensor,
    load_audio_classifier,
    predict_synthetic_voice_probability,
)


class TestAudioModel:
    """AASIST classifier architecture and checkpoint enforcement tests."""

    def test_model_architecture_and_forward_pass(self):
        model = AASISTAudioClassifier(n_mels=80, embedding_dim=128)
        model.eval()

        batch_tensor = torch.randn(2, 1, 80, 128)
        with torch.no_grad():
            logits = model(batch_tensor)

        assert logits.shape == (2, 2)
        probs = torch.softmax(logits, dim=-1)
        assert probs.shape == (2, 2)
        assert torch.all(probs >= 0.0)
        assert torch.all(probs <= 1.0)
        # Sum to 1.0
        assert torch.allclose(probs.sum(dim=-1), torch.ones(2), atol=1e-5)

    def test_format_log_mel_tensor_padding_and_standardization(self):
        # Shorter than 128 frames
        short_mel = np.random.randn(80, 50).astype(np.float32)
        tensor_short = format_log_mel_tensor(short_mel, target_frames=128)
        assert tensor_short.shape == (1, 1, 80, 128)

        # Longer than 128 frames
        long_mel = np.random.randn(80, 200).astype(np.float32)
        tensor_long = format_log_mel_tensor(long_mel, target_frames=128)
        assert tensor_long.shape == (1, 1, 80, 128)

        # Mean should be close to 0.0 and std close to 1.0
        assert abs(tensor_long.mean().item()) < 0.1
        assert abs(tensor_long.std().item() - 1.0) < 0.1

    def test_predict_synthetic_voice_probability(self):
        model = AASISTAudioClassifier(n_mels=80)
        tensor = torch.randn(1, 1, 80, 128)
        prob = predict_synthetic_voice_probability(tensor, model=model)

        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_development_fallback_when_checkpoint_missing(self):
        model, metadata = load_audio_classifier(
            checkpoint_path="",
            require_checkpoint=False,
        )
        assert isinstance(model, AASISTAudioClassifier)
        assert metadata["checkpoint_loaded"] is False
        assert "untrained" in metadata["model_version"]

    def test_strict_checkpoint_enforcement_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError, match="Production checkpoint required"):
            load_audio_classifier(
                checkpoint_path="nonexistent_production_audio_checkpoint.pt",
                require_checkpoint=True,
            )

    def test_checkpoint_save_and_load_cycle(self, tmp_path):
        model = AASISTAudioClassifier(n_mels=80)
        ckpt_path = tmp_path / "test_audio_checkpoint.pt"

        checkpoint_data = {
            "model_name": "TruthLens-AASIST-AudioClassifier",
            "model_version": "1.0.0-test",
            "architecture": "AASISTAudioClassifier",
            "n_mels": 80,
            "state_dict": model.state_dict(),
            "metadata": {"test": True},
        }
        torch.save(checkpoint_data, ckpt_path)

        loaded_model, metadata = load_audio_classifier(
            checkpoint_path=str(ckpt_path),
            require_checkpoint=True,
        )
        assert metadata["checkpoint_loaded"] is True
        assert metadata["model_version"] == "1.0.0-test"
        assert metadata["model_name"] == "TruthLens-AASIST-AudioClassifier"
