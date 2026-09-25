"""
TruthLens AI/ML — Module 08: Temporal Cross-Correlation & Audio Envelope Unit Tests
"""

from __future__ import annotations

import numpy as np
import pytest

from services.av_sync.correlator import (
    compute_audio_envelope,
    resample_to_video_timeline,
    compute_cross_correlation,
)


def test_compute_audio_envelope_with_synthetic_speech():
    """Verify audio envelope derivation from speech-like synthetic tone."""
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # 440 Hz tone modulated by 2 Hz envelope
    mod = 0.5 * (1.0 + np.sin(2 * np.pi * 2 * t))
    waveform = (mod * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    times, envelope = compute_audio_envelope(waveform, sr=sr, hop_length=256)

    assert len(times) == len(envelope)
    assert len(envelope) > 50
    assert np.all(envelope >= 0.0)
    assert np.all(envelope <= 1.0)
    assert float(np.max(envelope)) > 0.5


def test_compute_audio_envelope_empty():
    """Empty waveform produces empty envelope without errors."""
    times, env = compute_audio_envelope(np.array([], dtype=np.float32), sr=16000)
    assert len(times) == 0
    assert len(env) == 0


def test_resample_to_video_timeline():
    """Resampling interpolates envelope correctly onto target video timestamps."""
    source_t = np.array([0.0, 1.0, 2.0], dtype=np.float32)
    source_v = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    target_t = np.array([0.0, 0.5, 1.0, 1.5, 2.0], dtype=np.float32)
    res = resample_to_video_timeline(source_t, source_v, target_t)

    assert len(res) == 5
    assert np.isclose(res[0], 0.0)
    assert np.isclose(res[1], 0.5)
    assert np.isclose(res[2], 1.0)
    assert np.isclose(res[3], 0.5)
    assert np.isclose(res[4], 0.0)


def test_cross_correlation_synchronized_signals():
    """Synchronized Gaussian pulse events at t=1.0s should produce near-zero offset."""
    fps = 25.0
    t = np.arange(100, dtype=np.float32) / fps  # 4.0 seconds, 100 frames
    center_t = 1.5

    # Gaussian peak centered at 1.5s
    v_signal = np.exp(-((t - center_t) ** 2) / (2 * (0.15 ** 2)))
    a_signal = np.exp(-((t - center_t) ** 2) / (2 * (0.15 ** 2)))

    offset_ms, peak_corr, conf, lags, corrs = compute_cross_correlation(
        audio_signal=a_signal,
        visual_signal=v_signal,
        fps=fps,
        max_offset_ms=500.0,
    )

    assert abs(offset_ms) <= 40.0  # within 1 frame (40 ms)
    assert peak_corr > 0.90
    assert conf > 0.60


def test_cross_correlation_positive_offset():
    """Audio delayed by 200 ms (+5 frames at 25 fps) should produce positive offset ~200 ms."""
    fps = 25.0
    t = np.arange(125, dtype=np.float32) / fps  # 5.0 seconds
    v_center = 2.0
    a_center = 2.20  # +200 ms delayed

    v_signal = np.exp(-((t - v_center) ** 2) / (2 * (0.15 ** 2)))
    a_signal = np.exp(-((t - a_center) ** 2) / (2 * (0.15 ** 2)))

    offset_ms, peak_corr, conf, lags, corrs = compute_cross_correlation(
        audio_signal=a_signal,
        visual_signal=v_signal,
        fps=fps,
        max_offset_ms=500.0,
    )

    # Offset should be positive and approximately 200 ms
    assert 160.0 <= offset_ms <= 240.0
    assert peak_corr > 0.85


def test_cross_correlation_negative_offset():
    """Audio leading by 200 ms (-5 frames at 25 fps) should produce negative offset ~-200 ms."""
    fps = 25.0
    t = np.arange(125, dtype=np.float32) / fps  # 5.0 seconds
    v_center = 2.20
    a_center = 2.00  # -200 ms earlier

    v_signal = np.exp(-((t - v_center) ** 2) / (2 * (0.15 ** 2)))
    a_signal = np.exp(-((t - a_center) ** 2) / (2 * (0.15 ** 2)))

    offset_ms, peak_corr, conf, lags, corrs = compute_cross_correlation(
        audio_signal=a_signal,
        visual_signal=v_signal,
        fps=fps,
        max_offset_ms=500.0,
    )

    # Offset should be negative and approximately -200 ms
    assert -240.0 <= offset_ms <= -160.0
    assert peak_corr > 0.85


def test_cross_correlation_silent_signals():
    """Silent or static signals should return 0.0 offset and 0.0 confidence."""
    zeros = np.zeros(50, dtype=np.float32)
    offset_ms, peak_corr, conf, _, _ = compute_cross_correlation(
        audio_signal=zeros,
        visual_signal=zeros,
        fps=25.0,
    )
    assert offset_ms == 0.0
    assert peak_corr == 0.0
    assert conf == 0.0
