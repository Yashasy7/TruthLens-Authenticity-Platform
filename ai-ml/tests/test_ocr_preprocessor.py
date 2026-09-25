"""
TruthLens AI/ML — Module 09: Visual Text Preprocessing Unit Tests
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from services.ocr.preprocessor import ImagePreprocessor, PreprocessedImage


def _create_synthetic_text_image(width: int = 400, height: int = 150, text: str = "BREAKING NEWS") -> np.ndarray:
    """Generate a clean synthetic image with visual text."""
    img = np.full((height, width, 3), 240, dtype=np.uint8)
    # Draw dark text
    cv2.putText(img, text, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3, cv2.LINE_AA)
    return img


def test_preprocess_valid_image():
    """Verify standard preprocessing produces grayscale, binarized, and telemetry attributes."""
    img = _create_synthetic_text_image()
    prep = ImagePreprocessor(max_dimension=1024).preprocess(img)

    assert isinstance(prep, PreprocessedImage)
    assert prep.original_dimensions == (400, 150)
    assert prep.processed_dimensions == (400, 150)
    assert prep.scale_factor == 1.0
    assert prep.gray.shape == (150, 400)
    assert prep.binarized.shape == (150, 400)
    # Binarized contains binary values
    unique_vals = np.unique(prep.binarized)
    assert set(unique_vals).issubset({0, 255})
    assert len(prep.applied_steps) >= 4
    assert any("CLAHE" in s for s in prep.applied_steps)


def test_preprocess_downscaling_large_image():
    """Images exceeding max_dimension are downscaled while preserving aspect ratio."""
    large_img = np.full((3000, 1500, 3), 200, dtype=np.uint8)
    prep = ImagePreprocessor(max_dimension=1000).preprocess(large_img)

    assert prep.original_dimensions == (1500, 3000)
    assert max(prep.processed_dimensions) <= 1000
    assert prep.scale_factor < 1.0
    assert any("Resized" in s for s in prep.applied_steps)


def test_preprocess_deskewing():
    """Deskewing measures angle and straightens tilted text."""
    img = _create_synthetic_text_image(width=500, height=200, text="VERIFIED EVIDENCE")
    # Rotate by 10 degrees
    center = (250, 100)
    rot_mat = cv2.getRotationMatrix2D(center, 10.0, 1.0)
    rotated = cv2.warpAffine(img, rot_mat, (500, 200), borderMode=cv2.BORDER_REPLICATE)

    prep = ImagePreprocessor().preprocess(rotated)
    assert isinstance(prep.skew_angle, float)
    assert prep.gray.shape == (200, 500)


def test_preprocess_empty_image_raises():
    """Empty or None image raises ValueError."""
    preprocessor = ImagePreprocessor()
    with pytest.raises(ValueError, match="empty or invalid"):
        preprocessor.preprocess(np.array([], dtype=np.uint8))
