"""
TruthLens AI/ML — Image Utilities
Blueprint: OpenCV + Pillow for image I/O; PyTorch preprocessing (Module 05)
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Tuple, Union

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

# Supported image MIME extensions (Blueprint: Module 02 handles MIME validation via Apache Tika;
# this is a secondary guard at the AI/ML boundary).
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

# ImageNet normalisation constants used by all timm pretrained models
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)


def validate_image_path(image_path: str | Path) -> Path:
    """
    Validate that the given path exists and has a supported image extension.

    Raises:
        FileNotFoundError: if the path does not exist.
        ValueError: if the extension is not in SUPPORTED_EXTENSIONS.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported image format '{path.suffix}'. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return path


def load_pil_image(image_path: str | Path) -> Image.Image:
    """
    Load and return a PIL Image from disk in RGB mode.

    Raises:
        FileNotFoundError: if the path does not exist.
        ValueError: if the file is not a valid image (corrupted / wrong magic bytes).
    """
    path = validate_image_path(image_path)
    try:
        img = Image.open(path).convert("RGB")
        img.load()  # Force decode to catch corrupted files early
        logger.debug("Loaded image: %s  size=%s", path.name, img.size)
        return img
    except UnidentifiedImageError as exc:
        raise ValueError(f"Cannot decode image file '{path}': {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to open image '{path}': {exc}") from exc


def preprocess_for_model(
    image: Image.Image,
    input_size: int = 224,
) -> torch.Tensor:
    """
    Preprocess a PIL Image into a PyTorch tensor ready for timm model inference.

    Pipeline:
        Resize → CenterCrop → ToTensor → ImageNet Normalise → unsqueeze(0)

    Returns:
        Tensor of shape (1, 3, input_size, input_size).
    """
    transform = T.Compose([
        T.Resize(int(input_size * 1.143)),   # slight oversize before crop
        T.CenterCrop(input_size),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])
    tensor: torch.Tensor = transform(image)
    return tensor.unsqueeze(0)   # (1, C, H, W)


def image_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert a PIL Image (RGB) to a uint8 numpy array of shape (H, W, 3)."""
    return np.array(image, dtype=np.uint8)


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert a uint8 numpy array (H, W, 3) to a PIL Image."""
    return Image.fromarray(array.astype(np.uint8))


def get_image_size(image_path: str | Path) -> Tuple[int, int]:
    """Return (width, height) of an image without fully decoding it."""
    path = validate_image_path(image_path)
    with Image.open(path) as img:
        return img.size  # (width, height)


def load_pil_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """
    Decode raw image bytes into a PIL Image in RGB mode.

    Raises:
        ValueError: if bytes are empty or cannot be decoded as an image.
    """
    if not image_bytes:
        raise ValueError("Image bytes cannot be empty.")
    try:
        buf = io.BytesIO(image_bytes)
        img = Image.open(buf).convert("RGB")
        img.load()
        return img
    except UnidentifiedImageError as exc:
        raise ValueError(f"Cannot decode image data: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to open image from bytes: {exc}") from exc


def encode_image_to_base64_png(
    image: Union[np.ndarray, Image.Image],
    is_bgr: bool = False,
) -> str:
    """
    Encode an image array (uint8) or PIL Image to a clean Base64-encoded PNG string.
    The resulting string can be directly decoded by standard Base64 decoders.

    Args:
        image: PIL Image or numpy array (H, W) or (H, W, 3).
        is_bgr: If True and image is a numpy array, converts BGR to RGB before saving.

    Returns:
        Base64-encoded ASCII string of the PNG image bytes.
    """
    if isinstance(image, np.ndarray):
        arr = image.astype(np.uint8)
        if arr.ndim == 3 and arr.shape[2] == 3 and is_bgr:
            arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(arr)
    elif isinstance(image, Image.Image):
        pil_img = image
    else:
        raise TypeError(f"Unsupported image type for Base64 encoding: {type(image)}")

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

