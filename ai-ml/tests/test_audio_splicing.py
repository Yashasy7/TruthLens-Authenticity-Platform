"""
TruthLens AI/ML — Module 07 Tests: Audio Splice Boundary Detection
"""

import numpy as np
import pytest

from schemas.audio_analysis import AudioSpliceMarker
from services.audio_analysis.features import extract_acoustic_features
from services.audio_analysis.phase_spectral import analyze_phase_and_spectral_forensics
from services.audio_analysis.splicing import detect_audio_splices


class TestAudioSplicing:
    """Audio splicing boundary detection unit tests."""

    def test_continuous_tone_has_zero_splice_markers(self):
        sr = 16000
        t = np.linspace(0, 2.0, sr * 2, endpoint=False)
        clean = (0.5 * np.sin(2 * np.pi * 300.0 * t)).astype(np.float32)

        feat = extract_acoustic_features(clean, sr=sr)
        phase = analyze_phase_and_spectral_forensics(clean, sr=sr)
        markers = detect_audio_splices(feat, phase, threshold=0.55)

        assert isinstance(markers, list)
        assert len(markers) == 0

    def test_spliced_signal_detects_boundary(self):
        sr = 16000
        t1 = np.linspace(0, 1.0, sr, endpoint=False)
        t2 = np.linspace(0, 1.0, sr, endpoint=False)
        part1 = 0.7 * np.sin(2 * np.pi * 300.0 * t1)
        part2 = 0.2 * np.sin(2 * np.pi * 900.0 * t2)
        spliced = np.concatenate([part1, part2]).astype(np.float32)

        feat = extract_acoustic_features(spliced, sr=sr)
        phase = analyze_phase_and_spectral_forensics(spliced, sr=sr)
        markers = detect_audio_splices(feat, phase, threshold=0.55)

        assert len(markers) >= 1
        marker = markers[0]
        assert isinstance(marker, AudioSpliceMarker)
        # Boundary occurs around 1.0s
        assert 0.90 <= marker.timestamp_seconds <= 1.10
        assert 0.55 <= marker.score <= 1.0
        assert "discontinuity" in marker.reason.lower() or "transition" in marker.reason.lower()

    def test_short_audio_returns_empty_markers(self):
        sr = 16000
        short = (0.5 * np.sin(2 * np.pi * 300.0 * np.linspace(0, 0.2, int(sr * 0.2)))).astype(np.float32)
        feat = extract_acoustic_features(short, sr=sr)
        phase = analyze_phase_and_spectral_forensics(short, sr=sr)
        markers = detect_audio_splices(feat, phase)

        assert markers == []
