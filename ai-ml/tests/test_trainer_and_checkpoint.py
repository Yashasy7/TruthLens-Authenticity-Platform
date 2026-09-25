"""
Tests for services/image_analysis/trainer.py and checkpoint loading in classifier.py
Module 05 — Model Fine-Tuning & Weights Management
"""

from pathlib import Path
import numpy as np
import pytest
import torch
from PIL import Image

from config.settings import settings
from services.image_analysis.classifier import (
    get_model_metadata,
    load_model,
    predict_synthetic,
    reset_model,
)
from services.image_analysis.trainer import (
    compute_metrics,
    train_classifier,
)


@pytest.fixture(autouse=True)
def cleanup_classifier():
    reset_model()
    prev_ckpt = settings.classifier_checkpoint
    prev_req = settings.require_checkpoint
    yield
    reset_model()
    settings.classifier_checkpoint = prev_ckpt
    settings.require_checkpoint = prev_req


@pytest.fixture
def synthetic_training_data(tmp_path: Path):
    """Generate a tiny dataset of 4 authentic and 4 synthetic images."""
    data_dir = tmp_path / "dataset"
    auth_dir = data_dir / "authentic"
    synth_dir = data_dir / "synthetic"
    auth_dir.mkdir(parents=True)
    synth_dir.mkdir(parents=True)

    rng = np.random.default_rng(101)
    train_samples = []
    val_samples = []

    for i in range(4):
        # Authentic (smooth/organic)
        arr = rng.integers(100, 200, (64, 64, 3), dtype=np.uint8)
        p = auth_dir / f"auth_{i}.png"
        Image.fromarray(arr).save(p)
        if i < 3:
            train_samples.append((p, 0.0))
        else:
            val_samples.append((p, 0.0))

        # Synthetic (sharp noise/patterns)
        arr2 = rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)
        p2 = synth_dir / f"synth_{i}.png"
        Image.fromarray(arr2).save(p2)
        if i < 3:
            train_samples.append((p2, 1.0))
        else:
            val_samples.append((p2, 1.0))

    return train_samples, val_samples


class TestTrainerAndMetrics:

    def test_compute_metrics_perfect_predictions(self):
        y_true = np.array([0.0, 0.0, 1.0, 1.0])
        y_prob = np.array([0.1, 0.2, 0.9, 0.8])
        metrics = compute_metrics(y_true, y_prob)

        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0
        assert metrics["roc_auc"] == 1.0

    def test_compute_metrics_imperfect_predictions(self):
        y_true = np.array([0.0, 1.0, 1.0, 0.0])
        y_prob = np.array([0.8, 0.9, 0.1, 0.2])  # 2 errors
        metrics = compute_metrics(y_true, y_prob)

        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["f1"] <= 1.0

    def test_train_pipeline_and_checkpoint_saving(self, synthetic_training_data, tmp_path):
        train_samples, val_samples = synthetic_training_data
        ckpt_dest = tmp_path / "models" / "test_model.pt"

        res = train_classifier(
            train_samples=train_samples,
            val_samples=val_samples,
            output_checkpoint_path=ckpt_dest,
            backbone_name="efficientnet_b0",
            epochs=1,
            batch_size=2,
            lr=1e-4,
            unfreeze_backbone=False,
            model_version="1.0.0-test",
        )

        assert ckpt_dest.exists()
        assert "best_val_f1" in res
        assert len(res["history"]) == 1

        # Verify checkpoint contents
        saved = torch.load(str(ckpt_dest), map_location="cpu")
        assert "model_state_dict" in saved
        assert saved["model_version"] == "1.0.0-test"
        assert "metrics" in saved

    def test_load_trained_checkpoint_into_classifier(self, synthetic_training_data, tmp_path):
        train_samples, val_samples = synthetic_training_data
        ckpt_dest = tmp_path / "models" / "trained_eval.pt"

        train_classifier(
            train_samples=train_samples,
            val_samples=val_samples,
            output_checkpoint_path=ckpt_dest,
            epochs=1,
            batch_size=2,
            model_version="1.5.0-prod",
        )

        # Configure settings to load this checkpoint
        settings.classifier_checkpoint = str(ckpt_dest)
        reset_model()

        model = load_model()
        assert model is not None
        assert not model.training  # model is in eval mode

        name, version = get_model_metadata()
        assert version == "1.5.0-prod"

        # Verify inference
        tensor = torch.zeros(1, 3, 224, 224)
        prob, conf = predict_synthetic(tensor)
        assert 0.0 <= prob <= 1.0
        assert 0.0 <= conf <= 1.0

    def test_missing_checkpoint_raises_filenotfound(self):
        settings.classifier_checkpoint = "nonexistent_weights.pt"
        settings.require_checkpoint = True
        reset_model()

        with pytest.raises(FileNotFoundError) as exc_info:
            load_model()
        assert "not found" in str(exc_info.value)
