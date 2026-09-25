"""
TruthLens AI/ML Microservice — Configuration
Blueprint Section E: Python 3.11, FastAPI (Async Uvicorn)
"""

from pathlib import Path
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
    classifier_checkpoint: str = ""   # Empty = pretrained ImageNet head, no fine-tuned weights

    # ELA parameters (Blueprint: Module 05 — ELA heatmap generator)
    ela_quality: int = 90            # JPEG re-save quality; lower = more sensitive

    # Model input size
    model_input_size: int = 224

    def ensure_dirs(self) -> None:
        """Create storage and model directories if they do not exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "ela").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "gradcam").mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()
