"""
TruthLens AI/ML — Noise Variance & FFT Frequency Anomaly Engine
Blueprint: Module 05 — "noise variance calculator"
           Section J S2 — "noise variance, FFT frequencies"

Two complementary approaches are implemented:

1. Laplacian-based noise variance (spatial domain):
   - Applies a Laplacian filter to extract high-frequency content.
   - Variance of the Laplacian response is a well-established blur/noise proxy.
   - Synthetic AI images (Diffusion / GANs) often exhibit abnormally low or
     unnaturally uniform noise compared to optically-captured photographs.

2. FFT high-frequency energy ratio (frequency domain):
   - Computes the 2-D Fast Fourier Transform of the luminance channel.
   - Calculates the ratio of energy in the outer high-frequency ring vs total
     energy.
   - AI-generated images frequently show characteristic frequency-domain
     artefacts (periodic grid noise, spectral smoothing).
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def calculate_noise_variance(pil_image: Image.Image) -> float:
    """
    Estimate image noise using the Laplacian variance method.

    Args:
        pil_image: Source image (RGB).

    Returns:
        noise_variance — float >= 0. Higher values indicate more granular /
        organic noise (consistent with authentic camera images). Very low
        values can indicate AI-smoothed synthesis.
    """
    gray = cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = float(laplacian.var())
    logger.debug("Laplacian noise variance: %.6f", variance)
    return variance


def calculate_fft_high_freq_ratio(pil_image: Image.Image) -> float:
    """
    Compute the ratio of FFT high-frequency energy to total energy.

    Args:
        pil_image: Source image (RGB).

    Returns:
        float [0.0, 1.0] — fraction of spectral energy in the high-frequency
        ring. Unexpectedly low values in this ratio for detailed images can
        indicate AI-smoothed synthesis.
    """
    gray = cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = gray.shape

    # Shift zero-frequency component to centre
    f_transform = np.fft.fft2(gray)
    f_shifted = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shifted)

    # High-frequency ring: outer 25% radius
    cy, cx = h // 2, w // 2
    radius = min(h, w) // 2
    high_freq_threshold = 0.75  # fraction of max radius

    y_idx, x_idx = np.ogrid[:h, :w]
    dist_from_centre = np.sqrt((y_idx - cy) ** 2 + (x_idx - cx) ** 2)

    high_freq_mask = dist_from_centre > (high_freq_threshold * radius)
    total_energy = float(magnitude.sum())
    if total_energy == 0:
        return 0.0

    high_freq_energy = float(magnitude[high_freq_mask].sum())
    ratio = high_freq_energy / total_energy
    logger.debug("FFT high-frequency energy ratio: %.6f", ratio)
    return float(np.clip(ratio, 0.0, 1.0))
