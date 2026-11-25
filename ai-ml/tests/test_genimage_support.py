"""
Tests for GenImage dataset structure support and backward compatibility.

Requirements verified:
1. Support official GenImage structure: generator/{train,val}/{ai,nature}.
2. Map 'ai' -> label 1.0 (synthetic) and 'nature' -> label 0.0 (real).
3. Support generator filtering via the --generators CLI argument or argument list.
4. Official train data used for training and official val data used for validation (no random mixing).
5. Official test data isolated and excluded from training/validation.
6. Preserve compatibility with real/fake and authentic/synthetic folder layouts.
"""

from pathlib import Path
import pytest
from PIL import Image

from services.image_analysis.trainer import (
    ImageFolderAuthenticityDataset,
    discover_dataset_splits,
)


def _create_dummy_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (32, 32), color=(128, 128, 128))
    img.save(path)


def test_genimage_class_name_mapping(tmp_path: Path) -> None:
    """Verify 'ai' maps to 1.0 and 'nature' maps to 0.0."""
    ai_dir = tmp_path / "ai"
    nature_dir = tmp_path / "nature"

    _create_dummy_image(ai_dir / "gen_001.png")
    _create_dummy_image(ai_dir / "gen_002.jpg")
    _create_dummy_image(nature_dir / "real_001.png")
    _create_dummy_image(nature_dir / "real_002.jpg")

    dataset = ImageFolderAuthenticityDataset.from_directory(tmp_path)
    assert len(dataset) == 4

    labels = {path.name: label for path, label in dataset.samples}
    assert labels["gen_001.png"] == 1.0
    assert labels["gen_002.jpg"] == 1.0
    assert labels["real_001.png"] == 0.0
    assert labels["real_002.jpg"] == 0.0


def test_genimage_multi_generator_discovery(tmp_path: Path) -> None:
    """Verify official multi-generator GenImage directory layout with train/val/test splits."""
    gen1 = tmp_path / "midjourney"
    gen2 = tmp_path / "stable_diffusion"

    for gen in [gen1, gen2]:
        _create_dummy_image(gen / "train" / "ai" / "train_ai_1.png")
        _create_dummy_image(gen / "train" / "nature" / "train_nat_1.png")
        _create_dummy_image(gen / "val" / "ai" / "val_ai_1.png")
        _create_dummy_image(gen / "val" / "nature" / "val_nat_1.png")

    # Add an official test folder for gen1
    _create_dummy_image(gen1 / "test" / "ai" / "test_ai_1.png")
    _create_dummy_image(gen1 / "test" / "nature" / "test_nat_1.png")

    train_samples, val_samples, test_paths = discover_dataset_splits(tmp_path)

    # 2 generators * 2 train images = 4 train images
    assert len(train_samples) == 4
    # 2 generators * 2 val images = 4 val images
    assert len(val_samples) == 4

    # Verify no mixing: train images come strictly from train folders
    assert all("train" in str(p[0]) for p in train_samples)
    assert all("val" in str(p[0]) for p in val_samples)

    # Verify test folder was identified and no test images leaked into train/val
    assert any("test" == p.name.lower() for p in test_paths)
    all_sample_paths = [Path(p[0]) for p in train_samples + val_samples]
    assert not any("test" in [part.lower() for part in p.parts[:-2]] for p in all_sample_paths if p.parent.parent.name.lower() == "test")
    assert not any(p.parent.parent.name.lower() == "test" for p in all_sample_paths)

    # Verify label assignments
    for p, label in train_samples + val_samples:
        if "ai" in p.parent.name.lower():
            assert label == 1.0
        elif "nature" in p.parent.name.lower():
            assert label == 0.0


def test_genimage_generator_filtering(tmp_path: Path) -> None:
    """Verify filtering specific generators using the generators parameter."""
    gen1 = tmp_path / "midjourney"
    gen2 = tmp_path / "wukong"
    gen3 = tmp_path / "adm"

    for gen in [gen1, gen2, gen3]:
        _create_dummy_image(gen / "train" / "ai" / "train_ai.png")
        _create_dummy_image(gen / "train" / "nature" / "train_nat.png")
        _create_dummy_image(gen / "val" / "ai" / "val_ai.png")
        _create_dummy_image(gen / "val" / "nature" / "val_nat.png")

    # Select only midjourney and adm
    train_samples, val_samples, _ = discover_dataset_splits(
        tmp_path,
        generators=["midjourney", "adm"],
    )

    assert len(train_samples) == 4  # 2 generators * 2 images
    assert len(val_samples) == 4

    for p, _ in train_samples + val_samples:
        assert "wukong" not in str(p)
        assert "midjourney" in str(p) or "adm" in str(p)


def test_genimage_single_generator_direct(tmp_path: Path) -> None:
    """Verify pointing directly to a single generator directory with official train/val."""
    single_gen = tmp_path / "midjourney"
    _create_dummy_image(single_gen / "train" / "ai" / "train_ai.png")
    _create_dummy_image(single_gen / "train" / "nature" / "train_nat.png")
    _create_dummy_image(single_gen / "val" / "ai" / "val_ai.png")
    _create_dummy_image(single_gen / "val" / "nature" / "val_nat.png")

    train_samples, val_samples, _ = discover_dataset_splits(single_gen)

    assert len(train_samples) == 2
    assert len(val_samples) == 2
    assert all("train" in str(p[0]) for p in train_samples)
    assert all("val" in str(p[0]) for p in val_samples)


def test_cifake_backward_compatibility(tmp_path: Path) -> None:
    """Verify CIFAKE structure (train/REAL, train/FAKE, test/REAL, test/FAKE) splits train and preserves test."""
    train_dir = tmp_path / "train"
    test_dir = tmp_path / "test"

    for i in range(5):
        _create_dummy_image(train_dir / "REAL" / f"real_{i}.png")
        _create_dummy_image(train_dir / "FAKE" / f"fake_{i}.png")
        _create_dummy_image(test_dir / "REAL" / f"test_real_{i}.png")
        _create_dummy_image(test_dir / "FAKE" / f"test_fake_{i}.png")

    train_samples, val_samples, test_paths = discover_dataset_splits(
        tmp_path,
        val_split=0.2,
    )

    # 10 train images total: 8 train (80%), 2 val (20%)
    assert len(train_samples) == 8
    assert len(val_samples) == 2

    # Official test folder preserved and separate
    assert len(test_paths) == 1
    assert test_paths[0] == test_dir
    all_sample_paths = [Path(p[0]) for p in train_samples + val_samples]
    assert not any(p.parent.parent.name.lower() == "test" for p in all_sample_paths)


def test_missing_generator_raises_error(tmp_path: Path) -> None:
    """Verify requesting a non-existent generator raises FileNotFoundError."""
    _create_dummy_image(tmp_path / "midjourney" / "train" / "ai" / "img.png")

    with pytest.raises(FileNotFoundError):
        discover_dataset_splits(tmp_path, generators=["non_existent_gen"])
