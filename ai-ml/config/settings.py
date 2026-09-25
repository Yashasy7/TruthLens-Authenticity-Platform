"""
TruthLens AI/ML Microservice — Configuration
Blueprint Section E: Python 3.11, FastAPI (Async Uvicorn)
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    All values have safe defaults for local development.
    No secrets or credentials are stored here.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),   # Allow model_dir, model_input_size field names
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "info"

    # Storage paths
    storage_dir: Path = Path("./storage")
    model_dir: Path = Path("./models")

    # PyTorch / timm classifier settings (Blueprint: PyTorch 2.2 + timm)
    classifier_backbone: str = "efficientnet_b0"
    classifier_checkpoint: str = ""   # Relative to model_dir or absolute path
    require_checkpoint: bool = False  # If True, strictly requires a valid checkpoint file
    model_name: str = "TruthLens-EfficientNet-B0"
    model_version: str = "0.1.0-dev"

    # ELA parameters (Blueprint: Module 05 — ELA heatmap generator)
    ela_quality: int = 90            # JPEG re-save quality; lower = more sensitive

    # Model input size (Image)
    model_input_size: int = 224

    # Module 06 — Video Deepfake Detection settings (Blueprint: 3D-CNN / RetinaFace / FFmpeg)
    video_model_backbone: str = "r3d_18"
    video_classifier_checkpoint: str = ""   # Relative to model_dir or absolute path
    require_video_checkpoint: bool = False  # If True, strictly requires trained video weights
    video_model_name: str = "TruthLens-3DCNN-VideoClassifier"
    video_model_version: str = "0.1.0-dev"
    video_max_sampled_frames: int = 16
    video_face_detection_backend: str = "auto"
    video_target_fps: float = 2.0
    video_crop_size: int = 112

    # Module 07 — Audio Authenticity & Voice Forensics (Blueprint: PyTorch AASIST / Spectrogram / Forensic Features)
    audio_model_name: str = "TruthLens-AASIST-AudioClassifier"
    audio_model_version: str = "0.1.0-dev"
    audio_classifier_checkpoint: str = ""   # Relative to model_dir or absolute path
    require_audio_checkpoint: bool = False  # If True, strictly requires trained audio weights
    audio_sample_rate: int = 16000
    audio_n_mels: int = 80
    audio_n_fft: int = 1024
    audio_hop_length: int = 256
    audio_window_duration_seconds: float = 2.0
    audio_window_hop_seconds: float = 1.0
    audio_splice_threshold: float = 0.55

    # Module 08 — Audio-Video Synchronization (Blueprint: Lip Motion / SyncNet DualModel / Audio Envelope)
    av_sync_model_name: str = "TruthLens-SyncNet-DualModel"
    av_sync_model_version: str = "0.1.0-dev"
    av_sync_classifier_checkpoint: str = ""   # Relative to model_dir or absolute path
    require_av_sync_checkpoint: bool = False  # If True, strictly requires trained SyncNet weights
    av_sync_fps: float = 25.0
    av_sync_window_seconds: float = 1.0
    av_sync_step_seconds: float = 0.5
    av_sync_max_offset_ms: float = 500.0
    av_sync_max_duration_seconds: float = 60.0
    av_sync_mouth_crop_size: int = 96

    # Module 09 — OCR & Visual Text Extraction (Blueprint: OpenCV Preprocessor / Tesseract / EasyOCR)
    ocr_engine: str = "auto"                    # "auto", "tesseract", "easyocr", or "fallback"
    ocr_languages: str = "en"                   # Default OCR language
    ocr_confidence_threshold: float = 0.40      # Minimum confidence threshold for text regions
    ocr_max_image_dimension: int = 2048         # Maximum width/height for preprocessing scaling
    ocr_video_sample_interval_seconds: float = 1.0  # Video keyframe sampling interval
    ocr_video_max_frames: int = 30              # Max video frames to process
    ocr_tesseract_cmd: str = "tesseract"        # Path or command for Tesseract binary
    require_ocr_engine: bool = False            # Strict mode: fail fast if no real OCR engine found

    # Module 10 — Speech-to-Text & Transcript Extraction (Blueprint: Faster-Whisper ASR Microservice)
    whisper_model_name: str = "Faster-Whisper"
    whisper_model_size: str = "tiny"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_download_root: Optional[str] = None
    whisper_beam_size: int = 5
    whisper_language: Optional[str] = None      # Default auto-detect language
    whisper_word_timestamps: bool = True
    whisper_max_duration_seconds: float = 600.0  # 10 minutes maximum duration
    whisper_silence_threshold: float = 1e-4     # RMS silence detection threshold
    whisper_audio_timeout_seconds: float = 60.0
    require_asr_model: bool = False             # Strict mode: fail fast if Faster-Whisper is unavailable

    # Module 11 — Text & Claim Analysis (Blueprint: spaCy / Transformer NLP / Claim Decomposition)
    nlp_engine: str = "auto"                         # "auto", "spacy", "transformer", or "rule_based"
    spacy_model: str = "en_core_web_sm"              # spaCy model checkpoint or name
    claim_max_text_length: int = 100000              # Maximum text characters allowed
    claim_max_sentences: int = 500                   # Maximum sentences analyzed per request
    claim_min_confidence_threshold: float = 0.50     # Minimum confidence threshold
    require_nlp_model: bool = False                  # Strict mode: fail fast if no real spaCy/transformer model found

    @property
    def SPACY_MODEL(self) -> str:
        return self.spacy_model

    @property
    def CLAIM_MAX_TEXT_LENGTH(self) -> int:
        return self.claim_max_text_length

    @property
    def CLAIM_MAX_SENTENCES(self) -> int:
        return self.claim_max_sentences

    @property
    def CLAIM_MIN_CONFIDENCE_THRESHOLD(self) -> float:
        return self.claim_min_confidence_threshold

    @property
    def REQUIRE_NLP_MODEL(self) -> bool:
        return self.require_nlp_model

    def ensure_dirs(self) -> None:
        """Create storage and model directories if they do not exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "ela").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "gradcam").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "spectrogram").mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()


def get_settings() -> Settings:
    """Return the global settings instance."""
    return settings
