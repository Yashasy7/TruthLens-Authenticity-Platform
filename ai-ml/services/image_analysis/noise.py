"""
TruthLens AI/ML — Noise Variance & FFT Frequency Anomaly Engine
Blueprint: Module 05 — "noise variance calculator"
           Section J S2 — "noise variance, FFT frequencies"

Two complementary forensic approaches:
1. Laplacian & High-Pass Noise Residual Analysis (spatial domain):
   - Computes local high-pass residual ($I - \text{smooth}(I)$).
   - Calculates patch-level noise variance to map sensor noise uniformity.
   - Spliced composites or AI-generated inpainting often exhibit localized noise voids
     or sharp noise-level discontinuities.

2. FFT 2-D Spectral Analysis (frequency domain):
   - Computes 2-D Fast Fourier Transform log-magnitude spectrum.
   - Analyzes outer high-frequency energy ratio and azimuthal distribution.
   - Detects periodic grid artefacts (GAN upsampling, checkerboard patterns)
     and abnormal high-frequency spectral roll-offs (diffusion de-noising blur).

Heuristic Nature Disclaimer:
   - Noise and FFT measurements are heuristic physical indicators.
   - Natural texture variations, depth-of-field bokeh, and camera ISO settings
     influence noise variance; these values are never represented as calibrated
     manipulation probabilities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def calculate_noise_variance(pil_image: Image.Image) -> float:
    """
    Estimate global image noise variance using the Laplacian variance method.

    Args:
        pil_image: Source image (RGB).

    Returns:
        float >= 0. Lower values indicate smoother or synthetic textures;
        higher values indicate organic camera sensor grain.
    """
    gray = cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = float(laplacian.var())
    logger.debug("Laplacian noise variance: %.6f", variance)
    return float(variance)


def calculate_fft_high_freq_ratio(pil_image: Image.Image) -> float:
    """
    Compute the fraction of spectral energy in the outer 25% high-frequency ring.

    Args:
        pil_image: Source image (RGB).

    Returns:
        float [0.0, 1.0]. Abnormally low values in detailed scenes can indicate
        diffusion de-noising smoothing.
    """
    gray = cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = gray.shape

    f_transform = np.fft.fft2(gray)
    f_shifted = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shifted)

    cy, cx = h // 2, w // 2
    radius = min(h, w) // 2
    high_freq_threshold = 0.75

    y_idx, x_idx = np.ogrid[:h, :w]
    dist_from_centre = np.sqrt((y_idx - cy) ** 2 + (x_idx - cx) ** 2)

    high_freq_mask = dist_from_centre > (high_freq_threshold * radius)
    total_energy = float(magnitude.sum())
    if total_energy == 0:
        return 0.0

    high_freq_energy = float(magnitude[high_freq_mask].sum())
    ratio = float(high_freq_energy / total_energy)
    logger.debug("FFT high-frequency energy ratio: %.6f", ratio)
    return float(np.clip(ratio, 0.0, 1.0))


def generate_noise_map(pil_image: Image.Image) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Generate a visual spatial noise-residual inconsistency heatmap and metrics.

    Args:
        pil_image: Source image (RGB).

    Returns:
        Tuple of:
            heatmap_bgr — uint8 numpy array (H, W, 3) BGR colour-mapped noise map.
            metrics — dict of spatial noise statistics.
    """
    rgb = np.array(pil_image.convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = gray.shape

    # High-pass residual: difference from 5x5 Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)
    residual = np.abs(gray - blurred)

    # Local variance map (9x9 box filter)
    kernel = np.ones((9, 9), np.float32) / 81.0
    mean_sq = cv2.filter2D(residual ** 2, -1, kernel)
    sq_mean = cv2.filter2D(residual, -1, kernel) ** 2
    local_var = np.maximum(mean_sq - sq_mean, 0.0)

    # Normalize to 0-255 for color mapping
    v_max = float(np.percentile(local_var, 99))
    if v_max > 0:
        var_norm = np.clip(local_var / v_max * 255.0, 0, 255).astype(np.uint8)
    else:
        var_norm = local_var.astype(np.uint8)

    heatmap_bgr = cv2.applyColorMap(var_norm, cv2.COLORMAP_INFERNO)

    # Regional inconsistency across 8x8 patches
    rows, cols = 8, 8
    ph, pw = max(h // rows, 2), max(w // cols, 2)
    patch_vars: list[float] = []
    for r in range(rows):
        for c in range(cols):
            p = local_var[r * ph : min((r + 1) * ph, h), c * pw : min((c + 1) * pw, w)]
            if p.size > 0:
                patch_vars.append(float(np.mean(p)))

    p_arr = np.array(patch_vars, dtype=np.float64) if patch_vars else np.array([0.0])
    mean_v = float(np.mean(p_arr))
    std_v = float(np.std(p_arr))
    cv_score = float(std_v / (mean_v + 1e-4))
    laplacian_var = calculate_noise_variance(pil_image)

    metrics = {
        "laplacian_noise_variance": round(laplacian_var, 4),
        "patch_noise_cv": round(cv_score, 4),
        "is_suspicious": bool(cv_score > 0.75),
        "is_heuristic": True,
        "disclaimer": (
            "Noise variance is a heuristic indicator of sensor grain and local compression consistency. "
            "It varies naturally with scene lighting, depth-of-field, and camera sensor ISO."
        ),
    }

    return heatmap_bgr, metrics


def generate_fft_spectrum(pil_image: Image.Image) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Generate a 2-D FFT log-magnitude spectrum visualization and frequency anomaly metrics.

    Args:
        pil_image: Source image (RGB).

    Returns:
        Tuple of:
            spectrum_bgr — uint8 numpy array (H, W, 3) BGR colour-mapped FFT spectrum with cutoff overlay.
            metrics — dict of frequency domain metrics.
    """
    gray = cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = gray.shape

    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = np.abs(fshift)

    # Log-magnitude spectrum: 20 * log(1 + mag)
    log_mag = 20.0 * np.log(1.0 + mag)
    min_val, max_val = float(log_mag.min()), float(log_mag.max())
    if max_val > min_val:
        spec_norm = ((log_mag - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
    else:
        spec_norm = np.zeros((h, w), dtype=np.uint8)

    spectrum_bgr = cv2.applyColorMap(spec_norm, cv2.COLORMAP_VIRIDIS)

    # Draw high-frequency cutoff circle for visual forensic reference
    cy, cx = h // 2, w // 2
    radius = int(min(h, w) // 2 * 0.75)
    cv2.circle(spectrum_bgr, (cx, cy), radius, (0, 255, 255), 1, cv2.LINE_AA)

    high_freq_ratio = calculate_fft_high_freq_ratio(pil_image)

    # Detect spectral periodicity / spikes (GAN grid artefacts)
    # Exclude DC center (radius 10px) and compare peak to median in high band
    y_idx, x_idx = np.ogrid[:h, :w]
    dist = np.sqrt((y_idx - cy) ** 2 + (x_idx - cx) ** 2)
    outer_band = (dist > radius) & (dist < min(h, w) // 2)
    if np.sum(outer_band) > 0:
        band_mag = mag[outer_band]
        peak_to_med = float(np.max(band_mag) / (np.median(band_mag) + 1e-4))
    else:
        peak_to_med = 1.0

    has_frequency_spikes = bool(peak_to_med > 15.0)
    total_energy = float(mag.sum())

    if float(np.std(gray)) < 1.0 or total_energy <= 1e-6:
        # Uniform/blank image has no spatial variation rather than a spectral anomaly
        fft_anomaly_score = 0.0
        is_fft_suspicious = False
    else:
        spike_factor = float(np.clip((peak_to_med - 8.0) / 20.0, 0.0, 1.0))
        depletion_factor = float(np.clip((0.05 - high_freq_ratio) / 0.05, 0.0, 1.0)) * 0.5
        fft_anomaly_score = round(float(np.clip(max(spike_factor, depletion_factor), 0.0, 1.0)), 4)
        is_fft_suspicious = bool(has_frequency_spikes or high_freq_ratio < 0.03)

    metrics = {
        "fft_high_freq_ratio": round(high_freq_ratio, 4),
        "high_frequency_ratio": round(high_freq_ratio, 4),
        "fft_anomaly_score": fft_anomaly_score,
        "peak_to_median_spectral_ratio": round(peak_to_med, 4),
        "has_periodic_spikes": has_frequency_spikes,
        "is_suspicious": is_fft_suspicious,
        "is_heuristic": True,
        "disclaimer": (
            "FFT anomaly score is a heuristic frequency-domain indicator (not a calibrated probability). "
            "Unnatural periodic spectral spikes suggest GAN grid artifacts, while severe high-frequency depletion "
            "can indicate heavy smoothing or diffusion denoising."
        ),
    }

    return spectrum_bgr, metrics
