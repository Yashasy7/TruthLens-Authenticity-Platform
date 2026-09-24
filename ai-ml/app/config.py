import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for TruthLens AI/ML FastAPI service."""
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    MODEL_PATH: str = os.getenv("TRUTHLENS_IMAGE_MODEL_PATH", "")
    DEVICE: str = "cuda" if os.getenv("TRUTHLENS_USE_CUDA", "false").lower() == "true" else "cpu"
    MAX_IMAGE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB max upload
    MAX_DIMENSION: int = 4096  # Max width/height to avoid memory exhaustion
    ELA_JPEG_QUALITY: int = 90
    ELA_SCALE: int = 15
    ARTIFACT_DIR: str = os.getenv("TRUTHLENS_ARTIFACT_DIR", "./artifacts")

    # Module 06 Video Deepfake Configuration
    RETINAFACE_MODEL_PATH: str = os.getenv("TRUTHLENS_RETINAFACE_MODEL_PATH", "")
    VIDEO_MODEL_PATH: str = os.getenv("TRUTHLENS_VIDEO_MODEL_PATH", "")
    VIDEO_SEQUENCE_LENGTH: int = 4  # Spatiotemporal sequence depth for 3D-CNN
    FFMPEG_PATH: str = os.getenv("TRUTHLENS_FFMPEG_PATH", "ffmpeg")
    MAX_VIDEO_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB max upload
    VIDEO_SAMPLE_FPS: float = 1.0  # Sample 1 frame per second
    VIDEO_MAX_FRAMES: int = 60  # Upper bound of frames sampled per video
    VIDEO_MAX_DURATION_SECONDS: int = 300  # 5 minutes maximum video length
    VIDEO_PROCESSING_TIMEOUT_SECONDS: int = 60  # Subprocess timeout

    # Module 07 Audio Authenticity Configuration
    AUDIO_MODEL_PATH: str = os.getenv("TRUTHLENS_AUDIO_MODEL_PATH", "")
    MAX_AUDIO_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB max audio upload
    AUDIO_SAMPLE_RATE: int = 16000  # 16 kHz standard forensic sample rate
    AUDIO_MAX_DURATION_SECONDS: int = 300  # 5 minutes maximum audio length
    AUDIO_PROCESSING_TIMEOUT_SECONDS: int = 60  # Subprocess timeout

    # Module 08 AV Sync Configuration
    SYNCNET_CHECKPOINT_PATH: str = os.getenv("TRUTHLENS_SYNCNET_CHECKPOINT_PATH", "")
    MEDIAPIPE_MODEL_PATH: str = os.getenv("TRUTHLENS_MEDIAPIPE_MODEL_PATH", "")
    AV_SYNC_FPS: float = 25.0  # Normalized target frame rate for AV sync evaluation
    AV_SYNC_WINDOW_SECONDS: float = 1.0  # Sliding analysis window duration
    AV_SYNC_STEP_SECONDS: float = 0.5  # Window hop duration
    AV_SYNC_MAX_OFFSET_MS: int = 500  # Max temporal offset search boundary (+/- 500ms)
    AV_SYNC_MAX_DURATION_SECONDS: int = 120  # Max AV sync analysis duration (2 minutes)

    model_config = SettingsConfigDict(env_prefix="TRUTHLENS_AI_")


settings = Settings()
