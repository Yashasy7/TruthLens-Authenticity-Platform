"""
TruthLens AI/ML — Dataset Preparation & Stratified Splitting Framework
Prepares the DeepFakeDetection dataset (or any binary Real/Fake dataset)
for reproducible, stratified 80/10/10 Train/Validation/Test training and evaluation.

Features:
  - Stratified 80/10/10 split with deterministic seeding (seed=42).
  - Preserves source datasets: source files are read-only and never modified, moved, or deleted.
  - Prefers NTFS hard links (os.link) on Windows to consume 0 additional disk space;
    safely falls back to file copy if hard links are unavailable.
  - Generates output structure:
      <output_dir>/
        train/{real,fake}/
        val/{real,fake}/
        test/{real,fake}/
        split_manifest.json
  - Strict verification: asserts exact counts and zero data leakage across splits.
  - Safe, idempotent reruns: skips already-linked files and maintains split consistency.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
from pathlib import Path
import random
import shutil
import time
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.prepare_dataset")

VALID_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def collect_class_files(class_dir: Path) -> List[Path]:
    """
    Collect and sort all valid image files in a class directory.
    Sorting ensures deterministic ordering before pseudorandom shuffling.
    """
    if not class_dir.is_dir():
        raise FileNotFoundError(f"Class directory not found: {class_dir.resolve()}")

    files = [
        f for f in class_dir.iterdir()
        if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
    ]
    files.sort(key=lambda p: p.name)
    logger.info("Discovered %d images in %s", len(files), class_dir)
    return files


def partition_files(
    files: List[Path],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[Path], List[Path], List[Path]]:
    """
    Partition a sorted list of files into train, validation, and test subsets.
    Uses a dedicated Random generator with fixed seed for guaranteed reproducibility.
    """
    if not (0.999 <= train_ratio + val_ratio + test_ratio <= 1.001):
        raise ValueError(
            f"Split ratios must sum to 1.0 (got {train_ratio} + {val_ratio} + {test_ratio} = {train_ratio + val_ratio + test_ratio})"
        )

    n_total = len(files)
    if n_total == 0:
        raise ValueError("Cannot partition empty list of files.")

    # Shuffle deterministically
    shuffled = list(files)
    rng = random.Random(seed)
    rng.shuffle(shuffled)

    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_subset = shuffled[:n_train]
    val_subset = shuffled[n_train:n_train + n_val]
    test_subset = shuffled[n_train + n_val:]

    logger.info(
        "Partitioned %d files -> Train: %d (%.1f%%), Val: %d (%.1f%%), Test: %d (%.1f%%)",
        n_total,
        len(train_subset),
        len(train_subset) / n_total * 100,
        len(val_subset),
        len(val_subset) / n_total * 100,
        len(test_subset),
        len(test_subset) / n_total * 100,
    )
    return train_subset, val_subset, test_subset


def link_or_copy_file(src: Path, dst: Path, strategy: str = "auto") -> str:
    """
    Create a hard link or copy of src at dst.
    Returns:
      "skipped" if dst already exists and points to src,
      "hardlink" if hard link succeeded,
      "copy" if copied.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Check for safe rerun / idempotency
    if dst.exists():
        try:
            if os.path.samefile(src, dst):
                return "skipped"
        except (OSError, ValueError):
            pass

        # If file size and mtime match, avoid redundant copy
        if dst.stat().st_size == src.stat().st_size:
            return "skipped"

        # Otherwise remove mismatched destination file before re-linking
        dst.unlink()

    if strategy in ("auto", "hardlink"):
        try:
            os.link(src, dst)
            return "hardlink"
        except OSError as exc:
            if strategy == "hardlink":
                raise OSError(f"Hard link failed from {src} to {dst}: {exc}") from exc
            # Auto fallback to copy
            shutil.copy2(src, dst)
            return "copy"
    elif strategy == "copy":
        shutil.copy2(src, dst)
        return "copy"
    else:
        raise ValueError(f"Unknown link strategy: {strategy}")


