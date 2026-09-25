"""
TruthLens AI/ML — Module 09: OCR Engine Abstraction & Implementations Unit Tests
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from schemas.ocr import OcrBoundingBox, OcrTextRegion
from services.ocr.engine import (
    BaseOcrEngine,
    OpenCVMorphologicalOcrEngine,
    TesseractOcrEngine,
    EasyOcrEngine,
    get_ocr_engine,
)
from services.ocr.preprocessor import ImagePreprocessor, PreprocessedImage


def _create_synthetic_banner_image(text: str = "OFFICIAL STATEMENT") -> np.ndarray:
    """Generate image with high-contrast text banner."""
    img = np.full((120, 500, 3), 245, dtype=np.uint8)
    cv2.putText(img, text, (30, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (10, 10, 10), 3, cv2.LINE_AA)
    return img


def test_opencv_morphological_engine_detects_text():
    """Morphological fallback engine detects text bounding regions deterministically."""
    img = _create_synthetic_banner_image()
    prep = ImagePreprocessor().preprocess(img)

    engine = OpenCVMorphologicalOcrEngine(confidence_threshold=0.30)
    regions, lang, engine_name = engine.extract_text(prep)

    assert engine_name == "OpenCV-MSER-Fallback"
    assert lang == "en"
    assert len(regions) >= 1

    reg = regions[0]
    assert isinstance(reg, OcrTextRegion)
    assert reg.confidence >= 0.30
    assert 0 <= reg.bounding_box.x < 500
    assert 0 <= reg.bounding_box.y < 120
    assert reg.bounding_box.width > 0
    assert reg.bounding_box.height > 0
    # Normalized bbox in [0.0, 1.0]
    assert len(reg.bounding_box.normalized_bbox) == 4
    for coord in reg.bounding_box.normalized_bbox:
        assert 0.0 <= coord <= 1.0
    # Polygon has 4 points
    assert len(reg.bounding_box.polygon) == 4


def test_opencv_engine_on_clean_blank_image():
    """Blank image with no visual text produces 0 regions without crashing."""
    blank = np.full((150, 400, 3), 255, dtype=np.uint8)
    prep = ImagePreprocessor().preprocess(blank)

    engine = OpenCVMorphologicalOcrEngine()
    regions, lang, engine_name = engine.extract_text(prep)

    assert len(regions) == 0
    assert lang == "en"


def test_factory_returns_fallback_in_dev_mode():
    """Factory returns operational fallback engine in development environment."""
    engine = get_ocr_engine(engine_name="fallback")
    assert isinstance(engine, OpenCVMorphologicalOcrEngine)
    assert engine.is_available is True


def test_factory_auto_selects_available_engine():
    """Auto mode provides an available engine."""
    engine = get_ocr_engine(engine_name="auto")
    assert isinstance(engine, BaseOcrEngine)
    assert engine.is_available is True


def test_strict_mode_fails_fast_on_missing_tesseract():
    """Strict mode raises RuntimeError if Tesseract is required but unavailable."""
    tess = TesseractOcrEngine(tesseract_cmd="nonexistent_tesseract_binary_xyz")
    if not tess.is_available:
        with pytest.raises(RuntimeError, match="Strict mode enabled"):
            get_ocr_engine(engine_name="tesseract", require_engine=True)


def test_strict_mode_fails_fast_on_missing_easyocr():
    """Strict mode raises RuntimeError if EasyOCR is required but unavailable."""
    easy = EasyOcrEngine()
    if not easy.is_available:
        with pytest.raises(RuntimeError, match="Strict mode enabled"):
            get_ocr_engine(engine_name="easyocr", require_engine=True)
