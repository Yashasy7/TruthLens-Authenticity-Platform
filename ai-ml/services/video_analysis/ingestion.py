"""
TruthLens AI/ML — Video Ingestion & Deterministic Frame Sampling
Blueprint: Module 06 — FFmpeg / Video frame extraction pipeline
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import logging
from pathlib import Path
import tempfile
from typing import Generator, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@dataclass(frozen=True)
class VideoMetadata:
    """Core container for video stream metadata."""
    frame_count: int
    fps: float
    duration_seconds: float
    width: int
    height: int


@dataclass
class SampledFrame:
    """Sampled video frame with exact temporal coordinates."""
    frame_index: int
    timestamp_seconds: float
    frame_rgb: np.ndarray   # uint8 (H, W, 3) in RGB order


@contextmanager
def temp_video_file(video_bytes: bytes, filename: str = "video.mp4") -> Generator[Path, None, None]:
    """
    Safely write binary video bytes to a temporary disk file and ensure cleanup.

    Args:
        video_bytes: Raw binary video stream.
        filename: Original filename (used to preserve extension).

    Yields:
        Path to the temporary video file on disk.
    """
    if not video_bytes or len(video_bytes) == 0:
        raise ValueError("Video bytes cannot be empty (0 bytes).")

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        suffix = ".mp4"

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    try:
        tmp.write(video_bytes)
        tmp.flush()
        tmp.close()
        yield tmp_path
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError as exc:
                logger.warning("Failed to remove temporary video file %s: %s", tmp_path, exc)


def extract_video_metadata(video_path: Path) -> VideoMetadata:
    """
    Inspect a video file and extract playback and stream metadata.

    Raises:
        FileNotFoundError: if video_path does not exist.
        ValueError: if video cannot be opened or decoded.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        raise ValueError(f"Cannot open video file: {video_path}. Unreadable or corrupted codec.")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if frame_count <= 0 or width <= 0 or height <= 0:
        raise ValueError(f"Corrupted video stream in {video_path}: frames={frame_count}, size=({width}x{height})")

    # Safe fallback for missing or corrupted FPS header
    if fps <= 0.0 or np.isnan(fps):
        fps = 25.0

    duration_seconds = round(float(frame_count / fps), 3)

    return VideoMetadata(
        frame_count=frame_count,
        fps=fps,
        duration_seconds=duration_seconds,
        width=width,
        height=height,
    )


def sample_video_frames(
    video_path: Path,
    max_frames: int = 16,
) -> Tuple[VideoMetadata, List[SampledFrame]]:
    """
    Deterministically sample up to max_frames uniformly distributed across the video duration.

    Args:
        video_path: Path to video on disk.
        max_frames: Maximum number of frames to sample (default 16).

    Returns:
        Tuple of (VideoMetadata, List[SampledFrame]).
    """
    metadata = extract_video_metadata(video_path)
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise ValueError(f"Cannot read frames from {video_path}")

    # Determine target frame indices deterministically
    total_frames = metadata.frame_count
    if total_frames <= max_frames:
        target_indices = list(range(total_frames))
    else:
        target_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int).tolist()

    sampled_frames: List[SampledFrame] = []

    try:
        for idx in target_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame_bgr = cap.read()
            if not ret or frame_bgr is None:
                continue

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            timestamp_sec = round(float(idx / metadata.fps), 3)

            sampled_frames.append(
                SampledFrame(
                    frame_index=idx,
                    timestamp_seconds=timestamp_sec,
                    frame_rgb=frame_rgb,
                )
            )
    finally:
        cap.release()

    if len(sampled_frames) == 0:
        raise ValueError(f"No frames could be extracted from video {video_path}")

    logger.debug(
        "Sampled %d frames from %s (total: %d, duration: %.2fs)",
        len(sampled_frames),
        video_path.name,
        metadata.frame_count,
        metadata.duration_seconds,
    )

    return metadata, sampled_frames
