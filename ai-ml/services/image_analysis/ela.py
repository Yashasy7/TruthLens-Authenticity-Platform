"""
TruthLens AI/ML — ELA (Error Level Analysis) Engine
Blueprint: Module 05 — "OpenCV ELA heatmap generator"
           Section J S2 — "Error Level Analysis (ELA), JPEG compression quantization"

How ELA works:
  1. Re-save the image as JPEG at a fixed reduced quality.
  2. Compute the pixel-level absolute difference between the original and the
     re-saved copy.
  3. Scale the difference to the full 0–255 range for visibility.
  4. Apply a colour map to produce a human-readable heatmap.
  5. Derive manipulation_prob from the mean ELA magnitude:
     - Authentically-shot JPEG images have already been compressed once; a
       second compression causes uniform low residuals.
     - Manipulated / composited regions that were edited at higher quality
       produce disproportionately high residuals.
"""

from __future__ import annotations

import io
import logging
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

# Normalisation constant: mean ELA value that maps to manipulation_prob ≈ 1.0
# Calibrated empirically on CIFAKE / natural-image pairs (Section K benchmark).
_ELA_MAX_EXPECTED_MEAN: float = 25.0


def generate_ela(
    pil_image: Image.Image,
    quality: int | None = None,
) -> Tuple[np.ndarray, float]:
    """
    Generate an Error Level Analysis heatmap for the given PIL Image.

    Args:
        pil_image: Source image in RGB mode.
        quality:   JPEG re-save quality (1–95). Defaults to settings.ela_quality.

    Returns:
        Tuple of:
            heatmap   — uint8 numpy array (H, W, 3) BGR colour-mapped heatmap.
            manipulation_prob — float [0.0, 1.0] derived from mean ELA magnitude.
    """
    if quality is None:
        quality = settings.ela_quality

    # Step 1: Save original to in-memory buffer and re-read as numpy
    orig_buf = io.BytesIO()
    pil_image.save(orig_buf, format="JPEG", quality=95)
    orig_buf.seek(0)
    orig_array = np.array(Image.open(orig_buf).convert("RGB"), dtype=np.int32)

    # Step 2: Re-save at reduced quality (simulates another compression step)
    recomp_buf = io.BytesIO()
    pil_image.save(recomp_buf, format="JPEG", quality=quality)
    recomp_buf.seek(0)
    recomp_array = np.array(Image.open(recomp_buf).convert("RGB"), dtype=np.int32)

    # Step 3: Absolute difference
    ela_diff = np.abs(orig_array - recomp_array).astype(np.float32)

    # Step 4: Scale to 0–255 for visibility (preserve relative magnitudes)
    max_val = ela_diff.max()
    if max_val > 0:
        ela_scaled = (ela_diff / max_val * 255).astype(np.uint8)
    else:
        ela_scaled = ela_diff.astype(np.uint8)

    # Step 5: Grayscale → colour heatmap using COLORMAP_JET (blue=low, red=high)
    ela_gray = cv2.cvtColor(ela_scaled, cv2.COLOR_RGB2GRAY)
    heatmap_bgr = cv2.applyColorMap(ela_gray, cv2.COLORMAP_JET)

    # Step 6: Derive manipulation_prob from mean ELA magnitude before scaling
    mean_ela = float(ela_diff.mean())
    manipulation_prob = float(min(mean_ela / _ELA_MAX_EXPECTED_MEAN, 1.0))

    logger.debug(
        "ELA complete | quality=%d mean_ela=%.4f manipulation_prob=%.4f",
        quality, mean_ela, manipulation_prob,
    )
    return heatmap_bgr, manipulation_prob
