"""
TruthLens AI/ML — Copy-Move & Splicing Forensic Analysis Engine
Blueprint: Module 05 — Image Authenticity Analysis
           Section J S2 — Copy-move cloning detection & image splicing forensics

Classical computer vision forensic implementation:
  1. Copy-Move Forgery Detection:
     - Multi-scale ORB keypoint detection (fast, deterministic).
     - Descriptor self-matching with Lowe's ratio test (k-NN, k=3).
     - Spatial distance thresholding to eliminate adjacent local texture matches.
     - Shift Vector Consistency & Geometric verification via RANSAC affine transformation.
     - Natural texture suppression: Random non-parallel matches (e.g. foliage, waves, sand)
       are filtered by requiring coherent shift-vector clustering and geometric consistency.
     - Visual evidence overlay generation showing connected cloned keypoints.

  2. Splicing Forgery Detection:
     - Spatial patch-level Laplacian noise variance inconsistency analysis.
     - Cross-region noise coefficient of variation (CV) measurement.
     - Restricts comparison exclusively to textured patches, masking out sky and bokeh.
     - Images spliced from different sources exhibit disparate sensor noise profiles.
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
        min_spatial_dist: Minimum Euclidean pixel distance between matched keypoints.
        ratio_threshold: Lowe's ratio test threshold for descriptor matching.
        min_inliers_for_detection: Minimum RANSAC inliers required to flag copy-move.
        grid_size: (rows, cols) grid for regional noise inconsistency calculation.

    Returns:
        ManipulationAnalysisResult with deterministic flags, scores, and evidence.
    """
    result, _ = _detect_and_visualize(
        pil_image=pil_image,
        min_spatial_dist=min_spatial_dist,
        ratio_threshold=ratio_threshold,
        min_inliers_for_detection=min_inliers_for_detection,
        grid_size=grid_size,
        generate_visual=False,
    )
    return result


def generate_copy_move_map(
    pil_image: Image.Image,
    min_spatial_dist: float = 30.0,
    ratio_threshold: float = 0.75,
    min_inliers_for_detection: int = 6,
) -> Tuple[ManipulationAnalysisResult, Optional[np.ndarray]]:
    """
    Execute copy-move analysis and generate visual evidence overlay.

    Returns:
        Tuple of:
            result — ManipulationAnalysisResult.
            visualization_bgr — optional uint8 numpy array (H, W, 3) BGR image with matched lines/regions.
    """
    return _detect_and_visualize(
        pil_image=pil_image,
        min_spatial_dist=min_spatial_dist,
        ratio_threshold=ratio_threshold,
        min_inliers_for_detection=min_inliers_for_detection,
        grid_size=(4, 4),
        generate_visual=True,
    )


