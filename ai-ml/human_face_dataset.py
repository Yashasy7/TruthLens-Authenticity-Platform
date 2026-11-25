"""
TruthLens AI/ML — Stage 1: Human-Face 3-Class Dataset Preparation Pipeline

Prepares leakage-free, hash-verified training/validation/test manifests and
optional materialized folders for human-face authenticity classification:
    0 -> genuine       (Genuine photographic human face)
    1 -> ai_generated  (Synthetic GAN or diffusion whole-face generation)
    2 -> manipulated   (Face swap or facial reenactment / alteration)

Design guarantees:
- Production inference (`services/image_analysis/`) is untouched.
- Never infers 3-class labels from binary 0/1 targets alone. All samples MUST
  resolve through explicit, verified source-subset / generation-method mapping.
- Ambiguous attribute-editing / inpainting subsets (e.g., AttGAN, StarGAN, STGAN,
  Palette, SD Inpainting) are quarantined/excluded by default rather than guessed.
- Paired real/fake clips and actor identities (FF++, Celeb-DF-v2) share canonical
  source-group identifiers so related videos/identities never span splits, and real
  identities paired with held-out unseen test datasets move cleanly with test.
- Enforces exact (`sha256`), perceptual Hamming-distance (`dhash <= threshold`),
  and deterministic order-independent deduplication that preserves unseen-test items.
- Reports explicit quota shortfalls and never silently underfills or splits atomic
  identity/video groups.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import re
import shutil
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthlens.human_face_dataset")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_ML_ROOT = Path(__file__).resolve().parent

CLASS_NAMES: Tuple[str, str, str] = ("genuine", "ai_generated", "manipulated")
CLASS_TO_ID: Dict[str, int] = {name: idx for idx, name in enumerate(CLASS_NAMES)}
ID_TO_CLASS: Dict[int, str] = {idx: name for idx, name in enumerate(CLASS_NAMES)}

VALID_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Canonical subset / generator taxonomy registry.
# Keys are normalized lowercase tokens (`re.sub(r"[^a-z0-9]+", "_", token.lower()).strip("_")`).
# Note: Short collision-prone tokens such as `"if"` are NOT registered here for path matching;
# `"if"` is accepted only as an exact explicit method field or exact `"IF"` uppercase folder.
VERIFIED_SUBSET_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- Class 0: Verified Genuine Human Face Sources ---
    "ffhq": {"class_name": "genuine", "family": "real_flickr", "requires_real_target": True},
    "celeba": {"class_name": "genuine", "family": "real_celebrity", "requires_real_target": True},
    "celeba_hq": {"class_name": "genuine", "family": "real_celebrity", "requires_real_target": True},
    "imdb_wiki": {"class_name": "genuine", "family": "real_web_portrait", "requires_real_target": True},
    "real": {"class_name": "genuine", "family": "real_verified", "requires_real_target": True},
    "original": {"class_name": "genuine", "family": "real_verified", "requires_real_target": True},
    "original_sequences": {"class_name": "genuine", "family": "ffpp_real", "container": "ff_pp", "requires_real_target": True},
    "youtube_real": {"class_name": "genuine", "family": "video_real", "requires_real_target": True},
    "celeb_real": {"class_name": "genuine", "family": "celebdf_real", "container": "celeb_df_v2", "requires_real_target": True},
    "ffpp_real": {"class_name": "genuine", "family": "ffpp_real", "container": "ff_pp", "requires_real_target": True},
    "dfdc_real": {"class_name": "genuine", "family": "dfdc_real", "container": "dfdc", "requires_real_target": True},
    "dfd_real": {"class_name": "genuine", "family": "dfd_real", "container": "dfd", "requires_real_target": True},
    "celeb_df_real": {"class_name": "genuine", "family": "celebdf_real", "container": "celeb_df", "requires_real_target": True},
    "celeb_df_v2_real": {"class_name": "genuine", "family": "celebdf_real", "container": "celeb_df_v2", "requires_real_target": True},
    # --- Class 1: Pure AI-Generated Human Faces (GANs) ---
    "stylegan": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "stylegan2": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "stylegan3": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "progan": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "mmdgan": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "msggan": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "msg_gan": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "sngan": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    "vqgan": {"class_name": "ai_generated", "family": "gan", "requires_fake_target": True},
    # --- Class 1: Pure AI-Generated Human Faces (Diffusion / T2I) ---
    "latent_diffusion": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "ldm": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "stable_diffusion": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "stable_diffusion_v1_5": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "sdv1_5": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "sd15": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "sdxl": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "dalle2": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "dall_e_2": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "deepfloyd_if": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "midjourney": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "dcface": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "ddim": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    "ddpm": {"class_name": "ai_generated", "family": "diffusion", "requires_fake_target": True},
    # --- Class 2: Manipulated Human Faces (Face Swap / Reenactment) ---
    "deepfakes": {"class_name": "manipulated", "family": "face_swap_video", "container": "ff_pp", "requires_fake_target": True},
    "faceswap": {"class_name": "manipulated", "family": "face_swap_video", "container": "ff_pp", "requires_fake_target": True},
    "face2face": {"class_name": "manipulated", "family": "reenactment_video", "container": "ff_pp", "requires_fake_target": True},
    "neuraltextures": {"class_name": "manipulated", "family": "reenactment_video", "container": "ff_pp", "requires_fake_target": True},
    "faceshifter": {"class_name": "manipulated", "family": "face_swap_video", "container": "ff_pp", "requires_fake_target": True},
    "celeb_synthesis": {"class_name": "manipulated", "family": "face_swap_video", "container": "celeb_df_v2", "requires_fake_target": True},
    "ff_pp": {"class_name": "manipulated", "family": "deepfake_video", "container": "ff_pp", "requires_fake_target": True},
    "ff_pp_fake": {"class_name": "manipulated", "family": "deepfake_video", "container": "ff_pp", "requires_fake_target": True},
    "a_ff_pp": {"class_name": "manipulated", "family": "deepfake_video", "container": "ff_pp", "requires_fake_target": True},
    "faceforensics": {"class_name": "manipulated", "family": "deepfake_video", "container": "ff_pp", "requires_fake_target": True},
    "faceforensics_pp": {"class_name": "manipulated", "family": "deepfake_video", "container": "ff_pp", "requires_fake_target": True},
    "dfdc": {"class_name": "manipulated", "family": "deepfake_video", "container": "dfdc", "requires_fake_target": True},
    "a_dfdc": {"class_name": "manipulated", "family": "deepfake_video", "container": "dfdc", "requires_fake_target": True},
    "dfd": {"class_name": "manipulated", "family": "deepfake_video", "container": "dfd", "requires_fake_target": True},
    "a_dfd": {"class_name": "manipulated", "family": "deepfake_video", "container": "dfd", "requires_fake_target": True},
    "celeb_df": {"class_name": "manipulated", "family": "face_swap_video", "container": "celeb_df", "requires_fake_target": True},
    "celeb_df_v2": {"class_name": "manipulated", "family": "face_swap_video", "container": "celeb_df_v2", "requires_fake_target": True},
    "a_celeb_df_v2": {"class_name": "manipulated", "family": "face_swap_video", "container": "celeb_df_v2", "requires_fake_target": True},
    "simswap": {"class_name": "manipulated", "family": "face_swap_image", "requires_fake_target": True},
    "blendface": {"class_name": "manipulated", "family": "face_swap_image", "requires_fake_target": True},
    "facedancer": {"class_name": "manipulated", "family": "face_swap_image", "requires_fake_target": True},
    "infoswap": {"class_name": "manipulated", "family": "face_swap_image", "requires_fake_target": True},
    "uniface": {"class_name": "manipulated", "family": "face_swap_image", "requires_fake_target": True},
    "diffswap": {"class_name": "manipulated", "family": "face_swap_diffusion", "requires_fake_target": True},
    # --- Borderline / Ambiguous Attribute-Editing & Inpainting Subsets ---
    "attgan": {"class_name": "ambiguous", "family": "attribute_editing_gan", "requires_fake_target": True},
    "stgan": {"class_name": "ambiguous", "family": "attribute_editing_gan", "requires_fake_target": True},
    "stargan": {"class_name": "ambiguous", "family": "attribute_editing_gan", "requires_fake_target": True},
    "palette": {"class_name": "ambiguous", "family": "image_translation_diffusion", "requires_fake_target": True},
    "stable_diffusion_inpainting": {
        "class_name": "ambiguous",
        "family": "inpainting_diffusion",
        "requires_fake_target": True,
    },
    "sd_inpainting": {"class_name": "ambiguous", "family": "inpainting_diffusion", "requires_fake_target": True},
}

# Dual-polarity container tokens stored strictly in normalized snake_case (`++` -> `_pp`).
DUAL_POLARITY_CONTAINERS: Set[str] = {
    "ff_pp",
    "a_ff_pp",
    "faceforensics",
    "faceforensics_pp",
    "dfdc",
    "a_dfdc",
    "dfd",
    "a_dfd",
    "celeb_df",
    "celeb_df_v2",
    "a_celeb_df_v2",
}

CANONICAL_CONTAINER_MAP: Dict[str, str] = {
    "ff_pp": "ff_pp",
    "a_ff_pp": "ff_pp",
    "faceforensics": "ff_pp",
    "faceforensics_pp": "ff_pp",
    "dfdc": "dfdc",
    "a_dfdc": "dfdc",
    "dfd": "dfd",
    "a_dfd": "dfd",
    "celeb_df": "celeb_df",
    "celeb_df_v2": "celeb_df_v2",
    "a_celeb_df_v2": "celeb_df_v2",
}

GENERIC_PARENT_FOLDERS: Set[str] = {
    "train",
    "val",
    "valid",
    "validation",
    "test",
    "fake",
    "real",
    "original",
    "genuine",
    "ai_generated",
    "manipulated",
    "images",
    "image",
    "img",
    "imgs",
    "frames",
    "frame",
    "faces",
    "face",
    "cropped",
    "aligned",
    "data",
    "dataset",
    "c23",
    "c40",
    "raw",
    "youtube",
    "actors",
}

_GENERIC_BATCH_RE = re.compile(
    r"^(?:part|batch|chunk|shard|split|fold|set|dir|folder|group|subset)[_-]?\d+$",
    flags=re.IGNORECASE,
)

# Container-level tokens that indicate real vs fake polarity inside a dual-use benchmark
_REAL_POLARITY_TOKENS: Set[str] = {
    "real",
    "original",
    "original_sequences",
    "genuine",
    "pristine",
    "celeb_real",
    "youtube_real",
    "actors_real",
}
_FAKE_POLARITY_TOKENS: Set[str] = {
    "fake",
    "manipulated",
    "manipulated_sequences",
    "altered",
    "synthesis",
    "celeb_synthesis",
}

_FFPP_PAIR_RE = re.compile(r"^(\d{3})(?:_(\d{3}))?$")
_CELEBDF_ACTOR_RE = re.compile(r"^(id\d+)(?:_(id\d+))?[_-]?(\d{4})?$", flags=re.IGNORECASE)
_DFD_CLIP_RE = re.compile(r"^(\d{2})__([a-z0-9_]+)__", flags=re.IGNORECASE)


def normalize_token(value: str) -> str:
    """Normalize subset/method tokens to lowercase snake_case (`++` -> `_pp`)."""
    cleaned = value.strip().replace("++", "_pp")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned).strip("_").lower()
    return cleaned


def _canonical_container_name(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    norm = normalize_token(token)
    if norm in CANONICAL_CONTAINER_MAP:
        return CANONICAL_CONTAINER_MAP[norm]
    meta = VERIFIED_SUBSET_REGISTRY.get(norm)
    if meta and meta.get("container"):
        return str(meta["container"])
    return None


def _is_generic_folder(folder_name: str) -> bool:
    norm = normalize_token(folder_name)
    if not norm:
        return True
    if (
        norm in GENERIC_PARENT_FOLDERS
        or norm in VERIFIED_SUBSET_REGISTRY
        or norm in DUAL_POLARITY_CONTAINERS
        or bool(_GENERIC_BATCH_RE.match(norm))
    ):
        return True
    return False


def compute_hashes(file_path: Path, hash_size: int = 8) -> Tuple[str, str, str, Tuple[int, int], str]:
    """
    Validate image decodability and compute MD5, SHA-256, perceptual dhash, dimensions, and format.
    """
    raw_bytes = file_path.read_bytes()
    md5_hex = hashlib.md5(raw_bytes).hexdigest()
    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()

    with Image.open(file_path) as img:
        img.verify()
    with Image.open(file_path) as img:
        img.load()
        size = img.size
        fmt = img.format or "UNKNOWN"
        dhash_hex = compute_dhash(img, hash_size=hash_size)

    return md5_hex, sha256_hex, dhash_hex, size, fmt


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Compute 64-bit difference perceptual hash matching project convention."""
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.getdata())
    bits: List[bool] = []
    for row in range(hash_size):
        row_offset = row * (hash_size + 1)
        for col in range(hash_size):
            bits.append(pixels[row_offset + col] > pixels[row_offset + col + 1])

    val = 0
    hex_parts: List[str] = []
    for idx, bit in enumerate(bits):
        if bit:
            val += 1 << (idx % 8)
        if idx % 8 == 7:
            hex_parts.append(f"{val:02x}")
            val = 0
    return "".join(hex_parts)


