"""
TruthLens AI/ML — Known Demo Image Matcher
Blueprint Module 05 Extension: Fast recognition of known presentation demo images
without modifying, fine-tuning, or replacing the EfficientNet-B0 vision model.

Recognition Workflow:
1. Exact SHA-256 binary match.
2. If no exact match, perceptual difference hash (dHash) matching with configurable
   Hamming distance threshold and ambiguity detection.
3. Fallback to full EfficientNet-B0 inference when no confident match exists.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from PIL import Image, UnidentifiedImageError

from config.settings import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class DemoImageRecord:
    """Immutable representation of a registered presentation demo image."""
    file_path: Path
    relative_path: str
    filename: str
    label: str           # "genuine" or "ai_generated"
    display_label: str   # "REAL" or "FAKE"
    sha256: str
    dhash: str           # 16-character hex string representing 64-bit dHash
    format: str
    width: int
    height: int


@dataclass(frozen=True)
class DemoMatchResult:
    """Outcome of attempting to match an uploaded query image against the demo registry."""
    is_match: bool
    recognition_source: str             # "demo_image_match" or "efficientnet"
    match_type: Optional[str] = None    # "sha256", "perceptual_hash", or None
    label: Optional[str] = None         # "genuine", "ai_generated", or None
    display_label: Optional[str] = None # "REAL", "FAKE", or None
    matched_filename: Optional[str] = None
    hamming_distance: Optional[int] = None
    confidence: Optional[float] = None
    message: Optional[str] = None


def compute_sha256(raw_bytes: bytes) -> str:
    """Compute standard lowercase hexadecimal SHA-256 checksum."""
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """
    Compute 64-bit difference perceptual hash (dHash) for an image.

    Steps:
    1. Convert to grayscale ('L').
    2. Resize to (hash_size + 1, hash_size) using high-quality LANCZOS resampling.
    3. Compare adjacent horizontal pixels (pixel[c] > pixel[c + 1]).
    4. Encode 64 resulting boolean flags into a 16-character hex string.
    """
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
    """Compute bitwise Hamming distance between two 16-hex char dHash strings."""
    return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()


def resolve_demo_dir(custom_path: Optional[str | Path] = None) -> Optional[Path]:
    """
    Reliably locate the demo_images directory across diverse execution environments
    (root directory, ai-ml directory, tests, IDEs).
    """
    candidates: List[Path] = []
    if custom_path:
        candidates.append(Path(custom_path))

    configured = getattr(settings, "demo_images_dir", "datasets/demo_images")
    if configured:
        candidates.append(Path(configured))

    current_file = Path(__file__).resolve()
    # current_file: ai-ml/services/image_analysis/demo_matcher.py
    # parents[0]: image_analysis, parents[1]: services, parents[2]: ai-ml, parents[3]: project root
    if len(current_file.parents) >= 4:
        project_root = current_file.parents[3]
        candidates.append(project_root / "datasets" / "demo_images")
        candidates.append(project_root / "demo_images")

    candidates.append(Path.cwd() / "datasets" / "demo_images")
    candidates.append(Path.cwd() / "demo_images")

    for cand in candidates:
        try:
            if cand.exists() and cand.is_dir():
                real_sub = cand / "real"
                fake_sub = cand / "fake"
                if real_sub.exists() or fake_sub.exists():
                    return cand.resolve()
        except Exception:
            continue

    return None


class DemoImageRegistry:
    """
    In-memory registry of known demo images indexed by SHA-256 and perceptual dHash.
    Provides fast deterministic matching without altering neural network weights.
    """

    def __init__(self, demo_dir: Optional[str | Path] = None) -> None:
        self.demo_dir: Optional[Path] = resolve_demo_dir(demo_dir)
        self.records_by_sha256: Dict[str, DemoImageRecord] = {}
        self.records: List[DemoImageRecord] = []
        self.counts: Dict[str, int] = {"genuine": 0, "ai_generated": 0, "total": 0}
        self.load_registry()

    def load_registry(self) -> None:
        """Scan and register all demo images from the demo_images directory."""
        self.records_by_sha256.clear()
        self.records.clear()
        self.counts = {"genuine": 0, "ai_generated": 0, "total": 0}

        if not self.demo_dir or not self.demo_dir.exists():
            logger.warning("Demo image directory could not be located; matcher will operate as passthrough.")
            return

        logger.info("Registering known demo images from: %s", self.demo_dir)
        genuine_count = 0
        fake_count = 0

        # Scan recursively without assuming rigid flat depth
        for path in sorted(self.demo_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            rel_parts = [p.lower() for p in path.relative_to(self.demo_dir).parts]
            # Determine class label from parent folder hierarchy
            if any(part in ("real", "genuine") for part in rel_parts):
                label = "genuine"
                display_label = "REAL"
            elif any(part in ("fake", "ai_generated", "synthetic") for part in rel_parts):
                label = "ai_generated"
                display_label = "FAKE"
            else:
                logger.debug("Skipping image with undetermined class category: %s", path)
                continue

            try:
                raw_bytes = path.read_bytes()
                sha_hash = compute_sha256(raw_bytes)

                with Image.open(path) as img:
                    img.verify()

                with Image.open(path) as img:
                    img.load()
                    w, h = img.size
                    fmt = img.format or path.suffix.lstrip(".").upper()
                    dh = compute_dhash(img)

                record = DemoImageRecord(
                    file_path=path,
                    relative_path=str(path.relative_to(self.demo_dir)),
                    filename=path.name,
                    label=label,
                    display_label=display_label,
                    sha256=sha_hash,
                    dhash=dh,
                    format=fmt,
                    width=w,
                    height=h,
                )

                self.records_by_sha256[sha_hash] = record
                self.records.append(record)

                if label == "genuine":
                    genuine_count += 1
                else:
                    fake_count += 1

            except (UnidentifiedImageError, OSError, ValueError) as exc:
                logger.warning("Could not register demo image file '%s' (corrupt or unreadable): %s", path, exc)
            except Exception as exc:
                logger.warning("Unexpected error registering demo image '%s': %s", path, exc)

        self.counts["genuine"] = genuine_count
        self.counts["ai_generated"] = fake_count
        self.counts["total"] = len(self.records)

        logger.info(
            "DemoImageRegistry successfully loaded: %d genuine, %d AI-generated (%d total images).",
            genuine_count, fake_count, len(self.records),
        )

    def match(
        self,
        image_bytes: Optional[bytes] = None,
        pil_image: Optional[Image.Image] = None,
        max_hamming_distance: Optional[int] = None,
        ambiguity_margin: Optional[int] = None,
    ) -> DemoMatchResult:
        """
        Check whether an input image matches any registered demo image.

        Workflow:
        1. Exact SHA-256 lookup (fastest, bit-perfect).
        2. Perceptual dHash comparison with conservative threshold and ambiguity check.
        3. Fallback to EfficientNet inference when no confident match exists.
        """
        if not getattr(settings, "demo_match_enabled", True) or not self.records:
            return DemoMatchResult(
                is_match=False,
                recognition_source="efficientnet",
                message="Demo matcher disabled or registry empty; defaulting to AI model.",
            )

        max_dist = (
            max_hamming_distance
            if max_hamming_distance is not None
            else getattr(settings, "demo_match_max_hamming_distance", 6)
        )
        amb_margin = (
            ambiguity_margin
            if ambiguity_margin is not None
            else getattr(settings, "demo_match_ambiguity_margin", 2)
        )

        # 1. Exact SHA-256 match
        if image_bytes is not None:
            query_sha = compute_sha256(image_bytes)
            exact_rec = self.records_by_sha256.get(query_sha)
            if exact_rec is not None:
                logger.info(
                    "Demo image matched via exact SHA-256 checksum: %s (%s)",
                    exact_rec.filename, exact_rec.display_label,
                )
                return DemoMatchResult(
                    is_match=True,
                    recognition_source="demo_image_match",
                    match_type="sha256",
                    label=exact_rec.label,
                    display_label=exact_rec.display_label,
                    matched_filename=exact_rec.filename,
                    hamming_distance=0,
                    confidence=1.0,
                    message=f"Exact SHA-256 match with demo image '{exact_rec.filename}'.",
                )

        # 2. Perceptual dHash match (for resized or recompressed copies)
        if pil_image is None and image_bytes is not None:
            try:
                import io
                with Image.open(io.BytesIO(image_bytes)) as decoded:
                    decoded.load()
                    pil_image = decoded.copy()
            except Exception as exc:
                logger.debug("Failed to decode image bytes for perceptual hash matching: %s", exc)
                return DemoMatchResult(
                    is_match=False,
                    recognition_source="efficientnet",
                    message="Failed to decode image for perceptual matching; continuing to model.",
                )

        if pil_image is not None:
            try:
                query_dhash = compute_dhash(pil_image)
            except Exception as exc:
                logger.warning("Could not compute dHash for query image: %s", exc)
                return DemoMatchResult(
                    is_match=False,
                    recognition_source="efficientnet",
                    message="dHash computation failed; continuing to model.",
                )

            # Measure distances against all registered records
            candidates: List[Tuple[int, DemoImageRecord]] = []
            for rec in self.records:
                dist = dhash_hamming_distance(query_dhash, rec.dhash)
                if dist <= max_dist:
                    candidates.append((dist, rec))

            if candidates:
                candidates.sort(key=lambda item: item[0])
                best_dist, best_rec = candidates[0]

                # Ambiguity check: if another candidate with a DIFFERENT label is close, do not guess
                conflicting = [
                    rec for dist, rec in candidates
                    if dist <= best_dist + amb_margin and rec.label != best_rec.label
                ]

                if conflicting:
                    logger.warning(
                        "Ambiguous perceptual match detected: best candidate '%s' (%s, dist=%d) "
                        "conflicts with '%s' (%s, dist=%d). Refusing match to avoid false positive.",
                        best_rec.filename, best_rec.label, best_dist,
                        conflicting[0].filename, conflicting[0].label,
                        dhash_hamming_distance(query_dhash, conflicting[0].dhash),
                    )
                    return DemoMatchResult(
                        is_match=False,
                        recognition_source="efficientnet",
                        message="Ambiguous perceptual similarity detected across opposing labels; falling back to AI model.",
                    )

                # Unambiguous perceptual match within conservative threshold
                match_confidence = round(1.0 - (best_dist / 64.0), 4)
                logger.info(
                    "Demo image matched via perceptual dHash: %s (%s) with distance=%d (threshold=%d)",
                    best_rec.filename, best_rec.display_label, best_dist, max_dist,
                )
                return DemoMatchResult(
                    is_match=True,
                    recognition_source="demo_image_match",
                    match_type="perceptual_hash",
                    label=best_rec.label,
                    display_label=best_rec.display_label,
                    matched_filename=best_rec.filename,
                    hamming_distance=best_dist,
                    confidence=match_confidence,
                    message=f"Perceptual dHash match with '{best_rec.filename}' (Hamming distance: {best_dist}).",
                )

        return DemoMatchResult(
            is_match=False,
            recognition_source="efficientnet",
            message="No registered demo image match; evaluated by EfficientNet-B0 AI model.",
        )


# Module-level registry singleton
_demo_registry: Optional[DemoImageRegistry] = None


def get_demo_registry() -> DemoImageRegistry:
    """Return the global DemoImageRegistry singleton (lazy initialized)."""
    global _demo_registry
    if _demo_registry is None:
        _demo_registry = DemoImageRegistry()
    return _demo_registry


def reset_demo_registry() -> None:
    """Reset the singleton instance (useful for test isolation)."""
    global _demo_registry
    _demo_registry = None
