"""
TruthLens AI/ML — Audio Analysis Pydantic Schemas
Blueprint Section F: audio_analysis table schema
Blueprint Section G: POST /api/audio/analyze / POST /api/v1/analyze/audio
Spring Boot Contract: FastApiAudioAnalysisResponse DTO, AudioEvidenceDto, AudioSpliceMarkerDto
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AudioAnalysisStatus(str, Enum):
    """Processing status for audio analysis jobs."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AudioSpliceMarker(BaseModel):
    """
    Suspicious audio splice boundary event with timestamp and forensic justification.
    Maps directly to Spring Boot AudioSpliceMarkerDto.
    """
    timestamp_seconds: float = Field(ge=0.0, description="Timestamp in seconds from audio start")
    score: float = Field(ge=0.0, le=1.0, description="Splice boundary discontinuity anomaly score")
    reason: str = Field(description="Forensic justification for the splice boundary indicator")


class AudioEvidence(BaseModel):
    """
    Granular acoustic evidence metrics for audio authenticity analysis.
    Maps directly to Spring Boot AudioEvidenceDto.
    """
    duration_seconds: float = Field(ge=0.0, description="Total audio duration in seconds")
    pitch_mean: float = Field(ge=0.0, description="Mean fundamental frequency (F0) across voiced segments (Hz)")
    pitch_variance: float = Field(ge=0.0, description="Variance of fundamental frequency (F0) across voiced segments")
    spectral_centroid_mean: float = Field(ge=0.0, description="Mean spectral centroid frequency across frames (Hz)")
    spectral_bandwidth_mean: float = Field(ge=0.0, description="Mean spectral bandwidth across frames (Hz)")
    spectral_rolloff_mean: float = Field(ge=0.0, description="Mean spectral roll-off frequency (85% energy) across frames (Hz)")
    zero_crossing_rate_mean: float = Field(ge=0.0, description="Mean zero-crossing rate across frames")
    phase_discontinuity_score: float = Field(ge=0.0, le=1.0, description="Phase trajectory discontinuity / vocoder anomaly score")
    splice_markers: List[AudioSpliceMarker] = Field(default_factory=list, description="Detected splice boundaries")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional forensic telemetry & window metrics")


class BackendAudioAnalysisResponse(BaseModel):
    """
    Response payload for POST /api/v1/analyze/audio matching Spring Boot
    FastApiAudioAnalysisResponse DTO contract exactly.
    """
    model_config = ConfigDict(protected_namespaces=())

    synthetic_voice_prob: float = Field(ge=0.0, le=1.0, description="Synthetic voice cloning probability [0.0, 1.0]")
    spectrogram_url: Optional[str] = Field(default=None, description="Relative URL to saved Mel-spectrogram artifact")
    spectrogram_base64: str = Field(description="Base64-encoded PNG image of the normalized Mel-spectrogram")
    pitch_variance: float = Field(ge=0.0, description="Variance of pitch contour across voiced intervals")
    splice_markers: List[AudioSpliceMarker] = Field(default_factory=list, description="Detected splicing anomaly events")
    model_name: str = Field(default="TruthLens-AASIST-AudioClassifier", description="Audio anti-spoofing classifier model")
    model_version: str = Field(default="0.1.0-dev", description="Model weights semantic version")
    evidence: AudioEvidence = Field(description="Granular acoustic evidence metrics")
    status: str = Field(default="COMPLETED", description="Analysis status: COMPLETED or FAILED")


class AudioAnalysisRequest(BaseModel):
    """
    Legacy internal request payload for POST /api/audio/analyze.
    """
    media_id: UUID = Field(description="UUID of media record (FK -> media.id)")
    audio_path: str = Field(description="Absolute or relative path to audio file on shared storage", min_length=1)

    @field_validator("audio_path")
    @classmethod
    def audio_path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("audio_path must not be empty or whitespace.")
        return v.strip()


class LegacyAudioAnalysisResponse(BaseModel):
    """
    Legacy internal response payload for POST /api/audio/analyze.
    """
    media_id: UUID
    synthetic_voice_prob: float = Field(ge=0.0, le=1.0)
    spectrogram_url: Optional[str] = None
    spectrogram_base64: str
    pitch_variance: float = Field(ge=0.0)
    phase_discontinuity: float = Field(ge=0.0, le=1.0)
    splice_markers: List[AudioSpliceMarker] = Field(default_factory=list)
    processing_time_ms: int = Field(ge=0)
    status: AudioAnalysisStatus
    error_message: Optional[str] = None
