"""
TruthLens AI/ML — Module 08: Audio-Visual Alignment, Scoring & Mismatch Detection
Blueprint: Forensic composite synchronization analysis, temporal drift estimation, and localized mismatch segment scanner.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from schemas.av_sync import MismatchSegment

logger = logging.getLogger(__name__)


def compute_composite_sync_score(
    best_offset_ms: float,
    peak_correlation: float,
    syncnet_min_distance: float,
    syncnet_confidence: float,
    has_face: bool,
    has_audio: bool,
    has_mouth_movement: bool,
    has_speech_audio: bool,
) -> Tuple[float, float, str]:
    """
    Compute overall composite synchronization score, confidence, and categorical sync status.

    Scoring convention:
        1.0 = perfectly synchronized
        0.0 = completely desynchronized / manipulated / no speech

    Status categories:
        - "ALIGNED" (|offset| <= 80 ms, good correlation)
        - "SLIGHT_DESYNC" (80 ms < |offset| <= 160 ms)
        - "SEVERE_DESYNC" (|offset| > 160 ms or negative correlation)
        - "NO_FACE_DETECTED"
        - "NO_AUDIO_TRACK"
        - "SILENT_OR_INACTIVE"

    Returns:
        sync_score: Float in [0.0, 1.0].
        confidence: Float in [0.0, 1.0].
        sync_status: Categorical status string.
    """
    if not has_audio:
        return 0.0, 1.0, "NO_AUDIO_TRACK"
    if not has_face:
        return 0.0, 0.9, "NO_FACE_DETECTED"
    if not has_mouth_movement and not has_speech_audio:
        return 0.5, 0.5, "SILENT_OR_INACTIVE"

    abs_offset = abs(best_offset_ms)

    # Offset penalty: 0 penalty under 60 ms, scales to 1.0 at 400 ms
    offset_penalty = float(np.clip((abs_offset - 60.0) / 340.0, 0.0, 1.0))

    # Correlation factor: maps [-0.2, 0.8] to [0.0, 1.0]
    corr_factor = float(np.clip((peak_correlation + 0.2) / 1.0, 0.0, 1.0))

    # SyncNet distance factor: distance in [0.0, 2.0], ideal < 0.8
    dist_factor = float(np.clip((1.4 - syncnet_min_distance) / 0.8, 0.0, 1.0))

    # Composite base score: 50% offset penalty, 30% correlation, 20% syncnet metric
    sync_score = (1.0 - 0.5 * offset_penalty) * (0.3 + 0.45 * corr_factor + 0.25 * dist_factor)
    sync_score = float(np.clip(sync_score, 0.0, 1.0))

    # Overall confidence
    confidence = float(np.clip(0.5 * corr_factor + 0.3 * syncnet_confidence + 0.2, 0.1, 1.0))

    # Determine status
    if abs_offset <= 80.0 and sync_score >= 0.70:
        sync_status = "ALIGNED"
    elif abs_offset <= 160.0 and sync_score >= 0.45:
        sync_status = "SLIGHT_DESYNC"
    else:
        sync_status = "SEVERE_DESYNC"

    return round(sync_score, 4), round(confidence, 4), sync_status


def scan_mismatch_segments(
    timestamps: np.ndarray,
    visual_signal: np.ndarray,
    audio_signal: np.ndarray,
    face_detected_mask: List[bool],
    window_duration: float = 1.0,
    step_duration: float = 0.5,
    fps: float = 25.0,
) -> List[MismatchSegment]:
    """
    Sliding window scanner identifying localized temporal anomalies and synchronization mismatches.

    Detects:
        - DESYNC: Vocal activity present alongside mouth movement, but temporal offset exceeds threshold.
        - DUBBING_SUSPECTED: Active speech audio while mouth is static/closed.
        - MUTED_SPEECH: Active lip movement while speech audio is absent.
        - FACE_OCCLUSION: Face lost during active speech track.

    Args:
        timestamps: 1D array of frame timestamps in seconds.
        visual_signal: 1D array of lip motion activity values [0.0, 1.0].
        audio_signal: 1D array of speech acoustic envelope values [0.0, 1.0].
        face_detected_mask: Boolean mask indicating if primary face was detected per frame.
        window_duration: Sliding analysis window length in seconds (default: 1.0s).
        step_duration: Sliding window hop size in seconds (default: 0.5s).
        fps: Sampling rate (default: 25.0).

    Returns:
        List[MismatchSegment]: Detected and merged forensic anomaly intervals.
    """
    n_frames = min(len(timestamps), len(visual_signal), len(audio_signal), len(face_detected_mask))
    if n_frames < 5:
        return []

    t = timestamps[:n_frames]
    v = visual_signal[:n_frames]
    a = audio_signal[:n_frames]
    f_mask = face_detected_mask[:n_frames]

    total_duration = t[-1] - t[0] if len(t) > 1 else 0.0
    if total_duration < window_duration:
        window_duration = max(0.5, total_duration)
        step_duration = window_duration / 2.0

    window_frames = int(round(window_duration * fps))
    step_frames = max(1, int(round(step_duration * fps)))

    raw_segments: List[Dict[str, Any]] = []

    for start_idx in range(0, n_frames - window_frames + 1, step_frames):
        end_idx = start_idx + window_frames
        sub_t = t[start_idx:end_idx]
        sub_v = v[start_idx:end_idx]
        sub_a = a[start_idx:end_idx]
        sub_f = f_mask[start_idx:end_idx]

        t_start = round(float(sub_t[0]), 3)
        t_end = round(float(sub_t[-1]), 3)

        face_ratio = np.mean(sub_f)
        mean_v = float(np.mean(sub_v))
        mean_a = float(np.mean(sub_a))

        # 1. Face occlusion during active speech
        if face_ratio < 0.3 and mean_a > 0.25:
            raw_segments.append({
                "start": t_start,
                "end": t_end,
                "offset_ms": 0.0,
                "severity": "MEDIUM",
                "type": "FACE_OCCLUSION",
                "description": f"Face tracking lost during active speech at {t_start:.1f}s - {t_end:.1f}s",
            })
            continue

        # 2. Dubbing signature: strong acoustic energy with stationary mouth
        if mean_a > 0.30 and mean_v < 0.12 and face_ratio >= 0.7:
            raw_segments.append({
                "start": t_start,
                "end": t_end,
                "offset_ms": 0.0,
                "severity": "HIGH",
                "type": "DUBBING",
                "description": f"Dubbing signature: speech energy ({mean_a:.2f}) with closed/static mouth ({mean_v:.2f}) at {t_start:.1f}s - {t_end:.1f}s",
            })
            continue

        # 3. Muted speech: active mouth dynamics without acoustic speech
        if mean_v > 0.30 and mean_a < 0.08 and face_ratio >= 0.7:
            raw_segments.append({
                "start": t_start,
                "end": t_end,
                "offset_ms": 0.0,
                "severity": "MEDIUM",
                "type": "MUTED_SPEECH",
                "description": f"Active lip movement ({mean_v:.2f}) without speech audio at {t_start:.1f}s - {t_end:.1f}s",
            })
            continue

        # 4. Localized temporal desynchronization
        if mean_v > 0.15 and mean_a > 0.15 and face_ratio >= 0.7:
            # Measure local lag
            max_local_lag = min(window_frames // 3, 10)
            best_local_r = -1.0
            best_local_k = 0
            for k in range(-max_local_lag, max_local_lag + 1):
                if k < 0:
                    a_s = sub_a[-k:]
                    v_s = sub_v[: len(a_s)]
                elif k > 0:
                    a_s = sub_a[: len(sub_a) - k]
                    v_s = sub_v[k : k + len(a_s)]
                else:
                    a_s = sub_a
                    v_s = sub_v
                if len(a_s) > 2 and np.std(a_s) > 1e-4 and np.std(v_s) > 1e-4:
                    r = float(np.corrcoef(a_s, v_s)[0, 1])
                    if r > best_local_r:
                        best_local_r = r
                        best_local_k = k

            local_offset_ms = round(float(best_local_k * (1000.0 / fps)), 1)
            abs_local_offset = abs(local_offset_ms)

            if abs_local_offset >= 160.0 or (abs_local_offset >= 120.0 and best_local_r < 0.3):
                severity = "HIGH" if abs_local_offset >= 250.0 else "MEDIUM"
                raw_segments.append({
                    "start": t_start,
                    "end": t_end,
                    "offset_ms": local_offset_ms,
                    "severity": severity,
                    "type": "DESYNC",
                    "description": f"Temporal desynchronization of {local_offset_ms:+.0f} ms at {t_start:.1f}s - {t_end:.1f}s",
                })

    # Merge overlapping or contiguous segments of matching type
    merged = _merge_contiguous_segments(raw_segments)
    return merged


def _merge_contiguous_segments(raw_segments: List[Dict[str, Any]]) -> List[MismatchSegment]:
    """
    Merge overlapping or adjacent temporal segments into unified MismatchSegment objects.
    """
    if not raw_segments:
        return []

    # Sort primarily by start timestamp
    sorted_segs = sorted(raw_segments, key=lambda s: (s["type"], s["start"]))
    merged_results: List[MismatchSegment] = []

    current = sorted_segs[0]

    for next_seg in sorted_segs[1:]:
        same_type = next_seg["type"] == current["type"]
        is_overlapping = next_seg["start"] <= current["end"] + 0.25

        if same_type and is_overlapping:
            # Extend current segment
            current["end"] = max(current["end"], next_seg["end"])
            # Keep higher severity
            if next_seg["severity"] == "HIGH":
                current["severity"] = "HIGH"
            # Average offset
            current["offset_ms"] = round((current["offset_ms"] + next_seg["offset_ms"]) / 2.0, 1)
        else:
            merged_results.append(
                MismatchSegment(
                    start_time=current["start"],
                    end_time=current["end"],
                    offset_ms=current["offset_ms"],
                    confidence=0.85,
                    reason=current["description"],
                    severity=current["severity"],
                )
            )
            current = next_seg

    # Append trailing segment
    merged_results.append(
        MismatchSegment(
            start_time=current["start"],
            end_time=current["end"],
            offset_ms=current["offset_ms"],
            confidence=0.85,
            reason=current["description"],
            severity=current["severity"],
        )
    )

    # Final sort chronologically by start time
    return sorted(merged_results, key=lambda x: x.start_time)


def compute_temporal_drift(
    timestamps: np.ndarray,
    visual_signal: np.ndarray,
    audio_signal: np.ndarray,
    fps: float = 25.0,
) -> float:
    """
    Measure temporal drift (variation in alignment offset across duration).

    Divides duration into temporal quarters and measures standard deviation of regional offsets.
    A non-zero drift score indicates progressive desynchronization over time.

    Returns:
        drift_score: Float in [0.0, 1.0] representing degree of drift instability.
    """
    n_frames = min(len(timestamps), len(visual_signal), len(audio_signal))
    if n_frames < int(fps * 4):  # Less than 4 seconds
        return 0.0

    quarter = n_frames // 4
    offsets = []

    for i in range(4):
        start = i * quarter
        end = (i + 1) * quarter
        sub_v = visual_signal[start:end]
        sub_a = audio_signal[start:end]

        if np.std(sub_v) > 1e-4 and np.std(sub_a) > 1e-4:
            # Local cross-correlation
            lags = range(-8, 9)
            best_r = -1.0
            best_k = 0
            for k in lags:
                if k < 0:
                    a_s = sub_a[-k:]
                    v_s = sub_v[: len(a_s)]
                elif k > 0:
                    a_s = sub_a[: len(sub_a) - k]
                    v_s = sub_v[k : k + len(a_s)]
                else:
                    a_s = sub_a
                    v_s = sub_v
                if len(a_s) > 2:
                    r = float(np.corrcoef(a_s, v_s)[0, 1])
                    if r > best_r:
                        best_r = r
                        best_k = k
            offsets.append(best_k * (1000.0 / fps))

    if len(offsets) < 2:
        return 0.0

    drift_std = float(np.std(offsets))
    # Map std ms in [0, 200] -> [0.0, 1.0]
    drift_score = float(np.clip(drift_std / 200.0, 0.0, 1.0))
    return round(drift_score, 4)
