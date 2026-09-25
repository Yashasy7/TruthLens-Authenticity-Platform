"""
TruthLens AI/ML — Module 07: Audio Splice Boundary Detection
Blueprint: Detect audio splicing boundaries, joint acoustic discontinuity analysis, timestamp markers.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
from scipy import signal

from schemas.audio_analysis import AudioSpliceMarker
from services.audio_analysis.features import AcousticFeatures
from services.audio_analysis.phase_spectral import PhaseSpectralForensics

logger = logging.getLogger(__name__)


def detect_audio_splices(
    acoustic_features: AcousticFeatures,
    phase_forensics: PhaseSpectralForensics,
    threshold: float = 0.55,
    min_interval_seconds: float = 0.35,
    edge_margin_seconds: float = 0.15,
) -> List[AudioSpliceMarker]:
    """
    Detect suspicious audio splicing points by analyzing joint discontinuities
    in RMS energy flux, spectral flux, and phase trajectory deviations.

    Args:
        acoustic_features: Extracted acoustic features for the full audio track.
        phase_forensics: Phase discontinuity telemetry.
        threshold: Anomaly score threshold [0.0, 1.0] for flagging splice markers.
        min_interval_seconds: Minimum temporal separation between detected splice markers.
        edge_margin_seconds: Temporal margin at track start/end to suppress edge transients.

    Returns:
        List[AudioSpliceMarker]: Timestamped splice boundary events.
    """
    duration = acoustic_features.duration_seconds
    if duration < (2.0 * edge_margin_seconds + 0.1):
        # Audio too short to reliably identify internal splice boundaries
        return []

    min_len = min(
        len(acoustic_features.rms_energy),
        len(acoustic_features.spectral_flux),
        len(phase_forensics.frame_phase_discontinuity),
        len(acoustic_features.time_axis),
    )

    if min_len < 4:
        return []

    rms = acoustic_features.rms_energy[:min_len]
    flux = acoustic_features.spectral_flux[:min_len]
    phase = phase_forensics.frame_phase_discontinuity[:min_len]
    times = acoustic_features.time_axis[:min_len]

    # Relative RMS step discontinuity: |dRMS| / RMS
    rms_diff = np.abs(np.diff(rms, prepend=rms[0])) / (rms + 1e-4)
    # Gate out subtle natural speech/tone fluctuations (below 0.12 relative step)
    rms_diff_gated = np.where(rms_diff >= 0.12, rms_diff, 0.0)
    max_rms_diff = float(np.max(rms_diff_gated)) if len(rms_diff_gated) > 0 else 0.0
    norm_rms = np.clip(rms_diff_gated / (max_rms_diff + 1e-6), 0.0, 1.0) if max_rms_diff > 0.0 else np.zeros_like(rms_diff)

    # Spectral flux normalization (gate out subtle steady-state variations below 0.10)
    flux_gated = np.where(flux >= 0.10, flux, 0.0)
    max_flux = float(np.max(flux_gated)) if len(flux_gated) > 0 else 0.0
    norm_flux = np.clip(flux_gated / (max_flux + 1e-6), 0.0, 1.0) if max_flux > 0.0 else np.zeros_like(flux)

    # Composite discontinuity anomaly score [0.0, 1.0]
    # Emphasize true joint boundary events where both energy or spectral flux jump abruptly
    composite_score = 0.50 * norm_rms + 0.35 * norm_flux + 0.15 * phase

    # Suppress startup/tail boundary padding transients
    margin_mask = (times >= edge_margin_seconds) & (times <= (duration - edge_margin_seconds))
    composite_score = np.where(margin_mask, composite_score, 0.0)

    # Determine frame distance corresponding to min_interval_seconds
    dt = float(np.median(np.diff(times))) if len(times) > 1 else 0.016
    distance_frames = max(1, int(round(min_interval_seconds / max(dt, 1e-4))))

    peaks, _ = signal.find_peaks(
        composite_score,
        height=threshold,
        distance=distance_frames,
    )

    markers: List[AudioSpliceMarker] = []
    for peak_idx in peaks:
        ts = round(float(times[peak_idx]), 3)
        score_val = round(float(np.clip(composite_score[peak_idx], 0.0, 1.0)), 4)
        markers.append(
            AudioSpliceMarker(
                timestamp_seconds=ts,
                score=score_val,
                reason=(
                    f"Abrupt acoustic transition at {ts:.2f}s "
                    f"(score: {score_val:.2f}) with joint spectral flux and phase discontinuity."
                ),
            )
        )

    logger.debug("Splice detection found %d boundary markers (threshold=%.2f)", len(markers), threshold)
    return markers
