"""
TruthLens AI/ML — Module 07 Tests: Audio Classifier Training & EER Evaluation
"""

import io
from pathlib import Path
import numpy as np
import pytest
import scipy.io.wavfile as wavfile
import torch

from services.audio_analysis.model import load_audio_classifier
from services.audio_analysis.trainer import (
    AudioAuthenticityDataset,
    AudioSample,
    compute_eer,
    train_audio_classifier,
)


def _write_wav(path: Path, freq: float = 440.0, duration: float = 0.5, sr: int = 16000) -> None:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    data = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    wavfile.write(str(path), sr, data)


class TestAudioTrainer:
    """Audio training pipeline and EER evaluation tests."""

    def test_compute_eer_perfect_separation(self):
        # Authentic: low synthetic probability; Spoof: high synthetic probability
        bonafide = np.array([0.05, 0.10, 0.12, 0.15, 0.20])
        spoof = np.array([0.80, 0.85, 0.90, 0.92, 0.95])
        eer, th = compute_eer(bonafide, spoof)
        assert eer == 0.0
        assert 0.20 <= th <= 0.80

    def test_compute_eer_overlapping_distributions(self):
        bonafide = np.array([0.1, 0.3, 0.5, 0.7])
        spoof = np.array([0.3, 0.5, 0.7, 0.9])
        eer, th = compute_eer(bonafide, spoof)
        assert 0.0 <= eer <= 0.5

    def test_dataset_discovery_from_directory(self, tmp_path):
        auth_dir = tmp_path / "authentic"
        synth_dir = tmp_path / "synthetic"
        auth_dir.mkdir()
        synth_dir.mkdir()

        _write_wav(auth_dir / "auth1.wav", freq=300.0)
        _write_wav(auth_dir / "auth2.wav", freq=350.0)
        _write_wav(synth_dir / "synth1.wav", freq=600.0)
        _write_wav(synth_dir / "synth2.wav", freq=650.0)

        dataset = AudioAuthenticityDataset.from_directory(tmp_path)
        assert len(dataset) == 4
        labels = [s.label for s in dataset.samples]
        assert labels.count(0) == 2
        assert labels.count(1) == 2

        # Check item retrieval
        tensor, label = dataset[0]
        assert tensor.shape[0] == 1  # 1 channel
        assert tensor.shape[1] == 80  # n_mels
        assert tensor.shape[2] == 128  # target_frames
        assert label in (0, 1)

    def test_mini_training_and_checkpoint_saving(self, tmp_path):
        auth_dir = tmp_path / "dataset" / "authentic"
        synth_dir = tmp_path / "dataset" / "synthetic"
        auth_dir.mkdir(parents=True)
        synth_dir.mkdir(parents=True)

        for i in range(4):
            _write_wav(auth_dir / f"auth_{i}.wav", freq=250.0 + i * 20.0)
            _write_wav(synth_dir / f"synth_{i}.wav", freq=700.0 + i * 20.0)

        dataset = AudioAuthenticityDataset.from_directory(tmp_path / "dataset")
        train_samples = dataset.samples[:6]
        val_samples = dataset.samples[6:]

        ckpt_output = tmp_path / "models" / "test_audio_classifier.pt"

        result = train_audio_classifier(
            train_samples=train_samples,
            val_samples=val_samples,
            output_checkpoint_path=ckpt_output,
            epochs=1,
            batch_size=2,
            lr=1e-3,
            model_version="0.1.0-test",
            device=torch.device("cpu"),
        )

        assert ckpt_output.exists()
        assert "best_val_f1" in result
        assert "eer" in result["best_metrics"]

        # Validate that the saved checkpoint can be loaded into AASISTAudioClassifier
        loaded_model, metadata = load_audio_classifier(
            checkpoint_path=str(ckpt_output),
            require_checkpoint=True,
            device=torch.device("cpu"),
        )
        assert metadata["checkpoint_loaded"] is True
        assert metadata["model_version"] == "0.1.0-test"
