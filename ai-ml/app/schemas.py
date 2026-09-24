from typing import Dict, Any, Optional, List
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


# =============================================================================
# Module 08: Audio-Video Synchronization Analysis Schemas
# =============================================================================

class MismatchSegment(BaseModel):
    """Represents a localized temporal window where audio-video desynchronization occurs."""
    start_time: float = Field(description="Window start timestamp in seconds")
    end_time: float = Field(description="Window end timestamp in seconds")
    offset_ms: float = Field(description="Estimated lip-to-audio temporal offset in milliseconds for this segment")
    confidence: float = Field(ge=0.0, le=1.0, description="Forensic confidence in mismatch detection (0.0 - 1.0)")
    reason: str = Field(description="Diagnostic explanation (e.g. persistent offset, sync break, speech without mouth motion)")


class AvSyncEvidence(BaseModel):
    """Granular forensic evidence supporting the AV synchronization assessment."""
    detected_faces_count: int = Field(description="Total face tracks observed across sampled frames")
    selected_face_track_id: int = Field(description="Track ID of the primary speaker face selected for lip analysis")
    video_duration_seconds: float = Field(description="Total video stream duration in seconds")
    audio_duration_seconds: float = Field(description="Total demuxed audio stream duration in seconds")
    fps: float = Field(description="Frame rate used during AV sync sampling")
    envelope_correlation: float = Field(description="Normalized cross-correlation between audio envelope and visual lip activity (-1.0 to 1.0)")
    syncnet_min_distance: float = Field(description="Minimum embedding distance measured by SyncNet (lower = better alignment)")
    syncnet_confidence: float = Field(ge=0.0, le=1.0, description="SyncNet offset peak prominence confidence score (0.0 to 1.0)")
    tracking_stability: float = Field(ge=0.0, le=1.0, description="Proportion of frames with stable lip landmark tracking")
    is_development_model: bool = Field(default=True, description="True if operating in development mode without production fine-tuned weights")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary temporal curves and offset diagnostic details")


class AvSyncAnalysisResult(BaseModel):
    """Overall audio-video synchronization forensic analysis result."""
    sync_score: float = Field(ge=0.0, le=1.0, description="Global AV sync score (1.0 = perfectly synchronized, 0.0 = severe desync/dubbing)")
    lip_offset_ms: float = Field(description="Global estimated lip/audio offset in milliseconds (positive = audio lags video, negative = audio leads video)")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall forensic confidence score (0.0 to 1.0)")
    mismatch_segments: list[MismatchSegment] = Field(default_factory=list, description="Localized temporal mismatch segments")
    model_name: str = Field(description="AV synchronization model architecture name")
    model_version: str = Field(description="Model weights checkpoint identifier")
    evidence: AvSyncEvidence = Field(description="Comprehensive explainable forensic evidence")
    status: str = Field(default="COMPLETED", description="Analysis execution state (COMPLETED, FAILED)")


# =============================================================================
# Module 09: OCR & Visual Text Extraction Schemas
# =============================================================================

class OcrBoundingBox(BaseModel):
    """Spatial bounding box and polygon coordinates for an extracted text region."""
    x: int = Field(description="Bounding box top-left X coordinate in pixels")
    y: int = Field(description="Bounding box top-left Y coordinate in pixels")
    width: int = Field(description="Bounding box width in pixels")
    height: int = Field(description="Bounding box height in pixels")
    normalized_bbox: List[float] = Field(
        default_factory=list,
        description="Normalized coordinates [x, y, width, height] in range 0.0 to 1.0"
    )
    polygon: List[List[int]] = Field(
        default_factory=list,
        description="Quad polygon corners [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]"
    )


class OcrTextRegion(BaseModel):
    """Represents an extracted text span with spatial, confidence, and optional temporal metadata."""
    text: str = Field(description="Extracted text string")
    confidence: float = Field(ge=0.0, le=1.0, description="OCR recognition confidence (0.0 to 1.0)")
    bounding_box: OcrBoundingBox = Field(description="Spatial bounding box location")
    language: str = Field(default="en", description="Detected language code (e.g. 'en')")
    frame_index: Optional[int] = Field(default=None, description="Frame index for video OCR")
    timestamp_seconds: Optional[float] = Field(default=None, description="Keyframe timestamp in seconds")
    start_time: Optional[float] = Field(default=None, description="Start timestamp for continuous video chyron")
    end_time: Optional[float] = Field(default=None, description="End timestamp for continuous video chyron")


