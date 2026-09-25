"""
TruthLens AI/ML — Module 07: Audio Authenticity & Voice Forensics Service Orchestrator
Blueprint: Module 07 — Audio Authenticity & Voice Forensics pipeline
           Module 19 — Consumed internally via Spring Boot FastApiAudioAiServiceClient
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
import time
from typing import Optional, Union
from uuid import UUID, uuid4

from config.settings import settings
from schemas.audio_analysis import (
    AudioAnalysisRequest,
    AudioAnalysisStatus,
    AudioEvidence,
    BackendAudioAnalysisResponse,
    LegacyAudioAnalysisResponse,
)
from services.audio_analysis.features import extract_acoustic_features
from services.audio_analysis.ingestion import (
    load_and_preprocess_audio,
    temp_audio_file,
)
from services.audio_analysis.model import get_audio_classifier
from services.audio_analysis.phase_spectral import analyze_phase_and_spectral_forensics
from services.audio_analysis.pitch import extract_pitch_contour
from services.audio_analysis.splicing import detect_audio_splices
from services.audio_analysis.temporal import evaluate_temporal_audio_windows

logger = logging.getLogger(__name__)


def analyze_audio_bytes(
    audio_bytes: bytes,
    filename: str = "audio.wav",
) -> BackendAudioAnalysisResponse:
    """
    Execute full Module 07 Audio Authenticity & Voice Forensics pipeline
    directly from uploaded binary audio bytes.

    Stages:
      1. Validation & deterministic audio decoding (mono, 16 kHz float32).
      2. Acoustic feature extraction & Mel-spectrogram generation (Base64 PNG).
      3. Fundamental frequency (F0) pitch contour & pitch variance analysis.
      4. Phase continuity & vocoder spectral anomaly forensics.
      5. Audio splice boundary discontinuity detection.
      6. Temporal windowing & PyTorch AASIST anti-spoofing inference.
      7. Assembly of structured AudioEvidence and Spring Boot compatible DTO.

    Args:
        audio_bytes: Raw binary audio bytes.
        filename: Optional source filename (default: audio.wav).

    Returns:
        BackendAudioAnalysisResponse matching Spring Boot FastApiAudioAnalysisResponse.
    """
    start_time = time.monotonic()
    logger.info("Initiating audio authenticity analysis | filename=%s size=%d bytes", filename, len(audio_bytes))

    if not audio_bytes:
        raise ValueError("Audio payload cannot be empty (0 bytes).")

    # Stage 1: Ingestion & Preprocessing
    waveform, meta = load_and_preprocess_audio(
        audio_bytes,
        target_sr=settings.audio_sample_rate,
    )

    # Stage 2: Acoustic Features & Mel-Spectrogram
    features = extract_acoustic_features(
        waveform,
        sr=settings.audio_sample_rate,
        n_fft=settings.audio_n_fft,
        hop_length=settings.audio_hop_length,
        n_mels=settings.audio_n_mels,
    )

    # Optional: Persist Mel-spectrogram PNG artifact to storage
    spectrogram_filename = f"{uuid4()}.png"
    spectrogram_path = settings.storage_dir / "spectrogram" / spectrogram_filename
    try:
        spectrogram_bytes = base64.b64decode(features.spectrogram_base64)
        spectrogram_path.write_bytes(spectrogram_bytes)
        spectrogram_url: Optional[str] = f"/storage/spectrogram/{spectrogram_filename}"
    except Exception as err:
        logger.warning("Could not persist spectrogram artifact to disk: %s", err)
        spectrogram_url = None

    # Stage 3: Pitch & Acoustic Variance
    pitch_res = extract_pitch_contour(
        waveform,
        sr=settings.audio_sample_rate,
    )

    # Stage 4: Phase Discontinuity & Spectral Forensics
    phase_res = analyze_phase_and_spectral_forensics(
        waveform,
        sr=settings.audio_sample_rate,
        n_fft=settings.audio_n_fft,
        hop_length=settings.audio_hop_length,
    )

    # Stage 5: Splice Boundary Detection
    splice_markers = detect_audio_splices(
        features,
        phase_res,
        threshold=settings.audio_splice_threshold,
    )

    # Stage 6: PyTorch AASIST Classifier Inference over Temporal Windows
    classifier_model, model_metadata = get_audio_classifier()
    temporal_res = evaluate_temporal_audio_windows(
        waveform,
        sr=settings.audio_sample_rate,
        window_duration=settings.audio_window_duration_seconds,
        hop_duration=settings.audio_window_hop_seconds,
        model=classifier_model,
    )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "Audio analysis completed in %dms | synthetic_prob=%.4f pitch_var=%.2f splices=%d",
        elapsed_ms,
        temporal_res.aggregate_synthetic_prob,
        pitch_res.pitch_variance,
        len(splice_markers),
    )

    evidence_details = {
        "channels": meta.channels,
        "original_sample_rate": meta.original_sample_rate,
        "processed_sample_rate": meta.sample_rate,
        "total_samples": meta.samples,
        "voiced_fraction": round(pitch_res.voiced_fraction, 4),
        "spectral_anomaly_score": round(phase_res.spectral_anomaly_score, 4),
        "high_freq_attenuation_ratio": round(phase_res.high_freq_attenuation_ratio, 4),
        "processing_time_ms": elapsed_ms,
        "temporal": temporal_res.details,
    }

    evidence = AudioEvidence(
        duration_seconds=round(meta.duration_seconds, 3),
        pitch_mean=round(pitch_res.pitch_mean, 2),
        pitch_variance=round(pitch_res.pitch_variance, 4),
        spectral_centroid_mean=round(features.spectral_centroid_mean, 2),
        spectral_bandwidth_mean=round(features.spectral_bandwidth_mean, 2),
        spectral_rolloff_mean=round(features.spectral_rolloff_mean, 2),
        zero_crossing_rate_mean=round(features.zero_crossing_rate_mean, 4),
        phase_discontinuity_score=round(phase_res.phase_discontinuity_score, 4),
        splice_markers=splice_markers,
        details=evidence_details,
    )

    return BackendAudioAnalysisResponse(
        synthetic_voice_prob=temporal_res.aggregate_synthetic_prob,
        spectrogram_url=spectrogram_url,
        spectrogram_base64=features.spectrogram_base64,
        pitch_variance=round(pitch_res.pitch_variance, 4),
        splice_markers=splice_markers,
        model_name=model_metadata.get("model_name", settings.audio_model_name),
        model_version=model_metadata.get("model_version", settings.audio_model_version),
        evidence=evidence,
        status="COMPLETED",
    )


def analyze_audio_from_path(
    media_id: UUID,
    audio_path: str,
) -> LegacyAudioAnalysisResponse:
    """
    Legacy internal service entrypoint executing audio analysis from a local file path.
    """
    start_time = time.monotonic()
    p = Path(audio_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Audio file does not exist: {p}")

    audio_bytes = p.read_bytes()
    backend_res = analyze_audio_bytes(audio_bytes, filename=p.name)
    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    return LegacyAudioAnalysisResponse(
        media_id=media_id,
        synthetic_voice_prob=backend_res.synthetic_voice_prob,
        spectrogram_url=backend_res.spectrogram_url,
        spectrogram_base64=backend_res.spectrogram_base64,
        pitch_variance=backend_res.pitch_variance,
        phase_discontinuity=backend_res.evidence.phase_discontinuity_score,
        splice_markers=backend_res.splice_markers,
        processing_time_ms=elapsed_ms,
        status=AudioAnalysisStatus.COMPLETED,
    )
