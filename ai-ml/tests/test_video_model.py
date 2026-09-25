"""
Tests for services/video_analysis/model.py
Module 06 — 3D-CNN Video Deepfake Classifier
"""

from pathlib import Path
import pytest
import torch

from config.settings import settings
from services.video_analysis.model import (
    get_video_model_metadata,
    load_video_model,
    predict_video_clip,
    reset_video_model,
)


@pytest.fixture(autouse=True)
def cleanup_video_model():
    reset_video_model()
    prev_ckpt = settings.video_classifier_checkpoint
    prev_req = settings.require_video_checkpoint
    yield
    reset_video_model()
    settings.video_classifier_checkpoint = prev_ckpt
    settings.require_video_checkpoint = prev_req


class TestVideoModel:

    def test_video_model_loads_without_error(self):
        model = load_video_model()
        assert model is not None
        assert not model.training

    def test_video_model_singleton_caching(self):
        m1 = load_video_model()
        m2 = load_video_model()
        assert m1 is m2

    def test_predict_video_clip_probability_range(self):
        clip = torch.zeros(1, 3, 8, 112, 112)
        prob = predict_video_clip(clip)
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_predict_video_clip_no_gradient(self):
        clip = torch.randn(1, 3, 8, 112, 112, requires_grad=True)
        prob = predict_video_clip(clip)
        assert clip.grad is None
        assert isinstance(prob, float)

    def test_predict_deterministic_on_same_input(self):
        torch.manual_seed(99)
        clip = torch.randn(1, 3, 8, 112, 112)
        p1 = predict_video_clip(clip)
        p2 = predict_video_clip(clip)
        assert p1 == p2

    def test_missing_checkpoint_fails_fast_when_required(self):
        settings.video_classifier_checkpoint = "missing_3dcnn_weights.pt"
        settings.require_video_checkpoint = True
        reset_video_model()

        with pytest.raises(FileNotFoundError) as exc_info:
            load_video_model()
        assert "not found" in str(exc_info.value)

    def test_load_custom_checkpoint_and_version(self, tmp_path: Path):
        model = load_video_model()
        ckpt_path = tmp_path / "custom_3dcnn.pt"

        # Save checkpoint payload
        payload = {
            "model_state_dict": model.state_dict(),
            "model_version": "2.0.0-custom",
        }
        torch.save(payload, str(ckpt_path))

        settings.video_classifier_checkpoint = str(ckpt_path)
        reset_video_model()

        loaded_model = load_video_model()
        assert loaded_model is not None

        name, version = get_video_model_metadata()
        assert version == "2.0.0-custom"
