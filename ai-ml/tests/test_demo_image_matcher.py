"""
TruthLens AI/ML — Unit Tests for Known Demo Image Matching
Tests the DemoImageRegistry and full service pipeline integration:
1. Exact match of a genuine demo image (SHA-256).
2. Exact match of an AI-generated demo image (SHA-256).
3. Resized or recompressed copy recognition (perceptual dHash).
4. Unknown image fallback to EfficientNet-B0.
5. Corrupt or unsupported file handling.
6. Correct label assignment from directory structure.
7. Ambiguous perceptual match not producing a false classification.
8. End-to-end service pipeline behavior with demo vs unknown images.
"""

from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from services.image_analysis.demo_matcher import (
    DemoImageRegistry,
    compute_dhash,
    compute_sha256,
    dhash_hamming_distance,
)
from services.image_analysis.service import analyze_image_bytes


def _create_synthetic_image(seed_pattern: int, size: tuple[int, int] = (128, 128)) -> Image.Image:
    """Create a deterministic synthetic image with distinct visual features."""
    img = Image.new("RGB", size, color=(seed_pattern % 255, (seed_pattern * 3) % 255, (seed_pattern * 7) % 255))
    draw = ImageDraw.Draw(img)
    # Draw geometric shapes to establish distinct spatial gradient transitions
    draw.rectangle([10, 10, size[0] - 10, size[1] // 2], fill=((seed_pattern * 13) % 255, 120, 200))
    draw.ellipse([size[0] // 4, size[1] // 4, 3 * size[0] // 4, 3 * size[1] // 4], fill=(220, (seed_pattern * 17) % 255, 30))
    draw.line([0, 0, size[0], size[1]], fill=(255, 255, 255), width=3)
    return img


@pytest.fixture
def mock_demo_env(tmp_path: Path) -> Path:
    """Create a self-contained temporary demo image dataset with real and fake images."""
    demo_dir = tmp_path / "test_demo_images"
    real_dir = demo_dir / "real"
    fake_dir = demo_dir / "fake"
    real_dir.mkdir(parents=True)
    fake_dir.mkdir(parents=True)

    # Genuine synthetic images
    for i in range(1, 4):
        img = _create_synthetic_image(seed_pattern=i * 20)
        img.save(real_dir / f"real_{i:02d}.jpg", format="JPEG", quality=95)

    # Fake synthetic images (distinct seeds)
    for i in range(1, 4):
        img = _create_synthetic_image(seed_pattern=100 + i * 20)
        img.save(fake_dir / f"fake_{i:02d}.jpg", format="JPEG", quality=95)

    return demo_dir


def test_exact_match_genuine_demo_image(mock_demo_env: Path):
    """Test 1: Exact SHA-256 match for a registered genuine demo image."""
    registry = DemoImageRegistry(demo_dir=mock_demo_env)
    assert registry.counts["genuine"] == 3
    assert registry.counts["ai_generated"] == 3

    target_file = mock_demo_env / "real" / "real_01.jpg"
    target_bytes = target_file.read_bytes()

    result = registry.match(image_bytes=target_bytes)
    assert result.is_match is True
    assert result.recognition_source == "demo_image_match"
    assert result.match_type == "sha256"
    assert result.label == "genuine"
    assert result.display_label == "REAL"
    assert result.matched_filename == "real_01.jpg"
    assert result.hamming_distance == 0
    assert result.confidence == 1.0


def test_exact_match_fake_demo_image(mock_demo_env: Path):
    """Test 2: Exact SHA-256 match for a registered AI-generated demo image."""
    registry = DemoImageRegistry(demo_dir=mock_demo_env)

    target_file = mock_demo_env / "fake" / "fake_02.jpg"
    target_bytes = target_file.read_bytes()

    result = registry.match(image_bytes=target_bytes)
    assert result.is_match is True
    assert result.recognition_source == "demo_image_match"
    assert result.match_type == "sha256"
    assert result.label == "ai_generated"
    assert result.display_label == "FAKE"
    assert result.matched_filename == "fake_02.jpg"
    assert result.hamming_distance == 0
    assert result.confidence == 1.0


def test_perceptual_hash_resized_or_recompressed_copy(mock_demo_env: Path):
    """Test 3: Recognize modified copies (resized and recompressed) via perceptual dHash."""
    registry = DemoImageRegistry(demo_dir=mock_demo_env)
    target_file = mock_demo_env / "real" / "real_01.jpg"
    orig_bytes = target_file.read_bytes()

    # Create resized & recompressed version
    with Image.open(target_file) as img:
        modified = img.resize((96, 96))
        buf = io.BytesIO()
        modified.save(buf, format="JPEG", quality=75)
        modified_bytes = buf.getvalue()

    # Verify SHA-256 changed
    assert compute_sha256(modified_bytes) != compute_sha256(orig_bytes)

    result = registry.match(image_bytes=modified_bytes, max_hamming_distance=6)
    assert result.is_match is True
    assert result.recognition_source == "demo_image_match"
    assert result.match_type == "perceptual_hash"
    assert result.label == "genuine"
    assert result.display_label == "REAL"
    assert result.matched_filename == "real_01.jpg"
    assert result.hamming_distance is not None
    assert result.hamming_distance <= 6
    assert result.confidence is not None and result.confidence >= 0.85


def test_unknown_image_fallback_to_efficientnet(mock_demo_env: Path):
    """Test 4: Unregistered, distinct image falls back to EfficientNet."""
    registry = DemoImageRegistry(demo_dir=mock_demo_env)

    # Completely different image
    unknown = Image.new("RGB", (100, 100), color=(15, 230, 180))
    draw = ImageDraw.Draw(unknown)
    draw.rectangle([30, 30, 70, 70], fill=(240, 10, 80))
    buf = io.BytesIO()
    unknown.save(buf, format="PNG")
    unknown_bytes = buf.getvalue()

    result = registry.match(image_bytes=unknown_bytes)
    assert result.is_match is False
    assert result.recognition_source == "efficientnet"
    assert result.match_type is None
    assert result.label is None
    assert result.display_label is None


def test_corrupt_or_unsupported_image_handling(tmp_path: Path):
    """Test 5: Corrupt and unsupported files are handled safely without crashing."""
    demo_dir = tmp_path / "corrupt_demo_env"
    real_dir = demo_dir / "real"
    real_dir.mkdir(parents=True)

    # 1. Valid image
    valid_img = _create_synthetic_image(55)
    valid_img.save(real_dir / "valid.jpg", format="JPEG")

    # 2. Corrupt file with .jpg extension
    corrupt_file = real_dir / "corrupt.jpg"
    corrupt_file.write_bytes(b"CORRUPT_HEADER_AND_INVALID_PAYLOAD_DATA_123456789")

    # 3. Unsupported text file
    txt_file = real_dir / "notes.txt"
    txt_file.write_text("not an image")

    # Should register valid image and skip corrupt/text files safely
    registry = DemoImageRegistry(demo_dir=demo_dir)
    assert registry.counts["total"] == 1
    assert registry.counts["genuine"] == 1
    assert "valid.jpg" in [r.filename for r in registry.records]


def test_correct_label_assignment_from_directory(tmp_path: Path):
    """Test 6: Verify correct label assignment from nested and sub-directory structure."""
    demo_dir = tmp_path / "nested_demo_env"
    (demo_dir / "real" / "batch1").mkdir(parents=True)
    (demo_dir / "fake" / "batch2").mkdir(parents=True)

    img1 = _create_synthetic_image(10)
    img1.save(demo_dir / "real" / "batch1" / "nested_real.png", format="PNG")

    img2 = _create_synthetic_image(200)
    img2.save(demo_dir / "fake" / "batch2" / "nested_fake.png", format="PNG")

    registry = DemoImageRegistry(demo_dir=demo_dir)
    assert registry.counts["genuine"] == 1
    assert registry.counts["ai_generated"] == 1

    rec_real = registry.records_by_sha256[compute_sha256((demo_dir / "real" / "batch1" / "nested_real.png").read_bytes())]
    assert rec_real.label == "genuine"
    assert rec_real.display_label == "REAL"

    rec_fake = registry.records_by_sha256[compute_sha256((demo_dir / "fake" / "batch2" / "nested_fake.png").read_bytes())]
    assert rec_fake.label == "ai_generated"
    assert rec_fake.display_label == "FAKE"


def test_ambiguous_perceptual_match_not_producing_false_classification(tmp_path: Path):
    """Test 7: Ambiguous perceptual match between conflicting labels is rejected."""
    demo_dir = tmp_path / "ambiguous_demo_env"
    real_dir = demo_dir / "real"
    fake_dir = demo_dir / "fake"
    real_dir.mkdir(parents=True)
    fake_dir.mkdir(parents=True)

    # Create a base image
    base = _create_synthetic_image(77, size=(64, 64))
    base.save(real_dir / "ambig_real.jpg", format="JPEG", quality=90)

    # Create a near-twin image for fake (only slightly altered)
    near_twin = base.copy()
    draw = ImageDraw.Draw(near_twin)
    draw.point((1, 1), fill=(255, 255, 255))
    near_twin.save(fake_dir / "ambig_fake.jpg", format="JPEG", quality=90)

    registry = DemoImageRegistry(demo_dir=demo_dir)
    assert registry.counts["genuine"] == 1
    assert registry.counts["ai_generated"] == 1

    # Query with a third image equidistant from both
    query = base.copy()
    draw = ImageDraw.Draw(query)
    draw.point((2, 2), fill=(250, 250, 250))
    buf = io.BytesIO()
    query.save(buf, format="JPEG", quality=90)
    query_bytes = buf.getvalue()

    # Perceptual match should detect conflict and refuse false match
    result = registry.match(image_bytes=query_bytes, max_hamming_distance=10, ambiguity_margin=2)
    assert result.is_match is False
    assert result.recognition_source == "efficientnet"


def test_end_to_end_service_pipeline():
    """Test 8: Full service analyze_image_bytes pipeline executes with correct metadata."""
    # Test on a registered real demo image
    real_demo = Path("datasets/demo_images/real/real_01.jpg")
    if real_demo.exists():
        resp_real = analyze_image_bytes(real_demo.read_bytes(), "real_01.jpg")
        assert resp_real.status == "COMPLETED"
        assert resp_real.recognition_source == "demo_image_match"
        assert resp_real.demo_match is True
        assert resp_real.demo_match_label == "genuine"
        assert resp_real.ai_prob == 0.0
        assert resp_real.evidence["demo_match"] is True
        assert resp_real.evidence["details"]["recognition_source"] == "demo_image_match"
        assert "Known Demo Image – REAL" in resp_real.evidence["verdict_category"]

    # Test on a registered fake demo image
    fake_demo = Path("datasets/demo_images/fake/fake_01.jpeg")
    if fake_demo.exists():
        resp_fake = analyze_image_bytes(fake_demo.read_bytes(), "fake_01.jpeg")
        assert resp_fake.status == "COMPLETED"
        assert resp_fake.recognition_source == "demo_image_match"
        assert resp_fake.demo_match is True
        assert resp_fake.demo_match_label == "ai_generated"
        assert resp_fake.ai_prob == 1.0
        assert resp_fake.evidence["demo_match"] is True
        assert "Known Demo Image – FAKE" in resp_fake.evidence["verdict_category"]

    # Test on an unregistered image
    unregistered_img = _create_synthetic_image(999)
    buf = io.BytesIO()
    unregistered_img.save(buf, format="JPEG")
    resp_unreg = analyze_image_bytes(buf.getvalue(), "synthetic_unreg.jpg")
    assert resp_unreg.status == "COMPLETED"
    assert resp_unreg.recognition_source == "efficientnet"
    assert resp_unreg.demo_match is False
    assert resp_unreg.demo_match_label is None
