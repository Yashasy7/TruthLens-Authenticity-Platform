"""
TruthLens AI/ML — Module 08: Audio-Visual Media Ingestion & Demuxing Layer
Blueprint: Ingest dual-track video + audio containers, extract video frames at target FPS,
           and demux audio stream to 16 kHz mono float32.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np

from config.settings import settings
from services.audio_analysis.ingestion import load_and_preprocess_audio
from services.video_analysis.ingestion import temp_video_file

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AvMediaContainer:
    """Synchronized container of decoded visual frames and audio waveform."""
    frames_rgb: List[np.ndarray]
    timestamps: np.ndarray           # 1D array of frame timestamps in seconds
    fps: float                       # Video sampling frame rate
    video_duration: float
    waveform: np.ndarray             # 1D float32 audio waveform at 16kHz
    audio_sample_rate: int           # Standardized audio sample rate (16000)
    audio_duration: float
    has_audio: bool

    @property
    def frames(self) -> List[np.ndarray]:
        return self.frames_rgb

    @property
    def frame_timestamps(self) -> np.ndarray:
        return self.timestamps

    @property
    def total_frames(self) -> int:
        return len(self.frames_rgb)

    @property
    def duration_seconds(self) -> float:
        return self.video_duration

    @property
    def audio_waveform(self) -> np.ndarray:
        return self.waveform


def _find_audio_converter() -> Optional[Tuple[str, List[str]]]:
    """
    Locates an available system audio extractor tool:
    Prefers ffmpeg if available in PATH, otherwise checks macOS native /usr/bin/afconvert.
    Returns (tool_name, base_cmd_prefix) or None.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ("ffmpeg", [ffmpeg_path, "-nostdin", "-hide_banner", "-loglevel", "error", "-y"])

    afconvert_path = "/usr/bin/afconvert"
    if os.path.isfile(afconvert_path) and os.access(afconvert_path, os.X_OK):
        return ("afconvert", [afconvert_path])

    return None


def extract_audio_track(
    video_path: Path,
    target_sr: int = 16000,
) -> Tuple[np.ndarray, float, bool]:
    """
    Extract audio track from video container into a normalized 16 kHz mono waveform.

    Args:
        video_path: Path to video file on disk.
        target_sr: Target sample rate in Hz (default: 16000).

    Returns:
        Tuple[waveform, audio_duration, has_audio]
    """
    # 1. First check if file is directly a WAV / audio file
    try:
        waveform, meta = load_and_preprocess_audio(video_path, target_sr=target_sr)
        logger.debug("Source file decoded directly as audio waveform | duration=%.2fs", meta.duration_seconds)
        return waveform, meta.duration_seconds, True
    except Exception:
        pass

    # 2. Use system extractor (ffmpeg or macOS afconvert) to demux audio stream
    converter = _find_audio_converter()
    if not converter:
        logger.warning("No audio converter tool available (ffmpeg or afconvert not found).")
        return np.zeros(0, dtype=np.float32), 0.0, False

    tool_name, prefix = converter
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        temp_wav_path = Path(tmp_wav.name)

    try:
        if tool_name == "ffmpeg":
            cmd = prefix + [
                "-i", str(video_path.resolve()),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", str(target_sr),
                "-ac", "1",
                "-f", "wav",
                str(temp_wav_path.resolve()),
            ]
        else:  # afconvert
            cmd = prefix + [
                "-d", f"LEI16@{target_sr}",
                "-c", "1",
                "-f", "WAVE",
                str(video_path.resolve()),
                str(temp_wav_path.resolve()),
            ]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        if res.returncode == 0 and temp_wav_path.exists() and temp_wav_path.stat().st_size > 44:
            waveform, meta = load_and_preprocess_audio(temp_wav_path, target_sr=target_sr)
            return waveform, meta.duration_seconds, True
        else:
            logger.info("Video container does not contain an extractable audio track (returncode=%d)", res.returncode)
            return np.zeros(0, dtype=np.float32), 0.0, False

    except Exception as exc:
        logger.warning("Audio extraction failed from video container %s: %s", video_path, exc)
        return np.zeros(0, dtype=np.float32), 0.0, False
    finally:
        if temp_wav_path.exists():
            try:
                temp_wav_path.unlink()
            except OSError:
                pass


