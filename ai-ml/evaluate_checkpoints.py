from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from config.settings import settings
from services.image_analysis.classifier import _build_model
from services.image_analysis.trainer import (
    ImageFolderAuthenticityDataset,
    compute_metrics,
    get_transforms,
)


DATA_DIR = Path("./data/cifake/test")

CHECKPOINTS = [
    Path("./models/cifake-validation-run.pt"),
    Path("./models/cifake-10-epoch.pt"),
]

BATCH_SIZE = 32
DEVICE = torch.device(
    "mps"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    else "cpu"
)


def evaluate_checkpoint(checkpoint_path, loader):
    checkpoint = torch.load(
        str(checkpoint_path),
        map_location=DEVICE,
    )

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
        version = checkpoint.get("model_version", "unknown")
        saved_epoch = checkpoint.get("epoch", "unknown")
    else:
        state_dict = checkpoint
        version = "unknown"
        saved_epoch = "unknown"

    backbone = (
        checkpoint.get("backbone", settings.classifier_backbone)
        if isinstance(checkpoint, dict)
        else settings.classifier_backbone
    )

    model = _build_model(backbone)
    model.load_state_dict(state_dict, strict=False)
    model.to(DEVICE)
    model.eval()

    all_targets = []
    all_probs = []

    with torch.inference_mode():
        for images, targets in loader:
            probabilities = model(images.to(DEVICE)).squeeze(-1)

            all_probs.extend(probabilities.cpu().numpy().tolist())
            all_targets.extend(targets.squeeze(-1).numpy().tolist())

    y_true = np.asarray(all_targets, dtype=np.float32)
    y_prob = np.asarray(all_probs, dtype=np.float32)

    metrics = compute_metrics(y_true, y_prob)

    # Rows: actual REAL, actual FAKE.
    # Columns: predicted REAL, predicted FAKE.
    y_pred = (y_prob >= 0.5).astype(np.float32)

    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))

    print(f"\nCheckpoint: {checkpoint_path}")
    print(f"Version: {version} | Saved epoch: {saved_epoch}")
    print(f"Backbone: {backbone}")
    print(f"Test images evaluated: {len(y_true)}")
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1-score:  {metrics['f1']:.4f}")
    print(f"ROC-AUC:   {metrics['roc_auc']:.4f}")
    print("\nConfusion matrix:")
    print("                 Pred REAL  Pred FAKE")
    print(f"Actual REAL      {tn:9d}  {fp:9d}")
    print(f"Actual FAKE      {fn:9d}  {tp:9d}")

    del model


def main():
    if not DATA_DIR.is_dir():
        raise FileNotFoundError(f"Test directory not found: {DATA_DIR}")

    for checkpoint_path in CHECKPOINTS:
        if not checkpoint_path.is_file():
            raise FileNotFoundError(
                f"Checkpoint not found: {checkpoint_path}"
            )

    _, test_transform = get_transforms(input_size=224)

    dataset = ImageFolderAuthenticityDataset.from_directory(
        DATA_DIR,
        transform=test_transform,
    )

    if len(dataset) == 0:
        raise RuntimeError(f"No supported test images found in {DATA_DIR}")

    labels = [label for _, label in dataset.samples]
    real_count = sum(label == 0.0 for label in labels)
    fake_count = sum(label == 1.0 for label in labels)

    print(f"Device: {DEVICE}")
    print(f"Test images: {len(dataset)}")
    print(f"REAL: {real_count} | FAKE: {fake_count}")

    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    for checkpoint_path in CHECKPOINTS:
        evaluate_checkpoint(checkpoint_path, loader)


if __name__ == "__main__":
    main()
