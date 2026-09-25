"""
Tests for services/video_analysis/face_detector.py
Module 06 — Facial Detection & Bounding Box Tracking
"""

import numpy as np
import pytest

from services.video_analysis.face_detector import (
    FaceBoundingBox,
    OpenCVFaceDetector,
    RetinaFaceDetector,
    crop_face_with_margin,
    extract_facial_tracks,
    get_face_detector,
)
from services.video_analysis.ingestion import SampledFrame


class TestFaceDetector:

    def test_opencv_face_detector_initialization(self):
        detector = OpenCVFaceDetector()
        assert detector.cascade is not None

    def test_crop_face_with_margin_expansion(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        bbox = FaceBoundingBox(x=30, y=30, width=40, height=40, confidence=1.0)
        # Margin 20% on 40px = 8px padding each side -> 56x56
        res = crop_face_with_margin(frame, bbox, margin=0.20, target_size=(112, 112))
        assert not res.is_fallback
        assert res.face_crop_rgb.shape == (112, 112, 3)

    def test_no_face_fallback_to_center_crop(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        res = crop_face_with_margin(frame, bbox=None, target_size=(112, 112))
        assert res.is_fallback
        assert res.face_crop_rgb.shape == (112, 112, 3)
        assert res.bbox.width == 100
        assert res.bbox.height == 100

    def test_extract_facial_tracks_handles_empty_faces_gracefully(self):
        # Blank black frames (no face)
        sf1 = SampledFrame(frame_index=0, timestamp_seconds=0.0, frame_rgb=np.zeros((80, 80, 3), dtype=np.uint8))
        sf2 = SampledFrame(frame_index=1, timestamp_seconds=0.5, frame_rgb=np.zeros((80, 80, 3), dtype=np.uint8))

        tracks = extract_facial_tracks([sf1, sf2], target_size=(112, 112))
        assert len(tracks) == 2
        assert tracks[0].faces_detected == 0
        assert tracks[0].primary_face.is_fallback
        assert tracks[0].primary_face.face_crop_rgb.shape == (112, 112, 3)

    def test_get_face_detector_factory_auto(self):
        detector = get_face_detector("auto")
        assert isinstance(detector, OpenCVFaceDetector)

    def test_retinaface_backend_reports_missing_dependency_cleanly(self):
        retina = RetinaFaceDetector()
        with pytest.raises(NotImplementedError) as exc_info:
            retina.detect_faces(np.zeros((64, 64, 3), dtype=np.uint8))
        assert "RetinaFace" in str(exc_info.value)

    def test_deterministic_face_cropping(self):
        frame = np.random.randint(0, 255, (120, 120, 3), dtype=np.uint8)
        bbox = FaceBoundingBox(x=20, y=20, width=50, height=50, confidence=1.0)
        crop1 = crop_face_with_margin(frame, bbox, target_size=(112, 112)).face_crop_rgb
        crop2 = crop_face_with_margin(frame, bbox, target_size=(112, 112)).face_crop_rgb
        np.testing.assert_array_equal(crop1, crop2)
