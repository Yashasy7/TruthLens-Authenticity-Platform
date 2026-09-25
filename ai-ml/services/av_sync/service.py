"""
TruthLens AI/ML — Module 08: Audio-Visual Synchronization Pipeline Orchestration
Blueprint: End-to-end multi-modal pipeline coordinating video decoding, audio demuxing,
lip tracking, acoustic envelope cross-correlation, SyncNet metric evaluation, and forensic reporting.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any, List
import numpy as np

from config.settings import get_settings
from schemas.av_sync import (
    BackendAvSyncResponse,
    AvSyncEvidence,
    MismatchSegment,
    LegacyAvSyncAnalysisResponse,
)
from services.audio_analysis.features import compute_mel_spectrogram
from services.av_sync.ingestion import decode_video_and_extract_audio
from services.av_sync.lip_tracker import extract_lip_motion_timeline
from services.av_sync.correlator import (
    compute_audio_envelope,
    resample_to_video_timeline,
    compute_cross_correlation,
)
from services.av_sync.syncnet import SyncNetEvaluator
from services.av_sync.alignment import (
    compute_composite_sync_score,
    scan_mismatch_segments,
    compute_temporal_drift,
)

logger = logging.getLogger(__name__)

# Cached evaluator instance
_syncnet_evaluator: Optional[SyncNetEvaluator] = None


def get_syncnet_evaluator() -> SyncNetEvaluator:
    """Retrieve or lazily initialize the singleton SyncNetEvaluator instance."""
    global _syncnet_evaluator
    if _syncnet_evaluator is None:
        settings = get_settings()
        _syncnet_evaluator = SyncNetEvaluator(
            checkpoint_path=settings.av_sync_classifier_checkpoint,
            require_checkpoint=settings.require_av_sync_checkpoint,
        )
    return _syncnet_evaluator


def analyze_av_sync_bytes(
    video_bytes: bytes,
    filename: str = "upload.mp4",
) -> BackendAvSyncResponse:
    """
    Perform forensic audio-visual synchronization analysis on raw video file bytes.

    Pipeline execution:
        1. Decode video frames at target FPS and demux 16kHz mono audio.
        2. Detect speaker face, track primary subject, crop mouth ROIs, and extract lip activity timeline.
        3. Extract acoustic speech envelope and compute 80-band log-Mel spectrogram.
        4. Calculate normalized cross-correlation across temporal lag range (-500 ms to +500 ms).
        5. Evaluate cross-modal Euclidean distances using SyncNet dual-stream architecture.
        6. Compute composite synchronization score, confidence, and temporal drift.
        7. Run sliding window forensic mismatch scanner to isolate anomalous intervals.
        8. Construct strictly backend-compatible BackendAvSyncResponse.

    Args:
        video_bytes: Raw binary content of the video file.
        filename: Original or temporary filename for extension hint.

    Returns:
        BackendAvSyncResponse: Complete forensic analysis payload.
    """
    settings = get_settings()
    evaluator = get_syncnet_evaluator()

    # Step 1: Decode video frames and demux audio
    media = decode_video_and_extract_audio(
        source=video_bytes,
        filename=filename,
        target_fps=settings.av_sync_fps,
        max_duration_seconds=settings.av_sync_max_duration_seconds,
    )

    duration = media.duration_seconds
    total_frames = media.total_frames
    fps = media.fps

    # Edge Case A: Video has no audio track
    if not media.has_audio or len(media.audio_waveform) == 0:
        logger.warning(f"Video '{filename}' has no detectable audio track")
        evidence = AvSyncEvidence(
            detected_faces_count=0,
            selected_face_track_id=-1,
            video_duration_seconds=duration,
            audio_duration_seconds=0.0,
            fps=fps,
            envelope_correlation=0.0,
            syncnet_min_distance=1.414,
            syncnet_confidence=0.0,
            tracking_stability=0.0,
            is_development_model=not evaluator.is_production_checkpoint,
            audio_track_present=False,
            face_detected=False,
            cross_correlation_score=0.0,
            syncnet_distance=1.414,
            total_frames_analyzed=total_frames,
            temporal_drift_score=0.0,
            sync_status="NO_AUDIO_TRACK",
        )
        mismatch = [
            MismatchSegment(
                start_time=0.0,
                end_time=duration,
                offset_ms=0.0,
                confidence=1.0,
                reason="Video container has no readable audio track for synchronization analysis",
                severity="HIGH",
            )
        ]
        return BackendAvSyncResponse(
            sync_score=0.0,
            lip_offset_ms=0.0,
            confidence=1.0,
            mismatch_segments=mismatch,
            model_name=evaluator.model_name,
            model_version=evaluator.model_version,
            evidence=evidence,
            status="COMPLETED",
        )

    # Step 2: Visual lip tracking & mouth ROI extraction
    visual_features = extract_lip_motion_timeline(
        frames=media.frames,
        timestamps=media.frame_timestamps,
        mouth_crop_size=settings.av_sync_mouth_crop_size,
    )

    has_face = visual_features.face_detected_ratio >= 0.25

    # Edge Case B: No face detected in video
    if not has_face:
        logger.warning(f"No face detected in video '{filename}'")
        evidence = AvSyncEvidence(
            detected_faces_count=0,
            selected_face_track_id=-1,
            video_duration_seconds=duration,
            audio_duration_seconds=media.audio_duration,
            fps=fps,
            envelope_correlation=0.0,
            syncnet_min_distance=1.414,
            syncnet_confidence=0.0,
            tracking_stability=0.0,
            is_development_model=not evaluator.is_production_checkpoint,
            audio_track_present=True,
            face_detected=False,
            cross_correlation_score=0.0,
            syncnet_distance=1.414,
            total_frames_analyzed=total_frames,
            temporal_drift_score=0.0,
            sync_status="NO_FACE_DETECTED",
        )
        mismatch = [
            MismatchSegment(
                start_time=0.0,
                end_time=duration,
                offset_ms=0.0,
                confidence=0.9,
                reason="No face or visible mouth detected in video frames",
                severity="MEDIUM",
            )
        ]
        return BackendAvSyncResponse(
            sync_score=0.0,
            lip_offset_ms=0.0,
            confidence=0.9,
            mismatch_segments=mismatch,
            model_name=evaluator.model_name,
            model_version=evaluator.model_version,
            evidence=evidence,
            status="COMPLETED",
        )


    # Step 3: Acoustic envelope & log-Mel spectrogram
    audio_times, raw_audio_env = compute_audio_envelope(
        waveform=media.audio_waveform,
        sr=media.audio_sample_rate,
        hop_length=256,
    )

    # Resample audio activity envelope onto exact video frame timestamps
    resampled_audio_env = resample_to_video_timeline(
        source_times=audio_times,
        source_values=raw_audio_env,
        target_times=media.frame_timestamps,
    )

    log_mel, _, _, _ = compute_mel_spectrogram(
        waveform=media.audio_waveform,
        sr=media.audio_sample_rate,
        n_fft=1024,
        hop_length=256,
        n_mels=80,
    )

    # Step 4: Temporal cross-correlation between audio envelope and lip activity
    (
        corr_offset_ms,
        peak_corr,
        corr_confidence,
        lags_ms,
        corr_curve,
    ) = compute_cross_correlation(
        audio_signal=resampled_audio_env,
        visual_signal=visual_features.lip_activity_curve,
        fps=fps,
        max_offset_ms=settings.av_sync_max_offset_ms,
    )

    # Step 5: SyncNet metric evaluation
    syncnet_results = evaluator.evaluate_video_audio(
        mouth_crops=visual_features.mouth_crops,
        log_mel=log_mel,
        fps=fps,
        max_shift_frames=int(round(settings.av_sync_max_offset_ms / (1000.0 / fps))),
    )

    syncnet_offset_ms = syncnet_results["best_offset_ms"]
    syncnet_min_dist = syncnet_results["min_distance"]
    syncnet_conf = syncnet_results["confidence"]

    # Step 6: Fusion & composite scoring
    # Weigh offset: envelope correlation has higher temporal resolution for syllable envelope,
    # SyncNet verifies cross-modal phoneme-viseme alignment.
    if corr_confidence >= 0.35 and syncnet_conf >= 0.35:
        # Fuse estimates weighted by relative confidence
        total_w = corr_confidence + syncnet_conf
        final_offset_ms = round(
            (corr_offset_ms * corr_confidence + syncnet_offset_ms * syncnet_conf) / total_w, 1
        )
    elif corr_confidence >= 0.35:
        final_offset_ms = corr_offset_ms
    elif syncnet_conf >= 0.35:
        final_offset_ms = syncnet_offset_ms
    else:
        # Both low confidence -> default to cross-correlation
        final_offset_ms = corr_offset_ms

    has_mouth_motion = visual_features.mean_lip_motion > 0.05
    has_speech_audio = float(np.mean(resampled_audio_env)) > 0.08

    sync_score, overall_confidence, sync_status = compute_composite_sync_score(
        best_offset_ms=final_offset_ms,
        peak_correlation=peak_corr,
        syncnet_min_distance=syncnet_min_dist,
        syncnet_confidence=syncnet_conf,
        has_face=has_face,
        has_audio=True,
        has_mouth_movement=has_mouth_motion,
        has_speech_audio=has_speech_audio,
    )

    # Step 7: Temporal drift & localized mismatch scanning
    drift_score = compute_temporal_drift(
        timestamps=media.frame_timestamps,
        visual_signal=visual_features.lip_activity_curve,
        audio_signal=resampled_audio_env,
        fps=fps,
    )

    mismatch_segments = scan_mismatch_segments(
        timestamps=media.frame_timestamps,
        visual_signal=visual_features.lip_activity_curve,
        audio_signal=resampled_audio_env,
        face_detected_mask=visual_features.face_detected_mask,
        window_duration=settings.av_sync_window_seconds,
        step_duration=settings.av_sync_step_seconds,
        fps=fps,
    )

    # Step 8: Build Evidence & Assemble Final Backend Response
    evidence = AvSyncEvidence(
        detected_faces_count=visual_features.detected_faces_count,
        selected_face_track_id=0 if has_face else -1,
        video_duration_seconds=duration,
        audio_duration_seconds=media.audio_duration,
        fps=fps,
        envelope_correlation=peak_corr,
        syncnet_min_distance=syncnet_min_dist,
        syncnet_confidence=syncnet_conf,
        tracking_stability=visual_features.tracking_stability,
        is_development_model=not evaluator.is_production_checkpoint,
        audio_track_present=True,
        face_detected=True,
        cross_correlation_score=peak_corr,
        syncnet_distance=syncnet_min_dist,
        total_frames_analyzed=total_frames,
        temporal_drift_score=drift_score,
        sync_status=sync_status,
    )

    return BackendAvSyncResponse(
        sync_score=sync_score,
        lip_offset_ms=final_offset_ms,
        confidence=overall_confidence,
        mismatch_segments=mismatch_segments,
        model_name=evaluator.model_name,
        model_version=evaluator.model_version,
        evidence=evidence,
        status="COMPLETED",
    )


def analyze_av_sync_from_path(video_path: str) -> LegacyAvSyncAnalysisResponse:
    """
    Analyze video from a local filesystem path for legacy endpoint compatibility.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    backend_resp = analyze_av_sync_bytes(video_bytes, filename=os.path.basename(video_path))

    return LegacyAvSyncAnalysisResponse(
        video_path=video_path,
        sync_score=backend_resp.sync_score,
        lip_offset_ms=backend_resp.lip_offset_ms,
        confidence=backend_resp.confidence,
        mismatch_segments=backend_resp.mismatch_segments,
        model_name=backend_resp.model_name,
        model_version=backend_resp.model_version,
        evidence=backend_resp.evidence,
        status=backend_resp.status,
    )
