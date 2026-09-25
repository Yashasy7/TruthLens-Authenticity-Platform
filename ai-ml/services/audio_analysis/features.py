"""
TruthLens AI/ML — Module 07: Acoustic Feature Extraction & Mel-Spectrogram
Blueprint: Mel-spectrogram generator, acoustic feature extraction, Base64 PNG evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional, Tuple

import cv2
import numpy as np
from scipy import signal
from scipy.fft import dct

from utils.image_utils import encode_image_to_base64_png

logger = logging.getLogger(__name__)


@dataclass
class AcousticFeatures:
    """Full set of extracted acoustic and spectral features for forensic analysis."""
    duration_seconds: float
    time_axis: np.ndarray
    log_mel: np.ndarray
    mfcc: np.ndarray
    spectral_centroid: np.ndarray
    spectral_centroid_mean: float
    spectral_bandwidth: np.ndarray
    spectral_bandwidth_mean: float
    spectral_rolloff: np.ndarray
    spectral_rolloff_mean: float
    zero_crossing_rate: np.ndarray
    zero_crossing_rate_mean: float
    rms_energy: np.ndarray
    rms_energy_mean: float
    spectral_flux: np.ndarray
    spectral_flux_mean: float
    spectrogram_base64: str


def create_mel_filterbank(
    sr: int = 16000,
    n_fft: int = 1024,
    n_mels: int = 80,
    f_min: float = 0.0,
    f_max: Optional[float] = None,
) -> np.ndarray:
    """
    Construct a deterministic triangular Mel-filterbank matrix.

    Args:
        sr: Sample rate in Hz.
        n_fft: FFT window length.
        n_mels: Number of Mel frequency bands.
        f_min: Minimum frequency in Hz (default: 0.0).
        f_max: Maximum frequency in Hz (default: sr / 2).

    Returns:
        np.ndarray: Filterbank weights of shape (n_mels, n_fft // 2 + 1).
    """
    if f_max is None:
        f_max = float(sr) / 2.0

    # Linear to Mel conversion
    m_min = 2595.0 * np.log10(1.0 + f_min / 700.0)
    m_max = 2595.0 * np.log10(1.0 + f_max / 700.0)

    # Equispaced points in Mel scale
    m_points = np.linspace(m_min, m_max, n_mels + 2)

    # Mel to Linear conversion
    f_points = 700.0 * (10.0 ** (m_points / 2595.0) - 1.0)

    # Map to FFT bin indices
    num_bins = n_fft // 2 + 1
    bin_indices = np.floor((n_fft + 1) * f_points / sr).astype(int)
    bin_indices = np.clip(bin_indices, 0, num_bins - 1)

    weights = np.zeros((n_mels, num_bins), dtype=np.float32)
    for m in range(1, n_mels + 1):
        f_m_minus = bin_indices[m - 1]
        f_m = bin_indices[m]
        f_m_plus = bin_indices[m + 1]

        if f_m > f_m_minus:
            for k in range(f_m_minus, f_m):
                weights[m - 1, k] = (k - f_m_minus) / (f_m - f_m_minus)
        if f_m_plus > f_m:
            for k in range(f_m, f_m_plus):
                weights[m - 1, k] = (f_m_plus - k) / (f_m_plus - f_m)

    return weights


def compute_stft(
    waveform: np.ndarray,
    sr: int = 16000,
    n_fft: int = 1024,
    hop_length: int = 256,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute Short-Time Fourier Transform (STFT) of 1D waveform.

    Returns:
        frequencies: 1D array of frequency bins.
        time_axis: 1D array of frame timestamps in seconds.
        magnitude: 2D magnitude spectrogram (freq_bins, time_frames).
        complex_zxx: 2D complex STFT representation.
    """
    if len(waveform) < n_fft:
        pad_len = n_fft - len(waveform)
        waveform = np.pad(waveform, (0, pad_len), mode="constant")

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
    return freqs, times, magnitude, zxx


def compute_mel_spectrogram(
    waveform: np.ndarray,
    sr: int = 16000,
    n_fft: int = 1024,
    hop_length: int = 256,
    n_mels: int = 80,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute power and log-scaled Mel-spectrogram.

    Returns:
        log_mel: (n_mels, time_frames) in dB scale.
        mel_spec: (n_mels, time_frames) power spectrum.
        mag_spec: (freq_bins, time_frames) linear magnitude STFT.
        times: 1D array of frame timestamps.
    """
    freqs, times, mag_spec, _ = compute_stft(waveform, sr=sr, n_fft=n_fft, hop_length=hop_length)
    fb = create_mel_filterbank(sr=sr, n_fft=n_fft, n_mels=n_mels)
    power_spec = mag_spec ** 2
    mel_spec = np.dot(fb, power_spec)

    # 10 * log10(power) bounded at -100 dB
    log_mel = 10.0 * np.log10(np.maximum(mel_spec, 1e-10))
    return log_mel, mel_spec, mag_spec, times


def compute_mfcc(
    log_mel: np.ndarray,
    n_mfcc: int = 20,
) -> np.ndarray:
    """
    Extract Mel-Frequency Cepstral Coefficients (MFCCs) using Type-II DCT.

    Args:
        log_mel: (n_mels, time_frames) log Mel filterbank energies.
        n_mfcc: Number of cepstral coefficients to retain.

    Returns:
        np.ndarray: (n_mfcc, time_frames) MFCC feature matrix.
    """
    # Orthonormal DCT-II along mel frequency dimension
    full_mfcc = dct(log_mel, type=2, axis=0, norm="ortho")
    return full_mfcc[:n_mfcc, :]


def compute_spectral_centroid(
    magnitude_spec: np.ndarray,
    sr: int = 16000,
    n_fft: int = 1024,
) -> np.ndarray:
    """
    Compute spectral centroid (center of mass of the frequency spectrum) per frame.
    """
    freqs = np.linspace(0, sr / 2.0, n_fft // 2 + 1)
    norm = np.sum(magnitude_spec, axis=0) + 1e-10
    centroid = np.sum(freqs[:, np.newaxis] * magnitude_spec, axis=0) / norm
    return centroid.astype(np.float32)


def compute_spectral_bandwidth(
    magnitude_spec: np.ndarray,
    centroid: np.ndarray,
    sr: int = 16000,
    n_fft: int = 1024,
) -> np.ndarray:
    """
    Compute spectral bandwidth (2nd central moment) per frame.
    """
    freqs = np.linspace(0, sr / 2.0, n_fft // 2 + 1)
    norm = np.sum(magnitude_spec, axis=0) + 1e-10
    dev = freqs[:, np.newaxis] - centroid[np.newaxis, :]
    variance = np.sum((dev ** 2) * magnitude_spec, axis=0) / norm
    bandwidth = np.sqrt(np.maximum(variance, 0.0))
    return bandwidth.astype(np.float32)


def compute_spectral_rolloff(
    magnitude_spec: np.ndarray,
    roll_percent: float = 0.85,
    sr: int = 16000,
    n_fft: int = 1024,
) -> np.ndarray:
    """
    Compute spectral roll-off frequency: the frequency below which roll_percent
    (default 85%) of total spectral energy is contained.
    """
    freqs = np.linspace(0, sr / 2.0, n_fft // 2 + 1)
    cumulative_energy = np.cumsum(magnitude_spec, axis=0)
    total_energy = cumulative_energy[-1, :]
    threshold = roll_percent * total_energy

    rolloff = np.zeros(magnitude_spec.shape[1], dtype=np.float32)
    for t in range(magnitude_spec.shape[1]):
        if total_energy[t] <= 1e-9:
            rolloff[t] = 0.0
            continue
        idx = np.searchsorted(cumulative_energy[:, t], threshold[t])
        idx = min(idx, len(freqs) - 1)
        rolloff[t] = freqs[idx]

    return rolloff


def compute_zero_crossing_rate(
    waveform: np.ndarray,
    frame_length: int = 1024,
    hop_length: int = 256,
) -> np.ndarray:
    """
    Compute frame-wise Zero-Crossing Rate (ZCR) across time domain signal.
    """
    if len(waveform) < frame_length:
        waveform = np.pad(waveform, (0, frame_length - len(waveform)), mode="constant")

    num_frames = 1 + (len(waveform) - frame_length) // hop_length
    zcr = np.zeros(num_frames, dtype=np.float32)

    for i in range(num_frames):
        start = i * hop_length
        end = start + frame_length
        frame = waveform[start:end]
        sign_diff = np.abs(np.diff(np.signbit(frame).astype(int)))
        zcr[i] = np.mean(sign_diff)

    return zcr


def compute_rms_energy(
    waveform: np.ndarray,
    frame_length: int = 1024,
    hop_length: int = 256,
) -> np.ndarray:
    """
    Compute frame-wise Root Mean Square (RMS) energy.
    """
    if len(waveform) < frame_length:
        waveform = np.pad(waveform, (0, frame_length - len(waveform)), mode="constant")

    num_frames = 1 + (len(waveform) - frame_length) // hop_length
    rms = np.zeros(num_frames, dtype=np.float32)

    for i in range(num_frames):
        start = i * hop_length
        end = start + frame_length
        frame = waveform[start:end]
        rms[i] = np.sqrt(np.mean(frame ** 2) + 1e-10)

    return rms


def compute_spectral_flux(
    magnitude_spec: np.ndarray,
) -> np.ndarray:
    """
    Compute spectral flux (Euclidean rate of change between adjacent spectral frames).
    """
    norm_spec = magnitude_spec / (np.linalg.norm(magnitude_spec, axis=0, keepdims=True) + 1e-10)
    diff = np.diff(norm_spec, axis=1)
    flux = np.sqrt(np.sum(diff ** 2, axis=0))
    # Prepend zero for frame alignment
    flux = np.concatenate([[0.0], flux]).astype(np.float32)
    return flux


def render_mel_spectrogram_base64(
    log_mel: np.ndarray,
    colormap: int = cv2.COLORMAP_VIRIDIS,
) -> str:
    """
    Render a 2D log-Mel spectrogram array to a colormapped PNG image and encode to Base64.
    Flipped vertically so lowest frequency band (0 Hz) is at the bottom.

    Args:
        log_mel: 2D array of shape (n_mels, time_frames).
        colormap: OpenCV colormap constant (default: COLORMAP_VIRIDIS).

    Returns:
        str: Base64-encoded PNG image string.
    """
    # Normalize dB scale (-80 to 0 typical) to [0, 255] uint8
    norm = cv2.normalize(log_mel, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    # Spectrogram convention: low frequencies at bottom
    norm_flipped = np.flipud(norm)

    # Colormap RGB/BGR
    colored_bgr = cv2.applyColorMap(norm_flipped, colormap)

    # Encode using existing TruthLens image_utils Base64 utility
    return encode_image_to_base64_png(colored_bgr, is_bgr=True)


def extract_acoustic_features(
    waveform: np.ndarray,
    sr: int = 16000,
    n_fft: int = 1024,
    hop_length: int = 256,
    n_mels: int = 80,
    n_mfcc: int = 20,
) -> AcousticFeatures:
    """
    Extract comprehensive acoustic and spectral feature set from a waveform.

    Args:
        waveform: 1D float32 audio waveform.
        sr: Sample rate in Hz.
        n_fft: FFT window size.
        hop_length: STFT hop length.
        n_mels: Mel frequency bins.
        n_mfcc: Number of MFCC coefficients.

    Returns:
        AcousticFeatures dataclass containing arrays, scalars, and Base64 evidence.
    """
    duration = float(len(waveform) / sr)

    log_mel, mel_spec, mag_spec, times = compute_mel_spectrogram(
        waveform, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=n_mels
    )

    mfcc = compute_mfcc(log_mel, n_mfcc=n_mfcc)
    centroid = compute_spectral_centroid(mag_spec, sr=sr, n_fft=n_fft)
    bandwidth = compute_spectral_bandwidth(mag_spec, centroid, sr=sr, n_fft=n_fft)
    rolloff = compute_spectral_rolloff(mag_spec, roll_percent=0.85, sr=sr, n_fft=n_fft)
    zcr = compute_zero_crossing_rate(waveform, frame_length=n_fft, hop_length=hop_length)
    rms = compute_rms_energy(waveform, frame_length=n_fft, hop_length=hop_length)
    flux = compute_spectral_flux(mag_spec)

    spectrogram_b64 = render_mel_spectrogram_base64(log_mel)

    return AcousticFeatures(
        duration_seconds=duration,
        time_axis=times,
        log_mel=log_mel,
        mfcc=mfcc,
        spectral_centroid=centroid,
        spectral_centroid_mean=float(np.mean(centroid)) if len(centroid) > 0 else 0.0,
        spectral_bandwidth=bandwidth,
        spectral_bandwidth_mean=float(np.mean(bandwidth)) if len(bandwidth) > 0 else 0.0,
        spectral_rolloff=rolloff,
        spectral_rolloff_mean=float(np.mean(rolloff)) if len(rolloff) > 0 else 0.0,
        zero_crossing_rate=zcr,
        zero_crossing_rate_mean=float(np.mean(zcr)) if len(zcr) > 0 else 0.0,
        rms_energy=rms,
        rms_energy_mean=float(np.mean(rms)) if len(rms) > 0 else 0.0,
        spectral_flux=flux,
        spectral_flux_mean=float(np.mean(flux)) if len(flux) > 0 else 0.0,
        spectrogram_base64=spectrogram_b64,
    )
