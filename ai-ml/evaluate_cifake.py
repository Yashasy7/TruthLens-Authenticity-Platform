"""
Evaluate a trained TruthLens image classifier on the official CIFAKE test set.

REAL = 0
FAKE = 1

This script does not train the model or modify the test images.
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from services.image_analysis.classifier import _build_model
from utils.image_utils import preprocess_for_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("truthlens.evaluate")


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def evaluate(
    test_dir: Path,
    checkpoint_path: Path,
    batch_size: int = 32,
) -> None:
    """Evaluate a checkpoint against the official test directory."""

    if not test_dir.is_dir():
        raise FileNotFoundError(f"Test directory not found: {test_dir}")

    if not checkpoint_path.is_file():
        raise FileNotFoundError(
            f"Checkpoint not found: {checkpoint_path}"
        )

    device = torch.device(
        "mps"
        if hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
        else "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    logger.info("Evaluation device: %s", device)
    logger.info("Checkpoint: %s", checkpoint_path)
    logger.info("Test directory: %s", test_dir)

    samples = []

    for class_name, label in (("REAL", 0), ("FAKE", 1)):
        class_dir = test_dir / class_name

        if not class_dir.is_dir():
            raise FileNotFoundError(
                f"Expected class directory not found: {class_dir}"
            )

        for path in sorted(class_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS:
                samples.append((path, label))

    if not samples:
        raise RuntimeError(f"No supported images found in {test_dir}")

    labels = [label for _, label in samples]
    if len(set(labels)) != 2:
        raise RuntimeError("The test set must contain both REAL and FAKE images.")

    logger.info("Found %d test images", len(samples))

    # Build the same architecture as the inference classifier.
    model = _build_model("efficientnet_b0")

    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=True,
    )

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    else:
        state_dict = checkpoint

    # Do not silently accept missing or unexpected trained parameters.
    model.load_state_dict(state_dict, strict=True)
    model.to(device)
    model.eval()

    y_true = []
    y_prob = []
    skipped = []

    for start in range(0, len(samples), batch_size):
        batch = samples[start : start + batch_size]
        tensors = []
        batch_labels = []
        batch_paths = []

        for path, label in batch:
            try:
                with Image.open(path) as image:
                    image = image.convert("RGB")
                    tensor = preprocess_for_model(image)

                tensors.append(tensor.squeeze(0))
                batch_labels.append(label)
                batch_paths.append(path)

            except (OSError, ValueError, UnidentifiedImageError) as exc:
                skipped.append((path, str(exc)))
                logger.warning("Skipping unreadable image %s: %s", path, exc)

        if not tensors:
            continue

        inputs = torch.stack(tensors).to(device)

        with torch.inference_mode():
            probabilities = model(inputs).reshape(-1).cpu().numpy()

        y_true.extend(batch_labels)
        y_prob.extend(probabilities.tolist())

        if (start // batch_size + 1) % 50 == 0:
            logger.info(
                "Processed %d / %d images",
                min(start + batch_size, len(samples)),
                len(samples),
            )

    if not y_true:
        raise RuntimeError("No test images could be processed.")

    y_true_array = np.asarray(y_true, dtype=np.int64)
    y_prob_array = np.asarray(y_prob, dtype=np.float64)
    y_pred_array = (y_prob_array >= 0.5).astype(np.int64)

    accuracy = accuracy_score(y_true_array, y_pred_array)
    precision = precision_score(
        y_true_array, y_pred_array, zero_division=0
    )
    recall = recall_score(
        y_true_array, y_pred_array, zero_division=0
    )
    f1 = f1_score(y_true_array, y_pred_array, zero_division=0)

    if len(np.unique(y_true_array)) == 2:
        roc_auc = roc_auc_score(y_true_array, y_prob_array)
    else:
        roc_auc = float("nan")

    matrix = confusion_matrix(
        y_true_array,
        y_pred_array,
        labels=[0, 1],
    )

    print("\nOfficial CIFAKE Test Evaluation")
    print("=" * 38)
    print(f"Checkpoint:       {checkpoint_path}")
    print(f"Device:           {device}")
    print(f"Images evaluated: {len(y_true_array)}")
    print(f"Images skipped:   {len(skipped)}")
    print(f"Accuracy:         {accuracy:.4f}")
    print(f"Precision:        {precision:.4f}")
    print(f"Recall:           {recall:.4f}")
    print(f"F1 score:         {f1:.4f}")
    print(f"ROC-AUC:          {roc_auc:.4f}")
    print("\nConfusion matrix (rows=actual, columns=predicted)")
    print("                  Pred REAL  Pred FAKE")
    print(f"Actual REAL       {matrix[0, 0]:9d}  {matrix[0, 1]:9d}")
    print(f"Actual FAKE       {matrix[1, 0]:9d}  {matrix[1, 1]:9d}")

    if skipped:
        print("\nSkipped image examples:")
        for path, error in skipped[:10]:
            print(f"- {path}: {error}")

        if len(skipped) > 10:
            print(f"... and {len(skipped) - 10} more")

    if skipped:
        logger.warning(
            "Evaluation is incomplete because %d images were skipped.",
            len(skipped),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a TruthLens CIFAKE image checkpoint."
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path("./data/cifake/test"),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("./models/cifake-validation-run.pt"),
    )
    parser.add_argument("--batch-size", type=int, default=32)

    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    evaluate(
        test_dir=args.test_dir,
        checkpoint_path=args.checkpoint,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()