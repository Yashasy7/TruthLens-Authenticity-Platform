"""
TruthLens AI/ML — Module 08: Lip Tracking & Mouth ROI Unit Tests
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from services.av_sync.lip_tracker import (
    LipMotionTracker,
    VisualLipFeatures,
    extract_lip_motion_timeline,
)
from services.video_analysis.face_detector import FaceBoundingBox


def _create_synthetic_face_frame(mouth_open: bool = False) -> np.ndarray:
    """Create a synthetic 200x200 image with a basic face and mouth."""
    img = np.full((200, 200, 3), 180, dtype=np.uint8)
    # Eyes
    cv2.circle(img, (70, 70), 10, (20, 20, 20), -1)
    cv2.circle(img, (130, 70), 10, (20, 20, 20), -1)
    # Mouth: if open, draw dark ellipse; if closed, draw thin line
    if mouth_open:
        cv2.ellipse(img, (100, 150), (25, 15), 0, 0, 360, (10, 10, 10), -1)
    else:
        cv2.line(img, (75, 150), (125, 150), (10, 10, 10), 3)
    return img


def test_empty_frames_lip_tracking():
    """Empty frames input returns empty features gracefully."""
    res = extract_lip_motion_timeline([], np.array([], dtype=np.float32), mouth_crop_size=96)
    assert isinstance(res, VisualLipFeatures)
    assert len(res.lip_activity_curve) == 0
    assert len(res.mouth_crops) == 0
    assert res.tracking_stability == 0.0


def test_lip_tracking_fallback_on_blank_frames():
    """Blank frames (no detectable face) safely trigger center fallback without crashing."""
    frames = [np.full((128, 128, 3), 100, dtype=np.uint8) for _ in range(10)]
    ts = np.arange(10, dtype=np.float32) / 25.0

    res = extract_lip_motion_timeline(frames, ts, mouth_crop_size=96)
    assert len(res.mouth_crops) == 10
    for crop in res.mouth_crops:
        assert crop.shape == (96, 96)
        assert crop.dtype == np.uint8
    assert len(res.lip_activity_curve) == 10
    assert res.face_detected_ratio == 0.0


def test_extract_mouth_from_bounding_box():
    """Test mouth extraction directly from a known FaceBoundingBox."""
    tracker = LipMotionTracker(crop_size=96)
    frame = _create_synthetic_face_frame(mouth_open=True)
    bbox = FaceBoundingBox(x=30, y=30, width=140, height=140, confidence=0.95)

    record = tracker._extract_mouth_from_face(frame, bbox, frame_index=0, timestamp=0.0)

    assert record.mouth_crop.shape == (96, 96)
    assert record.mar > 0.0
    assert record.face_detected is True
    assert record.mouth_bbox is not None
    assert record.confidence == 0.95


def test_mar_dynamics_with_open_and_closed_mouth():
    """Mouth Aspect Ratio should be higher for open mouth compared to closed mouth."""
    tracker = LipMotionTracker(crop_size=96)
    open_frame = _create_synthetic_face_frame(mouth_open=True)
    closed_frame = _create_synthetic_face_frame(mouth_open=False)
    bbox = FaceBoundingBox(x=30, y=30, width=140, height=140, confidence=0.95)

    rec_open = tracker._extract_mouth_from_face(open_frame, bbox, 0, 0.0)
    rec_closed = tracker._extract_mouth_from_face(closed_frame, bbox, 1, 0.04)

    assert rec_open.mar > rec_closed.mar
