"""
TruthLens AI/ML — Dual-Engine Vision Classifier Wrapper
Blueprint: Module 05 — "PyTorch vision model inference wrapper"
           Section E  — "DL Framework: PyTorch 2.2", "Vision & Video: timm"
           Section K  — Benchmark datasets: CIFAKE, Midjourney-v6 Bench

Supported Detectors:
  1. UniversalFakeDetect (UnivFD) [Primary Engine]:
     - Architecture: Frozen CLIP ViT-L/14 backbone + lightweight linear classification head (768 -> 1).
     - Official CVPR 2023 weights: OpenAI ViT-L/14 + WAIV fc_weights.pth.
     - Strong cross-generator semantic generalization with low false-positive rate.
  2. TruthLens EfficientNet-B0 [Historical / Experimental Engines]:
     - deepfake_detection_efficientnet_b0.pt (Baseline portrait deepfake detector)
     - deepfake_detection_efficientnet_b0_generalized.pt (Generalized fine-tuned detector)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch
import torch.nn as nn
from PIL import Image
import timm

from config.settings import settings

logger = logging.getLogger(__name__)

# Module-level singletons
_model: Optional[nn.Module] = None
_clip_preprocess: Any = None
_device: torch.device = torch.device("cpu")
_is_trained: bool = False
_active_model_name: str = settings.model_name
_active_model_version: str = settings.model_version
_active_classifier_type: str = getattr(settings, "classifier_type", "efficientnet")


class UnivFDClassifier(nn.Module):
    """
    UniversalFakeDetect (UnivFD) classifier wrapper combining frozen CLIP ViT-L/14
    and pretrained linear classification head.
    """
    def __init__(self, clip_model: nn.Module, fc_layer: nn.Linear):
        super().__init__()
        self.clip_model = clip_model
        self.fc = fc_layer
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x is (B, 3, 224, 224) preprocessed for CLIP
        features = self.clip_model.encode_image(x).float()
        logits = self.fc(features)
        return self.sigmoid(logits)


def _build_model(backbone_name: str = "efficientnet_b0", num_classes: int = 1) -> nn.Module:
    """
    Build the EfficientNet classifier model.

    Args:
        backbone_name: timm model name (e.g. 'efficientnet_b0').
        num_classes: Number of target classes (1 for legacy sigmoid head, 2+ for multi-class logits).

    Returns:
        PyTorch nn.Module in evaluation mode.
    """
    model = timm.create_model(
        backbone_name,
        pretrained=False,
        num_classes=0,
    )
    num_features: int = int(model.num_features)

    if num_classes == 1:
        head = nn.Sequential(
            nn.Dropout(p=0.2),
            nn.Linear(num_features, 1),
            nn.Sigmoid(),
        )
    else:
        head = nn.Sequential(
            nn.Dropout(p=0.2),
            nn.Linear(num_features, num_classes),
        )
    model.head = head

    def patched_forward(x: torch.Tensor) -> torch.Tensor:
        feats = model.forward_features(x)
        pooled = model.forward_head(feats, pre_logits=True)
        return model.head(pooled)

    model.forward = patched_forward
    return model


def _resolve_checkpoint_path(configured_path: str) -> Optional[Path]:
    """Resolve checkpoint path across local directory structures."""
    if not configured_path:
        return None
    p = Path(configured_path)
    if p.is_absolute() and p.exists():
        return p
    candidates = [
        p,
        Path("ai-ml") / p,
        Path(settings.model_dir) / p,
        Path(settings.model_dir) / p.name,
        Path("ai-ml/checkpoints") / p.name,
        Path("ai-ml/models") / p.name,
    ]
    for cand in candidates:
        if cand.exists():
            return cand.resolve()
    return None


def get_model_metadata() -> Tuple[str, str]:
    """Return (model_name, model_version) currently active in the service."""
    return _active_model_name, _active_model_version


def is_model_trained() -> bool:
    """Return True if the active classifier was initialized with verified trained weights."""
    return _is_trained


def get_active_classifier_type() -> str:
    """Return active classifier type ('univfd', 'efficientnet', 'efficientnet_generalized')."""
    return _active_classifier_type


def load_model(
    device: Optional[torch.device] = None,
    classifier_type: Optional[str] = None,
) -> nn.Module:
    """
    Load (or return cached) classifier model singleton.

    Supported types:
      - 'efficientnet' (default): EfficientNet-B0 human face / portrait detector
      - 'univfd': UniversalFakeDetect CLIP ViT-L/14 + fc_weights.pth
      - 'efficientnet_generalized': Historical fine-tuned general checkpoint

    Args:
        device: torch.device override.
        classifier_type: Optional override of settings.classifier_type.

    Returns:
        nn.Module in eval mode.
    """
    global _model, _clip_preprocess, _device, _active_model_name, _active_model_version, _is_trained, _active_classifier_type

    if _model is not None and (classifier_type is None or classifier_type == _active_classifier_type):
        return _model

    _device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    c_type = (classifier_type or getattr(settings, "classifier_type", "efficientnet")).lower().strip()

    configured_ckpt = (settings.classifier_checkpoint or "").strip()
    _active_classifier_type = c_type

    univfd_fc_path = Path("ai-ml/models/univfd/fc_weights.pth")
    univfd_backbone_path = Path("ai-ml/models/univfd/ViT-L-14.pt")

    if c_type == "univfd" and univfd_fc_path.exists() and univfd_backbone_path.exists():
        logger.info("Initializing UniversalFakeDetect (CLIP ViT-L/14 + fc_weights) on %s", _device)
        try:
            import clip
            clip_m, clip_prep = clip.load(str(univfd_backbone_path), device=_device)
            clip_m.eval()

            fc_d = torch.load(str(univfd_fc_path), map_location=_device)
            fc_layer = nn.Linear(768, 1).to(_device)
            fc_layer.load_state_dict(fc_d.get("model_state_dict", fc_d))
            fc_layer.eval()

            univfd_wrapper = UnivFDClassifier(clip_m, fc_layer).to(_device)
            univfd_wrapper.eval()

            _model = univfd_wrapper
            _clip_preprocess = clip_prep
            _active_model_name = "UniversalFakeDetect (UnivFD CLIP ViT-L/14)"
            _active_model_version = "1.0.0-univfd-cvpr23"
            _is_trained = True
            logger.info("UniversalFakeDetect loaded successfully. Active model: %s", _active_model_name)
            return _model
        except Exception as exc:
            logger.warning("Failed to initialize UnivFD (%s). Falling back to EfficientNet-B0.", exc)
            c_type = "efficientnet"
            _active_classifier_type = "efficientnet"

    # EfficientNet-B0 classifier loader
    logger.info("Loading EfficientNet-B0 classifier on %s", _device)

    if configured_ckpt:
        ckpt_path = _resolve_checkpoint_path(configured_ckpt)
        if ckpt_path is None or not ckpt_path.exists():
            raise FileNotFoundError(f"Classifier checkpoint not found: {configured_ckpt}")
    else:
        ckpt_path = None

    if ckpt_path is not None and ckpt_path.exists():
        ckpt_data = torch.load(str(ckpt_path), map_location=_device)
        if isinstance(ckpt_data, dict):
            ckpt_backbone = ckpt_data.get("backbone")
            if ckpt_backbone and ckpt_backbone != settings.classifier_backbone:
                raise RuntimeError(
                    f"Architecture mismatch: checkpoint backbone '{ckpt_backbone}' != '{settings.classifier_backbone}'."
                )
            state_dict = ckpt_data.get("model_state_dict", ckpt_data)
            has_head = any(k.startswith("head.") for k in state_dict.keys())
            if not has_head:
                raise RuntimeError(f"Checkpoint '{ckpt_path}' is missing classification head weights.")

            num_classes = int(ckpt_data.get("num_classes", 1))
            if "head.1.weight" in state_dict:
                num_classes = state_dict["head.1.weight"].shape[0]

            eff_model = _build_model(
                ckpt_backbone or settings.classifier_backbone,
                num_classes=num_classes,
            )
            eff_model.load_state_dict(state_dict, strict=True)
            _active_model_name = ckpt_data.get("model_name", settings.model_name)
            _active_model_version = ckpt_data.get("model_version", settings.model_version)
            _is_trained = True
            logger.info("Loaded EfficientNet checkpoint (%d classes) from: %s", num_classes, ckpt_path)
        else:
            raise RuntimeError(f"Unsupported checkpoint format in {ckpt_path}")
    else:
        if settings.require_checkpoint:
            raise FileNotFoundError(f"Classifier checkpoint required (require_checkpoint=True) but not configured.")
        eff_model = _build_model(settings.classifier_backbone, num_classes=1)
        _active_model_name = settings.model_name
        _active_model_version = f"{settings.model_version}-untrained"
        _is_trained = False
        logger.warning("No checkpoint configured; initialized untrained %s", settings.classifier_backbone)

    eff_model.to(_device)
    eff_model.eval()
    _model = eff_model
    _clip_preprocess = None
    return _model


def predict_synthetic(
    image_tensor: torch.Tensor,
    pil_image: Optional[Image.Image] = None,
) -> Tuple[float, float]:
    """
    Run AI generation inference on an image.

    Args:
        image_tensor: (1, 3, H, W) tensor from image_utils.preprocess_for_model().
        pil_image: Optional source PIL Image (used for native CLIP preprocessing when UnivFD is active).

    Returns:
        Tuple of:
            synthetic_prob — float [0.0, 1.0] (1.0 = AI-generated)
            confidence     — float [0.0, 1.0] (distance from decision boundary 0.5)
    """
    model = load_model()
    if not _is_trained:
        raise RuntimeError("Classifier model is not initialized with trained weights.")

    model.eval()

    with torch.no_grad():
        if _active_classifier_type == "univfd" and _clip_preprocess is not None:
            if pil_image is not None:
                inp = _clip_preprocess(pil_image.convert("RGB")).unsqueeze(0).to(_device)
            else:
                inp = image_tensor.to(_device)
            output = model(inp)
            prob = float(output.squeeze().item())
        else:
            tensor = image_tensor.to(_device)
            output = model(tensor)
            if output.ndim == 2 and output.shape[1] > 1:
                # 2-class softmax: index 0 = genuine, index 1 = ai_generated
                probs = torch.softmax(output, dim=1)
                prob = float(probs[0, 1].item())
            else:
                prob = float(output.squeeze().item())

    prob = float(max(0.0, min(1.0, prob)))

    if _active_classifier_type == "univfd":
        if prob >= 0.5:
            confidence = float(max(0.0, min(1.0, (prob - 0.5) * 2.0)))
        else:
            confidence = float(max(0.0, min(0.35, (0.5 - prob) * 0.7)))
    else:
        # Distance from decision boundary 0.5 normalized to [0, 1]
        confidence = float(max(0.0, min(1.0, abs(prob - 0.5) * 2.0)))

    logger.debug("synthetic_prob=%.4f  confidence=%.4f (type=%s)", prob, confidence, _active_classifier_type)
    return prob, confidence


def reset_model() -> None:
    """Reset the module-level model singleton (useful for test isolation)."""
    global _model, _clip_preprocess, _active_model_name, _active_model_version, _is_trained, _active_classifier_type
    _model = None
    _clip_preprocess = None
    _active_model_name = settings.model_name
    _active_model_version = settings.model_version
    _is_trained = False
    _active_classifier_type = getattr(settings, "classifier_type", "efficientnet")
