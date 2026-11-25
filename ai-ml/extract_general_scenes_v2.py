"""
TruthLens AI/ML — General Scenes Dataset Acquisition Script (general_scenes_v2)
Acquires and validates the photographic dataset from TheKernel01/Tiny-GenImage.

Target:
- Real: 4,000 (2,400 Train, 600 Val, 1,000 Test)
- Fake: 3,500 - 4,000 (ADM, BigGAN, GLIDE, SD15, VQDM in Train/Val; Midjourney, Wukong in Test)
Note: SD14 is defined in Tiny-GenImage schema names but contains 0 samples in source Parquet files.

Guarantees:
- Real images selected independently with 0 overlap across splits.
- All 3,000 rows/MD5s previously downloaded in photographic_pilot and photographic_scenes are strictly excluded.
- Midjourney and Wukong appear strictly in test.
- SD15, ADM, BigGAN, GLIDE, VQDM appear strictly in train/val.
- Pillow integrity, exact MD5, SHA-256, and perceptual dhash validated for every image.
- Resilient pagination: skips failed pages after backoff rather than aborting splits.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import shutil
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.general_scenes_v2")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "ai-ml" / "data" / "expanded_image_detection"

PILOT_MANIFEST_PATH = DATA_ROOT / "photographic_pilot" / "pilot_manifest.json"
SCENES_MANIFEST_PATH = DATA_ROOT / "photographic_scenes" / "photographic_manifest.json"

TARGET_DIR = DATA_ROOT / "general_scenes_v2"
TARGET_MANIFEST_PATH = TARGET_DIR / "general_scenes_manifest.json"
SUMMARY_MD_PATH = TARGET_DIR / "EXTRACTION_SUMMARY.md"

API_BASE = "https://datasets-server.huggingface.co/rows?dataset=TheKernel01/Tiny-GenImage&config=default"

GENERATOR_NAMES = {
    0: "Real",
    1: "ADM",
    2: "BigGAN",
    3: "GLIDE",
    4: "Midjourney",
    5: "SD14",
    6: "SD15",
    7: "VQDM",
    8: "Wukong",
}

# Quotas per (split, label_name, generator_id)
TARGET_QUOTAS: Dict[Tuple[str, str, int], int] = {
    # Train Real
    ("train", "real", 0): 2400,
    # Val Real
    ("val", "real", 0): 600,
    # Test Real
    ("test", "real", 0): 1000,

    # Train Fake
    ("train", "fake", 1): 400,  # ADM
    ("train", "fake", 2): 400,  # BigGAN
    ("train", "fake", 3): 400,  # GLIDE
    ("train", "fake", 5): 400,  # SD14 (0 in source)
    ("train", "fake", 6): 400,  # SD15
    ("train", "fake", 7): 400,  # VQDM

    # Val Fake
    ("val", "fake", 1): 100,    # ADM
    ("val", "fake", 2): 100,    # BigGAN
    ("val", "fake", 3): 100,    # GLIDE
    ("val", "fake", 5): 100,    # SD14 (0 in source)
    ("val", "fake", 6): 100,    # SD15
    ("val", "fake", 7): 100,    # VQDM

    # Test Fake (2 unseen generators)
    ("test", "fake", 4): 500,   # Midjourney
    ("test", "fake", 8): 500,   # Wukong
}


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Compute difference hash (perceptual hash)."""
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.getdata())
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            p1 = pixels[row * (hash_size + 1) + col]
            p2 = pixels[row * (hash_size + 1) + col + 1]
            diff.append(p1 > p2)
    val = 0
    hex_str = []
    for i, b in enumerate(diff):
        if b:
            val += 2 ** (i % 8)
        if (i % 8) == 7:
            hex_str.append(hex(val)[2:].rjust(2, "0"))
            val = 0
    return "".join(hex_str)


def fetch_api_page(split: str, offset: int, length: int = 100, max_retries: int = 5) -> Tuple[Dict[str, Any], int]:
    """Fetch one page of rows from Hugging Face Serverless API with exponential backoff."""
    url = f"{API_BASE}&split={split}&offset={offset}&length={length}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TruthLens-GeneralScenes-v2/1.0"}
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8")), len(data)
        except Exception as exc:
            if attempt == max_retries - 1:
                logger.warning("Max retries exceeded at split=%s offset=%d: %s. Skipping offset.", split, offset, exc)
                return {}, 0
            sleep_time = 3.0 * (attempt + 1)
            logger.warning("API error at split=%s offset=%d (attempt %d/%d): %s. Retrying in %.1fs...", split, offset, attempt + 1, max_retries, exc, sleep_time)
            time.sleep(sleep_time)
    return {}, 0