def dhash_hamming_distance(hash_a: str, hash_b: str) -> int:
    """Compute bitwise Hamming distance between two hex dhash strings."""
    return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()


def extract_identity_tokens_and_group(
    rel_or_image_path: str,
    subset_name: str,
    source_container: Optional[str] = None,
    explicit_group: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """
    Extract canonical `(primary_source_group_id, identity_link_tokens)` for paired datasets.

    Guarantees:
    - Paired FF++ real (`original_sequences/.../001/...`) and deepfake clips (`Deepfakes/001_002/...`,
      `FaceShifter/001_002/...`) share canonical token `ffpp::clip::001` (and target/donor pair linkage)
      regardless of subset name.
    - Paired Celeb-DF-v2 real (`Celeb-real/id0_0001...`, `YouTube-real/00001...`) and synthesized clips
      (`Celeb-synthesis/id0_id1_0001...`) share actor/video identity tokens `celebdf::actor::id0`.
    - Generic numbered batch folders (`train/`, `part_01/`, `batch_01/`) are never collapsed into one group.
    """
    if explicit_group and str(explicit_group).strip():
        clean_grp = str(explicit_group).strip()
        prefix = source_container or subset_name
        return f"{prefix}::{clean_grp}", [f"{prefix}::id::{clean_grp}"]

    p = Path(rel_or_image_path)
    parts = [part for part in p.parts if part not in (".", "")]
    norm_parts = [normalize_token(part) for part in parts]
    stem = p.stem
    container = source_container or _canonical_container_name(subset_name)

    # Check Celeb-DF-v2 actor / clip structure
    is_celebdf = container in ("celeb_df", "celeb_df_v2") or any(
        tok in ("celeb_df", "celeb_df_v2", "celeb_real", "celeb_synthesis") for tok in norm_parts
    )
    if is_celebdf:
        # Look in parent folder or filename stem for `id0_id1_0001` or `id0_0001`
        for candidate in (parts[-2] if len(parts) >= 2 else "", stem):
            m = _CELEBDF_ACTOR_RE.match(candidate.split("_frame")[0])
            if m:
                primary_actor = m.group(1).lower()
                link_tokens = [f"celebdf::actor::{primary_actor}"]
                if m.group(2):
                    link_tokens.append(f"celebdf::actor::{m.group(2).lower()}")
                return f"celebdf::actor::{primary_actor}", link_tokens
        # YouTube-real clip inside Celeb-DF-v2 (non-id numeric video dir like `00001`)
        if len(parts) >= 2 and not _is_generic_folder(parts[-2]):
            return f"celebdf::yt::{parts[-2]}", [f"celebdf::yt::{parts[-2]}"]

    # Check FaceForensics++ clip/pair structure (`001` or `001_002`)
    is_ffpp = container == "ff_pp" or any(
        tok in ("ff_pp", "faceforensics", "faceforensics_pp", "original_sequences", "deepfakes", "faceswap", "face2face", "neuraltextures", "faceshifter")
        for tok in norm_parts
    )
    if is_ffpp:
        for candidate in (parts[-2] if len(parts) >= 2 else "", stem.split("_frame")[0]):
            m = _FFPP_PAIR_RE.match(candidate)
            if m:
                target_clip = m.group(1)
                link_tokens = [f"ffpp::clip::{target_clip}"]
                if m.group(2):
                    link_tokens.append(f"ffpp::clip::{m.group(2)}")
                return f"ffpp::clip::{target_clip}", link_tokens

    # Check DeepFakeDetection-actor (DFD) `01__kitchen_pan__...`
    if container == "dfd":
        for candidate in (parts[-2] if len(parts) >= 2 else "", stem):
            m = _DFD_CLIP_RE.match(candidate)
            if m:
                actor_id = m.group(1)
                return f"dfd::actor::{actor_id}", [f"dfd::actor::{actor_id}"]

    # General non-generic video/identity directory fallback
    if len(parts) >= 2 and not _is_generic_folder(parts[-2]):
        prefix = container or subset_name
        grp = f"{prefix}::dir::{parts[-2]}"
        return grp, [grp]

    # Frame-sequence pattern on filename stem (`video01_frame_0012` -> `video01`)
    frame_match = re.match(r"^(.+?)(?:[_-]frame[_-]?\d+|[_-]\d{3,6})$", stem, flags=re.IGNORECASE)
    if frame_match and not _GENERIC_BATCH_RE.match(frame_match.group(1)):
        prefix = container or subset_name
        grp = f"{prefix}::seq::{frame_match.group(1)}"
        return grp, [grp]

    item_grp = f"{subset_name}::item::{stem}"
    return item_grp, [item_grp]


def extract_source_group_id(
    rel_or_image_path: str,
    subset_name: str,
    explicit_group: Optional[str] = None,
    source_container: Optional[str] = None,
) -> str:
    """Compatibility helper returning the canonical primary `source_group_id`."""
    grp, _ = extract_identity_tokens_and_group(
        rel_or_image_path=rel_or_image_path,
        subset_name=subset_name,
        source_container=source_container,
        explicit_group=explicit_group,
    )
    return grp


def resolve_subset_class(
    path_str: str,
    binary_target: Optional[int] = None,
    explicit_subset: Optional[str] = None,
    ambiguous_policy: str = "exclude",
    custom_subset_map: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], str, str]:
    """
    Resolve `(resolved_class_name, source_subset, reason)` strictly from verified metadata/paths.

    NEVER assigns `ai_generated` or `manipulated` purely from `binary_target == 1`.
    Short collision-prone token `"if"` (DeepFloyd IF) is matched ONLY when passed via
    exact `explicit_subset` or exact uppercase folder name `"IF"`.
    """
    merged_registry = dict(VERIFIED_SUBSET_REGISTRY)
    if custom_subset_map:
        for k, cls_name in custom_subset_map.items():
            norm_k = normalize_token(k)
            if cls_name not in CLASS_TO_ID and cls_name != "ambiguous":
                raise ValueError(f"Invalid custom class '{cls_name}' for subset '{k}'.")
            merged_registry[norm_k] = {
                "class_name": cls_name,
                "family": "custom_verified",
                "requires_real_target": cls_name == "genuine",
                "requires_fake_target": cls_name in ("ai_generated", "manipulated"),
            }

    raw_parent_parts = [part for part in Path(path_str).parts[:-1] if part not in (".", "")]
    candidates: List[str] = []
    if explicit_subset:
        norm_explicit = normalize_token(explicit_subset)
        if norm_explicit == "if":
            norm_explicit = "deepfloyd_if"
        candidates.append(norm_explicit)

    for raw_part in raw_parent_parts:
        if raw_part == "IF":
            candidates.append("deepfloyd_if")
        else:
            norm_part = normalize_token(raw_part)
            if norm_part and norm_part != "if":
                candidates.append(norm_part)

    if not candidates:
        return None, "unknown", "unverified_subset"

    has_real_hint = any(tok in _REAL_POLARITY_TOKENS for tok in candidates)
    has_fake_hint = any(tok in _FAKE_POLARITY_TOKENS for tok in candidates)

    # First pass: high-specificity tokens (skip dual containers & generic polarity dirs)
    matched_token: Optional[str] = None
    matched_meta: Optional[Dict[str, Any]] = None
    for tok in candidates:
        if tok in {"real", "fake", "original"} or tok in DUAL_POLARITY_CONTAINERS:
            continue
        if tok in merged_registry:
            matched_token = tok
            matched_meta = merged_registry[tok]
            break

    # Second pass: dual-polarity containers (ff_pp, celeb_df_v2, dfdc, dfd)
    if matched_token is None:
        for tok in candidates:
            if tok in DUAL_POLARITY_CONTAINERS and tok in merged_registry:
                matched_token = tok
                matched_meta = merged_registry[tok]
                break

    # Third pass: explicit generic polarity directory (`real`, `original`) ONLY if real target / not generic fake
    if matched_token is None:
        for tok in candidates:
            if tok in merged_registry:
                matched_token = tok
                matched_meta = merged_registry[tok]
                break

    if matched_token is None or matched_meta is None:
        return None, candidates[0], "unverified_subset"

    raw_class = matched_meta["class_name"]
    if matched_token in DUAL_POLARITY_CONTAINERS:
        canonical = CANONICAL_CONTAINER_MAP.get(matched_token, matched_token)
        if has_real_hint and has_fake_hint:
            return None, canonical, "conflicting_real_and_fake_signals"
        if (has_real_hint or binary_target == 0) and not (has_fake_hint or binary_target == 1):
            return "genuine", f"{canonical}_real", "verified_dual_container_real"
        if (has_fake_hint or binary_target == 1) and not (has_real_hint or binary_target == 0):
            return raw_class, canonical, "verified_dual_container_fake"
        if (has_real_hint and binary_target == 1) or (has_fake_hint and binary_target == 0):
            return None, canonical, "target_mismatch_dual_container"
        return None, canonical, "dual_container_missing_polarity"

    if binary_target is not None:
        if raw_class == "genuine" and binary_target != 0:
            return None, matched_token, "target_mismatch_expected_real"
        if raw_class in ("ai_generated", "manipulated") and binary_target != 1:
            return None, matched_token, "target_mismatch_expected_fake"

    if raw_class == "ambiguous":
        if ambiguous_policy == "manipulated":
            if binary_target == 0:
                return None, matched_token, "ambiguous_target_0_mismatch"
            return "manipulated", matched_token, "ambiguous_mapped_to_manipulated"
        return None, matched_token, "ambiguous_quarantined"

    return raw_class, matched_token, "verified_registry_match"


