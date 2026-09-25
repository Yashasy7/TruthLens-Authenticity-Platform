"""
TruthLens AI/ML — Module 07 Tests: Audio Ingestion & Decoding Layer
"""

import io
from pathlib import Path
import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from services.audio_analysis.ingestion import (
    AudioMetadata,
    load_and_preprocess_audio,
    temp_audio_file,
)


def _create_wav_bytes(
    duration: float = 1.0,
    sr: int = 16000,
    channels: int = 1,
    freq: float = 440.0,
    dtype=np.int16,
) -> bytes:
    """Helper to synthesize valid WAV binary bytes."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    if channels == 1:
        if dtype == np.int16:
            data = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
        elif dtype == np.float32:
            data = np.sin(2 * np.pi * freq * t).astype(np.float32)
        else:
            data = ((np.sin(2 * np.pi * freq * t) + 1.0) * 127).astype(np.uint8)
    else:
        ch1 = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
        ch2 = (np.sin(2 * np.pi * (freq * 1.5) * t) * 32767).astype(np.int16)
        data = np.column_stack([ch1, ch2])

    buf = io.BytesIO()
    wavfile.write(buf, sr, data)
    return buf.getvalue()


class TestAudioIngestion:
    """Ingestion & decoding unit tests."""

    def test_load_valid_mono_wav_int16(self):
        wav_bytes = _create_wav_bytes(duration=1.5, sr=16000, channels=1, freq=440.0)
        waveform, meta = load_and_preprocess_audio(wav_bytes, target_sr=16000)

        assert isinstance(waveform, np.ndarray)
        assert waveform.ndim == 1
        assert len(waveform) == 24000
        assert waveform.dtype == np.float32
        assert -1.0 <= waveform.min() and waveform.max() <= 1.0

        assert isinstance(meta, AudioMetadata)
        assert meta.duration_seconds == pytest.approx(1.5, abs=0.01)
        assert meta.sample_rate == 16000
        assert meta.original_sample_rate == 16000
        assert meta.channels == 1
        assert meta.samples == 24000

    def test_load_stereo_and_downmix_to_mono(self):
        wav_bytes = _create_wav_bytes(duration=1.0, sr=16000, channels=2, freq=300.0)
        waveform, meta = load_and_preprocess_audio(wav_bytes, target_sr=16000)

        assert waveform.ndim == 1
        assert meta.channels == 2
        assert meta.samples == 16000

    def test_resample_from_44100_to_16000(self):
        wav_bytes = _create_wav_bytes(duration=2.0, sr=44100, channels=1, freq=500.0)
        waveform, meta = load_and_preprocess_audio(wav_bytes, target_sr=16000)

        assert meta.original_sample_rate == 44100
        assert meta.sample_rate == 16000
        assert len(waveform) == 32000
        assert meta.duration_seconds == pytest.approx(2.0, abs=0.01)

    def test_load_from_filepath(self, tmp_path):
        wav_bytes = _create_wav_bytes(duration=1.0, sr=16000)
        file_path = tmp_path / "sample.wav"
        file_path.write_bytes(wav_bytes)

        waveform, meta = load_and_preprocess_audio(file_path, target_sr=16000)
        assert len(waveform) == 16000
        assert meta.duration_seconds == pytest.approx(1.0, abs=0.01)

    def test_empty_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="Audio payload is empty"):
            load_and_preprocess_audio(b"")

    def test_empty_file_raises_value_error(self, tmp_path):
        empty_file = tmp_path / "empty.wav"
        empty_file.write_bytes(b"")
        with pytest.raises(ValueError, match="Audio file is empty"):
            load_and_preprocess_audio(empty_file)

    def test_nonexistent_file_raises_value_error(self, tmp_path):
        missing = tmp_path / "nonexistent.wav"
        with pytest.raises(ValueError, match="does not exist"):
            load_and_preprocess_audio(missing)

    def test_corrupt_bytes_raises_value_error(self):
        corrupt = b"RIFF\x00\x00\x00\x00WAVEcorruptdata12345678"
        with pytest.raises(ValueError):
            load_and_preprocess_audio(corrupt)

    def test_temp_audio_file_cleanup(self):
        wav_bytes = _create_wav_bytes(duration=0.5, sr=16000)
        temp_path = None
        with temp_audio_file(wav_bytes, filename="test.wav") as p:
            temp_path = p
            assert p.exists()
            assert p.is_file()
            assert p.stat().st_size > 0

        # Must be deleted after context exit
        assert not temp_path.exists()