def verify_dataset_splits(
    output_dir: Path,
    expected_counts: Optional[Dict[str, Dict[str, int]]] = None,
) -> Dict[str, Any]:
    """
    Verify split directory integrity:
      1. Every split/class directory matches expected counts.
      2. No source image filename appears across multiple splits (disjointness).
      3. All destination files exist and are non-empty.
    """
    output_dir = Path(output_dir).resolve()
    splits = ["train", "val", "test"]
    classes = ["real", "fake"]

    counts: Dict[str, Dict[str, int]] = {}
    files_by_split_and_class: Dict[Tuple[str, str], Set[str]] = {}

    for split in splits:
        counts[split] = {}
        for cls_name in classes:
            target_dir = output_dir / split / cls_name
            if not target_dir.is_dir():
                raise FileNotFoundError(f"Missing expected directory: {target_dir}")

            file_names = set()
            for f in target_dir.iterdir():
                if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS:
                    if f.stat().st_size == 0:
                        raise ValueError(f"Encountered 0-byte corrupt file in split: {f}")
                    file_names.add(f.name)

            counts[split][cls_name] = len(file_names)
            files_by_split_and_class[(split, cls_name)] = file_names

    # Check expected counts if provided
    if expected_counts:
        for split in splits:
            for cls_name in classes:
                expected = expected_counts.get(split, {}).get(cls_name)
                actual = counts[split][cls_name]
                if expected is not None and actual != expected:
                    raise ValueError(
                        f"Count mismatch in {split}/{cls_name}: expected {expected}, found {actual}"
                    )

    # Disjointness checks: ensure no leakage between train, val, and test for the same class
    for cls_name in classes:
        train_set = files_by_split_and_class[("train", cls_name)]
        val_set = files_by_split_and_class[("val", cls_name)]
        test_set = files_by_split_and_class[("test", cls_name)]

        train_val_leak = train_set & val_set
        train_test_leak = train_set & test_set
        val_test_leak = val_set & test_set

        if train_val_leak:
            raise RuntimeError(
                f"Data leakage detected! {len(train_val_leak)} {cls_name} file(s) in both train and val: {list(train_val_leak)[:5]}"
            )
        if train_test_leak:
            raise RuntimeError(
                f"Data leakage detected! {len(train_test_leak)} {cls_name} file(s) in both train and test: {list(train_test_leak)[:5]}"
            )
        if val_test_leak:
            raise RuntimeError(
                f"Data leakage detected! {len(val_test_leak)} {cls_name} file(s) in both val and test: {list(val_test_leak)[:5]}"
            )

    logger.info("Integrity verification passed successfully! All splits are strictly disjoint.")
    return counts


