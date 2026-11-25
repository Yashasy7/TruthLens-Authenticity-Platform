"""Unit & regression tests for Stage 1 human-face 3-class dataset preparation pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import sys

from PIL import Image
import pytest

AI_ML_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ML_ROOT))

import human_face_dataset as hfd  # noqa: E402


def _make_patterned_image(path: Path, seed_val: int, size: tuple[int, int] = (32, 32)) -> None:
    """Create a deterministic patterned image so each seed produces a distinct dhash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size)
    pixels = []
    for y in range(size[1]):
        for x in range(size[0]):
            r = (x * (seed_val + 3) + y * 5) % 256
            g = (y * (seed_val + 7) + x * 11) % 256
            b = ((x ^ y) * (seed_val + 13)) % 256
            pixels.append((r, g, b))
    img.putdata(pixels)
    img.save(path, format="PNG")


class TestSubsetResolution:
    """Verify strict 3-class resolution, Celeb-DF-v2/FF++ polarity, and short-token safety."""

    def test_verified_mappings_and_celebdf_polarity(self) -> None:
        assert hfd.resolve_subset_class("FFHQ/00001.png", binary_target=0)[0] == "genuine"
        assert hfd.resolve_subset_class("StyleGAN2/img_01.png", binary_target=1)[0] == "ai_generated"
        assert hfd.resolve_subset_class("Midjourney/mj_01.png", binary_target=1)[0] == "ai_generated"
        assert hfd.resolve_subset_class("FF++/Deepfakes/001_002/01.png", binary_target=1)[0] == "manipulated"
        assert hfd.resolve_subset_class("FF++/fake/001_002/01.png")[0] == "manipulated"
        assert hfd.resolve_subset_class("DFDC/real/vid01/01.png", binary_target=0)[0] == "genuine"
        assert hfd.resolve_subset_class("DFDC/fake/vid01/01.png", binary_target=1)[0] == "manipulated"

        # Celeb-DF-v2 folder polarity without CSV binary target
        cls_real, sub_real, _ = hfd.resolve_subset_class("Celeb-DF-v2/Celeb-real/id0_0001.jpg")
        assert cls_real == "genuine"
        assert sub_real == "celeb_real"

        cls_syn, sub_syn, _ = hfd.resolve_subset_class("Celeb-DF-v2/Celeb-synthesis/id0_id1_0001.jpg")
        assert cls_syn == "manipulated"
        assert sub_syn == "celeb_synthesis"

        # Generic real/fake polarity inside Celeb-DF-v2 container
        assert hfd.resolve_subset_class("Celeb-DF-v2/real/id0_0001.jpg")[:2] == ("genuine", "celeb_df_v2_real")
        assert hfd.resolve_subset_class("Celeb-DF-v2/fake/id0_id1_0001.jpg")[:2] == ("manipulated", "celeb_df_v2")

    def test_short_token_if_not_matched_in_arbitrary_path(self) -> None:
        cls_bad, _, reason_bad = hfd.resolve_subset_class("experiments/if/sample_01.png", binary_target=1)
        assert cls_bad is None
        assert reason_bad == "unverified_subset"

        # Explicit uppercase folder "IF" or explicit method="IF" still resolves
        assert hfd.resolve_subset_class("IF/sample_01.png", binary_target=1)[0] == "ai_generated"
        assert hfd.resolve_subset_class("custom/sample_01.png", binary_target=1, explicit_subset="IF")[0] == "ai_generated"

    def test_never_infers_class_from_binary_target_alone(self) -> None:
        cls_name, _, reason = hfd.resolve_subset_class("unknown_source/img_01.png", binary_target=1)
        assert cls_name is None
        assert reason == "unverified_subset"

        cls_generic, _, reason_generic = hfd.resolve_subset_class("fake/img_01.png", binary_target=1)
        assert cls_generic is None
        assert reason_generic == "unverified_subset"

    def test_rejects_binary_target_mismatch(self) -> None:
        cls_name, _, reason = hfd.resolve_subset_class("FFHQ/00001.png", binary_target=1)
        assert cls_name is None
        assert reason == "target_mismatch_expected_real"

        cls_name2, _, reason2 = hfd.resolve_subset_class("StyleGAN/00001.png", binary_target=0)
        assert cls_name2 is None
        assert reason2 == "target_mismatch_expected_fake"

    def test_quarantines_ambiguous_subsets_by_default(self) -> None:
        for subset in ("AttGAN", "StarGAN", "STGAN", "Palette", "Stable_Diffusion_Inpainting"):
            cls_name, _, reason = hfd.resolve_subset_class(f"{subset}/0001.png", binary_target=1)
            assert cls_name is None
            assert reason == "ambiguous_quarantined"

        cls_opt_in, _, reason_opt = hfd.resolve_subset_class(
            "AttGAN/0001.png", binary_target=1, ambiguous_policy="manipulated"
        )
        assert cls_opt_in == "manipulated"
        assert reason_opt == "ambiguous_mapped_to_manipulated"


