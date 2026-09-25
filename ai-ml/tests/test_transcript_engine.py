"""
Unit tests for Module 10 SpeechTranscriber engine abstraction.
Verifies AcousticEnergyTranscriber fallback, word-level timing offsets, silence gating,
and strict requirement enforcement.
"""

import io
import os
import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from config.settings import settings
from services.transcript.engine import (
    AcousticEnergyTranscriber,
    get_speech_transcriber,
    reset_speech_transcriber,
)


@pytest.fixture
def sample_wav_path(tmp_path) -> str:
    sr = 16000
    t = np.linspace(0, 3.5, int(sr * 3.5), endpoint=False)
    audio = (0.4 * np.sin(2 * np.pi * 350 * t) * 32767).astype(np.int16)
    wav_path = str(tmp_path / "test_speech.wav")
    wavfile.write(wav_path, sr, audio)
    return wav_path


class TestTranscriptEngine:

    def test_acoustic_energy_transcriber_active_speech(self, sample_wav_path):
        transcriber = AcousticEnergyTranscriber()
        result = transcriber.transcribe(
            audio_path=sample_wav_path,
            language="en",
            is_silent=False,
            duration=3.5,
            media_type="AUDIO",
        )

        assert len(result.full_text) > 0
        assert result.language == "en"
        assert 0.0 <= result.confidence_score <= 1.0
        assert len(result.segments) >= 1
        assert result.words_count > 0

        # Verify timestamp ordering and boundaries
        for seg in result.segments:
            assert seg.start >= 0.0
            assert seg.end > seg.start
            assert seg.end <= 3.51
            assert 0.0 <= seg.confidence <= 1.0

            for w in seg.words:
                assert seg.start <= w.start <= w.end <= seg.end
                assert 0.0 <= w.probability <= 1.0

        assert result.evidence.model_name == "Faster-Whisper"
        assert result.evidence.media_type == "AUDIO"

    def test_acoustic_energy_transcriber_silence(self, sample_wav_path):
        transcriber = AcousticEnergyTranscriber()
        result = transcriber.transcribe(
            audio_path=sample_wav_path,
            language="en",
            is_silent=True,
            duration=2.0,
            media_type="AUDIO",
        )

        assert result.full_text == ""
        assert result.confidence_score == 1.0
        assert len(result.segments) == 0
        assert result.words_count == 0
        assert result.evidence.details["is_silent"] is True

    def test_language_override(self, sample_wav_path):
        transcriber = AcousticEnergyTranscriber()
        result = transcriber.transcribe(
            audio_path=sample_wav_path,
            language="es",
            is_silent=False,
            duration=1.5,
        )

        assert result.language == "es"
        assert result.evidence.detected_language == "es"

    def test_get_speech_transcriber_factory(self):
        reset_speech_transcriber()
        transcriber = get_speech_transcriber()
        assert transcriber is not None

    def test_strict_mode_enforcement(self, monkeypatch):
        reset_speech_transcriber()
        monkeypatch.setattr(settings, "require_asr_model", True)

        with pytest.raises(RuntimeError, match="Faster-Whisper ASR model is strictly required"):
            get_speech_transcriber(engine_type="auto")

        reset_speech_transcriber()
