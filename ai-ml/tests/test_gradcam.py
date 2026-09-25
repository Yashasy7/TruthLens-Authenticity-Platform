"""
Tests for services/image_analysis/gradcam.py
Blueprint Section I: pytest unit tests for Python ML services
"""

import numpy as np
import pytest
import torch
from PIL import Image

from services.image_analysis.classifier import load_model, reset_model
from services.image_analysis.gradcam import generate_gradcam
from utils.image_utils import preprocess_for_model


@pytest.fixture(autouse=True)
def reset_singleton():
    reset_model()
    yield
    reset_model()


def _make_image(width=224, height=224) -> Image.Image:
    rng = np.random.default_rng(7)
    data = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    return Image.fromarray(data, mode="RGB")


class TestGenerateGradCAM:

    def test_returns_numpy_array(self):
        """generate_gradcam must return a numpy ndarray."""
        model = load_model()
        image = _make_image()
        tensor = preprocess_for_model(image)
        result = generate_gradcam(model, tensor, original_size=(224, 224))
        assert isinstance(result, np.ndarray), "Grad-CAM should return numpy array"

    def test_output_shape_matches_original_size(self):
        """Output shape should match the requested original_size (H, W, 3)."""
        model = load_model()
        image = _make_image(width=300, height=200)
        tensor = preprocess_for_model(image)
        result = generate_gradcam(model, tensor, original_size=(300, 200))
        # original_size is (width, height); cv2.resize gives (height, width, 3)
        assert result.shape == (200, 300, 3), f"Unexpected shape: {result.shape}"

    def test_output_dtype_uint8(self):
        """Output must be uint8 for PNG storage."""
        model = load_model()
        image = _make_image()
        tensor = preprocess_for_model(image)
        result = generate_gradcam(model, tensor, original_size=(224, 224))
        assert result.dtype == np.uint8, "Grad-CAM output should be uint8"

    def test_output_values_in_range(self):
        """All pixel values must be in [0, 255]."""
        model = load_model()
        image = _make_image()
        tensor = preprocess_for_model(image)
        result = generate_gradcam(model, tensor, original_size=(224, 224))
        assert result.min() >= 0 and result.max() <= 255

    def test_different_sizes(self):
        """Grad-CAM should resize correctly to different original_size values."""
        model = load_model()
        image = _make_image()
        tensor = preprocess_for_model(image)
        for w, h in [(100, 100), (640, 480), (50, 75)]:
            result = generate_gradcam(model, tensor, original_size=(w, h))
            assert result.shape == (h, w, 3), f"Shape mismatch for size ({w},{h}): {result.shape}"
