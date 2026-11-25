"""
TruthLens AI/ML — Module 07: ASVspoof2019 LA Benchmark Evaluation Script (Ready for Execution)

Dataset: https://huggingface.co/datasets/SpeechAntiSpoofingBenchmarks/ASVspoof2019_LA
Model:   Pretrained AASIST-L (ai-ml/models/aasist_l/AASIST-L.pth)

Protocol:
  - Streams the ASVspoof2019_LA evaluation split without downloading the full 4.39 GB archive.
  - Deterministically selects a balanced 1,000-sample subset (500 bona fide + 500 spoof, seed=42).
  - Evaluates the frozen pretrained AASIST-L checkpoint on CPU (no training / fine-tuning).
  - Outputs Accuracy, Precision, Recall, F1, ROC-AUC, EER, confusion matrix, FPR, FNR,
    per-class metrics, sample manifest, and JSON benchmark report under ai-ml/models/audio_evaluation/.

Note: Prepared for later benchmark execution; requires `datasets` (with streaming audio support)
      and network access at execution time.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
import logging
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal
import soundfile as sf
import torch

_AI_ML_ROOT = Path(__file__).resolve().parent
if str(_AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ML_ROOT))

from services.audio_analysis.model import (  # noqa: E402
    AASIST_L_INPUT_SAMPLES,
    load_audio_classifier,
    pad_or_crop_waveform,
    predict_synthetic_voice_probability,
)
from services.audio_analysis.trainer import compute_eer  # noqa: E402

logger = logging.getLogger("truthlens.audio_eval")

DATASET_ID = "SpeechAntiSpoofingBenchmarks/ASVspoof2019_LA"
DEFAULT_OUTPUT_DIR = _AI_ML_ROOT / "models" / "audio_evaluation"


def compute_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> Optional[float]:
    """Compute exact trapezoidal ROC-AUC from continuous probabilities."""
    positives = y_true == 1
    negatives = y_true == 0
    n_pos = int(np.sum(positives))
    n_neg = int(np.sum(negatives))
    if n_pos == 0 or n_neg == 0:
        return None

    order = np.argsort(-y_score, kind="mergesort")
    y_sorted = y_true[order]
    tps = np.cumsum(y_sorted == 1)
    fps = np.cumsum(y_sorted == 0)

    tpr = np.concatenate([[0.0], tps / n_pos, [1.0]])
    fpr = np.concatenate([[0.0], fps / n_neg, [1.0]])
    auc = float(np.trapz(tpr, fpr))
    return round(auc, 4)


def compute_benchmark_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Compute full binary & per-class audio evaluation metrics."""
    y_pred = (y_prob >= threshold).astype(int)

    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    total = len(y_true)
    accuracy = round((tp + tn) / total, 4) if total > 0 else 0.0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
    fnr = round(fn / (fn + tp), 4) if (fn + tp) > 0 else 0.0

    # Bona fide (class 0) metrics
    bf_prec = round(tn / (tn + fn), 4) if (tn + fn) > 0 else 0.0
    bf_rec = round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0.0
    bf_f1 = round(2 * bf_prec * bf_rec / (bf_prec + bf_rec), 4) if (bf_prec + bf_rec) > 0 else 0.0

    roc_auc = compute_roc_auc(y_true, y_prob)
    bonafide_scores = y_prob[y_true == 0]
    spoof_scores = y_prob[y_true == 1]
    eer, eer_threshold = compute_eer(bonafide_scores, spoof_scores)

    return {
        "threshold": threshold,
        "total_samples": total,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "roc_auc": roc_auc,
        "eer": eer,
        "eer_threshold": eer_threshold,
        "fpr": fpr,
        "fnr": fnr,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "per_class": {
            "bonafide_0": {
                "support": int(np.sum(y_true == 0)),
                "precision": bf_prec,
                "recall": bf_rec,
                "f1_score": bf_f1,
                "mean_spoof_prob": round(float(np.mean(bonafide_scores)), 4) if len(bonafide_scores) else None,
            },
            "spoof_1": {
                "support": int(np.sum(y_true == 1)),
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "mean_spoof_prob": round(float(np.mean(spoof_scores)), 4) if len(spoof_scores) else None,
            },
        },
    }


