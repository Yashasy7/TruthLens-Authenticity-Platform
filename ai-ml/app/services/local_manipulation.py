import cv2
import numpy as np


class LocalManipulationDetector:
    """
    Detector for localized physical manipulations, specifically:
    1. Copy-Move Tampering (cloning regions within the same image)
    2. Splicing Tampering (inserting foreign objects from external images)
    """

    def __init__(self, min_match_distance: float = 30.0, min_cluster_size: int = 8):
        self.min_match_distance = min_match_distance
        self.min_cluster_size = min_cluster_size
        self.orb = cv2.ORB_create(nfeatures=1500)

    def detect_manipulation(self, img_rgb: np.ndarray, noise_inconsistency: float, ela_max_error: float) -> dict:
        """
        Runs keypoint clustering for copy-move cloning and combines with
        noise/ELA metrics for splicing detection.
        
        Returns:
            Dictionary with copy_move_detected, splicing_detected,
            manipulation_prob, matched_clone_pairs, and diagnostic metrics.
        """
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        # -------------------------------------------------------------
        # 1. Copy-Move Detection via Self-Matching Feature Descriptors
        # -------------------------------------------------------------
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        clone_pairs_count = 0
        copy_move_flag = False

        if descriptors is not None and len(keypoints) >= 15:
            # BFMatcher with Hamming distance for binary ORB descriptors
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(descriptors, descriptors, k=3)

            valid_clones = []
            for match in matches:
                # match[0] is self-match (distance=0); examine match[1]
                if len(match) > 1:
                    m1 = match[1]
                    pt1 = np.array(keypoints[m1.queryIdx].pt)
                    pt2 = np.array(keypoints[m1.trainIdx].pt)

                    spatial_dist = np.linalg.norm(pt1 - pt2)
                    # Must have very similar descriptor (low hamming dist) but be spatially separated
                    if m1.distance < 28 and spatial_dist > self.min_match_distance:
                        valid_clones.append((pt1, pt2, spatial_dist))

            clone_pairs_count = len(valid_clones)
            # If a cluster of distinct, spatially separated keypoint pairs share near-identical features
            if clone_pairs_count >= self.min_cluster_size:
                copy_move_flag = True

        # -------------------------------------------------------------
        # 2. Splicing Detection via Boundary & Noise Inconsistency
        # -------------------------------------------------------------
        # Splicing introduces sharp localized sensor noise shifts and elevated ELA error
        splicing_flag = (noise_inconsistency > 0.65 and ela_max_error > 80.0) or (noise_inconsistency > 0.80)

        # -------------------------------------------------------------
        # 3. Aggregate Local Manipulation Probability
        # -------------------------------------------------------------
        score = 0.05  # Base photographic baseline

        if copy_move_flag:
            score += 0.45 + min(0.35, (clone_pairs_count - self.min_cluster_size) * 0.02)
        if splicing_flag:
            score += 0.40

        score += noise_inconsistency * 0.20
        manipulation_prob = float(np.clip(score, 0.0, 1.0))

        return {
            "copy_move_detected": copy_move_flag,
            "splicing_detected": splicing_flag,
            "manipulation_prob": round(manipulation_prob, 4),
            "clone_pairs_count": clone_pairs_count,
            "detected_keypoints": len(keypoints) if keypoints is not None else 0
        }
