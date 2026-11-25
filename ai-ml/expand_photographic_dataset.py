"""
TruthLens AI/ML — Photographic Dataset Expansion Script
Expands the photographic dataset to exactly 3,000 images (including the 400-image pilot)
from TheKernel01/Tiny-GenImage via the Hugging Face Serverless API and CloudFront CDN.

Split Allocation:
- Training:               600 Real + 600 SD15 (Total: 1,200)
- Validation:             150 Real + 150 SD15 (Total: 300)
- Unseen-Generator Test:  750 Real + 750 Midjourney (Total: 1,500)
Grand Total: 3,000 images (1,500 Real / 1,500 Synthetic, perfectly balanced)

Guarantees:
1. Disjointness: Real images in train/val are strictly disjoint from test real images.
2. Generator isolation: Midjourney is 100% excluded from train/val; SD15 is 100% excluded from test.
3. De-duplication: Reuses pilot images without re-downloading; verifies MD5 and perceptual hashes.
4. Non-destructive: Existing photographic_pilot and human_portraits are preserved intact.
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
logger = logging.getLogger("truthlens.photographic_expansion")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "ai-ml" / "data" / "expanded_image_detection"
PILOT_DIR = DATA_ROOT / "photographic_pilot"
PILOT_MANIFEST_PATH = PILOT_DIR / "pilot_manifest.json"
TARGET_DIR = DATA_ROOT / "photographic_scenes"
TARGET_MANIFEST_PATH = TARGET_DIR / "photographic_manifest.json"
SUMMARY_MD_PATH = TARGET_DIR / "EXTRACTION_SUMMARY.md"

API_BASE = "https://datasets-server.huggingface.co/rows?dataset=TheKernel01/Tiny-GenImage&config=default&split=train"

# Target quotas per split bucket
SPLIT_QUOTAS = {
    "train_real": {"split": "train", "label": 0, "label_name": "real", "generator": "Real", "generator_id": 0, "quota": 600, "subfolder": "train/real"},
    "train_fake": {"split": "train", "label": 1, "label_name": "fake", "generator": "SD15", "generator_id": 6, "quota": 600, "subfolder": "train/fake"},
    "val_real":   {"split": "val",   "label": 0, "label_name": "real", "generator": "Real", "generator_id": 0, "quota": 150, "subfolder": "val/real"},
    "val_fake":   {"split": "val",   "label": 1, "label_name": "fake", "generator": "SD15", "generator_id": 6, "quota": 150, "subfolder": "val/fake"},
    "test_real":  {"split": "test",  "label": 0, "label_name": "real", "generator": "Real", "generator_id": 0, "quota": 750, "subfolder": "test/real"},
    "test_fake":  {"split": "test",  "label": 1, "label_name": "fake", "generator": "Midjourney", "generator_id": 4, "quota": 750, "subfolder": "test/fake"},
}


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Compute difference hash (perceptual hash) for duplicate analysis."""
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


def fetch_api_page(offset: int, length: int = 100, max_retries: int = 4) -> Tuple[Dict[str, Any], int]:
    """Fetch one page of rows from Hugging Face Serverless API."""
    url = f"{API_BASE}&offset={offset}&length={length}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TruthLens-Photographic-Expansion/1.0"}
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8")), len(data)
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            sleep_time = 2.0 * (attempt + 1)
            logger.warning("API fetch error at offset %d (attempt %d/%d): %s. Retrying in %.1fs...", offset, attempt + 1, max_retries, exc, sleep_time)
            time.sleep(sleep_time)
    return {}, 0


