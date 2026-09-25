"""
Unit tests for Module 10 SpeechPreprocessor
Verifies audio/video demuxing, normalization to 16kHz mono WAV, duration limits, silence detection, and cleanup.
"""

import io
import os
import wave
from pathlib import Path
import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from config.settings import settings
from services.transcript.preprocessor import SpeechPreprocessor, PreprocessedAudio


@pytest.fixture
def sample_speech_wav_bytes() -> bytes:
    """Creates a 2-second synthesized sine wave tone resembling speech audio."""
    sr = 16000
    t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    # 440 Hz tone with harmonics to represent voiced speech
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.25 * np.sin(2 * np.pi * 880 * t)
    audio_int16 = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    wavfile.write(buf, sr, audio_int16)
    return buf.getvalue()


@pytest.fixture
def sample_silent_wav_bytes() -> bytes:
    """Creates a 1-second pure silent WAV."""
    sr = 16000
    audio_silent = np.zeros(int(sr * 1.0), dtype=np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sr, audio_silent)
    return buf.getvalue()


class TestSpeechPreprocessor:

    def test_preprocess_valid_wav_bytes(self, sample_speech_wav_bytes):
        preprocessor = SpeechPreprocessor()
        result = preprocessor.preprocess_bytes(sample_speech_wav_bytes, filename="speech.wav")

        try:
            assert isinstance(result, PreprocessedAudio)
            assert os.path.exists(result.wav_path)
            assert result.sample_rate == 16000
            assert 1.95 <= result.duration_seconds <= 2.05
            assert result.is_silent is False
            assert result.media_type == "AUDIO"
            assert result.rms_energy > 0.1
        finally:
            result.cleanup()

        assert not os.path.exists(result.wav_path)

    def test_preprocess_silent_audio(self, sample_silent_wav_bytes):
        preprocessor = SpeechPreprocessor()
        result = preprocessor.preprocess_bytes(sample_silent_wav_bytes, filename="silent.wav")

        try:
            assert result.is_silent is True
            assert result.duration_seconds > 0.0
            assert result.rms_energy < 1e-4
        finally:
            result.cleanup()

    def test_reject_empty_bytes(self):
        preprocessor = SpeechPreprocessor()
        with pytest.raises(ValueError, match="cannot be empty"):
            preprocessor.preprocess_bytes(b"", filename="empty.wav")

    def test_reject_image_payload(self):
        preprocessor = SpeechPreprocessor()
        # PNG magic header
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        with pytest.raises(ValueError, match="Image media cannot be processed"):
            preprocessor.preprocess_bytes(fake_png, filename="fake.png")

        # JPEG magic header
        fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 64
        with pytest.raises(ValueError, match="Image media cannot be processed"):
            preprocessor.preprocess_bytes(fake_jpeg, filename="fake.jpg")

    def test_reject_duration_exceeded(self):
        # Configure a small max duration of 1.0 second
        preprocessor = SpeechPreprocessor(max_duration_seconds=1.0)
        # Create a 2.0-second audio stream
        sr = 16000
        audio = (0.2 * np.sin(np.linspace(0, 2 * np.pi * 400 * 2, int(sr * 2.0))) * 32767).astype(np.int16)
        buf = io.BytesIO()
        wavfile.write(buf, sr, audio)

        with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
            preprocessor.preprocess_bytes(buf.getvalue(), filename="long.wav")

    def test_preprocess_stereo_resampling(self):
        """Tests that stereo 44.1kHz audio is downmixed to mono and resampled to 16kHz."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        left = (0.4 * np.sin(2 * np.pi * 300 * t) * 32767).astype(np.int16)
        right = (0.4 * np.sin(2 * np.pi * 500 * t) * 32767).astype(np.int16)
        stereo = np.column_stack([left, right])

        buf = io.BytesIO()
        wavfile.write(buf, sr, stereo)

        preprocessor = SpeechPreprocessor()
        result = preprocessor.preprocess_bytes(buf.getvalue(), filename="stereo.wav")

        try:
            assert result.sample_rate == 16000
            assert 0.95 <= result.duration_seconds <= 1.05
            assert result.is_silent is False
        finally:
            result.cleanup()
