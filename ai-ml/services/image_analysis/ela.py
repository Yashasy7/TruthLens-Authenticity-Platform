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
  5. Derive a heuristic manipulation risk score from regional residual disparity:
     - Authentically-shot JPEG images have already been compressed once; a
       second compression causes uniform low residuals.
     - Manipulated / composited regions edited at different compression levels
       produce disproportionately high residuals.

Format Handling (PNG vs JPEG):
  - ELA fundamentally operates on lossy JPEG quantization tables.
  - When given an uncompressed / lossless PNG, ELA recompression reflects synthetic
    quantization of a pristine raster rather than historical tampering.
  - The engine detects format and explicitly flags whether ELA is applicable.
"""

from __future__ import annotations

import io
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

# Normalisation constant: mean ELA value that maps to manipulation_prob ≈ 1.0
_ELA_MAX_EXPECTED_MEAN: float = 25.0


@dataclass(frozen=True)
class ElaAnalysisResult:
    """Detailed forensic result of Error Level Analysis."""
    heatmap_bgr: np.ndarray
    manipulation_prob: float
    is_applicable: bool
    is_suspicious: bool
    mean_error: float
    regional_disparity: float
    format_detected: str
    disclaimer: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("heatmap_bgr", None)
        return d


def analyze_ela(
    pil_image: Image.Image,
    quality: int | None = None,
    original_format: Optional[str] = None,
) -> ElaAnalysisResult:
    """
    Execute comprehensive Error Level Analysis on a PIL Image.

    Args:
        pil_image: Source image in RGB.
        quality: JPEG re-save quality (1–95). Defaults to settings.ela_quality.
        original_format: Optional string format (e.g. 'PNG', 'JPEG'). If None,
                         inferred from pil_image.format or metadata.

    Returns:
        ElaAnalysisResult with heatmap, risk score, applicability, and forensic details.
    """
    if quality is None:
        quality = settings.ela_quality

    fmt = (original_format or getattr(pil_image, "format", None) or "UNKNOWN").upper()
    is_png_or_lossless = fmt in ("PNG", "BMP", "TIFF", "RGBA")

    # Step 1: Save original to in-memory buffer as high-quality baseline
    orig_buf = io.BytesIO()
    pil_image.convert("RGB").save(orig_buf, format="JPEG", quality=95)
    orig_buf.seek(0)
    orig_array = np.array(Image.open(orig_buf).convert("RGB"), dtype=np.int32)

    # Step 2: Re-save at reduced quality (simulates another compression step)
    recomp_buf = io.BytesIO()
    pil_image.convert("RGB").save(recomp_buf, format="JPEG", quality=quality)
    recomp_buf.seek(0)
    recomp_array = np.array(Image.open(recomp_buf).convert("RGB"), dtype=np.int32)

    # Step 3: Absolute difference
    ela_diff = np.abs(orig_array - recomp_array).astype(np.float32)

    # Step 4: Scale to 0–255 for visibility (preserve relative magnitudes)
    max_val = float(ela_diff.max())
    if max_val > 0:
        ela_scaled = (ela_diff / max_val * 255.0).astype(np.uint8)
    else:
        ela_scaled = ela_diff.astype(np.uint8)

    # Step 5: Grayscale → colour heatmap using COLORMAP_JET (blue=low, red=high)
    ela_gray = cv2.cvtColor(ela_scaled, cv2.COLOR_RGB2GRAY)
    heatmap_bgr = cv2.applyColorMap(ela_gray, cv2.COLORMAP_JET)

    # Step 6: Derive localized regional disparity across an 8x8 grid
    diff_mag = np.mean(ela_diff, axis=2)
    h, w = diff_mag.shape
    rows, cols = 8, 8
    ph, pw = max(h // rows, 2), max(w // cols, 2)

    patch_means: List[float] = []
    for r in range(rows):
        for c in range(cols):
            p = diff_mag[r * ph : min((r + 1) * ph, h), c * pw : min((c + 1) * pw, w)]
            if p.size > 0:
                patch_means.append(float(np.mean(p)))

    mean_ela = float(np.mean(diff_mag))
    disparity = 0.0
    manipulation_prob = 0.0
    is_suspicious = False

    if len(patch_means) >= 4:
        p_arr = np.array(patch_means, dtype=np.float64)
        med_val = float(np.median(p_arr))
        top_val = float(np.percentile(p_arr, 90))
        disparity = float((top_val - med_val) / (med_val + 1.0))

        if not is_png_or_lossless:
            # For JPEG images: localized disparity indicates potential re-compression boundaries
            if disparity > 0.60:
                manipulation_prob = float(np.clip((disparity - 0.60) / 1.40, 0.0, 1.0))
                is_suspicious = bool(manipulation_prob >= 0.40)
            else:
                manipulation_prob = 0.0
        else:
            # Lossless PNG: ELA is not calibrated; suppress false positive tampering alerts
            manipulation_prob = 0.0
            is_suspicious = False

    if is_png_or_lossless:
        disclaimer = (
            "Source is lossless or PNG format. ELA relies on differential lossy JPEG quantization tables. "
            "Residuals represent synthetic first-generation compression and are not evidence of tampering."
        )
        is_applicable = False
    else:
        disclaimer = (
            "ELA indicates differential JPEG compression error. High regional disparity suggests potential "
            "compositing or splicing, but should be corroborated with noise and keypoint evidence."
        )
        is_applicable = True

    details: Dict[str, Any] = {
        "mean_error_magnitude": round(mean_ela, 4),
        "max_error_magnitude": round(max_val, 4),
        "regional_disparity": round(disparity, 4),
        "patches_evaluated": len(patch_means),
        "recompression_quality": quality,
        "is_heuristic": True,
    }

    logger.debug(
        "ELA complete | format=%s applicable=%s mean_ela=%.4f disp=%.4f prob=%.4f",
        fmt, is_applicable, mean_ela, disparity, manipulation_prob,
    )

    return ElaAnalysisResult(
        heatmap_bgr=heatmap_bgr,
        manipulation_prob=round(manipulation_prob, 4),
        is_applicable=is_applicable,
        is_suspicious=is_suspicious,
        mean_error=round(mean_ela, 4),
        regional_disparity=round(disparity, 4),
        format_detected=fmt,
        disclaimer=disclaimer,
        details=details,
    )


def generate_ela(
    pil_image: Image.Image,
    quality: int | None = None,
) -> Tuple[np.ndarray, float]:
    """
    Backwards-compatible wrapper returning (heatmap_bgr, manipulation_prob).
    """
    res = analyze_ela(pil_image, quality=quality)
    return res.heatmap_bgr, res.manipulation_prob