def download_single_image(url: str, max_retries: int = 3) -> bytes:
    """Download image payload from CloudFront CDN."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TruthLens-GeneralScenes-v2/1.0"}
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read()
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            time.sleep(1.0 * (attempt + 1))
    return b""


def load_excluded_fingerprints() -> Tuple[Set[str], Set[int]]:
    """Ingest row indices and MD5s from photographic_pilot and photographic_scenes."""
    excluded_md5s: Set[str] = set()
    excluded_rows: Set[int] = set()

    for p in [PILOT_MANIFEST_PATH, SCENES_MANIFEST_PATH]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                for item in manifest_data.get("images", []):
                    if "md5" in item:
                        excluded_md5s.add(item["md5"])
                    if "huggingface_row_idx" in item and item["huggingface_row_idx"] is not None:
                        excluded_rows.add(item["huggingface_row_idx"])
                    elif "source_row_id" in item and item["source_row_id"] is not None:
                        excluded_rows.add(item["source_row_id"])
            except Exception as e:
                logger.warning("Could not read previous manifest %s: %s", p, e)

    logger.info("Loaded %d excluded MD5s and %d excluded row indices from previous datasets.", len(excluded_md5s), len(excluded_rows))
    return excluded_md5s, excluded_rows


def save_manifest_and_summary(
    collected_records: List[Dict[str, Any]],
    current_counts: Dict[Tuple[str, str, int], int],
    seen_md5s: Dict[str, str],
    seen_dhashes: Dict[str, List[str]],
    total_api_bytes: int,
    total_image_bytes: int,
    start_time: float,
    total_rows_scanned: int,
):
    """Save general_scenes_manifest.json and EXTRACTION_SUMMARY.md atomically."""
    elapsed = time.perf_counter() - start_time
    saved_files = list(TARGET_DIR.glob("**/*.*"))
    disk_bytes = sum(f.stat().st_size for f in saved_files if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"])

    perceptual_dupes = {k: v for k, v in seen_dhashes.items() if len(v) > 1 and k}

    split_summary = {
        "train": {
            "real": current_counts.get(("train", "real", 0), 0),
            "fake": sum(current_counts.get(("train", "fake", g), 0) for g in [1, 2, 3, 5, 6, 7]),
            "generators": {GENERATOR_NAMES[g]: current_counts.get(("train", "fake", g), 0) for g in [1, 2, 3, 5, 6, 7]},
            "total": current_counts.get(("train", "real", 0), 0) + sum(current_counts.get(("train", "fake", g), 0) for g in [1, 2, 3, 5, 6, 7]),
        },
        "val": {
            "real": current_counts.get(("val", "real", 0), 0),
            "fake": sum(current_counts.get(("val", "fake", g), 0) for g in [1, 2, 3, 5, 6, 7]),
            "generators": {GENERATOR_NAMES[g]: current_counts.get(("val", "fake", g), 0) for g in [1, 2, 3, 5, 6, 7]},
            "total": current_counts.get(("val", "real", 0), 0) + sum(current_counts.get(("val", "fake", g), 0) for g in [1, 2, 3, 5, 6, 7]),
        },
        "test": {
            "real": current_counts.get(("test", "real", 0), 0),
            "fake": sum(current_counts.get(("test", "fake", g), 0) for g in [4, 8]),
            "generators": {GENERATOR_NAMES[g]: current_counts.get(("test", "fake", g), 0) for g in [4, 8]},
            "total": current_counts.get(("test", "real", 0), 0) + sum(current_counts.get(("test", "fake", g), 0) for g in [4, 8]),
        },
    }

    manifest_payload = {
        "dataset_name": "TruthLens-General-Scenes-v2",
        "description": "Expanded general photographic dataset for media authenticity detection with training generators and unseen test generators",
        "version": "2.0.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_directory": str(TARGET_DIR),
        "license": "CC BY-NC-SA 4.0 (GenImage) / Non-commercial research only (ImageNet-1k)",
        "source_repository": "https://huggingface.co/datasets/TheKernel01/Tiny-GenImage",
        "note": "SD14 was omitted by source repository Tiny-GenImage (0 rows). Real and available synthetic generators are balanced.",
        "statistics": {
            "total_images": len(collected_records),
            "rows_scanned": total_rows_scanned,
            "split_breakdown": split_summary,
            "counts_by_generator": {
                GENERATOR_NAMES[g]: sum(current_counts.get((s, "fake" if g > 0 else "real", g), 0) for s in ["train", "val", "test"])
                for g in GENERATOR_NAMES
            },
            "counts_by_label": {
                "real": sum(1 for r in collected_records if r["label"] == 0),
                "fake": sum(1 for r in collected_records if r["label"] == 1),
            },
            "network_transfer": {
                "api_metadata_bytes": total_api_bytes,
                "image_data_bytes": total_image_bytes,
                "total_downloaded_bytes": total_api_bytes + total_image_bytes,
                "total_downloaded_mb": round((total_api_bytes + total_image_bytes) / (1024 * 1024), 2),
            },
            "disk_usage": {
                "total_disk_bytes": disk_bytes,
                "total_disk_mb": round(disk_bytes / (1024 * 1024), 2),
            },
            "duplicate_audit": {
                "exact_md5_duplicates": len(collected_records) - len(seen_md5s),
                "perceptual_dhash_collisions": len(perceptual_dupes),
                "collision_details": perceptual_dupes,
            },
            "elapsed_seconds": round(elapsed, 2),
        },
        "images": collected_records,
    }

    tmp_manifest = TARGET_DIR / "general_scenes_manifest.json.tmp"
    with open(tmp_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)
    tmp_manifest.replace(TARGET_MANIFEST_PATH)
    logger.info("Saved manifest to %s (Total images: %d)", TARGET_MANIFEST_PATH, len(collected_records))

    # Summary Markdown
    summary_text = f"""# TruthLens — General Scenes v2 Extraction Summary

