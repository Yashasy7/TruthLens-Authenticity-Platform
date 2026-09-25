"""
TruthLens AI/ML — Video Deepfake Analysis FastAPI Router
Blueprint Section G: POST /api/video/analyze [INTERNAL / API]
Spring Boot Gateway Contract: POST /api/v1/analyze/video
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from schemas.video_analysis import (
    BackendVideoAnalysisResponse,
    LegacyVideoAnalysisResponse,
    VideoAnalysisRequest,
    VideoAnalysisStatus,
)
from services.video_analysis.service import (
    analyze_video_bytes,
    analyze_video_from_path,
)

logger = logging.getLogger(__name__)

# Legacy internal router
video_router = APIRouter(
    prefix="/api/video",
    tags=["Video Analysis — Module 06"],
)

# Spring Boot backend aligned contract router
video_v1_router = APIRouter(
    prefix="/api/v1",
    tags=["Module 06 — Spring Boot Contract (/api/v1/analyze/video)"],
)


@video_v1_router.post(
    "/analyze/video",
    response_model=BackendVideoAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze video deepfake authenticity (Spring Boot Backend Contract)",
    description=(
        "Primary endpoint invoked by Spring Boot FastApiVideoAiServiceClient. "
        "Consumes multipart/form-data with binary 'file' field and executes the "
        "full 3D-CNN / facial tracking / temporal deepfake evaluation pipeline."
    ),
)
async def analyze_video_v1_endpoint(
    file: UploadFile = File(..., description="Uploaded video file to analyze"),
) -> BackendVideoAnalysisResponse:
    """
    POST /api/v1/analyze/video

    Multipart handler reading binary video and returning FastApiVideoAnalysisResponse DTO.
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
        )

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video file is empty (0 bytes).",
        )

    try:
        response = analyze_video_bytes(content, filename=file.filename or "video.mp4")
        return response
    except ValueError as exc:
        logger.warning("Invalid or corrupt video uploaded: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error analyzing video in v1 endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal video analysis error: {exc}",
        ) from exc


@video_router.post(
    "/analyze",
    response_model=LegacyVideoAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute path-based video deepfake analysis (Legacy / Internal)",
)
def analyze_video_legacy_endpoint(request: VideoAnalysisRequest) -> LegacyVideoAnalysisResponse:
    """
    POST /api/video/analyze
    Path-based internal integration.
    """
    result = analyze_video_from_path(request)
    if result.status == VideoAnalysisStatus.FAILED and result.error_message:
        if "not found" in result.error_message or "Corrupted" in result.error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error_message,
            )
    return result


@video_router.get(
    "/health",
    summary="Video analysis service health check",
    status_code=status.HTTP_200_OK,
)
def video_health_check() -> dict:
    """GET /api/video/health — Liveness probe for Module 06 service."""
    return {"service": "video-analysis", "status": "ok"}
