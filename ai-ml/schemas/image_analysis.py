"""
TruthLens AI/ML — Image Analysis Pydantic Schemas
Blueprint Section F: image_analysis table schema
Blueprint Section G: POST /api/image/analyze endpoint
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisStatus(str, Enum):
    """Processing status of the image analysis job."""
    COMPLETED = "completed"
    FAILED = "failed"


class ImageAnalysisRequest(BaseModel):
    """
    Request payload for POST /api/image/analyze.

    The Spring Boot backend (Module 19 / Module 02) passes the media_id and the
    storage path where the uploaded image file resides on the shared volume.
    This avoids re-transmitting binary data over the internal network.
    """
    media_id: UUID = Field(
        ...,
        description="UUID of the media record in the image_analysis table (FK → media.id).",
    )
    image_path: str = Field(
        ...,
        description=(
            "Absolute or relative path to the image file on the shared storage volume. "
            "Populated by Module 02 (Media Ingestion) from the media.storage_path column."
        ),
        min_length=1,
    )

    @field_validator("image_path")
    @classmethod
    def image_path_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("image_path must not be empty or whitespace.")
        return v.strip()


class ImageAnalysisResponse(BaseModel):
    """
    Response payload for POST /api/image/analyze.

    Maps directly to the blueprint's image_analysis DB table columns (Section F)
    plus extended XAI / evidence fields required by Module 15 (Risk Engine)
    and Module 16 (Explainable Dashboard).

    NOTE: manipulation_prob is included here and should be added to the DB schema
    by the backend team (Yashas) — flagged as a gap from blueprint Section F.
    """

    # --- Core DB columns (Blueprint Section F: image_analysis table) ---
    media_id: UUID = Field(description="FK → media.id")
    synthetic_prob: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Probability [0–1] that the image was AI-generated (Diffusion/GAN). "
            "Produced by the PyTorch timm classifier. Feeds Module 15."
        ),
    )
    ela_heatmap_url: str = Field(
        description="Relative storage path to the ELA difference heatmap PNG. Feeds Module 16."
    )
    noise_variance: float = Field(
        ge=0.0,
        description=(
            "Mean regional noise variance score. Higher values indicate synthetic "
            "or JPEG-compressed smoothing patterns. Feeds Module 15."
        ),
    )

    # --- Extended fields (implied by blueprint Build Scope) ---
    manipulation_prob: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Probability [0–1] of localised physical manipulation (copy-move, splicing, "
            "re-compression artefacts) derived from ELA magnitude. "
            "NOTE: backend team should add this column to image_analysis table."
        ),
    )
    grad_cam_url: Optional[str] = Field(
        default=None,
        description="Relative path to the Grad-CAM attention overlay PNG. Feeds Module 16 heatmap renderer.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Overall pipeline confidence in the combined synthetic_prob + manipulation_prob scores.",
    )
    processing_time_ms: int = Field(
        ge=0,
        description="Wall-clock processing time in milliseconds for the full analysis pipeline.",
    )
    status: AnalysisStatus = Field(description="Final job status.")
    error_message: Optional[str] = Field(
        default=None,
        description="Human-readable error description populated only when status=FAILED.",
    )


class BackendImageAnalysisResponse(BaseModel):
    """
    Response payload for POST /api/v1/analyze/image matching Yashas's Spring Boot
    FastApiImageAnalysisResponse DTO contract exactly.
    """
    model_config = ConfigDict(protected_namespaces=())

    ai_prob: float = Field(ge=0.0, le=1.0, description="Probability [0.0, 1.0] that image is AI-generated")
    manipulation_prob: float = Field(ge=0.0, le=1.0, description="Probability [0.0, 1.0] of physical manipulation/splicing/copy-move")
    noise_variance: Optional[float] = Field(default=None, ge=0.0, description="Laplacian noise variance")
    fft_anomaly_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="FFT frequency domain anomaly score")
    copy_move_detected: bool = Field(default=False, description="Flag indicating detected copy-move cloning")
    splicing_detected: bool = Field(default=False, description="Flag indicating detected image splicing")
    model_name: str = Field(default="TruthLens-EfficientNet-B0", description="Name of the vision model")
    model_version: str = Field(default="0.1.0-dev", description="Semantic version of the model weights")
    ela_heatmap_base64: str = Field(description="Base64-encoded PNG string of ELA heatmap")
    gradcam_heatmap_base64: Optional[str] = Field(default=None, description="Base64-encoded PNG string of Grad-CAM attention overlay")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Structured forensic evidence and sub-metrics")
    status: str = Field(default="COMPLETED", description="Job status, e.g. COMPLETED or FAILED")

