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


# =============================================================================
# Module 06 — Video Deepfake & Forensic Analysis Schemas
# =============================================================================

class FaceBoundingBox(BaseModel):
    x: int = Field(description="Left pixel coordinate")
    y: int = Field(description="Top pixel coordinate")
    width: int = Field(description="Bounding box width")
    height: int = Field(description="Bounding box height")
    confidence: float = Field(ge=0.0, le=1.0, description="Face detector confidence score")
    track_id: int = Field(description="Unique continuous face track identifier across video frames")
    landmarks: Optional[list[list[float]]] = Field(default=None, description="5-point facial landmark coordinates [[x, y], ...]")


class VideoFrameScore(BaseModel):
    frame_index: int = Field(description="Zero-based sequence index of the sampled frame")
    timestamp_seconds: float = Field(description="Exact timestamp in seconds from video start")
    deepfake_score: float = Field(ge=0.0, le=1.0, description="AI face swap / deepfake manipulation score")
    temporal_inconsistency: float = Field(ge=0.0, le=1.0, description="Frame-to-frame inconsistency anomaly metric")
    faces_detected: int = Field(description="Number of faces detected in this frame")
    is_suspicious: bool = Field(description="Whether this frame exceeds the suspicious artifact threshold")


class SuspiciousTimestamp(BaseModel):
    timestamp_seconds: float = Field(description="Suspicious occurrence timestamp in seconds")
    frame_index: int = Field(description="Sampled frame sequence index")
    score: float = Field(ge=0.0, le=1.0, description="Composite anomaly score triggering the marker")
    reason: str = Field(description="Forensic rationale code, e.g. HIGH_DEEPFAKE_PROBABILITY, TEMPORAL_INCONSISTENCY")


class VideoAnalysisEvidence(BaseModel):
    face_count: int = Field(description="Total distinct face tracks observed")
    total_frames_sampled: int = Field(description="Total number of video frames analyzed")
    duration_seconds: float = Field(description="Estimated or extracted video duration in seconds")
    frame_scores: list[VideoFrameScore] = Field(default_factory=list, description="Per-frame scores")
    suspicious_timestamps: list[SuspiciousTimestamp] = Field(default_factory=list, description="Marked timestamps")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary forensic metrics")


class VideoAnalysisResult(BaseModel):
    deepfake_prob: float = Field(ge=0.0, le=1.0, description="Aggregate video deepfake probability score")
    face_count: int = Field(description="Count of distinct face tracks detected")
    total_frames_sampled: int = Field(description="Number of frames sampled and analyzed")
    suspicious_timestamps: list[SuspiciousTimestamp] = Field(default_factory=list, description="Marked suspicious timestamps")
    frame_scores: list[VideoFrameScore] = Field(default_factory=list, description="Detailed per-frame scores")
    model_name: str = Field(description="Name of PyTorch video deepfake classifier architecture")
    model_version: str = Field(description="Version of model weights / checkpoint")
    evidence: VideoAnalysisEvidence
    status: str = Field(default="COMPLETED", description="Analysis execution state (COMPLETED, FAILED)")


# =============================================================================
# Module 07 — Audio Authenticity & Voice Forensics Schemas
# =============================================================================

class AudioSpliceMarker(BaseModel):
    timestamp_seconds: float = Field(description="Timestamp in seconds of suspected audio splicing transition")
    score: float = Field(ge=0.0, le=1.0, description="Anomaly confidence of splicing boundary")
    reason: str = Field(description="Forensic rationale, e.g. SPECTRAL_FLUX_JUMP, PHASE_DISCONTINUITY, ENERGY_SHIFT")


class AudioEvidence(BaseModel):
    duration_seconds: float = Field(description="Total analyzed audio duration in seconds")
    pitch_mean: float = Field(description="Mean estimated fundamental frequency (F0 in Hz)")
    pitch_variance: float = Field(description="Variance of estimated fundamental frequency across voiced frames")
    spectral_centroid_mean: float = Field(description="Mean spectral centroid frequency (Hz)")
    spectral_bandwidth_mean: float = Field(description="Mean spectral bandwidth (Hz)")
    spectral_rolloff_mean: float = Field(description="Mean spectral rolloff frequency (Hz)")
    zero_crossing_rate_mean: float = Field(description="Mean rate of signal sign-changes")
    phase_discontinuity_score: float = Field(ge=0.0, le=1.0, description="Phase coherence anomaly indicator")
    splice_markers: list[AudioSpliceMarker] = Field(default_factory=list, description="Detected splice boundary anomalies")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary acoustic forensic metrics")


class AudioAnalysisResult(BaseModel):
    synthetic_voice_prob: float = Field(ge=0.0, le=1.0, description="Probability of synthetic voice cloning / neural TTS")
    spectrogram_url: Optional[str] = Field(default=None, description="Artifact URL to generated Mel-spectrogram image")
    spectrogram_base64: Optional[str] = Field(default=None, description="Base64-encoded PNG image of Mel-spectrogram")
    pitch_variance: float = Field(description="Acoustic pitch variance metric")
    splice_markers: list[AudioSpliceMarker] = Field(default_factory=list, description="Suspected splicing transition markers")
    model_name: str = Field(description="Name of audio authenticity classifier architecture (AASIST)")
    model_version: str = Field(description="Model weights checkpoint version identifier")
    evidence: AudioEvidence = Field(description="Granular acoustic evidence metrics")
    status: str = Field(default="COMPLETED", description="Analysis execution state (COMPLETED, FAILED)")