def ingest_av_media(
    source: Union[bytes, str, Path],
    filename: str = "video.mp4",
    target_fps: float = 25.0,
    target_sr: int = 16000,
    max_duration_seconds: float = 60.0,
) -> AvMediaContainer:
    """
    Ingest uploaded video asset, decode visual frames at target_fps,
    and demux audio track to 16 kHz mono waveform.

    Args:
        source: Binary video bytes or local filesystem path.
        filename: Uploaded filename hint.
        target_fps: Frame rate for video sampling (default: 25.0 fps).
        target_sr: Audio sample rate in Hz (default: 16000 Hz).
        max_duration_seconds: Maximum analysis clip duration.

    Returns:
        AvMediaContainer containing synchronized frames, timestamps, and audio waveform.

    Raises:
        ValueError: If media is corrupt, empty, or unreadable.
    """
    if isinstance(source, bytes):
        if len(source) == 0:
            raise ValueError("Uploaded media payload is empty (0 bytes).")
        with temp_video_file(source, filename=filename) as temp_path:
            return _process_av_file(
                temp_path,
                target_fps=target_fps,
                target_sr=target_sr,
                max_duration_seconds=max_duration_seconds,
            )
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists() or not p.is_file():
            raise ValueError(f"Media file does not exist: {p}")
        if p.stat().st_size == 0:
            raise ValueError(f"Media file is empty (0 bytes): {p}")
        return _process_av_file(
            p,
            target_fps=target_fps,
            target_sr=target_sr,
            max_duration_seconds=max_duration_seconds,
        )
    else:
        raise TypeError(f"Unsupported media source type: {type(source)}")


def _process_av_file(
    video_path: Path,
    target_fps: float = 25.0,
    target_sr: int = 16000,
    max_duration_seconds: float = 60.0,
) -> AvMediaContainer:
    """Internal decoding helper executing OpenCV frame sampling and audio extraction."""
    # 1. Extract audio track
    waveform, audio_dur, has_audio = extract_audio_track(video_path, target_sr=target_sr)

    # 2. Decode video stream using OpenCV
    cap = cv2.VideoCapture(str(video_path.resolve()))
    if not cap.isOpened():
        # If OpenCV fails to open as video, but it was decoded as audio, construct audio-only container
        if has_audio and len(waveform) > 0:
            frames_to_make = max(1, int(round(audio_dur * target_fps)))
            dummy_frames = [np.zeros((96, 96, 3), dtype=np.uint8) for _ in range(frames_to_make)]
            ts = np.arange(frames_to_make) / target_fps
            return AvMediaContainer(
                frames_rgb=dummy_frames,
                timestamps=ts,
                fps=target_fps,
                video_duration=audio_dur,
                waveform=waveform,
                audio_sample_rate=target_sr,
                audio_duration=audio_dur,
                has_audio=True,
            )
        raise ValueError("Unable to decode video stream. File may be corrupt or an unsupported container.")

    native_fps = float(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if native_fps <= 0.0 or np.isnan(native_fps):
        native_fps = target_fps

    native_duration = float(total_frames / native_fps) if total_frames > 0 else 0.0
    effective_duration = min(max_duration_seconds, native_duration if native_duration > 0.0 else max_duration_seconds)
    max_frames_to_sample = int(min(effective_duration * target_fps, 1500))

    frames_rgb: List[np.ndarray] = []
    timestamps_list: List[float] = []

    frame_interval = max(1, int(round(native_fps / target_fps)))
    current_frame_idx = 0

    try:
        while cap.isOpened() and len(frames_rgb) < max_frames_to_sample:
            ret, bgr_frame = cap.read()
            if not ret or bgr_frame is None:
                break

            if current_frame_idx % frame_interval == 0:
                rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                frames_rgb.append(rgb_frame)
                t_sec = current_frame_idx / native_fps
                timestamps_list.append(round(float(t_sec), 4))

            current_frame_idx += 1
    finally:
        cap.release()

    if len(frames_rgb) == 0:
        if has_audio and len(waveform) > 0:
            frames_to_make = max(1, int(round(audio_dur * target_fps)))
            dummy_frames = [np.zeros((96, 96, 3), dtype=np.uint8) for _ in range(frames_to_make)]
            ts = np.arange(frames_to_make) / target_fps
            return AvMediaContainer(
                frames_rgb=dummy_frames,
                timestamps=ts,
                fps=target_fps,
                video_duration=audio_dur,
                waveform=waveform,
                audio_sample_rate=target_sr,
                audio_duration=audio_dur,
                has_audio=True,
            )
        raise ValueError("Decoded video contains zero readable frames.")

    timestamps = np.array(timestamps_list, dtype=np.float32)
    video_dur = float(timestamps[-1]) if len(timestamps) > 0 else 0.0

    return AvMediaContainer(
        frames_rgb=frames_rgb,
        timestamps=timestamps,
        fps=target_fps,
        video_duration=video_dur,
        waveform=waveform,
        audio_sample_rate=target_sr,
        audio_duration=audio_dur,
        has_audio=has_audio,
    )


# Alias for pipeline compatibility
decode_video_and_extract_audio = ingest_av_media
