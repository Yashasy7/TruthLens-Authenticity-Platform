"""
TruthLens AI/ML — Module 07: Temporal Window Audio Evaluation
Blueprint: Slide deterministic 64,600-sample windows (~4.0375s @ 16kHz) across raw mono waveforms
           for AASIST-L inference, preserving temporal boundary sensitivity.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional

import numpy as np

from services.audio_analysis.model import (
    AASIST_L_INPUT_SAMPLES,
    AASISTLClassifier,
    pad_or_crop_waveform,
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
    window_duration: float = 4.0375,
    hop_duration: float = 2.0,
    model: Optional[AASISTLClassifier] = None,
) -> TemporalAnalysisResult:
    """
    Evaluate raw 16 kHz mono waveforms with AASIST-L using deterministic framing:
      - If waveform length <= 64,600 samples (~4.0375s): pad/tile deterministically to 64,600
        matching clovaai/aasist evaluation protocol (single window).
      - If waveform length > 64,600 samples: slide fixed 64,600-sample windows and aggregate.
    """
    total_samples = len(waveform)
    duration_seconds = total_samples / sr
    window_samples = max(AASIST_L_INPUT_SAMPLES, int(round(window_duration * sr)))
    hop_samples = max(1, int(round(hop_duration * sr)))

    windows: List[WindowEvaluation] = []

    if total_samples <= window_samples:
        framed = pad_or_crop_waveform(waveform, AASIST_L_INPUT_SAMPLES)
        prob = predict_synthetic_voice_probability(framed, model=model)
        windows.append(
            WindowEvaluation(
                window_index=0,
                start_seconds=0.0,
                end_seconds=round(duration_seconds, 3),
                synthetic_prob=round(prob, 4),
            )
        )
    else:
        win_idx = 0
        for start_idx in range(0, total_samples, hop_samples):
            end_idx = min(start_idx + AASIST_L_INPUT_SAMPLES, total_samples)
            chunk = waveform[start_idx:end_idx]
            framed = pad_or_crop_waveform(chunk, AASIST_L_INPUT_SAMPLES)
            prob = predict_synthetic_voice_probability(framed, model=model)

            windows.append(
                WindowEvaluation(
                    window_index=win_idx,
                    start_seconds=round(start_idx / sr, 3),
                    end_seconds=round(end_idx / sr, 3),
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
        p85 = float(np.percentile(scores, 85))
        mean_val = float(np.mean(scores))
        aggregate_prob = float(np.clip(0.70 * p85 + 0.30 * mean_val, 0.0, 1.0))

    max_prob = float(max(scores)) if scores else 0.0
    mean_prob = float(np.mean(scores)) if scores else 0.0

    details: Dict[str, Any] = {
        "window_count": len(windows),
        "window_samples": AASIST_L_INPUT_SAMPLES,
        "window_duration_seconds": round(AASIST_L_INPUT_SAMPLES / sr, 4),
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