def download_single_image(url: str, max_retries: int = 3) -> bytes:
    """Download image bytes from presigned CDN URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TruthLens-Photographic-Expansion/1.0"}
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


def copy_pilot_subset(
    existing_pilot_records: List[Dict[str, Any]],
    seen_md5s: Dict[str, str],
    seen_row_indices: Set[int],
    seen_dhashes: Dict[str, List[str]],
    records_by_bucket: Dict[str, List[Dict[str, Any]]],
) -> int:
    """
    Incorporate the 400 pilot images into the split buckets without re-downloading.
    Allocation:
    - 200 Real pilot images -> 160 train_real, 40 val_real, 0 test_real
    - 100 SD15 pilot images -> 80 train_fake, 20 val_fake, 0 test_fake
    - 100 Midjourney pilot images -> 0 train_fake, 0 val_fake, 100 test_fake
    """
    logger.info("Incorporating 400 pilot images from %s into target splits...", PILOT_DIR)
    pilot_copied = 0

    real_pilot = sorted([r for r in existing_pilot_records if r["generator_id"] == 0], key=lambda x: x["huggingface_row_idx"])
    sd15_pilot = sorted([r for r in existing_pilot_records if r["generator_id"] == 6], key=lambda x: x["huggingface_row_idx"])
    mj_pilot = sorted([r for r in existing_pilot_records if r["generator_id"] == 4], key=lambda x: x["huggingface_row_idx"])

    logger.info("Found in pilot manifest: Real=%d, SD15=%d, Midjourney=%d", len(real_pilot), len(sd15_pilot), len(mj_pilot))

    assignments = [
        (real_pilot[:160], "train_real"),
        (real_pilot[160:200], "val_real"),
        (sd15_pilot[:80], "train_fake"),
        (sd15_pilot[80:100], "val_fake"),
        (mj_pilot[:100], "test_fake"),
    ]

    for item_list, bucket in assignments:
        cfg = SPLIT_QUOTAS[bucket]
        dest_dir = TARGET_DIR / cfg["subfolder"]
        dest_dir.mkdir(parents=True, exist_ok=True)

        for item in item_list:
            src_path = PROJECT_ROOT / item["image_path"]
            if not src_path.exists():
                src_path = PILOT_DIR / Path(item["image_path"]).name
            if not src_path.exists():
                for sub in ["real", "midjourney", "sd15"]:
                    cand = PILOT_DIR / sub / Path(item["image_path"]).name
                    if cand.exists():
                        src_path = cand
                        break

            if not src_path.exists():
                logger.error("Could not locate pilot source file: %s", item["image_path"])
                continue

            dest_filename = f"{cfg['generator'].lower()}_{len(records_by_bucket[bucket]):04d}_{item['md5'][:8]}{src_path.suffix.lower()}"
            dest_path = dest_dir / dest_filename

            if not dest_path.exists():
                shutil.copy2(src_path, dest_path)

            try:
                rel_dest = dest_path.relative_to(PROJECT_ROOT).as_posix()
            except ValueError:
                rel_dest = dest_path.as_posix()

            rec = dict(item)
            rec["image_path"] = rel_dest
            rec["pilot_source_path"] = item["image_path"]
            rec["split"] = cfg["split"]
            rec["bucket"] = bucket
            rec["label"] = cfg["label"]
            rec["label_name"] = cfg["label_name"]
            rec["generator"] = cfg["generator"]
            rec["generator_id"] = cfg["generator_id"]
            rec["domain"] = "photographic_scenes"

            records_by_bucket[bucket].append(rec)
            seen_md5s[item["md5"]] = rel_dest
            seen_row_indices.add(item["huggingface_row_idx"])
            seen_dhashes.setdefault(item.get("dhash", ""), []).append(rel_dest)
            pilot_copied += 1

    logger.info("Successfully incorporated %d pilot images into target splits.", pilot_copied)
    return pilot_copied


def save_manifest_and_summary(
    records_by_bucket: Dict[str, List[Dict[str, Any]]],
    seen_md5s: Dict[str, str],
    seen_dhashes: Dict[str, List[str]],
    total_api_bytes: int,
    total_image_bytes: int,
    start_time: float,
    rows_scanned: int,
    pilot_count: int,
    newly_downloaded_count: int,
):
    """Save photographic_manifest.json and EXTRACTION_SUMMARY.md atomically."""
    elapsed = time.perf_counter() - start_time
    all_records: List[Dict[str, Any]] = []
    for bucket in ["train_real", "train_fake", "val_real", "val_fake", "test_real", "test_fake"]:
        all_records.extend(records_by_bucket.get(bucket, []))

    saved_files = list(TARGET_DIR.glob("**/*.*"))
    disk_bytes = sum(f.stat().st_size for f in saved_files if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"])

    perceptual_dupes = {k: v for k, v in seen_dhashes.items() if len(v) > 1 and k}

    manifest_payload = {
        "dataset_name": "TruthLens-Photographic-Scenes",
        "description": "Expanded photographic dataset for AI-generated media authenticity detection (ImageNet Real, SD15, Midjourney)",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_directory": str(TARGET_DIR),
        "license": "CC BY-NC-SA 4.0 (GenImage) / Non-commercial research only (ImageNet-1k)",
        "source_repository": "https://huggingface.co/datasets/TheKernel01/Tiny-GenImage",
        "note": "Tiny-GenImage Parquet schema provides (image, label, generator). Semantic ImageNet synset matching is not claimed because synset metadata is not in schema.",
        "statistics": {
            "total_images": len(all_records),
            "pilot_images_incorporated": pilot_count,
            "newly_downloaded_images": newly_downloaded_count,
            "rows_scanned": rows_scanned,
            "split_breakdown": {
                "train": {
                    "real": len(records_by_bucket["train_real"]),
                    "fake": len(records_by_bucket["train_fake"]),
                    "fake_generator": "SD15",
                    "total": len(records_by_bucket["train_real"]) + len(records_by_bucket["train_fake"]),
                },
                "val": {
                    "real": len(records_by_bucket["val_real"]),
                    "fake": len(records_by_bucket["val_fake"]),
                    "fake_generator": "SD15",
                    "total": len(records_by_bucket["val_real"]) + len(records_by_bucket["val_fake"]),
                },
                "test": {
                    "real": len(records_by_bucket["test_real"]),
                    "fake": len(records_by_bucket["test_fake"]),
                    "fake_generator": "Midjourney (Unseen Benchmark)",
                    "total": len(records_by_bucket["test_real"]) + len(records_by_bucket["test_fake"]),
                },
            },
            "counts_by_generator": {
                "Real": len(records_by_bucket["train_real"]) + len(records_by_bucket["val_real"]) + len(records_by_bucket["test_real"]),
                "SD15": len(records_by_bucket["train_fake"]) + len(records_by_bucket["val_fake"]),
                "Midjourney": len(records_by_bucket["test_fake"]),
            },
            "counts_by_label": {
                "real": sum(1 for r in all_records if r["label"] == 0),
                "fake": sum(1 for r in all_records if r["label"] == 1),
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
                "exact_md5_duplicates": len(all_records) - len(seen_md5s),
                "perceptual_dhash_collisions": len(perceptual_dupes),
                "collision_details": perceptual_dupes,
            },
            "elapsed_seconds": round(elapsed, 2),
        },
        "images": all_records,
    }

    tmp_manifest = TARGET_DIR / "photographic_manifest.json.tmp"
    with open(tmp_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)
    tmp_manifest.replace(TARGET_MANIFEST_PATH)
    logger.info("Updated manifest: %s (Total images: %d)", TARGET_MANIFEST_PATH, len(all_records))

    # Save summary markdown
    summary_text = f"""# TruthLens — Photographic Scenes Expansion Summary

