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

    model_config = SettingsConfigDict(env_prefix="TRUTHLENS_AI_")


settings = Settings()
