"""
TruthLens AI/ML — Module 09: OCR & Visual Text Extraction FastAPI Router
Blueprint: OCR Text Extraction
Spring Boot Gateway Contract: POST /api/v1/analyze/ocr
Legacy / Internal Router: POST /api/ocr/analyze, GET /api/ocr/health
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from config.settings import settings
from schemas.ocr import (
    BackendOcrResponse,
    LegacyOcrAnalysisResponse,
    LegacyOcrAnalysisRequest,
)
from services.ocr.engine import get_ocr_engine
from services.ocr.service import (
    analyze_ocr_bytes,
    analyze_ocr_from_path,
)

logger = logging.getLogger(__name__)

# Legacy internal router (/api/ocr)
ocr_router = APIRouter(
    prefix="/api/ocr",
    tags=["OCR Text Extraction — Module 09"],
)

# Spring Boot backend aligned contract router (/api/v1)
ocr_v1_router = APIRouter(
    prefix="/api/v1",
    tags=["Module 09 — Spring Boot Contract (/api/v1/analyze/ocr)"],
)


@ocr_v1_router.post(
    "/analyze/ocr",
    response_model=BackendOcrResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract visual text via OCR (Spring Boot Backend Contract)",
    description=(
        "Primary endpoint invoked by Spring Boot FastApiOcrServiceClient. "
        "Consumes multipart/form-data with binary 'file' field (image or video) and executes "
        "OpenCV preprocessing, multi-backend OCR (Tesseract / EasyOCR / morphological fallback), "
        "text region bounding box extraction, and chyron temporal consolidation."
    ),
)
async def analyze_ocr_v1_endpoint(
    file: UploadFile = File(..., description="Uploaded image or video file to extract text from"),
) -> BackendOcrResponse:
    """
    POST /api/v1/analyze/ocr

    Multipart handler reading binary media content and returning FastApiOcrResponse DTO.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File parameter is required.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded media stream: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded media stream: {exc}",
        ) from exc

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded media file is empty (0 bytes).",
        )

    try:
        response = analyze_ocr_bytes(content, filename=file.filename or "media.png")
        return response
    except ValueError as exc:
        logger.warning("Invalid or corrupt media uploaded for OCR: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error extracting visual text via OCR")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal OCR analysis error: {exc}",
        ) from exc


@ocr_router.post(
    "/analyze",
    response_model=LegacyOcrAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute path-based visual text extraction (Legacy / Internal)",
    description="Internal debug/batch endpoint accepting JSON with media_id and local media_path.",
)
def analyze_ocr_legacy_endpoint(
    request: LegacyOcrAnalysisRequest,
) -> LegacyOcrAnalysisResponse:
    """
    POST /api/ocr/analyze

    Accepts JSON body: { "media_path": "/path/to/media.png", "media_id": "optional" }
    """
    try:
        return analyze_ocr_from_path(media_path=request.media_path, media_id=request.media_id)
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
        logger.exception("Legacy OCR analysis pipeline failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR analysis failed: {exc}",
        ) from exc


@ocr_router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="OCR Service Health & Engine Status",
    description="Returns current operational status of Module 09 OCR Text Extraction and active backend engine.",
)
def ocr_health_check() -> dict:
    """
    GET /api/ocr/health
    """
    try:
        engine = get_ocr_engine()
        engine_ready = engine.is_available
        engine_name = engine.name
        error_msg = None
    except Exception as exc:
        engine_ready = False
        engine_name = "None"
        error_msg = str(exc)

    return {
        "status": "healthy" if engine_ready else "degraded",
        "module": "09-ocr-text-extraction",
        "engine_ready": engine_ready,
        "engine_name": engine_name,
        "configured_engine": settings.ocr_engine,
        "require_ocr_engine": settings.require_ocr_engine,
        "default_language": settings.ocr_languages,
        "confidence_threshold": settings.ocr_confidence_threshold,
        "max_image_dimension": settings.ocr_max_image_dimension,
        "error": error_msg,
    }
