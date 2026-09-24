import os
import shutil
import subprocess
import tempfile
from typing import Tuple, Optional
import soundfile as sf
import numpy as np
from ..config import settings


class PreprocessedAudio:
    """Container for preprocessed audio path and acoustic metadata."""
    def __init__(
        self,
        wav_path: str,
        duration_seconds: float,
        sample_rate: int,
        is_silent: bool,
        is_temporary: bool = False,
    ):
        self.wav_path = wav_path
        self.duration_seconds = duration_seconds
        self.sample_rate = sample_rate
        self.is_silent = is_silent
        self.is_temporary = is_temporary

    def cleanup(self):
        if self.is_temporary and os.path.exists(self.wav_path):
            try:
                os.remove(self.wav_path)
            except OSError:
                pass


class SpeechPreprocessor:
    """
    Audio preprocessing for Faster-Whisper Speech-to-Text (Module 10).
    
    Responsibilities:
    1. Demuxes audio track from video files into 16kHz mono PCM WAV.
    2. Resamples and standardizes audio files to 16kHz mono PCM WAV.
    3. Enforces maximum audio duration limit (WHISPER_MAX_DURATION_SECONDS).
    4. Evaluates root-mean-square (RMS) energy to detect silent / empty speech tracks.
    5. Safely manages temporary file lifecycles.
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        max_duration_seconds: float = settings.WHISPER_MAX_DURATION_SECONDS,
        ffmpeg_path: str = settings.FFMPEG_PATH,
    ):
        self.target_sample_rate = target_sample_rate
        self.max_duration_seconds = max_duration_seconds
        self.ffmpeg_path = ffmpeg_path

    def _resolve_ffmpeg_cmd(self) -> str:
        """Finds valid FFmpeg binary path."""
        if shutil.which(self.ffmpeg_path):
            return self.ffmpeg_path
        if os.path.isfile(self.ffmpeg_path) and os.access(self.ffmpeg_path, os.X_OK):
            return self.ffmpeg_path
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if os.path.isfile(exe):
                return exe
        except Exception:
            pass
        return "ffmpeg"

    def preprocess(self, media_path: str, media_type: Optional[str] = None) -> PreprocessedAudio:
        """
        Converts/demuxes media input to a clean 16kHz mono PCM WAV for Whisper ASR.
        
        Args:
            media_path: Local path to the audio or video media file.
            media_type: Optional hint ('AUDIO' or 'VIDEO').
            
        Returns:
            PreprocessedAudio instance with normalized WAV path and duration.
            
        Raises:
            ValueError: If file is missing, exceeds duration, or cannot be decoded.
        """
        if not os.path.isfile(media_path):
            raise ValueError(f"Media file not found: {media_path}")

        ext = os.path.splitext(media_path)[1].lower()
        video_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".mpeg", ".flv"}
        is_video = (media_type == "VIDEO") or (ext in video_exts)

        ffmpeg_cmd = self._resolve_ffmpeg_cmd()
        fd, temp_wav_path = tempfile.mkstemp(prefix="truthlens_stt_norm_", suffix=".wav")
        os.close(fd)

        # Build FFmpeg command to extract/convert to 16kHz mono 16-bit PCM WAV
        cmd = [
            ffmpeg_cmd,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", os.path.abspath(media_path),
            "-vn",  # Discard video if present
            "-acodec", "pcm_s16le",
            "-ar", str(self.target_sample_rate),
            "-ac", "1",  # Mono
            "-f", "wav",
            os.path.abspath(temp_wav_path)
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.AUDIO_PROCESSING_TIMEOUT_SECONDS,
                check=False
            )
            if res.returncode != 0 or not os.path.isfile(temp_wav_path) or os.path.getsize(temp_wav_path) == 0:
                if os.path.exists(temp_wav_path):
                    try:
                        os.remove(temp_wav_path)
                    except OSError:
                        pass
                msg = "Media contains no decodable audio stream." if is_video else "Audio format could not be decoded."
                raise ValueError(msg)

            # Validate duration and silent check via soundfile
            with sf.SoundFile(temp_wav_path) as audio_file:
                frames = audio_file.frames
                sr = audio_file.samplerate
                duration = frames / float(sr) if sr > 0 else 0.0
                audio_data = audio_file.read(min(frames, sr * 5), dtype="float32")
                rms = float(np.sqrt(np.mean(audio_data ** 2))) if len(audio_data) > 0 else 0.0
                is_silent = rms < 1e-4

            if duration > self.max_duration_seconds:
                if os.path.exists(temp_wav_path):
                    try:
                        os.remove(temp_wav_path)
                    except OSError:
                        pass
                raise ValueError(
                    f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit ({self.max_duration_seconds}s)."
                )

            if frames == 0 or duration == 0:
                if os.path.exists(temp_wav_path):
                    try:
                        os.remove(temp_wav_path)
                    except OSError:
                        pass
                raise ValueError("Audio stream has 0 duration or frames.")

            return PreprocessedAudio(
                wav_path=temp_wav_path,
                duration_seconds=round(duration, 3),
                sample_rate=sr,
                is_silent=is_silent,
                is_temporary=True,
            )

        except subprocess.TimeoutExpired:
            if os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except OSError:
                    pass
            raise ValueError("Audio demuxing/conversion timed out during preprocessing.")
