"""
TruthLens AI/ML — Module 07: Temporal Window Audio Evaluation
Blueprint: Slide fixed-duration windows across audio track, evaluate localized voice cloning, aggregate evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config.settings import settings
from services.audio_analysis.features import compute_mel_spectrogram
from services.audio_analysis.model import (
    AASISTAudioClassifier,
    format_log_mel_tensor,
    predict_synthetic_voice_probability,
)

logger = logging.getLogger(__name__)


@dataclass
class WindowEvaluation:
    """Evaluation result for an individual temporal audio window."""
    window_index: int
    start_seconds: float
    end_seconds: float
    synthetic_prob: float


@dataclass
class TemporalAnalysisResult:
    """Aggregate result from temporal windowed evaluation."""
    aggregate_synthetic_prob: float
    windows: List[WindowEvaluation]
    max_prob: float
    mean_prob: float
    details: Dict[str, Any]


def evaluate_temporal_audio_windows(
    waveform: np.ndarray,
    sr: int = 16000,
    window_duration: float = 2.0,
    hop_duration: float = 1.0,
    model: Optional[AASISTAudioClassifier] = None,
) -> TemporalAnalysisResult:
    """
    Split audio waveform into overlapping temporal windows, classify each segment,
    and compute an aggregate voice cloning probability resilient to localized audio splicing.

    Args:
        waveform: 1D float32 audio waveform.
        sr: Sample rate in Hz.
        window_duration: Window length in seconds (default: 2.0s).
        hop_duration: Hop step between windows in seconds (default: 1.0s).
        model: Optional pre-loaded classifier model instance.

    Returns:
        TemporalAnalysisResult: Window breakdown, summary statistics, and aggregated probability.
    """
    total_samples = len(waveform)
    duration_seconds = total_samples / sr
    window_samples = int(round(window_duration * sr))
    hop_samples = int(round(hop_duration * sr))

    windows: List[WindowEvaluation] = []

    # If audio is shorter than window_samples, evaluate as a single window with padding
    if total_samples <= window_samples:
        log_mel, _, _, _ = compute_mel_spectrogram(
            waveform,
            sr=sr,
            n_mels=settings.audio_n_mels,
            n_fft=settings.audio_n_fft,
            hop_length=settings.audio_hop_length,
        )
        tensor = format_log_mel_tensor(log_mel)
        prob = predict_synthetic_voice_probability(tensor, model=model)
        win = WindowEvaluation(
            window_index=0,
            start_seconds=0.0,
            end_seconds=round(duration_seconds, 3),
            synthetic_prob=round(prob, 4),
        )
        windows.append(win)
    else:
        win_idx = 0
        for start_idx in range(0, total_samples - window_samples // 2, hop_samples):
            end_idx = min(start_idx + window_samples, total_samples)
            chunk = waveform[start_idx:end_idx]

            log_mel, _, _, _ = compute_mel_spectrogram(
                chunk,
                sr=sr,
                n_mels=settings.audio_n_mels,
                n_fft=settings.audio_n_fft,
                hop_length=settings.audio_hop_length,
            )
            tensor = format_log_mel_tensor(log_mel)
            prob = predict_synthetic_voice_probability(tensor, model=model)

            t_start = round(start_idx / sr, 3)
            t_end = round(end_idx / sr, 3)
            windows.append(
                WindowEvaluation(
                    window_index=win_idx,
                    start_seconds=t_start,
                    end_seconds=t_end,
                    synthetic_prob=round(prob, 4),
                )
            )
            win_idx += 1

            if end_idx >= total_samples:
                break

    scores = [w.synthetic_prob for w in windows]
    if len(scores) == 1:
        aggregate_prob = float(scores[0])
    else:
        # 85th percentile captures localized synthetic voice insertion without being skewed by a single outlier
        p85 = float(np.percentile(scores, 85))
        mean_val = float(np.mean(scores))
        aggregate_prob = float(np.clip(0.70 * p85 + 0.30 * mean_val, 0.0, 1.0))

    max_prob = float(max(scores)) if scores else 0.0
    mean_prob = float(np.mean(scores)) if scores else 0.0

    details: Dict[str, Any] = {
        "window_count": len(windows),
        "window_duration_seconds": window_duration,
        "hop_duration_seconds": hop_duration,
        "max_window_synthetic_prob": round(max_prob, 4),
        "mean_window_synthetic_prob": round(mean_prob, 4),
        "window_timeline": [
            {
                "window": w.window_index,
                "start": w.start_seconds,
                "end": w.end_seconds,
                "prob": w.synthetic_prob,
            }
            for w in windows
        ],
    }

    return TemporalAnalysisResult(
        aggregate_synthetic_prob=round(aggregate_prob, 4),
        windows=windows,
        max_prob=round(max_prob, 4),
        mean_prob=round(mean_prob, 4),
        details=details,
    )