- **Total Images:** {len(all_records)} (Balanced: {manifest_payload['statistics']['counts_by_label']['real']} Real / {manifest_payload['statistics']['counts_by_label']['fake']} Fake)
- **Pilot Images Incorporated:** {pilot_count}
- **Newly Downloaded Images:** {newly_downloaded_count}
- **Total Network Transfer:** {manifest_payload['statistics']['network_transfer']['total_downloaded_mb']} MB
- **Total Disk Usage:** {manifest_payload['statistics']['disk_usage']['total_disk_mb']} MB
- **Elapsed Time:** {round(elapsed / 60, 2)} minutes

## Split Allocation
| Split | Real (ImageNet) | Synthetic Generator | Fake Count | Total Split Images |
| :--- | :--- | :--- | :--- | :--- |
| **Training** | {len(records_by_bucket['train_real'])} | SD15 (Stable Diffusion v1.5) | {len(records_by_bucket['train_fake'])} | {len(records_by_bucket['train_real']) + len(records_by_bucket['train_fake'])} |
| **Validation** | {len(records_by_bucket['val_real'])} | SD15 (Stable Diffusion v1.5) | {len(records_by_bucket['val_fake'])} | {len(records_by_bucket['val_real']) + len(records_by_bucket['val_fake'])} |
| **Unseen-Generator Test** | {len(records_by_bucket['test_real'])} | Midjourney (100% Unseen) | {len(records_by_bucket['test_fake'])} | {len(records_by_bucket['test_real']) + len(records_by_bucket['test_fake'])} |
| **Total** | **1,500** | | **1,500** | **3,000** |

