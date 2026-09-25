"""
Unit tests for Module 10 Speech-to-Text service orchestration layer.
Verifies analyze_speech_to_text_bytes and analyze_speech_to_text_from_path workflows.
"""

import io
import os
import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from schemas.transcript import BackendTranscriptResponse
from services.transcript.service import (
    analyze_speech_to_text_bytes,
    analyze_speech_to_text_from_path,
)


@pytest.fixture
def sample_audio_bytes() -> bytes:
    sr = 16000
    t = np.linspace(0, 2.5, int(sr * 2.5), endpoint=False)
    audio = (0.5 * np.sin(2 * np.pi * 320 * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sr, audio)
    return buf.getvalue()


@pytest.fixture
def silent_audio_bytes() -> bytes:
    sr = 16000
    audio = np.zeros(int(sr * 1.5), dtype=np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sr, audio)
    return buf.getvalue()


class TestTranscriptService:

    def test_analyze_speech_to_text_bytes_active(self, sample_audio_bytes):
        resp = analyze_speech_to_text_bytes(
            file_bytes=sample_audio_bytes,
            filename="sample.wav",
            content_type="audio/wav",
            language="en",
        )

        assert isinstance(resp, BackendTranscriptResponse)
        assert resp.status == "COMPLETED"
        assert len(resp.full_text) > 0
        assert resp.language == "en"
        assert 0.0 <= resp.confidence_score <= 1.0
        assert 2.4 <= resp.duration_seconds <= 2.6
        assert resp.segments_count >= 1
        assert resp.words_count > 0
        assert resp.error_message is None

    def test_analyze_speech_to_text_bytes_silent(self, silent_audio_bytes):
        resp = analyze_speech_to_text_bytes(
            file_bytes=silent_audio_bytes,
            filename="silent.wav",
            content_type="audio/wav",
        )

        assert resp.status == "COMPLETED"
        assert resp.full_text == ""
        assert resp.segments_count == 0
        assert resp.words_count == 0
        assert resp.confidence_score == 1.0

    def test_analyze_speech_to_text_from_path(self, sample_audio_bytes, tmp_path):
        wav_file = str(tmp_path / "service_test.wav")
        with open(wav_file, "wb") as f:
            f.write(sample_audio_bytes)

        resp = analyze_speech_to_text_from_path(media_path=wav_file, language="en")
        assert resp.status == "COMPLETED"
        assert len(resp.full_text) > 0
        assert resp.segments_count >= 1

    def test_service_rejects_empty_bytes(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            analyze_speech_to_text_bytes(file_bytes=b"", filename="empty.wav")

    def test_service_rejects_image(self):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        with pytest.raises(ValueError, match="Image media cannot be processed"):
            analyze_speech_to_text_bytes(file_bytes=fake_png, filename="fake.png")