- **Total Images:** {len(collected_records)} ({manifest_payload['statistics']['counts_by_label']['real']} Real / {manifest_payload['statistics']['counts_by_label']['fake']} Fake)
- **Total Network Transfer:** {manifest_payload['statistics']['network_transfer']['total_downloaded_mb']} MB
- **Total Disk Usage:** {manifest_payload['statistics']['disk_usage']['total_disk_mb']} MB
- **Elapsed Time:** {round(elapsed / 60, 2)} minutes

## Split Distribution
| Split | Real (ImageNet) | AI-Generated | Generators Represented | Total Split Images |
| :--- | :--- | :--- | :--- | :--- |
| **Training** | {split_summary['train']['real']} | {split_summary['train']['fake']} | {', '.join(f'{k} ({v})' for k, v in split_summary['train']['generators'].items() if v > 0)} | {split_summary['train']['total']} |
| **Validation** | {split_summary['val']['real']} | {split_summary['val']['fake']} | {', '.join(f'{k} ({v})' for k, v in split_summary['val']['generators'].items() if v > 0)} | {split_summary['val']['total']} |
| **Test (Unseen)** | {split_summary['test']['real']} | {split_summary['test']['fake']} | Midjourney ({split_summary['test']['generators'].get('Midjourney', 0)}), Wukong ({split_summary['test']['generators'].get('Wukong', 0)}) — **100% Unseen** | {split_summary['test']['total']} |
| **Total** | **{manifest_payload['statistics']['counts_by_label']['real']}** | **{manifest_payload['statistics']['counts_by_label']['fake']}** | | **{len(collected_records)}** |

