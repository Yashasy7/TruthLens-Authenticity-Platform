"""
TruthLens AI/ML — Module 07: Acoustic Pitch & Pitch Variance Forensics
Blueprint: F0 pitch tracking, pitch variance calculation, unvoiced/silence robustness.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PitchAnalysisResult:
    """Forensic pitch and fundamental frequency contour metrics."""
    pitch_mean: float
    pitch_variance: float
    voiced_fraction: float
    f0_contour: np.ndarray
    voiced_mask: np.ndarray
    time_axis: np.ndarray


def extract_pitch_contour(
    waveform: np.ndarray,
    sr: int = 16000,
    frame_length: int = 800,       # 50 ms window at 16 kHz
    hop_length: int = 256,         # 16 ms hop
    fmin: float = 60.0,            # Minimum speech F0 in Hz
    fmax: float = 500.0,           # Maximum speech F0 in Hz
    voicing_threshold: float = 0.35,
    energy_threshold: float = 1e-4,
) -> PitchAnalysisResult:
    """
    Extract fundamental frequency (F0) contour and pitch statistics via normalized
    autocorrelation analysis with sub-sample peak interpolation.

    Args:
        waveform: 1D float32 audio waveform.
        sr: Sample rate in Hz.
        frame_length: Analysis window in samples.
        hop_length: Step size between windows in samples.
        fmin: Minimum fundamental frequency search bound (Hz).
        fmax: Maximum fundamental frequency search bound (Hz).
        voicing_threshold: Minimum autocorrelation peak ratio for voiced decision.
        energy_threshold: Minimum frame RMS energy to be considered non-silent.

    Returns:
        PitchAnalysisResult: Mean F0, F0 variance, voiced ratio, and contour arrays.
    """
    if len(waveform) < frame_length:
        waveform = np.pad(waveform, (0, frame_length - len(waveform)), mode="constant")

    tau_min = max(1, int(sr / fmax))
    tau_max = max(tau_min + 1, int(sr / fmin))

    num_frames = 1 + (len(waveform) - frame_length) // hop_length
    f0_contour = np.zeros(num_frames, dtype=np.float32)
    voiced_mask = np.zeros(num_frames, dtype=bool)
    time_axis = (np.arange(num_frames) * hop_length + frame_length // 2) / sr

    for i in range(num_frames):
        start = i * hop_length
        end = start + frame_length
        frame = waveform[start:end]

        energy = float(np.mean(frame ** 2))
        if energy < energy_threshold:
            continue

        # Normalized autocorrelation
        corr = np.correlate(frame, frame, mode="full")
        center = len(corr) // 2
        lags = corr[center:]
        norm = lags[0]
        if norm <= 1e-9:
            continue

        norm_lags = lags / norm
        search_region = norm_lags[tau_min:tau_max + 1]
        if len(search_region) == 0:
            continue

        peak_idx = int(np.argmax(search_region))
        peak_val = float(search_region[peak_idx])
        best_tau = float(tau_min + peak_idx)

        if peak_val >= voicing_threshold and best_tau > 0:
            # Sub-sample parabolic interpolation around peak
            if 0 < peak_idx < len(search_region) - 1:
                alpha = float(search_region[peak_idx - 1])
                beta = peak_val
                gamma = float(search_region[peak_idx + 1])
                denom = 2.0 * (2.0 * beta - alpha - gamma)
                if abs(denom) > 1e-6:
                    delta = (alpha - gamma) / denom
                    best_tau = best_tau + delta

            f0 = sr / max(best_tau, 1.0)
            if fmin <= f0 <= fmax:
                f0_contour[i] = float(f0)
                voiced_mask[i] = True

    voiced_f0 = f0_contour[voiced_mask]
    voiced_fraction = float(len(voiced_f0) / num_frames) if num_frames > 0 else 0.0

    if len(voiced_f0) >= 2:
        pitch_mean = float(np.mean(voiced_f0))
        pitch_variance = float(np.var(voiced_f0))
    elif len(voiced_f0) == 1:
        pitch_mean = float(voiced_f0[0])
        pitch_variance = 0.0
    else:
        pitch_mean = 0.0
        pitch_variance = 0.0

    return PitchAnalysisResult(
        pitch_mean=pitch_mean,
        pitch_variance=pitch_variance,
        voiced_fraction=voiced_fraction,
        f0_contour=f0_contour,
        voiced_mask=voiced_mask,
        time_axis=time_axis,
    )
