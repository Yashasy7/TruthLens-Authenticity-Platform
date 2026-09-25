import os
import cv2
import numpy as np
import librosa
from typing import List, Dict, Any, Optional, Tuple
from ..config import settings
from ..schemas import MismatchSegment, AvSyncEvidence, AvSyncAnalysisResult
from .ffmpeg_sampler import FFmpegVideoSampler
from .mediapipe_lip_tracker import MediaPipeLipTracker, LipTrackingResult
from .audio_envelope_correlator import AudioEnvelopeCorrelator
from .syncnet_evaluator import SyncNetEvaluator


class AvSyncAnalysisPipeline:
    """
    End-to-End Audio-Video Synchronization Analysis Pipeline.
    
    Adheres to TruthLens Blueprint Module 08 specification:
    Video + Audio Tracks
            ↓
    MediaPipe Lip Tracker + Audio Envelope Correlator
            ↓
    SyncNet Evaluator
            ↓
    AV Sync Score + Mismatch Timestamps
    
    Produces explainable, deterministic evidence for dubbing detection, replaced
    audio tracks, and lip-sync deepfakes.
    """

    def __init__(
        self,
        lip_tracker: Optional[MediaPipeLipTracker] = None,
        envelope_correlator: Optional[AudioEnvelopeCorrelator] = None,
        syncnet_evaluator: Optional[SyncNetEvaluator] = None,
    ):
        self.lip_tracker = lip_tracker or MediaPipeLipTracker()
        self.envelope_correlator = envelope_correlator or AudioEnvelopeCorrelator()
        self.syncnet_evaluator = syncnet_evaluator or SyncNetEvaluator()
        self.target_fps = settings.AV_SYNC_FPS
        self.window_duration = settings.AV_SYNC_WINDOW_SECONDS
        self.step_duration = settings.AV_SYNC_STEP_SECONDS

    def analyze_video(self, video_path: str) -> AvSyncAnalysisResult:
        """
        Executes complete audio-video synchronization forensic analysis on an uploaded video.
        
        Args:
            video_path: Local filesystem path to the video asset.
            
        Returns:
            Structured AvSyncAnalysisResult containing sync_score, lip_offset_ms,
            mismatch_segments, and explainable evidence.
            
        Raises:
            ValueError: If media is not a valid video or lacks an audio stream.
        """
        if not os.path.isfile(video_path):
            raise ValueError(f"Video file not found: {video_path}")

        # 1. Validate video container and extract video frames
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Unable to decode video stream. File may be corrupt or an unsupported container.")

        native_fps = cap.get(cv2.CAP_PROP_FPS)
        total_native_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if native_fps <= 0 or np.isnan(native_fps):
            native_fps = 25.0

        native_duration = total_native_frames / native_fps if total_native_frames > 0 else 0.0

        # Deterministic frame sampling at target_fps (25 fps) up to max duration
        max_duration = min(float(settings.AV_SYNC_MAX_DURATION_SECONDS), native_duration if native_duration > 0 else 60.0)
        frames_to_sample = int(min(max_duration * self.target_fps, 1500))  # Max 1500 frames = 60s at 25fps

        frames_rgb: List[np.ndarray] = []
        timestamps: List[float] = []

        # Read frames evenly spaced at 1.0 / target_fps
        frame_interval = max(1, int(round(native_fps / self.target_fps)))
        frame_count = 0
        read_count = 0

        while cap.isOpened() and len(frames_rgb) < frames_to_sample:
            ret, bgr_frame = cap.read()
            if not ret or bgr_frame is None:
                break
            if frame_count % frame_interval == 0:
                rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                frames_rgb.append(rgb_frame)
                timestamps.append(round(frame_count / native_fps, 4))
                read_count += 1
            frame_count += 1

        cap.release()

        if len(frames_rgb) == 0:
            raise ValueError("Video contains zero valid image frames.")

        video_duration = timestamps[-1] if timestamps else 0.0

        # 2. Extract audio track from video container (validates audio presence)
        temp_audio_path = None
        try:
            temp_audio_path = self.envelope_correlator.extract_audio_from_video(video_path)
            
            # Load extracted audio
            y_audio, sr = librosa.load(
                temp_audio_path,
                sr=settings.AUDIO_SAMPLE_RATE,
                mono=True,
                duration=max_duration
            )
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except OSError:
                    pass

        if len(y_audio) == 0:
            raise ValueError("Audio track in video contains zero audio samples.")

        audio_duration = len(y_audio) / float(sr)

        # 3. MediaPipe Lip Tracking
        lip_result = self.lip_tracker.track_lips(frames_rgb, timestamps)

        # 4. Audio Envelope Extraction and Cross-Correlation
        target_ts_array = np.array(timestamps, dtype=np.float32)
        audio_envelope = self.envelope_correlator.compute_audio_envelope(
            waveform=y_audio,
            sample_rate=sr,
            target_timestamps=target_ts_array
        )

        best_offset_ms, env_corr, env_confidence, lags_ms, correlations = self.envelope_correlator.correlate(
            lip_activity=lip_result.lip_activity,
            audio_envelope=audio_envelope,
            fps=self.target_fps
        )

        # 5. Extract Mel-spectrogram for SyncNet evaluation
        hop_length = int(sr * 0.010)  # 10ms hop
        mel_spec = librosa.feature.melspectrogram(
            y=y_audio,
            sr=sr,
            n_fft=1024,
            hop_length=hop_length,
            n_mels=80,
            fmax=sr // 2
        )
        mel_db = librosa.power_to_db(mel_spec, ref=np.max)

        # 6. SyncNet Two-Stream Evaluation
        syncnet_result = self.syncnet_evaluator.evaluate_sync(
            lip_crops=lip_result.lip_crops,
            mel_spectrogram=mel_db,
            fps=self.target_fps,
            audio_hop_sec=0.010
        )

        # 7. Compute Composite Score and Temporal Alignment
        sync_score, global_offset_ms, overall_confidence = self._compute_composite_sync(
            env_offset_ms=best_offset_ms,
            env_corr=env_corr,
            env_confidence=env_confidence,
            syncnet_offset_ms=syncnet_result["best_offset_ms"],
            syncnet_min_dist=syncnet_result["min_distance"],
            syncnet_confidence=syncnet_result["confidence"],
            tracking_stability=lip_result.tracking_stability
        )

        # 8. Detect Granular Mismatch Segments
        mismatch_segments = self._detect_mismatch_segments(
            timestamps=timestamps,
            lip_activity=lip_result.lip_activity,
            audio_envelope=audio_envelope,
            global_offset_ms=global_offset_ms,
            tracking_stability=lip_result.tracking_stability,
            lip_frame_data=lip_result.frame_lip_data
        )

        evidence = AvSyncEvidence(
            detected_faces_count=lip_result.detected_faces_count,
            selected_face_track_id=lip_result.primary_track_id,
            video_duration_seconds=round(video_duration, 3),
            audio_duration_seconds=round(audio_duration, 3),
            fps=self.target_fps,
            envelope_correlation=env_corr,
            syncnet_min_distance=syncnet_result["min_distance"],
            syncnet_confidence=syncnet_result["confidence"],
            tracking_stability=lip_result.tracking_stability,
            is_development_model=self.syncnet_evaluator.is_development_model,
            details={
                "envelope_best_offset_ms": best_offset_ms,
                "envelope_confidence": env_confidence,
                "syncnet_best_offset_ms": syncnet_result["best_offset_ms"],
                "syncnet_distances_by_shift": syncnet_result["distances_by_shift"],
                "total_frames_analyzed": len(frames_rgb),
                "audio_samples_analyzed": len(y_audio),
            }
        )

        return AvSyncAnalysisResult(
            sync_score=round(sync_score, 4),
            lip_offset_ms=round(global_offset_ms, 2),
            confidence=round(overall_confidence, 4),
            mismatch_segments=mismatch_segments,
            model_name=self.syncnet_evaluator.model_name,
            model_version=self.syncnet_evaluator.model_version,
            evidence=evidence,
            status="COMPLETED"
        )

    def _compute_composite_sync(
        self,
        env_offset_ms: float,
        env_corr: float,
        env_confidence: float,
        syncnet_offset_ms: float,
        syncnet_min_dist: float,
        syncnet_confidence: float,
        tracking_stability: float,
    ) -> Tuple[float, float, float]:
        """
        Combines envelope correlation and SyncNet metric distance into a unified
        sync score (0.0 to 1.0) and optimal offset.
        
        Scoring convention:
        - 1.0 = Highly synchronized (offset near 0ms, strong positive correlation, minimal SyncNet distance).
        - 0.0 = Severe desync, audio replacement, or dubbing.
        """
        # Weighted offset consensus
        w_env = max(0.1, env_confidence)
        w_sync = max(0.1, syncnet_confidence)
        total_w = w_env + w_sync
        consensus_offset_ms = (env_offset_ms * w_env + syncnet_offset_ms * w_sync) / total_w

        # Offset penalty: tolerance of 80ms (human perceptual threshold is ~45ms to 100ms)
        abs_offset = abs(consensus_offset_ms)
        if abs_offset <= 60.0:
            offset_factor = 1.0
        elif abs_offset <= 200.0:
            offset_factor = 1.0 - ((abs_offset - 60.0) / 140.0) * 0.45
        elif abs_offset <= 400.0:
            offset_factor = 0.55 - ((abs_offset - 200.0) / 200.0) * 0.35
        else:
            offset_factor = 0.20

        # Correlation factor: map correlation [-1.0, 1.0] to [0.0, 1.0]
        corr_factor = max(0.0, min(1.0, (env_corr + 0.5) / 1.5))

        # SyncNet distance factor: distance in [0.0, 2.0], lower is better
        dist_factor = max(0.0, min(1.0, 1.0 - (syncnet_min_dist / 2.0)))

        # Composite score
        raw_score = (offset_factor * 0.40) + (corr_factor * 0.35) + (dist_factor * 0.25)
        
        # Penalize if tracking stability was poor
        if tracking_stability < 0.30:
            raw_score *= (0.5 + tracking_stability * 1.5)

        sync_score = float(np.clip(raw_score, 0.0, 1.0))

        # Overall confidence
        confidence = float(np.clip((env_confidence * 0.4) + (syncnet_confidence * 0.3) + (tracking_stability * 0.3), 0.0, 1.0))

        return sync_score, consensus_offset_ms, confidence

    def _detect_mismatch_segments(
        self,
        timestamps: List[float],
        lip_activity: np.ndarray,
        audio_envelope: np.ndarray,
        global_offset_ms: float,
        tracking_stability: float,
        lip_frame_data: List[Any],
    ) -> List[MismatchSegment]:
        """
        Scans temporal sliding windows to identify localized synchronization breaks,
        audible speech without mouth movement, or mouth motion without audio.
        """
        n = min(len(timestamps), len(lip_activity), len(audio_envelope))
        if n < 5:
            return []

        segments: List[MismatchSegment] = []
        fps = self.target_fps
        window_frames = int(max(5, round(self.window_duration * fps)))
        step_frames = int(max(2, round(self.step_duration * fps)))

        for i in range(0, n - window_frames + 1, step_frames):
            w_ts_start = timestamps[i]
            w_ts_end = timestamps[i + window_frames - 1]
            w_lip = lip_activity[i : i + window_frames]
            w_audio = audio_envelope[i : i + window_frames]
            w_frames = lip_frame_data[i : i + window_frames]

            mean_lip = float(np.mean(w_lip))
            mean_audio = float(np.mean(w_audio))
            local_stability = float(np.mean([1.0 if f.mouth_bbox is not None else 0.0 for f in w_frames]))

            reason = None
            conf = 0.70

            # Condition 1: Tracking loss / occlusion
            if local_stability < 0.25:
                reason = "Visual face tracking lost or heavily occluded"
                conf = 0.65

            # Condition 2: Active speech without mouth motion (Voice-over / Dubbing)
            elif mean_audio > 0.35 and mean_lip < 0.10:
                reason = "Active speech audio detected without corresponding visual lip motion (dubbing signature)"
                conf = 0.85

            # Condition 3: Mouth motion without audio (Muted / Replaced audio)
            elif mean_lip > 0.40 and mean_audio < 0.08:
                reason = "Active visual speech visemes detected without acoustic speech energy"
                conf = 0.80

            # Condition 4: Localized temporal offset anomaly
            elif abs(global_offset_ms) > 150.0 and mean_audio > 0.20 and mean_lip > 0.20:
                reason = f"Persistent AV temporal offset anomaly ({global_offset_ms:+.1f} ms)"
                conf = 0.75

            if reason:
                # Merge with previous segment if contiguous or overlapping
                if segments and segments[-1].reason == reason and abs(segments[-1].end_time - w_ts_start) <= (self.step_duration * 1.5):
                    prev = segments[-1]
                    prev.end_time = round(w_ts_end, 3)
                    prev.confidence = max(prev.confidence, conf)
                else:
                    segments.append(
                        MismatchSegment(
                            start_time=round(w_ts_start, 3),
                            end_time=round(w_ts_end, 3),
                            offset_ms=round(global_offset_ms, 2),
                            confidence=round(conf, 4),
                            reason=reason
                        )
                    )

        return segments
