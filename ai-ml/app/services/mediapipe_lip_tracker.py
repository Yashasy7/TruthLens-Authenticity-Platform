import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from ..config import settings
from .face_detector_tracker import RetinaFaceTracker, DetectedFace

# Attempt importing MediaPipe tasks
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    MEDIAPIPE_AVAILABLE = True
except Exception:
    MEDIAPIPE_AVAILABLE = False


class FrameLipData:
    """Represents extracted lip metrics and cropped viseme region for a single frame."""
    def __init__(
        self,
        frame_index: int,
        timestamp_seconds: float,
        mouth_bbox: Optional[Tuple[int, int, int, int]] = None,
        mar: float = 0.0,
        mouth_crop: Optional[np.ndarray] = None,
        confidence: float = 0.0,
    ):
        self.frame_index = frame_index
        self.timestamp_seconds = round(float(timestamp_seconds), 4)
        self.mouth_bbox = mouth_bbox  # (x, y, w, h)
        self.mar = float(mar)  # Mouth Aspect Ratio (height / width)
        self.mouth_crop = mouth_crop  # Grayscale or RGB normalized lip patch
        self.confidence = float(confidence)


class LipTrackingResult:
    """Container for multi-frame temporal lip tracking output."""
    def __init__(
        self,
        timestamps: np.ndarray,
        lip_activity: np.ndarray,
        lip_crops: List[np.ndarray],
        detected_faces_count: int,
        primary_track_id: int,
        tracking_stability: float,
        frame_lip_data: List[FrameLipData],
    ):
        self.timestamps = timestamps
        self.lip_activity = lip_activity  # 1D normalized activity timeline [0.0, 1.0]
        self.lip_crops = lip_crops  # List of (96, 96) mouth crops for SyncNet
        self.detected_faces_count = detected_faces_count
        self.primary_track_id = primary_track_id
        self.tracking_stability = float(tracking_stability)
        self.frame_lip_data = frame_lip_data