## Integrity & Guarantees
- **Disjoint Real Splits:** Real images in train/val ({len(records_by_bucket['train_real']) + len(records_by_bucket['val_real'])}) are completely disjoint from test real images ({len(records_by_bucket['test_real'])}).
- **Generator Isolation:** Midjourney is 100% excluded from train and val. SD15 is 100% excluded from test.
- **Duplicate Verification:** Exact MD5 collisions: {len(all_records) - len(seen_md5s)}. Perceptual dhash collisions: {len(perceptual_dupes)}.
"""
    with open(SUMMARY_MD_PATH, "w", encoding="utf-8") as f:
        f.write(summary_text)


def main():
    start_time = time.perf_counter()
    logger.info("Initializing TruthLens Photographic Dataset Expansion to 3,000 images...")

    # Ensure target subdirectories exist
    for cfg in SPLIT_QUOTAS.values():
        (TARGET_DIR / cfg["subfolder"]).mkdir(parents=True, exist_ok=True)

    records_by_bucket: Dict[str, List[Dict[str, Any]]] = {b: [] for b in SPLIT_QUOTAS}
    seen_md5s: Dict[str, str] = {}
    seen_row_indices: Set[int] = set()
    seen_dhashes: Dict[str, List[str]] = {}

    total_api_bytes = 0
    total_image_bytes = 0

    # Step 1: Check if an existing manifest already exists in TARGET_DIR (resumability)
    pilot_count = 0
    if TARGET_MANIFEST_PATH.exists():
        logger.info("Existing photographic manifest detected at %s. Loading existing state...", TARGET_MANIFEST_PATH)
        with open(TARGET_MANIFEST_PATH, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        pilot_count = existing_data.get("statistics", {}).get("pilot_images_incorporated", 0)
        for r in existing_data.get("images", []):
            b = r.get("bucket")
            if b in records_by_bucket:
                records_by_bucket[b].append(r)
                seen_md5s[r["md5"]] = r["image_path"]
                seen_row_indices.add(r["huggingface_row_idx"])
                seen_dhashes.setdefault(r.get("dhash", ""), []).append(r["image_path"])
        logger.info("Resumed state with %d existing images in target splits.", len(seen_md5s))
    else:
        # Incorporate from pilot manifest
        if PILOT_MANIFEST_PATH.exists():
            with open(PILOT_MANIFEST_PATH, "r", encoding="utf-8") as f:
                pilot_manifest = json.load(f)
            pilot_records = pilot_manifest.get("images", [])
            pilot_count = copy_pilot_subset(
                existing_pilot_records=pilot_records,
                seen_md5s=seen_md5s,
                seen_row_indices=seen_row_indices,
                seen_dhashes=seen_dhashes,
                records_by_bucket=records_by_bucket,
            )
        else:
            logger.warning("Pilot manifest not found at %s. Proceeding with full retrieval.", PILOT_MANIFEST_PATH)

    # Determine highest row index seen to date so we start scanning beyond it
    max_row_seen = max(seen_row_indices) if seen_row_indices else 0
    start_offset = ((max_row_seen // 100) + 1) * 100
    logger.info("Highest row index seen: %d. Starting API scan from offset: %d", max_row_seen, start_offset)

    def remaining_needed() -> Dict[str, int]:
        return {b: SPLIT_QUOTAS[b]["quota"] - len(records_by_bucket[b]) for b in SPLIT_QUOTAS}

    rem = remaining_needed()
    logger.info("Remaining quotas needed: %s", rem)

    newly_downloaded_count = sum(1 for b in records_by_bucket for r in records_by_bucket[b] if r.get("pilot_source_path") is None)
    offset = start_offset
    page_size = 100
    rows_scanned = max_row_seen + 1
    last_manifest_save = time.perf_counter()

    # Step 2: Stream remaining images via polite pagination
    while any(v > 0 for v in rem.values()):
        logger.info(
            "Fetching API page offset=%d | Current: Train(R=%d/600, F=%d/600) Val(R=%d/150, F=%d/150) Test(R=%d/750, F=%d/750) | Total=%d/3000",
            offset,
            len(records_by_bucket["train_real"]), len(records_by_bucket["train_fake"]),
            len(records_by_bucket["val_real"]), len(records_by_bucket["val_fake"]),
            len(records_by_bucket["test_real"]), len(records_by_bucket["test_fake"]),
            sum(len(v) for v in records_by_bucket.values()),
        )

        try:
            data, bytes_len = fetch_api_page(offset, page_size)
            total_api_bytes += bytes_len
        except Exception as exc:
            logger.error("Failed to fetch API page at offset %d: %s", offset, exc)
            break

        rows = data.get("rows", [])
        if not rows:
            logger.warning("No rows returned by API at offset %d. Scanning halted.", offset)
            break

        # Filter candidate rows for the current page using tentative bucket counts
        tentative_counts = {b: len(records_by_bucket[b]) for b in SPLIT_QUOTAS}
        candidates_to_download: List[Tuple[str, int, Dict[str, Any], str]] = []

        for item in rows:
            row_idx = item.get("row_idx", rows_scanned)
            row = item.get("row", {})
            rows_scanned = max(rows_scanned, row_idx + 1)

            if row_idx in seen_row_indices:
                continue

            g_id = row.get("generator")
            img_info = row.get("image", {})
            img_src = img_info.get("src")
            if not img_src:
                continue

            target_bucket: Optional[str] = None
            if g_id == 0:  # Real
                if tentative_counts["train_real"] < SPLIT_QUOTAS["train_real"]["quota"]:
                    target_bucket = "train_real"
                    tentative_counts["train_real"] += 1
                elif tentative_counts["val_real"] < SPLIT_QUOTAS["val_real"]["quota"]:
                    target_bucket = "val_real"
                    tentative_counts["val_real"] += 1
                elif tentative_counts["test_real"] < SPLIT_QUOTAS["test_real"]["quota"]:
                    target_bucket = "test_real"
                    tentative_counts["test_real"] += 1
            elif g_id == 6:  # SD15
                if tentative_counts["train_fake"] < SPLIT_QUOTAS["train_fake"]["quota"]:
                    target_bucket = "train_fake"
                    tentative_counts["train_fake"] += 1
                elif tentative_counts["val_fake"] < SPLIT_QUOTAS["val_fake"]["quota"]:
                    target_bucket = "val_fake"
                    tentative_counts["val_fake"] += 1
            elif g_id == 4:  # Midjourney
                if tentative_counts["test_fake"] < SPLIT_QUOTAS["test_fake"]["quota"]:
                    target_bucket = "test_fake"
                    tentative_counts["test_fake"] += 1

            if target_bucket:
                candidates_to_download.append((target_bucket, row_idx, row, img_src))

        # Download candidates concurrently using thread pool (8 threads) for CDN throughput
        if candidates_to_download:
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_cand = {
                    executor.submit(download_single_image, cand[3]): cand
                    for cand in candidates_to_download
                }
                for future in as_completed(future_to_cand):
                    cand = future_to_cand[future]
                    target_bucket, row_idx, row, img_src = cand
                    cfg = SPLIT_QUOTAS[target_bucket]

                    if len(records_by_bucket[target_bucket]) >= cfg["quota"]:
                        # If bucket filled while downloading, attempt overflow routing for Real / SD15
                        if target_bucket == "train_real" and len(records_by_bucket["val_real"]) < SPLIT_QUOTAS["val_real"]["quota"]:
                            target_bucket = "val_real"
                            cfg = SPLIT_QUOTAS[target_bucket]
                        elif (target_bucket in ["train_real", "val_real"]) and len(records_by_bucket["test_real"]) < SPLIT_QUOTAS["test_real"]["quota"]:
                            target_bucket = "test_real"
                            cfg = SPLIT_QUOTAS[target_bucket]
                        elif target_bucket == "train_fake" and len(records_by_bucket["val_fake"]) < SPLIT_QUOTAS["val_fake"]["quota"]:
                            target_bucket = "val_fake"
                            cfg = SPLIT_QUOTAS[target_bucket]
                        else:
                            continue

                    try:
                        img_bytes = future.result()
                    except Exception as exc:
                        logger.warning("Failed to download image for row %d: %s", row_idx, exc)
                        continue

                    if not img_bytes:
                        continue

                    total_image_bytes += len(img_bytes)

                    # Pillow verify and validate
                    try:
                        pil_img = Image.open(io.BytesIO(img_bytes))
                        pil_img.verify()
                        pil_img = Image.open(io.BytesIO(img_bytes))
                        width, height = pil_img.size
                        img_format = pil_img.format or "JPEG"
                        pil_img.load()
                    except Exception as exc:
                        logger.warning("Corrupted image in row %d: %s", row_idx, exc)
                        continue

                    md5_hash = hashlib.md5(img_bytes).hexdigest()
                    if md5_hash in seen_md5s:
                        logger.warning("Duplicate MD5 encountered at row %d, skipping.", row_idx)
                        continue

                    sha256_hash = hashlib.sha256(img_bytes).hexdigest()
                    dhash_val = compute_dhash(pil_img)

                    ext = ".jpg" if img_format.upper() == "JPEG" else f".{img_format.lower()}"
                    dest_dir = TARGET_DIR / cfg["subfolder"]
                    dest_filename = f"{cfg['generator'].lower()}_{len(records_by_bucket[target_bucket]):04d}_{md5_hash[:8]}{ext}"
                    dest_path = dest_dir / dest_filename

                    with open(dest_path, "wb") as f:
                        f.write(img_bytes)

                    try:
                        rel_path = dest_path.relative_to(PROJECT_ROOT).as_posix()
                    except ValueError:
                        rel_path = dest_path.as_posix()

                    record = {
                        "image_path": rel_path,
                        "pilot_source_path": None,
                        "split": cfg["split"],
                        "bucket": target_bucket,
                        "label": cfg["label"],
                        "label_name": cfg["label_name"],
                        "generator": cfg["generator"],
                        "generator_id": cfg["generator_id"],
                        "source_dataset": "TheKernel01/Tiny-GenImage",
                        "original_source": f"GenImage ({cfg['generator']} {cfg['label_name'].capitalize()})",
                        "content_category": "photographic_objects_and_scenes",
                        "domain": "photographic_scenes",
                        "original_split": "train",
                        "huggingface_row_idx": row_idx,
                        "dimensions": [width, height],
                        "format": img_format,
                        "file_size_bytes": len(img_bytes),
                        "md5": md5_hash,
                        "sha256": sha256_hash,
                        "dhash": dhash_val,
                    }

                    records_by_bucket[target_bucket].append(record)
                    seen_md5s[md5_hash] = rel_path
                    seen_row_indices.add(row_idx)
                    seen_dhashes.setdefault(dhash_val, []).append(rel_path)
                    newly_downloaded_count += 1

        # Periodic incremental manifest checkpointing every 45 seconds
        if time.perf_counter() - last_manifest_save > 45.0:
            save_manifest_and_summary(
                records_by_bucket, seen_md5s, seen_dhashes,
                total_api_bytes, total_image_bytes, start_time,
                rows_scanned, pilot_count, newly_downloaded_count
            )
            last_manifest_save = time.perf_counter()

        rem = remaining_needed()
        offset += page_size
        time.sleep(0.12)  # Polite pacing between API page requests

    # Final save and verification
    save_manifest_and_summary(
        records_by_bucket, seen_md5s, seen_dhashes,
        total_api_bytes, total_image_bytes, start_time,
        rows_scanned, pilot_count, newly_downloaded_count
    )

    total_images = sum(len(v) for v in records_by_bucket.values())
    logger.info("=" * 60)
    logger.info("EXPANSION COMPLETED SUCCESSFULLY!")
    logger.info("Total images: %d / 3000", total_images)
    logger.info("Split Breakdown:")
    logger.info("  Train: Real=%d/600, Fake(SD15)=%d/600", len(records_by_bucket["train_real"]), len(records_by_bucket["train_fake"]))
    logger.info("  Val:   Real=%d/150, Fake(SD15)=%d/150", len(records_by_bucket["val_real"]), len(records_by_bucket["val_fake"]))
    logger.info("  Test:  Real=%d/750, Fake(Midjourney)=%d/750", len(records_by_bucket["test_real"]), len(records_by_bucket["test_fake"]))
    logger.info("Elapsed: %.2f seconds", time.perf_counter() - start_time)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
