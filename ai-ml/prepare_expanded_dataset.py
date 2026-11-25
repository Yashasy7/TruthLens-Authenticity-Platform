"""
TruthLens AI/ML — Expanded Dataset Preparation & Multi-Domain Pipeline
Blueprint: Module 05 — Image Authenticity Analysis
Cross-Generator Generalization Expansion Protocol

Prepares the multi-domain expanded dataset under:
    ai-ml/data/expanded_image_detection/
Supporting:
  1. human_portraits/          (Retained FFHQ / StyleGAN2 benchmark domain)
  2. photographic_scenes/       (GenImage Stable Diffusion v1.5 & Midjourney domain)
  3. cartoons_illustrations/    (Curated digital art & diffusion illustration domain)
  4. modern_ai/                 (Unseen evaluation benchmark: ChatGPT, Gemini, Grok/Flux)

Preserves existing datasets, performs image validation, verifies zero cross-split leakage,
and generates a structured manifest: expanded_manifest.json.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.expanded_dataset")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "ai-ml" / "data" / "deepfake_detection"
DEFAULT_TARGET_DIR = PROJECT_ROOT / "ai-ml" / "data" / "expanded_image_detection"

VALID_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def compute_md5(file_path: Path) -> str:
    """Compute MD5 checksum of an image file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_image(file_path: Path) -> Tuple[bool, Tuple[int, int], str]:
    """
    Verify that an image file can be decoded and read.
    Returns (is_valid, (width, height), format_name).
    """
    try:
        with Image.open(file_path) as img:
            img.verify()
        with Image.open(file_path) as img:
            size = img.size
            fmt = img.format or "UNKNOWN"
            img.load()
        return True, size, fmt
    except Exception as exc:
        logger.warning("Corrupted image detected: %s (%s)", file_path, exc)
        return False, (0, 0), "CORRUPTED"


def safe_link_or_copy(source_path: Path, target_path: Path) -> str:
    """
    Hard-link source to target to consume 0 additional disk space;
    fall back to copy if hard links fail across filesystems.
    """
    if target_path.exists():
        return "skipped"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(str(source_path), str(target_path))
        return "hardlink"
    except (OSError, NotImplementedError):
        shutil.copy2(str(source_path), str(target_path))
        return "copy"


