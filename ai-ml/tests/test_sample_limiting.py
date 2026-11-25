"""
TruthLens AI/ML — Unit Tests for Dataset Sample Limiting and Class Balance
Tests verification of optional sample limits for CPU training benchmarks.
"""

from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from services.image_analysis.trainer import limit_samples_by_class, train_classifier


def _make_dummy_samples(n_real: int, n_fake: int):
    samples = []
    for i in range(n_real):
        samples.append((Path(f"/data/real/{i:05d}.jpg"), 0.0))
    for i in range(n_fake):
        samples.append((Path(f"/data/fake/{i:05d}.jpg"), 1.0))
    return samples


def test_limit_samples_none_or_large_returns_original():
    samples = _make_dummy_samples(20, 20)
    assert len(limit_samples_by_class(samples, max_samples=None)) == 40
    assert len(limit_samples_by_class(samples, max_samples=40)) == 40
    assert len(limit_samples_by_class(samples, max_samples=100)) == 40


def test_limit_samples_zero_or_negative():
    samples = _make_dummy_samples(10, 10)
    assert limit_samples_by_class(samples, max_samples=0) == []
    assert limit_samples_by_class(samples, max_samples=-5) == []


def test_limit_samples_preserves_equal_class_balance():
    samples = _make_dummy_samples(50, 50)

    # Even sample limit
    limited_even = limit_samples_by_class(samples, max_samples=20, seed=42)
    assert len(limited_even) == 20
    reals_even = sum(1 for _, label in limited_even if label == 0.0)
    fakes_even = sum(1 for _, label in limited_even if label == 1.0)
    assert reals_even == 10
    assert fakes_even == 10

    # Odd sample limit (difference must be <= 1)
    limited_odd = limit_samples_by_class(samples, max_samples=21, seed=42)
    assert len(limited_odd) == 21
    reals_odd = sum(1 for _, label in limited_odd if label == 0.0)
    fakes_odd = sum(1 for _, label in limited_odd if label == 1.0)
    assert abs(reals_odd - fakes_odd) == 1
    assert reals_odd + fakes_odd == 21


def test_limit_samples_imbalanced_dataset():
    # 10 real, 90 fake
    samples = _make_dummy_samples(10, 90)

    limited = limit_samples_by_class(samples, max_samples=30, seed=42)
    assert len(limited) == 30
    reals = sum(1 for _, label in limited if label == 0.0)
    fakes = sum(1 for _, label in limited if label == 1.0)
    # Since real has only 10 samples, it should exhaust all 10 reals and take 20 fakes
    assert reals == 10
    assert fakes == 20


def test_limit_samples_reproducibility():
    samples = _make_dummy_samples(100, 100)
    run1 = limit_samples_by_class(samples, max_samples=30, seed=42)
    run2 = limit_samples_by_class(samples, max_samples=30, seed=42)
    assert run1 == run2

    # Different seed should typically produce a different order/selection
    run3 = limit_samples_by_class(samples, max_samples=30, seed=99)
    assert run1 != run3


def test_cli_argument_parsing():
    import argparse
    from train import main

    # Inspect ArgumentParser configuration by invoking train.py with simulated arguments
    with patch("sys.argv", [
        "train.py",
        "--data-dir", "datasets/DeepFakeDetection",
        "--max-train-samples", "1000",
        "--max-val-samples", "200",
    ]):
        with patch("train.discover_dataset_splits") as mock_discover, \
             patch("train.train_classifier") as mock_train:

            mock_discover.return_value = (
                _make_dummy_samples(50, 50),
                _make_dummy_samples(10, 10),
                [],
            )
            mock_train.return_value = {
                "best_val_f1": 0.95,
                "checkpoint_path": "models/test.pt",
            }

            main()

            mock_train.assert_called_once()
            _, kwargs = mock_train.call_args
            assert kwargs["max_train_samples"] == 1000
            assert kwargs["max_val_samples"] == 200
            assert len(kwargs["train_samples"]) == 100  # since 100 < 1000, all preserved
            assert len(kwargs["val_samples"]) == 20     # since 20 < 200, all preserved
