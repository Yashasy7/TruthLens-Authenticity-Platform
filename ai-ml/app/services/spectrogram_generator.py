import os
import uuid
import base64
import cv2
import numpy as np
from ..config import settings


class SpectrogramGenerator:
    """
    Renders 80-band Mel-spectrograms into visual forensic artifacts.
    Produces both a saved PNG file in the artifacts directory and a Base64-encoded
    representation for frontend rendering and API response delivery.
    """

    def __init__(self, artifact_dir: str = settings.ARTIFACT_DIR):
        self.artifact_dir = artifact_dir
        if self.artifact_dir and not os.path.exists(self.artifact_dir):
            os.makedirs(self.artifact_dir, exist_ok=True)

    def generate_spectrogram_image(
        self,
        mel_spectrogram_db: np.ndarray,
        filename_prefix: str = "spectrogram",
        target_size: tuple[int, int] | None = None,
    ) -> tuple[str, str]:
        """
        Renders a Mel-spectrogram (in dB) into a pseudo-colored PNG forensic artifact.

        Args:
            mel_spectrogram_db: 2D numpy array [n_mels, time_frames] of log Mel power.
            filename_prefix: Prefix identifier for the saved PNG artifact.
            target_size: Optional (width, height) tuple to resize the output image.

        Returns:
            artifact_path: Absolute or relative file path to the saved PNG image.
            base64_png: Base64-encoded data string of the PNG image.
        """
        if mel_spectrogram_db is None or mel_spectrogram_db.size == 0:
            raise ValueError("Mel-spectrogram matrix cannot be empty.")

        # 1. Normalize dB values to [0, 255] uint8
        spec_min = float(np.min(mel_spectrogram_db))
        spec_max = float(np.max(mel_spectrogram_db))

        if spec_max - spec_min > 1e-6:
            norm_spec = (mel_spectrogram_db - spec_min) / (spec_max - spec_min)
            spec_uint8 = np.uint8(255.0 * norm_spec)
        else:
            spec_uint8 = np.zeros(mel_spectrogram_db.shape, dtype=np.uint8)

        # 2. In audio spectrograms, row 0 is lowest frequency.
        # Flip vertically so lowest frequency is at the bottom of the visual image.
        flipped_spec = cv2.flip(spec_uint8, 0)

        # 3. Optional resize for standard display dimensions
        if target_size is not None and target_size[0] > 0 and target_size[1] > 0:
            rendered_spec = cv2.resize(flipped_spec, target_size, interpolation=cv2.INTER_LINEAR)
        else:
            # Ensure sensible minimum resolution if very short audio
            h, w = flipped_spec.shape
            rendered_w = max(w, 256)
            rendered_h = max(h * 2, 160)
            rendered_spec = cv2.resize(flipped_spec, (rendered_w, rendered_h), interpolation=cv2.INTER_LINEAR)

        # 4. Apply pseudo-color map (VIRIDIS for acoustic spectral intensity)
        colormap_bgr = cv2.applyColorMap(rendered_spec, cv2.COLORMAP_VIRIDIS)

        # 5. Save PNG to artifact directory
        artifact_filename = f"{filename_prefix}_{uuid.uuid4().hex[:10]}.png"
        artifact_path = os.path.join(self.artifact_dir, artifact_filename) if self.artifact_dir else artifact_filename

        cv2.imwrite(artifact_path, colormap_bgr)

        # 6. Encode as Base64 string for direct API inclusion
        success, encoded_png = cv2.imencode(".png", colormap_bgr)
        base64_str = base64.b64encode(encoded_png.tobytes()).decode("utf-8") if success else ""

        return artifact_path, base64_str