def prepare_dataset(
    source_dir: Path | str,
    output_dir: Path | str,
    seed: int = 42,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    strategy: str = "auto",
    force: bool = False,
) -> Dict[str, Any]:
    """
    Main dataset preparation pipeline.
    """
    src_path = Path(source_dir).resolve()
    out_path = Path(output_dir).resolve()
    manifest_path = out_path / "split_manifest.json"

    logger.info("=" * 70)
    logger.info("TruthLens Image Dataset Preparation")
    logger.info("Source Directory : %s", src_path)
    logger.info("Output Directory : %s", out_path)
    logger.info("Random Seed      : %d", seed)
    logger.info("Split Ratios     : Train=%.2f, Val=%.2f, Test=%.2f", train_ratio, val_ratio, test_ratio)
    logger.info("=" * 70)

    # 1. Identify source class folders (supports real/fake, nature/ai, authentic/synthetic)
    real_dir = None
    fake_dir = None
    for cand in ["real", "nature", "authentic"]:
        if (src_path / cand).is_dir():
            real_dir = src_path / cand
            break
    for cand in ["fake", "ai", "synthetic"]:
        if (src_path / cand).is_dir():
            fake_dir = src_path / cand
            break

    if not real_dir or not fake_dir:
        raise FileNotFoundError(
            f"Source dataset at {src_path} must contain 'real' and 'fake' folders."
        )

    # 2. Collect files
    real_files = collect_class_files(real_dir)
    fake_files = collect_class_files(fake_dir)

    if len(real_files) == 0 or len(fake_files) == 0:
        raise ValueError(
            f"Source folders must contain valid image files (found {len(real_files)} real, {len(fake_files)} fake)"
        )

    # 3. Check for existing manifest on rerun
    split_assignments: Dict[str, str] = {}
    if manifest_path.is_file() and not force:
        logger.info("Existing manifest detected at %s. Verifying split assignments...", manifest_path)
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                existing_manifest = json.load(f)
            if existing_manifest.get("seed") == seed and "splits" in existing_manifest:
                split_assignments = existing_manifest["splits"]
                logger.info("Reusing %d verified split assignments from existing manifest.", len(split_assignments))
        except Exception as exc:
            logger.warning("Could not read existing manifest (%s); recomputing partitions.", exc)
            split_assignments = {}

    # 4. Partition files if not already populated from manifest
    if not split_assignments:
        real_train, real_val, real_test = partition_files(
            real_files, train_ratio, val_ratio, test_ratio, seed=seed
        )
        fake_train, fake_val, fake_test = partition_files(
            fake_files, train_ratio, val_ratio, test_ratio, seed=seed
        )

        for f in real_train:
            split_assignments[f"real/{f.name}"] = "train"
        for f in real_val:
            split_assignments[f"real/{f.name}"] = "val"
        for f in real_test:
            split_assignments[f"real/{f.name}"] = "test"

        for f in fake_train:
            split_assignments[f"fake/{f.name}"] = "train"
        for f in fake_val:
            split_assignments[f"fake/{f.name}"] = "val"
        for f in fake_test:
            split_assignments[f"fake/{f.name}"] = "test"

    # 5. Execute linking / copying
    out_path.mkdir(parents=True, exist_ok=True)
    strategy_counts = {"hardlink": 0, "copy": 0, "skipped": 0}
    start_time = time.time()
    total_files = len(real_files) + len(fake_files)
    processed = 0

    all_tasks: List[Tuple[Path, Path]] = []
    for rel_path, split_name in split_assignments.items():
        cls_name, fname = rel_path.split("/", 1)
        src_file = (real_dir if cls_name == "real" else fake_dir) / fname
        dst_file = out_path / split_name / cls_name / fname
        all_tasks.append((src_file, dst_file))

    logger.info("Processing %d image files into output splits...", len(all_tasks))
    log_interval = max(1000, len(all_tasks) // 10)

    for src_file, dst_file in all_tasks:
        result = link_or_copy_file(src_file, dst_file, strategy=strategy)
        strategy_counts[result] += 1
        processed += 1

        if processed % log_interval == 0 or processed == total_files:
            elapsed = time.time() - start_time
            logger.info(
                "Progress: %d / %d (%.1f%%) — %d/s (Hard links: %d, Copies: %d, Skipped: %d)",
                processed,
                total_files,
                processed / total_files * 100,
                int(processed / elapsed) if elapsed > 0 else 0,
                strategy_counts["hardlink"],
                strategy_counts["copy"],
                strategy_counts["skipped"],
            )

    # 6. Verify result counts and disjointness
    expected = {
        "train": {
            "real": int(len(real_files) * train_ratio),
            "fake": int(len(fake_files) * train_ratio),
        },
        "val": {
            "real": int(len(real_files) * val_ratio),
            "fake": int(len(fake_files) * val_ratio),
        },
        "test": {
            "real": len(real_files) - int(len(real_files) * train_ratio) - int(len(real_files) * val_ratio),
            "fake": len(fake_files) - int(len(fake_files) * train_ratio) - int(len(fake_files) * val_ratio),
        },
    }
    actual_counts = verify_dataset_splits(out_path, expected_counts=expected)

    # 7. Write / Update manifest
    manifest_data = {
        "dataset_name": src_path.name,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": seed,
        "source_directory": str(src_path),
        "output_directory": str(out_path),
        "ratios": {
            "train": train_ratio,
            "val": val_ratio,
            "test": test_ratio,
        },
        "counts": {
            "train": {
                "real": actual_counts["train"]["real"],
                "fake": actual_counts["train"]["fake"],
                "total": actual_counts["train"]["real"] + actual_counts["train"]["fake"],
            },
            "val": {
                "real": actual_counts["val"]["real"],
                "fake": actual_counts["val"]["fake"],
                "total": actual_counts["val"]["real"] + actual_counts["val"]["fake"],
            },
            "test": {
                "real": actual_counts["test"]["real"],
                "fake": actual_counts["test"]["fake"],
                "total": actual_counts["test"]["real"] + actual_counts["test"]["fake"],
            },
            "grand_total": total_files,
        },
        "link_stats": strategy_counts,
        "splits": split_assignments,
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    logger.info("Saved split manifest to: %s", manifest_path)

    elapsed_total = time.time() - start_time
    logger.info("=" * 70)
    logger.info("Dataset Preparation Complete in %.2f seconds", elapsed_total)
    logger.info("Train: %d real + %d fake = %d total", actual_counts['train']['real'], actual_counts['train']['fake'], actual_counts['train']['real'] + actual_counts['train']['fake'])
    logger.info("Val  : %d real + %d fake = %d total", actual_counts['val']['real'], actual_counts['val']['fake'], actual_counts['val']['real'] + actual_counts['val']['fake'])
    logger.info("Test : %d real + %d fake = %d total", actual_counts['test']['real'], actual_counts['test']['fake'], actual_counts['test']['real'] + actual_counts['test']['fake'])
    logger.info("=" * 70)

    return manifest_data


def main() -> None:
    parser = argparse.ArgumentParser(description="TruthLens Image Dataset Stratified Splitting Framework")
    parser.add_argument("--source-dir", type=Path, default=Path("datasets/DeepFakeDetection"), help="Source dataset containing real/ and fake/")
    parser.add_argument("--output-dir", type=Path, default=Path("ai-ml/data/deepfake_detection"), help="Destination directory for splits")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for deterministic shuffling")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split fraction (default: 0.8)")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split fraction (default: 0.1)")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="Test split fraction (default: 0.1)")
    parser.add_argument("--strategy", type=str, choices=["auto", "hardlink", "copy"], default="auto", help="File linking strategy")
    parser.add_argument("--force", action="store_true", help="Force recalculating splits and overwriting manifest")
    parser.add_argument("--verify-only", action="store_true", help="Only verify integrity of existing splits against expected counts")

    args = parser.parse_args()

    if args.verify_only:
        logger.info("Verifying existing dataset splits in %s...", args.output_dir)
        verify_dataset_splits(args.output_dir)
        logger.info("Verification passed!")
        return

    prepare_dataset(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        strategy=args.strategy,
        force=args.force,
    )


if __name__ == "__main__":
    main()
