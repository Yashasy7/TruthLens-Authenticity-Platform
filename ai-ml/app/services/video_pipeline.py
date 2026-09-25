import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
from ..config import settings
from ..schemas import (
    VideoAnalysisResult,
    VideoAnalysisEvidence,
    VideoFrameScore,
    SuspiciousTimestamp,
)
from .ffmpeg_sampler import FFmpegVideoSampler, SampledFrame
from .face_detector_tracker import RetinaFaceTracker, DetectedFace
from .video_deepfake_classifier import VideoDeepfakeInferenceService
from .temporal_analyzer import TemporalForensicAnalyzer


class VideoAnalysisPipeline:
    """
    End-to-end video authenticity and deepfake forensic analysis pipeline.
    
    Adheres to blueprint specification:
    Video File -> FFmpeg Sampler -> RetinaFace Detector -> PyTorch 3D-CNN / EfficientNet -> Suspicious Frame Array -> Video Deepfake Score
    """

    def __init__(
        self,
        sampler: FFmpegVideoSampler | None = None,
        tracker: RetinaFaceTracker | None = None,
        classifier: VideoDeepfakeInferenceService | None = None,
        temporal_analyzer: TemporalForensicAnalyzer | None = None,
    ):
        self.sampler = sampler or FFmpegVideoSampler()
        self.tracker = tracker or RetinaFaceTracker()
        self.classifier = classifier or VideoDeepfakeInferenceService()
        self.temporal_analyzer = temporal_analyzer or TemporalForensicAnalyzer()

    def analyze_video(self, video_path: str) -> VideoAnalysisResult:
        """
        Executes complete video deepfake and forensic analysis pipeline.
        
        Args:
            video_path: Absolute or relative path to local video file
            
        Returns:
            VideoAnalysisResult containing deepfake_prob, timeline markers, and frame scores.
        """
        # 1. Deterministic Frame Sampling
        sampled_frames, duration_seconds = self.sampler.sample_video(video_path)
        if not sampled_frames:
            raise ValueError("No valid video frames could be extracted.")

        frame_scores: List[VideoFrameScore] = []
        suspicious_timestamps: List[SuspiciousTimestamp] = []
        last_face_by_track: Dict[int, np.ndarray] = {}  # track_id -> face crop BGR
        track_crops_history: Dict[int, List[np.ndarray]] = {}  # track_id -> list of RGB face crops
        all_observed_track_ids = set()

        # 2. Iterate chronologically through sampled frames
        for frame in sampled_frames:
            # Face Detection & Tracking via genuine PyTorch RetinaFace
            faces: List[DetectedFace] = self.tracker.track_faces_in_frame(frame.image_bgr, frame.frame_index)
            faces_detected = len(faces)

            frame_deepfake_scores = []
            frame_temporal_scores = []

            if faces_detected > 0:
                for face in faces:
                    all_observed_track_ids.add(face.track_id)
                    # Extract face crop safely with boundary clamping
                    h, w = frame.image_bgr.shape[:2]
                    fx1 = max(0, face.x)
                    fy1 = max(0, face.y)
                    fx2 = min(w, face.x + face.width)
                    fy2 = min(h, face.y + face.height)

                    face_crop = frame.image_bgr[fy1:fy2, fx1:fx2]
                    if face_crop.size == 0:
                        continue

                    # Maintain temporal sequence for this face track
                    face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                    crops_history = track_crops_history.setdefault(face.track_id, [])
                    crops_history.append(face_rgb)

                    # Deepfake Model Inference on spatiotemporal face sequence via 3D-CNN
                    score = self.classifier.score_face_sequence(crops_history)
                    frame_deepfake_scores.append(score)

                    # Temporal Inconsistency against previous frame of same track
                    prev_crop = last_face_by_track.get(face.track_id)
                    temp_score = self.temporal_analyzer.analyze_temporal_inconsistency(prev_crop, face_crop)
                    frame_temporal_scores.append(temp_score)

                    # Update last observed crop for this track
                    last_face_by_track[face.track_id] = face_crop
            else:
                # No face detected in frame; evaluate full frame as baseline
                frame_rgb = frame.image_rgb
                score = self.classifier.score_face_crop(frame_rgb)
                frame_deepfake_scores.append(score * 0.5)  # Scale down non-face confidence
                frame_temporal_scores.append(0.05)

            # Determine composite scores for this frame
            avg_deepfake = float(np.mean(frame_deepfake_scores)) if frame_deepfake_scores else 0.05
            avg_temporal = float(np.mean(frame_temporal_scores)) if frame_temporal_scores else 0.05
            composite_frame_anomaly = float(np.clip(0.65 * avg_deepfake + 0.35 * avg_temporal, 0.0, 1.0))

            is_suspicious = composite_frame_anomaly >= 0.60 or avg_deepfake >= 0.70

            frame_scores.append(VideoFrameScore(
                frame_index=frame.frame_index,
                timestamp_seconds=frame.timestamp_seconds,
                deepfake_score=round(avg_deepfake, 4),
                temporal_inconsistency=round(avg_temporal, 4),
                faces_detected=faces_detected,
                is_suspicious=is_suspicious
            ))

            if is_suspicious:
                reason = "HIGH_SYNTHETIC_FACE_PROBABILITY" if avg_deepfake >= 0.70 else "TEMPORAL_DISCONTINUITY"
                suspicious_timestamps.append(SuspiciousTimestamp(
                    timestamp_seconds=frame.timestamp_seconds,
                    frame_index=frame.frame_index,
                    score=round(composite_frame_anomaly, 4),
                    reason=reason
                ))

        # 3. Aggregate Video Deepfake Probability
        # Weighted combination of 90th percentile peak frame anomaly and mean anomaly
        all_deepfake_scores = [fs.deepfake_score for fs in frame_scores]
        all_temporal_scores = [fs.temporal_inconsistency for fs in frame_scores]

        p90_deepfake = float(np.percentile(all_deepfake_scores, 90)) if all_deepfake_scores else 0.0
        mean_deepfake = float(np.mean(all_deepfake_scores)) if all_deepfake_scores else 0.0
        p90_temporal = float(np.percentile(all_temporal_scores, 90)) if all_temporal_scores else 0.0

        aggregate_score = 0.50 * p90_deepfake + 0.25 * mean_deepfake + 0.25 * p90_temporal
        deepfake_prob = float(np.clip(aggregate_score, 0.0, 1.0))

        evidence = VideoAnalysisEvidence(
            face_count=len(all_observed_track_ids),
            total_frames_sampled=len(sampled_frames),
            duration_seconds=duration_seconds,
            frame_scores=frame_scores,
            suspicious_timestamps=suspicious_timestamps,
            details={
                "p90_deepfake": round(p90_deepfake, 4),
                "mean_deepfake": round(mean_deepfake, 4),
                "p90_temporal": round(p90_temporal, 4),
                "active_face_tracks": list(all_observed_track_ids),
            }
        )

        return VideoAnalysisResult(
            deepfake_prob=round(deepfake_prob, 4),
            face_count=len(all_observed_track_ids),
            total_frames_sampled=len(sampled_frames),
            suspicious_timestamps=suspicious_timestamps,
            frame_scores=frame_scores,
            model_name=self.classifier.model_name,
            model_version=self.classifier.model_version,
            evidence=evidence,
            status="COMPLETED"
        )
