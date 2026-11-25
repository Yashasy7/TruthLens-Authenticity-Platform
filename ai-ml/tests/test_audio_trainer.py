"""Tests for Module 07 audio dataset loading, evaluation, and ASVspoof benchmark helpers."""

import wave
from pathlib import Path

import numpy as np
import pytest
import torch
from torch.utils.data import DataLoader

from evaluate_audio import compute_benchmark_metrics, compute_roc_auc
from services.audio_analysis.model import AASIST_L_INPUT_SAMPLES, load_audio_classifier
from services.audio_analysis.trainer import (
    AudioAuthenticityDataset,
    compute_eer,
    evaluate_audio_classifier,
)


def _write_wav(path: Path, freq: float = 220.0, duration_s: float = 0.5, sr: int = 16000) -> None:
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    samples = (0.4 * np.sin(2.0 * np.pi * freq * t) * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())


class TestAudioDatasetAndEvaluation:
    def test_dataset_from_directory_returns_64600_waveforms(self, tmp_path: Path):
        auth_dir = tmp_path / "bonafide"
        synth_dir = tmp_path / "spoof"
        auth_dir.mkdir()
        synth_dir.mkdir()
        _write_wav(auth_dir / "r1.wav", freq=180.0)
        _write_wav(synth_dir / "f1.wav", freq=440.0)

        dataset = AudioAuthenticityDataset.from_directory(tmp_path)
        assert len(dataset) == 2

        labels = set()
        for wf, label in dataset:
            assert isinstance(wf, torch.Tensor)
            assert wf.shape == (AASIST_L_INPUT_SAMPLES,)
            assert wf.dtype == torch.float32
            labels.add(label)
        assert labels == {0, 1}

    def test_evaluate_audio_classifier_runs_on_waveform_dataset(self, tmp_path: Path):
        auth_dir = tmp_path / "authentic"
        synth_dir = tmp_path / "synthetic"
        auth_dir.mkdir()
        synth_dir.mkdir()
        _write_wav(auth_dir / "r1.wav", freq=180.0)
        _write_wav(synth_dir / "f1.wav", freq=440.0)

        dataset = AudioAuthenticityDataset.from_directory(tmp_path)
        dataloader = DataLoader(dataset, batch_size=2, shuffle=False)
        model, meta = load_audio_classifier(require_checkpoint=True)
        assert meta["checkpoint_loaded"] is True

        metrics = evaluate_audio_classifier(model, dataloader, device=torch.device("cpu"))
        for key in ("accuracy", "precision", "recall", "f1", "eer", "eer_threshold"):
            assert key in metrics
            assert 0.0 <= metrics[key] <= 1.0


class TestBenchmarkMetricsHelpers:
    def test_compute_eer_and_roc_auc_perfect_separation(self):
        bonafide_scores = np.array([0.05, 0.10], dtype=np.float64)
        spoof_scores = np.array([0.90, 0.95], dtype=np.float64)
        y_true = np.array([0, 0, 1, 1], dtype=np.int64)
        y_score = np.array([0.05, 0.10, 0.90, 0.95], dtype=np.float64)

        eer, eer_th = compute_eer(bonafide_scores, spoof_scores)
        auc = compute_roc_auc(y_true, y_score)
        metrics = compute_benchmark_metrics(y_true, y_score, threshold=0.5)

        assert eer == pytest.approx(0.0, abs=1e-3)
        assert 0.0 <= eer_th <= 1.0
        assert auc == pytest.approx(1.0, abs=1e-6)
        assert metrics["accuracy"] == pytest.approx(1.0)
        assert metrics["precision"] == pytest.approx(1.0)
        assert metrics["recall"] == pytest.approx(1.0)
        assert metrics["f1_score"] == pytest.approx(1.0)
        assert metrics["confusion_matrix"]["tp"] == 2
        assert metrics["confusion_matrix"]["tn"] == 2
        assert metrics["confusion_matrix"]["fp"] == 0
        assert metrics["confusion_matrix"]["fn"] == 0
