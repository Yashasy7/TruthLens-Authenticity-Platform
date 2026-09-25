"""
TruthLens AI/ML — Storage Utilities
Saves generated artefacts (ELA heatmaps, Grad-CAM overlays) to the configured
STORAGE_DIR.  MinIO/S3 integration is handled by the Spring Boot backend team;
this service writes to a local directory on the shared volume.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal
from uuid import UUID

import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

ArtifactKind = Literal["ela", "gradcam"]


def save_heatmap(
    array: np.ndarray,
    media_id: UUID,
    kind: ArtifactKind,
) -> str:
    """
    Save a numpy array as a PNG file to the configured STORAGE_DIR.

    Args:
        array:    numpy uint8 array of shape (H, W) or (H, W, 3).
        media_id: UUID of the media record — used as the filename stem.
        kind:     'ela' or 'gradcam' — determines the sub-directory.

    Returns:
        Relative URL path string (e.g. 'storage/ela/uuid.png') that the
        backend persists in the image_analysis DB table.
    """
    dest_dir: Path = settings.storage_dir / kind
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{media_id}.png"
    dest_path = dest_dir / filename

    img = Image.fromarray(array.astype(np.uint8))
    img.save(str(dest_path), format="PNG")
    logger.info("Saved %s heatmap → %s", kind.upper(), dest_path)

    # Return a relative URL path the backend can expose or store
    return str(Path(settings.storage_dir.name) / kind / filename)
