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

    model_config = SettingsConfigDict(env_prefix="TRUTHLENS_AI_")


settings = Settings()
