"""
TruthLens AI/ML — Module 08: Audio-Visual Synchronization FastAPI Router
Blueprint: Audio-Visual Synchronization / Lip-Sync Forensics
Spring Boot Gateway Contract: POST /api/v1/analyze/av-sync
Legacy / Internal Router: POST /api/av-sync/analyze, GET /api/av-sync/health
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from config.settings import settings
from schemas.av_sync import (
    BackendAvSyncResponse,
    LegacyAvSyncAnalysisResponse,
    AvSyncAnalysisRequest,
)
from services.av_sync.service import (
    analyze_av_sync_bytes,
    analyze_av_sync_from_path,
    get_syncnet_evaluator,
)

logger = logging.getLogger(__name__)

# Legacy internal router (/api/av-sync)
av_sync_router = APIRouter(
    prefix="/api/av-sync",
    tags=["Audio-Visual Synchronization — Module 08"],
)

# Spring Boot backend aligned contract router (/api/v1)
av_sync_v1_router = APIRouter(
    prefix="/api/v1",
    tags=["Module 08 — Spring Boot Contract (/api/v1/analyze/av-sync)"],
)


@av_sync_v1_router.post(
    "/analyze/av-sync",
    response_model=BackendAvSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Audio-Visual Synchronization (Spring Boot Backend Contract)",
    description=(
        "Primary endpoint invoked by Spring Boot FastApiAvSyncServiceClient. "
        "Consumes multipart/form-data with binary 'file' field and executes "
        "lip tracking, audio envelope cross-correlation, SyncNet metric evaluation, "
        "and localized mismatch segment detection."
    ),
)
async def analyze_av_sync_v1_endpoint(
    file: UploadFile = File(..., description="Uploaded video file (.mp4, .avi, .mov, etc.)"),
) -> BackendAvSyncResponse:
    """
    POST /api/v1/analyze/av-sync

    Multipart handler reading binary video content and returning BackendAvSyncResponse DTO.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File parameter is required.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded video stream: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded video stream: {exc}",
        ) from exc

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video file is empty (0 bytes).",
        )

    try:
        response = analyze_av_sync_bytes(content, filename=file.filename or "video.mp4")
        return response
    except ValueError as exc:
        logger.warning("Invalid or corrupt video uploaded: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error analyzing audio-visual synchronization")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal AV synchronization error: {exc}",
        ) from exc


@av_sync_router.post(
    "/analyze",
    response_model=LegacyAvSyncAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute path-based AV synchronization analysis (Legacy / Internal)",
    description="Internal debug/batch endpoint accepting JSON with media_id and local video_path.",
)
def analyze_av_sync_legacy_endpoint(
    request: AvSyncAnalysisRequest,
) -> LegacyAvSyncAnalysisResponse:
    """
    POST /api/av-sync/analyze

    Accepts JSON body: { "video_path": "/path/to/video.mp4", "media_id": "optional" }
    """
    try:
        return analyze_av_sync_from_path(video_path=request.video_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Legacy AV sync analysis pipeline failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AV sync analysis failed: {exc}",
        ) from exc


@av_sync_router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="AV Synchronization Service Health & Model Status",
    description="Returns current operational status of Module 08 Audio-Visual Synchronization and model configuration.",
)
def av_sync_health_check() -> dict:
    """
    GET /api/av-sync/health
    """
    try:
        evaluator = get_syncnet_evaluator()
        model_ready = True
        error_msg = None
        model_name = evaluator.model_name
        model_version = evaluator.model_version
        checkpoint_loaded = evaluator.is_production_checkpoint
    except Exception as exc:
        model_ready = False
        error_msg = str(exc)
        model_name = settings.av_sync_model_name
        model_version = settings.av_sync_model_version
        checkpoint_loaded = False

    return {
        "status": "healthy" if model_ready else "degraded",
        "module": "08-av-synchronization",
        "model_ready": model_ready,
        "model_name": model_name,
        "model_version": model_version,
        "checkpoint_loaded": checkpoint_loaded,
        "require_checkpoint": settings.require_av_sync_checkpoint,
        "target_fps": settings.av_sync_fps,
        "window_seconds": settings.av_sync_window_seconds,
        "mouth_crop_size": settings.av_sync_mouth_crop_size,
        "error": error_msg,
    }
