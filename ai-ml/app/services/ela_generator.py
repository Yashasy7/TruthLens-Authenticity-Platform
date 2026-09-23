import base64
import io
import cv2
import numpy as np
from PIL import Image
from ..config import settings


class ElaGenerator:
    """
    OpenCV Error Level Analysis (ELA) generator.
    
    ELA exploits the lossy characteristics of JPEG compression:
    Unmodified regions of a JPEG image should have approximately uniform
    compression error levels when recompressed at a fixed quality, while
    spliced or digitally altered regions show distinct error spikes.
    """

    def __init__(self, quality: int = settings.ELA_JPEG_QUALITY, scale: int = settings.ELA_SCALE):
        self.quality = quality
        self.scale = scale

    def generate_ela(self, img_rgb: np.ndarray) -> tuple[np.ndarray, str, dict]:
        """
        Executes Error Level Analysis on an RGB image array.
        
        Returns:
            heatmap_bgr: Color-mapped ELA difference image (BGR for OpenCV).
            heatmap_base64: Base64-encoded PNG image of the heatmap.
            stats: Dictionary of quantitative ELA metrics.
        """
        pil_orig = Image.fromarray(img_rgb)
        
        # 1. In-memory recompression at defined JPEG quality
        buffer = io.BytesIO()
        pil_orig.save(buffer, format="JPEG", quality=self.quality)
        buffer.seek(0)
        recompressed = np.array(Image.open(buffer).convert("RGB"), dtype=np.uint8)

        # 2. Calculate pixel-wise absolute difference
        diff = cv2.absdiff(img_rgb, recompressed)

        # 3. Amplify error difference using scaling factor
        scaled_diff = cv2.convertScaleAbs(diff, alpha=self.scale, beta=0)

        # 4. Generate pseudo-color heatmap (JET colormap) for explainable visual review
        gray_diff = cv2.cvtColor(scaled_diff, cv2.COLOR_RGB2GRAY)
        heatmap_bgr = cv2.applyColorMap(gray_diff, cv2.COLORMAP_JET)

        # 5. Calculate quantitative statistics
        mean_diff = float(np.mean(diff))
        max_diff = float(np.max(diff))
        std_diff = float(np.std(diff))

        # 6. Encode heatmap as PNG base64 for API transmission
        success, encoded_png = cv2.imencode(".png", heatmap_bgr)
        heatmap_base64 = base64.b64encode(encoded_png.tobytes()).decode("utf-8") if success else ""

        stats = {
            "ela_mean_error": round(mean_diff, 4),
            "ela_max_error": round(max_diff, 4),
            "ela_std_error": round(std_diff, 4),
            "recompression_quality": self.quality,
            "amplification_scale": self.scale
        }

        return heatmap_bgr, heatmap_base64, stats
