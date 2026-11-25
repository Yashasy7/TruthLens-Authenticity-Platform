"""
TruthLens AI/ML — Photographic Dataset Pilot Extractor
Extracts a focused pilot subset (200 Real, 100 Midjourney, 100 SD15 = 400 images)
from TheKernel01/Tiny-GenImage via the Hugging Face Serverless Dataset API without
downloading full multi-gigabyte Parquet shards.

Records full metadata, exact checksums, perceptual hashes, and verifies data integrity.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Set, Tuple

from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.photographic_pilot")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_PILOT_DIR = PROJECT_ROOT / "ai-ml" / "data" / "expanded_image_detection" / "photographic_pilot"

# Target quotas
TARGET_QUOTAS = {
    0: {"name": "Real", "quota": 200, "label": 0, "subfolder": "real", "source": "GenImage (ImageNet-1k Real)"},
    4: {"name": "Midjourney", "quota": 100, "label": 1, "subfolder": "midjourney", "source": "GenImage (Midjourney Fake)"},
    6: {"name": "SD15", "quota": 100, "label": 1, "subfolder": "sd15", "source": "GenImage (Stable Diffusion v1.5 Fake)"},
}

API_BASE = "https://datasets-server.huggingface.co/rows?dataset=TheKernel01/Tiny-GenImage&config=default&split=train"


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


def fetch_api_page(offset: int, length: int = 100, max_retries: int = 3) -> Tuple[Dict[str, Any], int]:
    """Fetch one page of rows from the Hugging Face serverless API."""
    url = f"{API_BASE}&offset={offset}&length={length}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TruthLens-Photographic-Pilot/1.0"}
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8")), len(data)
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            time.sleep(2.0 * (attempt + 1))
    return {}, 0


def download_image_bytes(url: str, max_retries: int = 3) -> bytes:
    """Download image bytes from CDN presigned URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TruthLens-Photographic-Pilot/1.0"}
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    return b""


