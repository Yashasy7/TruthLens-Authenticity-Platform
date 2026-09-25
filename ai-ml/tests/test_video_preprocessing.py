"""
Tests for services/video_analysis/preprocessing.py
Module 06 — Facial Preprocessing & Temporal Tensor Assembly
"""

import numpy as np
import pytest
import torch

from services.video_analysis.preprocessing import (
    create_batch_frame_tensor,
    create_temporal_clip_tensor,
    preprocess_face_crop,
)


class TestVideoPreprocessing:

    def test_preprocess_face_crop_shape_and_dtype(self):
        crop = np.zeros((100, 100, 3), dtype=np.uint8)
        tensor = preprocess_face_crop(crop, target_size=112)
        assert isinstance(tensor, torch.Tensor)
        assert tensor.shape == (3, 112, 112)
        assert tensor.dtype == torch.float32

    def test_preprocess_face_crop_normalization(self):
        # All zeros RGB -> transformed with ImageNet normalization
        crop = np.zeros((64, 64, 3), dtype=np.uint8)
        tensor = preprocess_face_crop(crop, target_size=112)
        # Normalized channel values should be negative since mean was subtracted
        assert tensor.mean().item() < 0.0

    def test_create_temporal_clip_tensor_dimensions(self):
        crops = [np.full((80, 80, 3), i * 20, dtype=np.uint8) for i in range(16)]
        clip = create_temporal_clip_tensor(crops, clip_length=16, target_size=112)
        assert isinstance(clip, torch.Tensor)
        # PyTorch 3D-CNN format: (B, C, T, H, W)
        assert clip.shape == (1, 3, 16, 112, 112)

    def test_temporal_clip_padding_short_sequence(self):
        # 5 crops padded to 16
        crops = [np.zeros((80, 80, 3), dtype=np.uint8) for _ in range(5)]
        clip = create_temporal_clip_tensor(crops, clip_length=16, target_size=112)
        assert clip.shape == (1, 3, 16, 112, 112)

    def test_temporal_clip_subsampling_long_sequence(self):
        # 30 crops downsampled to 16
        crops = [np.zeros((80, 80, 3), dtype=np.uint8) for _ in range(30)]
        clip = create_temporal_clip_tensor(crops, clip_length=16, target_size=112)
        assert clip.shape == (1, 3, 16, 112, 112)

    def test_create_batch_frame_tensor_shape(self):
        crops = [np.zeros((60, 60, 3), dtype=np.uint8) for _ in range(6)]
        batch = create_batch_frame_tensor(crops, target_size=112)
        assert batch.shape == (6, 3, 112, 112)

    def test_create_temporal_clip_empty_raises_error(self):
        with pytest.raises(ValueError):
            create_temporal_clip_tensor([], clip_length=16)
