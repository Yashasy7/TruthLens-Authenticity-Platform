"""
TruthLens AI/ML — PyTorch Vision Classifier Wrapper
Blueprint: Module 05 — "PyTorch vision model inference wrapper"
           Section E  — "DL Framework: PyTorch 2.2", "Vision & Video: timm"
           Section K  — Benchmark datasets: CIFAKE, Midjourney-v6 Bench

Model Architecture Decision (documented per AGENTS.md guidance):
  - Backbone: efficientnet_b0 (timm) pretrained on ImageNet-1k.
  - Head:     Linear(num_features → 1) for binary classification
              (0 = authentic, 1 = AI-generated / synthetic).
  - Rationale: efficientnet_b0 is the lightest EfficientNet variant in timm,
    balancing inference speed with representational capacity, and is appropriate
    for a capstone demo environment where GPU resources may be limited.
  - Fine-tuning: The binary head is randomly initialised. The full model can be
    fine-tuned on CIFAKE (Section K) by swapping in a .pt checkpoint via
    CLASSIFIER_CHECKPOINT env var. The backbone itself uses ImageNet weights by
    default, which provides useful low-level texture/frequency features.
  - No model weights are committed to the repository (AGENTS.md rule).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import torch
import torch.nn as nn
import timm

from config.settings import settings

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once at FastAPI startup
_model: Optional[nn.Module] = None
_device: torch.device = torch.device("cpu")


def _build_model(backbone_name: str) -> nn.Module:
    """
    Build the EfficientNet + binary classification head.

    Args:
        backbone_name: timm model name (e.g. 'efficientnet_b0').

    Returns:
        PyTorch nn.Module in evaluation mode.
    """
    model = timm.create_model(
        backbone_name,
        pretrained=True,          # ImageNet pretrained backbone weights
        num_classes=0,            # Remove default classifier head
    )
    num_features: int = model.num_features

    # Binary head: authentic (0) vs AI-generated (1)
    head = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(num_features, 1),
        nn.Sigmoid(),
    )
    model.head = head  # type: ignore[assignment]

    # Patch forward to use our head
    original_forward = model.forward

    def patched_forward(x: torch.Tensor) -> torch.Tensor:  # type: ignore
        features = original_forward(x)
        return model.head(features)

    model.forward = patched_forward  # type: ignore[method-assign]
    return model


def load_model(device: Optional[torch.device] = None) -> nn.Module:
    """
    Load (or return the cached) PyTorch classifier model.

    If CLASSIFIER_CHECKPOINT is set in settings, loads fine-tuned weights.
    Otherwise uses the pretrained ImageNet backbone with an untrained binary head.

    Args:
        device: torch.device override. Defaults to CPU.

    Returns:
        nn.Module in eval mode, registered as module-level singleton.
    """
    global _model, _device

    if _model is not None:
        return _model

    _device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Loading classifier backbone: %s on %s", settings.classifier_backbone, _device)

    model = _build_model(settings.classifier_backbone)

    checkpoint_path = settings.classifier_checkpoint
    if checkpoint_path:
        ckpt = Path(settings.model_dir) / checkpoint_path
        if ckpt.exists():
            state = torch.load(str(ckpt), map_location=_device)
            model.load_state_dict(state, strict=False)
            logger.info("Loaded fine-tuned weights from: %s", ckpt)
        else:
            logger.warning(
                "CLASSIFIER_CHECKPOINT '%s' not found in MODEL_DIR. "
                "Using pretrained ImageNet backbone with untrained binary head.",
                checkpoint_path,
            )

    model.to(_device)
    model.eval()
    _model = model
    logger.info("Classifier ready.")
    return _model


def predict_synthetic(
    image_tensor: torch.Tensor,
) -> Tuple[float, float]:
    """
    Run inference on a preprocessed image tensor.

    Args:
        image_tensor: (1, 3, H, W) tensor from image_utils.preprocess_for_model().

    Returns:
        Tuple of:
            synthetic_prob — float [0.0, 1.0]  (1.0 = almost certainly AI-generated)
            confidence     — float [0.0, 1.0]  (distance from decision boundary 0.5)
    """
    model = load_model()
    tensor = image_tensor.to(_device)

    with torch.no_grad():
        output: torch.Tensor = model(tensor)         # (1, 1) after Sigmoid

    prob = float(output.squeeze().item())
    # Confidence: how far from the uncertain midpoint 0.5
    confidence = float(abs(prob - 0.5) * 2.0)

    logger.debug("synthetic_prob=%.4f  confidence=%.4f", prob, confidence)
    return prob, confidence


def reset_model() -> None:
    """Reset the module-level model singleton (useful for testing)."""
    global _model
    _model = None
