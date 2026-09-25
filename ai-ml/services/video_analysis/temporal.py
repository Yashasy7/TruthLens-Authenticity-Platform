"""
TruthLens AI/ML — Temporal Aggregation & Suspicious Timeline Generator
Blueprint: Module 06 — Temporal frame inconsistency analyzer & timeline timestamp marker
"""

from __future__ import annotations

import logging
from typing import List, Tuple

import cv2
import numpy as np

from schemas.video_analysis import FrameScore, SuspiciousTimestamp
from services.video_analysis.face_detector import FrameFaceAnalysis

logger = logging.getLogger(__name__)


def compute_temporal_inconsistency(
    crop_prev: np.ndarray,
    crop_curr: np.ndarray,
) -> float:
    """
    Measure pixel-level and structural discrepancy between consecutive face crops.
    Face-swap and deepfake models often exhibit frame-to-frame boundary jitter or warping.

    Args:
        crop_prev: uint8 RGB array (H, W, 3).
        crop_curr: uint8 RGB array (H, W, 3).

    Returns:
        float score in [0.0, 1.0] representing normalized temporal inconsistency.
    """
    if crop_prev.shape != crop_curr.shape:
        crop_curr = cv2.resize(crop_curr, (crop_prev.shape[1], crop_prev.shape[0]))

    gray_prev = cv2.cvtColor(crop_prev, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray_curr = cv2.cvtColor(crop_curr, cv2.COLOR_RGB2GRAY).astype(np.float32)

    diff = np.abs(gray_curr - gray_prev)
    mean_diff = float(np.mean(diff))

    # Normalized against max expected natural inter-frame motion (~40 pixel intensity shift)
    inconsistency = float(np.clip(mean_diff / 40.0, 0.0, 1.0))
    return round(inconsistency, 4)


def evaluate_temporal_timeline(
    face_analyses: List[FrameFaceAnalysis],
    base_clip_score: float,
    suspicious_threshold: float = 0.50,
) -> Tuple[float, List[FrameScore], List[SuspiciousTimestamp]]:
    """
    Aggregate frame-level facial analyses and 3D-CNN clip score into a coherent
    temporal timeline and overall video deepfake probability.

    Args:
        face_analyses: List of FrameFaceAnalysis objects from face detection stage.
        base_clip_score: 3D-CNN deepfake probability for the temporal video clip.
        suspicious_threshold: Threshold above which a frame is flagged suspicious.

    Returns:
        Tuple of (overall_deepfake_prob, frame_scores, suspicious_timestamps).
    """
    if not face_analyses:
        return 0.0, [], []

    frame_scores: List[FrameScore] = []
    num_frames = len(face_analyses)

    # 1. Compute per-frame metrics and temporal inconsistencies
    for i, analysis in enumerate(face_analyses):
        current_crop = analysis.primary_face.face_crop_rgb

        if i == 0:
            temporal_inconsistency = 0.0
        else:
            prev_crop = face_analyses[i - 1].primary_face.face_crop_rgb
            temporal_inconsistency = compute_temporal_inconsistency(prev_crop, current_crop)

        # Blend base clip score with frame-specific temporal discrepancy
        # Frame score elevates if there is high temporal jitter or fallback
        frame_deepfake_score = float(np.clip(
            base_clip_score * 0.70 + temporal_inconsistency * 0.30,
            0.0,
            1.0,
        ))

        is_suspicious = bool(
            frame_deepfake_score >= suspicious_threshold or temporal_inconsistency >= 0.45
        )

        frame_scores.append(
            FrameScore(
                frame_index=analysis.frame_index,
                timestamp_seconds=analysis.timestamp_seconds,
                deepfake_score=round(frame_deepfake_score, 4),
                temporal_inconsistency=round(temporal_inconsistency, 4),
                faces_detected=analysis.faces_detected,
                is_suspicious=is_suspicious,
            )
        )

    # 2. Overall Deepfake Probability: Top-k Percentile Pooling
    # Aggregates the top 35% most suspicious frame scores to prevent a single artifact
    # from skewing authentic video, while ensuring manipulated segments are detected.
    all_scores = [fs.deepfake_score for fs in frame_scores]
    k = max(1, int(np.ceil(num_frames * 0.35)))
    top_k_scores = sorted(all_scores, reverse=True)[:k]
    overall_deepfake_prob = float(np.clip(np.mean(top_k_scores), 0.0, 1.0))

    # 3. Cluster and group suspicious timestamps
    suspicious_timestamps = cluster_suspicious_timestamps(frame_scores)

    return round(overall_deepfake_prob, 4), frame_scores, suspicious_timestamps


def cluster_suspicious_timestamps(
    frame_scores: List[FrameScore],
    max_gap_seconds: float = 1.5,
) -> List[SuspiciousTimestamp]:
    """
    Group contiguous suspicious frames into timeline event markers.
    Prevents UI flood by consolidating adjacent anomalous frames into one representative event.

    Args:
        frame_scores: List of evaluated frame scores.
        max_gap_seconds: Maximum time gap to merge adjacent suspicious frames.

    Returns:
        Consolidated list of SuspiciousTimestamp objects.
    """
    suspicious_frames = [fs for fs in frame_scores if fs.is_suspicious]
    if not suspicious_frames:
        return []

    clusters: List[List[FrameScore]] = []
    current_cluster: List[FrameScore] = [suspicious_frames[0]]

    for fs in suspicious_frames[1:]:
        prev_fs = current_cluster[-1]
        if (fs.timestamp_seconds - prev_fs.timestamp_seconds) <= max_gap_seconds:
            current_cluster.append(fs)
        else:
            clusters.append(current_cluster)
            current_cluster = [fs]

    if current_cluster:
        clusters.append(current_cluster)

    timeline: List[SuspiciousTimestamp] = []
    for cluster in clusters:
        # Find peak anomaly frame within this contiguous interval
        peak_frame = max(cluster, key=lambda f: f.deepfake_score)

        if peak_frame.temporal_inconsistency >= 0.40 and peak_frame.deepfake_score >= 0.60:
            reason = f"Facial synthesis anomaly & boundary discontinuity (score: {peak_frame.deepfake_score:.2f})"
        elif peak_frame.temporal_inconsistency >= 0.40:
            reason = f"Abrupt temporal facial jitter (inconsistency: {peak_frame.temporal_inconsistency:.2f})"
        else:
            reason = f"High facial artifact anomaly (score: {peak_frame.deepfake_score:.2f})"

        timeline.append(
            SuspiciousTimestamp(
                timestamp_seconds=round(peak_frame.timestamp_seconds, 2),
                frame_index=peak_frame.frame_index,
                score=round(peak_frame.deepfake_score, 4),
                reason=reason,
            )
        )

    return timeline
