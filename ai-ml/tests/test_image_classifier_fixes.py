"""
Targeted verification tests for TruthLens Image Classifier Bug Fixes and Pipeline Correction.
Verifies points A through G from the specification:
  A. BatchNorm running statistics remain unchanged when unfreeze_backbone=False.
  B. Classification head receives gradients and updates while backbone remains frozen.
  C. Model directory and checkpoint paths resolve reliably regardless of CWD.
  D. Missing or incompatible checkpoints cause explicit initialization failure.
  E. Corrected label mappings are consistent across training and inference.
  F. Failed inference does not produce a fabricated ai_prob=0.0 result.
  G. FastAPI BackendImageAnalysisResponse fields match Spring Boot expectations.
"""

from pathlib import Path
import tempfile
import numpy as np
import pytest
import torch
import torch.nn as nn
from PIL import Image

from config.settings import settings
from schemas.image_analysis import BackendImageAnalysisResponse
from services.image_analysis.classifier import (
    _build_model,
    is_model_trained,
    load_model,
    predict_synthetic,
    reset_model,
)
from services.image_analysis.service import analyze_image_bytes
from services.image_analysis.trainer import (
    ImageFolderAuthenticityDataset,
    set_model_train_mode,
)
from utils.image_utils import preprocess_for_model


@pytest.fixture(autouse=True)
def cleanup_classifier():
    reset_model()
    prev_ckpt = settings.classifier_checkpoint
    prev_req = settings.require_checkpoint
    yield
    reset_model()
    settings.classifier_checkpoint = prev_ckpt
    settings.require_checkpoint = prev_req


# -----------------------------------------------------------------------------
# A. BatchNorm running statistics remain unchanged across training steps
# -----------------------------------------------------------------------------
def test_batchnorm_running_stats_remain_unchanged_when_backbone_frozen():
    model = _build_model("efficientnet_b0")
    set_model_train_mode(model, unfreeze_backbone=False)

    # Collect initial running statistics from all BatchNorm modules
    initial_stats = {}
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
            assert not module.training, f"BatchNorm layer {name} must be in eval mode!"
            initial_stats[name] = (
                module.running_mean.clone(),
                module.running_var.clone(),
                module.num_batches_tracked.clone() if module.num_batches_tracked is not None else None,
            )

    # Pass 5 random batches through the model
    dummy_input = torch.randn(4, 3, 224, 224)
    for _ in range(5):
        _ = model(dummy_input)

    # Verify that all running statistics are 100% unchanged
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
            init_mean, init_var, init_batches = initial_stats[name]
            assert torch.equal(module.running_mean, init_mean), f"BatchNorm {name} running_mean changed!"
            assert torch.equal(module.running_var, init_var), f"BatchNorm {name} running_var changed!"
            if init_batches is not None:
                assert torch.equal(module.num_batches_tracked, init_batches), f"BatchNorm {name} num_batches_tracked changed!"


# -----------------------------------------------------------------------------
# B. Classification head receives gradients and can update
# -----------------------------------------------------------------------------
def test_classification_head_receives_gradients_and_updates():
    model = _build_model("efficientnet_b0")

    # Freeze backbone, train head
    for param in model.parameters():
        param.requires_grad = False
    for param in model.head.parameters():
        param.requires_grad = True

    set_model_train_mode(model, unfreeze_backbone=False)

    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3)
    criterion = nn.BCELoss()

    head_weight_before = model.head[1].weight.clone()
    head_bias_before = model.head[1].bias.clone()

    inputs = torch.randn(4, 3, 224, 224)
    targets = torch.tensor([[1.0], [0.0], [1.0], [0.0]], dtype=torch.float32)

    optimizer.zero_grad()
    outputs = model(inputs)
    loss = criterion(outputs, targets)
    loss.backward()

    # Backbone parameters must have NO gradients
    for name, param in model.named_parameters():
        if not name.startswith("head."):
            assert param.grad is None, f"Backbone parameter {name} received unwanted gradient!"

    # Head parameters must have gradients
    assert model.head[1].weight.grad is not None
    assert model.head[1].weight.grad.norm().item() > 0.0
    assert model.head[1].bias.grad is not None

    optimizer.step()

    # Head weights must have updated
    assert not torch.equal(model.head[1].weight, head_weight_before), "Head weight did not update!"
    assert not torch.equal(model.head[1].bias, head_bias_before), "Head bias did not update!"


