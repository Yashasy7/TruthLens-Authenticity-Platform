"""
TruthLens AI/ML — Module 07: Audio Anti-Spoofing Classifier Training Pipeline
Blueprint: Reproducible training pipeline, dataset discovery, EER (Equal Error Rate) evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from config.settings import settings
from services.audio_analysis.features import compute_mel_spectrogram
from services.audio_analysis.ingestion import load_and_preprocess_audio
from services.audio_analysis.model import AASISTAudioClassifier, format_log_mel_tensor

logger = logging.getLogger(__name__)


@dataclass
class AudioSample:
    """Single audio dataset item with filepath and ground truth binary label."""
    file_path: Path
    label: int  # 0 = authentic / bonafide, 1 = synthetic / spoof


class AudioAuthenticityDataset(Dataset):
    """
    PyTorch Dataset for audio authenticity classification.
    Loads audio, resamples to 16 kHz mono, computes log-Mel spectrogram,
    and returns standardized (1, n_mels, T) tensor with binary label.
    """

    def __init__(
        self,
        samples: List[AudioSample],
        target_sr: int = 16000,
        n_mels: int = 80,
        target_frames: int = 128,
    ) -> None:
        self.samples = samples
        self.target_sr = target_sr
        self.n_mels = n_mels
        self.target_frames = target_frames

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        sample = self.samples[idx]
        waveform, _ = load_and_preprocess_audio(sample.file_path, target_sr=self.target_sr)
        log_mel, _, _, _ = compute_mel_spectrogram(
            waveform,
            sr=self.target_sr,
            n_mels=self.n_mels,
            n_fft=settings.audio_n_fft,
            hop_length=settings.audio_hop_length,
        )
        # Format to (1, n_mels, target_frames)
        tensor = format_log_mel_tensor(log_mel, target_frames=self.target_frames)
        # Squeeze batch dimension to return (1, n_mels, target_frames)
        return tensor.squeeze(0), sample.label

    @classmethod
    def from_directory(
        cls,
        root_dir: Path,
        target_sr: int = 16000,
        n_mels: int = 80,
        target_frames: int = 128,
    ) -> AudioAuthenticityDataset:
        """
        Discover audio files arranged in folder structure:
            root_dir/authentic/ (*.wav, etc.) -> label 0
            root_dir/synthetic/ (*.wav, etc.) -> label 1
        """
        samples: List[AudioSample] = []
        auth_dir = root_dir / "authentic"
        synth_dir = root_dir / "synthetic"

        valid_exts = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}

        if auth_dir.exists():
            for f in auth_dir.iterdir():
                if f.suffix.lower() in valid_exts and f.is_file():
                    samples.append(AudioSample(file_path=f, label=0))

        if synth_dir.exists():
            for f in synth_dir.iterdir():
                if f.suffix.lower() in valid_exts and f.is_file():
                    samples.append(AudioSample(file_path=f, label=1))

        logger.info(
            "Discovered %d audio samples in %s (authentic: %d, synthetic: %d)",
            len(samples),
            root_dir,
            sum(1 for s in samples if s.label == 0),
            sum(1 for s in samples if s.label == 1),
        )
        return cls(samples, target_sr=target_sr, n_mels=n_mels, target_frames=target_frames)


def compute_eer(bonafide_scores: np.ndarray, spoof_scores: np.ndarray) -> Tuple[float, float]:
    """
    Compute Equal Error Rate (EER) and operating threshold where
    False Rejection Rate (FRR) equals False Acceptance Rate (FAR).

    Args:
        bonafide_scores: Predicted spoof probabilities for authentic/bonafide speech.
        spoof_scores: Predicted spoof probabilities for synthetic/spoofed speech.

    Returns:
        Tuple[float, float]: (eer, optimal_threshold)
    """
    if len(bonafide_scores) == 0 or len(spoof_scores) == 0:
        return 0.0, 0.5

    thresholds = np.linspace(0.0, 1.0, 1000)
    frr = np.array([np.mean(bonafide_scores > th) for th in thresholds])
    far = np.array([np.mean(spoof_scores <= th) for th in thresholds])

    abs_diff = np.abs(frr - far)
    idx = int(np.nanargmin(abs_diff))
    eer = float((frr[idx] + far[idx]) / 2.0)
    return round(eer, 4), round(float(thresholds[idx]), 4)


def evaluate_audio_classifier(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device,
) -> Dict[str, float]:
    """
    Evaluate audio classifier on validation set and compute metrics including EER,
    Accuracy, Precision, Recall, and F1.
    """
    model.eval()
    all_labels: List[int] = []
    all_probs: List[float] = []
    all_preds: List[int] = []

    with torch.no_grad():
        for inputs, targets in dataloader:
            inputs = inputs.to(device)
            logits = model(inputs)
            probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
            preds = torch.argmax(logits, dim=-1).cpu().numpy()

            all_labels.extend(targets.numpy().tolist())
            all_probs.extend(probs.tolist())
            all_preds.extend(preds.tolist())

    y_true = np.array(all_labels)
    y_prob = np.array(all_probs)
    y_pred = np.array(all_preds)

    total = len(y_true)
    if total == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "eer": 0.0}

    accuracy = float(np.mean(y_true == y_pred))

    tp = float(np.sum((y_true == 1) & (y_pred == 1)))
    fp = float(np.sum((y_true == 0) & (y_pred == 1)))
    fn = float(np.sum((y_true == 1) & (y_pred == 0)))

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    bonafide_probs = y_prob[y_true == 0]
    spoof_probs = y_prob[y_true == 1]
    eer, eer_th = compute_eer(bonafide_probs, spoof_probs)

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "eer": eer,
        "eer_threshold": eer_th,
    }


def train_audio_classifier(
    train_samples: List[AudioSample],
    val_samples: List[AudioSample],
    output_checkpoint_path: Path,
    epochs: int = 5,
    batch_size: int = 8,
    lr: float = 1e-4,
    model_version: str = "1.0.0",
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """
    Train AASISTAudioClassifier and save reproducible checkpoint with EER and F1 metrics.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_dataset = AudioAuthenticityDataset(train_samples)
    val_dataset = AudioAuthenticityDataset(val_samples)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    model = AASISTAudioClassifier(n_mels=settings.audio_n_mels)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    best_val_f1 = -1.0
    best_metrics: Dict[str, float] = {}

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            logits = model(inputs)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item())

        val_metrics = evaluate_audio_classifier(model, val_loader, device)
        logger.info(
            "Epoch %d/%d — Loss: %.4f | Val F1: %.4f | Val Acc: %.4f | Val EER: %.4f",
            epoch, epochs, running_loss / max(1, len(train_loader)),
            val_metrics["f1"], val_metrics["accuracy"], val_metrics["eer"],
        )

        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            best_metrics = val_metrics

            output_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_payload = {
                "model_name": settings.audio_model_name,
                "model_version": model_version,
                "architecture": "AASISTAudioClassifier",
                "n_mels": settings.audio_n_mels,
                "sample_rate": settings.audio_sample_rate,
                "state_dict": model.state_dict(),
                "metrics": best_metrics,
                "training_config": {
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "lr": lr,
                    "train_samples": len(train_samples),
                    "val_samples": len(val_samples),
                },
            }
            torch.save(checkpoint_payload, output_checkpoint_path)
            logger.info("Saved best checkpoint to %s (Val F1: %.4f, EER: %.4f)", output_checkpoint_path, best_val_f1, best_metrics.get("eer", 0.0))

    return {
        "best_val_f1": best_val_f1,
        "best_metrics": best_metrics,
        "checkpoint_path": str(output_checkpoint_path),
    }
