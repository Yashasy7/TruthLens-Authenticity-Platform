"""Video-to-Face extraction pipeline for authorized datasets (FaceForensics++, Celeb-DF-v2, DFDC).

Extracts frames at configurable intervals, performs face detection and margin-expanded square
alignment, enforces zero center-crop fallback on missing faces, extracts paired identity/video
tokens, suppresses intra-video duplicates via perceptual dhash, and generates a Stage 1 compatible
dataset manifest.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import cv2
import numpy as np
from PIL import Image

# Ensure ai-ml root is in sys.path for importing human_face_dataset helpers
AI_ML_ROOT = Path(__file__).resolve().parent
if str(AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ML_ROOT))

try:
    import human_face_dataset as hfd
except ImportError:
    hfd = None  # Fallback gracefully if invoked in isolated environments

logger = logging.getLogger("extract_manipulated_faces")

SUPPORTED_VIDEO_EXTENSIONS: Set[str] = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    ".flv",
    ".m4v",
    ".wmv",
}

CLASS_NAMES: Tuple[str, str, str] = ("genuine", "ai_generated", "manipulated")
CLASS_TO_ID: Dict[str, int] = {name: idx for idx, name in enumerate(CLASS_NAMES)}
ID_TO_CLASS: Dict[int, str] = {idx: name for idx, name in enumerate(CLASS_NAMES)}


@dataclass
class FaceDetection:
    """Detected face bounding box and confidence."""

    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def area(self) -> int:
        return self.width * self.height


class BaseFaceDetector:
    """Abstract base detector interface."""

    def detect(self, frame_bgr: np.ndarray) -> List[FaceDetection]:
        raise NotImplementedError


class HaarFaceDetector(BaseFaceDetector):
    """
    OpenCV Haar Cascade Face Detector.
    Runs 100% offline with zero external downloads or network access.
    """

    def __init__(
        self,
        cascade_path: Optional[str] = None,
        scale_factor: float = 1.1,
        min_neighbors: int = 4,
        min_size: int = 64,
    ):
        if cascade_path is None:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            raise FileNotFoundError(f"Haar cascade XML not found: {cascade_path}")

        self.cascade = cv2.CascadeClassifier(cascade_path)
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size

    def detect(self, frame_bgr: np.ndarray) -> List[FaceDetection]:
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        try:
            res = self.cascade.detectMultiScale3(
                gray,
                scaleFactor=self.scale_factor,
                minNeighbors=self.min_neighbors,
                minSize=(self.min_size, self.min_size),
                outputRejectLevels=True,
            )
            rects, _, weights = res
        except cv2.error:
            # Fallback to standard detectMultiScale if detectMultiScale3 is unsupported
            rects = self.cascade.detectMultiScale(
                gray,
                scaleFactor=self.scale_factor,
                minNeighbors=self.min_neighbors,
                minSize=(self.min_size, self.min_size),
            )
            weights = [1.0] * len(rects)

        detections: List[FaceDetection] = []
        for (x, y, w, h), weight in zip(rects, weights):
            # Sigmoid normalization of cascade stage weights into [0, 1]
            conf = float(1.0 / (1.0 + np.exp(-0.3 * float(weight))))
            detections.append(FaceDetection(x=int(x), y=int(y), width=int(w), height=int(h), confidence=round(conf, 4)))

        # Sort primarily by area descending then confidence descending
        detections.sort(key=lambda d: (d.area, d.confidence), reverse=True)
        return detections


def compute_dhash_string(pil_img: Image.Image, hash_size: int = 8) -> str:
    """Compute difference hash (dhash) as 16-character hex string."""
    if hfd is not None:
        return hfd.compute_dhash(pil_img, hash_size=hash_size)
    # Standalone fallback
    resized = pil_img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(resized, dtype=np.int32)
    diff = pixels[:, 1:] > pixels[:, :-1]
    bit_str = "".join("1" if b else "0" for b in diff.flatten())
    int_val = int(bit_str, 2)
    return f"{int_val:0{hash_size * hash_size // 4}x}"


def compute_hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hex dhash strings."""
    if hfd is not None and hasattr(hfd, "dhash_hamming_distance"):
        return hfd.dhash_hamming_distance(hash1, hash2)
    return bin(int(hash1, 16) ^ int(hash2, 16)).count("1")


