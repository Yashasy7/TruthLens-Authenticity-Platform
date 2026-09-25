"""
TruthLens AI/ML — Module 07 Tests: Acoustic Pitch & Fundamental Frequency Forensics
"""

import numpy as np
import pytest

from services.audio_analysis.pitch import (
    PitchAnalysisResult,
    extract_pitch_contour,
)


class TestAudioPitch:
    """Pitch and pitch variance unit tests."""

    def test_pure_tone_pitch_and_variance(self):
        sr = 16000
        t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
        # 300 Hz pure tone
        waveform = (0.7 * np.sin(2 * np.pi * 300.0 * t)).astype(np.float32)

        result = extract_pitch_contour(waveform, sr=sr, fmin=60.0, fmax=500.0)

        assert isinstance(result, PitchAnalysisResult)
        assert 285.0 <= result.pitch_mean <= 315.0
        # A steady pure tone has negligible pitch variance
        assert result.pitch_variance < 5.0
        assert result.voiced_fraction > 0.8
        assert len(result.f0_contour) == len(result.time_axis)

    def test_frequency_modulated_tone_has_high_variance(self):
        sr = 16000
        t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
        # FM tone sweeping between 200 Hz and 400 Hz
        inst_freq = 300.0 + 80.0 * np.sin(2 * np.pi * 3.0 * t)
        phase = 2 * np.pi * np.cumsum(inst_freq) / sr
        waveform = (0.7 * np.sin(phase)).astype(np.float32)

        result = extract_pitch_contour(waveform, sr=sr, fmin=60.0, fmax=500.0)

        assert result.voiced_fraction > 0.7
        # Pitch variance must be noticeably higher than steady tone
        assert result.pitch_variance > 200.0

    def test_silent_audio_returns_zero_pitch(self):
        silent = np.zeros(16000, dtype=np.float32)
        result = extract_pitch_contour(silent, sr=16000)

        assert result.pitch_mean == 0.0
        assert result.pitch_variance == 0.0
        assert result.voiced_fraction == 0.0
        assert np.all(result.f0_contour == 0.0)

    def test_short_audio_padding(self):
        # Short audio (only 200 samples)
        short_wave = np.sin(2 * np.pi * 200.0 * np.linspace(0, 0.01, 200)).astype(np.float32)
        result = extract_pitch_contour(short_wave, sr=16000)

        assert isinstance(result, PitchAnalysisResult)
        assert result.pitch_mean >= 0.0
        assert result.pitch_variance >= 0.0
