"""
TruthLens AI/ML — Module 07: Audio Anti-Spoofing Classifier
Blueprint: AASIST-style audio anti-spoofing classifier, strict checkpoint enforcement, eval mode.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from config.settings import settings

logger = logging.getLogger(__name__)

# Cached model instance and metadata
_CACHED_AUDIO_MODEL: Optional[AASISTAudioClassifier] = None
_CACHED_MODEL_METADATA: Dict[str, Any] = {}


class AASISTAudioClassifier(nn.Module):
    """
    AASIST-inspired Spectro-Temporal Neural Network for synthetic speech and voice clone detection.
    Combines 2D convolutional spectro-temporal feature extraction with bidirectional recurrent
    temporal context aggregation and a binary anti-spoofing classification head.
    """

    def __init__(self, n_mels: int = 80, embedding_dim: int = 128) -> None:
        super().__init__()
        self.n_mels = n_mels
        self.embedding_dim = embedding_dim

        # 2D Spectro-Temporal Convolutional Front-End
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=5, padding=2),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((10, None)),
        )

        # Bi-directional Temporal Context Aggregator
        self.gru = nn.GRU(
            input_size=128 * 10,
            hidden_size=embedding_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
        )

        # Classification Head: [0 = Authentic/Bonafide, 1 = Synthetic/Spoof]
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim * 2, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Args:
            x: Input tensor of shape (B, 1, n_mels, T).
        Returns:
            torch.Tensor: Logits of shape (B, 2).
        """
        feat = self.conv(x)  # (B, 128, 10, T')
        b, c, h, w = feat.shape
        # Flatten spatial (channels * height) and permute to (B, T', C*H)
        feat = feat.permute(0, 3, 1, 2).reshape(b, w, c * h)
        out, _ = self.gru(feat)  # (B, T', 2 * embedding_dim)
        # Temporal mean pooling
        pooled = torch.mean(out, dim=1)  # (B, 2 * embedding_dim)
        logits = self.classifier(pooled)
        return logits


def format_log_mel_tensor(
    log_mel: np.ndarray,
    target_frames: int = 128,
) -> torch.Tensor:
    """
    Format and normalize a 2D log-Mel spectrogram for classifier inference.
    Pads or crops the time dimension to target_frames, standardizes values.

    Args:
        log_mel: 2D array of shape (n_mels, time_frames).
        target_frames: Fixed temporal frame length.

    Returns:
        torch.Tensor: Tensor of shape (1, 1, n_mels, target_frames).
    """
    n_mels, time_frames = log_mel.shape

    if time_frames < target_frames:
        pad_width = target_frames - time_frames
        padded = np.pad(log_mel, ((0, 0), (0, pad_width)), mode="edge")
    elif time_frames > target_frames:
        padded = log_mel[:, :target_frames]
    else:
        padded = log_mel

    # Standardization: zero mean, unit variance
    mean = np.mean(padded)
    std = np.std(padded) + 1e-6
    normalized = (padded - mean) / std

    tensor = torch.from_numpy(normalized.astype(np.float32)).unsqueeze(0).unsqueeze(0)
    return tensor


def load_audio_classifier(
    checkpoint_path: Optional[str] = None,
    require_checkpoint: Optional[bool] = None,
    device: Optional[torch.device] = None,
) -> Tuple[AASISTAudioClassifier, Dict[str, Any]]:
    """
    Initialize AASISTAudioClassifier and load weights from checkpoint if available.
    Enforces strict failure when require_checkpoint is enabled and checkpoint is missing.

    Args:
        checkpoint_path: Path to checkpoint file, defaults to settings.audio_classifier_checkpoint.
        require_checkpoint: Whether to enforce checkpoint existence, defaults to settings.require_audio_checkpoint.
        device: Target execution device.

    Returns:
        Tuple[AASISTAudioClassifier, Dict[str, Any]]: Model and associated metadata dict.
    """
    if checkpoint_path is None:
        checkpoint_path = settings.audio_classifier_checkpoint
    if require_checkpoint is None:
        require_checkpoint = settings.require_audio_checkpoint
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = AASISTAudioClassifier(n_mels=settings.audio_n_mels)
    model.to(device)
    model.eval()

    metadata: Dict[str, Any] = {
        "model_name": settings.audio_model_name,
        "model_version": settings.audio_model_version,
        "architecture": "AASISTAudioClassifier",
        "checkpoint_loaded": False,
        "checkpoint_path": None,
    }

    resolved_path: Optional[Path] = None
    if checkpoint_path:
        p = Path(checkpoint_path)
        if p.is_absolute() and p.exists():
            resolved_path = p
        else:
            rel = settings.model_dir / checkpoint_path
            if rel.exists():
                resolved_path = rel
            elif p.exists():
                resolved_path = p

    if resolved_path and resolved_path.exists():
        logger.info("Loading audio classifier checkpoint from %s", resolved_path)
        ckpt = torch.load(resolved_path, map_location=device)
        if isinstance(ckpt, dict) and "state_dict" in ckpt:
            model.load_state_dict(ckpt["state_dict"])
            metadata["checkpoint_loaded"] = True
            metadata["checkpoint_path"] = str(resolved_path)
            metadata["model_version"] = ckpt.get("model_version", settings.audio_model_version)
            metadata["model_name"] = ckpt.get("model_name", settings.audio_model_name)
        elif isinstance(ckpt, dict):
            model.load_state_dict(ckpt)
            metadata["checkpoint_loaded"] = True
            metadata["checkpoint_path"] = str(resolved_path)
        else:
            raise ValueError(f"Invalid checkpoint format in {resolved_path}")
        logger.info("Audio classifier checkpoint successfully loaded: %s (v%s)", metadata["model_name"], metadata["model_version"])
    else:
        if require_checkpoint:
            msg = (
                f"Production checkpoint required (require_audio_checkpoint=True) "
                f"but checkpoint '{checkpoint_path}' was not found in {settings.model_dir}."
            )
            logger.error(msg)
            raise FileNotFoundError(msg)

        metadata["model_version"] = f"{settings.audio_model_version}-untrained"
        logger.warning(
            "TruthLens Audio Classifier operating in DEVELOPMENT mode with an UNTRAINED architecture. "
            "No production weights are loaded. (model_version=%s)", metadata["model_version"]
        )

    return model, metadata


def get_audio_classifier() -> Tuple[AASISTAudioClassifier, Dict[str, Any]]:
    """Get or initialize singleton cached instance of AASISTAudioClassifier."""
    global _CACHED_AUDIO_MODEL, _CACHED_MODEL_METADATA
    if _CACHED_AUDIO_MODEL is None:
        _CACHED_AUDIO_MODEL, _CACHED_MODEL_METADATA = load_audio_classifier()
    return _CACHED_AUDIO_MODEL, _CACHED_MODEL_METADATA


def predict_synthetic_voice_probability(
    log_mel_tensor: torch.Tensor,
    model: Optional[AASISTAudioClassifier] = None,
) -> float:
    """
    Run forward inference with torch.no_grad() and compute synthetic voice probability.

    Args:
        log_mel_tensor: 4D tensor (B, 1, n_mels, T).
        model: Optional pre-loaded classifier; otherwise uses cached singleton.

    Returns:
        float: Probability [0.0, 1.0] that speech is synthetic / cloned.
    """
    if model is None:
        model, _ = get_audio_classifier()

    device = next(model.parameters()).device
    tensor = log_mel_tensor.to(device)

    model.eval()
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=-1)
        # Class 1 is synthetic / spoof
        synth_prob = float(probs[0, 1].item())

    return float(np.clip(synth_prob, 0.0, 1.0))
