"""
TruthLens AI/ML — Standalone Image Model Evaluation Framework

Evaluates trained binary image authenticity classifiers (Authentic = 0, AI-Generated = 1)
against an independent test dataset without retraining, data leakage, or synthetic score fabrication.

Features:
  - Reuses production preprocessing, architecture (EfficientNet-B0), and checkpoint validation.
  - Calculates Accuracy, Binary Precision/Recall/F1, Macro F1, and continuous-score ROC-AUC.
  - Computes per-class metrics (Precision, Recall, F1, Support) for Class 0 (Real) and Class 1 (Synthetic).
  - Handles single-class or imbalanced datasets safely without crashing.
  - Exports a machine-readable JSON evaluation report.
  - Renders a standalone confusion matrix visualization PNG (zero extra dependencies).
  - Outputs an executive ASCII evaluation summary to the console.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageDraw
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T

from config.settings import settings
from services.image_analysis.classifier import _build_model
from services.image_analysis.trainer import (
    ImageFolderAuthenticityDataset,
    get_transforms,
)
from utils.image_utils import _IMAGENET_MEAN, _IMAGENET_STD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.eval")


def load_evaluation_model(
    checkpoint_path: Path | str,
    backbone_name: str = "efficientnet_b0",
    device: Optional[torch.device] = None,
) -> Tuple[nn.Module, Dict[str, Any]]:
    """
    Load a trained image classifier checkpoint using the exact production architecture and strict validation.

    Args:
        checkpoint_path: Path to the .pt checkpoint file.
        backbone_name: timm backbone architecture (default: efficientnet_b0).
        device: Target execution device (CPU or CUDA).

    Returns:
        Tuple of (model in eval mode, checkpoint metadata dictionary).
    """
    ckpt_path = Path(checkpoint_path)
    if not ckpt_path.is_file():
        raise FileNotFoundError(f"Checkpoint file not found: {ckpt_path.resolve()}")

    target_device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Initializing backbone '%s' for evaluation on %s", backbone_name, target_device)

    model = _build_model(backbone_name)

    loaded = torch.load(str(ckpt_path), map_location=target_device)
    metadata: Dict[str, Any] = {
        "checkpoint_path": str(ckpt_path.resolve()),
        "backbone": backbone_name,
        "model_name": f"TruthLens-{backbone_name}",
        "model_version": "unknown",
        "epoch": None,
        "metrics": {},
    }

    if isinstance(loaded, dict):
        if "backbone" in loaded and loaded["backbone"] != backbone_name:
            raise RuntimeError(
                f"Backbone mismatch: checkpoint was trained for '{loaded['backbone']}', "
                f"but evaluation requested '{backbone_name}'."
            )
        state_dict = loaded.get("model_state_dict", loaded)
        metadata["model_version"] = str(loaded.get("model_version", "1.0.0"))
        metadata["epoch"] = loaded.get("epoch")
        metadata["metrics"] = loaded.get("metrics", {})
        metadata["created_at"] = loaded.get("created_at")
    else:
        state_dict = loaded

    if not isinstance(state_dict, dict):
        raise RuntimeError(f"Invalid checkpoint format in '{ckpt_path}': expected state_dict mapping.")

    if "head.1.weight" not in state_dict or "head.1.bias" not in state_dict:
        raise RuntimeError(
            f"Incompatible checkpoint '{ckpt_path}': missing classification head weights ('head.1.weight', 'head.1.bias')."
        )

    model.load_state_dict(state_dict, strict=True)
    model.to(target_device)
    model.eval()

    logger.info(
        "Successfully loaded checkpoint: %s (version: %s, epoch: %s)",
        ckpt_path.name,
        metadata["model_version"],
        metadata["epoch"],
    )
    return model, metadata


def discover_test_samples(
    test_dir: Path | str,
    generators: Optional[List[str]] = None,
) -> List[Tuple[Path, float]]:
    """
    Discover test image samples and labels from a directory.

    Supports:
      1. Direct class folders: <test_dir>/{real,fake}, {nature,ai}, {authentic,synthetic}
      2. Split-level directory: <test_dir>/test/{real,fake,nature,ai}
      3. Multi-generator root: <test_dir>/<generator>/test/{ai,nature} or <test_dir>/<generator>/{ai,nature}

    Returns:
        List of (image_file_path, binary_label) where 0.0 = Real, 1.0 = AI-Generated.
    """
    base_dir = Path(test_dir).resolve()
    if not base_dir.is_dir():
        raise FileNotFoundError(f"Test dataset directory does not exist: {base_dir}")

    # Case A: test_dir itself has a test/ subfolder
    if (base_dir / "test").is_dir():
        candidate_dir = base_dir / "test"
        direct_dataset = ImageFolderAuthenticityDataset.from_directory(candidate_dir)
        if len(direct_dataset) > 0:
            logger.info("Found test split inside %s (%d samples)", candidate_dir, len(direct_dataset))
            return direct_dataset.samples

    # Case B: test_dir contains class folders directly
    direct_dataset = ImageFolderAuthenticityDataset.from_directory(base_dir)
    if len(direct_dataset) > 0:
        logger.info("Found direct class folders in %s (%d samples)", base_dir, len(direct_dataset))
        return direct_dataset.samples

    # Case C: multi-generator structure (e.g. GenImage test splits)
    subdirs = [p for p in sorted(base_dir.iterdir()) if p.is_dir()]
    if generators:
        clean_gens = [g.strip().lower() for g in generators if g.strip() and g.strip().lower() != "all"]
        if clean_gens:
            subdirs = [p for p in subdirs if p.name.lower() in clean_gens]
            if not subdirs:
                raise FileNotFoundError(f"None of the requested generators {clean_gens} found in {base_dir}")

    samples: List[Tuple[Path, float]] = []
    for gen_dir in subdirs:
        # Check gen_dir/test first
        target_dir = gen_dir / "test" if (gen_dir / "test").is_dir() else gen_dir
        gen_dataset = ImageFolderAuthenticityDataset.from_directory(target_dir)
        samples.extend(gen_dataset.samples)

    if samples:
        logger.info("Discovered %d test samples across %d generator directories", len(samples), len(subdirs))
        return samples

    raise ValueError(f"No valid test image samples found in {base_dir}. Verify folder structure contains real/fake or nature/ai.")


def compute_evaluation_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Calculate comprehensive evaluation metrics.

    Calculates:
      - Overall: Accuracy, Precision, Recall, F1-Score, Macro F1, ROC-AUC.
      - Per-class: Precision, Recall, F1-Score, Support for Class 0 (Real) and Class 1 (Synthetic).
      - Confusion matrix: TP, TN, FP, FN, and 2x2 matrix.

    ROC-AUC is computed using the continuous AI probability scores, not binary predictions.
    Missing classes are handled safely (roc_auc is None).
    """
    y_true = np.asarray(y_true, dtype=np.float32)
    y_prob = np.asarray(y_prob, dtype=np.float64)
    y_pred = (y_prob >= threshold).astype(np.float32)

    total = len(y_true)
    if total == 0:
        raise ValueError("Cannot compute evaluation metrics on 0 samples.")

    # Binary counts (Class 1 = Synthetic, Class 0 = Real)
    tp = float(np.sum((y_true == 1.0) & (y_pred == 1.0)))
    tn = float(np.sum((y_true == 0.0) & (y_pred == 0.0)))
    fp = float(np.sum((y_true == 0.0) & (y_pred == 1.0)))
    fn = float(np.sum((y_true == 1.0) & (y_pred == 0.0)))

    accuracy = (tp + tn) / total if total > 0 else 0.0

    # Class 1 (AI-Generated / Synthetic) metrics
    p_synthetic = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r_synthetic = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_synthetic = 2 * (p_synthetic * r_synthetic) / (p_synthetic + r_synthetic) if (p_synthetic + r_synthetic) > 0 else 0.0
    support_synthetic = int(np.sum(y_true == 1.0))

    # Class 0 (Authentic / Real) metrics
    p_real = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    r_real = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1_real = 2 * (p_real * r_real) / (p_real + r_real) if (p_real + r_real) > 0 else 0.0
    support_real = int(np.sum(y_true == 0.0))

    macro_f1 = (f1_real + f1_synthetic) / 2.0

    # Continuous ROC-AUC calculation via Mann-Whitney U rank statistic
    roc_auc: Optional[float] = None
    if support_synthetic > 0 and support_real > 0:
        order = np.argsort(y_prob, kind="mergesort")
        sorted_probs = y_prob[order]
        ranks = np.empty(len(y_prob), dtype=np.float64)

        start = 0
        while start < len(sorted_probs):
            end = start + 1
            while end < len(sorted_probs) and sorted_probs[end] == sorted_probs[start]:
                end += 1
            average_rank = ((start + 1) + end) / 2.0
            ranks[order[start:end]] = average_rank
            start = end

        rank_sum_pos = np.sum(ranks[y_true == 1.0])
        u_stat = rank_sum_pos - (support_synthetic * (support_synthetic + 1)) / 2.0
        roc_auc = float(u_stat / (support_synthetic * support_real))

    return {
        "threshold": threshold,
        "total_samples": total,
        "accuracy": round(accuracy, 4),
        "precision": round(p_synthetic, 4),
        "recall": round(r_synthetic, 4),
        "f1_score": round(f1_synthetic, 4),
        "macro_f1": round(macro_f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "per_class": {
            "authentic_real_0": {
                "precision": round(p_real, 4),
                "recall": round(r_real, 4),
                "f1_score": round(f1_real, 4),
                "support": support_real,
            },
            "synthetic_ai_1": {
                "precision": round(p_synthetic, 4),
                "recall": round(r_synthetic, 4),
                "f1_score": round(f1_synthetic, 4),
                "support": support_synthetic,
            },
        },
        "confusion_matrix": {
            "tp": int(tp),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "matrix": [
                [int(tn), int(fp)],
                [int(fn), int(tp)],
            ],
            "labels": ["Authentic (0)", "Synthetic (1)"],
        },
    }


def render_confusion_matrix_image(
    metrics_result: Dict[str, Any],
    model_metadata: Dict[str, Any],
    output_image_path: Path | str,
) -> Path:
    """
    Render a confusion matrix visualization image using PIL.
    Outputs a PNG with colored cells, counts, percentages, and performance summary.
    """
    out_path = Path(output_image_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cm = metrics_result["confusion_matrix"]
    tn, fp = cm["matrix"][0]
    fn, tp = cm["matrix"][1]

    width, height = 760, 620
    img = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Colors
    c_header = (15, 23, 42)
    c_subtext = (100, 116, 139)
    c_border = (203, 213, 225)
    c_card_bg = (255, 255, 255)
    c_tn_bg = (220, 252, 231)  # Soft green
    c_tp_bg = (219, 234, 254)  # Soft blue
    c_fp_bg = (254, 226, 226)  # Soft red
    c_fn_bg = (254, 243, 199)  # Soft amber

    # Title & Metadata Header
    draw.text((40, 25), "TruthLens Image Authenticity — Confusion Matrix", fill=c_header)
    meta_str = f"Model: {model_metadata.get('model_name', 'TruthLens')} | Backbone: {model_metadata.get('backbone', 'efficientnet_b0')} | Version: {model_metadata.get('model_version', '1.0.0')}"
    draw.text((40, 50), meta_str, fill=c_subtext)
    draw.line([(40, 75), (width - 40, 75)], fill=c_border, width=1)

    # Grid Dimensions
    grid_left = 220
    grid_top = 130
    cell_w = 230
    cell_h = 150

    # Column Headers (Predicted)
    draw.text((grid_left + 70, grid_top - 35), "PREDICTED REAL (0)", fill=(30, 41, 59))
    draw.text((grid_left + cell_w + 50, grid_top - 35), "PREDICTED SYNTHETIC (1)", fill=(30, 41, 59))

    # Row Headers (Actual)
    draw.text((50, grid_top + 60), "ACTUAL REAL (0)", fill=(30, 41, 59))
    draw.text((50, grid_top + cell_h + 60), "ACTUAL SYNTH (1)", fill=(30, 41, 59))

    total_real = tn + fp
    total_synth = fn + tp
    tn_pct = (tn / total_real * 100) if total_real > 0 else 0.0
    fp_pct = (fp / total_real * 100) if total_real > 0 else 0.0
    fn_pct = (fn / total_synth * 100) if total_synth > 0 else 0.0
    tp_pct = (tp / total_synth * 100) if total_synth > 0 else 0.0

    cells = [
        # (x, y, bg, title, count, pct)
        (grid_left, grid_top, c_tn_bg, "TRUE NEGATIVE (TN)", tn, tn_pct),
        (grid_left + cell_w, grid_top, c_fp_bg, "FALSE POSITIVE (FP)", fp, fp_pct),
        (grid_left, grid_top + cell_h, c_fn_bg, "FALSE NEGATIVE (FN)", fn, fn_pct),
        (grid_left + cell_w, grid_top + cell_h, c_tp_bg, "TRUE POSITIVE (TP)", tp, tp_pct),
    ]

    for cx, cy, bg, label, count, pct in cells:
        draw.rectangle([cx, cy, cx + cell_w, cy + cell_h], fill=bg, outline=c_border, width=2)
        draw.text((cx + 20, cy + 25), label, fill=c_subtext)
        draw.text((cx + 20, cy + 55), f"{count:,}", fill=c_header)
        draw.text((cx + 20, cy + 95), f"Rate: {pct:.1f}% of class", fill=(51, 65, 85))

    # Summary Footer Card
    foot_top = grid_top + 2 * cell_h + 30
    draw.rectangle([40, foot_top, width - 40, foot_top + 80], fill=c_card_bg, outline=c_border, width=1)
    acc = metrics_result["accuracy"] * 100
    prec = metrics_result["precision"] * 100
    rec = metrics_result["recall"] * 100
    f1 = metrics_result["f1_score"] * 100
    roc_str = f"{metrics_result['roc_auc']:.4f}" if metrics_result["roc_auc"] is not None else "N/A"

    draw.text((60, foot_top + 18), f"Accuracy: {acc:.2f}%", fill=(16, 185, 129))
    draw.text((210, foot_top + 18), f"Precision: {prec:.2f}%", fill=c_header)
    draw.text((360, foot_top + 18), f"Recall: {rec:.2f}%", fill=c_header)
    draw.text((500, foot_top + 18), f"F1-Score: {f1:.2f}%", fill=c_header)
    draw.text((640, foot_top + 18), f"ROC-AUC: {roc_str}", fill=(59, 130, 246))

    draw.text(
        (60, foot_top + 48),
        f"Total Samples: {metrics_result['total_samples']:,} | Real Support: {metrics_result['per_class']['authentic_real_0']['support']:,} | Synthetic Support: {metrics_result['per_class']['synthetic_ai_1']['support']:,}",
        fill=c_subtext,
    )

    img.save(str(out_path), "PNG")
    logger.info("Saved confusion matrix image to: %s", out_path)
    return out_path


def evaluate_dataset(
    model: nn.Module,
    samples: List[Tuple[Path, float]],
    batch_size: int = 32,
    device: Optional[torch.device] = None,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Run evaluation inference across discovered samples and return metrics dictionary.
    """
    target_device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _, val_transform = get_transforms(input_size=settings.model_input_size)
    dataset = ImageFolderAuthenticityDataset(samples=samples, transform=val_transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    model.eval()
    all_probs: List[float] = []
    all_targets: List[float] = []

    logger.info("Running evaluation over %d samples (batch size: %d)...", len(dataset), batch_size)
    with torch.no_grad():
        for images, targets in dataloader:
            images = images.to(target_device)
            outputs = model(images)  # Outputs already passed through Sigmoid head
            probs = outputs.squeeze(-1).cpu().numpy().tolist()
            target_list = targets.squeeze(-1).cpu().numpy().tolist()

            all_probs.extend(probs)
            all_targets.extend(target_list)

    y_true = np.array(all_targets, dtype=np.float32)
    y_prob = np.array(all_probs, dtype=np.float64)

    return compute_evaluation_metrics(y_true=y_true, y_prob=y_prob, threshold=threshold)


def print_evaluation_summary(
    metrics: Dict[str, Any],
    metadata: Dict[str, Any],
    test_dir: Path,
    json_path: Path,
    img_path: Path,
) -> None:
    """Print an executive summary table to terminal stdout."""
    cm = metrics["confusion_matrix"]
    tn, fp = cm["matrix"][0]
    fn, tp = cm["matrix"][1]
    p_c0 = metrics["per_class"]["authentic_real_0"]
    p_c1 = metrics["per_class"]["synthetic_ai_1"]
    roc_str = f"{metrics['roc_auc']:.4f}" if metrics["roc_auc"] is not None else "N/A (Single-class dataset)"

    print("\n" + "=" * 80)
    print("                    TruthLens Image Model Evaluation Report")
    print("=" * 80)
    print(f"Model Backbone     : {metadata.get('backbone', 'efficientnet_b0')}")
    print(f"Model Version      : {metadata.get('model_version', '1.0.0')}")
    print(f"Checkpoint Path    : {metadata.get('checkpoint_path', 'None')}")
    print(f"Evaluation Dataset : {test_dir.resolve()} (Total: {metrics['total_samples']:,} samples)")
    print("-" * 80)
    print("Overall Performance Metrics:")
    print(f"  • Accuracy       : {metrics['accuracy'] * 100:.2f}% ({tn + tp:,} / {metrics['total_samples']:,})")
    print(f"  • Precision      : {metrics['precision'] * 100:.2f}%")
    print(f"  • Recall         : {metrics['recall'] * 100:.2f}%")
    print(f"  • F1-Score       : {metrics['f1_score'] * 100:.2f}%")
    print(f"  • Macro F1       : {metrics['macro_f1'] * 100:.2f}%")
    print(f"  • ROC-AUC        : {roc_str}")
    print("-" * 80)
    print("Per-Class Metrics:")
    print("  Class 0 — Authentic / Real:")
    print(f"    - Precision    : {p_c0['precision'] * 100:.2f}%")
    print(f"    - Recall       : {p_c0['recall'] * 100:.2f}%")
    print(f"    - F1-Score     : {p_c0['f1_score'] * 100:.2f}%")
    print(f"    - Support      : {p_c0['support']:,} samples")
    print("  Class 1 — AI-Generated / Synthetic:")
    print(f"    - Precision    : {p_c1['precision'] * 100:.2f}%")
    print(f"    - Recall       : {p_c1['recall'] * 100:.2f}%")
    print(f"    - F1-Score     : {p_c1['f1_score'] * 100:.2f}%")
    print(f"    - Support      : {p_c1['support']:,} samples")
    print("-" * 80)
    print("Confusion Matrix:")
    print(f"{'':20} {'Predicted Real (0)':>22} {'Predicted Synthetic (1)':>25}")
    print(f"  Actual Real (0)    : {tn:>16,} (TN) {fp:>20,} (FP)")
    print(f"  Actual Synth (1)   : {fn:>16,} (FN) {tp:>20,} (TP)")
    print("-" * 80)
    print("Artifacts Generated:")
    print(f"  • JSON Report    : {json_path}")
    print(f"  • Confusion PNG  : {img_path}")
    print("=" * 80 + "\n")


def run_evaluation(
    checkpoint_path: Path | str,
    test_dir: Path | str,
    output_dir: Path | str = Path("./eval_output"),
    backbone_name: str = "efficientnet_b0",
    generators: Optional[List[str]] = None,
    batch_size: int = 32,
    threshold: float = 0.5,
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """
    Main evaluation pipeline orchestrator.
    """
    test_path = Path(test_dir).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Discover test dataset samples
    samples = discover_test_samples(test_path, generators=generators)
    if len(samples) == 0:
        raise ValueError(f"No test samples discovered in {test_path}")

    # 2. Load model with exact production checkpoint verification
    model, metadata = load_evaluation_model(
        checkpoint_path=checkpoint_path,
        backbone_name=backbone_name,
        device=device,
    )

    # 3. Evaluate dataset
    metrics = evaluate_dataset(
        model=model,
        samples=samples,
        batch_size=batch_size,
        device=device,
        threshold=threshold,
    )

    # 4. Generate JSON report
    report_payload = {
        "model": {
            "name": metadata.get("model_name"),
            "backbone": backbone_name,
            "version": metadata.get("model_version"),
            "checkpoint": str(Path(checkpoint_path).resolve()),
            "checkpoint_epoch": metadata.get("epoch"),
        },
        "dataset": {
            "directory": str(test_path),
            "total_samples": metrics["total_samples"],
            "class_counts": {
                "authentic_real_0": metrics["per_class"]["authentic_real_0"]["support"],
                "synthetic_ai_1": metrics["per_class"]["synthetic_ai_1"]["support"],
            },
        },
        "metrics": {
            "threshold": metrics["threshold"],
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": metrics["f1_score"],
            "macro_f1": metrics["macro_f1"],
            "roc_auc": metrics["roc_auc"],
        },
        "per_class_metrics": metrics["per_class"],
        "confusion_matrix": metrics["confusion_matrix"],
        "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    json_path = out_dir / "evaluation_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)
    logger.info("Saved JSON evaluation report to: %s", json_path)

    # 5. Render Confusion Matrix PNG
    img_path = out_dir / "confusion_matrix.png"
    render_confusion_matrix_image(metrics, metadata, img_path)

    # 6. Terminal Summary
    print_evaluation_summary(metrics, metadata, test_path, json_path, img_path)

    return report_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="TruthLens Image Model Standalone Evaluation Framework")
    parser.add_argument("--test-dir", type=Path, required=True, help="Directory containing independent test dataset")
    parser.add_argument("--checkpoint", type=Path, default=None, help="Path to trained model checkpoint (.pt)")
    parser.add_argument("--backbone", type=str, default="efficientnet_b0", help="Model backbone architecture")
    parser.add_argument("--output-dir", type=Path, default=Path("./eval_output"), help="Directory for JSON and PNG reports")
    parser.add_argument("--generators", type=str, default=None, help="Comma-separated generator names to evaluate (for GenImage root)")
    parser.add_argument("--batch-size", type=int, default=32, help="Evaluation batch size")
    parser.add_argument("--threshold", type=float, default=0.5, help="Binary decision threshold (default: 0.5)")
    parser.add_argument("--device", type=str, default=None, help="Device override ('cpu' or 'cuda')")

    args = parser.parse_args()

    ckpt_path = args.checkpoint or (Path(settings.model_dir) / settings.classifier_checkpoint)
    generators_list = [g.strip() for g in args.generators.split(",") if g.strip()] if args.generators else None
    target_device = torch.device(args.device) if args.device else None

    run_evaluation(
        checkpoint_path=ckpt_path,
        test_dir=args.test_dir,
        output_dir=args.output_dir,
        backbone_name=args.backbone,
        generators=generators_list,
        batch_size=args.batch_size,
        threshold=args.threshold,
        device=target_device,
    )


if __name__ == "__main__":
    main()
