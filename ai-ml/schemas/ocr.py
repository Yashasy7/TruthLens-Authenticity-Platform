"""
TruthLens AI/ML — Module 09: OCR & Visual Text Extraction Pydantic Schemas
Blueprint Section F: ocr_results table schema
Blueprint Section G: POST /api/v1/analyze/ocr / POST /api/ocr/analyze
Spring Boot Contract: FastApiOcrResponse, OcrTextRegionDto, OcrBoundingBoxDto, OcrEvidenceDto
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OcrAnalysisStatus(str, Enum):
    """Processing status for OCR extraction jobs."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OcrBoundingBox(BaseModel):
    """
    Spatial coordinates, normalized box proportions, and 4-corner polygon for a detected text region.
    Maps directly to Spring Boot OcrBoundingBoxDto.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    x: int = Field(ge=0, description="Upper-left X coordinate in pixels")
    y: int = Field(ge=0, description="Upper-left Y coordinate in pixels")
    width: int = Field(ge=0, description="Bounding box width in pixels")
    height: int = Field(ge=0, description="Bounding box height in pixels")
    normalized_bbox: List[float] = Field(
        default_factory=list,
        description="Normalized coordinates [x/w, y/h, width/w, height/h] in [0.0, 1.0]",
    )
    polygon: List[List[int]] = Field(
        default_factory=list,
        description="Ordered list of polygon corner points [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]",
    )


class OcrTextRegion(BaseModel):
    """
    Extracted textual token/line with spatial bounding box, recognition confidence, and temporal metadata.
    Maps directly to Spring Boot OcrTextRegionDto.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    text: str = Field(description="Recognized visual text string")
    confidence: float = Field(ge=0.0, le=1.0, description="OCR recognition confidence [0.0, 1.0]")
    bounding_box: OcrBoundingBox = Field(description="Spatial bounding box in original media coordinates")
    language: str = Field(default="en", description="Detected language code (e.g. 'en', 'es', 'fr')")
    frame_index: Optional[int] = Field(default=None, description="Video keyframe index (for video assets)")
    timestamp_seconds: Optional[float] = Field(default=None, description="Exact keyframe timestamp in seconds")
    start_time: Optional[float] = Field(default=None, description="Start timestamp of persistent text segment")
    end_time: Optional[float] = Field(default=None, description="End timestamp of persistent text segment")


class OcrEvidence(BaseModel):
    """
    Forensic metadata and visual preprocessing parameters applied during extraction.
    Maps directly to Spring Boot OcrEvidenceDto.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    total_regions: int = Field(default=0, ge=0, description="Total text regions extracted")
    detected_languages: List[str] = Field(
        default_factory=list, description="Unique languages detected across all text regions"
    )
    image_width: int = Field(default=0, ge=0, description="Native width of media asset")
    image_height: int = Field(default=0, ge=0, description="Native height of media asset")
    engine_used: str = Field(default="Tesseract", description="OCR backend engine utilized")
    preprocessing_applied: List[str] = Field(
        default_factory=list, description="Ordered list of OpenCV preprocessing operations applied"
    )
    media_type: str = Field(default="IMAGE", description="Media modality: 'IMAGE' or 'VIDEO'")
    frames_analyzed: int = Field(default=1, ge=1, description="Number of visual frames analyzed")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional forensic telemetry")


class BackendOcrResponse(BaseModel):
    """
    Primary response payload for POST /api/v1/analyze/ocr matching Spring Boot
    FastApiOcrResponse contract exactly.
    """
    model_config = ConfigDict(protected_namespaces=())

    extracted_text: str = Field(default="", description="Full concatenated plain text extracted from visual media")
    language: str = Field(default="en", description="Primary detected language code")
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall average confidence score across all recognized text regions [0.0, 1.0]",
    )
    regions_count: int = Field(default=0, ge=0, description="Total number of discrete text regions detected")
    regions: List[OcrTextRegion] = Field(default_factory=list, description="List of granular text regions")
    evidence: OcrEvidence = Field(description="Forensic evidence and preprocessing telemetry")
    status: str = Field(default="COMPLETED", description="Analysis status: COMPLETED or FAILED")
    error_message: Optional[str] = Field(default=None, description="Error explanation if status is FAILED")


class LegacyOcrAnalysisRequest(BaseModel):
    """
    Legacy internal request payload for POST /api/ocr/analyze.
    """
    model_config = ConfigDict(extra="ignore")

    media_id: Optional[Union[UUID, str]] = Field(default=None, description="UUID or identifier of media record")
    media_path: str = Field(description="Filesystem path to the visual media file", min_length=1)

    @field_validator("media_path")
    @classmethod
    def media_path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("media_path must not be empty or whitespace.")
        return v.strip()


class LegacyOcrAnalysisResponse(BaseModel):
    """
    Legacy internal response payload for POST /api/ocr/analyze.
    """
    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    media_id: Optional[Union[UUID, str]] = None
    media_path: str = Field(default="")
    extracted_text: str = Field(default="")
    language: str = Field(default="en")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    regions_count: int = Field(default=0, ge=0)
    regions: List[OcrTextRegion] = Field(default_factory=list)
    evidence: Optional[OcrEvidence] = None
    status: str = "COMPLETED"
    error_message: Optional[str] = None
