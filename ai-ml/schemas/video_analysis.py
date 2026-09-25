"""
TruthLens AI/ML — Video Analysis Pydantic Schemas
Blueprint Section F: video_analysis table schema
Blueprint Section G: POST /api/video/analyze / POST /api/v1/analyze/video
Spring Boot Contract: FastApiVideoAnalysisResponse DTO
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VideoAnalysisStatus(str, Enum):
    """Processing status for video analysis jobs."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SuspiciousTimestamp(BaseModel):
    """Anomalous or suspicious timestamp in the video timeline."""
    timestamp_seconds: float = Field(ge=0.0, description="Timestamp in seconds from video start")
    frame_index: int = Field(ge=0, description="Sampled frame index")
    score: float = Field(ge=0.0, le=1.0, description="Deepfake/manipulation anomaly score")
    reason: str = Field(description="Explanatory forensic justification for the flag")


class FrameScore(BaseModel):
    """Granular forensic evaluation metrics for a single sampled frame."""
    frame_index: int = Field(ge=0, description="Sequential index of the sampled frame")
    timestamp_seconds: float = Field(ge=0.0, description="Video timestamp in seconds")
    deepfake_score: float = Field(ge=0.0, le=1.0, description="Deepfake probability score for this frame")
    temporal_inconsistency: float = Field(ge=0.0, description="Temporal variation relative to adjacent frames")
    faces_detected: int = Field(ge=0, description="Number of faces detected in this frame")
    is_suspicious: bool = Field(description="True if score or temporal anomaly exceeds threshold")


class VideoEvidence(BaseModel):
    """Detailed structured forensic evidence for video deepfake analysis."""
    face_count: int = Field(ge=0, description="Distinct or maximum faces detected")
    total_frames_sampled: int = Field(ge=0, description="Count of frames analyzed")
    duration_seconds: float = Field(ge=0.0, description="Video duration in seconds")
    frame_scores: List[FrameScore] = Field(default_factory=list, description="List of per-frame evaluations")
    suspicious_timestamps: List[SuspiciousTimestamp] = Field(default_factory=list, description="Marked anomaly events")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional forensic telemetry")


class BackendVideoAnalysisResponse(BaseModel):
    """
    Response payload for POST /api/v1/analyze/video matching Yashas's Spring Boot
    FastApiVideoAnalysisResponse DTO contract exactly.
    """
    model_config = ConfigDict(protected_namespaces=())

    deepfake_prob: float = Field(ge=0.0, le=1.0, description="Overall probability [0.0, 1.0] of video deepfake")
    face_count: int = Field(ge=0, description="Count of detected faces in the video")
    total_frames_sampled: int = Field(ge=0, description="Total number of frames sampled and evaluated")
    suspicious_timestamps: List[SuspiciousTimestamp] = Field(default_factory=list, description="Timeline of anomalies")
    frame_scores: List[FrameScore] = Field(default_factory=list, description="Per-frame scores across video duration")
    model_name: str = Field(default="TruthLens-3DCNN-VideoClassifier", description="Name of the video vision model")
    model_version: str = Field(default="0.1.0-dev", description="Semantic version of model weights")
    evidence: VideoEvidence = Field(description="Structured forensic evidence payload")
    status: str = Field(default="COMPLETED", description="Job status: COMPLETED or FAILED")


class VideoAnalysisRequest(BaseModel):
    """
    Legacy internal request payload for POST /api/video/analyze.
    """
    media_id: UUID = Field(description="UUID of media record (FK -> media.id)")
    video_path: str = Field(description="Absolute or relative path to video on shared volume", min_length=1)

    @field_validator("video_path")
    @classmethod
    def video_path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("video_path must not be empty or whitespace.")
        return v.strip()


class LegacyVideoAnalysisResponse(BaseModel):
    """Legacy internal response payload for POST /api/video/analyze."""
    media_id: UUID
    deepfake_prob: float = Field(ge=0.0, le=1.0)
    face_count: int = Field(ge=0)
    total_frames_sampled: int = Field(ge=0)
    suspicious_timestamps: List[SuspiciousTimestamp] = Field(default_factory=list)
    processing_time_ms: int = Field(ge=0)
    status: VideoAnalysisStatus
    error_message: Optional[str] = None
