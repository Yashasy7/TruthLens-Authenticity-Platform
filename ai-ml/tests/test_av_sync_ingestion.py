"""
TruthLens AI/ML — Module 08: Media Ingestion & Demuxing Tests
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest
from scipy.io import wavfile

from services.av_sync.ingestion import (
    AvMediaContainer,
    ingest_av_media,
    decode_video_and_extract_audio,
)


@pytest.fixture
def synthetic_video_bytes() -> bytes:
    """Generate a short 1-second synthetic video with black/white alternating frames."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        path = Path(tmp.name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 25.0
    out = cv2.VideoWriter(str(path), fourcc, fps, (128, 128))
    for i in range(25):
        val = 255 if i % 2 == 0 else 0
        frame = np.full((128, 128, 3), val, dtype=np.uint8)
        out.write(frame)
    out.release()

    video_bytes = path.read_bytes()
    path.unlink(missing_ok=True)
    return video_bytes


@pytest.fixture
def synthetic_wav_bytes() -> bytes:
    """Generate 1 second of 16kHz sine wave audio."""
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    # 440 Hz tone
    samples = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    wavfile.write(str(wav_path), sr, samples)
    content = wav_path.read_bytes()
    wav_path.unlink(missing_ok=True)
    return content


def test_ingest_empty_bytes_raises():
    """Empty payload must raise ValueError."""
    with pytest.raises(ValueError, match="empty"):
        ingest_av_media(b"", filename="empty.mp4")


def test_ingest_corrupt_bytes_raises():
    """Corrupt non-media bytes must raise ValueError."""
    with pytest.raises(ValueError):
        ingest_av_media(b"CORRUPT_NOT_A_REAL_VIDEO_HEADER", filename="bad.mp4")


def test_ingest_synthetic_video(synthetic_video_bytes: bytes):
    """Synthetic video container is ingested and sampled at 25 fps."""
    container = ingest_av_media(synthetic_video_bytes, filename="synth.mp4", target_fps=25.0)

    assert isinstance(container, AvMediaContainer)
    assert container.total_frames >= 20
    assert len(container.frames) == container.total_frames
    assert container.fps == 25.0
    assert len(container.frame_timestamps) == container.total_frames
    assert container.duration_seconds > 0.5


def test_ingest_wav_as_source(synthetic_wav_bytes: bytes):
    """Audio-only WAV source is ingested gracefully with fallback dummy frames."""
    container = ingest_av_media(synthetic_wav_bytes, filename="audio.wav", target_fps=25.0)

    assert container.has_audio is True
    assert len(container.audio_waveform) > 0
    assert container.audio_sample_rate == 16000
    assert container.total_frames > 0


def test_container_property_aliases():
    """Verify AvMediaContainer aliases for pipeline compatibility."""
    frames = [np.zeros((64, 64, 3), dtype=np.uint8)]
    ts = np.array([0.0], dtype=np.float32)
    wf = np.array([0.1, 0.2], dtype=np.float32)

    container = AvMediaContainer(
        frames_rgb=frames,
        timestamps=ts,
        fps=25.0,
        video_duration=1.0,
        waveform=wf,
        audio_sample_rate=16000,
        audio_duration=1.0,
        has_audio=True,
    )

    assert container.frames is frames
    assert container.frame_timestamps is ts
    assert container.total_frames == 1
    assert container.duration_seconds == 1.0
    assert container.audio_waveform is wf
    assert decode_video_and_extract_audio is ingest_av_media