def main():
    start_time = time.perf_counter()
    logger.info("Initializing Photographic Dataset Pilot in %s", TARGET_PILOT_DIR)

    for cfg in TARGET_QUOTAS.values():
        (TARGET_PILOT_DIR / cfg["subfolder"]).mkdir(parents=True, exist_ok=True)

    counts = {g: 0 for g in TARGET_QUOTAS}
    collected_records: List[Dict[str, Any]] = []
    seen_md5s: Dict[str, str] = {}
    seen_dhashes: Dict[str, List[str]] = {}

    total_api_bytes = 0
    total_image_bytes = 0

    offset = 0
    page_size = 100
    rows_inspected = 0

    all_quotas_filled = False

    while not all_quotas_filled:
        logger.info(
            "Fetching API page offset=%d (Current counts: Real=%d/%d, Midjourney=%d/%d, SD15=%d/%d)",
            offset,
            counts[0], TARGET_QUOTAS[0]["quota"],
            counts[4], TARGET_QUOTAS[4]["quota"],
            counts[6], TARGET_QUOTAS[6]["quota"],
        )

        try:
            data, bytes_len = fetch_api_page(offset, page_size)
            total_api_bytes += bytes_len
        except Exception as exc:
            logger.error("Failed to fetch page at offset %d: %s", offset, exc)
            break

        rows = data.get("rows", [])
        if not rows:
            logger.warning("No more rows returned by API at offset %d", offset)
            break

        for item in rows:
            row_idx = item.get("row_idx", rows_inspected)
            row = item.get("row", {})
            rows_inspected += 1

            g_id = row.get("generator")
            if g_id not in TARGET_QUOTAS:
                continue

            cfg = TARGET_QUOTAS[g_id]
            if counts[g_id] >= cfg["quota"]:
                continue

            img_info = row.get("image", {})
            img_src = img_info.get("src")
            if not img_src:
                continue

            # Download actual image
            try:
                img_data = download_image_bytes(img_src)
                total_image_bytes += len(img_data)
            except Exception as exc:
                logger.warning("Failed to download image for row %d: %s", row_idx, exc)
                continue

            # Verify readability and extract metadata
            try:
                pil_img = Image.open(io.BytesIO(img_data))
                pil_img.verify()
                # Re-open for attributes and loading
                pil_img = Image.open(io.BytesIO(img_data))
                width, height = pil_img.size
                img_format = pil_img.format or "JPEG"
                pil_img.load()
            except Exception as exc:
                logger.warning("Corrupted image in row %d: %s", row_idx, exc)
                continue

            md5_hash = hashlib.md5(img_data).hexdigest()
            sha256_hash = hashlib.sha256(img_data).hexdigest()
            dhash_val = compute_dhash(pil_img)

            # Determine file extension
            ext = ".jpg" if img_format.upper() == "JPEG" else f".{img_format.lower()}"
            filename = f"{cfg['subfolder']}_{counts[g_id]:04d}_{md5_hash[:8]}{ext}"
            file_path = TARGET_PILOT_DIR / cfg["subfolder"] / filename

            with open(file_path, "wb") as f:
                f.write(img_data)

            counts[g_id] += 1

            # Duplicate tracking
            if md5_hash in seen_md5s:
                logger.warning("Exact MD5 duplicate found: %s with %s", file_path.name, seen_md5s[md5_hash])
            seen_md5s[md5_hash] = filename
            seen_dhashes.setdefault(dhash_val, []).append(filename)

            try:
                rel_path = file_path.relative_to(PROJECT_ROOT).as_posix()
            except ValueError:
                rel_path = file_path.as_posix()

            record = {
                "image_path": rel_path,
                "label": cfg["label"],
                "label_name": "real" if cfg["label"] == 0 else "fake",
                "generator": cfg["name"],
                "generator_id": g_id,
                "source_dataset": "TheKernel01/Tiny-GenImage",
                "original_source": cfg["source"],
                "content_category": "photographic_objects_and_scenes",
                "domain": "photographic_pilot",
                "original_split": "train",
                "huggingface_row_idx": row_idx,
                "dimensions": [width, height],
                "format": img_format,
                "file_size_bytes": len(img_data),
                "md5": md5_hash,
                "sha256": sha256_hash,
                "dhash": dhash_val,
            }
            collected_records.append(record)

            if all(counts[g] >= TARGET_QUOTAS[g]["quota"] for g in TARGET_QUOTAS):
                all_quotas_filled = True
                break

        offset += page_size

    elapsed = time.perf_counter() - start_time
    logger.info("Extraction finished in %.2f seconds", elapsed)

    # Calculate actual disk usage
    saved_files = list(TARGET_PILOT_DIR.glob("**/*.*"))
    disk_bytes = sum(f.stat().st_size for f in saved_files)

    # Perceptual duplicates summary
    perceptual_dupes = {k: v for k, v in seen_dhashes.items() if len(v) > 1}

    manifest_payload = {
        "dataset_name": "TruthLens-Photographic-Pilot",
        "description": "Small photographic evaluation pilot extracted from TheKernel01/Tiny-GenImage",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_directory": str(TARGET_PILOT_DIR),
        "license": "CC BY-NC-SA 4.0 (GenImage) / Non-commercial research only (ImageNet-1k)",
        "source_repository": "https://huggingface.co/datasets/TheKernel01/Tiny-GenImage",
        "statistics": {
            "total_images": len(collected_records),
            "rows_scanned": rows_inspected,
            "counts_by_generator": {cfg["name"]: counts[g] for g, cfg in TARGET_QUOTAS.items()},
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

    manifest_file = TARGET_PILOT_DIR / "pilot_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    logger.info("Saved pilot manifest to %s", manifest_file)
    logger.info(
        "Summary: %d images collected (Real: %d, Midjourney: %d, SD15: %d) | Downloaded: %.2f MB | Disk: %.2f MB",
        len(collected_records),
        counts[0], counts[4], counts[6],
        (total_api_bytes + total_image_bytes) / (1024 * 1024),
        disk_bytes / (1024 * 1024),
    )


if __name__ == "__main__":
    main()
