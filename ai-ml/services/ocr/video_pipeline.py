"""
TruthLens AI/ML — Module 09: Video Keyframe OCR & Temporal Text Consolidation Pipeline
Blueprint: Video -> Keyframe Sampling -> Preprocessing -> OCR Engine -> Consolidated Chyrons
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional

import cv2
import numpy as np

from config.settings import get_settings
from schemas.ocr import OcrTextRegion
from services.ocr.engine import BaseOcrEngine, get_ocr_engine
from services.ocr.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class VideoOcrPipeline:
    """
    Video Frame Sampling and Temporal Text Extraction Pipeline.

    Key capabilities:
    1. Resource-bounded video keyframe sampling at configured interval (default: 1.0s).
    2. Temporal text consolidation: Merges persistent text bands (e.g. news chyrons, watermarks, breaking news)
       across consecutive frames into continuous [start_time, end_time] intervals.
    3. Prevents duplicate flooding while preserving temporal metadata and spatial boxes.
    """

    def __init__(
        self,
        image_preprocessor: Optional[ImagePreprocessor] = None,
        ocr_engine: Optional[BaseOcrEngine] = None,
        sample_interval_sec: Optional[float] = None,
        max_frames: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.preprocessor = image_preprocessor or ImagePreprocessor()
        self.ocr_engine = ocr_engine or get_ocr_engine()
        self.sample_interval_sec = sample_interval_sec or settings.ocr_video_sample_interval_seconds
        self.max_frames = max_frames or settings.ocr_video_max_frames

    def process_video(
        self,
        video_path: str,
    ) -> Tuple[List[OcrTextRegion], str, str, int, Tuple[int, int], List[str]]:
        """
        Samples video frames, extracts visual text regions, and consolidates temporal segments.

        Args:
            video_path: Local filesystem path to video file.

        Returns:
            Tuple of:
                consolidated_regions: List of merged OcrTextRegion objects with [start_time, end_time].
                primary_language: Detected or configured primary language.
                engine_name: Identification string of executing OCR engine.
                sampled_count: Total video keyframes analyzed.
                dimensions: (native_width, native_height).
                preprocessing_steps: List of applied OpenCV operations.

        Raises:
            ValueError: If video stream cannot be opened or contains zero frames.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Unable to open video stream: {video_path}")

        native_fps = cap.get(cv2.CAP_PROP_FPS)
        if native_fps <= 0.0 or np.isnan(native_fps):
            native_fps = 25.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_step = max(1, int(round(native_fps * self.sample_interval_sec)))

        all_frame_regions: List[OcrTextRegion] = []
        frame_idx = 0
        sampled_count = 0
        detected_languages: List[str] = []
        engine_name = self.ocr_engine.name
        preprocessing_steps: List[str] = []

        try:
            while cap.isOpened() and sampled_count < self.max_frames:
                ret, bgr_frame = cap.read()
                if not ret or bgr_frame is None:
                    break

                if frame_idx % frame_step == 0:
                    ts = round(frame_idx / float(native_fps), 3)
                    rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

                    # Preprocess frame
                    prep = self.preprocessor.preprocess(rgb_frame)
                    if not preprocessing_steps:
                        preprocessing_steps = prep.applied_steps

                    # Extract text
                    regions, lang, eng = self.ocr_engine.extract_text(
                        prep,
                        frame_index=sampled_count,
                        timestamp_seconds=ts,
                    )
                    engine_name = eng
                    if lang not in detected_languages:
                        detected_languages.append(lang)

                    # Initialize start_time and end_time bounds
                    for r in regions:
                        r.start_time = ts
                        r.end_time = round(ts + self.sample_interval_sec, 3)
                        all_frame_regions.append(r)

                    sampled_count += 1

                frame_idx += 1

        finally:
            cap.release()

        if sampled_count == 0:
            raise ValueError("Decoded video contains zero readable frames.")

        # Consolidate identical or consecutive text across temporal spans
        consolidated = self._consolidate_temporal_regions(all_frame_regions)
        primary_lang = detected_languages[0] if detected_languages else "en"

        return consolidated, primary_lang, engine_name, sampled_count, (width, height), preprocessing_steps

    def _consolidate_temporal_regions(self, regions: List[OcrTextRegion]) -> List[OcrTextRegion]:
        """
        Merges persistent visual text (e.g. news banners, watermarks) appearing in consecutive frames.
        """
        if not regions:
            return []

        # Sort by text, then by start_time
        sorted_regions = sorted(regions, key=lambda r: (r.text.lower(), r.start_time or 0.0))

        consolidated: List[OcrTextRegion] = []
        curr = sorted_regions[0]

        for nxt in sorted_regions[1:]:
            same_text = (curr.text.strip().lower() == nxt.text.strip().lower())
            is_consecutive = (
                curr.end_time is not None
                and nxt.start_time is not None
                and abs(nxt.start_time - curr.end_time) <= (self.sample_interval_sec * 1.5)
            )

            if same_text and is_consecutive:
                # Extend time window of current segment
                curr.end_time = nxt.end_time
                curr.confidence = round((curr.confidence + nxt.confidence) / 2.0, 4)
            else:
                consolidated.append(curr)
                curr = nxt

        consolidated.append(curr)

        # Restore chronological ordering by start_time, then vertical position
        consolidated.sort(key=lambda r: (r.start_time or 0.0, r.bounding_box.y, r.bounding_box.x))
        return consolidated
