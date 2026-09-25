"""
TruthLens AI/ML — Module 08: Facial Landmark & Lip-Motion Tracking
Blueprint: Extract primary speaker mouth ROI (96x96), compute Mouth Aspect Ratio (MAR) dynamics,
           and generate continuous normalized visual lip-activity timeline.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

from config.settings import settings
from services.video_analysis.face_detector import (
    FaceBoundingBox,
    DetectedFace,
    FrameFaceAnalysis,
    extract_facial_tracks,
)
from services.video_analysis.ingestion import SampledFrame

logger = logging.getLogger(__name__)


@dataclass
class FrameLipRecord:
    """Per-frame mouth tracking and aspect ratio telemetry."""
    frame_index: int
    timestamp_seconds: float
    mouth_bbox: Optional[Tuple[int, int, int, int]]  # (x, y, w, h)
    mar: float                                      # Mouth Aspect Ratio
    mouth_crop: np.ndarray                          # (96, 96) uint8 grayscale
    confidence: float
    face_detected: bool


@dataclass
class VisualLipFeatures:
    """Full visual lip tracking result across the video timeline."""
    timestamps: np.ndarray
    lip_activity_curve: np.ndarray          # 1D normalized lip activity [0.0, 1.0]
    mouth_crops: List[np.ndarray]           # List of (crop_size, crop_size) uint8 grayscale
    face_detected_mask: List[bool]          # True if real face detected per frame
    face_detected_ratio: float              # Ratio of frames with real face detected
    mean_lip_motion: float                  # Mean lip activity over time
    detected_faces_count: int
    tracking_stability: float
    frame_records: List[FrameLipRecord]

    # Aliases
    @property
    def lip_activity(self) -> np.ndarray:
        return self.lip_activity_curve

    @property
    def lip_crops(self) -> List[np.ndarray]:
        return self.mouth_crops


class LipMotionTracker:
    """
    Deterministic visual lip motion and mouth viseme tracking engine.
    Extracts geometric mouth ROIs from detected face bounding boxes,
    tracks Mouth Aspect Ratio (MAR) dynamics, and computes frame-to-frame visual motion.
    """

    def __init__(self, crop_size: int = 96) -> None:
        self.crop_size = crop_size

    def track_lip_motion(
        self,
        frames_rgb: List[np.ndarray],
        timestamps: np.ndarray,
    ) -> VisualLipFeatures:
        """
        Track mouth regions and compute continuous lip motion across video frames.

        Args:
            frames_rgb: List of RGB video frames as uint8 numpy arrays.
            timestamps: 1D array of frame timestamps in seconds.

        Returns:
            VisualLipFeatures containing lip activity curve, crops, and tracking stability.
        """
        n_frames = len(frames_rgb)
        if n_frames == 0:
            return VisualLipFeatures(
                timestamps=np.zeros(0, dtype=np.float32),
                lip_activity_curve=np.zeros(0, dtype=np.float32),
                mouth_crops=[],
                face_detected_mask=[],
                face_detected_ratio=0.0,
                mean_lip_motion=0.0,
                detected_faces_count=0,
                tracking_stability=0.0,
                frame_records=[],
            )

        # Convert to SampledFrame objects for M06 face detector
        sampled_frames = [
            SampledFrame(frame_index=i, timestamp_seconds=float(timestamps[i]), frame_rgb=frames_rgb[i])
            for i in range(n_frames)
        ]

        # Stage 1: Face detection and bounding box tracking using M06 detector
        face_analyses: List[FrameFaceAnalysis] = extract_facial_tracks(
            sampled_frames,
            target_size=(settings.video_crop_size, settings.video_crop_size),
        )

        detected_faces_count = max([fa.faces_detected for fa in face_analyses], default=0)

        # Stage 2: Extract mouth crops and Mouth Aspect Ratio (MAR)
        frame_records: List[FrameLipRecord] = []
        mouth_crops: List[np.ndarray] = []
        mar_values: List[float] = []
        face_detected_mask: List[bool] = []
        detected_frames_count = 0

        last_valid_crop = np.zeros((self.crop_size, self.crop_size), dtype=np.uint8)
        last_valid_mar = 0.25

        for i in range(n_frames):
            frame_rgb = frames_rgb[i]
            fa = face_analyses[i]
            ts = float(timestamps[i])

            has_real_face = not fa.primary_face.is_fallback and fa.faces_detected > 0

            if has_real_face:
                record = self._extract_mouth_from_face(frame_rgb, fa.primary_face.bbox, i, ts)
                detected_frames_count += 1
                last_valid_crop = record.mouth_crop
                last_valid_mar = record.mar
                face_detected_mask.append(True)
            else:
                record = self._extract_center_mouth_fallback(frame_rgb, i, ts, last_valid_crop, last_valid_mar)
                face_detected_mask.append(False)

            frame_records.append(record)
            mouth_crops.append(record.mouth_crop)
            mar_values.append(record.mar)

        tracking_stability = detected_frames_count / max(1, n_frames)

        # Stage 3: Compute continuous 1D normalized lip activity timeline [0.0, 1.0]
        lip_activity = self._compute_lip_activity(mar_values, mouth_crops)
        mean_motion = float(np.mean(lip_activity)) if len(lip_activity) > 0 else 0.0

        return VisualLipFeatures(
            timestamps=timestamps,
            lip_activity_curve=lip_activity,
            mouth_crops=mouth_crops,
            face_detected_mask=face_detected_mask,
            face_detected_ratio=round(float(tracking_stability), 4),
            mean_lip_motion=round(float(mean_motion), 4),
            detected_faces_count=detected_faces_count,
            tracking_stability=round(float(tracking_stability), 4),
            frame_records=frame_records,
        )

    def _extract_mouth_from_face(
        self,
        frame_rgb: np.ndarray,
        bbox: FaceBoundingBox,
        frame_index: int,
        timestamp: float,
    ) -> FrameLipRecord:
        """Extract mouth bounding box and aspect ratio from detected face bounding box."""
        h, w = frame_rgb.shape[:2]

        # Anatomical geometric heuristic: mouth is centered horizontally in lower third of face
        mouth_center_x = bbox.x + bbox.width / 2.0
        mouth_center_y = bbox.y + bbox.height * 0.78
        mouth_width = bbox.width * 0.52
        mouth_height = bbox.height * 0.32

        x1 = max(0, int(mouth_center_x - mouth_width / 2.0))
        y1 = max(0, int(mouth_center_y - mouth_height / 2.0))
        x2 = min(w, int(mouth_center_x + mouth_width / 2.0))
        y2 = min(h, int(mouth_center_y + mouth_height / 2.0))

        actual_w = max(1, x2 - x1)
        actual_h = max(1, y2 - y1)
        mouth_bbox = (x1, y1, actual_w, actual_h)

        mouth_roi = frame_rgb[y1:y2, x1:x2]
        if mouth_roi.size > 0:
            gray_crop = cv2.cvtColor(mouth_roi, cv2.COLOR_RGB2GRAY)
            norm_crop = cv2.resize(gray_crop, (self.crop_size, self.crop_size), interpolation=cv2.INTER_AREA)

            # Compute Mouth Aspect Ratio (MAR): geometric ratio + dark cavity opening
            thresh = cv2.threshold(norm_crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            opening_ratio = float(np.count_nonzero(thresh)) / float(norm_crop.size)
            mar = max(0.05, min(1.0, (actual_h / float(actual_w)) * 0.5 + opening_ratio * 0.5))
        else:
            norm_crop = np.zeros((self.crop_size, self.crop_size), dtype=np.uint8)
            mar = 0.25

        return FrameLipRecord(
            frame_index=frame_index,
            timestamp_seconds=timestamp,
            mouth_bbox=mouth_bbox,
            mar=round(mar, 4),
            mouth_crop=norm_crop,
            confidence=bbox.confidence,
            face_detected=True,
        )

    def _extract_center_mouth_fallback(
        self,
        frame_rgb: np.ndarray,
        frame_index: int,
        timestamp: float,
        last_valid_crop: np.ndarray,
        last_valid_mar: float,
    ) -> FrameLipRecord:
        """Fallback when face is absent: crop center-bottom of frame."""
        h, w = frame_rgb.shape[:2]
        cx, cy = w // 2, int(h * 0.7)
        crop_w, crop_h = int(w * 0.25), int(h * 0.15)
        x1, y1 = max(0, cx - crop_w // 2), max(0, cy - crop_h // 2)
        x2, y2 = min(w, cx + crop_w // 2), min(h, cy + crop_h // 2)

        roi = frame_rgb[y1:y2, x1:x2]
        if roi.size > 0:
            gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
            norm_crop = cv2.resize(gray, (self.crop_size, self.crop_size), interpolation=cv2.INTER_AREA)
        else:
            norm_crop = last_valid_crop.copy()

        return FrameLipRecord(
            frame_index=frame_index,
            timestamp_seconds=timestamp,
            mouth_bbox=None,
            mar=last_valid_mar,
            mouth_crop=norm_crop,
            confidence=0.0,
            face_detected=False,
        )

    def _compute_lip_activity(
        self,
        mar_values: List[float],
        lip_crops: List[np.ndarray],
    ) -> np.ndarray:
        """
        Compute a continuous 1D normalized visual lip activity timeline in [0.0, 1.0].
        Fuses first-order derivative of Mouth Aspect Ratio (MAR) with inter-frame pixel motion.
        """
        n = len(mar_values)
        if n == 0:
            return np.zeros(0, dtype=np.float32)
        if n == 1:
            return np.zeros(1, dtype=np.float32)

        mar_arr = np.array(mar_values, dtype=np.float32)

        # 1. First-order temporal derivative of MAR: |MAR_t - MAR_{t-1}|
        d_mar = np.abs(np.diff(mar_arr, prepend=mar_arr[0]))

        # 2. Inter-frame visual pixel motion between consecutive normalized mouth crops
        motion_scores = np.zeros(n, dtype=np.float32)
        for i in range(1, n):
            c_prev = lip_crops[i - 1].astype(np.float32)
            c_curr = lip_crops[i].astype(np.float32)
            motion_scores[i] = float(np.mean(np.abs(c_curr - c_prev)) / 255.0)
        motion_scores[0] = motion_scores[1] if n > 1 else 0.0

        # Weighted combination: 60% opening/closing dynamics + 40% visual motion
        activity = (d_mar * 0.60) + (motion_scores * 0.40)

        # Normalization to [0.0, 1.0]
        max_val = float(np.max(activity)) if len(activity) > 0 else 0.0
        if max_val > 1e-5:
            norm_activity = activity / max_val
        else:
            norm_activity = np.zeros(n, dtype=np.float32)

        return np.clip(norm_activity, 0.0, 1.0).astype(np.float32)


def extract_lip_motion_timeline(
    frames: List[np.ndarray],
    timestamps: np.ndarray,
    mouth_crop_size: int = 96,
) -> VisualLipFeatures:
    """Convenience functional wrapper for visual lip tracking."""
    tracker = LipMotionTracker(crop_size=mouth_crop_size)
    return tracker.track_lip_motion(frames_rgb=frames, timestamps=timestamps)