class TestPairingGroupingAndDeduplication:
    """Verify FF++/Celeb-DF paired grouping, generic folder safety, Hamming dedup, and determinism."""

    def test_ffpp_paired_real_and_fake_grouping(self) -> None:
        grp_real, toks_real = hfd.extract_identity_tokens_and_group(
            "FF++/original_sequences/youtube/001/frame_01.png",
            subset_name="original_sequences",
            source_container="ff_pp",
        )
        grp_df, toks_df = hfd.extract_identity_tokens_and_group(
            "FF++/Deepfakes/001_002/frame_01.png",
            subset_name="deepfakes",
            source_container="ff_pp",
        )
        grp_fs, toks_fs = hfd.extract_identity_tokens_and_group(
            "FF++/FaceShifter/001_002/frame_02.png",
            subset_name="faceshifter",
            source_container="ff_pp",
        )
        assert grp_real == grp_df == grp_fs == "ffpp::clip::001"
        assert "ffpp::clip::001" in toks_real
        assert "ffpp::clip::001" in toks_df
        assert "ffpp::clip::002" in toks_fs

    def test_celebdf_paired_real_and_fake_grouping_and_unseen_test_routing(self, tmp_path: Path) -> None:
        root = tmp_path / "data"
        paths_meta = [
            ("Celeb-DF-v2/Celeb-real/id0_0001/f1.png", "genuine", "celeb_df_v2_real", "celeb_df_v2", 1),
            ("Celeb-DF-v2/Celeb-synthesis/id0_id1_0001/f2.png", "manipulated", "celeb_df_v2", "celeb_df_v2", 7),
            ("FFHQ/real_100.png", "genuine", "ffhq", None, 13),
            ("FFHQ/real_101.png", "genuine", "ffhq", None, 19),
            ("FF++/Deepfakes/010_011/f1.png", "manipulated", "deepfakes", "ff_pp", 23),
            ("FF++/original_sequences/010/f1.png", "genuine", "original_sequences", "ff_pp", 29),
        ]
        recs = []
        for rel, cls_name, subset, container, seed in paths_meta:
            p = root / rel
            _make_patterned_image(p, seed_val=seed)
            gid, toks = hfd.extract_identity_tokens_and_group(rel, subset_name=subset, source_container=container)
            recs.append(
                {
                    "source_path": str(p),
                    "relative_source_path": rel,
                    "anchor_root": str(root),
                    "class_name": cls_name,
                    "label": hfd.CLASS_TO_ID[cls_name],
                    "source_subset": subset,
                    "source_container": container,
                    "source_group_id": gid,
                    "identity_tokens": toks,
                }
            )

        uniq, _ = hfd.deduplicate_and_validate_records(recs, unseen_test_generators=["celeb_df_v2"])
        splits = hfd.assign_leakage_free_splits(uniq, unseen_test_generators=["celeb_df_v2"], seed=42)

        by_rel = {r["relative_source_path"]: r["split"] for r in splits}
        # Both Celeb-DF-v2 synthetic AND paired real id0 MUST land in test together!
        assert by_rel["Celeb-DF-v2/Celeb-real/id0_0001/f1.png"] == "test"
        assert by_rel["Celeb-DF-v2/Celeb-synthesis/id0_id1_0001/f2.png"] == "test"
        # FF++ paired real 010 and Deepfakes 010_011 MUST land in the exact same split!
        assert by_rel["FF++/Deepfakes/010_011/f1.png"] == by_rel["FF++/original_sequences/010/f1.png"]

    def test_generic_parent_folders_never_collapse_into_one_group(self) -> None:
        g_train, _ = hfd.extract_identity_tokens_and_group("StyleGAN2/train/img_0001.png", "stylegan2")
        g_part, _ = hfd.extract_identity_tokens_and_group("Latent_Diffusion/part_01/img_0002.png", "latent_diffusion")
        g_batch, _ = hfd.extract_identity_tokens_and_group("ProGAN/batch_01/img_0003.png", "progan")
        assert "::dir::train" not in g_train
        assert "::dir::part_01" not in g_part
        assert "::dir::batch_01" not in g_batch

    def test_hamming_distance_near_duplicate_and_deterministic_dedup(self, tmp_path: Path) -> None:
        img_a = tmp_path / "FFHQ" / "a.png"
        img_b_near = tmp_path / "FFHQ" / "b_near.png"
        img_c_unseen = tmp_path / "Midjourney" / "c.png"
        img_d_unique = tmp_path / "StyleGAN2" / "d.png"

        _make_patterned_image(img_a, seed_val=3)
        # Heavy JPEG compression / slight resize can alter bits within Hamming <= 4
        with Image.open(img_a) as im:
            im.save(img_b_near, format="JPEG", quality=75)
        img_c_unseen.parent.mkdir(parents=True, exist_ok=True)
        # Same content placed inside an unseen test generator (with slight JPEG re-save)
        with Image.open(img_a) as im:
            im.save(img_c_unseen, format="JPEG", quality=85)
        _make_patterned_image(img_d_unique, seed_val=41)

        _, _, h_a, _, _ = hfd.compute_hashes(img_a)
        _, _, h_b, _, _ = hfd.compute_hashes(img_b_near)
        assert hfd.dhash_hamming_distance(h_a, h_b) <= 4

        recs = [
            {
                "source_path": str(img_a),
                "relative_source_path": "FFHQ/a.png",
                "class_name": "genuine",
                "label": 0,
                "source_subset": "ffhq",
                "source_group_id": "ffhq::item::a",
            },
            {
                "source_path": str(img_b_near),
                "relative_source_path": "FFHQ/b_near.jpg",
                "class_name": "genuine",
                "label": 0,
                "source_subset": "ffhq",
                "source_group_id": "ffhq::item::b_near",
            },
            {
                "source_path": str(img_c_unseen),
                "relative_source_path": "Midjourney/c.jpg",
                "class_name": "ai_generated",
                "label": 1,
                "source_subset": "midjourney",
                "source_group_id": "midjourney::item::c",
            },
            {
                "source_path": str(img_d_unique),
                "relative_source_path": "StyleGAN2/d.png",
                "class_name": "ai_generated",
                "label": 1,
                "source_subset": "stylegan2",
                "source_group_id": "stylegan2::item::d",
            },
        ]

        kept_fwd, stats_fwd = hfd.deduplicate_and_validate_records(
            recs,
            dhash_hamming_threshold=4,
            unseen_test_generators=["midjourney"],
        )
        shuffled = list(recs)
        random.Random(99).shuffle(shuffled)
        kept_rev, _ = hfd.deduplicate_and_validate_records(
            shuffled,
            dhash_hamming_threshold=4,
            unseen_test_generators=["midjourney"],
        )

        # Unseen test item (Midjourney/c.jpg) must be prioritized over near-duplicate shared FFHQ items,
        # and deduplication result must be identical regardless of input order!
        assert [r["sha256"] for r in kept_fwd] == [r["sha256"] for r in kept_rev]
        kept_subsets = {r["source_subset"] for r in kept_fwd}
        assert kept_subsets == {"midjourney", "stylegan2"}
        assert stats_fwd["perceptual_duplicate_removed"] == 2