def extract_square_face_crop(
    frame_bgr: np.ndarray,
    detection: FaceDetection,
    crop_size: int = 256,
    margin_percent: float = 0.25,
) -> np.ndarray:
    """
    Extract square face crop centered on detection with configurable boundary margin.

    Handles boundary clipping using reflection padding (`cv2.BORDER_REFLECT_101`) to preserve
    facial geometry even when faces touch video frame borders. Never distorts aspect ratio.
    """
    frame_h, frame_w = frame_bgr.shape[:2]
    cx = detection.x + detection.width / 2.0
    cy = detection.y + detection.height / 2.0

    # Expand box with margin
    side = max(detection.width, detection.height) * (1.0 + margin_percent)
    half_side = side / 2.0

    x1 = int(round(cx - half_side))
    y1 = int(round(cy - half_side))
    x2 = int(round(cx + half_side))
    y2 = int(round(cy + half_side))

    # Calculate padding if crop box extends outside video boundaries
    pad_left = max(0, -x1)
    pad_top = max(0, -y1)
    pad_right = max(0, x2 - frame_w)
    pad_bottom = max(0, y2 - frame_h)

    if pad_left > 0 or pad_top > 0 or pad_right > 0 or pad_bottom > 0:
        padded = cv2.copyMakeBorder(
            frame_bgr,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            borderType=cv2.BORDER_REFLECT_101,
        )
        crop_x1 = x1 + pad_left
        crop_y1 = y1 + pad_top
        crop_x2 = x2 + pad_left
        crop_y2 = y2 + pad_top
        crop = padded[crop_y1:crop_y2, crop_x1:crop_x2]
    else:
        crop = frame_bgr[y1:y2, x1:x2]

    if crop.size == 0 or crop.shape[0] == 0 or crop.shape[1] == 0:
        raise ValueError(f"Extracted zero-sized crop from bbox {detection}")

    resized = cv2.resize(crop, (crop_size, crop_size), interpolation=cv2.INTER_LANCZOS4)
    return resized


