"""
TruthLens AI/ML — Module 10: Speech-to-Text Service Orchestrator
Blueprint Section L: Orchestrates audio preprocessing, speech transcription,
                     segment normalization, and evidence packaging.
"""

from __future__ import annotations

import logging
from typing import Optional

from schemas.transcript import BackendTranscriptResponse
from services.transcript.engine import get_speech_transcriber
from services.transcript.preprocessor import SpeechPreprocessor

logger = logging.getLogger(__name__)


def analyze_speech_to_text_bytes(
    file_bytes: bytes,
    filename: str = "media.wav",
    content_type: Optional[str] = None,
    language: Optional[str] = None,
) -> BackendTranscriptResponse:
    """
    Primary orchestration entrypoint for multipart media uploads.
    
    Args:
        file_bytes: Raw binary payload of audio or video file.
        filename: Uploaded filename to determine format/extension.
        content_type: Optional MIME type from request header.
        language: Optional language code override (e.g., 'en', 'es').
        
    Returns:
        BackendTranscriptResponse matching Spring Boot DTO contract.
    """
    preprocessor = SpeechPreprocessor()
    preprocessed = preprocessor.preprocess_bytes(
        data=file_bytes,
        filename=filename,
        media_type_hint="VIDEO" if (content_type and "video" in content_type.lower()) else None,
    )

    try:
        transcriber = get_speech_transcriber()
        result = transcriber.transcribe(
            audio_path=preprocessed.wav_path,
            language=language,
            is_silent=preprocessed.is_silent,
            duration=preprocessed.duration_seconds,
            media_type=preprocessed.media_type,
        )

        return BackendTranscriptResponse(
            full_text=result.full_text,
            language=result.language,
            confidence_score=result.confidence_score,
            duration_seconds=result.evidence.duration_seconds,
            segments_count=len(result.segments),
            words_count=result.words_count,
            segments=result.segments,
            evidence=result.evidence,
            status="COMPLETED",
            error_message=None,
        )
    finally:
        preprocessed.cleanup()


def analyze_speech_to_text_from_path(
    media_path: str,
    language: Optional[str] = None,
) -> BackendTranscriptResponse:
    """
    Secondary path-based entrypoint for local CLI testing and batch workers.
    """
    preprocessor = SpeechPreprocessor()
    preprocessed = preprocessor.preprocess_path(media_path=media_path)

    try:
        transcriber = get_speech_transcriber()
        result = transcriber.transcribe(
            audio_path=preprocessed.wav_path,
            language=language,
            is_silent=preprocessed.is_silent,
            duration=preprocessed.duration_seconds,
            media_type=preprocessed.media_type,
        )

        return BackendTranscriptResponse(
            full_text=result.full_text,
            language=result.language,
            confidence_score=result.confidence_score,
            duration_seconds=result.evidence.duration_seconds,
            segments_count=len(result.segments),
            words_count=result.words_count,
            segments=result.segments,
            evidence=result.evidence,
            status="COMPLETED",
            error_message=None,
        )
    finally:
        preprocessed.cleanup()