# -----------------------------------------------------------------------------
# C. Checkpoint path resolution
# -----------------------------------------------------------------------------
def test_checkpoint_path_resolution():
    # settings.model_dir must be an absolute path ending in ai-ml/models
    assert settings.model_dir.is_absolute()
    assert settings.model_dir.name == "models"
    assert settings.model_dir.exists()

    # Verify that a checkpoint located in settings.model_dir resolves cleanly
    reset_model()
    settings.classifier_checkpoint = "cifake-10-epoch.pt"
    m = load_model()
    assert m is not None
    assert is_model_trained()


# -----------------------------------------------------------------------------
# D. Missing or incompatible checkpoints cause explicit initialization failure
# -----------------------------------------------------------------------------
def test_missing_checkpoint_raises_filenotfound():
    settings.classifier_checkpoint = "non_existent_model_checkpoint_12345.pt"
    reset_model()
    with pytest.raises(FileNotFoundError) as exc_info:
        load_model()
    assert "not found" in str(exc_info.value)


def test_incompatible_backbone_raises_runtime_error(tmp_path):
    bad_ckpt = tmp_path / "mismatched_backbone.pt"
    torch.save({
        "backbone": "resnet50",
        "model_state_dict": {},
    }, str(bad_ckpt))

    settings.classifier_checkpoint = str(bad_ckpt)
    reset_model()
    with pytest.raises(RuntimeError) as exc_info:
        load_model()
    assert "Architecture mismatch" in str(exc_info.value)


def test_missing_head_weights_raises_runtime_error(tmp_path):
    bad_ckpt = tmp_path / "missing_head.pt"
    torch.save({
        "backbone": "efficientnet_b0",
        "model_state_dict": {"conv_stem.weight": torch.randn(32, 3, 3, 3)},
    }, str(bad_ckpt))

    settings.classifier_checkpoint = str(bad_ckpt)
    reset_model()
    with pytest.raises(RuntimeError) as exc_info:
        load_model()
    assert "missing classification head weights" in str(exc_info.value)


def test_untrained_model_raises_on_predict_synthetic():
    settings.classifier_checkpoint = ""
    settings.require_checkpoint = False
    reset_model()

    model = load_model()
    assert model is not None
    assert not is_model_trained()

    dummy_tensor = torch.zeros(1, 3, 224, 224)
    with pytest.raises(RuntimeError) as exc_info:
        predict_synthetic(dummy_tensor)
    assert "not initialized with trained weights" in str(exc_info.value)


# -----------------------------------------------------------------------------
# E. Corrected label mapping is consistent across training and inference
# -----------------------------------------------------------------------------
def test_label_mapping_consistency():
    # Dataset discovery canonical names
    assert ImageFolderAuthenticityDataset.AUTHENTIC_NAMES == {"authentic", "real", "0", "pristine", "nature"}
    assert ImageFolderAuthenticityDataset.SYNTHETIC_NAMES == {"synthetic", "fake", "1", "ai_generated", "diffusion", "ai"}

    # Smoke train label mapping
    import smoke_train_cifake
    import inspect
    src = inspect.getsource(smoke_train_cifake.collect_samples)
    assert '"REAL": 0.0' in src
    assert '"FAKE": 1.0' in src


# -----------------------------------------------------------------------------
# F. Failed inference does not produce fabricated ai_prob=0.0
# -----------------------------------------------------------------------------
def test_failed_inference_raises_explicit_exception():
    # Corrupt/empty payload must raise ValueError, not return ai_prob=0.0
    with pytest.raises(ValueError):
        analyze_image_bytes(b"", filename="empty.jpg")

    with pytest.raises(ValueError):
        analyze_image_bytes(b"not_an_image_at_all", filename="bad.jpg")


# -----------------------------------------------------------------------------
# G. FastAPI response fields match Spring Boot FastApiImageAnalysisResponse
# -----------------------------------------------------------------------------
def test_fastapi_response_schema_compatibility():
    expected_fields = {
        "ai_prob",
        "manipulation_prob",
        "noise_variance",
        "fft_anomaly_score",
        "copy_move_detected",
        "splicing_detected",
        "model_name",
        "model_version",
        "ela_heatmap_base64",
        "gradcam_heatmap_base64",
        "evidence",
        "status",
    }
    actual_fields = set(BackendImageAnalysisResponse.model_fields.keys())
    assert expected_fields.issubset(actual_fields), f"Missing fields: {expected_fields - actual_fields}"


