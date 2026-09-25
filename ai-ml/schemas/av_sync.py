"""
TruthLens AI/ML — Audio-Visual Synchronization Pydantic Schemas
Blueprint Section F: av_sync_analysis table schema
Blueprint Section G: POST /api/av-sync/analyze / POST /api/v1/analyze/av-sync
Spring Boot Contract: FastApiAvSyncResponse DTO, AvSyncEvidenceDto, MismatchSegmentDto
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AvSyncAnalysisStatus(str, Enum):
    """Processing status for AV sync analysis jobs."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MismatchSegment(BaseModel):
    """
    Granular temporal mismatch interval where audio speech and visual lip motion diverge.
    Maps directly to Spring Boot MismatchSegmentDto.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    start_time: float = Field(default=0.0, ge=0.0, description="Start timestamp in seconds")
    end_time: float = Field(default=0.0, ge=0.0, description="End timestamp in seconds")
    offset_ms: float = Field(default=0.0, description="Estimated temporal offset in milliseconds")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the mismatch detection [0.0, 1.0]")
    reason: str = Field(default="", description="Forensic explanation for the localized synchronization break")
    severity: str = Field(default="MEDIUM", description="Severity level: LOW, MEDIUM, HIGH")

    @property
    def start_seconds(self) -> float:
        return self.start_time

    @property
    def end_seconds(self) -> float:
        return self.end_time

    @property
    def description(self) -> str:
        return self.reason


class AvSyncEvidence(BaseModel):
    """
    Structured explainable forensic evidence for audio-visual synchronization analysis.
    Maps directly to Spring Boot AvSyncEvidenceDto.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    detected_faces_count: int = Field(default=0, ge=0, description="Total number of distinct face tracks detected")
    selected_face_track_id: int = Field(default=-1, description="ID of primary active speaking face track evaluated (-1 if none)")
    video_duration_seconds: float = Field(default=0.0, ge=0.0, description="Total video duration in seconds")
    audio_duration_seconds: float = Field(default=0.0, ge=0.0, description="Total audio duration in seconds")
    fps: float = Field(default=25.0, ge=0.0, description="Analysis video frame rate")
    envelope_correlation: float = Field(default=0.0, description="Peak normalized cross-correlation of acoustic and visual motion envelopes")
    syncnet_min_distance: float = Field(default=1.414, ge=0.0, description="Minimum Euclidean distance in SyncNet joint embedding space")
    syncnet_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="SyncNet temporal offset confidence")
    tracking_stability: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of video frames with stable face/mouth tracking")
    is_development_model: bool = Field(default=True, description="True if running with development/untrained architecture")
    audio_track_present: bool = Field(default=True, description="Whether audio stream was decoded from video container")
    face_detected: bool = Field(default=True, description="Whether primary speaker face was detected")
    cross_correlation_score: float = Field(default=0.0, description="Peak normalized cross-correlation score")
    syncnet_distance: float = Field(default=1.414, description="SyncNet Euclidean distance")
    total_frames_analyzed: int = Field(default=0, description="Total video frames analyzed")
    temporal_drift_score: float = Field(default=0.0, description="Temporal offset drift variance across video")
    sync_status: str = Field(default="ALIGNED", description="Categorical synchronization status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional forensic telemetry & window evaluations")


class BackendAvSyncResponse(BaseModel):
    """
    Response payload for POST /api/v1/analyze/av-sync matching Spring Boot
    FastApiAvSyncResponse DTO contract exactly.
    """
    model_config = ConfigDict(protected_namespaces=())

    sync_score: float = Field(ge=0.0, le=1.0, description="Overall AV synchronization score [0.0, 1.0]; 1.0 = perfect alignment")
    lip_offset_ms: float = Field(description="Global temporal offset in ms; positive = audio lags, negative = audio leads")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence score in synchronization assessment")
    mismatch_segments: List[MismatchSegment] = Field(default_factory=list, description="List of localized desync/dubbing segments")
    model_name: str = Field(default="TruthLens-SyncNet-DualModel", description="AV sync neural evaluator model")
    model_version: str = Field(default="0.1.0-dev", description="Model semantic version")
    evidence: AvSyncEvidence = Field(description="Granular explainable evidence payload")
    status: str = Field(default="COMPLETED", description="Job status: COMPLETED or FAILED")


class AvSyncAnalysisRequest(BaseModel):
    """
    Legacy internal request payload for POST /api/av-sync/analyze.
    """
    model_config = ConfigDict(extra="ignore")

    media_id: Optional[Union[UUID, str]] = Field(default=None, description="UUID or string identifier of media record")
    video_path: str = Field(description="Absolute or relative path to video on shared volume", min_length=1)

    @field_validator("video_path")
    @classmethod
    def video_path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("video_path must not be empty or whitespace.")
        return v.strip()


class LegacyAvSyncAnalysisResponse(BaseModel):
    """
    Legacy internal response payload for POST /api/av-sync/analyze.
    """
    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    media_id: Optional[Union[UUID, str]] = None
    video_path: str = Field(default="")
    sync_score: float = Field(ge=0.0, le=1.0)
    lip_offset_ms: float
    confidence: float = Field(ge=0.0, le=1.0)
    mismatch_segments: List[MismatchSegment] = Field(default_factory=list)
    processing_time_ms: int = Field(default=0, ge=0)
    status: str = "COMPLETED"
    model_name: str = "TruthLens-SyncNet-DualModel"
    model_version: str = "0.1.0-dev"
    evidence: Optional[AvSyncEvidence] = None
    error_message: Optional[str] = None
