"""Unit tests for Stage 1 human-face 3-class evaluation, manifest integrity, and Colab notebook contract."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from collections import Counter, defaultdict
import logging
import sys
import tarfile
import zipfile

import numpy as np
from PIL import Image
import pytest
import timm
import torch
import torch.nn as nn
from torch.utils.data import Dataset

AI_ML_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ML_ROOT))

import evaluate_human_face as ehf  # noqa: E402
import human_face_dataset as hfd  # noqa: E402


def _write_rgb(path: Path, val: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (64, 64), color=(val, (val + 50) % 256, (val + 100) % 256))
    img.save(path, format="PNG")


class TestManifestIntegrityAndMetrics:
    """Verify leakage checks, 3-class metrics, and generator breakdown logic."""

    def test_multiclass_metrics_and_per_generator_breakdown(self) -> None:
        # 6 samples: 2 genuine (0), 2 ai_generated (1), 2 manipulated (2)
        y_true = [0, 0, 1, 1, 2, 2]
        y_probs = np.array(
            [
                [0.90, 0.05, 0.05],
                [0.80, 0.15, 0.05],
                [0.10, 0.85, 0.05],
                [0.70, 0.20, 0.10],  # False-genuine mistake on ai_generated
                [0.05, 0.15, 0.80],
                [0.10, 0.20, 0.70],
            ],
            dtype=np.float64,
        )
        metrics = ehf.compute_multiclass_metrics(y_true, y_probs)
        assert metrics["total_samples"] == 6
        assert np.isclose(metrics["accuracy"], 5 / 6, atol=1e-5)
        assert metrics["confusion_matrix"] == [
            [2, 0, 0],
            [1, 1, 0],
            [0, 0, 2],
        ]
        # 1 out of 4 non-genuine samples mistakenly classified as genuine -> 0.25
        assert np.isclose(metrics["false_genuine_rate"], 0.25, atol=1e-5)
        assert metrics["macro_ovr_roc_auc"] is not None

        records = [
            {"source_subset": "ffhq"},
            {"source_subset": "ffhq"},
            {"source_subset": "midjourney"},
            {"source_subset": "midjourney"},
            {"source_subset": "celeb_df_v2"},
            {"source_subset": "celeb_df_v2"},
        ]
        breakdown = ehf.compute_per_generator_breakdown(records, y_true, y_probs)
        assert breakdown["ffhq"]["accuracy"] == 1.0
        assert breakdown["midjourney"]["accuracy"] == 0.5
        assert breakdown["midjourney"]["false_genuine_rate"] == 0.5
        assert breakdown["celeb_df_v2"]["accuracy"] == 1.0

    def test_verify_manifest_integrity_detects_cross_split_leak(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "dataset_manifest.json"
        leaked_payload = {
            "schema_version": "1.0.0",
            "class_names": list(hfd.CLASS_NAMES),
            "images": [
                {
                    "image_path": "train/genuine/a.png",
                    "split": "train",
                    "label": 0,
                    "class_name": "genuine",
                    "source_subset": "ffhq",
                    "source_group_id": "ffhq::item::a",
                    "sha256": "samehash123",
                    "md5": "samemd5",
                    "dhash": "0011223344556677",
                },
                {
                    "image_path": "test/genuine/b.png",
                    "split": "test",
                    "label": 0,
                    "class_name": "genuine",
                    "source_subset": "ffhq",
                    "source_group_id": "ffhq::item::b",
                    "sha256": "samehash123",
                    "md5": "samemd5",
                    "dhash": "0011223344556677",
                },
            ],
        }
        manifest_path.write_text(json.dumps(leaked_payload), encoding="utf-8")
        result = ehf.verify_manifest_integrity(manifest_path)
        assert result["passed"] is False
        assert result["leakage"]["sha256_train_test"] == 1
        assert result["leakage"]["dhash_train_test"] == 1


class TestCheckpointAndNotebookContract:
    """Verify EfficientNet-B0 3-class checkpoint round-trip and Colab notebook syntax."""

    def test_checkpoint_contract_and_evaluation_roundtrip(self, tmp_path: Path) -> None:
        # Build synthetic test images & manifest
        img_paths = [
            ("test/genuine/g1.png", 0, "genuine", "ffhq", 10),
            ("test/ai_generated/a1.png", 1, "ai_generated", "stylegan2", 90),
            ("test/manipulated/m1.png", 2, "manipulated", "deepfakes", 180),
        ]
        manifest_rows = []
        for rel, label, cls_name, subset, color in img_paths:
            _write_rgb(tmp_path / rel, val=color)
            manifest_rows.append(
                {
                    "image_path": rel,
                    "split": "test",
                    "label": label,
                    "class_name": cls_name,
                    "source_subset": subset,
                    "source_group_id": f"{subset}::item::{cls_name}",
                    "sha256": f"sha_{cls_name}",
                    "md5": f"md5_{cls_name}",
                    "dhash": f"dhash_{cls_name}",
                }
            )
        manifest_path = tmp_path / "dataset_manifest.json"
        manifest_path.write_text(
            json.dumps({"class_names": list(hfd.CLASS_NAMES), "images": manifest_rows}),
            encoding="utf-8",
        )

        model = ehf.build_human_face_efficientnet_b0(num_classes=3, pretrained=False)
        assert model.head[1].out_features == 3

        ckpt_path = tmp_path / "human_face_efficientnet_b0_best.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "backbone": "efficientnet_b0",
                "num_classes": 3,
                "class_names": ["genuine", "ai_generated", "manipulated"],
                "input_size": 224,
                "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
                "model_version": "test_v1",
                "dataset_manifest": {"path": str(manifest_path)},
                "best_val_metrics": {"macro_f1": 0.91},
                "training_config": {"batch_size": 32},
                "epoch": 3,
                "created_at": "2026-11-12T00:00:00Z",
            },
            ckpt_path,
        )

        report_dir = tmp_path / "reports"
        report = ehf.evaluate_checkpoint_on_manifest(
            checkpoint_path=ckpt_path,
            manifest_path=manifest_path,
            split="test",
            data_root=tmp_path,
            batch_size=2,
            output_dir=report_dir,
        )
        assert report["metrics"]["total_samples"] == 3
        assert (report_dir / "human_face_eval_test.json").exists()
        assert (report_dir / "human_face_eval_test.md").exists()

    def test_colab_notebook_json_and_python_syntax_valid(self) -> None:
        nb_path = AI_ML_ROOT / "notebooks" / "train_human_face_colab.ipynb"
        assert nb_path.exists()
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
        assert nb["nbformat"] == 4
        code_cells = [c for c in nb["cells"] if c.get("cell_type") == "code"]
        assert len(code_cells) >= 7

        all_source = []
        for cell in code_cells:
            lines = [line for line in cell["source"] if not line.lstrip().startswith("!")]
            src = "".join(lines)
            ast.parse(src)
            all_source.append(src)

        joined = "\n".join(all_source)
        assert '"model_state_dict"' in joined
        assert '"optimizer_state_dict" not in best_ckpt' in joined
        assert "macro_f1" in joined
        assert "efficientnet_b0" in joined


def _load_notebook_definitions(extra_globals: dict | None = None) -> dict:
    """Extract and exec top-level function/class definitions from the Colab notebook without running training cells."""
    nb_path = AI_ML_ROOT / "notebooks" / "train_human_face_colab.ipynb"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))

    target_defs = {
        "extract_dataset_archive",
        "resolve_extracted_data_root",
        "validate_split_classes",
        "StreamingHumanFaceDataset",
        "safe_collate_valid_samples",
        "build_model",
        "configure_stage_trainable",
        "set_stage_train_mode",
        "make_optimizer",
        "restore_training_state",
        "compute_per_generator_breakdown_colab",
    }

    ns: dict = {
        "Path": Path,
        "Counter": Counter,
        "defaultdict": defaultdict,
        "zipfile": zipfile,
        "tarfile": tarfile,
        "Image": Image,
        "np": np,
        "torch": torch,
        "nn": nn,
        "timm": timm,
        "Dataset": Dataset,
        "logger": logging.getLogger("notebook_test"),
        "DEVICE": torch.device("cpu"),
        "SELECTIVE_UNFREEZE_PREFIXES": ("blocks.5.", "blocks.6.", "conv_head.", "bn2.", "head."),
        "CONFIG": {
            "backbone": "efficientnet_b0",
            "num_classes": 3,
            "class_names": ["genuine", "ai_generated", "manipulated"],
            "stage1_epochs": 4,
            "stage1_lr": 3e-4,
            "stage2_backbone_lr": 5e-5,
            "stage2_head_lr": 1e-4,
            "weight_decay": 1e-4,
        },
    }
    if extra_globals:
        ns.update(extra_globals)

    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        lines = [line for line in cell["source"] if not line.lstrip().startswith("!")]
        src = "".join(lines)
        tree = ast.parse(src)
        selected_nodes = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in target_defs
        ]
        if selected_nodes:
            mod = ast.Module(body=selected_nodes, type_ignores=[])
            ast.fix_missing_locations(mod)
            exec(compile(mod, filename=str(nb_path), mode="exec"), ns)

    return ns


class TestStage1EvaluationAndNotebookRegressions:
    """Stage 1 regression tests covering all technical review fixes."""

    def test_verify_manifest_integrity_detects_identity_and_hamming_leaks(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "dataset_manifest.json"
        # Two different source_group_ids and non-identical dhash with Hamming distance = 2 (0000...0000 vs 0000...0003)
        payload = {
            "schema_version": "1.0.0",
            "class_names": list(hfd.CLASS_NAMES),
            "images": [
                {
                    "image_path": "train/genuine/id0_a.png",
                    "split": "train",
                    "label": 0,
                    "class_name": "genuine",
                    "source_subset": "celeb_df_v2",
                    "source_group_id": "group_alpha",
                    "identity_tokens": ["celeb_actor::id0"],
                    "sha256": "sha_1",
                    "md5": "md5_1",
                    "dhash": "0000000000000000",
                },
                {
                    "image_path": "test/manipulated/id0_b.png",
                    "split": "test",
                    "label": 2,
                    "class_name": "manipulated",
                    "source_subset": "celeb_df_v2",
                    "source_group_id": "group_beta",
                    "identity_tokens": ["celeb_actor::id0"],
                    "sha256": "sha_2",
                    "md5": "md5_2",
                    "dhash": "0000000000000003",
                },
            ],
        }
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        result = ehf.verify_manifest_integrity(manifest_path, dhash_hamming_threshold=4)
        assert result["passed"] is False
        assert result["leakage"]["identity_token_train_test"] == 1
        assert result["leakage"]["dhash_hamming_cross_split"] == 1

    def test_compute_multiclass_metrics_rejects_missing_classes_by_default(self) -> None:
        # Missing class 2 (manipulated)
        y_true = [0, 0, 1, 1]
        y_probs = np.array(
            [
                [0.9, 0.05, 0.05],
                [0.8, 0.15, 0.05],
                [0.1, 0.85, 0.05],
                [0.2, 0.70, 0.10],
            ],
            dtype=np.float64,
        )
        with pytest.raises(ValueError, match="missing required classes"):
            ehf.compute_multiclass_metrics(y_true, y_probs, require_all_classes=True)

        partial = ehf.compute_multiclass_metrics(y_true, y_probs, require_all_classes=False)
        assert partial["partial_class_evaluation"] is True
        assert partial["missing_classes"] == ["manipulated"]
        assert partial["per_class"]["manipulated"]["support"] == 0

    def test_compute_per_generator_breakdown_handles_mixed_label_subset(self) -> None:
        # Mixed-label container ("kaggle_140k") containing both label=0 (genuine) and label=1 (ai_generated)
        records = [
            {"source_subset": "kaggle_140k"},
            {"source_subset": "kaggle_140k"},
            {"source_subset": "kaggle_140k"},
        ]
        y_true = [0, 1, 1]
        y_probs = np.array(
            [
                [0.90, 0.05, 0.05],  # correct genuine
                [0.80, 0.15, 0.05],  # non-genuine misclassified as genuine -> counted in FGR
                [0.05, 0.90, 0.05],  # correct ai_generated
            ],
            dtype=np.float64,
        )
        breakdown = ehf.compute_per_generator_breakdown(records, y_true, y_probs)
        entry = breakdown["kaggle_140k"]
        assert entry["expected_class"] == "mixed"
        assert entry["label_distribution"] == {"genuine": 1, "ai_generated": 2}
        assert entry["non_genuine_count"] == 2
        assert np.isclose(entry["accuracy"], 2 / 3, atol=1e-5)
        # 1 out of 2 non-genuine samples misclassified as genuine -> 0.5
        assert np.isclose(entry["false_genuine_rate"], 0.5, atol=1e-5)

    def test_load_checkpoint_validates_class_order_and_normalization_metadata(self, tmp_path: Path) -> None:
        model = ehf.build_human_face_efficientnet_b0(num_classes=3, pretrained=False)

        bad_classes_ckpt = tmp_path / "bad_classes.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "backbone": "efficientnet_b0",
                "num_classes": 3,
                "class_names": ["genuine", "manipulated", "ai_generated"],
                "input_size": 224,
                "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
            },
            bad_classes_ckpt,
        )
        with pytest.raises(ValueError, match="class_names"):
            ehf.load_human_face_checkpoint(bad_classes_ckpt, device=torch.device("cpu"))

        bad_norm_ckpt = tmp_path / "bad_norm.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "backbone": "efficientnet_b0",
                "num_classes": 3,
                "class_names": ["genuine", "ai_generated", "manipulated"],
                "input_size": 224,
                "normalization": {"mean": [0.5, 0.5], "std": [0.5, 0.5, 0.5]},
            },
            bad_norm_ckpt,
        )
        with pytest.raises(ValueError, match="normalization"):
            ehf.load_human_face_checkpoint(bad_norm_ckpt, device=torch.device("cpu"))

        custom_norm = {"mean": [0.5, 0.5, 0.5], "std": [0.25, 0.25, 0.25]}
        valid_ckpt = tmp_path / "custom_norm.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "backbone": "efficientnet_b0",
                "num_classes": 3,
                "class_names": ["genuine", "ai_generated", "manipulated"],
                "input_size": 224,
                "normalization": custom_norm,
            },
            valid_ckpt,
        )

        rows = []
        for rel, label, cls_name, subset, col in [
            ("test/g.png", 0, "genuine", "ffhq", 10),
            ("test/a.png", 1, "ai_generated", "stylegan2", 100),
            ("test/m.png", 2, "manipulated", "deepfakes", 200),
        ]:
            _write_rgb(tmp_path / rel, col)
            rows.append({"image_path": rel, "split": "test", "label": label, "class_name": cls_name, "source_subset": subset})
        manifest_path = tmp_path / "dataset_manifest.json"
        manifest_path.write_text(json.dumps({"class_names": list(hfd.CLASS_NAMES), "images": rows}), encoding="utf-8")

        report = ehf.evaluate_checkpoint_on_manifest(
            checkpoint_path=valid_ckpt,
            manifest_path=manifest_path,
            split="test",
            data_root=tmp_path,
        )
        assert report["normalization"] == custom_norm

    def test_notebook_stage1_dropout_and_stage2_patience_reset(self, tmp_path: Path) -> None:
        ns = _load_notebook_definitions()
        model = ns["build_model"](pretrained=False)
        ns["model"] = model  # used by notebook's make_optimizer helper

        # Stage 1 must keep head.Dropout in train() while backbone submodules stay eval()
        ns["set_stage_train_mode"](model, stage=1)
        assert model.head.training is True
        assert model.head[0].training is True  # nn.Dropout(p=0.2)
        assert model.blocks[0].training is False
        assert model.conv_stem.training is False

        # Resume within Stage 1 preserves no_improve_count
        opt1 = ns["make_optimizer"](stage=1)
        scaler = torch.cuda.amp.GradScaler(enabled=False)
        resume_stage1 = tmp_path / "resume_s1.pt"
        torch.save(
            {
                "epoch": 2,
                "stage": 1,
                "best_macro_f1": 0.72,
                "no_improve_count": 3,
                "history": [{"epoch": 1}, {"epoch": 2}],
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": opt1.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
            },
            resume_stage1,
        )
        next_ep, tgt_stage, best_f1, patience, hist, _ = ns["restore_training_state"](resume_stage1, model, scaler)
        assert next_ep == 3
        assert tgt_stage == 1
        assert np.isclose(best_f1, 0.72)
        assert patience == 3
        assert len(hist) == 2

        # Resume right at Stage 1 -> Stage 2 boundary resets no_improve_count to 0
        resume_boundary = tmp_path / "resume_boundary.pt"
        torch.save(
            {
                "epoch": 4,  # equals stage1_epochs -> next_ep = 5 -> Stage 2
                "stage": 1,
                "best_macro_f1": 0.75,
                "no_improve_count": 4,
                "history": [],
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": opt1.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
            },
            resume_boundary,
        )
        next_ep2, tgt_stage2, _, patience2, _, _ = ns["restore_training_state"](resume_boundary, model, scaler)
        assert next_ep2 == 5
        assert tgt_stage2 == 2
        assert patience2 == 0

    def test_notebook_archive_extraction_split_validation_and_corrupt_collate(self, tmp_path: Path) -> None:
        ns = _load_notebook_definitions()

        # 1) Missing class rejection in validate_split_classes
        with pytest.raises(RuntimeError, match="missing required classes"):
            ns["validate_split_classes"](
                {
                    "train": [{"label": 0}, {"label": 1}, {"label": 2}],
                    "val": [{"label": 0}, {"label": 1}],
                    "test": [{"label": 0}, {"label": 1}, {"label": 2}],
                },
                ["genuine", "ai_generated", "manipulated"],
            )

        # 2) Reject non-portable absolute manifest paths in resolve_extracted_data_root
        abs_sample = str((tmp_path / "abs.png").resolve())
        with pytest.raises(ValueError, match="non-portable absolute"):
            ns["resolve_extracted_data_root"](tmp_path, {"images": [{"image_path": abs_sample}]})

        # 3) ZIP and TAR archive extraction with nested wrapper directory auto-detection
        src_tree = tmp_path / "archive_src"
        nested_img = src_tree / "wrapped_root" / "materialized" / "train" / "genuine" / "sample.png"
        _write_rgb(nested_img, 42)
        manifest_data = {"images": [{"image_path": "materialized/train/genuine/sample.png"}]}

        zip_path = tmp_path / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(nested_img, arcname="wrapped_root/materialized/train/genuine/sample.png")
        zip_out = ns["extract_dataset_archive"](zip_path, tmp_path / "out_zip")
        resolved_zip_root = ns["resolve_extracted_data_root"](zip_out, manifest_data)
        assert (resolved_zip_root / "materialized/train/genuine/sample.png").exists()

        tar_path = tmp_path / "bundle.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(nested_img, arcname="wrapped_root/materialized/train/genuine/sample.png")
        tar_out = ns["extract_dataset_archive"](tar_path, tmp_path / "out_tar")
        resolved_tar_root = ns["resolve_extracted_data_root"](tar_out, manifest_data)
        assert (resolved_tar_root / "materialized/train/genuine/sample.png").exists()

        # 4) StreamingHumanFaceDataset + safe_collate_valid_samples skips corrupt image cleanly
        good_rel = "imgs/good.png"
        bad_rel = "imgs/corrupt.png"
        _write_rgb(tmp_path / good_rel, 80)
        (tmp_path / bad_rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / bad_rel).write_bytes(b"not_a_valid_image")

        from torchvision import transforms

        ds = ns["StreamingHumanFaceDataset"](
            [{"image_path": good_rel, "label": 1}, {"image_path": bad_rel, "label": 2}],
            data_root=tmp_path,
            transform=transforms.Compose([transforms.Resize((32, 32)), transforms.ToTensor()]),
        )
        batch = ns["safe_collate_valid_samples"]([ds[0], ds[1]])
        assert batch is not None
        imgs, labels, indices = batch
        assert imgs.shape[0] == 1
        assert labels.tolist() == [1]
        assert indices == [0]
        assert len(ds.decode_errors) == 1

        # 5) Notebook mixed-label per-generator breakdown matches evaluate_human_face.py
        mixed_records = [
            {"source_subset": "mixed_container"},
            {"source_subset": "mixed_container"},
        ]
        nb_breakdown = ns["compute_per_generator_breakdown_colab"](
            mixed_records,
            [0, 1],
            [0, 2],
            np.array([[0.8, 0.1, 0.1], [0.7, 0.1, 0.2]], dtype=np.float64),
            ["genuine", "ai_generated", "manipulated"],
        )
        assert nb_breakdown["mixed_container"]["expected_class"] == "mixed"
        assert nb_breakdown["mixed_container"]["false_genuine_rate"] == 1.0
