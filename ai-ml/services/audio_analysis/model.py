"""
TruthLens AI/ML — Module 07: Official AASIST-L Audio Anti-Spoofing Classifier
Architecture: clovaai/aasist (Jung et al., ICASSP 2022) — Lightweight variant (AASIST-L, 85,306 params).
Checkpoint: SpeechAntiSpoofingBenchmarks/AASIST-L (ASVspoof2019 LA pretrained).

Class orientation verified from official clovaai/aasist & SpeechAntiSpoofingBenchmarks/AASIST-L:
  - logits[:, 0] -> spoof / synthetic speech
  - logits[:, 1] -> bona fide / authentic speech
  - softmax(logits, dim=-1)[:, 0] -> synthetic_voice_prob in [0.0, 1.0]
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from config.settings import settings
from services.audio_analysis.aasist_net import Model as OfficialAASISTNet

logger = logging.getLogger(__name__)

# Official clovaai/aasist AASIST-L configuration (config/AASIST-L.conf)
AASIST_L_INPUT_SAMPLES: int = 64600
AASIST_L_CONFIG: Dict[str, Any] = {
    "architecture": "AASIST",
    "nb_samp": AASIST_L_INPUT_SAMPLES,
    "first_conv": 128,
    "filts": [70, [1, 32], [32, 32], [32, 24], [24, 24]],
    "gat_dims": [24, 32],
    "pool_ratios": [0.4, 0.5, 0.7, 0.5],
    "temperatures": [2.0, 2.0, 100.0, 100.0],
}

# Module-level cached classifier singleton
_CACHED_AUDIO_MODEL: Optional[AASISTLClassifier] = None
_CACHED_MODEL_METADATA: Dict[str, Any] = {}


class AASISTLClassifier(nn.Module):
    """
    Wrapper around the official clovaai/aasist Model configured for AASIST-L.
    Operates directly on 16 kHz mono raw waveforms of shape (B, 64600).
    """

    def __init__(self, d_args: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.d_args = d_args or dict(AASIST_L_CONFIG)
        self.net = OfficialAASISTNet(self.d_args)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass returning raw class logits of shape (B, 2):
          index 0 = spoof, index 1 = bona fide.
        """
        if x.dim() == 3 and x.size(1) == 1:
            x = x.squeeze(1)
        elif x.dim() == 1:
            x = x.unsqueeze(0)
        _last_hidden, logits = self.net(x)
        return logits


def pad_or_crop_waveform(
    waveform: np.ndarray,
    max_len: int = AASIST_L_INPUT_SAMPLES,
) -> np.ndarray:
    """
    Deterministic AASIST-L input framing matching clovaai/aasist data_utils.pad():
      - If len >= max_len: take the first max_len samples (no random crop).
      - If 0 < len < max_len: tile-repeat deterministically up to max_len.
    """
    arr = np.asarray(waveform, dtype=np.float32).reshape(-1)
    n = arr.shape[0]
    if n == 0:
        raise ValueError("Cannot frame an empty waveform (0 samples).")
    if n >= max_len:
        return arr[:max_len].astype(np.float32)
    reps = max_len // n + 1
    return np.tile(arr, reps)[:max_len].astype(np.float32)


def _resolve_checkpoint_path(checkpoint_path: str) -> Optional[Path]:
    if not checkpoint_path:
        return None
    p = Path(checkpoint_path)
    if p.is_absolute() and p.exists():
        return p
    rel_model_dir = settings.model_dir / checkpoint_path
    if rel_model_dir.exists():
        return rel_model_dir
    rel_ai_ml = Path("ai-ml/models") / checkpoint_path
    if rel_ai_ml.exists():
        return rel_ai_ml
    if p.exists():
        return p
    return None


