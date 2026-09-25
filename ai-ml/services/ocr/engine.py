"""
TruthLens AI/ML — Module 09: OCR Engine Abstraction & Multi-Backend Implementations
Blueprint: Tesseract / EasyOCR integration with deterministic OpenCV morphological fallback.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
import os
import shutil
from typing import List, Optional, Tuple

import cv2
import numpy as np

from config.settings import get_settings
from schemas.ocr import OcrBoundingBox, OcrTextRegion
from services.ocr.preprocessor import PreprocessedImage

logger = logging.getLogger(__name__)


class BaseOcrEngine(ABC):
    """Abstract base class defining the uniform interface for all OCR backends."""

    name: str = "BaseOCR"
    is_available: bool = False

    @abstractmethod
    def extract_text(
        self,
        prep: PreprocessedImage,
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> Tuple[List[OcrTextRegion], str, str]:
        """
        Execute visual character recognition on preprocessed image representations.

        Args:
            prep: PreprocessedImage containing enhanced grayscale, binarized images, and scaling metadata.
            frame_index: Optional keyframe index for video assets.
            timestamp_seconds: Optional timestamp in seconds for video assets.

        Returns:
            Tuple of:
                regions: List of extracted OcrTextRegion objects mapped to original image coordinates.
                primary_language: Detected or configured language code.
                engine_name: Identification string of the executing backend engine.
        """
        pass


class TesseractOcrEngine(BaseOcrEngine):
    """
    Tesseract OCR backend implementation using pytesseract wrapper or CLI binary.
    """

    name: str = "Tesseract"

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        language: str = "eng",
        confidence_threshold: float = 0.40,
    ) -> None:
        settings = get_settings()
        self.cmd = tesseract_cmd or settings.ocr_tesseract_cmd
        self.language = language or settings.ocr_languages
        self.confidence_threshold = confidence_threshold or settings.ocr_confidence_threshold

        self._pytesseract = None
        try:
            import pytesseract  # type: ignore # noqa: F401
            self._pytesseract = pytesseract
            if self.cmd and self.cmd != "tesseract":
                self._pytesseract.pytesseract.tesseract_cmd = self.cmd
            # Check binary availability
            self.is_available = bool(shutil.which(self.cmd) or os.path.isfile(self.cmd))
        except ImportError:
            self.is_available = False

    def extract_text(
        self,
        prep: PreprocessedImage,
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> Tuple[List[OcrTextRegion], str, str]:
        if not self.is_available or self._pytesseract is None:
            raise RuntimeError("Tesseract OCR engine is not installed or available on this system.")

        orig_w, orig_h = prep.original_dimensions
        scale_x = orig_w / float(prep.processed_dimensions[0])
        scale_y = orig_h / float(prep.processed_dimensions[1])

        # Run pytesseract with dictionary output for box-level coordinates
        data = self._pytesseract.image_to_data(
            prep.binarized,
            lang=self.language,
            output_type=self._pytesseract.Output.DICT,
        )

        regions: List[OcrTextRegion] = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = str(data["text"][i]).strip()
            conf_raw = float(data["conf"][i])
            if not text or conf_raw < 0:
                continue

            conf = conf_raw / 100.0
            if conf < self.confidence_threshold:
                continue

            # Coordinates in processed image
            px = int(data["left"][i])
            py = int(data["top"][i])
            pw = int(data["width"][i])
            ph = int(data["height"][i])

            # Scale to original dimensions
            x = max(0, int(round(px * scale_x)))
            y = max(0, int(round(py * scale_y)))
            w = max(1, min(orig_w - x, int(round(pw * scale_x))))
            h = max(1, min(orig_h - y, int(round(ph * scale_y))))

            norm_bbox = [
                round(x / float(orig_w), 4),
                round(y / float(orig_h), 4),
                round(w / float(orig_w), 4),
                round(h / float(orig_h), 4),
            ]

            polygon = [
                [x, y],
                [x + w, y],
                [x + w, y + h],
                [x, y + h],
            ]

            bbox = OcrBoundingBox(
                x=x,
                y=y,
                width=w,
                height=h,
                normalized_bbox=norm_bbox,
                polygon=polygon,
            )

            regions.append(
                OcrTextRegion(
                    text=text,
                    confidence=round(conf, 4),
                    bounding_box=bbox,
                    language=self.language[:2],
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    start_time=timestamp_seconds,
                    end_time=timestamp_seconds,
                )
            )

        return regions, self.language[:2], self.name


class EasyOcrEngine(BaseOcrEngine):
    """
    EasyOCR deep learning backend implementation.
    """

    name: str = "EasyOCR"

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        confidence_threshold: float = 0.40,
    ) -> None:
        settings = get_settings()
        self.languages = languages or [settings.ocr_languages]
        self.confidence_threshold = confidence_threshold or settings.ocr_confidence_threshold
        self._reader = None
        try:
            import easyocr  # type: ignore # noqa: F401
            self.is_available = True
        except ImportError:
            self.is_available = False

    def _get_reader(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader

    def extract_text(
        self,
        prep: PreprocessedImage,
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> Tuple[List[OcrTextRegion], str, str]:
        if not self.is_available:
            raise RuntimeError("EasyOCR engine is not installed or available on this system.")

        reader = self._get_reader()
        orig_w, orig_h = prep.original_dimensions
        scale_x = orig_w / float(prep.processed_dimensions[0])
        scale_y = orig_h / float(prep.processed_dimensions[1])

        results = reader.readtext(prep.gray)
        regions: List[OcrTextRegion] = []

        for poly, raw_text, conf in results:
            clean_text = str(raw_text).strip()
            conf_val = float(conf)
            if not clean_text or conf_val < self.confidence_threshold:
                continue

            scaled_poly: List[List[int]] = []
            xs: List[int] = []
            ys: List[int] = []
            for pt in poly:
                sx = int(round(pt[0] * scale_x))
                sy = int(round(pt[1] * scale_y))
                scaled_poly.append([sx, sy])
                xs.append(sx)
                ys.append(sy)

            x = max(0, min(xs))
            y = max(0, min(ys))
            w = max(1, min(orig_w - x, max(xs) - x))
            h = max(1, min(orig_h - y, max(ys) - y))

            norm_bbox = [
                round(x / float(orig_w), 4),
                round(y / float(orig_h), 4),
                round(w / float(orig_w), 4),
                round(h / float(orig_h), 4),
            ]

            bbox = OcrBoundingBox(
                x=x,
                y=y,
                width=w,
                height=h,
                normalized_bbox=norm_bbox,
                polygon=scaled_poly,
            )

            regions.append(
                OcrTextRegion(
                    text=clean_text,
                    confidence=round(conf_val, 4),
                    bounding_box=bbox,
                    language=self.languages[0] if self.languages else "en",
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    start_time=timestamp_seconds,
                    end_time=timestamp_seconds,
                )
            )

        return regions, self.languages[0] if self.languages else "en", self.name


class OpenCVMorphologicalOcrEngine(BaseOcrEngine):
    """
    Deterministic OpenCV text candidate region detector and morphological extraction engine.
    Guarantees zero-external-dependency execution across any testing or production environment:
    1. Uses vertical Sobel edge gradients to identify character stroke transitions.
    2. Connects character strokes horizontally via rectangular morphological kernel (17x3).
    3. Detects bounding boxes, verifies character aspect ratios, and orders regions top-to-bottom/left-to-right.
    4. Computes stroke contrast variance confidence scores.
    """

    name: str = "OpenCV-MSER-Fallback"
    is_available: bool = True

    def __init__(self, confidence_threshold: float = 0.40) -> None:
        self.confidence_threshold = confidence_threshold

    def extract_text(
        self,
        prep: PreprocessedImage,
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> Tuple[List[OcrTextRegion], str, str]:
        gray = prep.gray
        orig_w, orig_h = prep.original_dimensions
        scale_x = orig_w / float(prep.processed_dimensions[0])
        scale_y = orig_h / float(prep.processed_dimensions[1])

        # Sobel vertical gradient highlights character stroke transitions
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_x = np.absolute(grad_x)
        grad_norm = cv2.normalize(grad_x, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

        # Morphological close with rectangular kernel to connect character strokes into words
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(grad_norm, cv2.MORPH_CLOSE, kernel)

        # Threshold to create connected text masks
        _, text_mask = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Find candidate bounding contours
        contours, _ = cv2.findContours(text_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions: List[OcrTextRegion] = []

        # Filter contours by geometry
        bounding_rects: List[Tuple[int, int, int, int]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 60:
                continue
            bx, by, bw, bh = cv2.boundingRect(cnt)
            aspect_ratio = bw / float(bh) if bh > 0 else 0.0

            # Filter non-text geometric blobs (characters/words typically have aspect ratio 0.3 to 30.0)
            if aspect_ratio < 0.3 or aspect_ratio > 30.0 or bh < 6 or bw < 8:
                continue
            if bh > (gray.shape[0] * 0.90) or bw > (gray.shape[1] * 0.98):
                continue

            bounding_rects.append((bx, by, bw, bh))

        # Sort contours top-to-bottom, left-to-right (natural reading order)
        bounding_rects.sort(key=lambda r: (r[1] // 15, r[0]))

        for idx, (px, py, pw, ph) in enumerate(bounding_rects):
            x = max(0, int(round(px * scale_x)))
            y = max(0, int(round(py * scale_y)))
            w = max(1, min(orig_w - x, int(round(pw * scale_x))))
            h = max(1, min(orig_h - y, int(round(ph * scale_y))))

            norm_bbox = [
                round(x / float(orig_w), 4),
                round(y / float(orig_h), 4),
                round(w / float(orig_w), 4),
                round(h / float(orig_h), 4),
            ]

            polygon = [
                [x, y],
                [x + w, y],
                [x + w, y + h],
                [x, y + h],
            ]

            # Calculate stroke and contrast confidence from ROI
            roi_gray = gray[py : py + ph, px : px + pw]
            contrast = float(np.std(roi_gray)) if roi_gray.size > 0 else 0.0
            conf = min(0.95, max(0.40, (contrast / 128.0) * 0.85 + 0.25))

            if conf < self.confidence_threshold:
                continue

            text_str = f"TEXT_REGION_{idx + 1}"

            regions.append(
                OcrTextRegion(
                    text=text_str,
                    confidence=round(conf, 4),
                    bounding_box=OcrBoundingBox(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        normalized_bbox=norm_bbox,
                        polygon=polygon,
                    ),
                    language="en",
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    start_time=timestamp_seconds,
                    end_time=timestamp_seconds,
                )
            )

        return regions, "en", self.name


def get_ocr_engine(
    engine_name: Optional[str] = None,
    require_engine: Optional[bool] = None,
) -> BaseOcrEngine:
    """
    Factory function providing the configured OCR engine with safe fallback handling.

    Args:
        engine_name: Configured engine ("auto", "tesseract", "easyocr", "fallback").
        require_engine: If True, raises RuntimeError when requested engine is missing.

    Returns:
        BaseOcrEngine: Instantiated operational OCR backend.
    """
    settings = get_settings()
    target_engine = (engine_name or settings.ocr_engine).lower()
    is_required = require_engine if require_engine is not None else settings.require_ocr_engine

    if target_engine == "tesseract":
        tess = TesseractOcrEngine(
            tesseract_cmd=settings.ocr_tesseract_cmd,
            language=settings.ocr_languages,
            confidence_threshold=settings.ocr_confidence_threshold,
        )
        if tess.is_available:
            return tess
        if is_required:
            raise RuntimeError("Strict mode enabled: Tesseract OCR engine is not available on this system.")
        logger.warning("Tesseract requested but not available. Falling back to OpenCV morphological detector.")
        return OpenCVMorphologicalOcrEngine(confidence_threshold=settings.ocr_confidence_threshold)

    elif target_engine == "easyocr":
        easy = EasyOcrEngine(
            languages=[settings.ocr_languages],
            confidence_threshold=settings.ocr_confidence_threshold,
        )
        if easy.is_available:
            return easy
        if is_required:
            raise RuntimeError("Strict mode enabled: EasyOCR engine is not available on this system.")
        logger.warning("EasyOCR requested but not available. Falling back to OpenCV morphological detector.")
        return OpenCVMorphologicalOcrEngine(confidence_threshold=settings.ocr_confidence_threshold)

    elif target_engine == "auto":
        # Check Tesseract first
        tess = TesseractOcrEngine(
            tesseract_cmd=settings.ocr_tesseract_cmd,
            language=settings.ocr_languages,
            confidence_threshold=settings.ocr_confidence_threshold,
        )
        if tess.is_available:
            return tess

        # Check EasyOCR next
        easy = EasyOcrEngine(
            languages=[settings.ocr_languages],
            confidence_threshold=settings.ocr_confidence_threshold,
        )
        if easy.is_available:
            return easy

        if is_required:
            raise RuntimeError("Strict mode enabled: No production OCR engine (Tesseract or EasyOCR) is available.")

        logger.info("Operating with deterministic OpenCV morphological OCR engine fallback.")
        return OpenCVMorphologicalOcrEngine(confidence_threshold=settings.ocr_confidence_threshold)

    # Fallback engine
    return OpenCVMorphologicalOcrEngine(confidence_threshold=settings.ocr_confidence_threshold)
