"""
TruthLens AI/ML — Image Analysis FastAPI Router
Blueprint Section G: POST /api/image/analyze  [INTERNAL / API]
  Description: "Execute PyTorch vision model & ELA heatmap generator."

This router is internal — called by Spring Boot backend (Module 19 job worker
or Module 02 integration).  No JWT auth is applied here; the Spring Boot
gateway is the authentication boundary (Blueprint Section D architecture).

Error response schema follows FastAPI defaults (RFC 7807 style):
  422 — Pydantic validation failure (malformed request body)
  400 — Semantic validation failure (image path invalid, unsupported format)
  500 — Unexpected internal server error
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from schemas.image_analysis import ImageAnalysisRequest, ImageAnalysisResponse, AnalysisStatus
from services.image_analysis.service import analyze_image

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/image",
    tags=["Image Analysis — Module 05"],
)


@router.post(
    "/analyze",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute image authenticity analysis (Module 05)",
    description=(
        "Runs the dual-engine image analysis pipeline: "
        "(1) PyTorch timm EfficientNet-B0 Diffusion/GAN classifier → synthetic_prob, "
        "(2) OpenCV ELA heatmap generator → manipulation_prob + ela_heatmap_url, "
        "(3) Noise variance & FFT anomaly calculator → noise_variance, "
        "(4) Grad-CAM attention exporter → grad_cam_url. "
        "Results feed Module 15 (Risk Scoring Engine) and Module 16 (Explainable Dashboard). "
        "Called internally by Module 19 (Processing Queue) via Spring Boot."
    ),
)
def analyze_image_endpoint(request: ImageAnalysisRequest) -> ImageAnalysisResponse:
    """
    POST /api/image/analyze

    Accepts a media_id (UUID) and image_path (storage path) and returns the
    full Module 05 analysis result JSON.
    """
    logger.info(
        "Received /api/image/analyze | media_id=%s image_path=%s",
        request.media_id,
        request.image_path,
    )

    try:
        result = analyze_image(request)
    except Exception as exc:
        logger.exception("Unexpected error in image analysis | media_id=%s", request.media_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal analysis error: {exc}",
        ) from exc

    # If the service returned a FAILED status due to a bad image path/format,
    # surface it as a 400 so the backend can distinguish user error vs server error.
    if result.status == AnalysisStatus.FAILED and result.error_message:
        if any(
            keyword in (result.error_message or "")
            for keyword in ("not found", "Unsupported", "Cannot decode", "Failed to open")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error_message,
            )

    return result


@router.get(
    "/health",
    summary="Image analysis service health check",
    status_code=status.HTTP_200_OK,
)
def health_check() -> dict:
    """GET /api/image/health — Liveness probe for Module 05 service."""
    return {"service": "image-analysis", "status": "ok"}
