import io
import pytest
import numpy as np
from PIL import Image, ImageDraw


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Generates a simple in-memory JPEG test image."""
    img = Image.new("RGB", (256, 256), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (100, 100)], fill=(255, 0, 0), outline=(255, 255, 255))
    d.text((30, 40), "TruthLens", fill=(255, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Generates a simple in-memory PNG test image."""
    img = Image.new("RGB", (200, 200), color=(100, 200, 100))
    d = ImageDraw.Draw(img)
    d.ellipse([(50, 50), (150, 150)], fill=(0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_cloned_image_bytes() -> bytes:
    """
    Generates an image with repeated cloned patterns to trigger copy-move keypoint matching.
    """
    img = Image.new("RGB", (300, 300), color=(240, 240, 240))
    d = ImageDraw.Draw(img)
    # Draw complex pattern A
    for i in range(10):
        d.line([(30 + i * 2, 30), (70, 70 + i * 2)], fill=(i * 20, 50, 150), width=2)
    # Duplicate exact pattern at location B (separated by 150px)
    for i in range(10):
        d.line([(180 + i * 2, 180), (220, 220 + i * 2)], fill=(i * 20, 50, 150), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=98)
    return buf.getvalue()


@pytest.fixture
def corrupt_bytes() -> bytes:
    """Corrupt image stream bytes."""
    return b"not-a-valid-image-stream-content"
