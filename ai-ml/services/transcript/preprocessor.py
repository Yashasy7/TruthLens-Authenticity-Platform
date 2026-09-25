"""
TruthLens AI/ML — Module 10: Speech Preprocessing & Demuxing Layer
Blueprint: Ingests audio and video media, demuxes audio tracks to 16 kHz mono WAV,
           enforces duration limits, detects silence, and safely manages temporary media lifecycles.
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple, Union
import wave

import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal

from config.settings import settings

logger = logging.getLogger(__name__)


class PreprocessedAudio:
    """Container holding preprocessed audio file path, waveform, and metadata."""

    def __init__(
        self,
        wav_path: str,
        duration_seconds: float,
        sample_rate: int = 16000,
        is_silent: bool = False,
        media_type: str = "AUDIO",
        rms_energy: float = 0.0,
        waveform: Optional[np.ndarray] = None,
        is_temporary: bool = False,
    ):
        self.wav_path = wav_path
        self.duration_seconds = duration_seconds
        self.sample_rate = sample_rate
        self.is_silent = is_silent
        self.media_type = media_type
        self.rms_energy = rms_energy
        self.waveform = waveform if waveform is not None else np.zeros(0, dtype=np.float32)
        self.is_temporary = is_temporary

    def cleanup(self) -> None:
        """Safely delete temporary WAV file if marked as temporary."""
        if self.is_temporary and os.path.exists(self.wav_path):
            try:
                os.remove(self.wav_path)
            except OSError as exc:
                logger.warning("Failed to clean up temporary audio file %s: %s", self.wav_path, exc)


class SpeechPreprocessor:
    """
    Audio and video preprocessing engine for Speech-to-Text transcription.
    
    Responsibilities:
    1. Untrusted file validation (rejects 0 bytes, corrupted media, image files).
    2. Demuxes audio streams from video containers (MP4, MOV, MKV, AVI, etc.).
    3. Normalizes audio to 16 kHz mono 16-bit linear PCM WAV.
    4. Enforces duration limits (whisper_max_duration_seconds).
    5. Calculates RMS acoustic energy for voice activity / silence gating.
    6. Ensures deterministic temporary file lifecycle management.
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        max_duration_seconds: float = settings.whisper_max_duration_seconds,
        silence_threshold: float = settings.whisper_silence_threshold,
    ):
        self.target_sample_rate = target_sample_rate
        self.max_duration_seconds = max_duration_seconds
        self.silence_threshold = silence_threshold

    @staticmethod
    def _is_image_bytes(data: bytes) -> bool:
        """Inspects magic header bytes to reject image payloads."""
        if len(data) < 8:
            return False
        # PNG: \x89PNG\r\n\x1a\n
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return True
        # JPEG: \xff\xd8\xff
        if data.startswith(b"\xff\xd8\xff"):
            return True
        # GIF: GIF87a or GIF89a
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return True
        # WebP: RIFF....WEBP
        if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
            return True
        # BMP: BM
        if data.startswith(b"BM"):
            return True
        return False

    @staticmethod
    def _find_system_extractor() -> Optional[Tuple[str, list[str]]]:
        """Locates system-level audio converter tool (ffmpeg or macOS afconvert)."""
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            return ("ffmpeg", [ffmpeg_bin, "-nostdin", "-hide_banner", "-loglevel", "error", "-y"])

        afconvert_bin = "/usr/bin/afconvert"
        if os.path.isfile(afconvert_bin) and os.access(afconvert_bin, os.X_OK):
            return ("afconvert", [afconvert_bin])

        return None

    def preprocess_bytes(
        self,
        data: bytes,
        filename: str = "media.wav",
        media_type_hint: Optional[str] = None,
    ) -> PreprocessedAudio:
        """
        Validates and converts in-memory media bytes to normalized 16kHz mono WAV.
        """
        if not data or len(data) == 0:
            raise ValueError("Media payload cannot be empty (0 bytes).")

        if self._is_image_bytes(data):
            raise ValueError("Image media cannot be processed for speech-to-text. Please provide audio or video.")

        # Write to a secure temporary input file
        suffix = Path(filename).suffix if Path(filename).suffix else ".wav"
        fd, temp_input_path = tempfile.mkstemp(prefix="truthlens_stt_in_", suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            return self.preprocess_path(temp_input_path, media_type_hint=media_type_hint, is_input_temporary=True)
        except Exception:
            if os.path.exists(temp_input_path):
                try:
                    os.remove(temp_input_path)
                except OSError:
                    pass
            raise

    def preprocess_path(
        self,
        media_path: str,
        media_type_hint: Optional[str] = None,
        is_input_temporary: bool = False,
    ) -> PreprocessedAudio:
        """
        Converts media file at path to normalized 16kHz mono WAV.
        """
        if not os.path.isfile(media_path):
            raise ValueError(f"Media file not found: {media_path}")

        file_size = os.path.getsize(media_path)
        if file_size == 0:
            if is_input_temporary and os.path.exists(media_path):
                os.remove(media_path)
            raise ValueError("Media file is empty (0 bytes).")

        ext = Path(media_path).suffix.lower()
        video_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".flv", ".wmv"}
        is_video = (media_type_hint == "VIDEO") or (ext in video_exts)
        media_type = "VIDEO" if is_video else "AUDIO"

        waveform: Optional[np.ndarray] = None
        duration: float = 0.0

        # 1. If not video, attempt direct WAV reading with scipy / wave
        if not is_video:
            try:
                waveform, duration = self._load_wav_direct(media_path)
            except Exception:
                waveform = None

        # 2. If direct WAV reading was not applicable or failed, invoke converter
        if waveform is None:
            extractor = self._find_system_extractor()
            if not extractor:
                if is_input_temporary and os.path.exists(media_path):
                    os.remove(media_path)
                raise ValueError("No audio conversion tool available (neither ffmpeg nor afconvert found).")

            tool_name, base_cmd = extractor
            fd_out, temp_wav_path = tempfile.mkstemp(prefix="truthlens_stt_norm_", suffix=".wav")
            os.close(fd_out)

            try:
                if tool_name == "ffmpeg":
                    cmd = base_cmd + [
                        "-i", os.path.abspath(media_path),
                        "-vn",
                        "-acodec", "pcm_s16le",
                        "-ar", str(self.target_sample_rate),
                        "-ac", "1",
                        "-f", "wav",
                        os.path.abspath(temp_wav_path),
                    ]
                else:  # afconvert
                    cmd = base_cmd + [
                        "-d", f"LEI16@{self.target_sample_rate}",
                        "-c", "1",
                        "-f", "WAVE",
                        os.path.abspath(media_path),
                        os.path.abspath(temp_wav_path),
                    ]

                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=settings.whisper_audio_timeout_seconds,
                    check=False,
                )

                if res.returncode != 0 or not os.path.isfile(temp_wav_path) or os.path.getsize(temp_wav_path) == 0:
                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)
                    if is_input_temporary and os.path.exists(media_path):
                        os.remove(media_path)
                    msg = "Media contains no decodable audio stream." if is_video else "Unable to decode media stream. File may be corrupt or an unsupported container."
                    raise ValueError(msg)

                waveform, duration = self._load_wav_direct(temp_wav_path)
                # We can reuse temp_wav_path directly
                out_wav_path = temp_wav_path
            except subprocess.TimeoutExpired:
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)
                if is_input_temporary and os.path.exists(media_path):
                    os.remove(media_path)
                raise ValueError("Audio demuxing/conversion timed out during preprocessing.")
            except Exception:
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)
                if is_input_temporary and os.path.exists(media_path):
                    os.remove(media_path)
                raise
        else:
            # We decoded waveform from WAV directly; now persist to normalized 16kHz mono WAV file
            fd_out, temp_wav_path = tempfile.mkstemp(prefix="truthlens_stt_norm_", suffix=".wav")
            os.close(fd_out)
            int16_samples = np.clip(waveform * 32767.0, -32768.0, 32767.0).astype(np.int16)
            wavfile.write(temp_wav_path, self.target_sample_rate, int16_samples)
            out_wav_path = temp_wav_path

        # Cleanup input temporary file if one was created
        if is_input_temporary and os.path.exists(media_path):
            try:
                os.remove(media_path)
            except OSError:
                pass

        # 3. Validate duration limits
        if duration > self.max_duration_seconds:
            if os.path.exists(out_wav_path):
                os.remove(out_wav_path)
            raise ValueError(
                f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit ({self.max_duration_seconds}s)."
            )

        if duration <= 0.0 or len(waveform) == 0:
            if os.path.exists(out_wav_path):
                os.remove(out_wav_path)
            raise ValueError("Media contains no audio frames.")

        # 4. Measure RMS acoustic energy and silence detection
        rms = float(np.sqrt(np.mean(waveform ** 2))) if len(waveform) > 0 else 0.0
        max_amplitude = float(np.max(np.abs(waveform))) if len(waveform) > 0 else 0.0
        is_silent = (rms < self.silence_threshold) or (max_amplitude < self.silence_threshold)

        return PreprocessedAudio(
            wav_path=out_wav_path,
            duration_seconds=round(duration, 3),
            sample_rate=self.target_sample_rate,
            is_silent=is_silent,
            media_type=media_type,
            rms_energy=round(rms, 6),
            waveform=waveform,
            is_temporary=True,
        )

    def _load_wav_direct(self, wav_path: str) -> Tuple[np.ndarray, float]:
        """Loads and normalizes a WAV file into 16kHz mono float32 waveform."""
        try:
            sr, data = wavfile.read(wav_path)
        except Exception:
            with wave.open(wav_path, "rb") as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                raw_bytes = wf.readframes(n_frames)

            if sampwidth == 2:
                data = np.frombuffer(raw_bytes, dtype=np.int16)
            elif sampwidth == 1:
                data = np.frombuffer(raw_bytes, dtype=np.uint8)
            elif sampwidth == 4:
                data = np.frombuffer(raw_bytes, dtype=np.int32)
            else:
                raise ValueError(f"Unsupported sample width: {sampwidth}")

            if channels > 1:
                data = data.reshape(-1, channels)

        # Downmix multi-channel to mono
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        # Convert to float32 in [-1.0, 1.0]
        if np.issubdtype(data.dtype, np.integer):
            info = np.iinfo(data.dtype)
            if info.min < 0:
                float_data = data.astype(np.float32) / float(-info.min)
            else:
                float_data = (data.astype(np.float32) - 128.0) / 128.0
        elif np.issubdtype(data.dtype, np.floating):
            float_data = np.clip(data.astype(np.float32), -1.0, 1.0)
        else:
            raise ValueError(f"Unsupported audio data format: {data.dtype}")

        # Resample to target sample rate (16000 Hz) if needed
        if sr != self.target_sample_rate and len(float_data) > 0:
            target_len = int(round(len(float_data) * self.target_sample_rate / sr))
            float_data = signal.resample(float_data, target_len).astype(np.float32)

        duration = len(float_data) / float(self.target_sample_rate)
        return float_data, duration
