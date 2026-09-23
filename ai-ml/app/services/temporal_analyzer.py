import cv2
import numpy as np
from typing import List, Optional


class TemporalForensicAnalyzer:
    """
    Forensic analyzer for video temporal frame inconsistency.
    
    Adheres to blueprint specification:
    Deepfake video synthesis (face-swapping, expression reenactment) frequently introduces
    temporal discontinuities between consecutive frames:
    1. Facial landmark / boundary jitter
    2. Optical flow motion inconsistency across facial seams
    3. High-frequency color / illumination flicker across face crops
    """

    def analyze_temporal_inconsistency(
        self,
        prev_face_bgr: Optional[np.ndarray],
        curr_face_bgr: np.ndarray
    ) -> float:
        """
        Computes temporal discrepancy between consecutive observations of a tracked face.
        
        Args:
            prev_face_bgr: Face crop from preceding frame (or None if first observation)
            curr_face_bgr: Face crop from current frame
            
        Returns:
            inconsistency_score: Bounded anomaly score in [0.0, 1.0]
        """
        if prev_face_bgr is None or prev_face_bgr.size == 0 or curr_face_bgr.size == 0:
            return 0.10  # Baseline neutral score for initial track frame

        # Standardize face dimensions for differential comparison
        h, w = 112, 112
        prev_norm = cv2.resize(prev_face_bgr, (w, h), interpolation=cv2.INTER_AREA)
        curr_norm = cv2.resize(curr_face_bgr, (w, h), interpolation=cv2.INTER_AREA)

        prev_gray = cv2.cvtColor(prev_norm, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_norm, cv2.COLOR_BGR2GRAY)

        # 1. Pixel-wise structural difference
        diff = cv2.absdiff(prev_gray, curr_gray)
        mean_diff = float(np.mean(diff))

        # 2. Dense optical flow motion variance (Farneback method)
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        flow_magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        flow_variance = float(np.var(flow_magnitude))

        # 3. High-frequency boundary gradient divergence
        prev_laplacian = cv2.Laplacian(prev_gray, cv2.CV_32F)
        curr_laplacian = cv2.Laplacian(curr_gray, cv2.CV_32F)
        laplacian_diff = float(np.mean(np.abs(curr_laplacian - prev_laplacian)))

        # Normalize metrics using sigmoid-style bounded scaling
        norm_diff = min(1.0, mean_diff / 50.0)
        norm_flow = min(1.0, flow_variance / 20.0)
        norm_lap = min(1.0, laplacian_diff / 40.0)

        # Composite temporal anomaly score
        composite = 0.40 * norm_diff + 0.35 * norm_flow + 0.25 * norm_lap
        return round(float(np.clip(composite, 0.0, 1.0)), 4)
