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
from typing import Optional
from uuid import UUID, uuid4

from config.settings import settings
from schemas.audio_analysis import (
    AudioAnalysisStatus,
    AudioEvidence,
    AudioSpliceMarker,
    BackendAudioAnalysisResponse,
    LegacyAudioAnalysisResponse,
)
from services.audio_analysis.features import extract_acoustic_features
from services.audio_analysis.ingestion import load_and_preprocess_audio
from services.audio_analysis.model import get_audio_classifier
from services.audio_analysis.phase_spectral import analyze_phase_and_spectral_forensics
from services.audio_analysis.pitch import extract_pitch_contour
from services.audio_analysis.splicing import detect_audio_splices
from services.audio_analysis.temporal import evaluate_temporal_audio_windows

logger = logging.getLogger(__name__)

AUDIO_SCOPE_LIMITATION = (
    "AASIST-L is trained on ASVspoof2019 Logical Access data and is not a universal "
    "detector for all modern commercial voice-cloning or post-processed audio."
)


def classify_audio_authenticity(
    checkpoint_loaded: bool,
    synthetic_voice_prob: Optional[float],
    splice_markers: list[AudioSpliceMarker],
    phase_discontinuity: float,
    duration_seconds: float,
    voiced_fraction: float,
) -> tuple[str, str]:
    """
    Derive an evidence-grounded assessment category and verbal summary while preserving
    strict separation between the AASIST-L classifier output and physical heuristics.

    Categories:
      - Likely Authentic
      - Potentially Synthetic Voice
      - Potentially Spliced
      - Inconclusive
    """
    if not checkpoint_loaded or synthetic_voice_prob is None:
        return (
            "Inconclusive",
            "Inconclusive (Model Unavailable): pretrained AASIST-L checkpoint is not loaded; "
            "handcrafted acoustic heuristics alone cannot determine synthetic voice authenticity.",
        )

    if duration_seconds < 0.5 or voiced_fraction <= 0.0:
        return (
            "Inconclusive",
            "Inconclusive: insufficient voiced speech or audio duration to reliably evaluate voice authenticity.",
        )

    has_splices = len(splice_markers) > 0
    if synthetic_voice_prob >= 0.50 and has_splices:
        return (
            "Potentially Synthetic Voice",
            "Potentially Synthetic Voice: AASIST-L indicates elevated spoof likelihood alongside "
            f"{len(splice_markers)} heuristic splice boundary indicator(s). {AUDIO_SCOPE_LIMITATION}",
        )

    if synthetic_voice_prob >= 0.50:
        return (
            "Potentially Synthetic Voice",
            f"Potentially Synthetic Voice: AASIST-L spoof probability is elevated ({synthetic_voice_prob:.2%}). "
            f"{AUDIO_SCOPE_LIMITATION}",
        )

    if has_splices:
        return (
            "Potentially Spliced",
            f"Potentially Spliced: AASIST-L spoof probability is low ({synthetic_voice_prob:.2%}), "
            f"but {len(splice_markers)} abrupt acoustic discontinuity marker(s) were detected.",
        )

    if synthetic_voice_prob >= 0.25 or phase_discontinuity >= 0.50:
        return (
            "Inconclusive",
            "Inconclusive: borderline AASIST-L score or elevated STFT phase discontinuity does not support "
            "a definitive authenticity classification.",
        )

    return (
        "Likely Authentic",
        f"Likely Authentic (within benchmark scope): AASIST-L spoof probability is low ({synthetic_voice_prob:.2%}) "
        f"with no heuristic splice or severe phase anomalies detected. {AUDIO_SCOPE_LIMITATION}",
    )