class OcrEvidence(BaseModel):
    """Detailed forensic evidence, preprocessing metadata, and extraction parameters."""
    total_regions: int = Field(description="Count of distinct text regions identified")
    detected_languages: List[str] = Field(default_factory=list, description="Unique languages detected in visual text")
    image_width: int = Field(description="Processed image or frame width")
    image_height: int = Field(description="Processed image or frame height")
    engine_used: str = Field(description="OCR engine implementation (EasyOCR, Tesseract, or OpenCV-Morphological-OCR)")
    preprocessing_applied: List[str] = Field(default_factory=list, description="Applied visual preprocessing steps")
    media_type: str = Field(default="IMAGE", description="Analyzed media type (IMAGE or VIDEO)")
    frames_analyzed: int = Field(default=1, description="Number of visual frames analyzed")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary diagnostic and performance metrics")


class OcrAnalysisResult(BaseModel):
    """Overall result of OCR Visual Text Extraction (Module 09)."""
    extracted_text: str = Field(description="Complete concatenated extracted text")
    language: str = Field(default="en", description="Primary detected language code")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Average OCR confidence across all text regions")
    regions_count: int = Field(description="Total count of text regions")
    regions: List[OcrTextRegion] = Field(default_factory=list, description="Extracted text regions with coordinates")
    evidence: OcrEvidence = Field(description="Explainable preprocessing and extraction evidence")
    status: str = Field(default="COMPLETED", description="Analysis execution state (COMPLETED, FAILED)")
    error_message: Optional[str] = Field(default=None, description="Error message if analysis failed")


# =============================================================================
# Module 10: Speech-to-Text & Transcript Extraction Schemas
# =============================================================================

class TranscriptWord(BaseModel):
    """Word-level timing offset and acoustic alignment confidence."""
    word: str = Field(description="Spoken word token")
    start: float = Field(ge=0.0, description="Word start timestamp in seconds")
    end: float = Field(ge=0.0, description="Word end timestamp in seconds")
    probability: float = Field(ge=0.0, le=1.0, default=1.0, description="Confidence score for this word")


class TranscriptSegment(BaseModel):
    """Timestamped segment with phrase text, alignment offsets, and acoustic metrics."""
    id: int = Field(description="Sequential segment index")
    seek: int = Field(default=0, description="Frame seek offset")
    start: float = Field(ge=0.0, description="Segment start offset in seconds")
    end: float = Field(ge=0.0, description="Segment end offset in seconds")
    text: str = Field(description="Transcribed phrase or sentence")
    tokens: List[int] = Field(default_factory=list, description="Token IDs")
    temperature: float = Field(default=0.0, description="Decoding temperature")
    avg_logprob: float = Field(default=0.0, description="Average log probability")
    compression_ratio: float = Field(default=1.0, description="Text compression ratio")
    no_speech_prob: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability that the segment is non-speech")
    confidence: float = Field(ge=0.0, le=1.0, default=1.0, description="Normalized segment confidence score (0.0 to 1.0)")
    words: List[TranscriptWord] = Field(default_factory=list, description="Word-level timing offsets")


class TranscriptEvidence(BaseModel):
    """Forensic metadata, ASR model details, and acoustic extraction parameters."""
    model_name: str = Field(description="ASR model architecture name")
    model_size: str = Field(description="ASR model size (tiny, base, small, etc.)")
    compute_type: str = Field(description="Quantization / compute type (int8, float16, float32)")
    device: str = Field(description="Inference device (cpu, cuda)")
    detected_language: str = Field(description="Auto-detected primary language code")
    language_probability: float = Field(ge=0.0, le=1.0, description="Language classification probability")
    duration_seconds: float = Field(ge=0.0, description="Total processed audio duration in seconds")
    audio_sample_rate: int = Field(default=16000, description="Resampled audio sampling rate in Hz")
    media_type: str = Field(default="AUDIO", description="Source media type (AUDIO or VIDEO)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary forensic and diagnostic metrics")


class TranscriptResult(BaseModel):
    """Complete structured speech-to-text transcript output (Module 10)."""
    full_text: str = Field(description="Complete concatenated speech transcript")
    language: str = Field(default="en", description="Primary detected language code")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall transcript confidence (0.0 to 1.0)")
    duration_seconds: float = Field(ge=0.0, description="Total speech duration in seconds")
    segments_count: int = Field(default=0, description="Count of timestamped segments")
    words_count: int = Field(default=0, description="Total transcribed words count")
    segments: List[TranscriptSegment] = Field(default_factory=list, description="Timestamped transcript segments")
    evidence: TranscriptEvidence = Field(description="ASR model and acoustic evidence")
    status: str = Field(default="COMPLETED", description="Transcription execution state (COMPLETED, FAILED)")
    error_message: Optional[str] = Field(default=None, description="Error message if transcription failed")