def prepare_retained_faces(
    source_dir: Path,
    target_dir: Path,
    total_real: int = 2500,
    total_fake: int = 2500,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Sample exactly total_real and total_fake images from deepfake_detection
    preserving the original 80/10/10 split boundaries to ensure zero leakage.

    Split allocation:
      - Train: 80% (2,000 Real, 2,000 Fake)
      - Val:   10% (250 Real, 250 Fake)
      - Test:  10% (250 Real, 250 Fake)
    """
    split_ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
    rng = random.Random(seed)
    manifest_entries: List[Dict[str, Any]] = []
    link_stats = {"hardlink": 0, "copy": 0, "skipped": 0}

    domain_dir = target_dir / "human_portraits"
    seen_hashes: Set[str] = set()

    for split_name, ratio in split_ratios.items():
        n_real = int(total_real * ratio)
        n_fake = int(total_fake * ratio)

        for label_name, target_count, label_val, generator_name in [
            ("real", n_real, 0, "None (FFHQ)"),
            ("fake", n_fake, 1, "StyleGAN2"),
        ]:
            src_folder = source_dir / split_name / label_name
            if not src_folder.is_dir():
                raise FileNotFoundError(f"Missing source folder: {src_folder}")

            src_files = sorted([
                f for f in src_folder.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
            ], key=lambda p: p.name)

            if len(src_files) < target_count:
                raise ValueError(
                    f"Insufficient files in {src_folder}: requested {target_count}, found {len(src_files)}"
                )

            # Deterministic shuffle within source split
            shuffled = list(src_files)
            rng.shuffle(shuffled)
            selected = shuffled[:target_count]

            dest_folder = domain_dir / split_name / label_name
            dest_folder.mkdir(parents=True, exist_ok=True)

            for src_file in selected:
                dest_file = dest_folder / src_file.name
                action = safe_link_or_copy(src_file, dest_file)
                link_stats[action] += 1

                # Integrity check
                is_valid, dims, fmt = verify_image(dest_file)
                if not is_valid:
                    raise ValueError(f"Integrity check failed for {dest_file}")

                md5 = compute_md5(dest_file)
                if md5 in seen_hashes:
                    logger.warning("Duplicate hash detected across sample: %s (%s)", md5, dest_file)
                seen_hashes.add(md5)

                try:
                    rel_path = dest_file.relative_to(PROJECT_ROOT).as_posix()
                except ValueError:
                    rel_path = dest_file.as_posix()

                manifest_entries.append({
                    "image_path": rel_path,
                    "label": label_val,
                    "label_name": label_name,
                    "domain": "human_portraits",
                    "content_category": "human_face_portrait",
                    "source_dataset": "DeepFakeDetection",
                    "generator_name": generator_name,
                    "original_split": split_name,
                    "split": split_name,
                    "dimensions": [dims[0], dims[1]],
                    "format": fmt,
                    "file_size_bytes": dest_file.stat().st_size,
                    "md5": md5,
                })

    logger.info(
        "Prepared retained human_portraits: %d images (Hardlinks: %d, Copies: %d, Skipped: %d)",
        len(manifest_entries),
        link_stats["hardlink"],
        link_stats["copy"],
        link_stats["skipped"],
    )
    return manifest_entries, link_stats


def create_expansion_structure(target_dir: Path) -> Dict[str, Path]:
    """Create directory hierarchy for all present and future authenticity domains."""
    domains = {
        "human_portraits": target_dir / "human_portraits",
        "photographic_scenes": target_dir / "photographic_scenes",
        "cartoons_illustrations": target_dir / "cartoons_illustrations",
        "modern_ai": target_dir / "modern_ai",
    }

    for name, domain_path in domains.items():
        for split in ["train", "val", "test"]:
            for cls_name in ["real", "fake"]:
                (domain_path / split / cls_name).mkdir(parents=True, exist_ok=True)

    return domains


def verify_dataset_integrity(manifest_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify complete integrity of dataset:
      - All images exist and can be loaded.
      - Zero exact duplicates between train, val, and test splits.
      - Exact class counts and balance.
    """
    split_hashes: Dict[str, Set[str]] = {"train": set(), "val": set(), "test": set()}
    class_counts: Dict[str, Dict[str, int]] = {
        "train": {"real": 0, "fake": 0},
        "val": {"real": 0, "fake": 0},
        "test": {"real": 0, "fake": 0},
    }

    for entry in manifest_entries:
        split = entry["split"]
        label = entry["label_name"]
        md5 = entry["md5"]

        class_counts[split][label] += 1
        split_hashes[split].add(md5)

    leakage_train_val = len(split_hashes["train"] & split_hashes["val"])
    leakage_train_test = len(split_hashes["train"] & split_hashes["test"])
    leakage_val_test = len(split_hashes["val"] & split_hashes["test"])

    integrity_report = {
        "total_images": len(manifest_entries),
        "class_counts": class_counts,
        "cross_split_leakage": {
            "train_val_overlap": leakage_train_val,
            "train_test_overlap": leakage_train_test,
            "val_test_overlap": leakage_val_test,
        },
        "zero_leakage_verified": (leakage_train_val == 0 and leakage_train_test == 0 and leakage_val_test == 0),
    }
    return integrity_report


def main() -> None:
    parser = argparse.ArgumentParser(description="TruthLens Expanded Image Dataset Preparation")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR, help="Source deepfake_detection directory")
    parser.add_argument("--target-dir", type=Path, default=DEFAULT_TARGET_DIR, help="Output expanded dataset directory")
    parser.add_argument("--total-real-faces", type=int, default=2500, help="Number of real face images to sample")
    parser.add_argument("--total-fake-faces", type=int, default=2500, help="Number of fake face images to sample")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")

    args = parser.parse_args()

    logger.info("Initializing Expanded Dataset Preparation at %s", args.target_dir)

    # Step 1: Create extensible multi-domain folder layout
    create_expansion_structure(args.target_dir)

    # Step 2: Prepare retained human-portraits domain
    manifest_entries, link_stats = prepare_retained_faces(
        source_dir=args.source_dir,
        target_dir=args.target_dir,
        total_real=args.total_real_faces,
        total_fake=args.total_fake_faces,
        seed=args.seed,
    )

    # Step 3: Run comprehensive integrity and leakage checks
    integrity_report = verify_dataset_integrity(manifest_entries)
    logger.info("Integrity Verification: %s", integrity_report)

    # Step 4: Write comprehensive manifest
    manifest_payload = {
        "dataset_name": "TruthLens-Expanded-Image-Authenticity",
        "version": "1.1.0",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": args.seed,
        "target_directory": str(args.target_dir),
        "domains": {
            "human_portraits": {
                "status": "ready",
                "counts": integrity_report["class_counts"],
                "total": len(manifest_entries),
                "source": "DeepFakeDetection (FFHQ / StyleGAN2)",
            },
            "photographic_scenes": {
                "status": "pending_selective_download",
                "target_counts": {"real": 5000, "fake": 5000, "total": 10000},
                "source": "GenImage (ImageNet Real / SD 1.5 & Midjourney Fake)",
            },
            "cartoons_illustrations": {
                "status": "pending_curation",
                "target_counts": {"real": 2000, "fake": 2000, "total": 4000},
                "source": "Human Digital Art / NovelAI & DALL-E 3 Illustrations",
            },
            "modern_ai": {
                "status": "unseen_eval_benchmark",
                "target_counts": {"real": 500, "fake": 500, "total": 1000},
                "source": "Modern Web Captures / ChatGPT, Gemini, Grok (Flux)",
            },
        },
        "link_stats": link_stats,
        "integrity": integrity_report,
        "images": manifest_entries,
    }

    manifest_path = args.target_dir / "expanded_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    logger.info("Saved expanded manifest to %s (%d entries)", manifest_path, len(manifest_entries))


if __name__ == "__main__":
    main()
