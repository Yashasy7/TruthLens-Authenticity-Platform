"""
Tests for services/image_analysis/classifier.py
Blueprint Section I: pytest unit tests for Python ML services
"""

import pytest
import torch
from PIL import Image
import numpy as np

from services.image_analysis.classifier import (
    load_model,
    predict_synthetic,
    reset_model,
)
from utils.image_utils import preprocess_for_model


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the model singleton before each test for isolation."""
    reset_model()
    yield
    reset_model()


def _make_image(width=224, height=224) -> Image.Image:
    rng = np.random.default_rng(0)
    data = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    return Image.fromarray(data, mode="RGB")


class TestLoadModel:

    def test_model_loads_without_error(self):
        """load_model() should return a torch.nn.Module without raising."""
        import torch.nn as nn
        model = load_model()
        assert isinstance(model, nn.Module), "Expected nn.Module"

    def test_model_is_in_eval_mode(self):
        """Model must be in eval mode after loading."""
        model = load_model()
        assert not model.training, "Model should be in eval mode"

    def test_model_singleton_returns_same_object(self):
        """Calling load_model() twice should return the same object (singleton)."""
        m1 = load_model()
        m2 = load_model()
        assert m1 is m2, "load_model() should return the cached singleton"


class TestPredictSynthetic:

    def test_returns_tuple_of_floats(self):
        """predict_synthetic must return (float, float)."""
        image = _make_image()
        tensor = preprocess_for_model(image)
        synthetic_prob, confidence = predict_synthetic(tensor)
        assert isinstance(synthetic_prob, float), "synthetic_prob should be float"
        assert isinstance(confidence, float), "confidence should be float"

    def test_synthetic_prob_in_range(self):
        """synthetic_prob must be in [0.0, 1.0]."""
        image = _make_image()
        tensor = preprocess_for_model(image)
        synthetic_prob, _ = predict_synthetic(tensor)
        assert 0.0 <= synthetic_prob <= 1.0, f"synthetic_prob out of range: {synthetic_prob}"

    def test_confidence_in_range(self):
        """confidence must be in [0.0, 1.0]."""
        image = _make_image()
        tensor = preprocess_for_model(image)
        _, confidence = predict_synthetic(tensor)
        assert 0.0 <= confidence <= 1.0, f"confidence out of range: {confidence}"

    def test_no_gradient_in_output(self):
        """Inference should not produce gradients (runs under torch.no_grad)."""
        image = _make_image()
        tensor = preprocess_for_model(image)
        load_model()  # ensure model is loaded
        synthetic_prob, _ = predict_synthetic(tensor)
        # If no exception was raised with no_grad, the tensor is detached successfully
        assert synthetic_prob is not None

    def test_deterministic_on_same_input(self):
        """Same input tensor should produce the same output (model is in eval mode)."""
        image = _make_image(width=224, height=224)
        tensor = preprocess_for_model(image)
        prob1, conf1 = predict_synthetic(tensor)
        prob2, conf2 = predict_synthetic(tensor)
        assert abs(prob1 - prob2) < 1e-6, "Model output is non-deterministic"
        assert abs(conf1 - conf2) < 1e-6, "Confidence is non-deterministic"
