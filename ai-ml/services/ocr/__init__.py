"""
TruthLens AI/ML — Module 09: OCR & Visual Text Extraction Service Package
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.ocr.service import analyze_ocr_bytes, analyze_ocr_from_path


def __getattr__(name: str):
    if name in ("analyze_ocr_bytes", "analyze_ocr_from_path"):
        from services.ocr.service import analyze_ocr_bytes, analyze_ocr_from_path
        return analyze_ocr_bytes if name == "analyze_ocr_bytes" else analyze_ocr_from_path
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["analyze_ocr_bytes", "analyze_ocr_from_path"]
