"""
TruthLens AI/ML — Video Deepfake Face Preprocessing & Tensor Formatting
Blueprint: Module 06 — PyTorch 3D-CNN / EfficientNet input preparation
"""

from __future__ import annotations

import logging
from typing import List

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image

from utils.image_utils import _IMAGENET_MEAN, _IMAGENET_STD

logger = logging.getLogger(__name__)


def get_face_transform(target_size: int = 112) -> T.Compose:
    """Return deterministic PyTorch transform for face crops."""
    return T.Compose([
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])


def preprocess_face_crop(
    face_rgb: np.ndarray,
    target_size: int = 112,
) -> torch.Tensor:
    """
    Preprocess a single RGB face crop into a normalized (3, H, W) tensor.

    Args:
        face_rgb: uint8 array (H, W, 3) in RGB order.
        target_size: Spatial dimension (H = W = target_size).

    Returns:
        torch.Tensor of shape (3, target_size, target_size), float32.
    """
    if face_rgb.shape[:2] != (target_size, target_size):
        resized = cv2.resize(face_rgb, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
    else:
        resized = face_rgb

    pil_img = Image.fromarray(resized)
    transform = get_face_transform(target_size)
    tensor = transform(pil_img)  # (3, H, W)
    return tensor


def create_temporal_clip_tensor(
    face_crops: List[np.ndarray],
    clip_length: int = 16,
    target_size: int = 112,
) -> torch.Tensor:
    """
    Assemble a sequence of face crops into a 5-D tensor formatted for 3D-CNN models.

    PyTorch Video (3D-CNN) convention: (B, C, T, H, W)

    Args:
        face_crops: List of uint8 RGB numpy arrays.
        clip_length: Exact temporal sequence length T (default 16).
        target_size: Spatial size H, W (default 112).

    Returns:
        Tensor of shape (1, 3, clip_length, target_size, target_size).
    """
    if not face_crops:
        raise ValueError("Cannot create temporal clip from empty face crop list.")

    n = len(face_crops)
    if n == clip_length:
        selected_crops = face_crops
    elif n < clip_length:
        # Pad by repeating the last crop
        pad_count = clip_length - n
        selected_crops = list(face_crops) + [face_crops[-1]] * pad_count
    else:
        # Subsample uniformly to clip_length
        indices = np.linspace(0, n - 1, clip_length, dtype=int)
        selected_crops = [face_crops[i] for i in indices]

    # Preprocess each crop -> List of (3, H, W)
    tensors = [preprocess_face_crop(c, target_size=target_size) for c in selected_crops]

    # Stack along temporal dimension: (T, 3, H, W) -> permute to (3, T, H, W)
    stacked = torch.stack(tensors, dim=0)        # (T, 3, H, W)
    permuted = stacked.permute(1, 0, 2, 3)       # (3, T, H, W)
    batched = permuted.unsqueeze(0)              # (1, 3, T, H, W)

    return batched


def create_batch_frame_tensor(
    face_crops: List[np.ndarray],
    target_size: int = 112,
) -> torch.Tensor:
    """
    Format a sequence of face crops into a 4-D batch tensor for 2-D spatial classifiers.

    Args:
        face_crops: List of uint8 RGB numpy arrays.
        target_size: Target spatial dimension.

    Returns:
        Tensor of shape (N, 3, target_size, target_size).
    """
    if not face_crops:
        raise ValueError("Cannot create batch tensor from empty face crop list.")

    tensors = [preprocess_face_crop(c, target_size=target_size) for c in face_crops]
    return torch.stack(tensors, dim=0)  # (N, 3, H, W)