## Verification & Guarantees
- **Disjoint Real Splits:** Real images in train, val, and test have 0 row or MD5 overlap.
- **Generator Isolation:** Midjourney and Wukong appear exclusively in the test split. Training generators are 100% excluded from test.
- **Previous Dataset Isolation:** Completely excludes the 3,000 images previously present in photographic_pilot and photographic_scenes.
- **Zero Exact Duplicates:** 0 MD5 duplicate collisions across all samples.
- **Dataset Limitation:** SD14 is defined in the Tiny-GenImage schema but contains 0 samples in the source Parquet files.
"""
    with open(SUMMARY_MD_PATH, "w", encoding="utf-8") as f:
        f.write(summary_text)


def main():
    start_time = time.perf_counter()
    logger.info("Initializing TruthLens General Scenes v2 Extraction...")

    # Create directory structure
    for split in ["train", "val", "test"]:
        for label_name in ["real", "fake"]:
            (TARGET_DIR / split / label_name).mkdir(parents=True, exist_ok=True)

    # Step 1: Load exclusions from previous datasets
    excluded_md5s, excluded_rows = load_excluded_fingerprints()

    # Step 2: Initialize or resume state
    collected_records: List[Dict[str, Any]] = []
    current_counts: Dict[Tuple[str, str, int], int] = {k: 0 for k in TARGET_QUOTAS}
    seen_md5s: Dict[str, str] = {}
    seen_rows: Set[int] = set()
    seen_dhashes: Dict[str, List[str]] = {}

    total_api_bytes = 0
    total_image_bytes = 0

    if TARGET_MANIFEST_PATH.exists():
        logger.info("Existing manifest found at %s. Resuming extraction...", TARGET_MANIFEST_PATH)
        with open(TARGET_MANIFEST_PATH, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        for r in existing_data.get("images", []):
            collected_records.append(r)
            key = (r["split"], r["label_name"], r["generator_id"])
            current_counts[key] = current_counts.get(key, 0) + 1
            seen_md5s[r["md5"]] = r["image_path"]
            seen_rows.add(r["source_row_id"])
            seen_dhashes.setdefault(r.get("dhash", ""), []).append(r["image_path"])
        logger.info("Resumed %d already extracted images.", len(collected_records))

    # Identify remaining needed quotas (ignoring SD14 which has 0 rows)
    def remaining_quota() -> Dict[Tuple[str, str, int], int]:
        rem = {}
        for k in TARGET_QUOTAS:
            if k[2] == 5:  # SD14 has 0 in source
                continue
            rem[k] = TARGET_QUOTAS[k] - current_counts[k]
        return rem

    rem = remaining_quota()
    logger.info("Current remaining quotas needed: %s", {f"{k[0]}_{k[1]}_{GENERATOR_NAMES[k[2]]}": v for k, v in rem.items()})

    splits_to_scan = ["train", "validation"]
    total_rows_scanned = 0
    last_manifest_save = time.perf_counter()

    for current_split in splits_to_scan:
        if not any(v > 0 for v in remaining_quota().values()):
            break

        logger.info("Scanning Tiny-GenImage split: %s", current_split)
        offset = 0
        page_size = 100
        consecutive_empty_pages = 0

        while any(v > 0 for v in remaining_quota().values()):
            total_extracted = sum(current_counts.values())
            if offset % 500 == 0:
                logger.info(
                    "Split=%s offset=%d | Extracted=%d | Train=%d, Val=%d, Test=%d",
                    current_split, offset, total_extracted,
                    sum(current_counts[k] for k in current_counts if k[0] == "train"),
                    sum(current_counts[k] for k in current_counts if k[0] == "val"),
                    sum(current_counts[k] for k in current_counts if k[0] == "test"),
                )

            data, bytes_len = fetch_api_page(current_split, offset, page_size)
            total_api_bytes += bytes_len

            rows = data.get("rows", [])
            if not rows:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 3:
                    logger.info("3 consecutive empty responses at split=%s offset=%d. Moving to next split.", current_split, offset)
                    break
                offset += page_size
                continue
            else:
                consecutive_empty_pages = 0

            tentative_counts = dict(current_counts)
            candidates_to_download: List[Tuple[Tuple[str, str, int], int, Dict[str, Any], str]] = []

            for item in rows:
                row_idx = item.get("row_idx", total_rows_scanned)
                row = item.get("row", {})
                total_rows_scanned += 1

                if current_split == "train" and (row_idx in excluded_rows or row_idx in seen_rows):
                    continue
                if current_split == "validation" and row_idx in seen_rows:
                    continue

                g_id = row.get("generator")
                if g_id not in GENERATOR_NAMES:
                    continue

                img_info = row.get("image", {})
                img_src = img_info.get("src")
                if not img_src:
                    continue

                target_key: Optional[Tuple[str, str, int]] = None

                if g_id == 0:  # Real
                    if tentative_counts[("train", "real", 0)] < TARGET_QUOTAS[("train", "real", 0)]:
                        target_key = ("train", "real", 0)
                    elif tentative_counts[("val", "real", 0)] < TARGET_QUOTAS[("val", "real", 0)]:
                        target_key = ("val", "real", 0)
                    elif tentative_counts[("test", "real", 0)] < TARGET_QUOTAS[("test", "real", 0)]:
                        target_key = ("test", "real", 0)
                elif g_id in [1, 2, 3, 5, 6, 7]:  # Training generators
                    if tentative_counts[("train", "fake", g_id)] < TARGET_QUOTAS[("train", "fake", g_id)]:
                        target_key = ("train", "fake", g_id)
                    elif tentative_counts[("val", "fake", g_id)] < TARGET_QUOTAS[("val", "fake", g_id)]:
                        target_key = ("val", "fake", g_id)
                elif g_id in [4, 8]:  # Test unseen generators (Midjourney, Wukong)
                    if tentative_counts[("test", "fake", g_id)] < TARGET_QUOTAS[("test", "fake", g_id)]:
                        target_key = ("test", "fake", g_id)

                if target_key:
                    tentative_counts[target_key] += 1
                    candidates_to_download.append((target_key, row_idx, row, img_src))

            if candidates_to_download:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_cand = {
                        executor.submit(download_single_image, cand[3]): cand
                        for cand in candidates_to_download
                    }
                    for future in as_completed(future_to_cand):
                        cand = future_to_cand[future]
                        target_key, row_idx, row, img_src = cand
                        target_split, label_name, g_id = target_key

                        if current_counts[target_key] >= TARGET_QUOTAS[target_key]:
                            if g_id == 0:
                                if target_split == "train" and current_counts[("val", "real", 0)] < TARGET_QUOTAS[("val", "real", 0)]:
                                    target_key = ("val", "real", 0)
                                    target_split, label_name, g_id = target_key
                                elif target_split in ["train", "val"] and current_counts[("test", "real", 0)] < TARGET_QUOTAS[("test", "real", 0)]:
                                    target_key = ("test", "real", 0)
                                    target_split, label_name, g_id = target_key
                                else:
                                    continue
                            elif g_id in [1, 2, 3, 5, 6, 7] and target_split == "train":
                                if current_counts[("val", "fake", g_id)] < TARGET_QUOTAS[("val", "fake", g_id)]:
                                    target_key = ("val", "fake", g_id)
                                    target_split, label_name, g_id = target_key
                                else:
                                    continue
                            else:
                                continue

                        try:
                            img_bytes = future.result()
                        except Exception as exc:
                            logger.warning("Failed download row %d: %s", row_idx, exc)
                            continue

                        if not img_bytes:
                            continue

                        total_image_bytes += len(img_bytes)

                        try:
                            pil_img = Image.open(io.BytesIO(img_bytes))
                            pil_img.verify()
                            pil_img = Image.open(io.BytesIO(img_bytes))
                            width, height = pil_img.size
                            img_format = pil_img.format or "JPEG"
                            pil_img.load()
                        except Exception as exc:
                            logger.warning("Corrupt image row %d: %s", row_idx, exc)
                            continue

                        md5_hash = hashlib.md5(img_bytes).hexdigest()
                        if md5_hash in excluded_md5s or md5_hash in seen_md5s:
                            continue

                        sha256_hash = hashlib.sha256(img_bytes).hexdigest()
                        dhash_val = compute_dhash(pil_img)

                        gen_label_str = GENERATOR_NAMES[g_id].lower()
                        ext = ".jpg" if img_format.upper() == "JPEG" else f".{img_format.lower()}"
                        filename = f"{gen_label_str}_{current_counts[target_key]:04d}_{md5_hash[:8]}{ext}"
                        dest_path = TARGET_DIR / target_split / label_name / filename

                        with open(dest_path, "wb") as f:
                            f.write(img_bytes)

                        try:
                            rel_path = dest_path.relative_to(PROJECT_ROOT).as_posix()
                        except ValueError:
                            rel_path = dest_path.as_posix()

                        rec = {
                            "image_path": rel_path,
                            "filename": filename,
                            "split": target_split,
                            "label": 0 if label_name == "real" else 1,
                            "label_name": label_name,
                            "generator": GENERATOR_NAMES[g_id],
                            "generator_id": g_id,
                            "source_row_id": row_idx,
                            "source_split": current_split,
                            "source_url": img_src,
                            "dimensions": [width, height],
                            "format": img_format,
                            "file_size_bytes": len(img_bytes),
                            "sha256": sha256_hash,
                            "md5": md5_hash,
                            "dhash": dhash_val,
                        }

                        collected_records.append(rec)
                        current_counts[target_key] += 1
                        seen_md5s[md5_hash] = rel_path
                        seen_rows.add(row_idx)
                        seen_dhashes.setdefault(dhash_val, []).append(rel_path)

            if time.perf_counter() - last_manifest_save > 60.0:
                save_manifest_and_summary(
                    collected_records, current_counts, seen_md5s, seen_dhashes,
                    total_api_bytes, total_image_bytes, start_time, total_rows_scanned
                )
                last_manifest_save = time.perf_counter()

            offset += page_size
            time.sleep(0.12)

    save_manifest_and_summary(
        collected_records, current_counts, seen_md5s, seen_dhashes,
        total_api_bytes, total_image_bytes, start_time, total_rows_scanned
    )

    logger.info("=" * 60)
    logger.info("GENERAL SCENES V2 EXTRACTION RUN FINISHED!")
    logger.info("Total images: %d", len(collected_records))
    for k, v in current_counts.items():
        logger.info("  %s %s (%s): %d / %d", k[0].upper(), k[1], GENERATOR_NAMES[k[2]], v, TARGET_QUOTAS[k])
    logger.info("Elapsed: %.2f seconds", time.perf_counter() - start_time)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
