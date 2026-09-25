import numpy as np
import pytest
from app.utils.image_io import load_image_from_bytes, to_torch_tensor
from app.services.ela_generator import ElaGenerator
from app.services.noise_analyzer import NoiseAnalyzer
from app.services.frequency_analyzer import FrequencyAnalyzer
from app.services.local_manipulation import LocalManipulationDetector
from app.services.model_inference import ModelInferenceService


def test_image_io_valid_jpeg(sample_jpeg_bytes):
    img = load_image_from_bytes(sample_jpeg_bytes)
    assert isinstance(img, np.ndarray)
    assert img.shape == (256, 256, 3)
    assert img.dtype == np.uint8

    tensor = to_torch_tensor(img, (224, 224))
    assert tensor.shape == (1, 3, 224, 224)


def test_image_io_corrupt_stream(corrupt_bytes):
    with pytest.raises(ValueError, match="Corrupt or unreadable"):
        load_image_from_bytes(corrupt_bytes)


def test_image_io_empty_payload():
    with pytest.raises(ValueError, match="empty"):
        load_image_from_bytes(b"")


def test_ela_generator(sample_jpeg_bytes):
    img = load_image_from_bytes(sample_jpeg_bytes)
    ela = ElaGenerator(quality=90, scale=15)
    heatmap, b64_str, stats = ela.generate_ela(img)

    assert isinstance(heatmap, np.ndarray)
    assert heatmap.shape == (256, 256, 3)
    assert len(b64_str) > 0
    assert "ela_mean_error" in stats
    assert stats["recompression_quality"] == 90
    assert stats["amplification_scale"] == 15


def test_noise_analyzer(sample_jpeg_bytes):
    img = load_image_from_bytes(sample_jpeg_bytes)
    analyzer = NoiseAnalyzer(patch_size=32)
    stats = analyzer.analyze_noise(img)

    assert "noise_variance" in stats
    assert stats["noise_variance"] >= 0.0
    assert 0.0 <= stats["noise_inconsistency_score"] <= 1.0
    assert stats["patch_count"] > 0


def test_frequency_analyzer(sample_jpeg_bytes):
    img = load_image_from_bytes(sample_jpeg_bytes)
    analyzer = FrequencyAnalyzer()
    stats = analyzer.analyze_frequency(img)

    assert "fft_anomaly_score" in stats
    assert 0.0 <= stats["fft_anomaly_score"] <= 1.0
    assert "high_frequency_energy_ratio" in stats
    assert "spectral_peak_count" in stats


def test_local_manipulation_detector(sample_jpeg_bytes, sample_cloned_image_bytes):
    detector = LocalManipulationDetector(min_match_distance=20.0, min_cluster_size=5)

    # Test clean image
    img_clean = load_image_from_bytes(sample_jpeg_bytes)
    res_clean = detector.detect_manipulation(img_clean, noise_inconsistency=0.1, ela_max_error=10.0)
    assert 0.0 <= res_clean["manipulation_prob"] <= 1.0

    # Test cloned pattern image
    img_cloned = load_image_from_bytes(sample_cloned_image_bytes)
    res_cloned = detector.detect_manipulation(img_cloned, noise_inconsistency=0.2, ela_max_error=15.0)
    assert 0.0 <= res_cloned["manipulation_prob"] <= 1.0
    assert "detected_keypoints" in res_cloned


def test_model_inference_and_gradcam(sample_jpeg_bytes):
    service = ModelInferenceService()
    img = load_image_from_bytes(sample_jpeg_bytes)
    tensor = to_torch_tensor(img)

    ai_prob, gradcam_b64 = service.predict_and_explain(tensor, img)

    assert 0.0 <= ai_prob <= 1.0
    assert len(gradcam_b64) > 0  # Valid base64 PNG heatmap generated
    assert service.model_name == "TruthLens-DiffusionClassifier"
    assert "0.1.0-dev" in service.model_version