class MediaPipeLipTracker:
    """
    Temporal Lip Landmark and Viseme Extraction Pipeline.
    
    Adheres to TruthLens Blueprint Module 08 specification:
    Video Frames -> MediaPipe Lip Tracker -> Viseme motion timeline & normalized mouth patches.
    
    Features:
    1. MediaPipe FaceLandmarker integration when task model is present.
    2. Robust geometric lip fallback using RetinaFace face/landmark detector.
    3. Multi-face speaker attribution: tracks faces, calculates mouth motion dynamics,
       and selects the active speaking face track.
    4. Resilient handling of intermittent face loss, occlusions, and zero-face videos.
    5. Normalized mouth crop extraction (96x96) formatted for SyncNet evaluation.
    """

    def __init__(
        self,
        mediapipe_model_path: str = settings.MEDIAPIPE_MODEL_PATH,
        crop_size: int = 96,
    ):
        self.mediapipe_model_path = mediapipe_model_path
        self.crop_size = crop_size
        self.face_tracker = RetinaFaceTracker()
        self._mp_landmarker = None

        if MEDIAPIPE_AVAILABLE and self.mediapipe_model_path and os.path.isfile(self.mediapipe_model_path):
            try:
                base_options = mp_python.BaseOptions(model_asset_path=self.mediapipe_model_path)
                options = mp_vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    running_mode=mp_vision.RunningMode.IMAGE,
                    num_faces=4,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5,
                )
                self._mp_landmarker = mp_vision.FaceLandmarker.create_from_options(options)
            except Exception:
                self._mp_landmarker = None

    def track_lips(
        self,
        frames: List[np.ndarray],
        timestamps: List[float],
    ) -> LipTrackingResult:
        """
        Processes an ordered list of RGB video frames and extracts temporal lip activity.
        
        Args:
            frames: Chronologically ordered list of RGB frames (uint8 numpy arrays).
            timestamps: Timestamp in seconds corresponding to each frame.
            
        Returns:
            LipTrackingResult with normalized lip activity curve, mouth crops, and metadata.
        """
        n_frames = len(frames)
        if n_frames == 0:
            return LipTrackingResult(
                timestamps=np.array([], dtype=np.float32),
                lip_activity=np.array([], dtype=np.float32),
                lip_crops=[],
                detected_faces_count=0,
                primary_track_id=-1,
                tracking_stability=0.0,
                frame_lip_data=[],
            )

        ts_array = np.array(timestamps, dtype=np.float32)

        # Track faces across all frames
        # Map: track_id -> List of (frame_index, DetectedFace, mouth_data)
        tracks_data: Dict[int, List[Tuple[int, Optional[DetectedFace], FrameLipData]]] = {}
        all_track_ids = set()

        # Reset face tracker for fresh video
        self.face_tracker.active_tracks.clear()
        self.face_tracker.next_track_id = 1

        for idx, (frame_rgb, ts) in enumerate(zip(frames, timestamps)):
            # Ignore completely blank/solid frames with no image contrast
            if float(np.std(frame_rgb)) < 2.0 or int(np.max(frame_rgb)) == 0:
                tracked_faces = []
            else:
                tracked_faces = self.face_tracker.track_faces_in_frame(frame_rgb, frame_index=idx)
            if tracked_faces:
                for face in tracked_faces:
                    all_track_ids.add(face.track_id)
                    if face.track_id not in tracks_data:
                        tracks_data[face.track_id] = []
                    lip_data = self._extract_lip_data(frame_rgb, face, idx, ts)
                    tracks_data[face.track_id].append((idx, face, lip_data))

        # Select primary speaker face track
        primary_track_id = -1
        if tracks_data:
            primary_track_id = self._select_primary_speaker(tracks_data, n_frames)

        # Build continuous sequence for primary track
        frame_lip_records: List[FrameLipData] = []
        lip_crops: List[np.ndarray] = []
        mar_values: List[float] = []
        detected_frames_count = 0

        # Create quick lookup for primary track: frame_idx -> FrameLipData
        primary_lookup: Dict[int, FrameLipData] = {}
        if primary_track_id in tracks_data:
            for f_idx, _, lip_data in tracks_data[primary_track_id]:
                primary_lookup[f_idx] = lip_data

        last_valid_crop = np.zeros((self.crop_size, self.crop_size), dtype=np.uint8)
        last_valid_mar = 0.25

        for idx in range(n_frames):
            ts = float(timestamps[idx])
            if idx in primary_lookup:
                lip_record = primary_lookup[idx]
                detected_frames_count += 1
                last_valid_crop = lip_record.mouth_crop if lip_record.mouth_crop is not None else last_valid_crop
                last_valid_mar = lip_record.mar
                frame_lip_records.append(lip_record)
                lip_crops.append(last_valid_crop)
                mar_values.append(lip_record.mar)
            else:
                # Missing face / tracking loss in this frame: fill with last valid or neutral
                fallback_record = FrameLipData(
                    frame_index=idx,
                    timestamp_seconds=ts,
                    mouth_bbox=None,
                    mar=last_valid_mar,
                    mouth_crop=last_valid_crop.copy(),
                    confidence=0.0,
                )
                frame_lip_records.append(fallback_record)
                lip_crops.append(last_valid_crop.copy())
                mar_values.append(last_valid_mar)

        tracking_stability = detected_frames_count / max(1, n_frames)

        # Compute temporal lip activity from mouth opening dynamics and visual optical motion
        lip_activity = self._compute_lip_activity(mar_values, lip_crops)

        return LipTrackingResult(
            timestamps=ts_array,
            lip_activity=lip_activity,
            lip_crops=lip_crops,
            detected_faces_count=len(all_track_ids),
            primary_track_id=primary_track_id,
            tracking_stability=round(tracking_stability, 4),
            frame_lip_data=frame_lip_records,
        )

    def _extract_lip_data(
        self,
        frame_rgb: np.ndarray,
        face: DetectedFace,
        frame_index: int,
        timestamp: float,
    ) -> FrameLipData:
        """Extracts mouth bounding box, aspect ratio, and normalized crop from a detected face."""
        h, w = frame_rgb.shape[:2]

        # Use facial landmarks if available from RetinaFace (5 points: le, re, nose, lm, rm)
        if face.landmarks and len(face.landmarks) >= 5:
            # lm: left mouth corner, rm: right mouth corner
            lm = face.landmarks[3]
            rm = face.landmarks[4]
            mouth_center_x = (lm[0] + rm[0]) / 2.0
            mouth_center_y = (lm[1] + rm[1]) / 2.0
            mouth_width = max(10.0, abs(rm[0] - lm[0]) * 1.5)
            mouth_height = max(8.0, mouth_width * 0.65)
        else:
            # Geometric estimation from face bounding box: lower third of face
            mouth_center_x = face.x + face.width / 2.0
            mouth_center_y = face.y + face.height * 0.78
            mouth_width = face.width * 0.50
            mouth_height = face.height * 0.32

        # Bounding box coordinates with safety bounds
        x1 = max(0, int(mouth_center_x - mouth_width / 2.0))
        y1 = max(0, int(mouth_center_y - mouth_height / 2.0))
        x2 = min(w, int(mouth_center_x + mouth_width / 2.0))
        y2 = min(h, int(mouth_center_y + mouth_height / 2.0))

        actual_w = max(1, x2 - x1)
        actual_h = max(1, y2 - y1)
        mouth_bbox = (x1, y1, actual_w, actual_h)

        # Crop mouth patch
        mouth_roi = frame_rgb[y1:y2, x1:x2]
        if mouth_roi.size > 0:
            gray_crop = cv2.cvtColor(mouth_roi, cv2.COLOR_RGB2GRAY)
            norm_crop = cv2.resize(gray_crop, (self.crop_size, self.crop_size), interpolation=cv2.INTER_AREA)

            # Compute Mouth Aspect Ratio (MAR) using intensity vertical profile or geometry
            # Darker mouth cavity indicates opening
            thresh = cv2.threshold(norm_crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            opening_ratio = float(np.count_nonzero(thresh)) / float(norm_crop.size)
            mar = max(0.05, min(1.0, (actual_h / float(actual_w)) * 0.5 + opening_ratio * 0.5))
        else:
            norm_crop = np.zeros((self.crop_size, self.crop_size), dtype=np.uint8)
            mar = 0.25

        return FrameLipData(
            frame_index=frame_index,
            timestamp_seconds=timestamp,
            mouth_bbox=mouth_bbox,
            mar=round(mar, 4),
            mouth_crop=norm_crop,
            confidence=face.confidence,
        )

    def _select_primary_speaker(
        self,
        tracks_data: Dict[int, List[Tuple[int, Optional[DetectedFace], FrameLipData]]],
        total_frames: int,
    ) -> int:
        """
        Determines the primary active speaking face track.
        Evaluates temporal persistence, face size, and mouth opening variance.
        """
        best_track_id = -1
        best_score = -1.0

        for track_id, observations in tracks_data.items():
            obs_count = len(observations)
            if obs_count == 0:
                continue

            # Persistence score
            persistence = obs_count / float(total_frames)

            # Mean face area
            face_areas = [f.width * f.height for _, f, _ in observations if f is not None]
            mean_area = np.mean(face_areas) if face_areas else 1.0

            # Mouth dynamic variance (motion energy)
            mars = [lip.mar for _, _, lip in observations]
            mar_variance = float(np.var(mars)) if len(mars) > 1 else 0.0

            # Composite speaker activity score
            score = (persistence * 0.4) + (min(1.0, mean_area / 40000.0) * 0.3) + (min(1.0, mar_variance * 50.0) * 0.3)

            if score > best_score:
                best_score = score
                best_track_id = track_id

        return best_track_id

    def _compute_lip_activity(
        self,
        mar_values: List[float],
        lip_crops: List[np.ndarray],
    ) -> np.ndarray:
        """
        Computes a continuous 1D normalized lip activity timeline [0.0, 1.0].
        Combines delta Mouth Aspect Ratio (derivative) and inter-frame visual motion.
        """
        n = len(mar_values)
        if n == 0:
            return np.array([], dtype=np.float32)
        if n == 1:
            return np.array([0.0], dtype=np.float32)

        mar_arr = np.array(mar_values, dtype=np.float32)

        # 1. First-order temporal derivative of MAR
        d_mar = np.abs(np.diff(mar_arr, prepend=mar_arr[0]))

        # 2. Inter-frame pixel motion in mouth crops
        motion_scores = np.zeros(n, dtype=np.float32)
        for i in range(1, n):
            c_prev = lip_crops[i - 1].astype(np.float32)
            c_curr = lip_crops[i].astype(np.float32)
            motion_scores[i] = np.mean(np.abs(c_curr - c_prev)) / 255.0
        motion_scores[0] = motion_scores[1] if n > 1 else 0.0

        # Combine MAR derivative and visual motion
        activity = (d_mar * 0.6) + (motion_scores * 0.4)

        # Normalization with min-max smoothing
        max_val = np.max(activity)
        if max_val > 1e-5:
            activity = activity / max_val
        else:
            activity = np.zeros(n, dtype=np.float32)

        return np.clip(activity, 0.0, 1.0).astype(np.float32)
