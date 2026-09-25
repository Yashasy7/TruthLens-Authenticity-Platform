"""
TruthLens AI/ML — Module 07: Audio Ingestion & Decoding Layer
Blueprint: Ingest audio tracks, deterministic decoding, resample to 16 kHz mono.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import io
import logging
from pathlib import Path
import tempfile
from typing import Generator, Tuple, Union
import wave

import numpy as np
from scipy import signal
import scipy.io.wavfile as wavfile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioMetadata:
    """Telemetry and format metadata extracted from ingested audio."""
    duration_seconds: float
    sample_rate: int
    original_sample_rate: int
    channels: int
    samples: int


@contextmanager
def temp_audio_file(
    audio_bytes: bytes,
    filename: str = "audio.wav",
) -> Generator[Path, None, None]:
    """
    Context manager that safely writes uploaded audio bytes to a temporary file
    and guarantees unlink/cleanup upon context exit.

    Args:
        audio_bytes: Raw binary audio payload.
        filename: Optional source filename to preserve extension.

    Yields:
        Path: Absolute path to the temporary audio file.
    """
    if not audio_bytes:
        raise ValueError("Audio payload cannot be empty.")

    suffix = Path(filename).suffix if Path(filename).suffix else ".wav"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        temp_file.write(audio_bytes)
        temp_file.flush()
        temp_file.close()
        yield Path(temp_file.name)
    finally:
        p = Path(temp_file.name)
        if p.exists():
            try:
                p.unlink()
            except OSError as err:
                logger.warning("Failed to remove temporary audio file %s: %s", p, err)


def _decode_wav_stream(
    stream: io.BytesIO,
) -> Tuple[int, np.ndarray, int]:
    """
    Attempt WAV decoding using scipy.io.wavfile, falling back to python stdlib wave.
    Returns: (original_sample_rate, normalized_float_data, channels)
    """
    stream.seek(0)
    try:
        sr, data = wavfile.read(stream)
        channels = 1 if data.ndim == 1 else data.shape[1]

        # Convert to float32 normalized in [-1.0, 1.0]
        if np.issubdtype(data.dtype, np.integer):
            info = np.iinfo(data.dtype)
            if info.min < 0:
                float_data = data.astype(np.float32) / float(-info.min)
            else:  # uint8: 0..255 -> -1..1
                float_data = (data.astype(np.float32) - 128.0) / 128.0
        elif np.issubdtype(data.dtype, np.floating):
            float_data = np.clip(data.astype(np.float32), -1.0, 1.0)
        else:
            raise ValueError(f"Unsupported audio data type: {data.dtype}")

        return sr, float_data, channels
    except Exception as exc:
        # Fallback to stdlib wave
        stream.seek(0)
        try:
            with wave.open(stream, "rb") as wf:
                sr = wf.getframerate()
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                n_frames = wf.getnframes()
                raw_frames = wf.readframes(n_frames)

                if sampwidth == 1:
                    data = np.frombuffer(raw_frames, dtype=np.uint8)
                    float_data = (data.astype(np.float32) - 128.0) / 128.0
                elif sampwidth == 2:
                    data = np.frombuffer(raw_frames, dtype=np.int16)
                    float_data = data.astype(np.float32) / 32768.0
                elif sampwidth == 4:
                    data = np.frombuffer(raw_frames, dtype=np.int32)
                    float_data = data.astype(np.float32) / 2147483648.0
                else:
                    raise ValueError(f"Unsupported sample width: {sampwidth} bytes")

                if channels > 1:
                    float_data = float_data.reshape(-1, channels)

                return sr, float_data, channels
        except Exception:
            raise ValueError(f"Corrupt, invalid, or unreadable audio format: {exc}") from exc


def load_and_preprocess_audio(
    source: Union[bytes, str, Path],
    target_sr: int = 16000,
) -> Tuple[np.ndarray, AudioMetadata]:
    """
    Ingest, decode, convert to mono, and resample an audio track to target_sr.

    Args:
        source: Raw binary audio bytes or path to an audio file on disk.
        target_sr: Standardized sample rate for forensic analysis (default: 16000 Hz).

    Returns:
        Tuple[np.ndarray, AudioMetadata]:
            - waveform: 1D float32 numpy array normalized to [-1.0, 1.0] at target_sr.
            - metadata: Extracted AudioMetadata.

    Raises:
        ValueError: If audio is empty, corrupted, unreadable, or missing.
    """
    if isinstance(source, bytes):
        if len(source) == 0:
            raise ValueError("Audio payload is empty (0 bytes).")
        stream = io.BytesIO(source)
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists() or not p.is_file():
            raise ValueError(f"Audio file does not exist: {p}")
        if p.stat().st_size == 0:
            raise ValueError(f"Audio file is empty (0 bytes): {p}")
        stream = io.BytesIO(p.read_bytes())
    else:
        raise TypeError(f"Unsupported audio source type: {type(source)}")

    orig_sr, data, channels = _decode_wav_stream(stream)

    if orig_sr <= 0:
        raise ValueError(f"Invalid audio sample rate: {orig_sr}")

    # Downmix multi-channel to mono
    if data.ndim == 2:
        waveform = np.mean(data, axis=1)
    else:
        waveform = data

    waveform = waveform.astype(np.float32)

    # Sanitize NaN / Inf
    if not np.all(np.isfinite(waveform)):
        waveform = np.nan_to_num(waveform, nan=0.0, posinf=1.0, neginf=-1.0)

    if len(waveform) == 0:
        raise ValueError("Decoded audio contains zero samples.")

    # Resample to target_sr if necessary
    if orig_sr != target_sr:
        num_target_samples = max(1, int(round(len(waveform) * target_sr / orig_sr)))
        waveform = signal.resample(waveform, num_target_samples).astype(np.float32)

    # Clamp bounds [-1.0, 1.0]
    waveform = np.clip(waveform, -1.0, 1.0)

    duration = float(len(waveform) / target_sr)
    metadata = AudioMetadata(
        duration_seconds=duration,
        sample_rate=target_sr,
        original_sample_rate=orig_sr,
        channels=channels,
        samples=len(waveform),
    )

    logger.debug(
        "Ingested audio: duration=%.2fs | orig_sr=%d | target_sr=%d | channels=%d | samples=%d",
        duration, orig_sr, target_sr, channels, len(waveform)
    )

    return waveform, metadata