class TestQuotasAndPortableManifest:
    """Verify explicit quota shortfall reporting, atomic group preservation, and Colab paths."""

    def test_quota_shortfall_explicit_and_strict_mode_fails(self, tmp_path: Path) -> None:
        root = tmp_path / "aiface"
        csv_path = root / "dataset" / "train.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        seed = 1
        # Only 4 images in FFHQ + 4 StyleGAN2 + 4 Deepfakes (grouped as 2 pairs of 2)
        for i in range(4):
            rel = f"FFHQ/r_{i}.png"
            _make_patterned_image(root / rel, seed_val=seed)
            rows.append([rel, "0"])
            seed += 5
        for i in range(4):
            rel = f"StyleGAN2/s_{i}.png"
            _make_patterned_image(root / rel, seed_val=seed)
            rows.append([rel, "1"])
            seed += 5
        for vid in range(2):
            for f_i in range(2):
                rel = f"FF++/Deepfakes/0{vid}_99/frame_{f_i}.png"
                _make_patterned_image(root / rel, seed_val=seed)
                rows.append([rel, "1"])
                seed += 5

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Image Path", "Target"])
            writer.writerows(rows)

        out_dir = tmp_path / "manifest_only_out"
        # Manifest-only mode with target_per_class=10 (shortfall expected!)
        hfd.main(
            [
                "--aiface-csv",
                str(csv_path),
                "--aiface-root",
                str(root),
                "--output-dir",
                str(out_dir),
                "--target-per-class",
                "10",
            ]
        )
        manifest = json.loads((out_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
        audit = json.loads((out_dir / "dataset_audit_report.json").read_text(encoding="utf-8"))

        assert audit["quota_shortfalls"]["genuine"]["shortfall"] == 6
        assert audit["quota_shortfalls"]["ai_generated"]["shortfall"] == 6
        assert audit["quota_shortfalls"]["manipulated"]["shortfall"] == 6
        assert audit["zero_leakage_verified"] is True

        # Ensure manifest-only paths are portable POSIX relative paths (never Windows drive letter paths)
        for item in manifest["images"]:
            img_p = item["image_path"]
            assert not Path(img_p).is_absolute()
            assert ":\\" not in img_p and ":/" not in img_p

        # Ensure strict-quotas rejects shortfall
        with pytest.raises(RuntimeError, match="Strict quota check failed"):
            hfd.main(
                [
                    "--aiface-csv",
                    str(csv_path),
                    "--aiface-root",
                    str(root),
                    "--output-dir",
                    str(tmp_path / "strict_fail"),
                    "--target-per-class",
                    "10",
                    "--strict-quotas",
                ]
            )

    def test_kaggle_140k_profile_never_labels_manipulated(self, tmp_path: Path) -> None:
        ds_dir = tmp_path / "DeepFakeDetection"
        _make_patterned_image(ds_dir / "real" / "00000.jpg", seed_val=2)
        _make_patterned_image(ds_dir / "fake" / "001DDU0NI4.jpg", seed_val=9)

        recs, rej = hfd.scan_local_source_directory(ds_dir, source_profile="kaggle_140k_ffhq_stylegan")
        assert len(recs) == 2
        assert len(rej) == 0
        assert {r["class_name"] for r in recs} == {"genuine", "ai_generated"}
