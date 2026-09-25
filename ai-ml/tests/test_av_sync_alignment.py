"""
TruthLens AI/ML — Module 08: Alignment, Scoring & Mismatch Detection Unit Tests
"""

from __future__ import annotations

import numpy as np
import pytest

from services.av_sync.alignment import (
    compute_composite_sync_score,
    scan_mismatch_segments,
    compute_temporal_drift,
)
from schemas.av_sync import MismatchSegment


def test_composite_score_aligned():
    """Near-zero offset with positive correlation yields high sync score and ALIGNED status."""
    score, conf, status = compute_composite_sync_score(
        best_offset_ms=20.0,
        peak_correlation=0.85,
        syncnet_min_distance=0.65,
        syncnet_confidence=0.80,
        has_face=True,
        has_audio=True,
        has_mouth_movement=True,
        has_speech_audio=True,
    )
    assert score >= 0.70
    assert status == "ALIGNED"
    assert conf > 0.5


def test_composite_score_severe_desync():
    """Large offset (300 ms) yields low sync score and SEVERE_DESYNC status."""
    score, conf, status = compute_composite_sync_score(
        best_offset_ms=300.0,
        peak_correlation=0.20,
        syncnet_min_distance=1.35,
        syncnet_confidence=0.50,
        has_face=True,
        has_audio=True,
        has_mouth_movement=True,
        has_speech_audio=True,
    )
    assert score < 0.50
    assert status == "SEVERE_DESYNC"


def test_composite_score_missing_audio_or_face():
    """Missing audio or face results in 0.0 score and descriptive status."""
    score, conf, status = compute_composite_sync_score(
        best_offset_ms=0.0,
        peak_correlation=0.0,
        syncnet_min_distance=1.414,
        syncnet_confidence=0.0,
        has_face=True,
        has_audio=False,
        has_mouth_movement=True,
        has_speech_audio=False,
    )
    assert score == 0.0
    assert status == "NO_AUDIO_TRACK"

    score, conf, status = compute_composite_sync_score(
        best_offset_ms=0.0,
        peak_correlation=0.0,
        syncnet_min_distance=1.414,
        syncnet_confidence=0.0,
        has_face=False,
        has_audio=True,
        has_mouth_movement=False,
        has_speech_audio=True,
    )
    assert score == 0.0
    assert status == "NO_FACE_DETECTED"


def test_mismatch_scanner_detects_dubbing():
    """Scanner detects dubbing when speech audio is active but mouth is stationary."""
    fps = 25.0
    n = 100  # 4 seconds
    ts = np.arange(n, dtype=np.float32) / fps

    v_sig = np.zeros(n, dtype=np.float32)  # stationary mouth
    a_sig = np.full(n, 0.6, dtype=np.float32)  # active speech
    f_mask = [True] * n

    segments = scan_mismatch_segments(
        timestamps=ts,
        visual_signal=v_sig,
        audio_signal=a_sig,
        face_detected_mask=f_mask,
        window_duration=1.0,
        step_duration=0.5,
        fps=fps,
    )

    assert len(segments) > 0
    assert isinstance(segments[0], MismatchSegment)
    assert any("Dubbing" in s.description for s in segments)
    assert any(s.severity == "HIGH" for s in segments)


def test_mismatch_scanner_detects_muted_speech():
    """Scanner detects muted speech when mouth is moving actively but audio is silent."""
    fps = 25.0
    n = 100
    ts = np.arange(n, dtype=np.float32) / fps

    v_sig = np.full(n, 0.6, dtype=np.float32)  # active mouth
    a_sig = np.zeros(n, dtype=np.float32)  # silent audio
    f_mask = [True] * n

    segments = scan_mismatch_segments(
        timestamps=ts,
        visual_signal=v_sig,
        audio_signal=a_sig,
        face_detected_mask=f_mask,
        window_duration=1.0,
        step_duration=0.5,
        fps=fps,
    )

    assert len(segments) > 0
    assert any("Active lip movement" in s.description for s in segments)


def test_compute_temporal_drift():
    """Temporal drift measures offset variance across video quarters."""
    fps = 25.0
    n = 125  # 5 seconds
    ts = np.arange(n, dtype=np.float32) / fps

    # Aligned signals
    v_sig = np.sin(2 * np.pi * 1.5 * ts).astype(np.float32)
    a_sig = np.sin(2 * np.pi * 1.5 * ts).astype(np.float32)

    drift = compute_temporal_drift(ts, v_sig, a_sig, fps=fps)
    assert drift >= 0.0
    assert drift < 0.20
