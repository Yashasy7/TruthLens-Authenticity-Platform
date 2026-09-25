"""
TruthLens AI/ML — 3D-CNN Video Deepfake Classifier
Blueprint: Module 06 — PyTorch 3D-CNN / EfficientNet video deepfake classifier
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torchvision.models.video as vm

from config.settings import settings

logger = logging.getLogger(__name__)

# Module-level singleton
_video_model: Optional[nn.Module] = None
_video_device: torch.device = torch.device("cpu")
_active_video_model_version: str = settings.video_model_version


def _build_video_model(backbone_name: str = "r3d_18") -> nn.Module:
    """
    Construct the 3D-CNN architecture with a custom binary classification head.

    Args:
        backbone_name: Architecture variant in torchvision.models.video (e.g. 'r3d_18', 'mc3_18').

    Returns:
        PyTorch nn.Module ready for binary classification.
    """
    if backbone_name == "r3d_18":
        model = vm.r3d_18(weights=None)
    elif backbone_name == "mc3_18":
        model = vm.mc3_18(weights=None)
    elif backbone_name == "r2plus1d_18":
        model = vm.r2plus1d_18(weights=None)
    else:
        logger.warning("Unknown video backbone '%s', falling back to r3d_18", backbone_name)
        model = vm.r3d_18(weights=None)

    in_features: int = model.fc.in_features

    # Binary deepfake classification head: 0 = Authentic, 1 = Deepfake
    model.fc = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 1),
        nn.Sigmoid(),
    )

    return model


def get_video_model_metadata() -> Tuple[str, str]:
    """Return active model name and version for response telemetry."""
    return settings.video_model_name, _active_video_model_version


def load_video_model(device: Optional[torch.device] = None) -> nn.Module:
    """
    Load (or return the cached) 3D-CNN video deepfake classifier.

    If VIDEO_CLASSIFIER_CHECKPOINT is configured, loads fine-tuned weights.
    If REQUIRE_VIDEO_CHECKPOINT is True, fails fast if checkpoint is missing or empty.
    Otherwise runs in development mode with untrained head, logging an explicit warning.

    Args:
        device: torch.device override.

    Returns:
        nn.Module in eval mode.
    """
    global _video_model, _video_device, _active_video_model_version

    if _video_model is not None:
        return _video_model

    _video_device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Initializing 3D-CNN video model (%s) on %s", settings.video_model_backbone, _video_device)

    model = _build_video_model(settings.video_model_backbone)

    checkpoint_path = settings.video_classifier_checkpoint.strip()
    if settings.require_video_checkpoint and not checkpoint_path:
        raise RuntimeError(
            "Production mode requires VIDEO_CLASSIFIER_CHECKPOINT to be set. "
            "Cannot run in production mode with untrained video weights."
        )

    if checkpoint_path:
        ckpt = Path(checkpoint_path)
        if not ckpt.is_absolute():
            ckpt = Path(settings.model_dir) / checkpoint_path

        if not ckpt.exists():
            raise FileNotFoundError(
                f"Video classifier checkpoint '{checkpoint_path}' not found at '{ckpt}'."
            )

        loaded = torch.load(str(ckpt), map_location=_video_device)
        if isinstance(loaded, dict) and "model_state_dict" in loaded:
            state = loaded["model_state_dict"]
            if "model_version" in loaded:
                _active_video_model_version = str(loaded["model_version"])
        else:
            state = loaded

        model.load_state_dict(state, strict=False)
        logger.info("Loaded video classifier weights from %s (version: %s)", ckpt, _active_video_model_version)
    else:
        _active_video_model_version = f"{settings.video_model_version}-untrained"
        logger.warning(
            "No VIDEO_CLASSIFIER_CHECKPOINT configured. Running 3D-CNN video classifier "
            "with development/untrained weights."
        )

    model.to(_video_device)
    model.eval()
    _video_model = model
    logger.info("Video classifier ready. Active model: %s | version: %s", settings.video_model_name, _active_video_model_version)
    return _video_model


def predict_video_clip(clip_tensor: torch.Tensor) -> float:
    """
    Execute 3D-CNN inference on a 5-D temporal clip tensor (1, 3, T, H, W).

    Returns:
        Deepfake probability float in [0.0, 1.0].
    """
    model = load_video_model()
    model.eval()
    tensor = clip_tensor.to(_video_device)

    with torch.no_grad():
        output = model(tensor)

    prob = float(output.squeeze().item())
    return float(np.clip(prob, 0.0, 1.0))


def reset_video_model() -> None:
    """Reset the module-level singleton model for testing."""
    global _video_model, _active_video_model_version
    _video_model = None
    _active_video_model_version = settings.video_model_version
