"""
TruthLens AI/ML — Module 09: End-to-End OCR Service Orchestration
Blueprint: Image/Frame -> Binarization Preprocessor -> Tesseract / EasyOCR Engine -> Extracted Text + Bounding Boxes
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import cv2
import numpy as np

from config.settings import get_settings
from schemas.ocr import (
    BackendOcrResponse,
    OcrEvidence,
    OcrTextRegion,
    LegacyOcrAnalysisResponse,
)
from services.ocr.engine import BaseOcrEngine, get_ocr_engine
from services.ocr.preprocessor import ImagePreprocessor
from services.ocr.video_pipeline import VideoOcrPipeline
from services.video_analysis.ingestion import temp_video_file

logger = logging.getLogger(__name__)

# Video format extensions
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".mpeg", ".m4v"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


class OcrAnalysisPipeline:
    """
    End-to-End Visual Text Extraction & OCR Orchestrator.
    Handles both standalone images (screenshots, memes, posters) and video keyframes (news broadcasts, chyrons).
    """

    def __init__(
        self,
        image_preprocessor: Optional[ImagePreprocessor] = None,
        ocr_engine: Optional[BaseOcrEngine] = None,
        video_ocr_pipeline: Optional[VideoOcrPipeline] = None,
    ) -> None:
        self.preprocessor = image_preprocessor or ImagePreprocessor()
        self.ocr_engine = ocr_engine or get_ocr_engine()
        self.video_pipeline = video_ocr_pipeline or VideoOcrPipeline(
            image_preprocessor=self.preprocessor,
            ocr_engine=self.ocr_engine,
        )

    def analyze_bytes(
        self,
        media_bytes: bytes,
        filename: str = "media.png",
        media_type: Optional[str] = None,
    ) -> BackendOcrResponse:
        """
        Execute full OCR pipeline on raw binary media bytes.

        Args:
            media_bytes: Binary payload of image or video.
            filename: Uploaded filename hint.
            media_type: Optional explicit media type ("IMAGE" or "VIDEO").

        Returns:
            BackendOcrResponse matching Spring Boot FastApiOcrResponse contract.

        Raises:
            ValueError: If media bytes are empty, corrupt, or unsupported.
        """
        if not media_bytes or len(media_bytes) == 0:
            raise ValueError("Uploaded media payload is empty (0 bytes).")

        ext = Path(filename).suffix.lower()
        is_video = (media_type == "VIDEO") or (ext in VIDEO_EXTENSIONS)

        if is_video:
            return self._analyze_video_bytes(media_bytes, filename=filename)
        else:
            return self._analyze_image_bytes(media_bytes, filename=filename)

    def _analyze_image_bytes(
        self,
        image_bytes: bytes,
        filename: str = "image.png",
    ) -> BackendOcrResponse:
        """Decode image bytes and execute image OCR pipeline."""
        np_arr = np.frombuffer(image_bytes, np.uint8)
        bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if bgr is None:
            # Check if this might be a video instead of an image
            ext = Path(filename).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                return self._analyze_video_bytes(image_bytes, filename=filename)
            raise ValueError("Unable to decode media stream. File may be corrupt or an unsupported container.")

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]

        if h < 2 or w < 2:
            raise ValueError("Image dimensions too small for OCR analysis.")

        # 1. OpenCV Preprocessing
        prep = self.preprocessor.preprocess(rgb)

        # 2. OCR text extraction
        regions, language, engine_name = self.ocr_engine.extract_text(prep)

        # 3. Text aggregation
        text_lines = [r.text.strip() for r in regions if r.text.strip()]
        full_text = "\n".join(text_lines)

        if regions:
            avg_conf = float(np.mean([r.confidence for r in regions]))
        else:
            avg_conf = 1.0

        unique_languages = list(set([r.language for r in regions])) if regions else [language]

        evidence = OcrEvidence(
            total_regions=len(regions),
            detected_languages=unique_languages,
            image_width=w,
            image_height=h,
            engine_used=engine_name,
            preprocessing_applied=prep.applied_steps,
            media_type="IMAGE",
            frames_analyzed=1,
            details={
                "skew_angle_deg": prep.skew_angle,
                "scale_factor": prep.scale_factor,
                "processed_dimensions": list(prep.processed_dimensions),
            },
        )

        return BackendOcrResponse(
            extracted_text=full_text,
            language=language,
            confidence_score=round(avg_conf, 4),
            regions_count=len(regions),
            regions=regions,
            evidence=evidence,
            status="COMPLETED",
        )

    def _analyze_video_bytes(
        self,
        video_bytes: bytes,
        filename: str = "video.mp4",
    ) -> BackendOcrResponse:
        """Persist video bytes to temporary file and execute video keyframe OCR pipeline."""
        with temp_video_file(video_bytes, filename=filename) as temp_path:
            try:
                (
                    regions,
                    language,
                    engine_name,
                    frames_count,
                    dims,
                    prep_steps,
                ) = self.video_pipeline.process_video(str(temp_path))
            except ValueError as exc:
                raise ValueError(f"Unable to decode video stream: {exc}") from exc

        text_lines = [r.text.strip() for r in regions if r.text.strip()]
        full_text = "\n".join(text_lines)

        if regions:
            avg_conf = float(np.mean([r.confidence for r in regions]))
        else:
            avg_conf = 1.0

        unique_languages = list(set([r.language for r in regions])) if regions else [language]

        evidence = OcrEvidence(
            total_regions=len(regions),
            detected_languages=unique_languages,
            image_width=dims[0],
            image_height=dims[1],
            engine_used=engine_name,
            preprocessing_applied=prep_steps,
            media_type="VIDEO",
            frames_analyzed=frames_count,
            details={
                "video_dimensions": list(dims),
                "sample_interval_sec": self.video_pipeline.sample_interval_sec,
                "temporal_regions_count": len(regions),
            },
        )

        return BackendOcrResponse(
            extracted_text=full_text,
            language=language,
            confidence_score=round(avg_conf, 4),
            regions_count=len(regions),
            regions=regions,
            evidence=evidence,
            status="COMPLETED",
        )


# Singleton pipeline instance
_ocr_pipeline: Optional[OcrAnalysisPipeline] = None


def get_ocr_pipeline() -> OcrAnalysisPipeline:
    """Retrieve or lazily initialize the singleton OCR pipeline instance."""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        _ocr_pipeline = OcrAnalysisPipeline()
    return _ocr_pipeline


def analyze_ocr_bytes(
    media_bytes: bytes,
    filename: str = "media.png",
    media_type: Optional[str] = None,
) -> BackendOcrResponse:
    """Convenience functional wrapper for analyzing media bytes."""
    pipeline = get_ocr_pipeline()
    return pipeline.analyze_bytes(media_bytes, filename=filename, media_type=media_type)


def analyze_ocr_from_path(
    media_path: str,
    media_id: Optional[Union[str, Any]] = None,
) -> LegacyOcrAnalysisResponse:
    """
    Execute OCR analysis from local filesystem path for legacy/internal endpoint compatibility.
    """
    if not os.path.exists(media_path):
        raise FileNotFoundError(f"Media file not found: {media_path}")

    with open(media_path, "rb") as f:
        content = f.read()

    resp = analyze_ocr_bytes(content, filename=os.path.basename(media_path))

    return LegacyOcrAnalysisResponse(
        media_id=media_id,
        media_path=media_path,
        extracted_text=resp.extracted_text,
        language=resp.language,
        confidence_score=resp.confidence_score,
        regions_count=resp.regions_count,
        regions=resp.regions,
        evidence=resp.evidence,
        status=resp.status,
        error_message=resp.error_message,
    )