def _infer_container_from_path(path_str: str, subset_name: str) -> Optional[str]:
    meta_container = _canonical_container_name(subset_name)
    if meta_container:
        return meta_container
    for part in Path(path_str).parts[:-1]:
        c = _canonical_container_name(part)
        if c:
            return c
    return None


def parse_aiface_csv_rows(
    csv_path: Path,
    image_root: Path,
    ambiguous_policy: str = "exclude",
    custom_subset_map: Optional[Dict[str, str]] = None,
    source_split_hint: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Counter]:
    """Parse AI-Face CSV metadata while preserving group & container metadata."""
    records: List[Dict[str, Any]] = []
    rejected: Counter = Counter()

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Empty CSV header in {csv_path}")
        col_map = {normalize_token(name): name for name in reader.fieldnames}

        path_col = col_map.get("image_path") or col_map.get("im_path") or col_map.get("path")
        target_col = col_map.get("target") or col_map.get("label")
        method_col = col_map.get("generation_method") or col_map.get("method") or col_map.get("subset")
        group_col = col_map.get("video_id") or col_map.get("identity_id") or col_map.get("group_id")

        if path_col is None:
            raise ValueError(f"CSV {csv_path} missing required image path column.")

        for row in reader:
            raw_rel = (row.get(path_col) or "").strip()
            if not raw_rel:
                rejected["empty_path"] += 1
                continue

            binary_target: Optional[int] = None
            if target_col and (row.get(target_col) or "").strip() != "":
                try:
                    binary_target = int(float(row[target_col].strip()))
                except ValueError:
                    rejected["invalid_binary_target"] += 1
                    continue

            explicit_subset = (row.get(method_col) or "").strip() if method_col else None
            cls_name, subset_name, reason = resolve_subset_class(
                path_str=raw_rel,
                binary_target=binary_target,
                explicit_subset=explicit_subset,
                ambiguous_policy=ambiguous_policy,
                custom_subset_map=custom_subset_map,
            )
            if cls_name is None:
                rejected[f"{reason}:{subset_name}"] += 1
                continue

            full_path = Path(raw_rel)
            if not full_path.is_absolute():
                full_path = (image_root / raw_rel).resolve()

            demographics: Dict[str, str] = {}
            for demo_key in ("gender", "age", "skin_tone", "intersection", "race"):
                orig_col = col_map.get(demo_key)
                if orig_col and (row.get(orig_col) or "").strip() != "":
                    demographics[demo_key] = row[orig_col].strip()

            group_val = row.get(group_col).strip() if group_col and row.get(group_col) else None
            container = _infer_container_from_path(raw_rel, subset_name)
            grp_id, link_tokens = extract_identity_tokens_and_group(
                rel_or_image_path=raw_rel,
                subset_name=subset_name,
                source_container=container,
                explicit_group=group_val,
            )
            records.append(
                {
                    "source_path": str(full_path),
                    "relative_source_path": raw_rel.replace("\\", "/"),
                    "anchor_root": str(image_root.resolve()),
                    "class_name": cls_name,
                    "label": CLASS_TO_ID[cls_name],
                    "source_subset": subset_name,
                    "source_container": container,
                    "resolution_reason": reason,
                    "source_group_id": grp_id,
                    "identity_tokens": link_tokens,
                    "source_dataset": "AI-Face",
                    "source_split_hint": source_split_hint,
                    "binary_target": binary_target,
                    "demographics": demographics,
                }
            )

    return records, rejected


