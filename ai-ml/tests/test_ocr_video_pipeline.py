"""
TruthLens AI/ML — Module 09: Video Keyframe OCR Pipeline Unit Tests
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest

from services.ocr.video_pipeline import VideoOcrPipeline


@pytest.fixture
def synthetic_video_with_text() -> Path:
    """Generate a 2-second video with a static text chyron banner at the bottom."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        path = Path(tmp.name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 25.0
    out = cv2.VideoWriter(str(path), fourcc, fps, (320, 240))

    # 50 frames = 2.0 seconds
    for i in range(50):
        frame = np.full((240, 320, 3), 200, dtype=np.uint8)
        # Persistent bottom news chyron
        cv2.rectangle(frame, (10, 180), (310, 230), (20, 20, 20), -1)
        cv2.putText(frame, "LIVE NEWS", (30, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (250, 250, 250), 2)
        out.write(frame)

    out.release()
    yield path
    path.unlink(missing_ok=True)


def test_video_ocr_sampling_and_chyron_consolidation(synthetic_video_with_text: Path):
    """Verify video pipeline samples keyframes and consolidates persistent text across time."""
    pipeline = VideoOcrPipeline(sample_interval_sec=0.5, max_frames=10)
    regions, lang, engine_name, frames_count, dims, prep_steps = pipeline.process_video(str(synthetic_video_with_text))

    assert frames_count >= 2
    assert dims == (320, 240)
    assert lang == "en"
    assert len(prep_steps) > 0

    # Regions should exist
    assert len(regions) >= 1
    # Check temporal bounds
    first = regions[0]
    assert first.start_time is not None
    assert first.end_time is not None
    assert first.end_time >= first.start_time


def test_video_ocr_invalid_file_raises():
    """Invalid video file path raises ValueError."""
    pipeline = VideoOcrPipeline()
    with pytest.raises(ValueError, match="Unable to open video stream"):
        pipeline.process_video("/nonexistent/video_path_xyz.mp4")
