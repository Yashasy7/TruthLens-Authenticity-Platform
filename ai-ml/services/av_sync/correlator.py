"""
TruthLens AI/ML — Module 08: Temporal Cross-Correlation & Audio Envelope
Blueprint: Temporal alignment between speech activity envelope and visual lip dynamics.
"""

from __future__ import annotations

import logging
from typing import Tuple, List, Optional
import numpy as np

from services.audio_analysis.features import compute_rms_energy, compute_spectral_flux, compute_stft

logger = logging.getLogger(__name__)


def compute_audio_envelope(
    waveform: np.ndarray,
    sr: int = 16000,
    hop_length: int = 256,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Derive an audio activity envelope representing continuous speech/acoustic energy.

    Combines frame-wise RMS energy with spectral flux (onset/syllable transitions)
    and applies a short smoothing window.

    Args:
        waveform: 1D normalized audio samples (-1.0 to 1.0).
        sr: Audio sample rate in Hz (default: 16000).
        hop_length: Hop length between analysis frames in samples.

    Returns:
        timestamps: 1D array of time positions in seconds.
        envelope: 1D array of normalized speech activity values in [0.0, 1.0].
    """
    if len(waveform) == 0:
        return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

    # Compute RMS energy (hop_length=256 at 16kHz -> ~62.5 Hz temporal resolution)
    rms = compute_rms_energy(waveform, frame_length=1024, hop_length=hop_length)
    
    # Compute STFT for spectral flux
    _, times, mag_spec, _ = compute_stft(waveform, sr=sr, n_fft=1024, hop_length=hop_length)
    flux = compute_spectral_flux(mag_spec)

    # Align lengths if needed
    min_len = min(len(rms), len(flux), len(times))
    if min_len == 0:
        return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

    rms = rms[:min_len]
    flux = flux[:min_len]
    times = times[:min_len]

    # Normalize components
    rms_max = np.max(rms) if np.max(rms) > 1e-6 else 1.0
    flux_max = np.max(flux) if np.max(flux) > 1e-6 else 1.0
    norm_rms = np.clip(rms / rms_max, 0.0, 1.0)
    norm_flux = np.clip(flux / flux_max, 0.0, 1.0)

    # Weighted combination: 70% energy, 30% onset spectral flux
    raw_env = 0.7 * norm_rms + 0.3 * norm_flux

    # Smooth with small 5-frame moving average (~80 ms window)
    kernel_size = 5
    if len(raw_env) >= kernel_size:
        kernel = np.ones(kernel_size) / kernel_size
        envelope = np.convolve(raw_env, kernel, mode="same")
    else:
        envelope = raw_env

    # Clip to [0.0, 1.0]
    envelope = np.clip(envelope, 0.0, 1.0).astype(np.float32)
    return times.astype(np.float32), envelope


def resample_to_video_timeline(
    source_times: np.ndarray,
    source_values: np.ndarray,
    target_times: np.ndarray,
) -> np.ndarray:
    """
    Interpolate a 1D signal onto target video frame timestamps using piecewise linear interpolation.

    Args:
        source_times: Timestamps of the source signal.
        source_values: Values of the source signal.
        target_times: Timestamps of the target video frames.

    Returns:
        np.ndarray: Resampled values matching len(target_times).
    """
    if len(target_times) == 0:
        return np.array([], dtype=np.float32)
    if len(source_times) == 0 or len(source_values) == 0:
        return np.zeros(len(target_times), dtype=np.float32)

    # Use np.interp with edge clamping
    resampled = np.interp(target_times, source_times, source_values, left=0.0, right=0.0)
    return resampled.astype(np.float32)


def compute_cross_correlation(
    audio_signal: np.ndarray,
    visual_signal: np.ndarray,
    fps: float = 25.0,
    max_offset_ms: float = 500.0,
) -> Tuple[float, float, float, np.ndarray, np.ndarray]:
    """
    Compute normalized cross-correlation between audio activity and visual lip activity.

    Conventions:
        Offset is defined as (audio_time - video_time):
        - Positive (+ms): Audio lags video (speech heard after mouth moves).
        - Negative (-ms): Audio leads video (speech heard before mouth moves).
        - ~0 ms: Synchronized.

    Args:
        audio_signal: 1D array of audio envelope sampled at `fps`.
        visual_signal: 1D array of visual lip activity sampled at `fps`.
        fps: Sampling rate of both signals (frames per second).
        max_offset_ms: Maximum lag search range in milliseconds.

    Returns:
        Tuple of:
            best_offset_ms: Estimated alignment offset in milliseconds.
            peak_correlation: Maximum normalized correlation coefficient [-1.0, 1.0].
            confidence: Reliability of the estimate in [0.0, 1.0].
            lags_ms: 1D array of evaluated lag offsets in milliseconds.
            correlations: 1D array of normalized correlation values for each lag.
    """
    n_frames = min(len(audio_signal), len(visual_signal))
    if n_frames < 5:
        # Insufficient data
        return 0.0, 0.0, 0.0, np.array([0.0], dtype=np.float32), np.array([0.0], dtype=np.float32)

    a = audio_signal[:n_frames].astype(np.float64)
    v = visual_signal[:n_frames].astype(np.float64)

    # Check signal variations
    std_a = np.std(a)
    std_v = np.std(v)

    if std_a < 1e-4 or std_v < 1e-4:
        # Either silent audio or completely still face
        return 0.0, 0.0, 0.0, np.array([0.0], dtype=np.float32), np.array([0.0], dtype=np.float32)

    # Standardize signals
    a_norm = (a - np.mean(a)) / std_a
    v_norm = (v - np.mean(v)) / std_v

    # Max lag in frames
    frame_duration_ms = 1000.0 / fps
    max_lag_frames = int(np.round(max_offset_ms / frame_duration_ms))
    max_lag_frames = min(max_lag_frames, n_frames // 2)

    if max_lag_frames < 1:
        return 0.0, float(np.corrcoef(a_norm, v_norm)[0, 1]), 0.5, np.array([0.0], dtype=np.float32), np.array([1.0], dtype=np.float32)

    lags = np.arange(-max_lag_frames, max_lag_frames + 1)
    correlations = []

    # For lag k:
    # If audio is delayed by k frames relative to video:
    # a[t] corresponds to v[t - k], or a[t + k] corresponds to v[t].
    # In time: offset_ms = k * frame_duration_ms.
    # Positive offset means audio occurs after video.
    for k in lags:
        if k < 0:
            # Audio leads video (k frames earlier)
            # audio[-k:] pairs with video[:n+k]
            a_slice = a_norm[-k:]
            v_slice = v_norm[: len(a_slice)]
        elif k > 0:
            # Audio lags video (k frames later)
            # audio[:n-k] pairs with video[k:]
            a_slice = a_norm[: n_frames - k]
            v_slice = v_norm[k : k + len(a_slice)]
        else:
            a_slice = a_norm
            v_slice = v_norm

        if len(a_slice) > 2:
            r = np.mean(a_slice * v_slice)
            correlations.append(float(r))
        else:
            correlations.append(0.0)

    corr_array = np.array(correlations, dtype=np.float32)
    # Lags in milliseconds:
    # When audio is delayed (audio lags video), slices align at k < 0, so offset = -k * frame_duration_ms > 0
    lags_ms = (-lags * frame_duration_ms).astype(np.float32)

    best_idx = int(np.argmax(corr_array))
    peak_corr = float(corr_array[best_idx])
    best_offset_ms = float(lags_ms[best_idx])

    # Calculate confidence based on peak height, peak-to-mean prominence, and signal energies
    mean_corr = float(np.mean(corr_array))
    prominence = max(0.0, peak_corr - mean_corr)
    energy_factor = float(np.clip(max(float(np.max(a)), float(np.max(v))), 0.1, 1.0))
    confidence = float(np.clip((prominence * 0.7 + max(0.0, peak_corr) * 0.3) * energy_factor, 0.0, 1.0))

    return round(best_offset_ms, 2), round(peak_corr, 4), round(confidence, 4), lags_ms, corr_array
