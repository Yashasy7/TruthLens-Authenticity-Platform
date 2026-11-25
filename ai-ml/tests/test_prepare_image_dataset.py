"""
Focused tests for the TruthLens Image Dataset Preparation Framework.

Verifies:
  1. Stratified 80/10/10 partitioning determinism, reproducibility, and disjointness (seed=42).
  2. Idempotency and safe rerun handling without data duplication.
  3. Data leakage and count mismatch detection in verify_dataset_splits.
  4. End-to-end dataset preparation and manifest generation.
  5. Full backward compatibility with trainer.py (discover_dataset_splits) and evaluate_image.py (discover_test_samples).
"""

from pathlib import Path
import json
import pytest
from PIL import Image

import prepare_image_dataset
from prepare_image_dataset import (
    collect_class_files,
    partition_files,
    link_or_copy_file,
    prepare_dataset,
    verify_dataset_splits,
)
from services.image_analysis.trainer import discover_dataset_splits
from evaluate_image import discover_test_samples


def _create_dummy_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (32, 32), color=(128, 128, 128))
    img.save(path)


def test_partition_files_reproducibility():
    """Verify deterministic 80/10/10 partitioning with seed=42 and complete disjointness."""
    dummy_files = [Path(f"file_{i:04d}.jpg") for i in range(100)]

    train1, val1, test1 = partition_files(dummy_files, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42)
    train2, val2, test2 = partition_files(dummy_files, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42)

    # Identical across repeated calls with seed=42
    assert [p.name for p in train1] == [p.name for p in train2]
    assert [p.name for p in val1] == [p.name for p in val2]
    assert [p.name for p in test1] == [p.name for p in test2]

    # Exact counts
    assert len(train1) == 80
    assert len(val1) == 10
    assert len(test1) == 10

    # Strict disjointness
    set_train = set(p.name for p in train1)
    set_val = set(p.name for p in val1)
    set_test = set(p.name for p in test1)

    assert set_train & set_val == set()
    assert set_train & set_test == set()
    assert set_val & set_test == set()
    assert len(set_train | set_val | set_test) == 100

    # Different seed yields different ordering
    train_alt, _, _ = partition_files(dummy_files, seed=99)
    assert [p.name for p in train1] != [p.name for p in train_alt]


def test_link_or_copy_idempotency(tmp_path: Path):
    """Verify link_or_copy_file is idempotent on repeated runs."""
    src = tmp_path / "src" / "image.jpg"
    _create_dummy_image(src)

    dst = tmp_path / "dst" / "image.jpg"

    # First run: copies or links
    res1 = link_or_copy_file(src, dst, strategy="copy")
    assert res1 == "copy"
    assert dst.is_file()

    # Second run: detects existing matching file and skips
    res2 = link_or_copy_file(src, dst, strategy="copy")
    assert res2 == "skipped"


def test_verify_dataset_splits_leakage_detection(tmp_path: Path):
    """Verify verify_dataset_splits flags data leakage and count mismatches."""
    out_dir = tmp_path / "splits"

    # Create disjoint structure
    _create_dummy_image(out_dir / "train" / "real" / "img1.jpg")
    _create_dummy_image(out_dir / "val" / "real" / "img2.jpg")
    _create_dummy_image(out_dir / "test" / "real" / "img3.jpg")
    _create_dummy_image(out_dir / "train" / "fake" / "fake1.jpg")
    _create_dummy_image(out_dir / "val" / "fake" / "fake2.jpg")
    _create_dummy_image(out_dir / "test" / "fake" / "fake3.jpg")

    counts = verify_dataset_splits(out_dir)
    assert counts["train"]["real"] == 1
    assert counts["val"]["real"] == 1
    assert counts["test"]["real"] == 1

    # Inject data leakage: copy img1.jpg into val/real
    _create_dummy_image(out_dir / "val" / "real" / "img1.jpg")
    with pytest.raises(RuntimeError, match="Data leakage detected"):
        verify_dataset_splits(out_dir)


def test_prepare_dataset_full_flow(tmp_path: Path):
    """Verify full dataset preparation, directory layout, manifest output, and idempotency."""
    src_dir = tmp_path / "source"
    out_dir = tmp_path / "out"

    # Create 20 real and 20 fake dummy images
    for i in range(20):
        _create_dummy_image(src_dir / "real" / f"real_{i:03d}.jpg")
        _create_dummy_image(src_dir / "fake" / f"fake_{i:03d}.jpg")

    # Run preparation with copy strategy for sandboxed unit test
    manifest = prepare_dataset(
        source_dir=src_dir,
        output_dir=out_dir,
        seed=42,
        train_ratio=0.8,
        val_ratio=0.1,
        test_ratio=0.1,
        strategy="copy",
    )

    # Expected counts: 80% of 20 = 16, 10% of 20 = 2, 10% of 20 = 2
    assert manifest["counts"]["train"]["real"] == 16
    assert manifest["counts"]["train"]["fake"] == 16
    assert manifest["counts"]["val"]["real"] == 2
    assert manifest["counts"]["val"]["fake"] == 2
    assert manifest["counts"]["test"]["real"] == 2
    assert manifest["counts"]["test"]["fake"] == 2

    # Verify manifest file exists on disk
    manifest_file = out_dir / "split_manifest.json"
    assert manifest_file.is_file()
    with open(manifest_file, "r", encoding="utf-8") as f:
        loaded_manifest = json.load(f)
        assert loaded_manifest["seed"] == 42
        assert len(loaded_manifest["splits"]) == 40

    # Rerun test: verify idempotency
    manifest_rerun = prepare_dataset(
        source_dir=src_dir,
        output_dir=out_dir,
        seed=42,
        strategy="copy",
    )
    assert manifest_rerun["counts"]["grand_total"] == 40
    assert manifest_rerun["link_stats"]["skipped"] == 40

    # Compatibility Test 1: Verify trainer.py discovers the splits
    train_samples, val_samples, test_paths = discover_dataset_splits(out_dir)
    assert len(train_samples) == 32  # 16 real + 16 fake
    assert len(val_samples) == 4    # 2 real + 2 fake
    assert len(test_paths) == 1
    assert test_paths[0] == out_dir / "test"

    # Compatibility Test 2: Verify evaluate_image.py discovers the test split
    test_samples = discover_test_samples(out_dir)
    assert len(test_samples) == 4   # 2 real + 2 fake
    labels = {p.name: label for p, label in test_samples}
    assert any("real" in name and label == 0.0 for name, label in labels.items())
    assert any("fake" in name and label == 1.0 for name, label in labels.items())
