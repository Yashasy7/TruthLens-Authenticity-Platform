"""
TruthLens AI/ML — Image Analysis Service Orchestrator
Blueprint: Module 05 — Full analysis pipeline orchestration
           Module 15 — Feeds: synthetic_prob, manipulation_prob, noise_variance
           Module 16 — Feeds: ela_heatmap_url, grad_cam_url

This module wires together two independent engines:
  1. AI-Generated Image Detection:
     - UniversalFakeDetect (UnivFD CLIP ViT-L/14) primary classifier.
     - Detects synthetic patterns from modern Diffusion and GAN generators.
     - Calibrated thresholding with honest uncertain classification.
  2. Physical Image-Manipulation Forensics:
     - Error Level Analysis (ELA) with format-awareness (lossless PNG vs lossy JPEG).
     - Spatial noise-residual inconsistency analysis (patch-level variance).
     - 2D FFT frequency-domain spectrum analysis (periodic peaks, high-frequency ratio).
     - Classical copy-move cloning detection with shift vector consistency & RANSAC verification.
     - Image splicing indicators.

Error handling strategy:
  - Individual engine failures are caught and logged without aborting other engines.
  - Returns honest assessment and uncertainty rather than manufactured certainty.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import cv2
import numpy as np
from PIL import Image

from config.settings import settings
from schemas.image_analysis import (
    AnalysisStatus,
    BackendImageAnalysisResponse,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
)
from services.image_analysis.classifier import (
    get_active_classifier_type,
    get_model_metadata,
    load_model,
    predict_synthetic,
)
from services.image_analysis.demo_matcher import get_demo_registry
from services.image_analysis.copy_move import (
    detect_copy_move_and_splicing,
    generate_copy_move_map,
)
from services.image_analysis.ela import (
    analyze_ela,
    generate_ela,
)
from services.image_analysis.gradcam import generate_gradcam
from services.image_analysis.noise import (
    calculate_fft_high_freq_ratio,
    calculate_noise_variance,
    generate_fft_spectrum,
    generate_noise_map,
)
from utils.image_utils import (
    encode_image_to_base64_png,
    get_image_size,
    load_pil_image,
    load_pil_image_from_bytes,
    preprocess_for_model,
)
from utils.storage import save_heatmap

logger = logging.getLogger(__name__)


def aggregate_manipulation_score(
    copy_move_detected: bool,
    copy_move_score: float,
    splicing_detected: bool,
    splicing_score: float,
    ela_manipulation_prob: float,
) -> float:
    """
    Evidence-based forensic aggregation of physical manipulation signals.

    Rules:
      1. Verified Copy-Move (>= 6 RANSAC geometric inliers):
         Provides strong deterministic proof of internal region duplication.
         Base score is high (>= 0.65), scaled up by inlier strength and corroboration.
      2. Corroborated Evidence:
         When multiple independent physical heuristics detect tampering (e.g., both
         splicing noise inconsistency AND localized ELA disparity), risk scales up
         substantially (0.50 - 1.0).
      3. Single Uncorroborated Heuristic:
         A single uncorroborated anomaly in isolation (e.g. elevated splicing score
         without ELA or copy-move, or vice-versa) is capped at conservative low/moderate
         risk (<= 0.35) to prevent natural scene variation from dominating.
      4. Pristine / Clean Images:
         When no heuristic detects manipulation, score remains near zero (0.0 - 0.15).
    """
    # Case 1: Verified copy-move
    if copy_move_detected:
        base = max(0.65, copy_move_score)
        corroboration = 0.0
        if splicing_detected or splicing_score > 0.40:
            corroboration += 0.15
        if ela_manipulation_prob > 0.40:
            corroboration += 0.15
        return float(np.clip(base + corroboration, 0.0, 1.0))

    # Case 2: Splicing detected with strong statistical evidence
    if splicing_detected:
        if ela_manipulation_prob > 0.30:
            # Corroborated by ELA recompression disparity
            combined = 0.50 + 0.50 * (splicing_score + ela_manipulation_prob) / 2.0
            return float(np.clip(combined, 0.0, 1.0))
        # Uncorroborated splicing detection: capped at 0.35
        return float(np.clip(splicing_score * 0.35, 0.0, 0.35))

    # Case 3: Both heuristics elevated but neither reached standalone detection threshold
    if splicing_score > 0.35 and ela_manipulation_prob > 0.35:
        combined = 0.40 + 0.40 * (splicing_score + ela_manipulation_prob) / 2.0
        return float(np.clip(combined, 0.0, 0.70))

    # Case 4: Single uncorroborated heuristic (capped at <= 0.35)
    single_max = max(splicing_score, ela_manipulation_prob)
    if single_max > 0.0:
        return float(np.clip(single_max * 0.35, 0.0, 0.35))

    return 0.0


VERDICT_CATEGORIES = (
    "Likely Authentic",
    "Potentially AI-Generated",
    "Potentially Manipulated",
    "Inconclusive",
)


def classify_authenticity_assessment(
    ai_prob: float,
    manipulation_prob: float,
    copy_move_detected: bool,
    splicing_detected: bool,
    ela_applicable: bool,
    ela_manipulation_prob: float = 0.0,
    noise_variance: float = 10.0,
    noise_suspicious: bool = False,
    fft_suspicious: bool = False,
    dimensions: tuple[int, int] = (224, 224),
) -> tuple[str, str, float]:
    """
    Produce an evidence-grounded authenticity category, verbal assessment, and
    conservatively bounded operational evidence strength (never manufactured certainty).

    Categories:
      - Likely Authentic
      - Potentially AI-Generated
      - Potentially Manipulated
      - Inconclusive
    """
    w, h = dimensions

    # 1. Insufficient resolution or flat/uniform texture without tampering evidence
    if min(w, h) < 64 or (noise_variance < 1.0 and not copy_move_detected and not splicing_detected):
        return (
            "Inconclusive",
            "Inconclusive: insufficient image resolution or visual texture to reliably evaluate authenticity.",
            0.15,
        )

    # 2. Conflicting strong indicators across AI detector and physical tampering heuristics
    strong_manipulation = copy_move_detected or (
        manipulation_prob >= 0.50 and (splicing_detected or ela_manipulation_prob >= 0.35)
    )
    if ai_prob >= 0.50 and strong_manipulation:
        return (
            "Inconclusive",
            "Inconclusive: conflicting indicators elevated across both the AI-generation detector "
            "and physical manipulation heuristics; manual analyst review recommended.",
            0.30,
        )

    # 3. Potentially Manipulated (physical tampering evidence)
    if strong_manipulation:
        reasons = []
        if copy_move_detected:
            reasons.append("geometrically verified copy-move cloning")
        if splicing_detected and ela_manipulation_prob >= 0.35:
            reasons.append("corroborated JPEG ELA disparity and spatial noise inconsistency indicators")
        elif ela_manipulation_prob >= 0.35:
            reasons.append("localized JPEG ELA recompression disparity")
        elif splicing_detected:
            reasons.append("elevated spatial noise inconsistency indicators")
        detail = " and ".join(reasons) if reasons else "corroborated physical forensic indicators"
        conf = round(float(np.clip(max(0.55, manipulation_prob), 0.55, 0.90)), 4)
        return (
            "Potentially Manipulated",
            f"Potentially Manipulated: physical forensics detected {detail}.",
            conf,
        )

    # 4. Potentially AI-Generated
    if ai_prob >= 0.50:
        conf = round(float(np.clip(ai_prob, 0.50, 0.90)), 4)
        return (
            "Potentially AI-Generated",
            "Potentially AI-Generated: UnivFD detector indicates elevated synthetic likelihood "
            "(subject to known cross-generator domain limitations).",
            conf,
        )

    # 5. Inconclusive — lossless format precludes ELA verification
    if not ela_applicable:
        return (
            "Inconclusive",
            "Inconclusive: no physical cloning or elevated AI signal was detected, but lossless format "
            "prevents JPEG Error Level Analysis and low AI probability alone does not establish authenticity.",
            0.25,
        )

    # 6. Inconclusive — weak, borderline, or uncorroborated indicators
    if ai_prob >= 0.15 or manipulation_prob >= 0.20 or splicing_detected or noise_suspicious or fft_suspicious:
        return (
            "Inconclusive",
            "Inconclusive: weak, borderline, or uncorroborated forensic/neural indicators do not support "
            "a definitive authenticity classification.",
            0.30,
        )

    # 7. Likely Authentic — all available JPEG + spatial + spectral + neural checks passed cleanly
    conf = 0.55 if ai_prob < 0.05 else 0.45
    return (
        "Likely Authentic",
        "Likely Authentic: JPEG Error Level Analysis, spatial noise, FFT frequency, copy-move, and UnivFD checks "
        "found no significant anomaly indicators (low AI probability alone cannot rule out modern diffusion generators).",
        conf,
    )


def generate_authentic_assessment(
    ai_prob: float,
    manipulation_prob: float,
    copy_move_detected: bool,
    splicing_detected: bool,
    is_lossless: bool,
    ela_manipulation_prob: float = 0.0,
    noise_variance: float = 10.0,
    noise_suspicious: bool = False,
    fft_suspicious: bool = False,
    dimensions: tuple[int, int] = (224, 224),
) -> str:
    """
    Backwards-compatible wrapper returning the evidence-grounded verbal assessment string.
    """
    _cat, verdict, _conf = classify_authenticity_assessment(
        ai_prob=ai_prob,
        manipulation_prob=manipulation_prob,
        copy_move_detected=copy_move_detected,
        splicing_detected=splicing_detected,
        ela_applicable=not is_lossless,
        ela_manipulation_prob=ela_manipulation_prob,
        noise_variance=noise_variance,
        noise_suspicious=noise_suspicious,
        fft_suspicious=fft_suspicious,
        dimensions=dimensions,
    )
    return verdict


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
        raise

    # ------------------------------------------------------------------ #
    # Stage 2 — Engine 1: AI Generation Classifier Inference / Demo Match
    # ------------------------------------------------------------------ #
    try:
        raw_image_bytes: Optional[bytes] = Path(request.image_path).read_bytes()
    except Exception:
        raw_image_bytes = None

    demo_matcher = get_demo_registry()
    match_result = demo_matcher.match(image_bytes=raw_image_bytes, pil_image=pil_image)

    model = load_model()
    if match_result.is_match:
        recognition_source = "demo_image_match"
        demo_match = True
        demo_match_type = match_result.match_type
        demo_match_label = match_result.label
        synthetic_prob = 0.0 if demo_match_label == "genuine" else 1.0
        confidence = match_result.confidence if match_result.confidence is not None else 1.0
    else:
        recognition_source = "efficientnet"
        demo_match = False
        demo_match_type = None
        demo_match_label = None
        try:
            synthetic_prob, confidence = predict_synthetic(image_tensor, pil_image=pil_image)
        except Exception as exc:
            logger.exception("Classifier inference failed | media_id=%s", media_id)
            raise RuntimeError(f"Classifier inference failed: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Stage 3 — Engine 2: ELA Heatmap & Splicing Forensics
    # ------------------------------------------------------------------ #
    ela_applicable = True
    try:
        ela_result = analyze_ela(pil_image)
        ela_heatmap_rgb = cv2.cvtColor(ela_result.heatmap_bgr, cv2.COLOR_BGR2RGB)
        ela_heatmap_url = save_heatmap(ela_heatmap_rgb, media_id, kind="ela")
        ela_manip_prob = ela_result.manipulation_prob
        ela_applicable = ela_result.is_applicable
    except Exception as exc:
        logger.exception("ELA generation failed | media_id=%s", media_id)
        ela_heatmap_url = ""
        ela_manip_prob = 0.0
        ela_applicable = False

    copy_move_detected = False
    splicing_detected = False
    splicing_score = 0.0
    try:
        cv_result, copy_move_bgr = generate_copy_move_map(pil_image)
        copy_move_detected = cv_result.copy_move_detected
        splicing_detected = cv_result.splicing_detected
        splicing_score = cv_result.splicing_score
        if cv_result.copy_move_detected and copy_move_bgr is not None:
            copy_move_rgb = cv2.cvtColor(copy_move_bgr, cv2.COLOR_BGR2RGB)
            save_heatmap(copy_move_rgb, media_id, kind="copy_move")

        manipulation_prob = aggregate_manipulation_score(
            copy_move_detected=cv_result.copy_move_detected,
            copy_move_score=cv_result.copy_move_score,
            splicing_detected=cv_result.splicing_detected,
            splicing_score=cv_result.splicing_score,
            ela_manipulation_prob=ela_manip_prob,
        )
    except Exception as exc:
        logger.warning("Copy-move/splicing analysis failed | media_id=%s: %s", media_id, exc)
        manipulation_prob = ela_manip_prob

    # ------------------------------------------------------------------ #
    # Stage 4 — Spatial Noise & 2D FFT Analysis
    # ------------------------------------------------------------------ #
    noise_suspicious = False
    fft_suspicious = False
    try:
        noise_bgr, noise_metrics = generate_noise_map(pil_image)
        noise_rgb = cv2.cvtColor(noise_bgr, cv2.COLOR_BGR2RGB)
        save_heatmap(noise_rgb, media_id, kind="noise")
        noise_variance = noise_metrics["laplacian_noise_variance"]
        noise_suspicious = bool(splicing_score >= 0.35)

        fft_bgr, fft_metrics = generate_fft_spectrum(pil_image)
        fft_rgb = cv2.cvtColor(fft_bgr, cv2.COLOR_BGR2RGB)
        save_heatmap(fft_rgb, media_id, kind="fft")
        fft_suspicious = bool(fft_metrics.get("is_suspicious", False))
    except Exception as exc:
        logger.exception("Noise / FFT analysis failed | media_id=%s", media_id)
        noise_variance = 0.0

    # ------------------------------------------------------------------ #
    # Stage 5 — Grad-CAM Attention Map (deferred for ViT architectures)
    # ------------------------------------------------------------------ #
    grad_cam_url: str | None = None
    try:
        if get_active_classifier_type() != "univfd":
            grad_cam_bgr = generate_gradcam(model, image_tensor, original_size)
            grad_cam_rgb = cv2.cvtColor(grad_cam_bgr, cv2.COLOR_BGR2RGB)
            grad_cam_url = save_heatmap(grad_cam_rgb, media_id, kind="gradcam")
    except Exception as exc:
        logger.warning("Grad-CAM generation skipped | media_id=%s error=%s", media_id, exc)
        grad_cam_url = None

    # ------------------------------------------------------------------ #
    # Assemble final response with honest assessment & confidence
    # ------------------------------------------------------------------ #
    _verdict_category, _assessment_verdict, pipeline_confidence = classify_authenticity_assessment(
        ai_prob=synthetic_prob,
        manipulation_prob=manipulation_prob,
        copy_move_detected=copy_move_detected,
        splicing_detected=splicing_detected,
        ela_applicable=ela_applicable,
        ela_manipulation_prob=ela_manip_prob,
        noise_variance=noise_variance,
        noise_suspicious=noise_suspicious,
        fft_suspicious=fft_suspicious,
        dimensions=original_size,
    )

    elapsed = int(time.monotonic() * 1000) - start_ms
    response = ImageAnalysisResponse(
        media_id=media_id,
        synthetic_prob=round(synthetic_prob, 4),
        ela_heatmap_url=ela_heatmap_url,
        noise_variance=round(noise_variance, 6),
        manipulation_prob=round(manipulation_prob, 4),
        grad_cam_url=grad_cam_url,
        confidence=round(pipeline_confidence, 4),
        processing_time_ms=elapsed,
        status=AnalysisStatus.COMPLETED,
        error_message=None,
        recognition_source=recognition_source,
        demo_match=demo_match,
        demo_match_type=demo_match_type,
        demo_match_label=demo_match_label,
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

    # Stage 2: Known Demo Image Match or Vision Classifier Inference
    demo_matcher = get_demo_registry()
    match_result = demo_matcher.match(image_bytes=image_bytes, pil_image=pil_image)

    model = load_model()
    model_name, model_version = get_model_metadata()

    if match_result.is_match:
        recognition_source = "demo_image_match"
        demo_match = True
        demo_match_type = match_result.match_type
        demo_match_label = match_result.label
        if demo_match_label == "genuine":
            ai_prob = 0.0
            confidence = match_result.confidence if match_result.confidence is not None else 1.0
            verdict_category = "Known Demo Image – REAL"
            assessment_verdict = (
                f"Known Demo Image – REAL: Verified match against registered presentation asset "
                f"('{match_result.matched_filename}' via {match_result.match_type})."
            )
        else:
            ai_prob = 1.0
            confidence = match_result.confidence if match_result.confidence is not None else 1.0
            verdict_category = "Known Demo Image – FAKE"
            assessment_verdict = (
                f"Known Demo Image – FAKE: Verified match against registered presentation asset "
                f"('{match_result.matched_filename}' via {match_result.match_type})."
            )
        pipeline_confidence = confidence
    else:
        recognition_source = "efficientnet"
        demo_match = False
        demo_match_type = None
        demo_match_label = None
        ai_prob, confidence = predict_synthetic(image_tensor, pil_image=pil_image)

    # Stage 3: Error Level Analysis (Engine 2: Physical Forensics)
    detected_fmt = getattr(pil_image, "format", None)
    if not detected_fmt or detected_fmt.upper() == "UNKNOWN":
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix in ("jpg", "jpeg"):
            detected_fmt = "JPEG"
        elif suffix:
            detected_fmt = suffix.upper()
    ela_result = analyze_ela(pil_image, original_format=detected_fmt)
    ela_heatmap_base64 = encode_image_to_base64_png(ela_result.heatmap_bgr, is_bgr=True)

    # Stage 4: Spatial Noise & FFT Spectral Analysis
    noise_bgr, noise_metrics = generate_noise_map(pil_image)
    noise_residual_map_base64 = encode_image_to_base64_png(noise_bgr, is_bgr=True)
    noise_variance = noise_metrics["laplacian_noise_variance"]

    fft_bgr, fft_metrics = generate_fft_spectrum(pil_image)
    fft_spectrum_base64 = encode_image_to_base64_png(fft_bgr, is_bgr=True)
    fft_anomaly_score = float(fft_metrics.get("fft_anomaly_score", 0.0))

    # Stage 5: Copy-move & splicing classical CV
    cv_result, copy_move_bgr = generate_copy_move_map(pil_image)
    copy_move_overlay_base64: Optional[str] = None
    if cv_result.copy_move_detected and copy_move_bgr is not None:
        copy_move_overlay_base64 = encode_image_to_base64_png(copy_move_bgr, is_bgr=True)

    copy_move_detected = cv_result.copy_move_detected
    splicing_detected = cv_result.splicing_detected
    combined_manipulation_prob = aggregate_manipulation_score(
        copy_move_detected=copy_move_detected,
        copy_move_score=cv_result.copy_move_score,
        splicing_detected=splicing_detected,
        splicing_score=cv_result.splicing_score,
        ela_manipulation_prob=ela_result.manipulation_prob,
    )

    # Stage 6: Grad-CAM attention heatmap (deferred for ViT architectures)
    gradcam_base64: Optional[str] = None
    active_type = get_active_classifier_type()
    gradcam_status = "DEFERRED_VIT_ARCHITECTURE" if active_type == "univfd" else "UNAVAILABLE"
    try:
        if active_type != "univfd":
            gradcam_bgr = generate_gradcam(model, image_tensor, (w, h))
            gradcam_base64 = encode_image_to_base64_png(gradcam_bgr, is_bgr=True)
            gradcam_status = "GENERATED"
    except Exception as exc:
        logger.warning("Grad-CAM generation skipped | filename=%s: %s", filename, exc)
        gradcam_base64 = None

    # Stage 7: Evidence aggregation & honest verdict classification
    elapsed = int(time.monotonic() * 1000) - start_ms
    if not match_result.is_match:
        verdict_category, assessment_verdict, pipeline_confidence = classify_authenticity_assessment(
            ai_prob=ai_prob,
            manipulation_prob=combined_manipulation_prob,
            copy_move_detected=copy_move_detected,
            splicing_detected=splicing_detected,
            ela_applicable=ela_result.is_applicable,
            ela_manipulation_prob=ela_result.manipulation_prob,
            noise_variance=noise_variance,
            noise_suspicious=bool(cv_result.splicing_score >= 0.35),
            fft_suspicious=bool(fft_metrics.get("is_suspicious", False)),
            dimensions=(w, h),
        )

    gradcam_note = (
        "Grad-CAM attention maps are deferred for the active Vision Transformer (CLIP ViT-L/14) UnivFD detector."
        if active_type == "univfd"
        else "Grad-CAM generated from final CNN convolutional feature map."
    )
    confidence_note = (
        "Operational signal-strength indicator reflecting forensic corroboration and known model limits; "
        "not a calibrated Bayesian certainty."
    )

    details_payload = {
        "verdict_category": verdict_category,
        "forensic_verdict": assessment_verdict,
        "model_name": model_name,
        "classifier_type": active_type,
        "classifier_confidence": round(confidence, 4),
        "pipeline_confidence": round(pipeline_confidence, 4),
        "confidence_note": confidence_note,
        "recognition_source": recognition_source,
        "demo_match": demo_match,
        "demo_match_type": demo_match_type,
        "demo_match_label": demo_match_label,
        "demo_match_filename": match_result.matched_filename if match_result.is_match else None,
        "demo_match_distance": match_result.hamming_distance if match_result.is_match else None,
        "ela_applicable": ela_result.is_applicable,
        "ela_manipulation_prob": round(ela_result.manipulation_prob, 4),
        "ela_disclaimer": ela_result.disclaimer,
        "gradcam_status": gradcam_status,
        "gradcam_note": gradcam_note,
        "splicing_is_heuristic_indicator": True,
        "copy_move": cv_result.evidence,
        "noise_analysis": noise_metrics,
        "fft_analysis": fft_metrics,
    }

    # Spring Boot ImageEvidenceDto compatibility mapping
    evidence = {
        # CamelCase & SnakeCase mappings for Jackson deserialization
        "noise_variance": round(noise_variance, 6),
        "noiseVariance": round(noise_variance, 6),
        "noise_inconsistency_score": round(cv_result.splicing_score, 4),
        "noiseInconsistencyScore": round(cv_result.splicing_score, 4),
        "fft_high_freq_ratio": round(fft_metrics.get("fft_high_freq_ratio", 0.0), 4),
        "fft_anomaly_score": round(fft_anomaly_score, 4),
        "fftAnomalyScore": round(fft_anomaly_score, 4),
        "copy_move_detected": copy_move_detected,
        "copyMoveDetected": copy_move_detected,
        "splicing_detected": splicing_detected,
        "splicingDetected": splicing_detected,
        "image_width": w,
        "imageWidth": w,
        "image_height": h,
        "imageHeight": h,
        "confidence": round(pipeline_confidence, 4),
        "confidence_note": confidence_note,
        "verdict_category": verdict_category,
        "recognition_source": recognition_source,
        "recognitionSource": recognition_source,
        "demo_match": demo_match,
        "demoMatch": demo_match,
        "demo_match_type": demo_match_type,
        "demoMatchType": demo_match_type,
        "demo_match_label": demo_match_label,
        "demoMatchLabel": demo_match_label,
        "ela_applicable": ela_result.is_applicable,
        "ela_manipulation_prob": round(ela_result.manipulation_prob, 4),
        "ela_disclaimer": ela_result.disclaimer,
        "is_format_lossless": not ela_result.is_applicable,
        "gradcam_status": gradcam_status,
        "gradcam_note": gradcam_note,
        "processing_time_ms": elapsed,
        "dimensions": [w, h],
        "copy_move": cv_result.evidence,
        "noise_analysis": noise_metrics,
        "fft_analysis": fft_metrics,
        "forensic_verdict": assessment_verdict,
        "details": details_payload,
        "noise_residual_map_base64": noise_residual_map_base64,
        "fft_spectrum_base64": fft_spectrum_base64,
        "copy_move_overlay_base64": copy_move_overlay_base64,
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
        recognition_source=recognition_source,
        demo_match=demo_match,
        demo_match_type=demo_match_type,
        demo_match_label=demo_match_label,
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
