"""
TruthLens AI/ML — Module 10: Speech-to-Text & Transcript Extraction Schemas
Blueprint Section L: Transcribes speech from audio/video into timestamped transcripts.
Aligns 1:1 with Spring Boot FastApiTranscriptResponse DTO.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TranscriptWord(BaseModel):
    """Word-level timing offset and alignment confidence (Module 10)."""
    word: str = Field(..., description="Recognized word or punctuation token")
    start: float = Field(..., description="Start offset in seconds relative to media beginning")
    end: float = Field(..., description="End offset in seconds relative to media beginning")
    probability: float = Field(..., ge=0.0, le=1.0, description="Word alignment confidence score [0.0, 1.0]")


class TranscriptSegment(BaseModel):
    """Timestamped phrase segment with acoustic metrics and word offsets."""
    id: int = Field(0, description="Sequential segment identifier")
    seek: int = Field(0, description="Frame seek offset in audio track")
    start: float = Field(..., description="Segment start offset in seconds")
    end: float = Field(..., description="Segment end offset in seconds")
    text: str = Field(..., description="Transcribed phrase text")
    tokens: List[int] = Field(default_factory=list, description="Whisper subword token IDs")
    temperature: float = Field(0.0, description="Decoding temperature")
    avg_logprob: float = Field(0.0, description="Average log probability of segment tokens")
    compression_ratio: float = Field(1.0, description="Zlib compression ratio of text")
    no_speech_prob: float = Field(0.0, ge=0.0, le=1.0, description="Probability that segment contains no speech")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Normalized segment confidence score in [0.0, 1.0]")
    words: List[TranscriptWord] = Field(default_factory=list, description="Word-level alignments")


class TranscriptEvidence(BaseModel):
    """ASR model metadata, extraction parameters, and diagnostic metrics."""
    model_config = {"protected_namespaces": ()}

    model_name: str = Field("Faster-Whisper", description="ASR model family name")
    model_size: str = Field("tiny", description="Whisper checkpoint size (tiny/base/small/medium/large)")
    compute_type: str = Field("int8", description="Quantization compute precision (int8/float16/float32)")
    device: str = Field("cpu", description="Execution device (cpu or cuda)")
    detected_language: str = Field("en", description="Detected or configured ISO-639-1 language code")
    language_probability: float = Field(1.0, ge=0.0, le=1.0, description="Language classification probability")
    duration_seconds: float = Field(0.0, ge=0.0, description="Analyzed audio stream duration in seconds")
    audio_sample_rate: int = Field(16000, description="Standardized audio sample rate in Hz")
    media_type: str = Field("AUDIO", description="Container category: 'AUDIO' or 'VIDEO'")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional ASR and diagnostic metadata")


class BackendTranscriptResponse(BaseModel):
    """
    Primary API contract matching Spring Boot FastApiTranscriptResponse.java exactly.
    """
    full_text: str = Field(..., description="Consolidated full-text transcript")
    language: str = Field(..., description="Detected primary spoken language code")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Mean acoustic confidence score across segments")
    duration_seconds: float = Field(..., ge=0.0, description="Total media duration in seconds")
    segments_count: int = Field(0, description="Total number of phrase segments")
    words_count: int = Field(0, description="Total number of aligned words")
    segments: List[TranscriptSegment] = Field(default_factory=list, description="Timestamped phrase segments")
    evidence: TranscriptEvidence = Field(default_factory=TranscriptEvidence, description="Diagnostic ASR evidence")
    status: str = Field("COMPLETED", description="Job status: COMPLETED or FAILED")
    error_message: Optional[str] = Field(None, description="Detailed error message if failed")


class LegacyTranscriptAnalysisRequest(BaseModel):
    """Optional path-based request model for internal testing or batch scripts."""
    media_path: str = Field(..., description="Local path to audio or video media file")
    language: Optional[str] = Field(None, description="Optional ISO language code override")


class LegacyTranscriptAnalysisResponse(BaseModel):
    """Legacy response schema maintaining backward compatibility with internal scripts."""
    full_text: str
    language: str
    confidence_score: float
    duration_seconds: float
    segments_count: int
    words_count: int
    segments: List[TranscriptSegment] = Field(default_factory=list)
    evidence: TranscriptEvidence = Field(default_factory=TranscriptEvidence)
    status: str = "COMPLETED"
