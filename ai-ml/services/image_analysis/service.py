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
from uuid import UUID

from schemas.image_analysis import AnalysisStatus, ImageAnalysisRequest, ImageAnalysisResponse
from services.image_analysis.classifier import load_model, predict_synthetic
from services.image_analysis.ela import generate_ela
from services.image_analysis.gradcam import generate_gradcam
from services.image_analysis.noise import calculate_fft_high_freq_ratio, calculate_noise_variance
from utils.image_utils import (
    get_image_size,
    load_pil_image,
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
