"""
TruthLens AI/ML — Module 10: Speech-to-Text FastAPI Endpoints
Blueprint Section L: POST /api/v1/analyze/speech-to-text multipart endpoint
                     matching Spring Boot FastApiTranscriptServiceClient.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from config.settings import settings
from schemas.transcript import (
    BackendTranscriptResponse,
    LegacyTranscriptAnalysisRequest,
    LegacyTranscriptAnalysisResponse,
)
from services.transcript.engine import FASTER_WHISPER_AVAILABLE
from services.transcript.service import (
    analyze_speech_to_text_bytes,
    analyze_speech_to_text_from_path,
)

logger = logging.getLogger(__name__)

# Primary V1 API router aligned with Spring Boot FastApiTranscriptServiceClient
transcript_v1_router = APIRouter(tags=["Module 10 — Speech-to-Text"])

# Legacy / diagnostic router for internal health checks and batch testing
transcript_router = APIRouter(tags=["Speech-to-Text"])


@transcript_v1_router.post(
    "/api/v1/analyze/speech-to-text",
    response_model=BackendTranscriptResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe speech from audio or video media into timestamped text (Module 10)",
    description=(
        "Primary TruthLens Spring Boot gateway contract. Accepts a raw audio or video file "
        "as multipart/form-data with field 'file', normalizes audio to 16 kHz mono WAV, "
        "and produces timestamped transcript segments with word-level alignments and language detection."
    ),
)
async def analyze_speech_to_text_v1(
    file: UploadFile = File(..., description="Binary audio or video file"),
    language: Optional[str] = Form(None, description="Optional ISO language code override (e.g. 'en')"),
) -> BackendTranscriptResponse:
    """Primary multipart endpoint called by Spring Boot FastApiTranscriptServiceClient."""
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded media file stream: {exc}",
        )

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded media file is empty (0 bytes).",
        )

    filename = file.filename or "media.wav"

    try:
        response = analyze_speech_to_text_bytes(
            file_bytes=content,
            filename=filename,
            content_type=file.content_type,
            language=language,
        )
        return response
    except ValueError as val_err:
        logger.warning("Invalid or corrupt media uploaded for STT: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as r_err:
        logger.error("ASR engine runtime error: %s", r_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(r_err),
        )
    except Exception as exc:
        logger.exception("Unexpected error during speech transcription: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech transcription pipeline error: {exc}",
        )


@transcript_router.post(
    "/api/stt/analyze",
    response_model=LegacyTranscriptAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Path-based speech transcription (Legacy / Batch testing)",
)
def analyze_stt_legacy(
    request: LegacyTranscriptAnalysisRequest,
) -> LegacyTranscriptAnalysisResponse:
    """Legacy path-based transcription for batch scripts."""
    try:
        res = analyze_speech_to_text_from_path(
            media_path=request.media_path,
            language=request.language,
        )
        return LegacyTranscriptAnalysisResponse(
            full_text=res.full_text,
            language=res.language,
            confidence_score=res.confidence_score,
            duration_seconds=res.duration_seconds,
            segments_count=res.segments_count,
            words_count=res.words_count,
            segments=res.segments,
            evidence=res.evidence,
            status=res.status,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@transcript_router.get(
    "/api/stt/health",
    status_code=status.HTTP_200_OK,
    summary="Module 10 STT liveness & Faster-Whisper capability probe",
)
def stt_health() -> dict:
    """Liveness probe reporting model configuration and ASR readiness."""
    return {
        "status": "healthy",
        "module": "10-speech-to-text",
        "model_name": settings.whisper_model_name,
        "model_size": settings.whisper_model_size,
        "compute_type": settings.whisper_compute_type,
        "device": settings.whisper_device,
        "faster_whisper_available": FASTER_WHISPER_AVAILABLE,
        "active_engine": "Faster-Whisper" if FASTER_WHISPER_AVAILABLE else "AcousticEnergyTranscriber",
    }


@transcript_router.get(
    "/api/transcript/health",
    status_code=status.HTTP_200_OK,
    summary="Module 10 transcript diagnostic probe",
)
def transcript_health() -> dict:
    """Alias diagnostic probe for transcript pipeline."""
    return stt_health()
