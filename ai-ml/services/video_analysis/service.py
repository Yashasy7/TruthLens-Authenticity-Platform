"""
TruthLens AI/ML — Video Deepfake Analysis Orchestrator
Blueprint: Module 06 — Video Deepfake & Forensic Analysis pipeline
           Module 19 — Consumed internally via Spring Boot FastApiVideoAiServiceClient
"""

from __future__ import annotations

import logging
from pathlib import Path
import time

from config.settings import settings
from schemas.video_analysis import (
    BackendVideoAnalysisResponse,
    LegacyVideoAnalysisResponse,
    VideoAnalysisRequest,
    VideoAnalysisStatus,
    VideoEvidence,
)
from services.video_analysis.face_detector import extract_facial_tracks
from services.video_analysis.ingestion import (
    sample_video_frames,
    temp_video_file,
)
from services.video_analysis.model import (
    get_video_model_metadata,
    predict_video_clip,
)
from services.video_analysis.preprocessing import create_temporal_clip_tensor
from services.video_analysis.temporal import evaluate_temporal_timeline

logger = logging.getLogger(__name__)


def analyze_video_bytes(
    video_bytes: bytes,
    filename: str = "video.mp4",
) -> BackendVideoAnalysisResponse:
    """
    Execute full Module 06 Video Deepfake Analysis pipeline directly from uploaded binary bytes.

    Stages:
      1. Safe temporary file persistence & validation.
      2. Deterministic frame sampling via OpenCV/FFmpeg backend.
      3. Facial detection and boundary tracking.
      4. Face crop normalization & 5D temporal tensor assembly.
      5. PyTorch 3D-CNN temporal deepfake classification.
      6. Temporal inconsistency evaluation & timeline anomaly clustering.
      7. Assembly of structured VideoEvidence and Spring Boot compatible DTO.

    Args:
        video_bytes: Raw binary video stream.
        filename: Uploaded filename.

    Returns:
        BackendVideoAnalysisResponse matching Spring Boot FastApiVideoAnalysisResponse contract.
    """
    start_time = time.monotonic()
    logger.info("Initiating video deepfake analysis | filename=%s size=%d bytes", filename, len(video_bytes))

    # Stage 1 & 2: Ingestion & Deterministic Sampling
    with temp_video_file(video_bytes, filename=filename) as temp_path:
        metadata, sampled_frames = sample_video_frames(
            temp_path,
            max_frames=settings.video_max_sampled_frames,
        )

    # Stage 3: Face Detection & Tracking
    face_analyses = extract_facial_tracks(
        sampled_frames,
        target_size=(settings.video_crop_size, settings.video_crop_size),
    )

    face_counts = [fa.faces_detected for fa in face_analyses]
    max_faces = max(face_counts) if face_counts else 0

    # Stage 4: Temporal Tensor Preprocessing
    face_crops = [fa.primary_face.face_crop_rgb for fa in face_analyses]
    clip_length = min(16, max(4, len(face_crops)))
    clip_tensor = create_temporal_clip_tensor(
        face_crops,
        clip_length=clip_length,
        target_size=settings.video_crop_size,
    )

    # Stage 5: 3D-CNN Classifier Inference
    base_clip_score = predict_video_clip(clip_tensor)
    model_name, model_version = get_video_model_metadata()

    # Stage 6: Temporal Inconsistency & Timeline Marking
    deepfake_prob, frame_scores, suspicious_timestamps = evaluate_temporal_timeline(
        face_analyses,
        base_clip_score=base_clip_score,
        suspicious_threshold=0.50,
    )

    # Stage 7: Assemble Evidence DTO
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    evidence = VideoEvidence(
        face_count=max_faces,
        total_frames_sampled=len(sampled_frames),
        duration_seconds=metadata.duration_seconds,
        frame_scores=frame_scores,
        suspicious_timestamps=suspicious_timestamps,
        details={
            "fps": metadata.fps,
            "resolution": [metadata.width, metadata.height],
            "total_video_frames": metadata.frame_count,
            "base_clip_score": round(base_clip_score, 4),
            "processing_time_ms": elapsed_ms,
        },
    )

    response = BackendVideoAnalysisResponse(
        deepfake_prob=round(deepfake_prob, 4),
        face_count=max_faces,
        total_frames_sampled=len(sampled_frames),
        suspicious_timestamps=suspicious_timestamps,
        frame_scores=frame_scores,
        model_name=model_name,
        model_version=model_version,
        evidence=evidence,
        status="COMPLETED",
    )

    logger.info(
        "Completed video analysis | filename=%s deepfake_prob=%.4f faces=%d frames=%d anomalies=%d elapsed_ms=%d",
        filename,
        response.deepfake_prob,
        response.face_count,
        response.total_frames_sampled,
        len(response.suspicious_timestamps),
        elapsed_ms,
    )
    return response


def analyze_video_from_path(request: VideoAnalysisRequest) -> LegacyVideoAnalysisResponse:
    """
    Legacy path-based orchestrator for internal POST /api/video/analyze.
    """
    start_time = time.monotonic()
    video_path = Path(request.video_path)

    if not video_path.exists():
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return LegacyVideoAnalysisResponse(
            media_id=request.media_id,
            deepfake_prob=0.0,
            face_count=0,
            total_frames_sampled=0,
            suspicious_timestamps=[],
            processing_time_ms=elapsed_ms,
            status=VideoAnalysisStatus.FAILED,
            error_message=f"Video file not found at: {video_path}",
        )

    try:
        video_bytes = video_path.read_bytes()
        res = analyze_video_bytes(video_bytes, filename=video_path.name)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return LegacyVideoAnalysisResponse(
            media_id=request.media_id,
            deepfake_prob=res.deepfake_prob,
            face_count=res.face_count,
            total_frames_sampled=res.total_frames_sampled,
            suspicious_timestamps=res.suspicious_timestamps,
            processing_time_ms=elapsed_ms,
            status=VideoAnalysisStatus.COMPLETED,
            error_message=None,
        )
    except Exception as exc:
        logger.exception("Error executing legacy video analysis | media_id=%s", request.media_id)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return LegacyVideoAnalysisResponse(
            media_id=request.media_id,
            deepfake_prob=0.0,
            face_count=0,
            total_frames_sampled=0,
            suspicious_timestamps=[],
            processing_time_ms=elapsed_ms,
            status=VideoAnalysisStatus.FAILED,
            error_message=str(exc),
        )