# -----------------------------------------------------------------------------
# H. Stabilization: Honest Verdict Categories, Format Preservation & Confidence
# -----------------------------------------------------------------------------
def test_verdict_categories_and_honest_uncertainty():
    from services.image_analysis.service import (
        VERDICT_CATEGORIES,
        classify_authenticity_assessment,
    )

    # 1. JPEG with all clean signals -> Likely Authentic, bounded confidence <= 0.55
    cat, msg, conf = classify_authenticity_assessment(
        ai_prob=0.02,
        manipulation_prob=0.05,
        copy_move_detected=False,
        splicing_detected=False,
        ela_applicable=True,
        ela_manipulation_prob=0.04,
        noise_variance=45.0,
        noise_suspicious=False,
        fft_suspicious=False,
        dimensions=(512, 512),
    )
    assert cat == "Likely Authentic"
    assert cat in VERDICT_CATEGORIES
    assert 0.40 <= conf <= 0.60
    assert "cannot rule out" in msg.lower()

    # 2. Lossless PNG with low AI prob -> MUST be Inconclusive (ELA not applicable)
    cat, msg, conf = classify_authenticity_assessment(
        ai_prob=0.02,
        manipulation_prob=0.0,
        copy_move_detected=False,
        splicing_detected=False,
        ela_applicable=False,
        ela_manipulation_prob=0.0,
        noise_variance=45.0,
        noise_suspicious=False,
        fft_suspicious=False,
        dimensions=(512, 512),
    )
    assert cat == "Inconclusive"
    assert conf <= 0.35
    assert "lossless" in msg.lower()

    # 3. High AI signal -> Potentially AI-Generated
    cat, _msg, conf = classify_authenticity_assessment(
        ai_prob=0.82,
        manipulation_prob=0.05,
        copy_move_detected=False,
        splicing_detected=False,
        ela_applicable=True,
        ela_manipulation_prob=0.05,
        noise_variance=20.0,
        dimensions=(512, 512),
    )
    assert cat == "Potentially AI-Generated"
    assert conf >= 0.50

    # 4. Verified copy-move -> Potentially Manipulated
    cat, _msg, conf = classify_authenticity_assessment(
        ai_prob=0.04,
        manipulation_prob=0.78,
        copy_move_detected=True,
        splicing_detected=False,
        ela_applicable=True,
        ela_manipulation_prob=0.10,
        noise_variance=30.0,
        dimensions=(512, 512),
    )
    assert cat == "Potentially Manipulated"
    assert conf >= 0.55

    # 5. Conflicting strong AI + Copy-Move -> Inconclusive
    cat, _msg, conf = classify_authenticity_assessment(
        ai_prob=0.85,
        manipulation_prob=0.80,
        copy_move_detected=True,
        splicing_detected=False,
        ela_applicable=True,
        noise_variance=30.0,
        dimensions=(512, 512),
    )
    assert cat == "Inconclusive"
    assert conf <= 0.35

    # 6. Tiny or zero-texture image -> Inconclusive
    cat, _msg, conf = classify_authenticity_assessment(
        ai_prob=0.01,
        manipulation_prob=0.0,
        copy_move_detected=False,
        splicing_detected=False,
        ela_applicable=True,
        noise_variance=0.0,
        dimensions=(32, 32),
    )
    assert cat == "Inconclusive"
    assert conf <= 0.25


def test_png_format_preserved_and_ela_bypassed_correctly():
    import io
    from services.image_analysis.ela import analyze_ela
    from utils.image_utils import load_pil_image_from_bytes

    rng = np.random.default_rng(11)
    arr = rng.integers(20, 230, (128, 128, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="PNG")

    loaded = load_pil_image_from_bytes(buf.getvalue())
    assert loaded.format == "PNG"
    ela_res = analyze_ela(loaded)
    assert ela_res.is_applicable is False
    assert ela_res.manipulation_prob == 0.0
    assert "lossless" in ela_res.disclaimer.lower()


def test_fft_and_splicing_heuristic_safety():
    from services.image_analysis.copy_move import detect_copy_move_and_splicing
    from services.image_analysis.noise import generate_fft_spectrum

    solid = Image.new("RGB", (128, 128), (120, 120, 120))
    _spec, fft_metrics = generate_fft_spectrum(solid)
    assert fft_metrics["fft_anomaly_score"] == 0.0
    assert fft_metrics["is_heuristic"] is True

    rng = np.random.default_rng(55)
    noisy = Image.fromarray(rng.integers(0, 255, (128, 128, 3), dtype=np.uint8))
    _spec2, fft_metrics2 = generate_fft_spectrum(noisy)
    assert fft_metrics2["fft_anomaly_score"] < 0.35

    cm_res = detect_copy_move_and_splicing(noisy)
    assert cm_res.evidence.get("splicing_is_heuristic_indicator") is True
