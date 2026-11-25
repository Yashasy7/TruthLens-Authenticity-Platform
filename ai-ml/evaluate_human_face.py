"""
TruthLens AI/ML — Stage 1: Human-Face 3-Class Evaluation & Manifest Audit

Provides:
1. Standalone leakage & schema verification for `dataset_manifest.json` (`--verify-only`).
2. Complete 3-class evaluation metrics (`Accuracy`, `Macro-F1`, `Weighted-F1`,
   3x3 confusion matrix, per-class Precision/Recall/F1/FPR/FNR, One-vs-Rest ROC-AUC,
   and per-generator / mixed-label breakdown).
3. Strict checkpoint contract verification (backbone, exact class ordering, and
   normalization metadata) and CPU/GPU evaluation for EfficientNet-B0 3-class checkpoints.

Production `services/image_analysis/` remains completely isolated and untouched.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from PIL import Image
import timm
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

AI_ML_ROOT = Path(__file__).resolve().parent
if str(AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ML_ROOT))

from human_face_dataset import CLASS_NAMES, CLASS_TO_ID, _dhash_bands  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.evaluate_human_face")

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def compute_binary_roc_auc(y_true: np.ndarray, y_scores: np.ndarray) -> Optional[float]:
    """
    Tie-aware Mann-Whitney U ROC-AUC without external sklearn dependency.
    Returns None if only one class is present in `y_true`.
    """
    pos_mask = y_true == 1
    n_pos = int(np.sum(pos_mask))
    n_neg = int(len(y_true) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return None

    order = np.argsort(y_scores, kind="mergesort")
    sorted_scores = y_scores[order]
    sorted_pos = pos_mask[order]

    ranks = np.empty(len(y_scores), dtype=np.float64)
    i = 0
    n = len(sorted_scores)
    while i < n:
        j = i + 1
        while j < n and sorted_scores[j] == sorted_scores[i]:
            j += 1
        avg_rank = 0.5 * ((i + 1) + j)
        ranks[i:j] = avg_rank
        i = j

    pos_rank_sum = float(np.sum(ranks[sorted_pos]))
    u_stat = pos_rank_sum - (n_pos * (n_pos + 1)) / 2.0
    return float(u_stat / (n_pos * n_neg))


def compute_multiclass_metrics(
    y_true: Sequence[int],
    y_probs: np.ndarray,
    class_names: Sequence[str] = CLASS_NAMES,
    require_all_classes: bool = True,
) -> Dict[str, Any]:
    """
    Compute multi-class evaluation metrics from integer true labels `[N]` and softmax probs `[N, C]`.

    Raises ValueError by default when any required class has `support == 0`, preventing
    silently inflated partial-class Macro-F1 scores.
    """
    if tuple(class_names) != CLASS_NAMES:
        raise ValueError(f"Expected canonical class order {list(CLASS_NAMES)}, got {list(class_names)}.")

    y_true_arr = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.asarray(y_probs, dtype=np.float64)
    num_classes = len(class_names)

    if probs_arr.ndim != 2 or probs_arr.shape[1] != num_classes:
        raise ValueError(f"Expected probs shape [N, {num_classes}], got {probs_arr.shape}.")
    if len(y_true_arr) == 0:
        raise ValueError("Cannot compute metrics on an empty evaluation set.")

    y_pred_arr = np.argmax(probs_arr, axis=1)
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true_arr, y_pred_arr):
        cm[int(t), int(p)] += 1

    total = int(len(y_true_arr))
    accuracy = float(np.trace(cm) / total)

    per_class: Dict[str, Dict[str, Any]] = {}
    f1_values: List[float] = []
    weights: List[int] = []
    auc_values: List[float] = []
    missing_classes: List[str] = []

    for c_idx, cls_name in enumerate(class_names):
        tp = int(cm[c_idx, c_idx])
        fn = int(np.sum(cm[c_idx, :]) - tp)
        fp = int(np.sum(cm[:, c_idx]) - tp)
        tn = int(total - tp - fn - fp)
        support = tp + fn

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float((2.0 * precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

        ovr_binary = (y_true_arr == c_idx).astype(np.int64)
        ovr_auc = compute_binary_roc_auc(ovr_binary, probs_arr[:, c_idx])
        if ovr_auc is not None:
            auc_values.append(ovr_auc)

        if support == 0:
            missing_classes.append(cls_name)
        else:
            f1_values.append(f1)
            weights.append(support)

        per_class[cls_name] = {
            "support": support,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "fpr": round(fpr, 6),
            "fnr": round(fnr, 6),
            "ovr_roc_auc": round(ovr_auc, 6) if ovr_auc is not None else None,
        }

    if missing_classes:
        msg = f"Evaluation split is missing required classes {missing_classes}; partial Macro-F1 would be misleading."
        if require_all_classes:
            raise ValueError(msg)
        logger.warning(msg)

    macro_f1 = float(np.mean(f1_values)) if f1_values else 0.0
    weighted_f1 = float(np.average(f1_values, weights=weights)) if weights else 0.0
    macro_ovr_auc = float(np.mean(auc_values)) if auc_values else None

    non_genuine_mask = y_true_arr != 0
    if np.any(non_genuine_mask):
        false_genuine_rate = float(np.mean(y_pred_arr[non_genuine_mask] == 0))
    else:
        false_genuine_rate = None

    return {
        "total_samples": total,
        "accuracy": round(accuracy, 6),
        "macro_f1": round(macro_f1, 6),
        "weighted_f1": round(weighted_f1, 6),
        "macro_ovr_roc_auc": round(macro_ovr_auc, 6) if macro_ovr_auc is not None else None,
        "false_genuine_rate": round(false_genuine_rate, 6) if false_genuine_rate is not None else None,
        "missing_classes": missing_classes,
        "partial_class_evaluation": len(missing_classes) > 0,
        "class_names": list(class_names),
        "confusion_matrix": cm.tolist(),
        "per_class": per_class,
    }


def compute_per_generator_breakdown(
    records: Sequence[Dict[str, Any]],
    y_true: Sequence[int],
    y_probs: np.ndarray,
    class_names: Sequence[str] = CLASS_NAMES,
) -> Dict[str, Dict[str, Any]]:
    """
    Summarize accuracy, label distribution, mixed-label safe false-genuine rate,
    and mean probabilities per `source_subset`.
    """
    probs_arr = np.asarray(y_probs, dtype=np.float64)
    preds = np.argmax(probs_arr, axis=1)

    grouped_indices: Dict[str, List[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        subset = str(rec.get("source_subset") or "unknown")
        grouped_indices[subset].append(idx)

    breakdown: Dict[str, Dict[str, Any]] = {}
    for subset in sorted(grouped_indices.keys()):
        idxs = grouped_indices[subset]
        sub_true = np.asarray([y_true[i] for i in idxs], dtype=np.int64)
        sub_pred = preds[idxs]
        sub_probs = probs_arr[idxs]

        label_dist_raw = Counter(sub_true.tolist())
        label_distribution = {
            class_names[int(k)]: int(v) for k, v in sorted(label_dist_raw.items())
        }
        expected_class = class_names[int(sub_true[0])] if len(label_distribution) == 1 else "mixed"

        acc = float(np.mean(sub_pred == sub_true))
        non_genuine_mask = sub_true != 0
        false_genuine = (
            float(np.mean(sub_pred[non_genuine_mask] == 0)) if np.any(non_genuine_mask) else None
        )
        mean_probs = {
            cls_name: round(float(np.mean(sub_probs[:, c_i])), 6)
            for c_i, cls_name in enumerate(class_names)
        }
        breakdown[subset] = {
            "count": len(idxs),
            "expected_class": expected_class,
            "label_distribution": label_distribution,
            "non_genuine_count": int(np.sum(non_genuine_mask)),
            "accuracy": round(acc, 6),
            "false_genuine_rate": round(false_genuine, 6) if false_genuine is not None else None,
            "mean_probabilities": mean_probs,
        }

    return breakdown


def verify_manifest_integrity(
    manifest_path: Path,
    check_files_exist: bool = False,
    dhash_hamming_threshold: int = 4,
) -> Dict[str, Any]:
    """
    Validate manifest structure, label consistency, cross-split hash/group/identity
    leakage (including Hamming near-duplicates), and unseen-generator separation.
    """
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    images: List[Dict[str, Any]] = manifest.get("images", [])
    split_sha: Dict[str, Set[str]] = defaultdict(set)
    split_md5: Dict[str, Set[str]] = defaultdict(set)
    split_dhash: Dict[str, Set[str]] = defaultdict(set)
    split_groups: Dict[str, Set[str]] = defaultdict(set)
    split_tokens: Dict[str, Set[str]] = defaultdict(set)
    split_paths: Dict[str, Set[str]] = defaultdict(set)
    split_gens: Dict[str, Set[str]] = defaultdict(set)
    split_class_counts: Dict[str, Counter] = defaultdict(Counter)

    dhash_records: List[Tuple[str, int]] = []
    errors: List[str] = []
    manifest_dir = manifest_path.parent

    for idx, rec in enumerate(images):
        sp = rec.get("split")
        cls_name = rec.get("class_name")
        label = rec.get("label")
        if sp not in ("train", "val", "test"):
            errors.append(f"Row {idx}: invalid split '{sp}'")
            continue
        if cls_name not in CLASS_TO_ID or label != CLASS_TO_ID[cls_name]:
            errors.append(f"Row {idx}: class_name '{cls_name}' mismatches label '{label}'")

        rel_img = str(rec.get("image_path") or "")
        split_paths[sp].add(rel_img)
        if rec.get("sha256"):
            split_sha[sp].add(str(rec["sha256"]))
        if rec.get("md5"):
            split_md5[sp].add(str(rec["md5"]))
        if rec.get("dhash"):
            d_hex = str(rec["dhash"])
            split_dhash[sp].add(d_hex)
            try:
                dhash_records.append((sp, int(d_hex, 16)))
            except ValueError:
                pass
        if rec.get("source_group_id"):
            split_groups[sp].add(str(rec["source_group_id"]))
        for tok in rec.get("identity_tokens", ()):
            split_tokens[sp].add(str(tok))
        if rec.get("source_subset"):
            split_gens[sp].add(str(rec["source_subset"]))
        split_class_counts[sp][str(cls_name)] += 1

        if check_files_exist:
            cand = Path(rel_img)
            if not cand.is_absolute():
                cand = manifest_dir / cand
            if not cand.exists():
                errors.append(f"Row {idx}: missing file {cand}")

    # Exact cross-split near-duplicate check via Hamming distance
    near_dup_cross_pairs = 0
    if dhash_hamming_threshold > 0 and dhash_records:
        num_bands = min(16, dhash_hamming_threshold + 1)
        seen_by_band: Dict[Tuple[int, int], List[Tuple[str, int]]] = defaultdict(list)
        for sp, h_int in dhash_records:
            seen_candidates: Set[Tuple[str, int]] = set()
            for bk in _dhash_bands(h_int, num_bands):
                for prev in seen_by_band.get(bk, ()):
                    if prev[0] != sp:
                        seen_candidates.add(prev)
                seen_by_band[bk].append((sp, h_int))
            for _, prev_int in seen_candidates:
                if (h_int ^ prev_int).bit_count() <= dhash_hamming_threshold:
                    near_dup_cross_pairs += 1
                    break

    leakage = {
        "sha256_train_val": len(split_sha["train"] & split_sha["val"]),
        "sha256_train_test": len(split_sha["train"] & split_sha["test"]),
        "sha256_val_test": len(split_sha["val"] & split_sha["test"]),
        "md5_train_val": len(split_md5["train"] & split_md5["val"]),
        "md5_train_test": len(split_md5["train"] & split_md5["test"]),
        "md5_val_test": len(split_md5["val"] & split_md5["test"]),
        "dhash_train_val": len(split_dhash["train"] & split_dhash["val"]),
        "dhash_train_test": len(split_dhash["train"] & split_dhash["test"]),
        "dhash_val_test": len(split_dhash["val"] & split_dhash["test"]),
        "dhash_hamming_cross_split": near_dup_cross_pairs,
        "group_train_val": len(split_groups["train"] & split_groups["val"]),
        "group_train_test": len(split_groups["train"] & split_groups["test"]),
        "group_val_test": len(split_groups["val"] & split_groups["test"]),
        "identity_token_train_val": len(split_tokens["train"] & split_tokens["val"]),
        "identity_token_train_test": len(split_tokens["train"] & split_tokens["test"]),
        "identity_token_val_test": len(split_tokens["val"] & split_tokens["test"]),
        "path_train_val": len(split_paths["train"] & split_paths["val"]),
        "path_train_test": len(split_paths["train"] & split_paths["test"]),
        "path_val_test": len(split_paths["val"] & split_paths["test"]),
    }
    total_leaks = sum(leakage.values())
    unseen_test_gens = sorted(split_gens["test"] - (split_gens["train"] | split_gens["val"]))

    return {
        "manifest_path": str(manifest_path),
        "total_images": len(images),
        "split_counts": {sp: dict(split_class_counts[sp]) for sp in ("train", "val", "test")},
        "leakage": leakage,
        "total_leaks": total_leaks,
        "unseen_test_generators": unseen_test_gens,
        "schema_errors": errors[:50],
        "schema_error_count": len(errors),
        "passed": total_leaks == 0 and len(errors) == 0 and len(images) > 0,
    }


def build_human_face_efficientnet_b0(
    num_classes: int = 3,
    pretrained: bool = False,
) -> nn.Module:
    """
    Build EfficientNet-B0 3-class architecture matching TruthLens `classifier.py`
    layer naming (`head.1.weight`, `head.1.bias`) with raw logits output.
    """
    model = timm.create_model("efficientnet_b0", pretrained=pretrained, num_classes=0)
    num_features = int(model.num_features)
    model.head = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(num_features, num_classes),
    )

    def _patched_forward(x: torch.Tensor) -> torch.Tensor:
        features = model.forward_features(x)
        pooled = model.forward_head(features, pre_logits=True)
        return model.head(pooled)

    model.forward = _patched_forward  # type: ignore[method-assign]
    return model


def load_human_face_checkpoint(
    checkpoint_path: Path,
    device: torch.device,
) -> Tuple[nn.Module, Dict[str, Any]]:
    """
    Load and validate an exported Colab 3-class EfficientNet-B0 checkpoint.

    Strictly validates:
    - Required contract keys (`model_state_dict`, `backbone`, `num_classes`,
      `class_names`, `input_size`, `normalization`)
    - Exact class ordering `["genuine", "ai_generated", "manipulated"]`
    - Valid normalization `mean` and `std` vectors of length 3
    """
    ckpt = torch.load(str(checkpoint_path), map_location=device, weights_only=False)
    required_keys = {
        "model_state_dict",
        "backbone",
        "num_classes",
        "class_names",
        "input_size",
        "normalization",
    }
    missing = required_keys - set(ckpt.keys())
    if missing:
        raise ValueError(f"Checkpoint missing required contract keys: {sorted(missing)}")

    if ckpt["backbone"] != "efficientnet_b0":
        raise ValueError(f"Expected backbone 'efficientnet_b0', got '{ckpt['backbone']}'.")

    num_classes = int(ckpt["num_classes"])
    ckpt_class_names = tuple(str(c) for c in ckpt["class_names"])
    if num_classes != len(CLASS_NAMES) or ckpt_class_names != CLASS_NAMES:
        raise ValueError(
            f"Checkpoint class specification mismatch: expected num_classes={len(CLASS_NAMES)} "
            f"and class_names={list(CLASS_NAMES)}, got num_classes={num_classes}, "
            f"class_names={list(ckpt_class_names)}."
        )

    norm = ckpt["normalization"]
    if (
        not isinstance(norm, dict)
        or len(norm.get("mean", ())) != 3
        or len(norm.get("std", ())) != 3
    ):
        raise ValueError(f"Checkpoint normalization metadata invalid: {norm}")

    model = build_human_face_efficientnet_b0(num_classes=num_classes, pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)
    model.to(device)
    model.eval()
    return model, ckpt


class _ManifestEvalDataset(Dataset):
    """Streaming PyTorch Dataset reading manifest rows on the fly using checkpoint normalization."""

    def __init__(
        self,
        records: Sequence[Dict[str, Any]],
        data_root: Path,
        input_size: int = 224,
        mean: Sequence[float] = IMAGENET_MEAN,
        std: Sequence[float] = IMAGENET_STD,
    ) -> None:
        self.records = list(records)
        self.data_root = data_root
        resize_dim = int(round(input_size * 1.143))
        self.transform = transforms.Compose(
            [
                transforms.Resize(resize_dim),
                transforms.CenterCrop(input_size),
                transforms.ToTensor(),
                transforms.Normalize(mean=tuple(float(v) for v in mean), std=tuple(float(v) for v in std)),
            ]
        )

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        rec = self.records[idx]
        path = Path(rec["image_path"])
        if not path.is_absolute():
            path = self.data_root / path
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            tensor = self.transform(rgb)
        return tensor, int(rec["label"])


def evaluate_checkpoint_on_manifest(
    checkpoint_path: Path,
    manifest_path: Path,
    split: str = "test",
    data_root: Optional[Path] = None,
    batch_size: int = 32,
    output_dir: Optional[Path] = None,
    require_all_classes: bool = True,
) -> Dict[str, Any]:
    """Run inference over a manifest split using checkpoint metadata and export JSON + Markdown reports."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    records = [r for r in manifest.get("images", []) if r.get("split") == split]
    if not records:
        raise ValueError(f"No records found for split='{split}' in {manifest_path}.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, ckpt = load_human_face_checkpoint(checkpoint_path, device=device)
    input_size = int(ckpt["input_size"])
    class_names = tuple(ckpt["class_names"])
    norm = ckpt["normalization"]

    root = data_root or manifest_path.parent
    dataset = _ManifestEvalDataset(
        records=records,
        data_root=root,
        input_size=input_size,
        mean=norm["mean"],
        std=norm["std"],
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    all_probs: List[np.ndarray] = []
    all_targets: List[int] = []

    with torch.no_grad():
        for images_batch, labels_batch in loader:
            logits = model(images_batch.to(device))
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            all_probs.append(probs)
            all_targets.extend(labels_batch.numpy().tolist())

    probs_np = np.concatenate(all_probs, axis=0)
    metrics = compute_multiclass_metrics(
        all_targets,
        probs_np,
        class_names=class_names,
        require_all_classes=require_all_classes,
    )
    gen_breakdown = compute_per_generator_breakdown(records, all_targets, probs_np, class_names=class_names)

    report = {
        "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checkpoint_path": str(checkpoint_path),
        "model_version": ckpt.get("model_version"),
        "manifest_path": str(manifest_path),
        "split": split,
        "normalization": norm,
        "input_size": input_size,
        "metrics": metrics,
        "per_generator_breakdown": gen_breakdown,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_out = output_dir / f"human_face_eval_{split}.json"
        md_out = output_dir / f"human_face_eval_{split}.md"
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        with open(md_out, "w", encoding="utf-8") as f:
            f.write(render_markdown_report(report))

    return report


def render_markdown_report(report: Dict[str, Any]) -> str:
    """Format an evaluation report dictionary into clean Markdown."""
    m = report["metrics"]
    lines = [
        "# TruthLens Human-Face 3-Class Evaluation Report",
        "",
        f"- **Evaluated At:** `{report['evaluated_at']}`",
        f"- **Checkpoint:** `{report['checkpoint_path']}` (version: `{report.get('model_version')}`)",
        f"- **Split:** `{report['split']}` ({m['total_samples']} samples)",
        f"- **Accuracy:** `{m['accuracy']:.4f}`",
        f"- **Macro-F1:** `{m['macro_f1']:.4f}`",
        f"- **Macro OVR ROC-AUC:** `{m['macro_ovr_roc_auc']}`",
        f"- **False-Genuine Rate (fake/manipulated predicted genuine):** `{m['false_genuine_rate']}`",
        "",
        "## Per-Class Metrics",
        "",
        "| Class | Support | Precision | Recall | F1 | FPR | FNR | OVR ROC-AUC |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cls_name, cm_metrics in m["per_class"].items():
        lines.append(
            f"| {cls_name} | {cm_metrics['support']} | {cm_metrics['precision']:.4f} | "
            f"{cm_metrics['recall']:.4f} | {cm_metrics['f1']:.4f} | {cm_metrics['fpr']:.4f} | "
            f"{cm_metrics['fnr']:.4f} | {cm_metrics['ovr_roc_auc']} |"
        )

    lines.extend(["", "## Per-Generator Breakdown", "", "| Subset | Count | Expected Class | Accuracy | False-Genuine Rate |", "|---|---:|---|---:|---:|"])
    for subset, info in report.get("per_generator_breakdown", {}).items():
        lines.append(
            f"| {subset} | {info['count']} | {info['expected_class']} | "
            f"{info['accuracy']:.4f} | {info['false_genuine_rate']} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify manifest integrity or evaluate 3-class human-face checkpoint.")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to dataset_manifest.json.")
    parser.add_argument("--verify-only", action="store_true", help="Run schema & leakage verification only.")
    parser.add_argument("--check-files-exist", action="store_true", help="Verify every manifest path exists on disk.")
    parser.add_argument("--checkpoint", type=Path, default=None, help="Path to exported 3-class .pt checkpoint.")
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--allow-partial-classes",
        action="store_true",
        help="Allow evaluation even when a class has support=0 (emits warning; disabled by default).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    integrity = verify_manifest_integrity(args.manifest, check_files_exist=args.check_files_exist)
    logger.info("Manifest check passed=%s | total=%d | leaks=%d", integrity["passed"], integrity["total_images"], integrity["total_leaks"])
    if not integrity["passed"]:
        logger.error("Manifest integrity failed: %s", json.dumps(integrity, indent=2))
        raise SystemExit(1)

    if args.verify_only:
        print(json.dumps(integrity, indent=2))
        return

    if args.checkpoint is None:
        raise ValueError("--checkpoint is required unless --verify-only is set.")

    report = evaluate_checkpoint_on_manifest(
        checkpoint_path=args.checkpoint,
        manifest_path=args.manifest,
        split=args.split,
        data_root=args.data_root,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
        require_all_classes=not args.allow_partial_classes,
    )
    print(json.dumps(report["metrics"], indent=2))


if __name__ == "__main__":
    main()
