"""
TruthLens AI/ML — Classifier Training CLI Entrypoint
Usage:
    # Image Authenticity (Module 05)
    python train.py --modality image --data-dir ./data/cifake --epochs 5 --batch-size 16 --output-dir ./models

    # Audio Authenticity (Module 07)
    python train.py --modality audio --data-dir ./data/asvspoof --epochs 5 --batch-size 8 --output-dir ./models
"""

import argparse
import logging
from pathlib import Path
import random
import sys

from services.audio_analysis.trainer import (
    AudioAuthenticityDataset,
    train_audio_classifier,
)
from services.image_analysis.trainer import (
    ImageFolderAuthenticityDataset,
    discover_dataset_splits,
    limit_samples_by_class,
    train_classifier,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.train")


def main() -> None:
    parser = argparse.ArgumentParser(description="TruthLens Multi-Modal Authenticity Model Trainer")
    parser.add_argument("--modality", type=str, choices=["image", "audio"], default="image", help="Target modality: image or audio")
    parser.add_argument("--data-dir", type=Path, required=True, help="Directory containing authentic/ and synthetic/ folders")
    parser.add_argument("--output-dir", type=Path, default=Path("./models"), help="Destination directory for model checkpoints")
    parser.add_argument("--checkpoint-name", type=str, default=None, help="Filename for the saved checkpoint")
    parser.add_argument("--backbone", type=str, default="efficientnet_b0", help="Model backbone architecture (image only)")
    parser.add_argument("--generators", type=str, default=None, help="Comma-separated generator folder names to train on (e.g. 'midjourney,stable_diffusion_v_1_4' or 'all')")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Training batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--val-split", type=float, default=0.2, help="Fraction of data reserved for validation (0.0–1.0)")
    parser.add_argument("--unfreeze-backbone", action="store_true", help="Fine-tune entire backbone instead of head only (image)")
    parser.add_argument("--max-train-samples", type=int, default=None, help="Maximum number of training samples (preserving class balance)")
    parser.add_argument("--max-val-samples", type=int, default=None, help="Maximum number of validation samples (preserving class balance)")
    parser.add_argument("--model-version", type=str, default="1.0.0", help="Semantic version to stamp into the checkpoint")

    args = parser.parse_args()

    if not args.data_dir.exists():
        logger.error("Dataset directory does not exist: %s", args.data_dir)
        sys.exit(1)

    if args.modality == "audio":
        default_ckpt = "aasist_audio_authenticity.pt"
        ckpt_name = args.checkpoint_name or default_ckpt
        output_path = args.output_dir / ckpt_name

        dataset = AudioAuthenticityDataset.from_directory(args.data_dir)
        if len(dataset) < 4:
            logger.error("Audio dataset must contain at least 4 audio files (found %d)", len(dataset))
            sys.exit(1)

        samples = list(dataset.samples)
        random.seed(42)
        random.shuffle(samples)

        val_count = max(1, int(len(samples) * args.val_split))
        train_samples = samples[val_count:]
        val_samples = samples[:val_count]

        logger.info("Audio dataset split: %d train, %d validation", len(train_samples), len(val_samples))

        result = train_audio_classifier(
            train_samples=train_samples,
            val_samples=val_samples,
            output_checkpoint_path=output_path,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            model_version=args.model_version,
        )

        logger.info(
            "Audio training complete. Best Val F1: %.4f | Val EER: %.4f | Checkpoint: %s",
            result["best_val_f1"],
            result["best_metrics"].get("eer", 0.0),
            result["checkpoint_path"],
        )

    else:
        # Default: image modality
        default_ckpt = "efficientnet_b0_authenticity.pt"
        ckpt_name = args.checkpoint_name or default_ckpt
        output_path = args.output_dir / ckpt_name

        generators_list = None
        if args.generators:
            generators_list = [g.strip() for g in args.generators.split(",") if g.strip()]

        try:
            train_samples, val_samples, test_paths = discover_dataset_splits(
                data_dir=args.data_dir,
                generators=generators_list,
                val_split=args.val_split,
            )
        except (ValueError, FileNotFoundError) as exc:
            logger.error("Dataset discovery error: %s", exc)
            sys.exit(1)

        if args.max_train_samples is not None:
            train_samples = limit_samples_by_class(
                train_samples, max_samples=args.max_train_samples
            )
            logger.info("Limited training samples to %d (max_train_samples=%d)", len(train_samples), args.max_train_samples)

        if args.max_val_samples is not None:
            val_samples = limit_samples_by_class(
                val_samples, max_samples=args.max_val_samples
            )
            logger.info("Limited validation samples to %d (max_val_samples=%d)", len(val_samples), args.max_val_samples)

        if len(train_samples) < 4:
            logger.error(
                "Image dataset must contain at least 4 training images (found %d)",
                len(train_samples),
            )
            sys.exit(1)

        if len(val_samples) < 1:
            logger.error(
                "Image dataset must contain at least 1 validation image (found %d)",
                len(val_samples),
            )
            sys.exit(1)

        logger.info(
            "Image dataset ready: %d training samples, %d validation samples",
            len(train_samples),
            len(val_samples),
        )

        if test_paths:
            logger.info(
                "Official test data found (%d directory/directories); kept completely separate: %s",
                len(test_paths),
                [str(p) for p in test_paths],
            )

        result = train_classifier(
            train_samples=train_samples,
            val_samples=val_samples,
            output_checkpoint_path=output_path,
            backbone_name=args.backbone,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            unfreeze_backbone=args.unfreeze_backbone,
            model_version=args.model_version,
            max_train_samples=args.max_train_samples,
            max_val_samples=args.max_val_samples,
        )

        logger.info(
            "Image training complete. Best validation F1: %.4f | "
            "Checkpoint: %s",
            result["best_val_f1"],
            result["checkpoint_path"],
        )
if __name__ == "__main__":
    main()
