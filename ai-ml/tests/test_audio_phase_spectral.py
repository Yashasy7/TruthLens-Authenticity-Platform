"""
TruthLens AI/ML — Module 07 Tests: Phase Discontinuity & Spectral Forensics
"""

import numpy as np
import pytest

from services.audio_analysis.phase_spectral import (
    PhaseSpectralForensics,
    analyze_phase_and_spectral_forensics,
)


class TestAudioPhaseSpectral:
    """Phase and spectral forensics unit tests."""

    def test_clean_tone_phase_analysis(self):
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = (0.6 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

        res = analyze_phase_and_spectral_forensics(tone, sr=sr)
        assert isinstance(res, PhaseSpectralForensics)
        assert 0.0 <= res.phase_discontinuity_score <= 1.0
        assert 0.0 <= res.spectral_anomaly_score <= 1.0
        assert len(res.frame_phase_discontinuity) > 0
        assert res.high_freq_attenuation_ratio >= 0.0

    def test_white_noise_phase_discontinuity(self):
        sr = 16000
        noise = (np.random.randn(sr) * 0.3).astype(np.float32)

        res = analyze_phase_and_spectral_forensics(noise, sr=sr)
        assert 0.0 <= res.phase_discontinuity_score <= 1.0
        assert 0.0 <= res.spectral_anomaly_score <= 1.0

    def test_silent_audio(self):
        silent = np.zeros(16000, dtype=np.float32)
        res = analyze_phase_and_spectral_forensics(silent, sr=16000)

        assert 0.0 <= res.phase_discontinuity_score <= 1.0
        assert 0.0 <= res.spectral_anomaly_score <= 1.0
