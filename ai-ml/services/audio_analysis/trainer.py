"""
TruthLens AI/ML — Module 07: Audio Anti-Spoofing Dataset & Evaluation Metrics Utilities
Provides dataset discovery, Equal Error Rate (EER), and standard classification metric helpers.
Note: Production audio inference uses the official pretrained AASIST-L checkpoint directly
without fine-tuning or scratch training.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from services.audio_analysis.ingestion import SUPPORTED_AUDIO_EXTENSIONS, load_and_preprocess_audio
from services.audio_analysis.model import AASIST_L_INPUT_SAMPLES, pad_or_crop_waveform

logger = logging.getLogger(__name__)


@dataclass
class AudioSample:
    """Single audio dataset item with filepath and ground truth binary label."""
    file_path: Path
    label: int  # 0 = bonafide / authentic, 1 = spoof / synthetic


class AudioAuthenticityDataset(Dataset):
    """
    PyTorch Dataset yielding deterministic 16 kHz mono waveforms of length 64,600
    for AASIST-L evaluation.
    """

    def __init__(
        self,
        samples: List[AudioSample],
        target_sr: int = 16000,
        target_samples: int = AASIST_L_INPUT_SAMPLES,
    ) -> None:
        self.samples = samples
        self.target_sr = target_sr
        self.target_samples = target_samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        sample = self.samples[idx]
        waveform, _ = load_and_preprocess_audio(sample.file_path, target_sr=self.target_sr)
        framed = pad_or_crop_waveform(waveform, max_len=self.target_samples)
        return torch.from_numpy(framed), sample.label

    @classmethod
    def from_directory(
        cls,
        root_dir: Path,
        target_sr: int = 16000,
        target_samples: int = AASIST_L_INPUT_SAMPLES,
    ) -> AudioAuthenticityDataset:
        """
        Discover audio files arranged in folder structure:
            root_dir/authentic/ (or bonafide/) -> label 0
            root_dir/synthetic/ (or spoof/)    -> label 1
        """
        samples: List[AudioSample] = []
        auth_dirs = [root_dir / "authentic", root_dir / "bonafide"]
        synth_dirs = [root_dir / "synthetic", root_dir / "spoof"]

        for auth_dir in auth_dirs:
            if auth_dir.exists():
                for f in sorted(auth_dir.iterdir()):
                    if f.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and f.is_file():
                        samples.append(AudioSample(file_path=f, label=0))

        for synth_dir in synth_dirs:
            if synth_dir.exists():
                for f in sorted(synth_dir.iterdir()):
                    if f.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and f.is_file():
                        samples.append(AudioSample(file_path=f, label=1))

        logger.info(
            "Discovered %d audio samples in %s (bonafide: %d, spoof: %d)",
            len(samples),
            root_dir,
            sum(1 for s in samples if s.label == 0),
            sum(1 for s in samples if s.label == 1),
        )
        return cls(samples, target_sr=target_sr, target_samples=target_samples)


def compute_eer(bonafide_scores: np.ndarray, spoof_scores: np.ndarray) -> Tuple[float, float]:
    """
    Compute Equal Error Rate (EER) and threshold where FRR equals FAR.

    Args:
        bonafide_scores: Predicted spoof probabilities for authentic/bonafide speech (lower = bonafide).
        spoof_scores: Predicted spoof probabilities for synthetic/spoofed speech (higher = spoof).
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
    model: torch.nn.Module,
    dataloader: DataLoader,
    device: torch.device,
    threshold: float = 0.5,
) -> Dict[str, float]:
    """
    Evaluate AASIST-L on a dataset yielding (waveform [B, L], label) pairs.
    Note: AASIST-L logits index 0 = spoof, index 1 = bonafide.
    """
    model.eval()
    all_labels: List[int] = []
    all_spoof_probs: List[float] = []

    with torch.inference_mode():
        for inputs, targets in dataloader:
            inputs = inputs.to(device)
            logits = model(inputs)
            probs = torch.softmax(logits, dim=-1)[:, 0].cpu().numpy()
            all_labels.extend(targets.numpy().tolist())
            all_spoof_probs.extend(probs.tolist())

    y_true = np.array(all_labels)
    y_prob = np.array(all_spoof_probs)
    if len(y_true) == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "eer": 0.0}

    y_pred = (y_prob >= threshold).astype(int)
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
