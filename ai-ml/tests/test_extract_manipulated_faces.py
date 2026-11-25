"""Automated tests for Video-to-Face Extraction Pipeline (FaceForensics++, Celeb-DF-v2).

Covers:
- Dataset subset resolution & paired identity token grouping
- Face detection and margin-expanded square cropping
- Zero center-crop fallback enforcement on face detection failure
- Minimum face size and intra-video duplicate suppression
- Corrupt video, unreadable frame, and error handling
- End-to-end extraction and Stage 1 manifest compatibility
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Tuple

import cv2
import numpy as np
from PIL import Image
import pytest

AI_ML_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ML_ROOT))

import extract_manipulated_faces as emf  # noqa: E402
import human_face_dataset as hfd  # noqa: E402


def _draw_synthetic_face(
    canvas_size: Tuple[int, int] = (300, 300),
    center: Tuple[int, int] = (150, 150),
    radius: int = 70,
) -> np.ndarray:
    """Draw a face-like pattern detectable by OpenCV Haar Cascade."""
    img = np.zeros((canvas_size[1], canvas_size[0], 3), dtype=np.uint8)
    cx, cy = center
    # Head contour
    cv2.circle(img, (cx, cy), radius, (220, 220, 220), -1)
    # Eyes
    eye_offset_x = int(radius * 0.4)
    eye_offset_y = int(radius * 0.25)
    eye_r = max(4, int(radius * 0.12))
    cv2.circle(img, (cx - eye_offset_x, cy - eye_offset_y), eye_r, (40, 40, 40), -1)
    cv2.circle(img, (cx + eye_offset_x, cy - eye_offset_y), eye_r, (40, 40, 40), -1)
    # Mouth
    mouth_w = int(radius * 0.45)
    mouth_h = int(radius * 0.18)
    cv2.ellipse(
        img,
        (cx, cy + int(radius * 0.4)),
        (mouth_w, mouth_h),
        0,
        0,
        180,
        (40, 40, 40),
        -1,
    )
    return img


def _create_synthetic_video(
    video_path: Path,
    num_frames: int = 20,
    fps: float = 10.0,
    has_face: bool = True,
    resolution: Tuple[int, int] = (320, 320),
) -> Path:
    """Create a temporary MP4 video with either face frames or blank noise frames."""
    video_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, fps, resolution)
    for i in range(num_frames):
        if has_face:
            # Shift slightly across frames
            cx = resolution[0] // 2 + (i % 3) * 2
            cy = resolution[1] // 2 + (i % 2) * 2
            frame = _draw_synthetic_face(canvas_size=resolution, center=(cx, cy), radius=65)
        else:
            # Plain noise / blank frame (no face features)
            frame = np.full((resolution[1], resolution[0], 3), 40, dtype=np.uint8)
        out.write(frame)
    out.release()
    return video_path


class TestVideoMetadataResolution:
    """Verify dataset taxonomy, manipulation method, and paired identity grouping."""

    def test_ffpp_paired_videos_share_target_clip_identity(self) -> None:
        deepfake_path = Path("FaceForensics++/manipulated_sequences/Deepfakes/c23/videos/042_056.mp4")
        original_path = Path("FaceForensics++/original_sequences/youtube/c23/videos/042.mp4")

        meta_fake = emf.resolve_video_metadata(deepfake_path)
        meta_real = emf.resolve_video_metadata(original_path)

        assert meta_fake["class_name"] == "manipulated"
        assert meta_fake["label"] == 2
        assert meta_fake["source_subset"] == "deepfakes"
        assert meta_fake["source_container"] == "ff_pp"
        assert meta_fake["source_group_id"] == "ffpp::clip::042"
        assert "ffpp::clip::042" in meta_fake["identity_tokens"]
        assert "ffpp::clip::056" in meta_fake["identity_tokens"]

        assert meta_real["class_name"] == "genuine"
        assert meta_real["label"] == 0
        assert meta_real["source_subset"] == "original_sequences"
        assert meta_real["source_container"] == "ff_pp"
        assert meta_real["source_group_id"] == "ffpp::clip::042"
        assert meta_real["identity_tokens"] == ["ffpp::clip::042"]

        # Shared token guarantee
        assert set(meta_real["identity_tokens"]).issubset(set(meta_fake["identity_tokens"]))

    def test_celebdf_paired_actors_share_actor_identity(self) -> None:
        synth_path = Path("Celeb-DF-v2/Celeb-synthesis/id3_id7_0001.mp4")
        real_path = Path("Celeb-DF-v2/Celeb-real/id3_0001.mp4")

        meta_synth = emf.resolve_video_metadata(synth_path)
        meta_real = emf.resolve_video_metadata(real_path)

        assert meta_synth["class_name"] == "manipulated"
        assert meta_synth["label"] == 2
        assert meta_synth["source_subset"] == "celeb_synthesis"
        assert meta_synth["source_group_id"] == "celebdf::actor::id3"
        assert "celebdf::actor::id3" in meta_synth["identity_tokens"]
        assert "celebdf::actor::id7" in meta_synth["identity_tokens"]

        assert meta_real["class_name"] == "genuine"
        assert meta_real["label"] == 0
        assert meta_real["source_subset"] == "celeb_real"
        assert meta_real["source_group_id"] == "celebdf::actor::id3"
        assert meta_real["identity_tokens"] == ["celebdf::actor::id3"]

    def test_other_manipulation_methods_mapped_correctly(self) -> None:
        for method in ("faceswap", "face2face", "neuraltextures", "faceshifter"):
            p = Path(f"FaceForensics++/manipulated_sequences/{method}/c23/videos/001_002.mp4")
            meta = emf.resolve_video_metadata(p)
            assert meta["class_name"] == "manipulated"
            assert meta["label"] == 2
            assert meta["source_subset"] == method


class TestFaceDetectionAndCropAlignment:
    """Verify offline face detection, margin-expanded square cropping, and failure handling."""

    def test_haar_detector_finds_face_and_confidence(self) -> None:
        detector = emf.HaarFaceDetector(min_size=40)
        face_img = _draw_synthetic_face(canvas_size=(300, 300), center=(150, 150), radius=70)
        detections = detector.detect(face_img)

        assert len(detections) >= 1
        top = detections[0]
        assert top.width >= 40
        assert top.height >= 40
        assert 0.0 <= top.confidence <= 1.0

    def test_detector_returns_empty_on_blank_frame(self) -> None:
        detector = emf.HaarFaceDetector(min_size=40)
        blank = np.zeros((300, 300, 3), dtype=np.uint8)
        detections = detector.detect(blank)
        assert len(detections) == 0

    def test_square_crop_with_margin_and_reflection_padding(self) -> None:
        # Place face near image boundary to test boundary padding
        face_img = _draw_synthetic_face(canvas_size=(200, 200), center=(20, 20), radius=40)
        det = emf.FaceDetection(x=0, y=0, width=50, height=50, confidence=0.9)

        crop = emf.extract_square_face_crop(face_img, det, crop_size=256, margin_percent=0.3)
        assert crop.shape == (256, 256, 3)

    def test_never_substitutes_center_crop_on_face_detection_failure(self, tmp_path: Path) -> None:
        """When face detection fails, the pipeline MUST skip the frame, NOT invent a center crop."""
        no_face_video = tmp_path / "videos" / "manipulated_sequences" / "Deepfakes" / "010_020.mp4"
        _create_synthetic_video(no_face_video, num_frames=10, has_face=False)

        out_dir = tmp_path / "extracted_faces"
        detector = emf.HaarFaceDetector(min_size=50)

        records, stats = emf.extract_faces_from_video(
            video_path=no_face_video,
            output_dir=out_dir,
            detector=detector,
            frame_interval=2,
        )

        assert len(records) == 0
        assert stats["faces_extracted"] == 0
        assert stats["frames_no_face"] > 0
        # Ensure zero crop files were saved to disk
        assert len(list(out_dir.rglob("*.jpg"))) == 0


class TestDeduplicationAndFiltering:
    """Verify minimum face size, duplicate crop suppression, and frame limits."""

    def test_intra_video_duplicate_crops_suppressed(self, tmp_path: Path) -> None:
        # A static video where every frame is identical
        static_video = tmp_path / "videos" / "Celeb-DF-v2" / "Celeb-synthesis" / "id1_id2_0001.mp4"
        _create_synthetic_video(static_video, num_frames=30, has_face=True)

        out_dir = tmp_path / "extracted"
        detector = emf.HaarFaceDetector(min_size=40)

        records, stats = emf.extract_faces_from_video(
            video_path=static_video,
            output_dir=out_dir,
            detector=detector,
            frame_interval=5,
            dedup_threshold=4,  # Suppress identical/near-identical crops
        )

        # 6 sampled frames (30 / 5); only first frame crop should be saved, rest skipped as duplicates
        assert stats["faces_extracted"] == 1
        assert stats["duplicate_crops_skipped"] >= 1
        assert len(records) == 1

    def test_min_face_size_filters_small_detections(self, tmp_path: Path) -> None:
        video = tmp_path / "small_face.mp4"
        _create_synthetic_video(video, num_frames=5, resolution=(400, 400), has_face=True)

        out_dir = tmp_path / "extracted_small"
        detector = emf.HaarFaceDetector(min_size=30)

        # Require minimum face size of 350px (drawn face is around ~130px) -> all rejected
        records, stats = emf.extract_faces_from_video(
            video_path=video,
            output_dir=out_dir,
            detector=detector,
            frame_interval=2,
            min_face_size=350,
        )
        assert len(records) == 0
        assert stats["faces_too_small"] > 0


class TestFaultToleranceAndCorruptVideoHandling:
    """Verify graceful handling of corrupt, zero-byte, and broken video streams."""

    def test_zero_byte_video_does_not_crash_batch(self, tmp_path: Path) -> None:
        corrupt_video = tmp_path / "corrupt.mp4"
        corrupt_video.write_bytes(b"")

        detector = emf.HaarFaceDetector(min_size=40)
        records, stats = emf.extract_faces_from_video(
            video_path=corrupt_video,
            output_dir=tmp_path / "out",
            detector=detector,
        )
        assert records == []
        assert stats["status"] == "failed_open"

    def test_batch_processes_valid_videos_even_if_corrupt_video_present(self, tmp_path: Path) -> None:
        v_dir = tmp_path / "batch_videos"
        v_dir.mkdir(parents=True, exist_ok=True)

        # Video 1: Corrupt
        (v_dir / "bad_video.mp4").write_bytes(b"NOT_A_VALID_MP4_HEADER")

        # Video 2: Valid with face
        good_video = v_dir / "FaceForensics++" / "manipulated_sequences" / "Deepfakes" / "001_002.mp4"
        _create_synthetic_video(good_video, num_frames=10, has_face=True)

        out_dir = tmp_path / "batch_out"
        manifest = emf.process_video_extraction(
            input_source=v_dir,
            output_dir=out_dir,
            frame_interval=3,
            max_frames_per_video=5,
            dedup_threshold=0,  # Allow extraction for test
        )

        assert manifest["summary"]["total_videos_found"] == 2
        assert manifest["summary"]["videos_failed"] == 1
        assert manifest["summary"]["videos_processed"] == 1
        assert manifest["summary"]["total_faces_extracted"] > 0


class TestManifestCompatibilityWithStage1:
    """Verify output manifest schema compatibility with Stage 1 dataset and evaluation scripts."""

    def test_extracted_manifest_schema_and_image_properties(self, tmp_path: Path) -> None:
        input_root = tmp_path / "raw_videos"
        v1 = input_root / "FaceForensics++" / "manipulated_sequences" / "Deepfakes" / "042_056.mp4"
        v2 = input_root / "FaceForensics++" / "original_sequences" / "youtube" / "042.mp4"
        _create_synthetic_video(v1, num_frames=15, has_face=True)
        _create_synthetic_video(v2, num_frames=15, has_face=True)

        out_dir = tmp_path / "stage1_compatible_out"
        manifest_data = emf.process_video_extraction(
            input_source=input_root,
            output_dir=out_dir,
            frame_interval=5,
            max_frames_per_video=4,
            dedup_threshold=0,
            crop_size=256,
        )

        # 1. Manifest structure checks
        assert manifest_data["schema_version"] == "1.1.0"
        assert manifest_data["class_names"] == ["genuine", "ai_generated", "manipulated"]
        assert manifest_data["class_to_id"] == {"genuine": 0, "ai_generated": 1, "manipulated": 2}
        assert (out_dir / "extracted_faces_manifest.json").exists()
        assert (out_dir / "extraction_report.json").exists()

        images = manifest_data["images"]
        assert len(images) > 0

        # 2. Check individual record fields required by human_face_dataset.py
        for item in images:
            assert item["class_name"] in ("genuine", "manipulated")
            assert item["label"] in (0, 2)
            assert item["dimensions"] == [256, 256]
            assert "source_group_id" in item
            assert "identity_tokens" in item
            assert len(item["identity_tokens"]) >= 1
            assert "sha256" in item
            assert "md5" in item
            assert "dhash" in item
            assert (out_dir / item["image_path"]).exists()

            # Confirm image is decodable by PIL and has exact 256x256 dimensions
            with Image.open(out_dir / item["image_path"]) as img:
                assert img.size == (256, 256)
                assert img.format == "JPEG"

        # 3. Check shared group ID between paired videos
        deepfake_items = [it for it in images if it["source_subset"] == "deepfakes"]
        real_items = [it for it in images if it["source_subset"] == "original_sequences"]
        assert len(deepfake_items) > 0
        assert len(real_items) > 0

        assert deepfake_items[0]["source_group_id"] == "ffpp::clip::042"
        assert real_items[0]["source_group_id"] == "ffpp::clip::042"
