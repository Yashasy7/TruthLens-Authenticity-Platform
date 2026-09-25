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

    AUTHENTIC_NAMES = {"authentic", "real", "0", "pristine"}
    SYNTHETIC_NAMES = {"synthetic", "fake", "1", "ai_generated", "diffusion"}

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
                if file_path.suffix.lower() in valid_exts:
                    samples.append((file_path, label))

        logger.info("Discovered %d samples in %s", len(samples), data_dir)
        return cls(samples=samples, transform=transform)


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
    n_pos = np.sum(y_true == 1.0)
    n_neg = np.sum(y_true == 0.0)
    if n_pos > 0 and n_neg > 0:
        # Rank scores
        ranks = np.argsort(np.argsort(y_prob)) + 1
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

    Returns:
        Dictionary of training and final validation metrics.
    """
    dev = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
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
        model.train()
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