def load_audio_classifier(
    checkpoint_path: Optional[str] = None,
    require_checkpoint: Optional[bool] = None,
    device: Optional[torch.device] = None,
) -> Tuple[Optional[AASISTLClassifier], Dict[str, Any]]:
    """
    Initialize AASIST-L and strictly load pretrained weights on CPU (or target device).

    Never returns an untrained network as an active classifier:
      - If checkpoint is missing/invalid and require_checkpoint=True -> raises FileNotFoundError/RuntimeError.
      - If checkpoint is missing/invalid and require_checkpoint=False -> returns (None, metadata) with
        checkpoint_loaded=False so downstream inference explicitly reports MODEL_UNAVAILABLE / Inconclusive.
    """
    if checkpoint_path is None:
        checkpoint_path = settings.audio_classifier_checkpoint
    if require_checkpoint is None:
        require_checkpoint = settings.require_audio_checkpoint
    if device is None:
        device = torch.device("cpu")

    metadata: Dict[str, Any] = {
        "model_name": settings.audio_model_name,
        "model_version": settings.audio_model_version,
        "architecture": "AASIST-L",
        "checkpoint_loaded": False,
        "checkpoint_path": None,
        "parameter_count": 0,
        "class_mapping": {"0": "spoof", "1": "bonafide"},
        "error": None,
    }

    resolved_path = _resolve_checkpoint_path(checkpoint_path)
    if resolved_path is None or not resolved_path.exists():
        msg = (
            f"AASIST-L checkpoint '{checkpoint_path}' was not found in {settings.model_dir}."
        )
        metadata["model_version"] = f"{settings.audio_model_version}-unavailable"
        metadata["error"] = msg
        if require_checkpoint:
            logger.error(msg)
            raise FileNotFoundError(msg)
        logger.warning("%s Audio anti-spoofing classifier will report MODEL_UNAVAILABLE.", msg)
        return None, metadata

    try:
        model = AASISTLClassifier(AASIST_L_CONFIG)
        raw_ckpt = torch.load(str(resolved_path), map_location="cpu")
        if isinstance(raw_ckpt, dict) and "state_dict" in raw_ckpt:
            state_dict = raw_ckpt["state_dict"]
        elif isinstance(raw_ckpt, dict) and "model_state_dict" in raw_ckpt:
            state_dict = raw_ckpt["model_state_dict"]
        elif isinstance(raw_ckpt, dict):
            state_dict = raw_ckpt
        else:
            raise ValueError(f"Unsupported checkpoint payload type in {resolved_path}: {type(raw_ckpt)}")

        # Strip optional DataParallel 'module.' prefix if present
        cleaned_state = {
            (k[7:] if k.startswith("module.") else k): v
            for k, v in state_dict.items()
        }
        model.net.load_state_dict(cleaned_state, strict=True)
        model.to(device)
        model.eval()
        for param in model.parameters():
            param.requires_grad_(False)

        metadata["checkpoint_loaded"] = True
        metadata["checkpoint_path"] = str(resolved_path)
        metadata["parameter_count"] = sum(p.numel() for p in model.parameters())
        logger.info(
            "Loaded AASIST-L checkpoint (%d params) from %s on %s",
            metadata["parameter_count"],
            resolved_path,
            device,
        )
        return model, metadata

    except Exception as exc:
        msg = f"Failed to load AASIST-L checkpoint from {resolved_path}: {exc}"
        metadata["model_version"] = f"{settings.audio_model_version}-unavailable"
        metadata["error"] = msg
        if require_checkpoint:
            logger.error(msg)
            raise RuntimeError(msg) from exc
        logger.warning("%s Audio anti-spoofing classifier will report MODEL_UNAVAILABLE.", msg)
        return None, metadata


def get_audio_classifier() -> Tuple[Optional[AASISTLClassifier], Dict[str, Any]]:
    """Get or initialize singleton cached instance of AASISTLClassifier."""
    global _CACHED_AUDIO_MODEL, _CACHED_MODEL_METADATA
    if not _CACHED_MODEL_METADATA:
        _CACHED_AUDIO_MODEL, _CACHED_MODEL_METADATA = load_audio_classifier()
    return _CACHED_AUDIO_MODEL, _CACHED_MODEL_METADATA


def reset_audio_model() -> None:
    """Reset the cached audio classifier singleton (for test isolation)."""
    global _CACHED_AUDIO_MODEL, _CACHED_MODEL_METADATA
    _CACHED_AUDIO_MODEL = None
    _CACHED_MODEL_METADATA = {}


def predict_synthetic_voice_probability(
    waveform_or_tensor: np.ndarray | torch.Tensor,
    model: Optional[AASISTLClassifier] = None,
) -> float:
    """
    Run CPU no-grad AASIST-L inference on a 16 kHz mono waveform and return
    spoof / synthetic voice probability in [0.0, 1.0].

    Note on class orientation:
      Official AASIST-L outputs logits where index 0 = spoof and index 1 = bona fide.
      Therefore synthetic_voice_prob = softmax(logits, dim=-1)[0, 0].
    """
    if model is None:
        model, meta = get_audio_classifier()
        if model is None or not meta.get("checkpoint_loaded", False):
            raise RuntimeError(
                meta.get("error") or "AASIST-L checkpoint is unavailable; cannot compute spoof probability."
            )

    if isinstance(waveform_or_tensor, np.ndarray):
        framed = pad_or_crop_waveform(waveform_or_tensor, AASIST_L_INPUT_SAMPLES)
        tensor = torch.from_numpy(framed).unsqueeze(0)
    elif isinstance(waveform_or_tensor, torch.Tensor):
        tensor = waveform_or_tensor.detach().float()
        if tensor.dim() == 1:
            if tensor.numel() != AASIST_L_INPUT_SAMPLES:
                framed = pad_or_crop_waveform(tensor.cpu().numpy(), AASIST_L_INPUT_SAMPLES)
                tensor = torch.from_numpy(framed).unsqueeze(0)
            else:
                tensor = tensor.unsqueeze(0)
        elif tensor.dim() == 3 and tensor.size(1) == 1:
            tensor = tensor.squeeze(1)
    else:
        raise TypeError(f"Unsupported input type for AASIST-L inference: {type(waveform_or_tensor)}")

    device = next(model.parameters()).device
    tensor = tensor.to(device)

    model.eval()
    with torch.inference_mode():
        logits = model(tensor)
        if logits.dim() != 2 or logits.size(-1) != 2:
            raise RuntimeError(f"Unexpected AASIST-L output shape: {tuple(logits.shape)}")
        probs = torch.softmax(logits, dim=-1)
        # Index 0 = spoof, Index 1 = bona fide
        spoof_prob = float(probs[0, 0].item())

    return float(np.clip(spoof_prob, 0.0, 1.0))
