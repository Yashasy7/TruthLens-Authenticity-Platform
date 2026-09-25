import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from ..config import settings
from ..schemas import OcrBoundingBox, OcrTextRegion, OcrEvidence, OcrAnalysisResult
from .image_preprocessor import ImagePreprocessor
from .ocr_engine import OcrEngine
from .video_ocr_pipeline import VideoOcrPipeline


class OcrAnalysisPipeline:
    """
    End-to-End Optical Character Recognition & Visual Text Extraction Pipeline.
    
    Adheres to TruthLens Blueprint Module 09 specification:
    Image/Frame -> Binarization Preprocessor -> Tesseract / EasyOCR Engine -> Extracted Text Strings + Bounding Boxes.
    
    Coordinates:
    1. Multi-modal media ingestion (both static images and video keyframes).
    2. Adaptive OpenCV preprocessing (contrast normalization, binarization, deskewing).
    3. Multi-backend OCR inference (EasyOCR, Tesseract, and morphological fallback).
    4. Text aggregation, confidence calculation, and spatial coordinate mapping.
    """

    def __init__(
        self,
        image_preprocessor: Optional[ImagePreprocessor] = None,
        ocr_engine: Optional[OcrEngine] = None,
        video_ocr_pipeline: Optional[VideoOcrPipeline] = None,
    ):
        self.preprocessor = image_preprocessor or ImagePreprocessor()
        self.ocr_engine = ocr_engine or OcrEngine()
        self.video_pipeline = video_ocr_pipeline or VideoOcrPipeline(
            image_preprocessor=self.preprocessor,
            ocr_engine=self.ocr_engine,
        )

    def analyze(self, file_path: str, media_type: Optional[str] = None) -> OcrAnalysisResult:
        """
        Executes complete OCR text extraction pipeline on a media asset.
        
        Args:
            file_path: Local filesystem path to the uploaded image or video.
            media_type: Explicit media type ("IMAGE" or "VIDEO"), or inferred from extension.
            
        Returns:
            Structured OcrAnalysisResult with extracted text, bounding boxes, and evidence.
        """
        if not os.path.isfile(file_path):
            raise ValueError(f"Media file not found: {file_path}")

        # Infer media type if not provided
        ext = os.path.splitext(file_path)[1].lower()
        video_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".mpeg"}
        is_video = (media_type == "VIDEO") or (ext in video_exts)

        if is_video:
            return self._analyze_video(file_path)
        else:
            return self._analyze_image(file_path)

    def _analyze_image(self, image_path: str) -> OcrAnalysisResult:
        """Executes OCR extraction on an image asset."""
        # Read image with OpenCV
        bgr = cv2.imread(image_path)
        if bgr is None:
            raise ValueError("Failed to decode image file. File may be corrupt or an unsupported image format.")

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]

        # 1. Preprocess
        prep = self.preprocessor.preprocess(rgb)

        # 2. Extract text regions
        regions, language, engine_name = self.ocr_engine.extract_text(prep)

        # 3. Aggregate text and confidence
        text_lines = [r.text.strip() for r in regions if r.text.strip()]
        full_text = "\n".join(text_lines)

        if regions:
            avg_conf = float(np.mean([r.confidence for r in regions]))
        else:
            # Clean image with no text has high confidence of zero text
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
                "processed_dimensions": prep.processed_dimensions,
            }
        )

        return OcrAnalysisResult(
            extracted_text=full_text,
            language=language,
            confidence_score=round(avg_conf, 4),
            regions_count=len(regions),
            regions=regions,
            evidence=evidence,
            status="COMPLETED",
        )

    def _analyze_video(self, video_path: str) -> OcrAnalysisResult:
        """Executes OCR extraction across video keyframes."""
        regions, language, engine_name, frames_count, dims, prep_steps = self.video_pipeline.process_video(video_path)

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
                "video_dimensions": dims,
                "sample_interval_sec": self.video_pipeline.sample_interval_sec,
                "temporal_regions_count": len(regions),
            }
        )

        return OcrAnalysisResult(
            extracted_text=full_text,
            language=language,
            confidence_score=round(avg_conf, 4),
            regions_count=len(regions),
            regions=regions,
            evidence=evidence,
            status="COMPLETED",
        )
