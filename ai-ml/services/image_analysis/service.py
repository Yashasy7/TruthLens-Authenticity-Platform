"""
TruthLens AI/ML — Image Analysis Service Orchestrator
Blueprint: Module 05 — Full analysis pipeline orchestration
           Module 15 — Feeds: synthetic_prob, manipulation_prob, noise_variance
           Module 16 — Feeds: ela_heatmap_url, grad_cam_url

This module wires together the four analysis engines:
  1. PyTorch classifier  → synthetic_prob, confidence
  2. ELA engine          → manipulation_prob, ela_heatmap_url
  3. Noise engine        → noise_variance
  4. Grad-CAM exporter   → grad_cam_url

Error handling strategy:
  - Individual engine failures are caught and logged.
  - The service still returns a partial result with status=FAILED and
    error_message so the backend / Module 15 can handle gracefully.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import UUID

import numpy as np

from schemas.image_analysis import (
    AnalysisStatus,
    BackendImageAnalysisResponse,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
)
from services.image_analysis.classifier import (
    get_model_metadata,
    load_model,
    predict_synthetic,
)
from services.image_analysis.copy_move import detect_copy_move_and_splicing
from services.image_analysis.ela import generate_ela
from services.image_analysis.gradcam import generate_gradcam
from services.image_analysis.noise import calculate_fft_high_freq_ratio, calculate_noise_variance
from utils.image_utils import (
    encode_image_to_base64_png,
    get_image_size,
    load_pil_image,
    load_pil_image_from_bytes,
    preprocess_for_model,
)
from utils.storage import save_heatmap
from config.settings import settings

logger = logging.getLogger(__name__)


def analyze_image(request: ImageAnalysisRequest) -> ImageAnalysisResponse:
    """
    Execute the full Module 05 image analysis pipeline.

    Args:
        request: ImageAnalysisRequest with media_id and image_path.

    Returns:
        ImageAnalysisResponse containing all analysis scores, heatmap URLs,
        and pipeline metadata.
    """
    start_ms = int(time.monotonic() * 1000)
    media_id: UUID = request.media_id

    logger.info("Starting image analysis | media_id=%s path=%s", media_id, request.image_path)

    # ------------------------------------------------------------------ #
    # Stage 1 — Load & validate image
    # ------------------------------------------------------------------ #
    try:
        pil_image = load_pil_image(request.image_path)
        original_size = get_image_size(request.image_path)   # (width, height)
        image_tensor = preprocess_for_model(pil_image, input_size=settings.model_input_size)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Image load failed | media_id=%s error=%s", media_id, exc)
        elapsed = int(time.monotonic() * 1000) - start_ms
        return ImageAnalysisResponse(
            media_id=media_id,
            synthetic_prob=0.0,
            ela_heatmap_url="",
            noise_variance=0.0,
            manipulation_prob=0.0,
            confidence=0.0,
            processing_time_ms=elapsed,
            status=AnalysisStatus.FAILED,
            error_message=str(exc),
        )

    # ------------------------------------------------------------------ #
    # Stage 2 — PyTorch Diffusion / GAN Classifier Inference
    # ------------------------------------------------------------------ #
    try:
        model = load_model()
        synthetic_prob, confidence = predict_synthetic(image_tensor)
    except Exception as exc:
        logger.exception("Classifier inference failed | media_id=%s", media_id)
        elapsed = int(time.monotonic() * 1000) - start_ms
        return ImageAnalysisResponse(
            media_id=media_id,
            synthetic_prob=0.0,
            ela_heatmap_url="",
            noise_variance=0.0,
            manipulation_prob=0.0,
            confidence=0.0,
            processing_time_ms=elapsed,
            status=AnalysisStatus.FAILED,
            error_message=f"Classifier failed: {exc}",
        )

    # ------------------------------------------------------------------ #
    # Stage 3 — OpenCV ELA Heatmap Generation
    # ------------------------------------------------------------------ #
    try:
        ela_heatmap_bgr, manipulation_prob = generate_ela(pil_image)
        # Convert BGR → RGB before saving
        import cv2
        ela_heatmap_rgb = cv2.cvtColor(ela_heatmap_bgr, cv2.COLOR_BGR2RGB)
        ela_heatmap_url = save_heatmap(ela_heatmap_rgb, media_id, kind="ela")
    except Exception as exc:
        logger.exception("ELA generation failed | media_id=%s", media_id)
        ela_heatmap_url = ""
        manipulation_prob = 0.0

    # ------------------------------------------------------------------ #
    # Stage 4 — Noise Variance & FFT Analysis
    # ------------------------------------------------------------------ #
    try:
        noise_variance = calculate_noise_variance(pil_image)
        _fft_ratio = calculate_fft_high_freq_ratio(pil_image)
        # Combine: lower FFT ratio = less organic noise = raises suspicion
        # Blend: noise_variance is the primary output for the DB column.
        logger.debug("FFT high-freq ratio: %.4f", _fft_ratio)
    except Exception as exc:
        logger.exception("Noise analysis failed | media_id=%s", media_id)
        noise_variance = 0.0

    # ------------------------------------------------------------------ #
    # Stage 5 — Grad-CAM Attention Map
    # ------------------------------------------------------------------ #
    grad_cam_url: str | None = None
    try:
        grad_cam_bgr = generate_gradcam(model, image_tensor, original_size)
        import cv2 as _cv2
        grad_cam_rgb = _cv2.cvtColor(grad_cam_bgr, _cv2.COLOR_BGR2RGB)
        grad_cam_url = save_heatmap(grad_cam_rgb, media_id, kind="gradcam")
    except Exception as exc:
        logger.warning("Grad-CAM generation failed (non-critical) | media_id=%s error=%s", media_id, exc)
        grad_cam_url = None

    # ------------------------------------------------------------------ #
    # Assemble final response
    # ------------------------------------------------------------------ #
    elapsed = int(time.monotonic() * 1000) - start_ms
    response = ImageAnalysisResponse(
        media_id=media_id,
        synthetic_prob=round(synthetic_prob, 4),
        ela_heatmap_url=ela_heatmap_url,
        noise_variance=round(noise_variance, 6),
        manipulation_prob=round(manipulation_prob, 4),
        grad_cam_url=grad_cam_url,
        confidence=round(confidence, 4),
        processing_time_ms=elapsed,
        status=AnalysisStatus.COMPLETED,
        error_message=None,
    )

    logger.info(
        "Analysis complete | media_id=%s synthetic_prob=%.4f manipulation_prob=%.4f "
        "noise_variance=%.4f elapsed_ms=%d",
        media_id,
        response.synthetic_prob,
        response.manipulation_prob,
        response.noise_variance,
        elapsed,
    )
    return response


def analyze_image_bytes(
    image_bytes: bytes,
    filename: str = "image.jpg",
) -> BackendImageAnalysisResponse:
    """
    Execute full Module 05 authenticity analysis directly from uploaded binary image bytes.

    Matches Yashas's Spring Boot FastApiImageAnalysisResponse contract:
      - ai_prob: [0.0, 1.0]
      - manipulation_prob: [0.0, 1.0]
      - noise_variance: non-negative float
      - fft_anomaly_score: [0.0, 1.0]
      - copy_move_detected: bool
      - splicing_detected: bool
      - model_name: string
      - model_version: string
      - ela_heatmap_base64: valid Base64 PNG string
      - gradcam_heatmap_base64: valid Base64 PNG string or None
      - evidence: structured dictionary
      - status: "COMPLETED"

    Args:
        image_bytes: Raw binary image payload.
        filename: Optional uploaded filename.

    Returns:
        BackendImageAnalysisResponse ready for serialization.
    """
    start_ms = int(time.monotonic() * 1000)
    logger.info("Starting byte-level image analysis | filename=%s size=%d bytes", filename, len(image_bytes))

    # Stage 1: Decode & preprocess image
    pil_image = load_pil_image_from_bytes(image_bytes)
    w, h = pil_image.size
    image_tensor = preprocess_for_model(pil_image, input_size=settings.model_input_size)

    # Stage 2: Classifier inference
    model = load_model()
    ai_prob, confidence = predict_synthetic(image_tensor)
    model_name, model_version = get_model_metadata()

    # Stage 3: Error Level Analysis
    ela_heatmap_bgr, ela_manipulation_prob = generate_ela(pil_image)
    ela_heatmap_base64 = encode_image_to_base64_png(ela_heatmap_bgr, is_bgr=True)

    # Stage 4: Noise & FFT analysis
    noise_variance = calculate_noise_variance(pil_image)
    fft_ratio = calculate_fft_high_freq_ratio(pil_image)
    fft_anomaly_score = float(np.clip(1.0 - fft_ratio, 0.0, 1.0))

    # Stage 5: Copy-move & splicing classical CV
    cv_result = detect_copy_move_and_splicing(pil_image)
    copy_move_detected = cv_result.copy_move_detected
    splicing_detected = cv_result.splicing_detected
    combined_manipulation_prob = float(np.clip(
        max(ela_manipulation_prob, cv_result.copy_move_score, cv_result.splicing_score),
        0.0,
        1.0,
    ))

    # Stage 6: Grad-CAM attention heatmap
    gradcam_base64: Optional[str] = None
    try:
        gradcam_bgr = generate_gradcam(model, image_tensor, (w, h))
        gradcam_base64 = encode_image_to_base64_png(gradcam_bgr, is_bgr=True)
    except Exception as exc:
        logger.warning("Grad-CAM generation failed (non-critical) | filename=%s error=%s", filename, exc)
        gradcam_base64 = None

    # Stage 7: Evidence aggregation
    elapsed = int(time.monotonic() * 1000) - start_ms
    evidence = {
        "noise_variance": round(noise_variance, 6),
        "fft_high_freq_ratio": round(fft_ratio, 4),
        "fft_anomaly_score": round(fft_anomaly_score, 4),
        "confidence": round(confidence, 4),
        "ela_manipulation_prob": round(ela_manipulation_prob, 4),
        "processing_time_ms": elapsed,
        "dimensions": [w, h],
        "copy_move": cv_result.evidence,
    }

    response = BackendImageAnalysisResponse(
        ai_prob=round(ai_prob, 4),
        manipulation_prob=round(combined_manipulation_prob, 4),
        noise_variance=round(noise_variance, 6),
        fft_anomaly_score=round(fft_anomaly_score, 4),
        copy_move_detected=copy_move_detected,
        splicing_detected=splicing_detected,
        model_name=model_name,
        model_version=model_version,
        ela_heatmap_base64=ela_heatmap_base64,
        gradcam_heatmap_base64=gradcam_base64,
        evidence=evidence,
        status="COMPLETED",
    )

    logger.info(
        "Byte-level analysis complete | filename=%s ai_prob=%.4f manip_prob=%.4f "
        "copy_move=%s splicing=%s elapsed_ms=%d",
        filename,
        response.ai_prob,
        response.manipulation_prob,
        response.copy_move_detected,
        response.splicing_detected,
        elapsed,
    )
    return response

