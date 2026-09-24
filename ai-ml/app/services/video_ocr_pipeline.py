import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from ..config import settings
from ..schemas import OcrTextRegion
from .image_preprocessor import ImagePreprocessor
from .ocr_engine import OcrEngine


class VideoOcrPipeline:
    """
    Video Frame Sampling and Temporal Text Extraction Pipeline.
    
    Adheres to TruthLens Blueprint Module 09 specification:
    Extracts embedded visual text from video keyframes, news banners, posters, and memes
    with frame/time association and temporal deduplication.
    
    Features:
    1. Safe frame sampling at 1.0s interval up to max frame bounds.
    2. Temporal text consolidation: Merges persistent text bands (e.g. news chyrons)
       across consecutive frames into continuous [start_time, end_time] segments.
    3. Prevents duplicate flood while preserving temporal bounds.
    """

    def __init__(
        self,
        image_preprocessor: Optional[ImagePreprocessor] = None,
        ocr_engine: Optional[OcrEngine] = None,
        sample_interval_sec: float = settings.OCR_VIDEO_SAMPLE_INTERVAL_SECONDS,
        max_frames: int = settings.OCR_VIDEO_MAX_FRAMES,
    ):
        self.preprocessor = image_preprocessor or ImagePreprocessor()
        self.ocr_engine = ocr_engine or OcrEngine()
        self.sample_interval_sec = sample_interval_sec
        self.max_frames = max_frames

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
            - List of consolidated OcrTextRegion
            - Primary language
            - OCR engine name
            - Total frames analyzed
            - Native dimensions (width, height)
            - Applied preprocessing steps summary
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Unable to open video stream: {video_path}")

        native_fps = cap.get(cv2.CAP_PROP_FPS)
        if native_fps <= 0 or np.isnan(native_fps):
            native_fps = 25.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / native_fps if total_frames > 0 else 0.0

        # Step in native frames corresponding to sample_interval_sec
        frame_step = max(1, int(round(native_fps * self.sample_interval_sec)))

        all_frame_regions: List[OcrTextRegion] = []
        frame_idx = 0
        sampled_count = 0
        detected_languages: List[str] = []
        engine_name = "EasyOCR"
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

                    # Initialize start_time and end_time
                    for r in regions:
                        r.start_time = ts
                        r.end_time = round(ts + self.sample_interval_sec, 3)
                        all_frame_regions.append(r)

                    sampled_count += 1

                frame_idx += 1

        finally:
            cap.release()

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

        # Restore chronological ordering by start_time
        consolidated.sort(key=lambda r: (r.start_time or 0.0, r.bounding_box.y, r.bounding_box.x))
        return consolidated