def _detect_and_visualize(
    pil_image: Image.Image,
    min_spatial_dist: float = 30.0,
    ratio_threshold: float = 0.75,
    min_inliers_for_detection: int = 6,
    grid_size: Tuple[int, int] = (4, 4),
    generate_visual: bool = False,
) -> Tuple[ManipulationAnalysisResult, Optional[np.ndarray]]:
    rgb_array = np.array(pil_image.convert("RGB"), dtype=np.uint8)
    h, w, _ = rgb_array.shape
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

    if h < 16 or w < 16:
        empty_res = ManipulationAnalysisResult(
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
        return empty_res, bgr_array if generate_visual else None

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
    inlier_pairs_pts: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

    if keypoints is not None and descriptors is not None and len(keypoints) >= 10:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
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
                inlier_mask = inliers.ravel() == 1
                inlier_count = int(np.sum(inlier_mask))

                # Natural texture suppression:
                # Check spatial cluster dispersion. In genuine copy-move, inliers have
                # consistent translation vectors and span separate source and target regions.
                # In natural textures (e.g. grass, foliage), vectors are scattered in random directions.
                if inlier_count >= min_inliers_for_detection:
                    inlier_src = src_pts[inlier_mask].reshape(-1, 2)
                    inlier_dst = dst_pts[inlier_mask].reshape(-1, 2)

                    shift_vectors = inlier_dst - inlier_src
                    angles = np.arctan2(shift_vectors[:, 1], shift_vectors[:, 0])
                    # Circular variance of angle: 1 - |mean(exp(i * angle))|
                    circ_mean = np.mean(np.exp(1j * angles))
                    circ_var = float(1.0 - np.abs(circ_mean))

                    # Consistent translation has circ_var < 0.35
                    is_vector_coherent = bool(circ_var < 0.35)

                    if is_vector_coherent:
                        copy_move_detected = True
                        copy_move_score = float(np.clip(inlier_count / 12.0, 0.0, 1.0))
                    else:
                        # Repetitive natural texture: suppress false detection
                        copy_move_detected = False
                        copy_move_score = float(np.clip(inlier_count / 30.0, 0.0, 0.25))

                    for s_pt, d_pt in zip(inlier_src, inlier_dst):
                        inlier_pairs_pts.append(((float(s_pt[0]), float(s_pt[1])), (float(d_pt[0]), float(d_pt[1]))))
                else:
                    copy_move_score = float(np.clip(inlier_count / 12.0, 0.0, 1.0))

    # Visual evidence generation
    vis_bgr = bgr_array.copy() if generate_visual else None
    if generate_visual and vis_bgr is not None:
        if copy_move_detected and inlier_pairs_pts:
            for p1, p2 in inlier_pairs_pts:
                pt1 = (int(p1[0]), int(p1[1]))
                pt2 = (int(p2[0]), int(p2[1]))
                cv2.circle(vis_bgr, pt1, 5, (0, 255, 255), -1)  # Yellow source
                cv2.circle(vis_bgr, pt2, 5, (255, 0, 255), -1)  # Magenta target
                cv2.line(vis_bgr, pt1, pt2, (0, 255, 0), 2, cv2.LINE_AA)  # Green vector
            # Add watermark text
            cv2.putText(
                vis_bgr,
                f"Copy-Move Detected: {inlier_count} inliers",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
        else:
            # Clean indicator watermark
            cv2.putText(
                vis_bgr,
                "No Cloned Regions Detected",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 200, 0),
                2,
                cv2.LINE_AA,
            )

    # ------------------------------------------------------------------ #
    # Part 2: Splicing Detection via Regional Noise Variance Discrepancy
    # ------------------------------------------------------------------ #
    rows, cols = grid_size
    patch_h = h // rows
    patch_w = w // cols

    patch_residuals: List[float] = []

    if patch_h >= 8 and patch_w >= 8:
        gray_f = gray.astype(np.float32)
        blurred = cv2.GaussianBlur(gray_f, (5, 5), 1.0)
        residual = np.abs(gray_f - blurred)

        kernel = np.ones((5, 5), np.float32) / 25.0
        mean_sq = cv2.filter2D(gray_f ** 2, -1, kernel)
        sq_mean = cv2.filter2D(gray_f, -1, kernel) ** 2
        local_var = np.maximum(mean_sq - sq_mean, 0.0)

        for r in range(rows):
            for c in range(cols):
                p_gray = gray_f[r * patch_h : (r + 1) * patch_h, c * patch_w : (c + 1) * patch_w]
                p_res = residual[r * patch_h : (r + 1) * patch_h, c * patch_w : (c + 1) * patch_w]
                p_var = local_var[r * patch_h : (r + 1) * patch_h, c * patch_w : (c + 1) * patch_w]

                mean_int = float(np.mean(p_gray))
                if mean_int < 15.0 or mean_int > 240.0:
                    continue

                pct_textured = float(np.mean(p_var >= 15.0))
                if pct_textured < 0.35:
                    continue

                mask = (p_var >= 15.0) & (p_var <= 350.0)
                if np.sum(mask) >= 64:
                    patch_res = float(np.mean(p_res[mask]))
                    patch_residuals.append(patch_res)

        if len(patch_residuals) >= 4:
            res_arr = np.array(patch_residuals, dtype=np.float64)
            mean_res = float(np.mean(res_arr))
            std_res = float(np.std(res_arr))
            med_res = float(np.median(res_arr))

            noise_cv = std_res / (mean_res + 1e-4)
            max_to_med = float(np.max(res_arr) / (med_res + 1e-4))

            if max_to_med > 2.2:
                splicing_score = float(np.clip((max_to_med - 2.2) / 2.0, 0.0, 1.0))
            else:
                splicing_score = 0.0

            splicing_detected = bool(splicing_score >= 0.70 and max_to_med >= 3.5 and noise_cv >= 0.65)
        else:
            noise_cv = 0.0
            splicing_detected = False
            splicing_score = 0.0
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
        "patches_analyzed": len(patch_residuals),
        "splicing_is_heuristic_indicator": True,
        "splicing_disclaimer": (
            "Splicing anomaly flag and score are heuristic spatial noise-inconsistency indicators, "
            "not an independently validated splicing classifier."
        ),
    }

    res = ManipulationAnalysisResult(
        copy_move_detected=copy_move_detected,
        splicing_detected=splicing_detected,
        copy_move_score=round(copy_move_score, 4),
        splicing_score=round(splicing_score, 4),
        evidence=evidence,
    )
    return res, vis_bgr