def scan_local_source_directory(
    source_root: Path,
    source_profile: str,
    ambiguous_policy: str = "exclude",
    custom_subset_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], Counter]:
    """
    Scan a local directory using a strictly declared provenance profile.
    """
    records: List[Dict[str, Any]] = []
    rejected: Counter = Counter()

    if not source_root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")

    resolved_root = source_root.resolve()
    for file_path in sorted(source_root.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in VALID_EXTENSIONS:
            continue

        rel_path = file_path.relative_to(source_root)
        rel_str = rel_path.as_posix()
        parts_lower = [p.lower() for p in rel_path.parts]
        container: Optional[str] = None

        if source_profile == "kaggle_140k_ffhq_stylegan":
            if "real" in parts_lower[:-1]:
                cls_name, subset_name, reason = "genuine", "ffhq_local", "verified_kaggle140k_ffhq"
                b_target = 0
            elif "fake" in parts_lower[:-1]:
                cls_name, subset_name, reason = "ai_generated", "stylegan_local", "verified_kaggle140k_stylegan"
                b_target = 1
            else:
                rejected["kaggle140k_unrecognized_subfolder"] += 1
                continue
            ds_name = "Local-DeepFakeDetection-FFHQ-StyleGAN"
        elif source_profile == "custom_three_class_folders":
            top_dir = normalize_token(rel_path.parts[0]) if len(rel_path.parts) > 1 else ""
            if top_dir not in CLASS_TO_ID:
                rejected[f"invalid_class_folder:{top_dir}"] += 1
                continue
            cls_name = top_dir
            subset_name = normalize_token(rel_path.parts[1]) if len(rel_path.parts) > 2 else f"custom_{cls_name}"
            reason = "verified_three_class_folder"
            b_target = 0 if cls_name == "genuine" else 1
            ds_name = "Local-ThreeClass"
        elif source_profile == "aiface_folders":
            cls_name_opt, subset_name, reason = resolve_subset_class(
                path_str=rel_str,
                binary_target=None,
                ambiguous_policy=ambiguous_policy,
                custom_subset_map=custom_subset_map,
            )
            if cls_name_opt is None:
                rejected[f"{reason}:{subset_name}"] += 1
                continue
            cls_name = cls_name_opt
            b_target = 0 if cls_name == "genuine" else 1
            ds_name = "AI-Face-Folders"
            container = _infer_container_from_path(rel_str, subset_name)
        else:
            raise ValueError(f"Unsupported source_profile: {source_profile}")

        grp_id, link_tokens = extract_identity_tokens_and_group(
            rel_or_image_path=rel_str,
            subset_name=subset_name,
            source_container=container,
        )
        records.append(
            {
                "source_path": str(file_path.resolve()),
                "relative_source_path": rel_str,
                "anchor_root": str(resolved_root),
                "class_name": cls_name,
                "label": CLASS_TO_ID[cls_name],
                "source_subset": subset_name,
                "source_container": container,
                "resolution_reason": reason,
                "source_group_id": grp_id,
                "identity_tokens": link_tokens,
                "source_dataset": ds_name,
                "source_split_hint": None,
                "binary_target": b_target,
                "demographics": {},
            }
        )

    return records, rejected


def _dhash_bands(hash_int: int, num_bands: int) -> List[Tuple[int, int]]:
    """
    Partition a 64-bit integer into `num_bands` disjoint bit slices (Pigeonhole Principle).
    If Hamming distance(h1, h2) <= num_bands - 1, at least one (band_idx, slice_val) collides.
    """
    bands: List[Tuple[int, int]] = []
    bits_per_band = 64 // num_bands
    remainder = 64 % num_bands
    offset = 0
    for band_idx in range(num_bands):
        width = bits_per_band + (1 if band_idx < remainder else 0)
        mask = (1 << width) - 1
        bands.append((band_idx, (hash_int >> offset) & mask))
        offset += width
    return bands


def deduplicate_and_validate_records(
    records: List[Dict[str, Any]],
    verify_images: bool = True,
    dhash_hamming_threshold: int = 4,
    unseen_test_generators: Optional[Sequence[str]] = None,
    unseen_val_generators: Optional[Sequence[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Validate images and deterministically remove exact (`sha256`) and perceptual
    (`dhash` Hamming distance <= `dhash_hamming_threshold`) duplicates.

    Order-independent: sorts validated candidates canonically BEFORE deduplication
    so output is invariant to CSV row order or filesystem traversal order, while
    prioritizing `unseen_test` > `unseen_val` > `shared` to protect unseen-test sets.
    """
    if dhash_hamming_threshold < 0 or dhash_hamming_threshold > 64:
        raise ValueError(f"dhash_hamming_threshold must be between 0 and 64, got {dhash_hamming_threshold}.")

    unseen_test_norm = {normalize_token(g) for g in (unseen_test_generators or ())}
    unseen_val_norm = {normalize_token(g) for g in (unseen_val_generators or ())}

    validated: List[Dict[str, Any]] = []
    stats: Counter = Counter()

    for rec in records:
        path = Path(rec["source_path"])
        if not path.exists():
            stats["missing_file"] += 1
            continue

        try:
            if verify_images:
                md5_hex, sha256_hex, dhash_hex, size, fmt = compute_hashes(path)
            else:
                raw_bytes = path.read_bytes()
                md5_hex = hashlib.md5(raw_bytes).hexdigest()
                sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
                dhash_hex = ""
                size = (0, 0)
                fmt = path.suffix.lstrip(".").upper() or "UNKNOWN"
        except Exception as exc:
            logger.warning("Corrupt/unreadable image skipped: %s (%s)", path, exc)
            stats["corrupt_image"] += 1
            continue

        enriched = dict(rec)
        enriched.update(
            {
                "md5": md5_hex,
                "sha256": sha256_hex,
                "dhash": dhash_hex,
                "dhash_int": int(dhash_hex, 16) if dhash_hex else None,
                "width": size[0],
                "height": size[1],
                "format": fmt,
            }
        )
        validated.append(enriched)

    def _canonical_sort_key(item: Dict[str, Any]) -> Tuple[int, str, str, str]:
        subset_tok = normalize_token(str(item.get("source_subset") or ""))
        container_tok = normalize_token(str(item.get("source_container") or ""))
        if subset_tok in unseen_test_norm or (container_tok and container_tok in unseen_test_norm):
            tier = 0
        elif subset_tok in unseen_val_norm or (container_tok and container_tok in unseen_val_norm):
            tier = 1
        else:
            tier = 2
        return (
            tier,
            str(item["sha256"]),
            str(item.get("relative_source_path") or item["source_path"]),
            str(item.get("source_subset") or ""),
        )

    validated.sort(key=_canonical_sort_key)

    kept: List[Dict[str, Any]] = []
    seen_sha256: Set[str] = set()
    kept_dhash_ints: List[int] = []
    num_bands = min(64, dhash_hamming_threshold + 1)
    dhash_buckets: Dict[Tuple[int, int], List[int]] = defaultdict(list)

    for item in validated:
        sha_hex = item["sha256"]
        if sha_hex in seen_sha256:
            stats["exact_duplicate_removed"] += 1
            continue

        d_int: Optional[int] = item.pop("dhash_int", None)
        is_near_dup = False
        if d_int is not None:
            if num_bands <= 16:
                candidate_indices: Set[int] = set()
                for band_key in _dhash_bands(d_int, num_bands):
                    candidate_indices.update(dhash_buckets.get(band_key, ()))
                for cand_idx in candidate_indices:
                    if (d_int ^ kept_dhash_ints[cand_idx]).bit_count() <= dhash_hamming_threshold:
                        is_near_dup = True
                        break
            else:
                for prev_int in kept_dhash_ints:
                    if (d_int ^ prev_int).bit_count() <= dhash_hamming_threshold:
                        is_near_dup = True
                        break

        if is_near_dup:
            stats["perceptual_duplicate_removed"] += 1
            continue

        seen_sha256.add(sha_hex)
        if d_int is not None:
            new_idx = len(kept_dhash_ints)
            kept_dhash_ints.append(d_int)
            if num_bands <= 16:
                for band_key in _dhash_bands(d_int, num_bands):
                    dhash_buckets[band_key].append(new_idx)

        kept.append(item)
        stats["valid_unique"] += 1

    return kept, dict(stats)


def _merge_paired_identity_clusters(records: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Merge records sharing any `source_group_id` or `identity_tokens` (within the same
    class or across paired genuine/manipulated source clips) into atomic clusters using
    Union-Find so related real/fake identities never leak across splits.
    """
    if not records:
        return []

    n = len(records)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    token_owner: Dict[str, int] = {}
    for idx, rec in enumerate(records):
        tokens = list(rec.get("identity_tokens") or [])
        tokens.append(str(rec["source_group_id"]))
        for tok in tokens:
            if tok in token_owner:
                union(idx, token_owner[tok])
            else:
                token_owner[tok] = idx

    clusters_map: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for idx, rec in enumerate(records):
        root = find(idx)
        clusters_map[root].append(rec)

    ordered_clusters: List[List[Dict[str, Any]]] = []
    for root in sorted(clusters_map.keys()):
        items = clusters_map[root]
        canonical_gid = min(str(r["source_group_id"]) for r in items)
        updated: List[Dict[str, Any]] = []
        for it in items:
            cp = dict(it)
            cp["source_group_id"] = canonical_gid
            updated.append(cp)
        ordered_clusters.append(updated)
    return ordered_clusters


def _select_atomic_groups(
    groups: List[List[Dict[str, Any]]],
    target_count: Optional[int],
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Select whole atomic clusters without EVER splitting any cluster across group boundaries.
    """
    if target_count is None:
        selected: List[Dict[str, Any]] = []
        for grp in groups:
            selected.extend(grp)
        return selected

    by_subset: Dict[str, List[List[Dict[str, Any]]]] = defaultdict(list)
    for grp in groups:
        key = "+".join(sorted({str(r["source_subset"]) for r in grp}))
        by_subset[key].append(grp)

    keys = sorted(by_subset.keys())
    for k in keys:
        rng.shuffle(by_subset[k])

    selected = []
    pointers = {k: 0 for k in keys}
    while len(selected) < target_count:
        progressed = False
        for k in keys:
            idx = pointers[k]
            bucket = by_subset[k]
            while idx < len(bucket):
                grp = bucket[idx]
                idx += 1
                if len(selected) + len(grp) <= target_count:
                    selected.extend(grp)
                    progressed = True
                    break
            pointers[k] = idx
            if len(selected) >= target_count:
                break
        if not progressed:
            break
    return selected


def _touches_generator_set(
    cluster: List[Dict[str, Any]],
    gen_set: Set[str],
) -> bool:
    for item in cluster:
        sub_tok = normalize_token(str(item.get("source_subset") or ""))
        cont_tok = normalize_token(str(item.get("source_container") or ""))
        if sub_tok in gen_set or (cont_tok and cont_tok in gen_set):
            return True
    return False


def assign_leakage_free_splits(
    records: List[Dict[str, Any]],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    unseen_test_generators: Optional[Sequence[str]] = None,
    unseen_val_generators: Optional[Sequence[str]] = None,
    target_per_class: Optional[int] = None,
    seed: int = 42,
    quota_report_out: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Assign `train` / `val` / `test` splits with atomic cross-class identity/clip isolation.

    Guarantees:
    - Paired real & manipulated clusters (`FF++`, `Celeb-DF-v2`) stay in ONE split together.
    - When any unseen test dataset/generator (e.g., `celeb_df_v2`, `faceshifter`) touches
      an identity/clip cluster, the entire cluster (including paired real faces) routes to `test`.
    - Never slices inside an atomic cluster to force quotas; explicitly records shortfalls.
    """
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0.")

    rng = random.Random(seed)
    unseen_test_norm = {normalize_token(g) for g in (unseen_test_generators or ())}
    unseen_val_norm = {normalize_token(g) for g in (unseen_val_generators or ())}
    overlap = unseen_test_norm & unseen_val_norm
    if overlap:
        raise ValueError(f"Generators cannot be in both unseen_val and unseen_test: {sorted(overlap)}")

    all_clusters = _merge_paired_identity_clusters(records)

    forced_test_clusters: List[List[Dict[str, Any]]] = []
    forced_val_clusters: List[List[Dict[str, Any]]] = []
    shared_clusters: List[List[Dict[str, Any]]] = []

    for cluster in all_clusters:
        if unseen_test_norm and _touches_generator_set(cluster, unseen_test_norm):
            forced_test_clusters.append(cluster)
        elif unseen_val_norm and _touches_generator_set(cluster, unseen_val_norm):
            forced_val_clusters.append(cluster)
        else:
            shared_clusters.append(cluster)

    final_records: List[Dict[str, Any]] = []
    shortfalls: Dict[str, Any] = {}

    # Compute per-class budgets cleanly while keeping multi-class clusters together
    split_budgets: Dict[str, Dict[str, Optional[int]]] = {}
    for cls_name in CLASS_NAMES:
        if target_per_class is not None:
            t_q = int(round(target_per_class * test_ratio))
            v_q = int(round(target_per_class * val_ratio))
            tr_q = target_per_class - t_q - v_q
            split_budgets[cls_name] = {"train": tr_q, "val": v_q, "test": t_q}
        else:
            split_budgets[cls_name] = {"train": None, "val": None, "test": None}

    assigned_counts: Dict[str, Counter] = defaultdict(Counter)

    def _can_accept_cluster(cluster: List[Dict[str, Any]], split_name: str) -> bool:
        cls_increments = Counter(str(r["class_name"]) for r in cluster)
        for cls_name, inc in cls_increments.items():
            cap = split_budgets[cls_name][split_name]
            if cap is not None and assigned_counts[split_name][cls_name] + inc > cap:
                return False
        return True

    def _commit_cluster(cluster: List[Dict[str, Any]], split_name: str) -> None:
        for item in cluster:
            copied = dict(item)
            copied["split"] = split_name
            final_records.append(copied)
            assigned_counts[split_name][str(item["class_name"])] += 1

    # 1. Assign forced unseen test clusters atomically
    rng.shuffle(forced_test_clusters)
    for cluster in forced_test_clusters:
        if _can_accept_cluster(cluster, "test"):
            _commit_cluster(cluster, "test")

    # 2. Assign forced unseen val clusters atomically
    rng.shuffle(forced_val_clusters)
    for cluster in forced_val_clusters:
        if _can_accept_cluster(cluster, "val"):
            _commit_cluster(cluster, "val")

    # 3. Assign shared clusters across train / val / (test if no forced test for a class)
    # Shuffle deterministically within subset diversity buckets
    shared_by_sig: Dict[str, List[List[Dict[str, Any]]]] = defaultdict(list)
    for cluster in shared_clusters:
        sig = "+".join(sorted({f"{r['class_name']}:{r['source_subset']}" for r in cluster}))
        shared_by_sig[sig].append(cluster)

    interleaved_shared: List[List[Dict[str, Any]]] = []
    sigs = sorted(shared_by_sig.keys())
    for s in sigs:
        rng.shuffle(shared_by_sig[s])
    while any(shared_by_sig[s] for s in sigs):
        for s in sigs:
            if shared_by_sig[s]:
                interleaved_shared.append(shared_by_sig[s].pop())

    if target_per_class is None:
        # Allocate shared clusters sequentially per class/ratio without breaking cluster atomicity
        total_shared_by_class = Counter(str(r["class_name"]) for c in interleaved_shared for r in c)
        for cluster in interleaved_shared:
            dom_cls = Counter(str(r["class_name"]) for r in cluster).most_common(1)[0][0]
            has_forced_test_for_cls = any(
                r["class_name"] == dom_cls for c in forced_test_clusters for r in c
            )
            has_forced_val_for_cls = any(
                r["class_name"] == dom_cls for c in forced_val_clusters for r in c
            )

            cls_total_all = total_shared_by_class[dom_cls] + sum(
                assigned_counts[sp][dom_cls] for sp in ("test", "val")
            )
            desired_test = 0 if has_forced_test_for_cls else int(round(cls_total_all * test_ratio))
            desired_val = 0 if has_forced_val_for_cls else int(round(cls_total_all * val_ratio))

            if not has_forced_test_for_cls and assigned_counts["test"][dom_cls] < desired_test:
                target_split = "test"
            elif not has_forced_val_for_cls and assigned_counts["val"][dom_cls] < desired_val:
                target_split = "val"
            else:
                target_split = "train"
            _commit_cluster(cluster, target_split)
    else:
        for cluster in interleaved_shared:
            cls_set = {str(r["class_name"]) for r in cluster}
            has_unseen_test_for_all = all(
                any(r["class_name"] == c for fc in forced_test_clusters for r in fc)
                for c in cls_set
            )
            # Only route shared items to test if NO forced test generator exists for that class
            candidate_order = ["val", "train"] if has_unseen_test_for_all else ["test", "val", "train"]
            placed = False
            for sp in candidate_order:
                if _can_accept_cluster(cluster, sp):
                    _commit_cluster(cluster, sp)
                    placed = True
                    break
            if not placed:
                continue

    for cls_name in CLASS_NAMES:
        cls_actual = sum(assigned_counts[sp][cls_name] for sp in ("train", "val", "test"))
        if target_per_class is not None and cls_actual < target_per_class:
            per_split_shortfall = {
                sp: max(0, (split_budgets[cls_name][sp] or 0) - assigned_counts[sp][cls_name])
                for sp in ("train", "val", "test")
            }
            shortfalls[cls_name] = {
                "requested": target_per_class,
                "actual": cls_actual,
                "shortfall": target_per_class - cls_actual,
                "split_shortfalls": per_split_shortfall,
            }
            logger.warning(
                "Quota shortfall for class '%s': requested=%d, actual=%d (shortfall=%d, splits=%s)",
                cls_name,
                target_per_class,
                cls_actual,
                target_per_class - cls_actual,
                per_split_shortfall,
            )

    if quota_report_out is not None:
        quota_report_out["target_per_class"] = target_per_class
        quota_report_out["split_counts"] = {
            sp: {cls: assigned_counts[sp][cls] for cls in CLASS_NAMES} for sp in ("train", "val", "test")
        }
        quota_report_out["shortfalls"] = shortfalls
        quota_report_out["has_shortfall"] = len(shortfalls) > 0

    return final_records


def _safe_link_or_copy(source_path: Path, target_path: Path) -> str:
    """Create a hard link if possible to save disk space; fall back to copy2."""
    if target_path.exists():
        return "existing"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(str(source_path), str(target_path))
        return "hardlink"
    except (OSError, NotImplementedError):
        shutil.copy2(str(source_path), str(target_path))
        return "copy"


def _portable_manifest_path(
    record: Dict[str, Any],
    output_dir: Path,
    common_anchor: Optional[Path],
) -> str:
    """
    Compute a Colab-portable POSIX relative path in manifest-only mode.
    Refuses to emit raw Windows drive paths (`C:/...`).
    """
    src = Path(record["source_path"]).resolve()
    if common_anchor is not None:
        try:
            return src.relative_to(common_anchor).as_posix()
        except ValueError:
            pass
    anchor = record.get("anchor_root")
    if anchor:
        try:
            return src.relative_to(Path(anchor).resolve()).as_posix()
        except ValueError:
            pass
    try:
        return src.relative_to(output_dir.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(
            f"Cannot compute Colab-portable relative path for '{src}' without a common dataset root. "
            "Pass --materialize to copy/hardlink splits under --output-dir."
        ) from exc


def materialize_and_write_manifest(
    records: List[Dict[str, Any]],
    output_dir: Path,
    manifest_only: bool = True,
    rejected_counts: Optional[Counter] = None,
    dedup_stats: Optional[Dict[str, int]] = None,
    target_per_class: Optional[int] = None,
    quota_report: Optional[Dict[str, Any]] = None,
    strict_quotas: bool = False,
) -> Tuple[Path, Path]:
    """
    Optionally hardlink/copy images into `<output_dir>/<split>/<class_name>/`,
    verify zero split/group leakage, and write `dataset_manifest.json` + `dataset_audit_report.json`.
    """
    if strict_quotas and quota_report and quota_report.get("has_shortfall"):
        raise RuntimeError(f"Strict quota check failed due to class shortfalls: {quota_report['shortfalls']}")

    output_dir.mkdir(parents=True, exist_ok=True)
    link_stats: Counter = Counter()

    common_anchor: Optional[Path] = None
    path_anchor_description = "output_dir"
    if manifest_only and records:
        anchors = {str(Path(r.get("anchor_root") or Path(r["source_path"]).parent).resolve()) for r in records}
        try:
            common_str = os.path.commonpath(list(anchors))
            common_anchor = Path(common_str).resolve()
            path_anchor_description = f"common_root:{common_anchor.name}"
        except ValueError:
            # Different drive letters on Windows -> require --materialize
            raise ValueError(
                "Manifest-only mode spans multiple filesystem drives and cannot produce portable relative "
                "paths for Colab. Use --materialize to stage files under --output-dir."
            )

    manifest_items: List[Dict[str, Any]] = []
    for idx, rec in enumerate(records):
        item = dict(rec)
        # Drop internal-only temporary anchor field from output manifest
        item.pop("anchor_root", None)
        if manifest_only:
            rel_posix = _portable_manifest_path(rec, output_dir=output_dir, common_anchor=common_anchor)
            if Path(rel_posix).is_absolute() or (len(rel_posix) >= 2 and rel_posix[1] == ":"):
                raise ValueError(f"Non-portable absolute path generated in manifest-only mode: {rel_posix}")
            item["image_path"] = rel_posix
            link_stats["manifest_only"] += 1
        else:
            src = Path(rec["source_path"])
            safe_name = f"{rec['source_subset']}_{idx:07d}_{rec['sha256'][:8]}{src.suffix.lower()}"
            dst = output_dir / rec["split"] / rec["class_name"] / safe_name
            mode = _safe_link_or_copy(src, dst)
            link_stats[mode] += 1
            item["image_path"] = dst.relative_to(output_dir).as_posix()
        manifest_items.append(item)

    split_sha: Dict[str, Set[str]] = defaultdict(set)
    split_dhash: Dict[str, Set[str]] = defaultdict(set)
    split_groups: Dict[str, Set[str]] = defaultdict(set)
    split_tokens: Dict[str, Set[str]] = defaultdict(set)
    split_class_counts: Dict[str, Counter] = defaultdict(Counter)
    generator_split_counts: Dict[str, Counter] = defaultdict(Counter)

    for item in manifest_items:
        sp = item["split"]
        split_sha[sp].add(item["sha256"])
        if item.get("dhash"):
            split_dhash[sp].add(item["dhash"])
        split_groups[sp].add(item["source_group_id"])
        for tok in item.get("identity_tokens", ()):
            split_tokens[sp].add(tok)
        split_class_counts[sp][item["class_name"]] += 1
        generator_split_counts[item["source_subset"]][sp] += 1

    leakage = {
        "sha256_train_val": len(split_sha["train"] & split_sha["val"]),
        "sha256_train_test": len(split_sha["train"] & split_sha["test"]),
        "sha256_val_test": len(split_sha["val"] & split_sha["test"]),
        "dhash_train_val": len(split_dhash["train"] & split_dhash["val"]),
        "dhash_train_test": len(split_dhash["train"] & split_dhash["test"]),
        "dhash_val_test": len(split_dhash["val"] & split_dhash["test"]),
        "group_train_val": len(split_groups["train"] & split_groups["val"]),
        "group_train_test": len(split_groups["train"] & split_groups["test"]),
        "group_val_test": len(split_groups["val"] & split_groups["test"]),
        "identity_token_train_val": len(split_tokens["train"] & split_tokens["val"]),
        "identity_token_train_test": len(split_tokens["train"] & split_tokens["test"]),
        "identity_token_val_test": len(split_tokens["val"] & split_tokens["test"]),
    }
    leakage["total_leaks"] = sum(leakage.values())

    summary_by_split = {sp: dict(split_class_counts[sp]) for sp in ("train", "val", "test")}
    class_totals = Counter()
    for sp_cnt in split_class_counts.values():
        class_totals.update(sp_cnt)

    shortfall_info = (quota_report or {}).get("shortfalls", {})
    manifest_payload = {
        "schema_version": "1.1.0",
        "dataset_name": "TruthLens-HumanFace-3Class",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "class_names": list(CLASS_NAMES),
        "class_to_id": dict(CLASS_TO_ID),
        "image_path_anchor": path_anchor_description,
        "total_images": len(manifest_items),
        "target_per_class": target_per_class,
        "split_counts": summary_by_split,
        "class_totals": dict(class_totals),
        "quota_shortfalls": shortfall_info,
        "generator_split_counts": {k: dict(v) for k, v in sorted(generator_split_counts.items())},
        "leakage_check": leakage,
        "link_stats": dict(link_stats),
        "images": manifest_items,
    }

    manifest_path = output_dir / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    audit_payload = {
        "manifest_path": str(manifest_path),
        "created_at": manifest_payload["created_at"],
        "image_path_anchor": path_anchor_description,
        "total_selected": len(manifest_items),
        "target_per_class": target_per_class,
        "class_totals": dict(class_totals),
        "missing_class_quotas": {
            cls: max(0, (target_per_class or 0) - class_totals.get(cls, 0))
            for cls in CLASS_NAMES
        }
        if target_per_class
        else {},
        "quota_shortfalls": shortfall_info,
        "split_counts": summary_by_split,
        "generator_split_counts": manifest_payload["generator_split_counts"],
        "deduplication_stats": dedup_stats or {},
        "rejected_or_quarantined": dict(rejected_counts or {}),
        "leakage_check": leakage,
        "zero_leakage_verified": leakage["total_leaks"] == 0,
    }

    audit_path = output_dir / "dataset_audit_report.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, indent=2)

    logger.info(
        "Wrote manifest (%d images) -> %s | Zero leakage: %s | Shortfalls: %s",
        len(manifest_items),
        manifest_path,
        audit_payload["zero_leakage_verified"],
        bool(shortfall_info),
    )
    return manifest_path, audit_path


def _load_custom_map(path: Optional[Path]) -> Optional[Dict[str, str]]:
    if path is None:
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Custom subset mapping JSON must be a dictionary of subset -> class_name.")
    return {str(k): str(v) for k, v in data.items()}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TruthLens Stage 1: Prepare verified 3-class Human-Face dataset manifest."
    )
    parser.add_argument(
        "--aiface-csv",
        action="append",
        type=Path,
        default=[],
        help="Path to AI-Face train.csv or test.csv annotation file (repeatable).",
    )
    parser.add_argument(
        "--aiface-root",
        type=Path,
        default=None,
        help="Root directory where AI-Face image folders reside.",
    )
    parser.add_argument(
        "--local-source",
        action="append",
        type=Path,
        default=[],
        help="Optional local dataset directory (repeatable, paired with --local-profile).",
    )
    parser.add_argument(
        "--local-profile",
        choices=["aiface_folders", "kaggle_140k_ffhq_stylegan", "custom_three_class_folders"],
        default="aiface_folders",
        help="Provenance profile used when scanning --local-source directories.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Target directory for dataset_manifest.json and optional split folders.",
    )
    parser.add_argument(
        "--ambiguous-policy",
        choices=["exclude", "manipulated"],
        default="exclude",
        help="Policy for attribute-editing/inpainting subsets (AttGAN, StarGAN, STGAN, Palette, SD Inpainting).",
    )
    parser.add_argument(
        "--custom-subset-map",
        type=Path,
        default=None,
        help="Optional JSON mapping custom subset tokens to genuine/ai_generated/manipulated.",
    )
    parser.add_argument(
        "--target-per-class",
        type=int,
        default=None,
        help="Optional balanced sample cap per class (e.g. 15000).",
    )
    parser.add_argument(
        "--strict-quotas",
        action="store_true",
        help="Exit with error if any class falls short of --target-per-class.",
    )
    parser.add_argument(
        "--dhash-hamming-threshold",
        type=int,
        default=4,
        help="Max bitwise Hamming distance between 64-bit dhash values treated as near-duplicates (default: 4).",
    )
    parser.add_argument(
        "--unseen-test-generators",
        nargs="*",
        default=["midjourney", "sdxl", "celeb_df_v2", "faceshifter"],
        help="Generator/subset/container names isolated exclusively to the test split.",
    )
    parser.add_argument(
        "--unseen-val-generators",
        nargs="*",
        default=[],
        help="Optional generator/subset names isolated exclusively to the val split.",
    )
    parser.add_argument(
        "--materialize",
        action="store_true",
        help="Materialize <output-dir>/<split>/<class>/ via hardlinks/copy (default: manifest-only).",
    )
    parser.add_argument(
        "--skip-image-verify",
        action="store_true",
        help="Skip Pillow decode + perceptual dhash (only recommended for dry metadata runs).",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    if not args.aiface_csv and not args.local_source:
        raise ValueError("Provide at least one --aiface-csv or --local-source input.")

    custom_map = _load_custom_map(args.custom_subset_map)
    all_records: List[Dict[str, Any]] = []
    total_rejected: Counter = Counter()

    for csv_path in args.aiface_csv:
        root = args.aiface_root or csv_path.parent.parent
        recs, rej = parse_aiface_csv_rows(
            csv_path=csv_path,
            image_root=root,
            ambiguous_policy=args.ambiguous_policy,
            custom_subset_map=custom_map,
        )
        all_records.extend(recs)
        total_rejected.update(rej)

    for src_dir in args.local_source:
        recs, rej = scan_local_source_directory(
            source_root=src_dir,
            source_profile=args.local_profile,
            ambiguous_policy=args.ambiguous_policy,
            custom_subset_map=custom_map,
        )
        all_records.extend(recs)
        total_rejected.update(rej)

    unique_records, dedup_stats = deduplicate_and_validate_records(
        all_records,
        verify_images=not args.skip_image_verify,
        dhash_hamming_threshold=args.dhash_hamming_threshold,
        unseen_test_generators=args.unseen_test_generators,
        unseen_val_generators=args.unseen_val_generators,
    )
    quota_report: Dict[str, Any] = {}
    split_records = assign_leakage_free_splits(
        unique_records,
        unseen_test_generators=args.unseen_test_generators,
        unseen_val_generators=args.unseen_val_generators,
        target_per_class=args.target_per_class,
        seed=args.seed,
        quota_report_out=quota_report,
    )
    materialize_and_write_manifest(
        split_records,
        output_dir=args.output_dir,
        manifest_only=not args.materialize,
        rejected_counts=total_rejected,
        dedup_stats=dedup_stats,
        target_per_class=args.target_per_class,
        quota_report=quota_report,
        strict_quotas=args.strict_quotas,
    )


if __name__ == "__main__":
    main()
