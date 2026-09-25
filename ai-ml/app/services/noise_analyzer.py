import cv2
import numpy as np


class NoiseAnalyzer:
    """
    Forensic image noise analyzer.
    
    Natural camera sensors introduce high-frequency photon noise (sensor noise pattern).
    When an image is spliced from multiple camera sources or inpainted with AI,
    the localized noise distribution becomes inconsistent.
    """

    def __init__(self, patch_size: int = 32):
        self.patch_size = patch_size

    def analyze_noise(self, img_rgb: np.ndarray) -> dict:
        """
        Estimates global noise variance and spatial noise consistency.
        
        Returns:
            Dictionary with noise variance, noise inconsistency score,
            patch count, and regional variance spread.
        """
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = gray.shape

        # 1. High-pass filtering via Laplacian to isolate high-frequency sensor noise
        laplacian = cv2.Laplacian(gray, cv2.CV_32F)
        global_variance = float(np.var(laplacian))

        # 2. Block-based local noise variance analysis across grid patches
        patch_variances = []
        for y in range(0, h - self.patch_size + 1, self.patch_size):
            for x in range(0, w - self.patch_size + 1, self.patch_size):
                patch = laplacian[y : y + self.patch_size, x : x + self.patch_size]
                p_var = float(np.var(patch))
                patch_variances.append(p_var)

        if not patch_variances:
            patch_variances = [global_variance]

        patch_arr = np.array(patch_variances, dtype=np.float32)
        mean_patch_var = float(np.mean(patch_arr))
        std_patch_var = float(np.std(patch_arr))

        # Coefficient of variation of local noise (higher value = greater spatial inconsistency)
        inconsistency_ratio = (std_patch_var / (mean_patch_var + 1e-6))
        # Bound score between 0.0 and 1.0 using sigmoid-like scaling
        inconsistency_score = float(1.0 - (1.0 / (1.0 + inconsistency_ratio * 0.5)))

        return {
            "noise_variance": round(global_variance, 4),
            "noise_inconsistency_score": round(inconsistency_score, 4),
            "mean_patch_variance": round(mean_patch_var, 4),
            "std_patch_variance": round(std_patch_var, 4),
            "patch_count": len(patch_variances),
            "patch_size": self.patch_size
        }