def resolve_video_metadata(
    video_path: Path,
    explicit_class: Optional[str] = None,
    explicit_subset: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Derive dataset source, manipulation method, class label, container, and paired identity tokens.

    Integrates with `human_face_dataset.py` subset registry and identity token clustering:
    - FF++: Paired clips (`001.mp4` real vs `001_002.mp4` fake) share `ffpp::clip::001`
    - Celeb-DF-v2: Paired actor clips (`id0_0001.mp4` real vs `id0_id1_0001.mp4` fake) share `celebdf::actor::id0`
    """
    path_str = str(video_path).replace("\\", "/")
    stem = video_path.stem

    cls_name: Optional[str] = explicit_class
    subset: str = explicit_subset or "unknown"
    container: Optional[str] = None
    reason: str = "explicit" if explicit_class else "inferred"

    # Use human_face_dataset resolver if available
    if hfd is not None and not explicit_class:
        cls_cand, sub_cand, r_cand = hfd.resolve_subset_class(path_str, explicit_subset=explicit_subset)
        if cls_cand in ("genuine", "manipulated"):
            cls_name = cls_cand
            subset = sub_cand
            reason = r_cand

    # Canonical container inference
    lower_path = path_str.lower()
    if "celeb_df" in lower_path or "celeb-df" in lower_path:
        container = "celeb_df_v2"
        dataset_source = "Celeb-DF-v2"
        if not cls_name:
            if any(k in lower_path for k in ("celeb-real", "youtube-real", "real")):
                cls_name = "genuine"
                subset = "celeb_real" if "celeb-real" in lower_path else "youtube_real"
            elif any(k in lower_path for k in ("celeb-synthesis", "synthesis", "fake")):
                cls_name = "manipulated"
                subset = "celeb_synthesis"
    elif any(k in lower_path for k in ("faceforensics", "ff++", "ff_pp")):
        container = "ff_pp"
        dataset_source = "FaceForensics++"
        if not cls_name:
            if "original_sequences" in lower_path or "/real/" in lower_path or "/youtube/" in lower_path:
                cls_name = "genuine"
                subset = "original_sequences"
            elif "manipulated_sequences" in lower_path or "/fake/" in lower_path:
                cls_name = "manipulated"
                for m in ("deepfakes", "faceswap", "face2face", "neuraltextures", "faceshifter"):
                    if m in lower_path:
                        subset = m
                        break
                else:
                    subset = "deepfakes"
    elif "dfdc" in lower_path:
        container = "dfdc"
        dataset_source = "DFDC"
        if not cls_name:
            cls_name = "genuine" if "/real/" in lower_path or "real" in stem.lower() else "manipulated"
            subset = "dfdc"
    else:
        dataset_source = "Custom-Video"
        container = "custom"
        if not cls_name:
            if any(k in lower_path for k in ("real", "original", "genuine", "pristine")):
                cls_name = "genuine"
                subset = "custom_real"
            elif any(k in lower_path for k in ("fake", "manipulated", "swap", "deepfake", "synthesis")):
                cls_name = "manipulated"
                subset = "custom_fake"
            else:
                cls_name = "manipulated"  # Default assumption for video manipulation pipeline
                subset = "custom_video"

    # Derive manipulation method name
    if cls_name == "genuine":
        method = "Original"
    elif subset in ("deepfakes", "faceswap", "face2face", "neuraltextures", "faceshifter"):
        method = subset.capitalize()
    elif subset == "celeb_synthesis":
        method = "Celeb-synthesis"
    else:
        method = subset

    # Derive primary source_group_id and identity_link_tokens
    if hfd is not None:
        grp_id, link_tokens = hfd.extract_identity_tokens_and_group(
            rel_or_image_path=path_str,
            subset_name=subset,
            source_container=container,
        )
    else:
        # Fallback grouping
        grp_id = f"{container or subset}::vid::{stem}"
        link_tokens = [grp_id]

    label = CLASS_TO_ID.get(cls_name or "manipulated", 2)
    return {
        "class_name": cls_name or "manipulated",
        "label": label,
        "source_subset": subset,
        "source_container": container or subset,
        "source_group_id": grp_id,
        "identity_tokens": link_tokens,
        "manipulation_method": method,
        "dataset_source": dataset_source,
        "resolution_reason": reason,
    }


def extract_faces_from_video(
    video_path: Path,
    output_dir: Path,
    detector: BaseFaceDetector,
    frame_interval: int = 15,
    max_frames_per_video: Optional[int] = 50,
    crop_size: int = 256,
    margin_percent: float = 0.25,
    min_face_size: int = 64,
    confidence_threshold: float = 0.5,
    max_faces_per_frame: int = 2,
    dedup_threshold: int = 4,
    metadata_override: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extract face crops from a single video file.

    Features:
    - Never centre-crops on face detection failure.
    - Gracefully handles corrupt frames without crashing.
    - Suppresses near-duplicate face crops within the video using perceptual dhash.
    - Saves crops in standard JPEG format under `{output_dir}/{class_name}/{source_subset}/`.
    """
    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("Failed to open video file: %s", video_path)
        return [], {"status": "failed_open", "error": "cv2_open_failed"}

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)

    meta = metadata_override or resolve_video_metadata(video_path)
    cls_name = meta["class_name"]
    subset = meta["source_subset"]

    sub_dir = output_dir / cls_name / subset
    sub_dir.mkdir(parents=True, exist_ok=True)

    extracted_records: List[Dict[str, Any]] = []
    video_dhashes: List[str] = []

    frame_idx = 0
    sampled_count = 0
    corrupt_count = 0
    no_face_count = 0
    small_face_count = 0
    duplicate_count = 0

    try:
        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                sampled_count += 1
                if frame_bgr is None or frame_bgr.size == 0:
                    corrupt_count += 1
                    frame_idx += 1
                    continue

                detections = detector.detect(frame_bgr)
                if not detections:
                    # STRICT RULE: NEVER fall back to center crop on detection failure!
                    no_face_count += 1
                    frame_idx += 1
                    continue

                # Filter detections by min_face_size and confidence threshold
                valid_detections = [
                    d
                    for d in detections
                    if d.width >= min_face_size
                    and d.height >= min_face_size
                    and d.confidence >= confidence_threshold
                ]
                if not valid_detections:
                    small_face_count += len(detections)
                    frame_idx += 1
                    continue

                for face_idx, det in enumerate(valid_detections[:max_faces_per_frame]):
                    try:
                        crop_bgr = extract_square_face_crop(
                            frame_bgr,
                            det,
                            crop_size=crop_size,
                            margin_percent=margin_percent,
                        )
                    except Exception as exc:
                        logger.debug("Failed crop on frame %d, face %d: %s", frame_idx, face_idx, exc)
                        continue

                    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                    pil_crop = Image.fromarray(crop_rgb)
                    crop_dhash = compute_dhash_string(pil_crop, hash_size=8)

                    # Deduplication check against previously accepted faces in this video
                    is_dup = False
                    if dedup_threshold > 0:
                        for prev_hash in video_dhashes:
                            if compute_hamming_distance(crop_dhash, prev_hash) <= dedup_threshold:
                                is_dup = True
                                break
                    if is_dup:
                        duplicate_count += 1
                        continue

                    # Save crop image
                    filename = f"{video_path.stem}_f{frame_idx:06d}_face{face_idx}.jpg"
                    out_path = sub_dir / filename
                    pil_crop.save(out_path, format="JPEG", quality=95)

                    raw_bytes = out_path.read_bytes()
                    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
                    md5_hex = hashlib.md5(raw_bytes).hexdigest()

                    rel_path = out_path.relative_to(output_dir).as_posix()
                    record = {
                        "image_path": rel_path,
                        "class_name": cls_name,
                        "label": meta["label"],
                        "source_subset": subset,
                        "source_container": meta["source_container"],
                        "source_group_id": meta["source_group_id"],
                        "identity_tokens": meta["identity_tokens"],
                        "source_video": str(video_path).replace("\\", "/"),
                        "source_video_stem": video_path.stem,
                        "frame_number": frame_idx,
                        "timestamp_sec": round(frame_idx / fps, 3),
                        "face_index": face_idx,
                        "bounding_box": {
                            "x": det.x,
                            "y": det.y,
                            "width": det.width,
                            "height": det.height,
                        },
                        "detection_confidence": det.confidence,
                        "manipulation_method": meta["manipulation_method"],
                        "dataset_source": meta["dataset_source"],
                        "sha256": sha256_hex,
                        "md5": md5_hex,
                        "dhash": crop_dhash,
                        "dimensions": [crop_size, crop_size],
                        "format": "JPEG",
                    }
                    extracted_records.append(record)
                    video_dhashes.append(crop_dhash)

                if max_frames_per_video and len(extracted_records) >= max_frames_per_video:
                    break

            frame_idx += 1
    finally:
        cap.release()

    stats = {
        "status": "completed",
        "total_video_frames": total_frames,
        "frames_sampled": sampled_count,
        "frames_corrupt": corrupt_count,
        "frames_no_face": no_face_count,
        "faces_too_small": small_face_count,
        "duplicate_crops_skipped": duplicate_count,
        "faces_extracted": len(extracted_records),
    }
    return extracted_records, stats


