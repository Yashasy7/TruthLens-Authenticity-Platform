"""
Tests for services/image_analysis/ela.py
Blueprint Section I: pytest unit tests for Python ML services
"""

import io
import numpy as np
import pytest
from PIL import Image

from services.image_analysis.ela import generate_ela


def _make_solid_rgb_image(width: int = 200, height: int = 200, color=(128, 64, 32)) -> Image.Image:
    """Create a solid-colour PIL Image for deterministic testing."""
    img = Image.new("RGB", (width, height), color)
    return img


def _make_gradient_image(width: int = 200, height: int = 200) -> Image.Image:
    """Create a smooth gradient image (low ELA expected)."""
    data = np.tile(
        np.linspace(0, 255, width, dtype=np.uint8),
        (height, 1),
    )
    rgb = np.stack([data, data, data], axis=-1)
    return Image.fromarray(rgb, mode="RGB")


def _make_noisy_image(width: int = 200, height: int = 200) -> Image.Image:
    """Create a random-noise image (higher ELA expected vs smooth)."""
    rng = np.random.default_rng(42)
    data = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    return Image.fromarray(data, mode="RGB")


class TestGenerateELA:

    def test_returns_correct_types(self):
        """generate_ela must return (ndarray, float)."""
        img = _make_solid_rgb_image()
        heatmap, manip_prob = generate_ela(img)
        assert isinstance(heatmap, np.ndarray), "Heatmap should be a numpy array"
        assert isinstance(manip_prob, float), "manipulation_prob should be a float"

    def test_heatmap_shape(self):
        """Heatmap shape must match input image dimensions (H, W, 3)."""
        img = _make_solid_rgb_image(width=150, height=100)
        heatmap, _ = generate_ela(img)
        assert heatmap.shape == (100, 150, 3), f"Unexpected heatmap shape: {heatmap.shape}"

    def test_heatmap_dtype(self):
        """Heatmap must be uint8 for PNG saving."""
        img = _make_solid_rgb_image()
        heatmap, _ = generate_ela(img)
        assert heatmap.dtype == np.uint8, "Heatmap should be uint8"

    def test_manipulation_prob_range(self):
        """manipulation_prob must be in [0.0, 1.0]."""
        for img in [_make_solid_rgb_image(), _make_gradient_image(), _make_noisy_image()]:
            _, manip_prob = generate_ela(img)
            assert 0.0 <= manip_prob <= 1.0, f"manipulation_prob out of range: {manip_prob}"

    def test_solid_image_low_manipulation_prob(self):
        """A uniform solid image has minimal JPEG compression artefacts → low manip_prob."""
        img = _make_solid_rgb_image()
        _, manip_prob = generate_ela(img)
        # Solid images have nearly zero ELA residuals
        assert manip_prob < 0.1, f"Expected low manip_prob for solid image, got {manip_prob}"

    def test_custom_quality_accepted(self):
        """generate_ela should accept a custom quality parameter."""
        img = _make_gradient_image()
        heatmap_75, prob_75 = generate_ela(img, quality=75)
        heatmap_50, prob_50 = generate_ela(img, quality=50)
        assert heatmap_75.shape == heatmap_50.shape
        # Lower quality → higher residuals
        assert prob_50 >= prob_75 - 0.05, "Lower quality should produce >= manipulation_prob"

    def test_square_image(self):
        """ELA should work on square images."""
        img = _make_solid_rgb_image(width=64, height=64)
        heatmap, prob = generate_ela(img)
        assert heatmap.shape == (64, 64, 3)

    def test_small_image(self):
        """ELA should handle small images without error."""
        img = _make_solid_rgb_image(width=16, height=16)
        heatmap, prob = generate_ela(img)
        assert heatmap.shape == (16, 16, 3)
