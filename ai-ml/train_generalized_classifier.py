"""
TruthLens AI/ML — Fine-Tune EfficientNet-B0 for General Media Authenticity
Blueprint Module 05: PyTorch vision model inference & training wrapper
Fine-tunes the baseline model on a combined 7,112-image balanced multi-domain dataset:
- 3,556 general photographic images (ImageNet real, ADM, BigGAN, GLIDE, VQDM, SD15)
- 3,556 human portrait images (FFHQ real, StyleGAN2 fake)
Total: 7,112 training images (3,556 authentic / 3,556 synthetic).

Validation set:
- 800 general photographic images (400 real / 400 fake)
- 800 human portrait images (400 real / 400 fake)
Total: 1,600 validation images.

Fine-tuning protocol:
- Initialized from existing checkpoint: ai-ml/models/deepfake_detection_efficientnet_b0.pt
- Unfreezes later backbone stages (blocks[5], blocks[6], conv_head, bn2) and head
- Keeps earlier backbone stages frozen
- Discriminative learning rates: 1e-5 for backbone, 1e-4 for head
- Frozen BatchNorm layers kept in eval mode
- Saves best checkpoint to ai-ml/models/deepfake_detection_efficientnet_b0_generalized.pt
- Evaluates on unseen-generator general scene test set and untouched portrait test set.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.train_generalized")

# Ensure ai-ml is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_ML_DIR = PROJECT_ROOT / "ai-ml"
if str(AI_ML_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ML_DIR))

from services.image_analysis.classifier import _build_model
from services.image_analysis.trainer import (
    ImageFolderAuthenticityDataset,
    get_transforms,
    compute_metrics,
)
from utils.image_utils import _IMAGENET_MEAN, _IMAGENET_STD

ORIGINAL_CHECKPOINT = AI_ML_DIR / "models" / "deepfake_detection_efficientnet_b0.pt"
NEW_CHECKPOINT = AI_ML_DIR / "models" / "deepfake_detection_efficientnet_b0_generalized.pt"
EVAL_OUTPUT_JSON = AI_ML_DIR / "models" / "generalized_evaluation_report.json"

GEN_SCENES_DIR = AI_ML_DIR / "data" / "expanded_image_detection" / "general_scenes_v2"
PORTRAITS_DIR = AI_ML_DIR / "data" / "deepfake_detection"


def assemble_balanced_datasets() -> Tuple[List[Tuple[Path, float]], List[Tuple[Path, float]]]:
    """
    Assemble training (7,112 images) and validation (1,600 images) datasets
    balanced equally between real/fake and general photography / portraits.
    """
    logger.info("Assembling balanced multi-domain datasets...")

    # 1. General scenes train
    gen_train_real = sorted((GEN_SCENES_DIR / "train" / "real").glob("*.*"))
    gen_train_fake = sorted((GEN_SCENES_DIR / "train" / "fake").glob("*.*"))
    logger.info("General scenes train found: %d real, %d fake", len(gen_train_real), len(gen_train_fake))

    # 2. Portrait train (deterministic sample of 1,778 each)
    p_train_real_all = sorted((PORTRAITS_DIR / "train" / "real").glob("*.*"))
    p_train_fake_all = sorted((PORTRAITS_DIR / "train" / "fake").glob("*.*"))
    p_train_real = p_train_real_all[:len(gen_train_real)]
    p_train_fake = p_train_fake_all[:len(gen_train_fake)]
    logger.info("Portrait train selected: %d real, %d fake", len(p_train_real), len(p_train_fake))

    # Build train samples: (Path, float)
    train_samples: List[Tuple[Path, float]] = []
    for p in gen_train_real:
        train_samples.append((p, 0.0))
    for p in p_train_real:
        train_samples.append((p, 0.0))
    for p in gen_train_fake:
        train_samples.append((p, 1.0))
    for p in p_train_fake:
        train_samples.append((p, 1.0))

    rng = random.Random(42)
    rng.shuffle(train_samples)
    logger.info("Total combined training samples: %d (Real: %d, Fake: %d)",
                len(train_samples),
                sum(1 for _, l in train_samples if l == 0.0),
                sum(1 for _, l in train_samples if l == 1.0))

    # 3. General scenes val (400 real, 400 fake)
    gen_val_real = sorted((GEN_SCENES_DIR / "val" / "real").glob("*.*"))
    gen_val_fake = sorted((GEN_SCENES_DIR / "val" / "fake").glob("*.*"))
    logger.info("General scenes val found: %d real, %d fake", len(gen_val_real), len(gen_val_fake))

    # 4. Portrait val (deterministic sample of 400 each)
    p_val_real_all = sorted((PORTRAITS_DIR / "val" / "real").glob("*.*"))
    p_val_fake_all = sorted((PORTRAITS_DIR / "val" / "fake").glob("*.*"))
    p_val_real = p_val_real_all[:len(gen_val_real)]
    p_val_fake = p_val_fake_all[:len(gen_val_fake)]
    logger.info("Portrait val selected: %d real, %d fake", len(p_val_real), len(p_val_fake))

    val_samples: List[Tuple[Path, float]] = []
    for p in gen_val_real:
        val_samples.append((p, 0.0))
    for p in p_val_real:
        val_samples.append((p, 0.0))
    for p in gen_val_fake:
        val_samples.append((p, 1.0))
    for p in p_val_fake:
        val_samples.append((p, 1.0))

    rng.shuffle(val_samples)
    logger.info("Total combined validation samples: %d (Real: %d, Fake: %d)",
                len(val_samples),
                sum(1 for _, l in val_samples if l == 0.0),
                sum(1 for _, l in val_samples if l == 1.0))

    return train_samples, val_samples


def get_fine_tuning_transforms(input_size: int = 224) -> Tuple[Callable, Callable]:
    """Data augmentation suitable for fine-tuning without distorting forensic artifacts."""
    train_transform = T.Compose([
        T.Resize((256, 256)),
        T.RandomCrop((input_size, input_size)),
        T.RandomHorizontalFlip(p=0.5),
        T.ColorJitter(brightness=0.08, contrast=0.08),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])

    val_transform = T.Compose([
        T.Resize((256, 256)),
        T.CenterCrop((input_size, input_size)),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])

    return train_transform, val_transform


def prepare_model_for_fine_tuning(
    checkpoint_path: Path,
    device: torch.device,
) -> Tuple[nn.Module, torch.optim.Optimizer]:
    """
    Build EfficientNet-B0, load original checkpoint, unfreeze later stages and classifier,
    and create optimizer with discriminative learning rates.
    """
    logger.info("Building model architecture and loading weights from %s...", checkpoint_path)
    model = _build_model("efficientnet_b0")

    ckpt = torch.load(str(checkpoint_path), map_location=device)
    state = ckpt.get("model_state_dict", ckpt)
    model.load_state_dict(state, strict=True)
    logger.info("Checkpoint state_dict loaded successfully.")

    # Parameter partitioning:
    # Later backbone stages: blocks[5], blocks[6], conv_head, bn2
    # Classifier head: head
    # Earlier backbone: conv_stem, bn1, blocks[0..4] (frozen)
    backbone_trainable = []
    head_trainable = []
    frozen_count = 0

    for name, param in model.named_parameters():
        if any(k in name for k in ["blocks.5.", "blocks.6.", "conv_head.", "bn2."]):
            param.requires_grad = True
            backbone_trainable.append(param)
        elif "head." in name:
            param.requires_grad = True
            head_trainable.append(param)
        else:
            param.requires_grad = False
            frozen_count += param.numel()

    backbone_numel = sum(p.numel() for p in backbone_trainable)
    head_numel = sum(p.numel() for p in head_trainable)
    total_numel = backbone_numel + head_numel + frozen_count

    logger.info("Parameter breakdown:")
    logger.info("  Frozen earlier backbone: %d parameters (%.1f%%)", frozen_count, frozen_count / total_numel * 100)
    logger.info("  Trainable later backbone: %d parameters (%.1f%%) [lr=1e-5]", backbone_numel, backbone_numel / total_numel * 100)
    logger.info("  Trainable classifier head: %d parameters (%.1f%%) [lr=1e-4]", head_numel, head_numel / total_numel * 100)

    model.to(device)

    # Optimizer with discriminative learning rates
    optimizer = torch.optim.AdamW([
        {"params": backbone_trainable, "lr": 1e-5, "weight_decay": 1e-4},
        {"params": head_trainable, "lr": 1e-4, "weight_decay": 1e-4},
    ])

    return model, optimizer


def set_fine_tuning_train_mode(model: nn.Module) -> None:
    """Set model to training mode while ensuring frozen BatchNorm layers stay in eval mode."""
    model.train()
    for module in model.modules():
        if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
            # If all parameters in this batchnorm layer are frozen, force eval mode
            if all(not p.requires_grad for p in module.parameters()):
                module.eval()


def evaluate_dataset(
    model: nn.Module,
    samples: List[Tuple[Path, float]],
    device: torch.device,
    batch_size: int = 64,
    transform: Optional[Callable] = None,
) -> Tuple[Dict[str, Any], np.ndarray, np.ndarray]:
    """Run full evaluation on a sample list returning metrics and predictions."""
    model.eval()
    if transform is None:
        _, transform = get_fine_tuning_transforms(224)

    dataset = ImageFolderAuthenticityDataset(samples, transform=transform)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    all_targets: List[float] = []
    all_probs: List[float] = []

    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device)
            outputs = model(images)
            all_targets.extend(targets.squeeze(-1).cpu().numpy().tolist())
            all_probs.extend(outputs.squeeze(-1).cpu().numpy().tolist())

    y_true = np.array(all_targets, dtype=np.float32)
    y_prob = np.array(all_probs, dtype=np.float32)

    metrics = compute_metrics(y_true, y_prob, threshold=0.5)

    # Add confusion matrix details
    y_pred = (y_prob >= 0.5).astype(np.float32)
    tp = int(np.sum((y_true == 1.0) & (y_pred == 1.0)))
    tn = int(np.sum((y_true == 0.0) & (y_pred == 0.0)))
    fp = int(np.sum((y_true == 0.0) & (y_pred == 1.0)))
    fn = int(np.sum((y_true == 1.0) & (y_pred == 0.0)))

    metrics["confusion_matrix"] = {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "matrix": [[tn, fp], [fn, tp]],
        "labels": ["Authentic (0)", "Synthetic (1)"],
    }
    metrics["total_samples"] = len(y_true)
    metrics["support_real"] = int(np.sum(y_true == 0.0))
    metrics["support_fake"] = int(np.sum(y_true == 1.0))

    return metrics, y_true, y_prob


def run_training():
    start_total_time = time.perf_counter()
    logger.info("=" * 70)
    logger.info("TRUTHLENS EFFICIENTNET-B0 GENERALIZED FINE-TUNING")
    logger.info("=" * 70)

    # Configure execution resources
    torch.set_num_threads(8)
    device = torch.device("cpu")
    logger.info("Using device: %s (torch threads=%d)", device, torch.get_num_threads())

    # 1. Prepare datasets
    train_samples, val_samples = assemble_balanced_datasets()

    train_tf, val_tf = get_fine_tuning_transforms(224)
    train_dataset = ImageFolderAuthenticityDataset(train_samples, transform=train_tf)
    val_dataset = ImageFolderAuthenticityDataset(val_samples, transform=val_tf)

    batch_size = 64
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # 2. Build model and optimizer
    model, optimizer = prepare_model_for_fine_tuning(ORIGINAL_CHECKPOINT, device)

    # Learning rate scheduler
    epochs = 5
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    criterion = nn.BCELoss()

    # Initial pre-fine-tuning validation baseline
    logger.info("Evaluating validation baseline before fine-tuning...")
    val_base_metrics, _, _ = evaluate_dataset(model, val_samples, device, batch_size=64, transform=val_tf)
    logger.info(
        "Initial Pre-Training Val — Acc: %.4f | F1: %.4f | ROC-AUC: %.4f | (Real Acc: %.1f%%, Fake Acc: %.1f%%)",
        val_base_metrics["accuracy"], val_base_metrics["f1"], val_base_metrics["roc_auc"],
        val_base_metrics["confusion_matrix"]["tn"] / val_base_metrics["support_real"] * 100,
        val_base_metrics["confusion_matrix"]["tp"] / val_base_metrics["support_fake"] * 100,
    )

    best_val_f1 = -1.0
    best_epoch = 0
    history = []

    # 3. Training Loop
    for epoch in range(1, epochs + 1):
        epoch_start = time.perf_counter()
        set_fine_tuning_train_mode(model)
        running_loss = 0.0
        batch_idx = 0

        for images, targets in train_loader:
            images = images.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * len(images)
            batch_idx += 1

            if batch_idx % 25 == 0 or batch_idx == len(train_loader):
                logger.info(
                    "Epoch %d/%d [Batch %d/%d] — Current Loss: %.4f",
                    epoch, epochs, batch_idx, len(train_loader), loss.item()
                )

        scheduler.step()
        train_loss = running_loss / len(train_dataset)

        # Validation phase
        val_metrics, _, _ = evaluate_dataset(model, val_samples, device, batch_size=64, transform=val_tf)
        val_metrics["train_loss"] = round(train_loss, 4)
        val_metrics["epoch"] = epoch
        val_metrics["epoch_duration_s"] = round(time.perf_counter() - epoch_start, 2)
        history.append(val_metrics)

        logger.info(
            "=== Epoch %d/%d Finished in %.1fs — Train Loss: %.4f | Val Acc: %.4f | Val F1: %.4f | ROC-AUC: %.4f ===",
            epoch, epochs, val_metrics["epoch_duration_s"], train_loss, val_metrics["accuracy"], val_metrics["f1"], val_metrics["roc_auc"]
        )

        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            best_epoch = epoch
            NEW_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_payload = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "backbone": "efficientnet_b0",
                "model_name": "TruthLens-efficientnet_b0-generalized",
                "model_version": "2.0.0",
                "metrics": val_metrics,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            torch.save(checkpoint_payload, str(NEW_CHECKPOINT))
            logger.info(">>> New best checkpoint saved to %s (Val F1: %.4f) <<<", NEW_CHECKPOINT, best_val_f1)

    training_duration = time.perf_counter() - start_total_time
    logger.info("Training completed in %.2f minutes. Best epoch: %d with Val F1: %.4f", training_duration / 60, best_epoch, best_val_f1)

    # 4. Final Evaluation of BOTH models on Test Sets
    logger.info("=" * 70)
    logger.info("FINAL EVALUATION ON INDEPENDENT TEST SETS")
    logger.info("=" * 70)

    # Prepare Test Set A (General Scenes test)
    gen_test_real = sorted((GEN_SCENES_DIR / "test" / "real").glob("*.*"))
    gen_test_fake_all = sorted((GEN_SCENES_DIR / "test" / "fake").glob("*.*"))
    gen_test_samples = [(p, 0.0) for p in gen_test_real] + [(p, 1.0) for p in gen_test_fake_all]

    # Specific generator subgroups for Midjourney and Wukong
    mj_samples = [(p, 1.0) for p in gen_test_fake_all if "midjourney" in p.name.lower()]
    wukong_samples = [(p, 1.0) for p in gen_test_fake_all if "wukong" in p.name.lower()]

    logger.info("Test Set A (General Scenes): %d total (%d Real, %d Fake [%d Midjourney, %d Wukong])",
                len(gen_test_samples), len(gen_test_real), len(gen_test_fake_all), len(mj_samples), len(wukong_samples))

    # Prepare Test Set B (Original untouched portrait test set)
    portrait_test_real = sorted((PORTRAITS_DIR / "test" / "real").glob("*.*"))
    portrait_test_fake = sorted((PORTRAITS_DIR / "test" / "fake").glob("*.*"))
    portrait_test_samples = [(p, 0.0) for p in portrait_test_real] + [(p, 1.0) for p in portrait_test_fake]
    logger.info("Test Set B (Portraits): %d total (%d Real, %d Fake)",
                len(portrait_test_samples), len(portrait_test_real), len(portrait_test_fake))

    # Load previous baseline model
    prev_model = _build_model("efficientnet_b0")
    prev_ckpt = torch.load(str(ORIGINAL_CHECKPOINT), map_location=device)
    prev_model.load_state_dict(prev_ckpt.get("model_state_dict", prev_ckpt), strict=True)
    prev_model.eval()

    # Load newly fine-tuned model
    new_model = _build_model("efficientnet_b0")
    new_ckpt = torch.load(str(NEW_CHECKPOINT), map_location=device)
    new_model.load_state_dict(new_ckpt.get("model_state_dict", new_ckpt), strict=True)
    new_model.eval()

    # Evaluate both on Test Set A (General Scenes)
    logger.info("Evaluating baseline model on Test Set A (General Scenes)...")
    prev_gen_metrics, _, prev_gen_probs = evaluate_dataset(prev_model, gen_test_samples, device, batch_size=64)

    logger.info("Evaluating fine-tuned generalized model on Test Set A (General Scenes)...")
    new_gen_metrics, _, new_gen_probs = evaluate_dataset(new_model, gen_test_samples, device, batch_size=64)

    # Evaluate generator breakdowns for Midjourney and Wukong
    logger.info("Evaluating generator breakdowns on Test Set A...")
    prev_mj_metrics, _, _ = evaluate_dataset(prev_model, mj_samples, device, batch_size=64)
    new_mj_metrics, _, _ = evaluate_dataset(new_model, mj_samples, device, batch_size=64)

    prev_wk_metrics, _, _ = evaluate_dataset(prev_model, wukong_samples, device, batch_size=64)
    new_wk_metrics, _, _ = evaluate_dataset(new_model, wukong_samples, device, batch_size=64)

    # Evaluate both on Test Set B (Portraits)
    logger.info("Evaluating baseline model on Test Set B (Portraits)...")
    prev_port_metrics, _, _ = evaluate_dataset(prev_model, portrait_test_samples, device, batch_size=64)

    logger.info("Evaluating fine-tuned generalized model on Test Set B (Portraits)...")
    new_port_metrics, _, _ = evaluate_dataset(new_model, portrait_test_samples, device, batch_size=64)

    # Assemble comprehensive report
    report = {
        "evaluation_title": "TruthLens EfficientNet-B0 Generalized Fine-Tuning Evaluation",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "training_configuration": {
            "initial_checkpoint": str(ORIGINAL_CHECKPOINT),
            "output_checkpoint": str(NEW_CHECKPOINT),
            "backbone": "efficientnet_b0",
            "epochs": epochs,
            "best_epoch": best_epoch,
            "batch_size": batch_size,
            "learning_rates": {"backbone": 1e-5, "classifier_head": 1e-4},
            "training_samples": len(train_samples),
            "validation_samples": len(val_samples),
            "duration_seconds": round(training_duration, 2),
            "duration_minutes": round(training_duration / 60, 2),
            "history": history,
        },
        "test_results": {
            "general_scenes_unseen_test": {
                "dataset_path": str(GEN_SCENES_DIR / "test"),
                "total_samples": len(gen_test_samples),
                "baseline_model": prev_gen_metrics,
                "generalized_model": new_gen_metrics,
                "generator_breakdown": {
                    "midjourney_unseen": {
                        "samples": len(mj_samples),
                        "baseline_detection_rate": round(prev_mj_metrics["confusion_matrix"]["tp"] / len(mj_samples), 4),
                        "generalized_detection_rate": round(new_mj_metrics["confusion_matrix"]["tp"] / len(mj_samples), 4),
                    },
                    "wukong_unseen": {
                        "samples": len(wukong_samples),
                        "baseline_detection_rate": round(prev_wk_metrics["confusion_matrix"]["tp"] / len(wukong_samples), 4),
                        "generalized_detection_rate": round(new_wk_metrics["confusion_matrix"]["tp"] / len(wukong_samples), 4),
                    },
                },
            },
            "portrait_test": {
                "dataset_path": str(PORTRAITS_DIR / "test"),
                "total_samples": len(portrait_test_samples),
                "baseline_model": prev_port_metrics,
                "generalized_model": new_port_metrics,
            },
        },
    }

    with open(EVAL_OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Saved evaluation report to %s", EVAL_OUTPUT_JSON)

    # Print Executive Summary Table
    print("\n" + "=" * 80)
    print("TRUTHLENS EFFICIENTNET-B0 EVALUATION COMPARISON SUMMARY")
    print("=" * 80)
    print(f"{'Metric':<25} | {'Test A (General Scenes)':<25} | {'Test B (Portraits)':<25}")
    print(f"{'':<25} | {'Baseline -> Generalized':<25} | {'Baseline -> Generalized':<25}")
    print("-" * 80)
    print(f"{'Accuracy':<25} | {prev_gen_metrics['accuracy']:.4f} -> {new_gen_metrics['accuracy']:.4f}       | {prev_port_metrics['accuracy']:.4f} -> {new_port_metrics['accuracy']:.4f}")
    print(f"{'Precision':<25} | {prev_gen_metrics['precision']:.4f} -> {new_gen_metrics['precision']:.4f}       | {prev_port_metrics['precision']:.4f} -> {new_port_metrics['precision']:.4f}")
    print(f"{'Recall':<25} | {prev_gen_metrics['recall']:.4f} -> {new_gen_metrics['recall']:.4f}       | {prev_port_metrics['recall']:.4f} -> {new_port_metrics['recall']:.4f}")
    print(f"{'F1-Score':<25} | {prev_gen_metrics['f1']:.4f} -> {new_gen_metrics['f1']:.4f}       | {prev_port_metrics['f1']:.4f} -> {new_port_metrics['f1']:.4f}")
    print(f"{'ROC-AUC':<25} | {prev_gen_metrics['roc_auc']:.4f} -> {new_gen_metrics['roc_auc']:.4f}       | {prev_port_metrics['roc_auc']:.4f} -> {new_port_metrics['roc_auc']:.4f}")
    print("-" * 80)
    print("UNSEEN GENERATOR DETECTION RATE (Test A):")
    print(f"  Midjourney Detection: {prev_mj_metrics['confusion_matrix']['tp']}/{len(mj_samples)} ({prev_mj_metrics['confusion_matrix']['tp']/len(mj_samples)*100:.1f}%) -> {new_mj_metrics['confusion_matrix']['tp']}/{len(mj_samples)} ({new_mj_metrics['confusion_matrix']['tp']/len(mj_samples)*100:.1f}%)")
    print(f"  Wukong Detection:     {prev_wk_metrics['confusion_matrix']['tp']}/{len(wukong_samples)} ({prev_wk_metrics['confusion_matrix']['tp']/len(wukong_samples)*100:.1f}%) -> {new_wk_metrics['confusion_matrix']['tp']}/{len(wukong_samples)} ({new_wk_metrics['confusion_matrix']['tp']/len(wukong_samples)*100:.1f}%)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_training()
