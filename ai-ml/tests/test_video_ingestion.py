"""
Tests for services/video_analysis/ingestion.py
Module 06 — Video Ingestion & Deterministic Frame Sampling
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from services.video_analysis.ingestion import (
    VideoMetadata,
    extract_video_metadata,
    sample_video_frames,
    temp_video_file,
)


def create_test_video(path: Path, num_frames: int = 10, fps: float = 10.0, width: int = 80, height: int = 80):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    for i in range(num_frames):
        # Varying frame intensity to ensure distinct frames
        frame = np.full((height, width, 3), int((i / max(1, num_frames)) * 255), dtype=np.uint8)
        writer.write(frame)
    writer.release()


@pytest.fixture
def short_video(tmp_path: Path) -> Path:
    video_path = tmp_path / "short_video.mp4"
    create_test_video(video_path, num_frames=8, fps=10.0, width=64, height=64)
    return video_path


@pytest.fixture
def long_video(tmp_path: Path) -> Path:
    video_path = tmp_path / "long_video.mp4"
    create_test_video(video_path, num_frames=30, fps=10.0, width=64, height=64)
    return video_path


class TestVideoIngestion:

    def test_extract_video_metadata_valid(self, short_video):
        meta = extract_video_metadata(short_video)
        assert isinstance(meta, VideoMetadata)
        assert meta.frame_count == 8
        assert meta.fps == 10.0
        assert meta.width == 64
        assert meta.height == 64
        assert meta.duration_seconds == 0.8

    def test_extract_metadata_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            extract_video_metadata(Path("/tmp/nonexistent_video_path.mp4"))

    def test_extract_metadata_corrupt_file(self, tmp_path):
        bad_file = tmp_path / "bad.mp4"
        bad_file.write_text("not a video")
        with pytest.raises(ValueError) as exc:
            extract_video_metadata(bad_file)
        assert "Cannot open video" in str(exc.value) or "Corrupted" in str(exc.value)

    def test_sample_frames_short_video(self, short_video):
        meta, frames = sample_video_frames(short_video, max_frames=16)
        # Should sample all 8 frames
        assert len(frames) == 8
        assert frames[0].frame_index == 0
        assert frames[-1].frame_index == 7
        assert frames[0].timestamp_seconds == 0.0
        assert frames[-1].timestamp_seconds == 0.7
        assert frames[0].frame_rgb.shape == (64, 64, 3)

    def test_sample_frames_long_video_deterministic(self, long_video):
        meta, frames1 = sample_video_frames(long_video, max_frames=10)
        _, frames2 = sample_video_frames(long_video, max_frames=10)

        assert len(frames1) == 10
        assert len(frames2) == 10

        # Deterministic frame indices
        indices1 = [f.frame_index for f in frames1]
        indices2 = [f.frame_index for f in frames2]
        assert indices1 == indices2
        assert indices1[0] == 0
        assert indices1[-1] == 29

    def test_temp_video_file_lifecycle(self, short_video):
        bytes_data = short_video.read_bytes()
        temp_path_ref = None

        with temp_video_file(bytes_data, filename="sample.mp4") as temp_p:
            temp_path_ref = temp_p
            assert temp_p.exists()
            assert temp_p.stat().st_size == len(bytes_data)

        # File must be cleaned up on context manager exit
        assert not temp_path_ref.exists()

    def test_temp_video_file_empty_bytes(self):
        with pytest.raises(ValueError):
            with temp_video_file(b""):
                pass
