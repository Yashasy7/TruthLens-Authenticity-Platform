"""
Tests for services/image_analysis/copy_move.py
Module 05 — Copy-Move Forgery & Image Splicing Analysis
"""

import numpy as np
import pytest
from PIL import Image

from services.image_analysis.copy_move import (
    ManipulationAnalysisResult,
    detect_copy_move_and_splicing,
)


@pytest.fixture
def clean_image() -> Image.Image:
    """A natural image texture without copy-move duplication."""
    rng = np.random.default_rng(123)
    y, x = np.mgrid[0:180, 0:180]
    grad = (x * 0.7 + y * 0.5).astype(np.float32)
    noise = rng.normal(0, 15, (180, 180)).astype(np.float32)
    arr = np.clip(grad + noise, 0, 255).astype(np.uint8)
    rgb = np.stack([arr, arr, arr], axis=-1)
    return Image.fromarray(rgb, mode="RGB")



@pytest.fixture
def synthetic_copy_move_image() -> Image.Image:
    """
    Image containing an exact duplicated textured region to simulate copy-move cloning.
    """
    rng = np.random.default_rng(42)
    # Background texture
    base = rng.integers(100, 180, (200, 200, 3), dtype=np.uint8)

    # Distinctive textured patch with strong corners/features
    patch_size = 45
    patch = rng.integers(0, 255, (patch_size, patch_size, 3), dtype=np.uint8)

    # Source location
    base[20 : 20 + patch_size, 20 : 20 + patch_size] = patch
    # Target (cloned) location (spatially separated > 50 px)
    base[120 : 120 + patch_size, 120 : 120 + patch_size] = patch

    return Image.fromarray(base, mode="RGB")


@pytest.fixture
def solid_image() -> Image.Image:
    """Solid color image with zero texture/keypoints."""
    arr = np.full((128, 128, 3), 128, dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


class TestCopyMoveDetection:

    def test_clean_image_no_copy_move(self, clean_image):
        result = detect_copy_move_and_splicing(clean_image)
        assert isinstance(result, ManipulationAnalysisResult)
        assert result.copy_move_detected is False
        assert 0.0 <= result.copy_move_score <= 1.0

    def test_synthetic_copy_move_detected(self, synthetic_copy_move_image):
        result = detect_copy_move_and_splicing(
            synthetic_copy_move_image,
            min_spatial_dist=25.0,
            ratio_threshold=0.85,
            min_inliers_for_detection=4,
        )
        assert isinstance(result, ManipulationAnalysisResult)
        assert result.copy_move_detected is True
        assert result.evidence["ransac_inliers"] >= 4
        assert result.copy_move_score > 0.0

    def test_solid_image_insufficient_keypoints(self, solid_image):
        result = detect_copy_move_and_splicing(solid_image)
        assert result.copy_move_detected is False
        assert result.splicing_detected is False
        assert result.copy_move_score == 0.0
        assert result.evidence["orb_keypoints"] == 0

    def test_tiny_image_graceful_handling(self):
        tiny = Image.new("RGB", (10, 10), "red")
        result = detect_copy_move_and_splicing(tiny)
        assert result.copy_move_detected is False
        assert result.splicing_detected is False
        assert "too small" in result.evidence.get("reason", "")

    def test_deterministic_behavior(self, synthetic_copy_move_image):
        res1 = detect_copy_move_and_splicing(synthetic_copy_move_image)
        res2 = detect_copy_move_and_splicing(synthetic_copy_move_image)
        assert res1.copy_move_detected == res2.copy_move_detected
        assert res1.copy_move_score == res2.copy_move_score
        assert res1.splicing_detected == res2.splicing_detected
        assert res1.splicing_score == res2.splicing_score
        assert res1.evidence["ransac_inliers"] == res2.evidence["ransac_inliers"]

    def test_evidence_dictionary_structure(self, clean_image):
        result = detect_copy_move_and_splicing(clean_image)
        evidence = result.evidence
        assert "orb_keypoints" in evidence
        assert "candidate_matches" in evidence
        assert "ransac_inliers" in evidence
        assert "noise_cv" in evidence
