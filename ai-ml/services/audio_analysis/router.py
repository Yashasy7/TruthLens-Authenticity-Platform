"""
TruthLens AI/ML — Audio Authenticity & Voice Forensics FastAPI Router
Blueprint Section G: POST /api/audio/analyze [INTERNAL / API]
Spring Boot Gateway Contract: POST /api/v1/analyze/audio
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from config.settings import settings
from schemas.audio_analysis import (
    AudioAnalysisRequest,
    AudioAnalysisStatus,
    BackendAudioAnalysisResponse,
    LegacyAudioAnalysisResponse,
)
from services.audio_analysis.model import get_audio_classifier
from services.audio_analysis.service import (
    analyze_audio_bytes,
    analyze_audio_from_path,
)

logger = logging.getLogger(__name__)

# Legacy internal router (/api/audio)
audio_router = APIRouter(
    prefix="/api/audio",
    tags=["Audio Analysis — Module 07"],
)

# Spring Boot backend aligned contract router (/api/v1)
audio_v1_router = APIRouter(
    prefix="/api/v1",
    tags=["Module 07 — Spring Boot Contract (/api/v1/analyze/audio)"],
)


@audio_v1_router.post(
    "/analyze/audio",
    response_model=BackendAudioAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze audio authenticity & voice forensics (Spring Boot Backend Contract)",
    description=(
        "Primary endpoint invoked by Spring Boot FastApiAudioAiServiceClient. "
        "Consumes multipart/form-data with binary 'file' field and executes the "
        "full AASIST / Mel-spectrogram / pitch variance / voice cloning evaluation pipeline."
    ),
)
async def analyze_audio_v1_endpoint(
    file: UploadFile = File(..., description="Uploaded audio file to analyze (.wav, .mp3, .flac, etc.)"),
) -> BackendAudioAnalysisResponse:
    """
    POST /api/v1/analyze/audio

    Multipart handler reading binary audio bytes and returning FastApiAudioAnalysisResponse DTO.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File parameter is required.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded audio stream: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded audio stream: {exc}",
        )

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes).",
        )

    try:
        response = analyze_audio_bytes(content, filename=file.filename or "audio.wav")
        return response
    except ValueError as exc:
        logger.warning("Invalid or corrupt audio uploaded: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error analyzing audio in v1 endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal audio analysis error: {exc}",
        ) from exc


@audio_router.post(
    "/analyze",
    response_model=LegacyAudioAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute path-based audio authenticity analysis (Legacy / Internal)",
    description="Internal debug/batch endpoint accepting JSON with media_id and local audio_path.",
)
def analyze_audio_legacy_endpoint(
    request: AudioAnalysisRequest,
) -> LegacyAudioAnalysisResponse:
    """
    POST /api/audio/analyze

    Accepts JSON body: { "media_id": "...", "audio_path": "/path/to/audio.wav" }
    """
    try:
        return analyze_audio_from_path(
            media_id=request.media_id,
            audio_path=request.audio_path,
        )
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
        logger.exception("Legacy audio analysis pipeline failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio analysis failed: {exc}",
        ) from exc


@audio_router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Audio Service Health & Model Status",
    description="Returns current operational status of Module 07 Audio Authenticity and model configuration.",
)
def audio_health_check() -> dict:
    """
    GET /api/audio/health
    """
    try:
        _, metadata = get_audio_classifier()
        model_ready = True
        error_msg = None
    except Exception as exc:
        model_ready = False
        error_msg = str(exc)
        metadata = {}

    return {
        "status": "healthy" if model_ready else "degraded",
        "module": "07-audio-authenticity",
        "model_ready": model_ready,
        "model_name": metadata.get("model_name", settings.audio_model_name),
        "model_version": metadata.get("model_version", settings.audio_model_version),
        "checkpoint_loaded": metadata.get("checkpoint_loaded", False),
        "require_checkpoint": settings.require_audio_checkpoint,
        "sample_rate": settings.audio_sample_rate,
        "n_mels": settings.audio_n_mels,
        "error": error_msg,
    }