def discover_video_files(input_dir_or_file: Path) -> List[Path]:
    """Find all valid video files from directory or single file path."""
    p = Path(input_dir_or_file)
    if not p.exists():
        raise FileNotFoundError(f"Input path does not exist: {p}")
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
            return [p]
        # Text file with video paths
        if p.suffix.lower() in (".txt", ".csv"):
            lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
            return [Path(line) for line in lines if Path(line).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS]
        raise ValueError(f"Unsupported input file format: {p}")

    videos: List[Path] = []
    for ext in sorted(SUPPORTED_VIDEO_EXTENSIONS):
        videos.extend(p.rglob(f"*{ext}"))
        videos.extend(p.rglob(f"*{ext.upper()}"))
    return sorted(set(videos))


def process_video_extraction(
    input_source: Path,
    output_dir: Path,
    detector: Optional[BaseFaceDetector] = None,
    frame_interval: int = 15,
    max_frames_per_video: Optional[int] = 50,
    max_videos: Optional[int] = None,
    crop_size: int = 256,
    margin_percent: float = 0.25,
    min_face_size: int = 64,
    confidence_threshold: float = 0.5,
    max_faces_per_frame: int = 2,
    dedup_threshold: int = 4,
    manifest_name: str = "extracted_faces_manifest.json",
    log_interval: int = 10,
) -> Dict[str, Any]:
    """
    Batch extraction runner across multiple videos.

    Generates:
    - `{output_dir}/extracted_faces_manifest.json` (Stage 1 compatible)
    - `{output_dir}/extraction_report.json`
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if detector is None:
        detector = HaarFaceDetector(min_size=min_face_size)

    video_files = discover_video_files(input_source)
    if max_videos and max_videos > 0:
        video_files = video_files[:max_videos]

    total_videos = len(video_files)
    logger.info("Found %d video files to process under %s", total_videos, input_source)

    all_records: List[Dict[str, Any]] = []
    video_summaries: Dict[str, Any] = {}
    total_faces = 0
    failed_videos = 0

    start_time = time.time()
    for idx, vpath in enumerate(video_files, 1):
        try:
            records, stats = extract_faces_from_video(
                video_path=vpath,
                output_dir=output_dir,
                detector=detector,
                frame_interval=frame_interval,
                max_frames_per_video=max_frames_per_video,
                crop_size=crop_size,
                margin_percent=margin_percent,
                min_face_size=min_face_size,
                confidence_threshold=confidence_threshold,
                max_faces_per_frame=max_faces_per_frame,
                dedup_threshold=dedup_threshold,
            )
            all_records.extend(records)
            total_faces += len(records)
            video_summaries[vpath.name] = stats
            if stats.get("status") != "completed":
                failed_videos += 1
        except Exception as exc:
            logger.error("Failed processing video '%s': %s", vpath, exc, exc_info=True)
            failed_videos += 1
            video_summaries[vpath.name] = {"status": "error", "error": str(exc)}

        if idx % log_interval == 0 or idx == total_videos:
            elapsed = time.time() - start_time
            logger.info(
                "Progress: %d/%d videos (%.1f%%) | Extracted: %d faces | Elapsed: %.1fs",
                idx,
                total_videos,
                (idx / total_videos) * 100,
                total_faces,
                elapsed,
            )

    # Compile class counts and subset counts
    class_counts: Dict[str, int] = {name: 0 for name in CLASS_NAMES}
    subset_counts: Dict[str, int] = {}
    for r in all_records:
        class_counts[r["class_name"]] = class_counts.get(r["class_name"], 0) + 1
        subset_counts[r["source_subset"]] = subset_counts.get(r["source_subset"], 0) + 1

    manifest_payload: Dict[str, Any] = {
        "schema_version": "1.1.0",
        "dataset_name": "TruthLens-Extracted-Video-Faces",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "class_names": list(CLASS_NAMES),
        "class_to_id": dict(CLASS_TO_ID),
        "total_images": len(all_records),
        "class_totals": class_counts,
        "subset_counts": subset_counts,
        "extraction_config": {
            "input_source": str(input_source),
            "frame_interval": frame_interval,
            "max_frames_per_video": max_frames_per_video,
            "crop_size": crop_size,
            "margin_percent": margin_percent,
            "min_face_size": min_face_size,
            "confidence_threshold": confidence_threshold,
            "max_faces_per_frame": max_faces_per_frame,
            "dedup_threshold": dedup_threshold,
        },
        "summary": {
            "total_videos_found": total_videos,
            "videos_processed": total_videos - failed_videos,
            "videos_failed": failed_videos,
            "total_faces_extracted": total_faces,
            "elapsed_seconds": round(time.time() - start_time, 2),
        },
        "images": all_records,
    }

    manifest_path = output_dir / manifest_name
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    logger.info("Saved extracted faces manifest to: %s", manifest_path)

    report_payload: Dict[str, Any] = {
        "manifest_path": str(manifest_path),
        "summary": manifest_payload["summary"],
        "class_totals": class_counts,
        "subset_counts": subset_counts,
        "video_summaries": video_summaries,
    }
    report_path = output_dir / "extraction_report.json"
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    logger.info("Saved extraction report to: %s", report_path)

    return manifest_payload


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="TruthLens Video-to-Face Extraction Pipeline for FF++, Celeb-DF-v2, and DFDC",
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        help="Input video file, directory containing videos, or text file listing video paths.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        required=True,
        type=Path,
        help="Output directory to store extracted face images and manifest.",
    )
    parser.add_argument(
        "--frame-interval",
        type=int,
        default=15,
        help="Sample every N-th frame (default: 15).",
    )
    parser.add_argument(
        "--max-frames-per-video",
        type=int,
        default=50,
        help="Maximum face crops to extract per video (default: 50, 0 for unlimited).",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="Optional ceiling on number of videos to process.",
    )
    parser.add_argument(
        "--crop-size",
        type=int,
        default=256,
        help="Output square image size in pixels (default: 256).",
    )
    parser.add_argument(
        "--margin-percent",
        type=float,
        default=0.25,
        help="Padding margin around face bounding box (default: 0.25 for 25%%).",
    )
    parser.add_argument(
        "--min-face-size",
        type=int,
        default=64,
        help="Minimum face width/height in pixels (default: 64).",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Minimum face detection confidence (default: 0.5).",
    )
    parser.add_argument(
        "--max-faces-per-frame",
        type=int,
        default=2,
        help="Maximum faces to extract per sampled frame (default: 2).",
    )
    parser.add_argument(
        "--dedup-threshold",
        type=int,
        default=4,
        help="Hamming distance threshold for intra-video duplicate crop suppression (default: 4, 0 to disable).",
    )
    parser.add_argument(
        "--manifest-name",
        type=str,
        default="extracted_faces_manifest.json",
        help="Name of output JSON manifest (default: extracted_faces_manifest.json).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose DEBUG logging.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    max_frames = None if args.max_frames_per_video <= 0 else args.max_frames_per_video
    result = process_video_extraction(
        input_source=args.input,
        output_dir=args.output_dir,
        frame_interval=args.frame_interval,
        max_frames_per_video=max_frames,
        max_videos=args.max_videos,
        crop_size=args.crop_size,
        margin_percent=args.margin_percent,
        min_face_size=args.min_face_size,
        confidence_threshold=args.confidence_threshold,
        max_faces_per_frame=args.max_faces_per_frame,
        dedup_threshold=args.dedup_threshold,
        manifest_name=args.manifest_name,
    )
    print("\n=== Video Face Extraction Summary ===")
    print(f"Total Videos:   {result['summary']['total_videos_found']}")
    print(f"Processed:      {result['summary']['videos_processed']}")
    print(f"Failed:         {result['summary']['videos_failed']}")
    print(f"Faces Extracted:{result['summary']['total_faces_extracted']}")
    print(f"Class Counts:   {result['class_totals']}")
    print(f"Elapsed:        {result['summary']['elapsed_seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
