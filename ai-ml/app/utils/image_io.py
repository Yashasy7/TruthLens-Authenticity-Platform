import io
import cv2
import numpy as np
import torch
from PIL import Image
from ..config import settings


def load_image_from_bytes(data: bytes) -> np.ndarray:
    """
    Safely decodes image bytes into an RGB numpy array (uint8).
    Enforces maximum payload size and pixel dimension limits.
    """
    if not data:
        raise ValueError("Image data payload is empty")
    if len(data) > settings.MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"Image payload size ({len(data)} bytes) exceeds limit ({settings.MAX_IMAGE_SIZE_BYTES} bytes)")

    try:
        pil_img = Image.open(io.BytesIO(data))
        pil_img.verify()  # Verify integrity
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable image stream: {str(e)}")

    # Re-open after verify (verify closes stream in PIL)
    pil_img = Image.open(io.BytesIO(data))

    width, height = pil_img.size
    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions (0x0)")
    if width > settings.MAX_DIMENSION or height > settings.MAX_DIMENSION:
        raise ValueError(
            f"Image dimensions ({width}x{height}) exceed maximum allowed dimension ({settings.MAX_DIMENSION}px)"
        )

    # Convert to RGB mode
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    return np.array(pil_img, dtype=np.uint8)


def to_torch_tensor(img_rgb: np.ndarray, target_size=(224, 224)) -> torch.Tensor:
    """
    Resizes image and converts to a normalized PyTorch tensor [1, 3, H, W]
    using standard ImageNet normalization.
    """
    resized = cv2.resize(img_rgb, target_size, interpolation=cv2.INTER_AREA)
    img_float = resized.astype(np.float32) / 255.0

    # Standard ImageNet mean and std
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (img_float - mean) / std

    # HWC -> CHW -> NCHW
    tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0)
    return tensor