def _extract_waveform_from_record(record: Dict[str, Any], target_sr: int = 16000) -> np.ndarray:
    """Decode streamed HuggingFace audio record into mono 16 kHz float32 waveform."""
    audio_field = record.get("audio") or record.get("flac") or record.get("wav")
    if isinstance(audio_field, dict) and "array" in audio_field:
        arr = np.asarray(audio_field["array"], dtype=np.float32)
        sr = int(audio_field.get("sampling_rate", target_sr))
    elif isinstance(audio_field, dict) and "bytes" in audio_field and audio_field["bytes"]:
        arr, sr = sf.read(io.BytesIO(audio_field["bytes"]), dtype="float32", always_2d=False)
    else:
        raise ValueError(f"Unsupported streamed audio payload structure: {list(record.keys())}")

    if arr.ndim == 2:
        arr = np.mean(arr, axis=1)
    arr = np.asarray(arr, dtype=np.float32)
    if sr != target_sr and len(arr) > 0:
        num_samples = max(1, int(round(len(arr) * target_sr / sr)))
        arr = signal.resample(arr, num_samples).astype(np.float32)
    return np.clip(arr, -1.0, 1.0)


def _normalize_label(raw_label: Any) -> int:
    """Map dataset label to 0=bonafide, 1=spoof."""
    if isinstance(raw_label, str):
        val = raw_label.strip().lower()
        if val in ("bonafide", "bona_fide", "real", "authentic", "0"):
            return 0
        if val in ("spoof", "fake", "synthetic", "1"):
            return 1
    if isinstance(raw_label, (int, np.integer)):
        return 0 if int(raw_label) == 0 else 1
    raise ValueError(f"Unrecognized ASVspoof label: {raw_label!r}")


def select_streamed_samples(
    n_bonafide: int = 500,
    n_spoof: int = 500,
    seed: int = 42,
    split: str = "eval",
    scan_limit: int = 20000,
) -> List[Dict[str, Any]]:
    """
    Stream ASVspoof2019_LA and perform deterministic reservoir sampling of
    n_bonafide + n_spoof samples without downloading the full dataset archive.
    """
    try:
        from datasets import load_dataset  # imported lazily so runtime stays lightweight
    except ImportError as exc:
        raise RuntimeError(
            "HuggingFace `datasets` package is required for streaming evaluation. "
            "Install `datasets` before running evaluate_audio.py."
        ) from exc

    rng = random.Random(seed)
    bonafide_reservoir: List[Dict[str, Any]] = []
    spoof_reservoir: List[Dict[str, Any]] = []
    bf_seen = 0
    sp_seen = 0

    stream = load_dataset(DATASET_ID, split=split, streaming=True)
    for idx, row in enumerate(stream):
        if idx >= scan_limit and len(bonafide_reservoir) >= n_bonafide and len(spoof_reservoir) >= n_spoof:
            break

        raw_lbl = row.get("label") if "label" in row else row.get("key")
        lbl = _normalize_label(raw_lbl)
        utt_id = str(row.get("utt_id") or row.get("id") or row.get("speaker_id") or f"row_{idx}")
        waveform = _extract_waveform_from_record(row, target_sr=16000)
        entry = {
            "row_index": idx,
            "utt_id": utt_id,
            "label": lbl,
            "attack_id": str(row.get("attack_id") or row.get("system_id") or ("bonafide" if lbl == 0 else "unknown")),
            "waveform": waveform,
        }

        if lbl == 0:
            bf_seen += 1
            if len(bonafide_reservoir) < n_bonafide:
                bonafide_reservoir.append(entry)
            else:
                j = rng.randint(0, bf_seen - 1)
                if j < n_bonafide:
                    bonafide_reservoir[j] = entry
        else:
            sp_seen += 1
            if len(spoof_reservoir) < n_spoof:
                spoof_reservoir.append(entry)
            else:
                j = rng.randint(0, sp_seen - 1)
                if j < n_spoof:
                    spoof_reservoir[j] = entry

    combined = bonafide_reservoir + spoof_reservoir
    rng.shuffle(combined)
    return combined


