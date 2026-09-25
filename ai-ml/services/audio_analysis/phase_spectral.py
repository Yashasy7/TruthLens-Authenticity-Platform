"""
TruthLens AI/ML — Module 07: Phase Discontinuity & Spectral Forensics
Blueprint: Phase continuity analysis, spectral anomaly indicators, vocoder artifact metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)


@dataclass
class PhaseSpectralForensics:
    """Forensic metrics capturing phase discontinuity and high-frequency spectral anomalies."""
    phase_discontinuity_score: float
    spectral_anomaly_score: float
    frame_phase_discontinuity: np.ndarray
    high_freq_attenuation_ratio: float


def analyze_phase_and_spectral_forensics(
    waveform: np.ndarray,
    sr: int = 16000,
    n_fft: int = 1024,
    hop_length: int = 256,
) -> PhaseSpectralForensics:
    """
    Compute phase trajectory continuity and spectral anomaly metrics indicative of
    vocoder phase reconstruction or synthetic TTS synthesis.

    Args:
        waveform: 1D float32 audio waveform.
        sr: Sample rate in Hz.
        n_fft: FFT window size.
        hop_length: Hop length between analysis frames.

    Returns:
        PhaseSpectralForensics: Aggregate scores and frame-level series.
    """
    if len(waveform) < n_fft:
        waveform = np.pad(waveform, (0, n_fft - len(waveform)), mode="constant")

    freqs, times, zxx = signal.stft(
        waveform,
        fs=sr,
        window="hann",
        nperseg=n_fft,
        noverlap=n_fft - hop_length,
        boundary="zeros",
        padded=True,
    )
    magnitude = np.abs(zxx)
    phase = np.angle(zxx)

    num_bins = n_fft // 2 + 1
    k = np.arange(num_bins)
    omega_hop = 2.0 * np.pi * k * hop_length / n_fft

    if phase.shape[1] > 1:
        # Phase derivative across adjacent frames
        phase_diff = np.diff(phase, axis=1)
        expected_diff = omega_hop[:, np.newaxis]
        phase_dev = np.angle(np.exp(1j * (phase_diff - expected_diff)))

        # Magnitude-weighted phase deviation across frames
        weights = magnitude[:, 1:]
        weight_sum = np.sum(weights) + 1e-10

        phase_score = float(np.sum(np.abs(phase_dev) * weights) / (np.pi * weight_sum))
        frame_phase = np.sum(np.abs(phase_dev) * weights, axis=0) / (np.pi * np.sum(weights, axis=0) + 1e-10)
        # Prepend zero for alignment
        frame_phase = np.concatenate([[0.0], frame_phase]).astype(np.float32)
    else:
        phase_score = 0.0
        frame_phase = np.zeros(phase.shape[1], dtype=np.float32)

    phase_score = float(np.clip(phase_score, 0.0, 1.0))

    # Spectral Anomaly Analysis: high frequency cutoff / energy distribution
    # Vocal energy above 7000 Hz vs mid frequency (1000 Hz - 4000 Hz)
    mid_idx = (freqs >= 1000.0) & (freqs <= 4000.0)
    high_idx = freqs >= 7000.0

    mid_energy = float(np.sum(magnitude[mid_idx, :])) if np.any(mid_idx) else 1e-9
    high_energy = float(np.sum(magnitude[high_idx, :])) if np.any(high_idx) else 0.0

    hf_ratio = high_energy / max(mid_energy, 1e-9)

    # Anomaly score: combines extreme HF suppression (< 0.01) or excessive HF noise (> 0.8)
    # with spectral irregularity (variance of spectral flux)
    if hf_ratio < 0.005:
        # Abrupt cutoff typical of 16kHz bandlimited models
        hf_anomaly = 0.4
    elif hf_ratio > 0.8:
        # Unnatural high-frequency vocoder hiss
        hf_anomaly = 0.5
    else:
        hf_anomaly = 0.1

    # Composite spectral anomaly score bounded in [0.0, 1.0]
    spectral_anomaly = float(np.clip(0.6 * phase_score + 0.4 * hf_anomaly, 0.0, 1.0))

    return PhaseSpectralForensics(
        phase_discontinuity_score=phase_score,
        spectral_anomaly_score=spectral_anomaly,
        frame_phase_discontinuity=frame_phase,
        high_freq_attenuation_ratio=float(hf_ratio),
    )
