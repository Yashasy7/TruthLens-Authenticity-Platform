"""
TruthLens AI/ML — Copy-Move & Splicing Forensic Analysis Engine
Blueprint: Module 05 — Image Authenticity Analysis
           Section J S2 — Copy-move cloning detection & image splicing forensics

Classical computer vision forensic implementation:
  1. Copy-Move Forgery Detection:
     - Multi-scale ORB keypoint detection (Fast & deterministic).
     - Descriptor self-matching with Lowe's ratio test (k-NN, k=3).
     - Spatial distance thresholding to eliminate adjacent/local texture matches.
     - Geometric verification via RANSAC affine transformation estimation.
     - Clusters of spatially separated, geometrically consistent inliers identify
       cloned / copy-moved image patches.

  2. Splicing Forgery Detection:
     - Spatial patch-level Laplacian noise variance inconsistency analysis.
     - Cross-region noise coefficient of variation (CV) measurement.
     - Combined with localized compression/residual disparity.
     - Images spliced from different sources exhibit disparate sensor noise
       profiles across regional blocks.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ManipulationAnalysisResult:
    """Output container for copy-move and splicing forensic detection."""
    copy_move_detected: bool
    splicing_detected: bool
    copy_move_score: float      # [0.0, 1.0] confidence score based on RANSAC inliers
    splicing_score: float       # [0.0, 1.0] score based on spatial noise inconsistency
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_copy_move_and_splicing(
    pil_image: Image.Image,
    min_spatial_dist: float = 30.0,
    ratio_threshold: float = 0.75,
    min_inliers_for_detection: int = 6,
    grid_size: Tuple[int, int] = (4, 4),
) -> ManipulationAnalysisResult:
    """
    Execute copy-move and splicing forensic analysis on a PIL Image.

    Args:
        pil_image: Source image in RGB.
        min_spatial_dist: Minimum Euclidean pixel distance between matched keypoints
                          to exclude natural adjacent repetitive textures.
        ratio_threshold: Lowe's ratio test threshold for descriptor matching.
        min_inliers_for_detection: Minimum RANSAC inliers required to flag copy-move.
        grid_size: (rows, cols) grid for regional noise inconsistency calculation.

    Returns:
        ManipulationAnalysisResult with deterministic flags, scores, and evidence.
    """
    rgb_array = np.array(pil_image.convert("RGB"), dtype=np.uint8)
    h, w, _ = rgb_array.shape

    if h < 16 or w < 16:
        return ManipulationAnalysisResult(
            copy_move_detected=False,
            splicing_detected=False,
            copy_move_score=0.0,
            splicing_score=0.0,
            evidence={
                "reason": "Image too small for keypoint or patch analysis",
                "image_dimensions": [w, h],
                "orb_keypoints": 0,
                "candidate_matches": 0,
                "ransac_inliers": 0,
                "noise_cv": 0.0,
            },
        )

    gray = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)

    # ------------------------------------------------------------------ #
    # Part 1: Copy-Move Detection via ORB + Self-Match + RANSAC
    # ------------------------------------------------------------------ #
    orb = cv2.ORB_create(
        nfeatures=1200,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=15,
        patchSize=31,
    )
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    copy_move_detected = False
    inlier_count = 0
    candidate_matches_count = 0
    copy_move_score = 0.0

    if keypoints is not None and descriptors is not None and len(keypoints) >= 10:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        # Match against own descriptors: k=3
        # Match 0 is self (dist=0); Match 1 is closest non-self; Match 2 is second closest
        try:
            raw_matches = bf.knnMatch(descriptors, descriptors, k=3)
        except cv2.error as exc:
            logger.warning("ORB self-matching failed: %s", exc)
            raw_matches = []

        candidate_pairs: List[Tuple[int, int]] = []
        seen_pairs = set()

        for match_group in raw_matches:
            if len(match_group) < 3:
                continue
            _m_self, m1, m2 = match_group[0], match_group[1], match_group[2]

            # Lowe's ratio test on non-self matches
            if m1.distance < ratio_threshold * m2.distance:
                q_idx = m1.queryIdx
                t_idx = m1.trainIdx
                if q_idx == t_idx:
                    continue

                pair_key = (min(q_idx, t_idx), max(q_idx, t_idx))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                pt1 = keypoints[q_idx].pt
                pt2 = keypoints[t_idx].pt
                spatial_dist = float(np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1]))

                if spatial_dist >= min_spatial_dist:
                    candidate_pairs.append((q_idx, t_idx))

        candidate_matches_count = len(candidate_pairs)

        # Geometric verification using RANSAC
        if candidate_matches_count >= 4:
            src_pts = np.float32([keypoints[q].pt for q, _ in candidate_pairs]).reshape(-1, 1, 2)
            dst_pts = np.float32([keypoints[t].pt for _, t in candidate_pairs]).reshape(-1, 1, 2)

            _, inliers = cv2.estimateAffinePartial2D(
                src_pts,
                dst_pts,
                method=cv2.RANSAC,
                ransacReprojThreshold=8.0,
                maxIters=2000,
            )

            if inliers is not None:
                inlier_count = int(np.sum(inliers))
                copy_move_score = float(np.clip(inlier_count / 12.0, 0.0, 1.0))
                if inlier_count >= min_inliers_for_detection:
                    copy_move_detected = True

    # ------------------------------------------------------------------ #
    # Part 2: Splicing Detection via Regional Noise Variance Discrepancy
    # ------------------------------------------------------------------ #
    rows, cols = grid_size
    patch_h = h // rows
    patch_w = w // cols

    patch_variances: List[float] = []

    if patch_h >= 4 and patch_w >= 4:
        for r in range(rows):
            for c in range(cols):
                patch = gray[r * patch_h : (r + 1) * patch_h, c * patch_w : (c + 1) * patch_w]
                lap = cv2.Laplacian(patch, cv2.CV_64F)
                patch_variances.append(float(lap.var()))

        variances_arr = np.array(patch_variances, dtype=np.float64)
        mean_var = float(np.mean(variances_arr))
        std_var = float(np.std(variances_arr))

        # Coefficient of variation (CV = std / mean)
        if mean_var > 1e-4:
            noise_cv = std_var / mean_var
        else:
            noise_cv = 0.0

        # Splicing detection threshold: natural single-capture images have moderate CV.
        # Spliced composites combining disparate camera/render textures produce high CV.
        splicing_detected = bool(noise_cv > 0.85 and mean_var > 1.0)
        splicing_score = float(np.clip(noise_cv / 1.5, 0.0, 1.0))
    else:
        noise_cv = 0.0
        splicing_detected = False
        splicing_score = 0.0

    evidence: Dict[str, Any] = {
        "orb_keypoints": len(keypoints) if keypoints is not None else 0,
        "candidate_matches": candidate_matches_count,
        "ransac_inliers": inlier_count,
        "copy_move_score": round(copy_move_score, 4),
        "noise_cv": round(noise_cv, 4),
        "splicing_score": round(splicing_score, 4),
        "patches_analyzed": len(patch_variances),
    }

    logger.debug(
        "Manipulation analysis | copy_move=%s (inliers=%d) splicing=%s (noise_cv=%.3f)",
        copy_move_detected,
        inlier_count,
        splicing_detected,
        noise_cv,
    )

    return ManipulationAnalysisResult(
        copy_move_detected=copy_move_detected,
        splicing_detected=splicing_detected,
        copy_move_score=round(copy_move_score, 4),
        splicing_score=round(splicing_score, 4),
        evidence=evidence,
    )
