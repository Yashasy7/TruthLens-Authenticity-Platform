"""
Tests for services/image_analysis/noise.py
Blueprint Section I: pytest unit tests for Python ML services
"""

import numpy as np
import pytest
from PIL import Image

from services.image_analysis.noise import (
    calculate_fft_high_freq_ratio,
    calculate_noise_variance,
)


def _solid_image(width=128, height=128, color=(128, 128, 128)) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def _noisy_image(width=128, height=128, seed=42) -> Image.Image:
    rng = np.random.default_rng(seed)
    data = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    return Image.fromarray(data, mode="RGB")


def _gradient_image(width=128, height=128) -> Image.Image:
    data = np.tile(np.linspace(0, 255, width, dtype=np.uint8), (height, 1))
    rgb = np.stack([data, data, data], axis=-1)
    return Image.fromarray(rgb, mode="RGB")


class TestCalculateNoiseVariance:

    def test_returns_float(self):
        img = _solid_image()
        result = calculate_noise_variance(img)
        assert isinstance(result, float), "noise_variance should be a float"

    def test_non_negative(self):
        for img in [_solid_image(), _noisy_image(), _gradient_image()]:
            result = calculate_noise_variance(img)
            assert result >= 0.0, f"noise_variance must be >= 0, got {result}"

    def test_solid_image_very_low_variance(self):
        """Uniform image has zero Laplacian response."""
        img = _solid_image(color=(100, 100, 100))
        variance = calculate_noise_variance(img)
        assert variance < 1.0, f"Solid image should have near-zero variance, got {variance}"

    def test_noisy_image_higher_than_solid(self):
        """Random noise image should have significantly higher variance than a solid image."""
        solid_var = calculate_noise_variance(_solid_image())
        noisy_var = calculate_noise_variance(_noisy_image())
        assert noisy_var > solid_var, (
            f"Noisy image variance ({noisy_var}) should exceed solid image ({solid_var})"
        )


class TestCalculateFFTHighFreqRatio:

    def test_returns_float(self):
        img = _solid_image()
        result = calculate_fft_high_freq_ratio(img)
        assert isinstance(result, float), "FFT ratio should be a float"

    def test_range_zero_to_one(self):
        for img in [_solid_image(), _noisy_image(), _gradient_image()]:
            result = calculate_fft_high_freq_ratio(img)
            assert 0.0 <= result <= 1.0, f"FFT ratio out of range: {result}"

    def test_noisy_has_higher_ratio_than_solid(self):
        """
        Random noise images contain significant high-frequency energy.
        Solid images have nearly zero high-frequency content.
        """
        solid_ratio = calculate_fft_high_freq_ratio(_solid_image())
        noisy_ratio = calculate_fft_high_freq_ratio(_noisy_image())
        assert noisy_ratio > solid_ratio, (
            f"Noisy ratio ({noisy_ratio}) should exceed solid ratio ({solid_ratio})"
        )
