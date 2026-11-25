"""
TruthLens AI/ML — Module 07: Audio Ingestion & Decoding Layer
Supported audio formats: WAV, FLAC, OGG, MP3 (decoded via libsndfile/soundfile with
scipy/wave fallback for standard PCM WAV). Deterministic resampling to 16 kHz mono.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import io
import logging
from pathlib import Path
import tempfile
from typing import Generator, Optional, Tuple, Union
import wave

import numpy as np
from scipy import signal
import scipy.io.wavfile as wavfile
import soundfile as sf

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3"}
SUPPORTED_SNDFILE_FORMATS = {"WAV", "FLAC", "OGG", "MP3"}


@dataclass(frozen=True)
class AudioMetadata:
    """Telemetry and format metadata extracted from ingested audio."""
    duration_seconds: float
    sample_rate: int
    original_sample_rate: int
    channels: int
    samples: int
    format_name: str = "WAV"


@contextmanager
def temp_audio_file(
    audio_bytes: bytes,
    filename: str = "audio.wav",
) -> Generator[Path, None, None]:
    """
    Context manager that safely writes uploaded audio bytes to a temporary file
    and guarantees unlink/cleanup upon context exit.
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


def _decode_with_soundfile(stream: io.BytesIO) -> Tuple[int, np.ndarray, int, str]:
    """Decode WAV, FLAC, OGG, or MP3 audio bytes via soundfile/libsndfile."""
    stream.seek(0)
    info = sf.info(stream)
    fmt = (info.format or "").upper()
    if fmt not in SUPPORTED_SNDFILE_FORMATS:
        raise ValueError(
            f"Unsupported audio container format '{fmt}'. "
            f"Supported formats: {sorted(SUPPORTED_SNDFILE_FORMATS)}."
        )
    stream.seek(0)
    data, sr = sf.read(stream, dtype="float32", always_2d=False)
    channels = 1 if data.ndim == 1 else int(data.shape[1])
    float_data = np.clip(np.asarray(data, dtype=np.float32), -1.0, 1.0)
    return int(sr), float_data, channels, fmt


def _decode_wav_fallback(stream: io.BytesIO) -> Tuple[int, np.ndarray, int, str]:
    """Fallback WAV decoder using scipy.io.wavfile and stdlib wave."""
    stream.seek(0)
    try:
        sr, data = wavfile.read(stream)
        channels = 1 if data.ndim == 1 else data.shape[1]

        if np.issubdtype(data.dtype, np.integer):
            info = np.iinfo(data.dtype)
            if info.min < 0:
                float_data = data.astype(np.float32) / float(-info.min)
            else:
                float_data = (data.astype(np.float32) - 128.0) / 128.0
        elif np.issubdtype(data.dtype, np.floating):
            float_data = np.clip(data.astype(np.float32), -1.0, 1.0)
        else:
            raise ValueError(f"Unsupported audio data type: {data.dtype}")

        return int(sr), float_data, channels, "WAV"
    except Exception as exc:
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

                return int(sr), float_data, channels, "WAV"
        except Exception:
            raise ValueError(f"Corrupt, invalid, or unreadable audio format: {exc}") from exc


def load_and_preprocess_audio(
    source: Union[bytes, str, Path],
    target_sr: int = 16000,
    filename: Optional[str] = None,
) -> Tuple[np.ndarray, AudioMetadata]:
    """
    Ingest, validate format (WAV, FLAC, OGG, MP3), decode, convert to mono,
    and deterministically resample an audio track to target_sr.

    Raises:
        ValueError: If audio is empty, unsupported format, corrupted, unreadable, or missing.
    """
    ext_hint: Optional[str] = None
    if isinstance(source, bytes):
        if len(source) == 0:
            raise ValueError("Audio payload is empty (0 bytes).")
        if filename:
            ext = Path(filename).suffix.lower()
            if ext:
                ext_hint = ext
        stream = io.BytesIO(source)
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists() or not p.is_file():
            raise ValueError(f"Audio file does not exist: {p}")
        if p.stat().st_size == 0:
            raise ValueError(f"Audio file is empty (0 bytes): {p}")
        if p.suffix:
            ext_hint = p.suffix.lower()
        stream = io.BytesIO(p.read_bytes())
    else:
        raise TypeError(f"Unsupported audio source type: {type(source)}")

    if ext_hint and ext_hint not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio file format '{ext_hint}'. "
            f"Supported formats: {sorted(SUPPORTED_AUDIO_EXTENSIONS)}."
        )

    try:
        orig_sr, data, channels, fmt_name = _decode_with_soundfile(stream)
    except ValueError as sf_err:
        if "Unsupported audio container format" in str(sf_err):
            raise
        # Try legacy WAV fallback for uncommon WAV headers (e.g. non-standard chunks)
        try:
            orig_sr, data, channels, fmt_name = _decode_wav_fallback(stream)
        except ValueError:
            raise ValueError(f"Corrupt, invalid, or unsupported audio stream: {sf_err}") from sf_err
    except Exception as sf_exc:
        try:
            orig_sr, data, channels, fmt_name = _decode_wav_fallback(stream)
        except ValueError:
            raise ValueError(f"Corrupt, invalid, or unsupported audio stream: {sf_exc}") from sf_exc

    if orig_sr <= 0:
        raise ValueError(f"Invalid audio sample rate: {orig_sr}")

    if data.ndim == 2:
        waveform = np.mean(data, axis=1)
    else:
        waveform = data

    waveform = waveform.astype(np.float32)

    if not np.all(np.isfinite(waveform)):
        waveform = np.nan_to_num(waveform, nan=0.0, posinf=1.0, neginf=-1.0)

    if len(waveform) == 0:
        raise ValueError("Decoded audio contains zero samples.")

    if orig_sr != target_sr:
        num_target_samples = max(1, int(round(len(waveform) * target_sr / orig_sr)))
        waveform = signal.resample(waveform, num_target_samples).astype(np.float32)

    waveform = np.clip(waveform, -1.0, 1.0)

    duration = float(len(waveform) / target_sr)
    metadata = AudioMetadata(
        duration_seconds=duration,
        sample_rate=target_sr,
        original_sample_rate=orig_sr,
        channels=channels,
        samples=len(waveform),
        format_name=fmt_name,
    )

    logger.debug(
        "Ingested audio (%s): duration=%.2fs | orig_sr=%d | target_sr=%d | channels=%d | samples=%d",
        fmt_name, duration, orig_sr, target_sr, channels, len(waveform),
    )
    return waveform, metadata
