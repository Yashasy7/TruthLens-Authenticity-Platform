from pathlib import Path
import random

import torch

from services.image_analysis.trainer import train_classifier


DATA_DIR = Path("data/cifake/train")
OUTPUT_PATH = Path("models/cifake-smoke-test.pt")

SAMPLES_PER_CLASS = 32
EPOCHS = 1
BATCH_SIZE = 8
SEED = 42


def collect_samples():
    """Collect a small, balanced sample from the training dataset."""
    rng = random.Random(SEED)

    # Confirm these label values match the existing dataset implementation.
    label_map = {
        "FAKE": 0.0,
        "REAL": 1.0,
    }

    samples = []

    for class_name, label in label_map.items():
        class_dir = DATA_DIR / class_name

        if not class_dir.is_dir():
            raise FileNotFoundError(
                f"Missing CIFAKE class directory: {class_dir}"
            )

        image_paths = [
            path
            for path in class_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in {
                ".jpg", ".jpeg", ".png", ".bmp", ".webp"
            }
        ]

        if len(image_paths) < SAMPLES_PER_CLASS:
            raise RuntimeError(
                f"Expected at least {SAMPLES_PER_CLASS} images in "
                f"{class_dir}; found {len(image_paths)}"
            )

        selected = rng.sample(image_paths, SAMPLES_PER_CLASS)

        samples.extend(
            (path, label)
            for path in selected
        )

    rng.shuffle(samples)

    # Keep the validation subset separate from the training subset.
    split_index = int(len(samples) * 0.75)

    train_samples = samples[:split_index]
    val_samples = samples[split_index:]

    return train_samples, val_samples


def main():
    train_samples, val_samples = collect_samples()

    if not train_samples or not val_samples:
        raise RuntimeError("Training and validation samples must not be empty.")

    if {label for _, label in train_samples} != {0.0, 1.0}:
        raise RuntimeError("Training subset must contain both classes.")

    if {label for _, label in val_samples} != {0.0, 1.0}:
        raise RuntimeError("Validation subset must contain both classes.")

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    print(f"Device: {device}")
    print(f"Training images: {len(train_samples)}")
    print(f"Validation images: {len(val_samples)}")
    print(f"Checkpoint: {OUTPUT_PATH}")

    result = train_classifier(
        train_samples=train_samples,
        val_samples=val_samples,
        output_checkpoint_path=OUTPUT_PATH,
        backbone_name="efficientnet_b0",
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        lr=1e-4,
        unfreeze_backbone=False,
        device=device,
        model_version="smoke-test",
    )

    checkpoint_path = Path(result["checkpoint_path"])

    if not checkpoint_path.is_file():
        raise RuntimeError("Training finished without saving a checkpoint.")

    if checkpoint_path.stat().st_size == 0:
        raise RuntimeError("The saved checkpoint is empty.")

    print("\nSmoke test completed.", flush=True)
    print(f"Best validation F1: {result['best_val_f1']}", flush=True)

    print("\nValidation metrics by epoch:")
    for metrics in result["history"]:
        print(
            f"Epoch {metrics['epoch']}: "
            f"accuracy={metrics['accuracy']:.4f}, "
            f"precision={metrics['precision']:.4f}, "
            f"recall={metrics['recall']:.4f}, "
            f"f1={metrics['f1']:.4f}, "
            f"roc_auc={metrics['roc_auc']:.4f}, "
            f"train_loss={metrics['train_loss']:.4f}, "
            f"val_loss={metrics['val_loss']:.4f}"
        )

    print(f"\nCheckpoint: {checkpoint_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()