"""
TruthLens AI/ML — Classifier Training & Fine-Tuning Pipeline
Blueprint Section E: PyTorch 2.2, timm
Blueprint Section K: CIFAKE / Midjourney-v6 benchmark dataset training protocol

Provides a reproducible, production-ready training workflow for the binary
authenticity classifier (Authentic = 0, Synthetic / AI-Generated = 1).
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T

from services.image_analysis.classifier import _build_model
from utils.image_utils import _IMAGENET_MEAN, _IMAGENET_STD

logger = logging.getLogger(__name__)


class ImageFolderAuthenticityDataset(Dataset):
    """
    Dataset that loads images from structured subfolders:
      - authentic / real / 0  → Label 0.0 (Authentic)
      - synthetic / fake / 1   → Label 1.0 (AI-Generated)
    """

    AUTHENTIC_NAMES = {"authentic", "real", "0", "pristine", "nature"}
    SYNTHETIC_NAMES = {"synthetic", "fake", "1", "ai_generated", "diffusion", "ai"}

    def __init__(
        self,
        samples: List[Tuple[Path, float]],
        transform: Optional[Callable[[Image.Image], torch.Tensor]] = None,
    ) -> None:
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        img_path, label = self.samples[idx]
        with Image.open(img_path) as img:
            image_rgb = img.convert("RGB")
            if self.transform is not None:
                tensor = self.transform(image_rgb)
            else:
                tensor = T.ToTensor()(image_rgb)
        return tensor, torch.tensor([label], dtype=torch.float32)

    @classmethod
    def from_directory(
        cls,
        data_dir: Path,
        transform: Optional[Callable] = None,
    ) -> "ImageFolderAuthenticityDataset":
        """Scan a directory with subdirectories for authentic and synthetic samples."""
        samples: List[Tuple[Path, float]] = []
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

        for subdir in sorted(data_dir.iterdir()):
            if not subdir.is_dir():
                continue
            name_lower = subdir.name.lower()
            if name_lower in cls.AUTHENTIC_NAMES:
                label = 0.0
            elif name_lower in cls.SYNTHETIC_NAMES:
                label = 1.0
            else:
                logger.warning("Skipping unrecognized class folder: %s", subdir.name)
                continue

            for file_path in sorted(subdir.glob("**/*")):
                if file_path.is_file() and file_path.suffix.lower() in valid_exts:
                    samples.append((file_path, label))

        logger.info("Discovered %d samples in %s", len(samples), data_dir)
        return cls(samples=samples, transform=transform)


def discover_dataset_splits(
    data_dir: Path,
    generators: Optional[List[str]] = None,
    val_split: float = 0.2,
    seed: int = 42,
) -> Tuple[List[Tuple[Path, float]], List[Tuple[Path, float]], List[Path]]:
    """
    Discover training, validation, and test splits from a dataset directory.

    Supports:
      1. Multi-generator GenImage directory:
         <data_dir>/<generator>/train/{ai,nature}
         <data_dir>/<generator>/val/{ai,nature}
         <data_dir>/<generator>/test/{ai,nature} (optional)
      2. Single-generator or split-level directory:
         <data_dir>/train/{ai,nature,real,fake,...}
         <data_dir>/val/{ai,nature,real,fake,...}
         <data_dir>/test/{ai,nature,real,fake,...} (optional)
      3. Flat class-folder directory:
         <data_dir>/{nature,ai,authentic,synthetic,real,fake,...}

    Official validation data is used directly for validation without random mixing into training.
    Official test directories are identified, preserved, and kept completely separate.
    """
    data_dir = Path(data_dir)
    train_samples: List[Tuple[Path, float]] = []
    val_samples: List[Tuple[Path, float]] = []
    test_paths: List[Path] = []

    has_direct_splits = (
        (data_dir / "train").is_dir()
        or (data_dir / "val").is_dir()
        or (data_dir / "validation").is_dir()
    )

    generator_dirs: List[Path] = []
    if generators:
        clean_gens = [g.strip() for g in generators if g.strip() and g.strip().lower() != "all"]
        if clean_gens:
            for g in clean_gens:
                cand = data_dir / g
                if cand.is_dir():
                    generator_dirs.append(cand)
                else:
                    raise FileNotFoundError(f"Requested generator directory does not exist: {cand}")
        else:
            if not has_direct_splits:
                generator_dirs = [
                    p for p in sorted(data_dir.iterdir())
                    if p.is_dir() and ((p / "train").is_dir() or (p / "val").is_dir() or (p / "validation").is_dir())
                ]
    elif not has_direct_splits:
        generator_dirs = [
            p for p in sorted(data_dir.iterdir())
            if p.is_dir() and ((p / "train").is_dir() or (p / "val").is_dir() or (p / "validation").is_dir())
        ]

    if generator_dirs:
        logger.info(
            "Discovered %d generator directory(ies): %s",
            len(generator_dirs),
            [g.name for g in generator_dirs],
        )
        has_official_val = False

        for gen_dir in generator_dirs:
            t_dir = gen_dir / "train"
            v_dir = gen_dir / "val" if (gen_dir / "val").is_dir() else (gen_dir / "validation")
            tst_dir = gen_dir / "test"

            if tst_dir.is_dir():
                test_paths.append(tst_dir)

            if t_dir.is_dir():
                t_dataset = ImageFolderAuthenticityDataset.from_directory(t_dir)
                train_samples.extend(t_dataset.samples)

            if v_dir.is_dir():
                v_dataset = ImageFolderAuthenticityDataset.from_directory(v_dir)
                val_samples.extend(v_dataset.samples)
                has_official_val = True

        if (data_dir / "test").is_dir():
            test_paths.append(data_dir / "test")

        if not has_official_val:
            if len(train_samples) < 4:
                raise ValueError(
                    f"Insufficient training samples found across generators: {len(train_samples)}"
                )
            rng = random.Random(seed)
            shuffled = list(train_samples)
            rng.shuffle(shuffled)
            val_count = max(1, int(len(shuffled) * val_split))
            if val_count >= len(shuffled):
                raise ValueError("Validation split leaves no training images.")
            train_samples = shuffled[val_count:]
            val_samples = shuffled[:val_count]
        else:
            logger.info(
                "Using official validation splits across generators without mixing (%d train, %d val).",
                len(train_samples),
                len(val_samples),
            )

    elif has_direct_splits:
        t_dir = data_dir / "train"
        v_dir = data_dir / "val" if (data_dir / "val").is_dir() else (data_dir / "validation")
        tst_dir = data_dir / "test"

        if tst_dir.is_dir():
            test_paths.append(tst_dir)

        if v_dir.is_dir():
            if t_dir.is_dir():
                train_samples.extend(ImageFolderAuthenticityDataset.from_directory(t_dir).samples)
            val_samples.extend(ImageFolderAuthenticityDataset.from_directory(v_dir).samples)
            logger.info(
                "Using official validation split from %s without mixing (%d train, %d val).",
                v_dir,
                len(train_samples),
                len(val_samples),
            )
        elif t_dir.is_dir():
            dataset = ImageFolderAuthenticityDataset.from_directory(t_dir)
            if len(dataset) < 4:
                raise ValueError(
                    f"Training directory must contain at least 4 images (found {len(dataset)})"
                )
            rng = random.Random(seed)
            shuffled = list(dataset.samples)
            rng.shuffle(shuffled)
            val_count = max(1, int(len(shuffled) * val_split))
            if val_count >= len(shuffled):
                raise ValueError("Validation split leaves no training images.")
            train_samples = shuffled[val_count:]
            val_samples = shuffled[:val_count]

    else:
        dataset = ImageFolderAuthenticityDataset.from_directory(data_dir)
        if len(dataset) < 4:
            raise ValueError(f"Dataset must contain at least 4 images (found {len(dataset)})")
        rng = random.Random(seed)
        shuffled = list(dataset.samples)
        rng.shuffle(shuffled)
        val_count = max(1, int(len(shuffled) * val_split))
        if val_count >= len(shuffled):
            raise ValueError("Validation split leaves no training images.")
        train_samples = shuffled[val_count:]
        val_samples = shuffled[:val_count]

    return train_samples, val_samples, test_paths


def limit_samples_by_class(
    samples: List[Tuple[Path, float]],
    max_samples: Optional[int] = None,
    seed: int = 42,
) -> List[Tuple[Path, float]]:
    """
    Subsample a list of (image_path, label) tuples up to max_samples while preserving
    class balance as closely as possible.

    Args:
        samples: List of (Path, float) tuples.
        max_samples: Maximum number of samples to retain. If None or >= len(samples),
                     the original list is returned unchanged.
        seed: Random seed for deterministic shuffling within each class.

    Returns:
        Subsampled list of (Path, float) tuples.
    """
    if max_samples is None or max_samples >= len(samples):
        return samples
    if max_samples <= 0:
        return []

    by_class: Dict[float, List[Tuple[Path, float]]] = {}
    for item in samples:
        by_class.setdefault(item[1], []).append(item)

    rng = random.Random(seed)
    shuffled_by_class: Dict[float, List[Tuple[Path, float]]] = {}
    for label in sorted(by_class.keys()):
        cls_list = list(by_class[label])
        cls_list.sort(key=lambda x: str(x[0]))
        rng.shuffle(cls_list)
        shuffled_by_class[label] = cls_list

    allocated: Dict[float, List[Tuple[Path, float]]] = {label: [] for label in shuffled_by_class}
    classes = sorted(shuffled_by_class.keys())

    total_allocated = 0
    while total_allocated < max_samples:
        allocated_in_round = 0
        for label in classes:
            if total_allocated >= max_samples:
                break
            if len(allocated[label]) < len(shuffled_by_class[label]):
                allocated[label].append(shuffled_by_class[label][len(allocated[label])])
                total_allocated += 1
                allocated_in_round += 1
        if allocated_in_round == 0:
            break

    result: List[Tuple[Path, float]] = []
    for label in classes:
        result.extend(allocated[label])

    rng.shuffle(result)
    return result


def get_transforms(input_size: int = 224) -> Tuple[Callable, Callable]:
    """Return (train_transform, val_transform) matching inference pipeline."""
    oversize = int(input_size * 1.143)

    train_transform = T.Compose([
        T.Resize((oversize, oversize)),
        T.RandomCrop((input_size, input_size)),
        T.RandomHorizontalFlip(p=0.5),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])

    val_transform = T.Compose([
        T.Resize(oversize),
        T.CenterCrop(input_size),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])

    return train_transform, val_transform


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, float]:
    """
    Compute binary classification metrics without external dependencies.
    Computes Loss, Accuracy, Precision, Recall, F1, and ROC-AUC.
    """
    y_pred = (y_prob >= threshold).astype(np.float32)

    tp = float(np.sum((y_true == 1.0) & (y_pred == 1.0)))
    tn = float(np.sum((y_true == 0.0) & (y_pred == 0.0)))
    fp = float(np.sum((y_true == 0.0) & (y_pred == 1.0)))
    fn = float(np.sum((y_true == 1.0) & (y_pred == 0.0)))

    total = len(y_true)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # Mann-Whitney U for ROC-AUC
        # Mann-Whitney U for ROC-AUC, using average ranks for ties.
    n_pos = int(np.sum(y_true == 1.0))
    n_neg = int(np.sum(y_true == 0.0))

    if n_pos > 0 and n_neg > 0:
        order = np.argsort(y_prob, kind="mergesort")
        sorted_probs = y_prob[order]

        ranks = np.empty(len(y_prob), dtype=np.float64)

        start = 0
        while start < len(sorted_probs):
            end = start + 1

            while (
                end < len(sorted_probs)
                and sorted_probs[end] == sorted_probs[start]
            ):
                end += 1

            # Ranks are 1-based; tied values receive their average rank.
            average_rank = ((start + 1) + end) / 2.0
            ranks[order[start:end]] = average_rank
            start = end

        rank_sum_pos = np.sum(ranks[y_true == 1.0])
        u_stat = rank_sum_pos - (n_pos * (n_pos + 1)) / 2.0
        roc_auc = float(u_stat / (n_pos * n_neg))
    else:
        roc_auc = 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
    }


def set_model_train_mode(model: nn.Module, unfreeze_backbone: bool) -> None:
    """
    Set model to training mode while ensuring frozen BatchNorm layers
    remain in evaluation mode when unfreeze_backbone is False.
    """
    model.train()
    if not unfreeze_backbone:
        for module in model.modules():
            if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
                module.eval()


def train_classifier(
    train_samples: List[Tuple[Path, float]],
    val_samples: List[Tuple[Path, float]],
    output_checkpoint_path: Path,
    backbone_name: str = "efficientnet_b0",
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 1e-4,
    unfreeze_backbone: bool = False,
    device: Optional[torch.device] = None,
    model_version: str = "1.0.0",
    max_train_samples: Optional[int] = None,
    max_val_samples: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fine-tune the binary classification model and save checkpoint.

    Args:
        train_samples: List of (image_path, label) for training.
        val_samples: List of (image_path, label) for validation.
        output_checkpoint_path: Destination path for .pt file.
        backbone_name: timm model architecture.
        epochs: Number of training epochs.
        batch_size: DataLoader batch size.
        lr: AdamW learning rate.
        unfreeze_backbone: If False, only the binary classification head is trained.
        device: Device override (defaults to cuda if available, else cpu).
        model_version: Semantic version string for metadata.
        max_train_samples: Optional upper bound on training samples (preserving class balance).
        max_val_samples: Optional upper bound on validation samples (preserving class balance).

    Returns:
        Dictionary of training and final validation metrics.
    """
    if max_train_samples is not None:
        train_samples = limit_samples_by_class(train_samples, max_samples=max_train_samples)
    if max_val_samples is not None:
        val_samples = limit_samples_by_class(val_samples, max_samples=max_val_samples)
    if device is not None:
        dev = device
    elif torch.cuda.is_available():
        dev = torch.device("cuda")
    elif (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        dev = torch.device("mps")
    else:
        dev = torch.device("cpu")
    logger.info("Initializing training on %s (unfreeze_backbone=%s)", dev, unfreeze_backbone)

    train_tf, val_tf = get_transforms(input_size=224)
    train_dataset = ImageFolderAuthenticityDataset(train_samples, transform=train_tf)
    val_dataset = ImageFolderAuthenticityDataset(val_samples, transform=val_tf)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    model = _build_model(backbone_name)

    if not unfreeze_backbone:
        # Freeze all backbone layers except the custom binary head
        for param in model.parameters():
            param.requires_grad = False
        for param in model.head.parameters():
            param.requires_grad = True
        # Ensure all frozen BatchNorm layers are set to eval mode
        for module in model.modules():
            if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
                module.eval()

    model.to(dev)

    criterion = nn.BCELoss()
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=1e-4,
    )

    best_val_f1 = -1.0
    history: List[Dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        set_model_train_mode(model, unfreeze_backbone)
        running_loss = 0.0

        for images, targets in train_loader:
            images = images.to(dev)
            targets = targets.to(dev)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * len(images)

        epoch_train_loss = running_loss / len(train_dataset) if len(train_dataset) > 0 else 0.0

        # Validation phase
        model.eval()
        val_loss = 0.0
        all_targets: List[float] = []
        all_probs: List[float] = []

        with torch.no_grad():
            for images, targets in val_loader:
                images = images.to(dev)
                targets = targets.to(dev)
                outputs = model(images)
                loss = criterion(outputs, targets)
                val_loss += loss.item() * len(images)

                all_targets.extend(targets.squeeze(-1).cpu().numpy().tolist())
                all_probs.extend(outputs.squeeze(-1).cpu().numpy().tolist())

        epoch_val_loss = val_loss / len(val_dataset) if len(val_dataset) > 0 else 0.0
        val_metrics = compute_metrics(np.array(all_targets), np.array(all_probs))
        val_metrics["val_loss"] = round(epoch_val_loss, 4)
        val_metrics["train_loss"] = round(epoch_train_loss, 4)
        val_metrics["epoch"] = epoch

        history.append(val_metrics)
        logger.info(
            "Epoch %d/%d — Train Loss: %.4f | Val Loss: %.4f | Acc: %.4f | F1: %.4f",
            epoch, epochs, epoch_train_loss, epoch_val_loss, val_metrics["accuracy"], val_metrics["f1"],
        )

        if val_metrics["f1"] >= best_val_f1:
            best_val_f1 = val_metrics["f1"]
            output_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_payload = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "backbone": backbone_name,
                "model_name": f"TruthLens-{backbone_name}",
                "model_version": model_version,
                "metrics": val_metrics,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            torch.save(checkpoint_payload, str(output_checkpoint_path))
            logger.info("Saved best checkpoint to %s", output_checkpoint_path)

    return {
        "best_val_f1": best_val_f1,
        "checkpoint_path": str(output_checkpoint_path),
        "history": history,
    }
