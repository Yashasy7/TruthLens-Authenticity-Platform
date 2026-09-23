from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "UP"
    module: str = "Module 05 — Image Authenticity Analysis"
    version: str = "0.1.0"
    device: str
    model_loaded: bool
    model_name: str
    model_version: str


class ImageAnalysisEvidence(BaseModel):
    noise_variance: float = Field(description="Estimated noise variance of image surface")
    noise_inconsistency_score: float = Field(description="Spatial variation in local noise patches")
    fft_anomaly_score: float = Field(description="High-frequency periodic spectral anomaly indicator")
    copy_move_detected: bool = Field(description="Whether cloned/duplicated keypoint clusters were found")
    splicing_detected: bool = Field(description="Whether localized splicing boundary inconsistencies were flagged")
    image_width: int
    image_height: int
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary forensic metrics")


class ImageAnalysisResult(BaseModel):
    ai_prob: float = Field(ge=0.0, le=1.0, description="Probability that the image is synthetic / AI-generated")
    manipulation_prob: float = Field(ge=0.0, le=1.0, description="Probability of localized tampering or manipulation")
    noise_variance: float = Field(description="Global surface noise variance")
    fft_anomaly_score: float = Field(description="Frequency-domain anomaly score")
    copy_move_detected: bool = Field(description="Copy-move duplicate feature cluster indicator")
    splicing_detected: bool = Field(description="Splicing boundary inconsistency indicator")
    model_name: str = Field(description="Name of PyTorch inference model architecture")
    model_version: str = Field(description="Version of model weights / checkpoint")
    ela_heatmap_base64: Optional[str] = Field(default=None, description="Base64-encoded PNG of ELA heatmap")
    gradcam_heatmap_base64: Optional[str] = Field(default=None, description="Base64-encoded PNG of Grad-CAM attention map")
    evidence: ImageAnalysisEvidence
    status: str = Field(default="COMPLETED", description="Analysis execution state (COMPLETED, FAILED)")