def run_benchmark(
    n_bonafide: int = 500,
    n_spoof: int = 500,
    seed: int = 42,
    split: str = "eval",
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    """Execute reproducible benchmark evaluation and persist manifest + report."""
    model, metadata = load_audio_classifier(require_checkpoint=True, device=torch.device("cpu"))
    if model is None or not metadata.get("checkpoint_loaded"):
        raise RuntimeError("Pretrained AASIST-L checkpoint must be loaded before evaluation.")

    samples = select_streamed_samples(
        n_bonafide=n_bonafide,
        n_spoof=n_spoof,
        seed=seed,
        split=split,
    )

    y_true: List[int] = []
    y_prob: List[float] = []
    manifest_rows: List[Dict[str, Any]] = []
    t_start = time.monotonic()

    for s in samples:
        framed = pad_or_crop_waveform(s["waveform"], AASIST_L_INPUT_SAMPLES)
        prob = predict_synthetic_voice_probability(framed, model=model)
        y_true.append(s["label"])
        y_prob.append(prob)
        manifest_rows.append(
            {
                "row_index": s["row_index"],
                "utt_id": s["utt_id"],
                "label": s["label"],
                "attack_id": s["attack_id"],
                "spoof_prob": round(prob, 6),
            }
        )

    elapsed_sec = round(time.monotonic() - t_start, 2)
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=np.float64)

    metrics_05 = compute_benchmark_metrics(y_true_arr, y_prob_arr, threshold=0.50)
    eer_thresh = metrics_05["eer_threshold"]
    metrics_eer = compute_benchmark_metrics(y_true_arr, y_prob_arr, threshold=eer_thresh)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "asvspoof2019_la_sample_manifest.json"
    report_path = output_dir / "asvspoof2019_la_evaluation_report.json"

    manifest_path.write_text(
        json.dumps(
            {
                "dataset": DATASET_ID,
                "split": split,
                "seed": seed,
                "counts": {"bonafide": int(np.sum(y_true_arr == 0)), "spoof": int(np.sum(y_true_arr == 1))},
                "samples": manifest_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report = {
        "benchmark_label": "ASVspoof2019_LA_eval_subset_1000",
        "dataset": DATASET_ID,
        "split": split,
        "seed": seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": {
            "name": metadata["model_name"],
            "version": metadata["model_version"],
            "architecture": metadata["architecture"],
            "checkpoint": metadata["checkpoint_path"],
            "parameter_count": metadata["parameter_count"],
        },
        "runtime": {
            "device": "cpu",
            "total_inference_seconds": elapsed_sec,
            "avg_ms_per_sample": round((elapsed_sec * 1000.0) / max(1, len(samples)), 2),
        },
        "metrics_threshold_0_50": metrics_05,
        "metrics_eer_threshold": metrics_eer,
        "scope_note": (
            "Benchmark evaluated strictly on ASVspoof2019 Logical Access evaluation subset; "
            "results do not imply universal detection on unseen commercial voice cloning models."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate pretrained AASIST-L on ASVspoof2019_LA subset")
    parser.add_argument("--bonafide", type=int, default=500)
    parser.add_argument("--spoof", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--split", type=str, default="eval")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    report = run_benchmark(
        n_bonafide=args.bonafide,
        n_spoof=args.spoof,
        seed=args.seed,
        split=args.split,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
