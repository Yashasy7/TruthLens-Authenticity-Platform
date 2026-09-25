"""
TruthLens AI/ML — Module 09: Image Preprocessing Pipeline for OCR
Blueprint: Image/Frame -> Binarization Preprocessor -> Tesseract / EasyOCR Engine
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import List, Tuple

import cv2
import numpy as np

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedImage:
    """Container for preprocessed image representations and coordinate mapping telemetry."""
    original_rgb: np.ndarray
    gray: np.ndarray
    binarized: np.ndarray
    scale_factor: float
    skew_angle: float
    applied_steps: List[str]
    original_dimensions: Tuple[int, int]   # (width, height)
    processed_dimensions: Tuple[int, int]  # (width, height)


class ImagePreprocessor:
    """
    OpenCV-based visual text preprocessor implementing:
    1. Dimension check & aspect-ratio preserving scaling.
    2. Grayscale conversion.
    3. Bilateral edge-preserving denoising.
    4. Contrast Limited Adaptive Histogram Equalization (CLAHE).
    5. Text orientation estimation & affine deskewing.
    6. Dual binarization (fusing Otsu global thresholding with adaptive Gaussian thresholding).
    """

    def __init__(
        self,
        max_dimension: Optional[int] = None,
        clahe_clip_limit: float = 2.5,
        clahe_tile_grid_size: Tuple[int, int] = (8, 8),
    ) -> None:
        settings = get_settings()
        self.max_dimension = max_dimension or settings.ocr_max_image_dimension
        self.clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=clahe_tile_grid_size)

    def preprocess(self, img_rgb: np.ndarray) -> PreprocessedImage:
        """
        Execute full OpenCV preprocessing pipeline on an RGB image.

        Args:
            img_rgb: Input RGB image as uint8 numpy array (H, W, 3).

        Returns:
            PreprocessedImage with enhanced grayscale, binarized images, and scaling telemetry.

        Raises:
            ValueError: If input image is empty or degenerate.
        """
        if img_rgb is None or img_rgb.size == 0:
            raise ValueError("Input image is empty or invalid.")

        orig_h, orig_w = img_rgb.shape[:2]
        applied_steps: List[str] = []

        # 1. Dimension check & downscaling
        scale_factor = 1.0
        max_dim = max(orig_h, orig_w)
        if max_dim > self.max_dimension:
            scale_factor = self.max_dimension / float(max_dim)
            new_w = max(1, int(round(orig_w * scale_factor)))
            new_h = max(1, int(round(orig_h * scale_factor)))
            resized_rgb = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            applied_steps.append(f"Resized from ({orig_w}x{orig_h}) to ({new_w}x{new_h})")
        else:
            resized_rgb = img_rgb.copy()

        proc_h, proc_w = resized_rgb.shape[:2]

        # 2. Grayscale conversion
        if len(resized_rgb.shape) == 3 and resized_rgb.shape[2] == 3:
            gray = cv2.cvtColor(resized_rgb, cv2.COLOR_RGB2GRAY)
            applied_steps.append("Grayscale conversion")
        else:
            gray = resized_rgb.copy()

        # 3. Bilateral edge-preserving denoising
        denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
        applied_steps.append("Bilateral denoising")

        # 4. Contrast Limited Adaptive Histogram Equalization (CLAHE)
        enhanced = self.clahe.apply(denoised)
        applied_steps.append("CLAHE contrast enhancement")

        # 5. Deskewing
        skew_angle, deskewed = self._deskew(enhanced)
        if abs(skew_angle) > 0.5:
            applied_steps.append(f"Deskewed by {skew_angle:+.2f} degrees")
        else:
            deskewed = enhanced

        # 6. Binarization (Otsu + Adaptive threshold fusion)
        binarized = self._binarize(deskewed)
        applied_steps.append("Adaptive & Otsu binarization")

        return PreprocessedImage(
            original_rgb=img_rgb,
            gray=deskewed,
            binarized=binarized,
            scale_factor=scale_factor,
            skew_angle=round(float(skew_angle), 2),
            applied_steps=applied_steps,
            original_dimensions=(orig_w, orig_h),
            processed_dimensions=(proc_w, proc_h),
        )

    def _deskew(self, gray: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        Estimates skew angle of text blocks and applies affine rotation correction.
        """
        h, w = gray.shape[:2]
        if h < 20 or w < 20:
            return 0.0, gray

        # Invert: text becomes white, background black
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Morphological dilation to merge letters into horizontal text lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        # Find text contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        angles: List[float] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 100:
                continue
            rect = cv2.minAreaRect(cnt)
            angle = rect[-1]

            # Normalize angle to [-45, 45] range
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle

            if abs(angle) < 45.0:
                angles.append(angle)

        if not angles:
            return 0.0, gray

        # Median angle avoids outliers
        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return 0.0, gray

        # Rotate image to correct skew
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        corrected = cv2.warpAffine(gray, rot_mat, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        return median_angle, corrected

    def _binarize(self, gray: np.ndarray) -> np.ndarray:
        """
        Produces a high-contrast binary image optimizing character edge clarity.
        Blends Otsu global thresholding with local adaptive Gaussian thresholding.
        """
        # Otsu thresholding
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Local adaptive Gaussian thresholding
        block_size = 21
        adaptive = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            5,
        )

        # Bitwise fusion: keeps pixels confirmed by both thresholding techniques
        fused = cv2.bitwise_and(otsu, adaptive)
        return fused
