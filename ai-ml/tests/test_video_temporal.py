"""
Tests for services/video_analysis/temporal.py
Module 06 — Temporal Aggregation & Timeline Clustering
"""

import numpy as np
import pytest

from schemas.video_analysis import FrameScore
from services.video_analysis.face_detector import (
    DetectedFace,
    FaceBoundingBox,
    FrameFaceAnalysis,
)
from services.video_analysis.temporal import (
    cluster_suspicious_timestamps,
    compute_temporal_inconsistency,
    evaluate_temporal_timeline,
)


class TestVideoTemporal:

    def test_temporal_inconsistency_identical_crops(self):
        crop = np.full((112, 112, 3), 128, dtype=np.uint8)
        inconsistency = compute_temporal_inconsistency(crop, crop)
        assert inconsistency == 0.0

    def test_temporal_inconsistency_disparate_crops(self):
        crop1 = np.zeros((112, 112, 3), dtype=np.uint8)
        crop2 = np.full((112, 112, 3), 255, dtype=np.uint8)
        inconsistency = compute_temporal_inconsistency(crop1, crop2)
        assert inconsistency > 0.5

    def test_evaluate_temporal_timeline_empty(self):
        score, frames, timeline = evaluate_temporal_timeline([], base_clip_score=0.5)
        assert score == 0.0
        assert frames == []
        assert timeline == []

    def test_evaluate_temporal_timeline_synthetic_sequence(self):
        dummy_bbox = FaceBoundingBox(x=10, y=10, width=50, height=50, confidence=1.0)
        face_analyses = []
        for i in range(10):
            crop = np.full((112, 112, 3), 100 + i * 5, dtype=np.uint8)
            det = DetectedFace(bbox=dummy_bbox, face_crop_rgb=crop, is_fallback=False)
            face_analyses.append(
                FrameFaceAnalysis(
                    frame_index=i,
                    timestamp_seconds=round(i * 0.5, 2),
                    faces_detected=1,
                    primary_face=det,
                )
            )

        prob, frame_scores, timeline = evaluate_temporal_timeline(
            face_analyses,
            base_clip_score=0.40,
            suspicious_threshold=0.50,
        )

        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0
        assert len(frame_scores) == 10
        assert isinstance(timeline, list)

    def test_cluster_suspicious_timestamps_consolidation(self):
        # 3 contiguous suspicious frames followed by a distant suspicious frame
        scores = [
            FrameScore(frame_index=0, timestamp_seconds=1.0, deepfake_score=0.85, temporal_inconsistency=0.2, faces_detected=1, is_suspicious=True),
            FrameScore(frame_index=1, timestamp_seconds=1.5, deepfake_score=0.90, temporal_inconsistency=0.3, faces_detected=1, is_suspicious=True),
            FrameScore(frame_index=2, timestamp_seconds=2.0, deepfake_score=0.80, temporal_inconsistency=0.2, faces_detected=1, is_suspicious=True),
            FrameScore(frame_index=3, timestamp_seconds=3.0, deepfake_score=0.20, temporal_inconsistency=0.1, faces_detected=1, is_suspicious=False),
            # Distant anomalous event at 10.0s
            FrameScore(frame_index=4, timestamp_seconds=10.0, deepfake_score=0.75, temporal_inconsistency=0.5, faces_detected=1, is_suspicious=True),
        ]

        clusters = cluster_suspicious_timestamps(scores, max_gap_seconds=1.5)
        # Should consolidate the first 3 frames into 1 event, plus the distant event at 10.0s -> 2 events total
        assert len(clusters) == 2
        assert clusters[0].score == 0.90
        assert clusters[0].timestamp_seconds == 1.5
        assert clusters[1].timestamp_seconds == 10.0
