"""
Unit and integration tests for TruthLens Image Model Evaluation Framework.

Verifies:
  1. Exact metric calculations (Accuracy, Binary/Per-Class Precision, Recall, F1, Macro F1).
  2. ROC-AUC is calculated using continuous AI probability scores, not discrete thresholded predictions.
  3. Single-class and class-imbalanced datasets are handled safely (ROC-AUC reports None, no crashes).
  4. Test dataset folder discovery (REAL/FAKE, nature/ai, multi-generator GenImage test layouts).
  5. Checkpoint validation strictness.
  6. Confusion matrix PNG rendering and JSON report export.
  7. End-to-end evaluation pipeline execution.
"""

from pathlib import Path
import json
import numpy as np
import pytest
import torch
import torch.nn as nn
from PIL import Image

import evaluate_image
from evaluate_image import (
    compute_evaluation_metrics,
    discover_test_samples,
    load_evaluation_model,
    render_confusion_matrix_image,
    run_evaluation,
)
from services.image_analysis.classifier import _build_model


def _create_dummy_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (32, 32), color=(128, 128, 128))
    img.save(path)


# -----------------------------------------------------------------------------
# 1. Metric Calculations & Verification
# -----------------------------------------------------------------------------

def test_compute_metrics_known_values():
    """Verify TP, TN, FP, FN, per-class and overall metrics against known ground truth."""
    # 4 Authentic (0), 4 Synthetic (1)
    # Authentic: 3 correctly predicted 0 (TN), 1 incorrectly predicted 1 (FP)
    # Synthetic: 3 correctly predicted 1 (TP), 1 incorrectly predicted 0 (FN)
    y_true = np.array([0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0])
    y_prob = np.array([0.1, 0.2, 0.3, 0.8, 0.9, 0.7, 0.6, 0.4])

    metrics = compute_evaluation_metrics(y_true, y_prob, threshold=0.5)

    assert metrics["total_samples"] == 8
    assert metrics["confusion_matrix"]["tp"] == 3
    assert metrics["confusion_matrix"]["tn"] == 3
    assert metrics["confusion_matrix"]["fp"] == 1
    assert metrics["confusion_matrix"]["fn"] == 1

    # Accuracy = 6 / 8 = 0.75
    assert metrics["accuracy"] == 0.75

    # Class 1 (Synthetic): TP=3, FP=1, FN=1 -> Prec = 3/4 = 0.75, Rec = 3/4 = 0.75, F1 = 0.75
    assert metrics["precision"] == 0.75
    assert metrics["recall"] == 0.75
    assert metrics["f1_score"] == 0.75

    # Class 0 (Real): TN=3, FN=1, FP=1 -> Prec = 3/4 = 0.75, Rec = 3/4 = 0.75, F1 = 0.75
    c0 = metrics["per_class"]["authentic_real_0"]
    assert c0["precision"] == 0.75
    assert c0["recall"] == 0.75
    assert c0["f1_score"] == 0.75
    assert c0["support"] == 4

    c1 = metrics["per_class"]["synthetic_ai_1"]
    assert c1["support"] == 4


def test_roc_auc_continuous_probability_dependence():
    """Verify ROC-AUC uses continuous probability scores rather than binary predictions."""
    y_true = np.array([0.0, 0.0, 1.0, 1.0])

    # Ranking 1: Perfect ordering of probabilities
    y_prob_perfect = np.array([0.1, 0.2, 0.8, 0.9])
    res_perfect = compute_evaluation_metrics(y_true, y_prob_perfect)
    assert res_perfect["roc_auc"] == 1.0

    # Ranking 2: Inverted ordering of probabilities
    y_prob_inverted = np.array([0.9, 0.8, 0.2, 0.1])
    res_inverted = compute_evaluation_metrics(y_true, y_prob_inverted)
    assert res_inverted["roc_auc"] == 0.0

    # Ranking 3: Same binary predictions at 0.5 threshold ([0, 0, 1, 1]),
    # but imperfect rank order (one positive has lower prob than one negative)
    y_prob_partial = np.array([0.1, 0.7, 0.6, 0.9])
    res_partial = compute_evaluation_metrics(y_true, y_prob_partial)
    assert 0.0 < res_partial["roc_auc"] < 1.0