def analyze_audio_bytes(
    audio_bytes: bytes,
    filename: str = "audio.wav",
) -> BackendAudioAnalysisResponse:
    """
    Execute full Module 07 Audio Authenticity & Voice Forensics pipeline
    directly from uploaded binary audio bytes.
    """
    start_time = time.monotonic()
    logger.info("Initiating audio authenticity analysis | filename=%s size=%d bytes", filename, len(audio_bytes))

    if not audio_bytes:
        raise ValueError("Audio payload cannot be empty (0 bytes).")

    # Stage 1: Ingestion & Format Validation (WAV, FLAC, OGG, MP3 -> 16 kHz mono float32)
    waveform, meta = load_and_preprocess_audio(
        audio_bytes,
        target_sr=settings.audio_sample_rate,
        filename=filename,
    )

    # Stage 2: Acoustic Features & Mel-Spectrogram
    features = extract_acoustic_features(
        waveform,
        sr=settings.audio_sample_rate,
        n_fft=settings.audio_n_fft,
        hop_length=settings.audio_hop_length,
        n_mels=settings.audio_n_mels,
    )

    # Persist Mel-spectrogram PNG artifact safely
    spectrogram_filename = f"{uuid4()}.png"
    spectrogram_dir = settings.storage_dir / "spectrogram"
    spectrogram_dir.mkdir(parents=True, exist_ok=True)
    spectrogram_path = spectrogram_dir / spectrogram_filename
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

    # Stage 5: Splice Boundary Detection (Heuristic acoustic discontinuity indicators)
    splice_markers = detect_audio_splices(
        features,
        phase_res,
        threshold=settings.audio_splice_threshold,
    )

    # Stage 6: Official Pretrained AASIST-L Classifier Inference
    classifier_model, model_metadata = get_audio_classifier()
    checkpoint_loaded = bool(model_metadata.get("checkpoint_loaded", False)) and classifier_model is not None

    if checkpoint_loaded:
        temporal_res = evaluate_temporal_audio_windows(
            waveform,
            sr=settings.audio_sample_rate,
            window_duration=settings.audio_window_duration_seconds,
            hop_duration=settings.audio_window_hop_seconds,
            model=classifier_model,
        )
        synthetic_voice_prob: Optional[float] = temporal_res.aggregate_synthetic_prob
        temporal_details = temporal_res.details
        response_status = AudioAnalysisStatus.COMPLETED.value
    else:
        synthetic_voice_prob = None
        temporal_details = {
            "window_count": 0,
            "checkpoint_loaded": False,
            "error": model_metadata.get("error") or "AASIST-L checkpoint unavailable",
        }
        response_status = AudioAnalysisStatus.MODEL_UNAVAILABLE.value

    verdict_category, forensic_verdict = classify_audio_authenticity(
        checkpoint_loaded=checkpoint_loaded,
        synthetic_voice_prob=synthetic_voice_prob,
        splice_markers=splice_markers,
        phase_discontinuity=phase_res.phase_discontinuity_score,
        duration_seconds=meta.duration_seconds,
        voiced_fraction=pitch_res.voiced_fraction,
    )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "Audio analysis finished in %dms | status=%s checkpoint_loaded=%s synth_prob=%s pitch_var=%.2f splices=%d",
        elapsed_ms,
        response_status,
        checkpoint_loaded,
        f"{synthetic_voice_prob:.4f}" if synthetic_voice_prob is not None else "None",
        pitch_res.pitch_variance,
        len(splice_markers),
    )

    evidence_details = {
        "format": meta.format_name,
        "channels": meta.channels,
        "original_sample_rate": meta.original_sample_rate,
        "processed_sample_rate": meta.sample_rate,
        "total_samples": meta.samples,
        "voiced_fraction": round(pitch_res.voiced_fraction, 4),
        "spectral_anomaly_score": round(phase_res.spectral_anomaly_score, 4),
        "high_freq_attenuation_ratio": round(phase_res.high_freq_attenuation_ratio, 4),
        "processing_time_ms": elapsed_ms,
        "checkpoint_loaded": checkpoint_loaded,
        "architecture": model_metadata.get("architecture", "AASIST-L"),
        "class_mapping": model_metadata.get("class_mapping", {"0": "spoof", "1": "bonafide"}),
        "verdict_category": verdict_category,
        "forensic_verdict": forensic_verdict,
        "limitations_note": AUDIO_SCOPE_LIMITATION,
        "heuristics_disclaimer": (
            "Pitch variance, STFT phase discontinuity, and splice markers are acoustic forensic "
            "indicators supporting review and are kept independent from neural spoof probability."
        ),
        "temporal": temporal_details,
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
        synthetic_voice_prob=synthetic_voice_prob,
        spectrogram_url=spectrogram_url,
        spectrogram_base64=features.spectrogram_base64,
        pitch_variance=round(pitch_res.pitch_variance, 4),
        splice_markers=splice_markers,
        model_name=model_metadata.get("model_name", settings.audio_model_name),
        model_version=model_metadata.get("model_version", settings.audio_model_version),
        evidence=evidence,
        status=response_status,
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

    legacy_status = (
        AudioAnalysisStatus.MODEL_UNAVAILABLE
        if backend_res.status == AudioAnalysisStatus.MODEL_UNAVAILABLE.value
        else AudioAnalysisStatus.COMPLETED
    )

    return LegacyAudioAnalysisResponse(
        media_id=media_id,
        synthetic_voice_prob=backend_res.synthetic_voice_prob,
        spectrogram_url=backend_res.spectrogram_url,
        spectrogram_base64=backend_res.spectrogram_base64,
        pitch_variance=backend_res.pitch_variance,
        phase_discontinuity=backend_res.evidence.phase_discontinuity_score,
        splice_markers=backend_res.splice_markers,
        processing_time_ms=elapsed_ms,
        status=legacy_status,
        error_message=backend_res.evidence.details.get("forensic_verdict")
        if legacy_status == AudioAnalysisStatus.MODEL_UNAVAILABLE
        else None,
    )