def test_single_class_safe_handling():
    """Verify single-class datasets (missing real or synthetic) do not crash and report roc_auc as None."""
    # Only Real images (all 0.0)
    y_true_real_only = np.array([0.0, 0.0, 0.0, 0.0])
    y_prob = np.array([0.1, 0.2, 0.3, 0.4])

    metrics = compute_evaluation_metrics(y_true_real_only, y_prob)
    assert metrics["roc_auc"] is None
    assert metrics["per_class"]["synthetic_ai_1"]["support"] == 0
    assert metrics["per_class"]["authentic_real_0"]["support"] == 4
    assert metrics["accuracy"] == 1.0

    # Only Synthetic images (all 1.0)
    y_true_synth_only = np.array([1.0, 1.0, 1.0])
    metrics_synth = compute_evaluation_metrics(y_true_synth_only, y_prob[:3])
    assert metrics_synth["roc_auc"] is None
    assert metrics_synth["per_class"]["authentic_real_0"]["support"] == 0
    assert metrics_synth["per_class"]["synthetic_ai_1"]["support"] == 3


# -----------------------------------------------------------------------------
# 2. Test Dataset Discovery
# -----------------------------------------------------------------------------

def test_discover_test_samples_layouts(tmp_path: Path):
    """Verify discovery from test/ subfolder and direct class folders."""
    # Layout A: Direct class folders (nature / ai)
    layout_a = tmp_path / "layout_a"
    _create_dummy_image(layout_a / "nature" / "img1.png")
    _create_dummy_image(layout_a / "ai" / "img2.jpg")

    samples_a = discover_test_samples(layout_a)
    assert len(samples_a) == 2
    labels_a = {p.name: label for p, label in samples_a}
    assert labels_a["img1.png"] == 0.0
    assert labels_a["img2.jpg"] == 1.0

    # Layout B: Explicit test/ subfolder (cifake style: test/REAL, test/FAKE)
    layout_b = tmp_path / "layout_b"
    _create_dummy_image(layout_b / "test" / "REAL" / "real.png")
    _create_dummy_image(layout_b / "test" / "FAKE" / "fake.png")
    _create_dummy_image(layout_b / "train" / "REAL" / "train_real.png")  # Must be ignored

    samples_b = discover_test_samples(layout_b)
    assert len(samples_b) == 2
    assert all("test" in str(p[0]) for p in samples_b)
    assert not any("train" in str(p[0]) for p in samples_b)

    # Layout C: Multi-generator filtering
    layout_c = tmp_path / "layout_c"
    _create_dummy_image(layout_c / "midjourney" / "test" / "ai" / "mj_ai.png")
    _create_dummy_image(layout_c / "midjourney" / "test" / "nature" / "mj_nat.png")
    _create_dummy_image(layout_c / "wukong" / "test" / "ai" / "wk_ai.png")
    _create_dummy_image(layout_c / "wukong" / "test" / "nature" / "wk_nat.png")

    samples_filtered = discover_test_samples(layout_c, generators=["midjourney"])
    assert len(samples_filtered) == 2
    assert all("midjourney" in str(p[0]) for p in samples_filtered)
    assert not any("wukong" in str(p[0]) for p in samples_filtered)


# -----------------------------------------------------------------------------
# 3. Checkpoint Validation Strictness
# -----------------------------------------------------------------------------

def test_checkpoint_validation_strictness(tmp_path: Path):
    """Verify strict validation of missing files, architecture mismatch, and missing head weights."""
    # 1. Missing file
    with pytest.raises(FileNotFoundError):
        load_evaluation_model(tmp_path / "non_existent.pt")

    # 2. Checkpoint with backbone mismatch
    bad_backbone_ckpt = tmp_path / "bad_backbone.pt"
    torch.save({"backbone": "resnet50", "model_state_dict": {}}, bad_backbone_ckpt)
    with pytest.raises(RuntimeError, match="Backbone mismatch"):
        load_evaluation_model(bad_backbone_ckpt, backbone_name="efficientnet_b0")

    # 3. Checkpoint missing head weights
    missing_head_ckpt = tmp_path / "missing_head.pt"
    torch.save({"backbone": "efficientnet_b0", "model_state_dict": {"conv.weight": torch.zeros(1)}}, missing_head_ckpt)
    with pytest.raises(RuntimeError, match="missing classification head weights"):
        load_evaluation_model(missing_head_ckpt, backbone_name="efficientnet_b0")


# -----------------------------------------------------------------------------
# 4. Artifact Rendering & End-to-End Pipeline
# -----------------------------------------------------------------------------

def test_confusion_matrix_image_rendering(tmp_path: Path):
    """Verify PNG confusion matrix image generation."""
    metrics = {
        "accuracy": 0.85,
        "precision": 0.88,
        "recall": 0.82,
        "f1_score": 0.85,
        "roc_auc": 0.92,
        "total_samples": 100,
        "per_class": {
            "authentic_real_0": {"support": 50},
            "synthetic_ai_1": {"support": 50},
        },
        "confusion_matrix": {
            "matrix": [[43, 7], [9, 41]],
        },
    }
    metadata = {
        "model_name": "TruthLens-EfficientNet-B0",
        "backbone": "efficientnet_b0",
        "model_version": "1.0.0",
    }
    out_img = tmp_path / "confusion_matrix.png"
    render_confusion_matrix_image(metrics, metadata, out_img)

    assert out_img.is_file()
    assert out_img.stat().st_size > 1000

    # Ensure it's a valid readable PNG
    with Image.open(out_img) as img:
        assert img.format == "PNG"
        assert img.size == (760, 620)


def test_end_to_end_evaluation_pipeline(tmp_path: Path):
    """Test full evaluation pipeline from checkpoint loading to report generation."""
    # 1. Build a valid model and save a test checkpoint
    model = _build_model("efficientnet_b0")
    ckpt_path = tmp_path / "test_model.pt"
    payload = {
        "epoch": 1,
        "model_state_dict": model.state_dict(),
        "backbone": "efficientnet_b0",
        "model_version": "1.0.0-test",
        "metrics": {"val_f1": 0.90},
    }
    torch.save(payload, str(ckpt_path))

    # 2. Create small test dataset (2 real, 2 fake)
    test_dir = tmp_path / "test_dataset"
    _create_dummy_image(test_dir / "real" / "real1.png")
    _create_dummy_image(test_dir / "real" / "real2.jpg")
    _create_dummy_image(test_dir / "fake" / "fake1.png")
    _create_dummy_image(test_dir / "fake" / "fake2.jpg")

    out_dir = tmp_path / "eval_out"

    # 3. Run evaluation
    report = run_evaluation(
        checkpoint_path=ckpt_path,
        test_dir=test_dir,
        output_dir=out_dir,
        backbone_name="efficientnet_b0",
        batch_size=2,
        device=torch.device("cpu"),
    )

    # 4. Verify outputs
    assert report["dataset"]["total_samples"] == 4
    assert (out_dir / "evaluation_report.json").is_file()
    assert (out_dir / "confusion_matrix.png").is_file()

    with open(out_dir / "evaluation_report.json", "r", encoding="utf-8") as f:
        saved_report = json.load(f)
        assert saved_report["model"]["backbone"] == "efficientnet_b0"
        assert saved_report["metrics"]["total_samples"] if "total_samples" in saved_report["metrics"] else saved_report["dataset"]["total_samples"] == 4
        assert "accuracy" in saved_report["metrics"]
        assert "roc_auc" in saved_report["metrics"]
        assert "per_class_metrics" in saved_report
