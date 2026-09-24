import os
import cv2
import numpy as np
import tempfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.image_preprocessor import ImagePreprocessor
from app.services.ocr_engine import OcrEngine
from app.services.video_ocr_pipeline import VideoOcrPipeline
from app.services.ocr_pipeline import OcrAnalysisPipeline
from app.schemas import OcrAnalysisResult


# =============================================================================
# Synthetic Media Fixtures for OCR Testing
# =============================================================================

def create_synthetic_text_image(text: str = "BREAKING NEWS ALERT", width: int = 400, height: int = 150) -> np.ndarray:
    """Creates a high-contrast white image containing rendered black text."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, (30, 90), font, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
    return img


def create_blank_image(width: int = 200, height: int = 200) -> np.ndarray:
    """Creates a uniform blank image with zero visual text."""
    return np.full((height, width, 3), 240, dtype=np.uint8)


def create_synthetic_video_with_text(video_path: str, duration_sec: float = 2.0, fps: float = 25.0) -> None:
    """Creates a synthetic MP4 video with a persistent lower-third news banner."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    num_frames = int(duration_sec * fps)
    out = cv2.VideoWriter(video_path, fourcc, fps, (320, 240))

    for i in range(num_frames):
        frame = np.full((240, 320, 3), 100, dtype=np.uint8)
        # Background gradient or shape
        cv2.circle(frame, (160, 100), 50, (180, 140, 120), -1)
        # Lower third banner rectangle
        cv2.rectangle(frame, (10, 180), (310, 230), (20, 20, 180), -1)
        # White text inside banner
        cv2.putText(frame, "TRUTHLENS VERIFIED", (25, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        out.write(frame)

    out.release()


# =============================================================================
# Unit Tests
# =============================================================================

def test_image_preprocessor_clahe_and_binarization():
    """Verifies image preprocessing: grayscale conversion, CLAHE, denoising, and binarization."""
    preprocessor = ImagePreprocessor(max_dimension=512)
    img_rgb = create_synthetic_text_image("SAMPLE TEXT", width=300, height=100)

    prep = preprocessor.preprocess(img_rgb)
    assert prep.gray.shape == (100, 300)
    assert prep.binarized.shape == (100, 300)
    assert prep.scale_factor == 1.0
    assert "CLAHE contrast enhancement" in prep.applied_steps
    assert "Adaptive & Otsu binarization" in prep.applied_steps


def test_image_preprocessor_resizing():
    """Verifies that oversized images are safely scaled down preserving aspect ratio."""
    preprocessor = ImagePreprocessor(max_dimension=200)
    large_img = np.full((600, 400, 3), 200, dtype=np.uint8)

    prep = preprocessor.preprocess(large_img)
    assert prep.scale_factor < 1.0
    assert max(prep.processed_dimensions) <= 200
    assert prep.processed_dimensions[1] == 200  # height was 600, scaled to 200
    assert prep.processed_dimensions[0] == 133  # width was 400, scaled to ~133


def test_image_preprocessor_deskewing():
    """Verifies that skewed text blocks are detected and deskewed."""
    preprocessor = ImagePreprocessor()
    img_rgb = create_synthetic_text_image("TILTED HEADLINE", width=400, height=200)

    # Artificially rotate image by 5 degrees
    center = (200, 100)
    rot_mat = cv2.getRotationMatrix2D(center, 5.0, 1.0)
    tilted_rgb = cv2.warpAffine(img_rgb, rot_mat, (400, 200), borderValue=(255, 255, 255))

    prep = preprocessor.preprocess(tilted_rgb)
    assert prep.skew_angle is not None
    assert prep.gray.shape == (200, 400)


def test_ocr_engine_extract_text_regions():
    """Verifies that OCR engine identifies candidate text regions with bounding boxes."""
    preprocessor = ImagePreprocessor()
    ocr_engine = OcrEngine()

    img_rgb = create_synthetic_text_image("AUTHENTIC REPORT 2026", width=400, height=120)
    prep = preprocessor.preprocess(img_rgb)

    regions, lang, engine_name = ocr_engine.extract_text(prep)
    assert len(regions) >= 1
    assert engine_name in ["EasyOCR", "Tesseract", "OpenCV-Morphological-OCR"]

    first_region = regions[0]
    assert first_region.confidence >= 0.20
    assert first_region.bounding_box.width > 0
    assert first_region.bounding_box.height > 0
    assert len(first_region.bounding_box.normalized_bbox) == 4
    assert len(first_region.bounding_box.polygon) == 4


def test_ocr_engine_blank_image_returns_empty():
    """Verifies that an image without text returns zero regions."""
    preprocessor = ImagePreprocessor()
    ocr_engine = OcrEngine()

    blank_rgb = create_blank_image(width=200, height=100)
    prep = preprocessor.preprocess(blank_rgb)

    regions, lang, _ = ocr_engine.extract_text(prep)
    assert len(regions) == 0


def test_video_ocr_pipeline_frame_sampling_and_deduplication():
    """Verifies video OCR sampling and temporal segment consolidation."""
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "test_ocr_video.mp4")

    try:
        create_synthetic_video_with_text(video_path, duration_sec=2.0, fps=25.0)

        pipeline = VideoOcrPipeline(sample_interval_sec=1.0, max_frames=5)
        regions, lang, eng, frames_count, dims, prep_steps = pipeline.process_video(video_path)

        assert frames_count >= 2
        assert dims == (320, 240)
        assert len(regions) >= 1
        # Text present across consecutive frames should have start_time and end_time
        first_region = regions[0]
        assert first_region.start_time is not None
        assert first_region.end_time is not None
        assert first_region.end_time >= first_region.start_time

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        os.rmdir(temp_dir)


def test_ocr_analysis_pipeline_image_end_to_end():
    """Verifies end-to-end OCR analysis on a static image file."""
    temp_dir = tempfile.mkdtemp()
    img_path = os.path.join(temp_dir, "test_banner.png")

    try:
        img_rgb = create_synthetic_text_image("BREAKING FACT CHECK", width=350, height=120)
        cv2.imwrite(img_path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))

        pipeline = OcrAnalysisPipeline()
        result = pipeline.analyze(img_path)

        assert isinstance(result, OcrAnalysisResult)
        assert result.status == "COMPLETED"
        assert result.regions_count >= 1
        assert result.confidence_score >= 0.20
        assert result.evidence.media_type == "IMAGE"
        assert result.evidence.image_width == 350
        assert result.evidence.image_height == 120

    finally:
        if os.path.exists(img_path):
            os.remove(img_path)
        os.rmdir(temp_dir)


def test_ocr_analysis_pipeline_video_end_to_end():
    """Verifies end-to-end OCR analysis on a video file."""
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "test_video.mp4")

    try:
        create_synthetic_video_with_text(video_path, duration_sec=1.5, fps=25.0)

        pipeline = OcrAnalysisPipeline()
        result = pipeline.analyze(video_path)

        assert isinstance(result, OcrAnalysisResult)
        assert result.status == "COMPLETED"
        assert result.evidence.media_type == "VIDEO"
        assert result.evidence.frames_analyzed >= 1

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        os.rmdir(temp_dir)


# =============================================================================
# FastAPI Endpoint Tests
# =============================================================================

@pytest.fixture
def client():
    return TestClient(app)


def test_api_analyze_ocr_image_success(client):
    """Verifies POST /api/v1/analyze/ocr with a valid image file."""
    img_rgb = create_synthetic_text_image("ELECTION INTEGRITY 2026", width=360, height=100)
    _, img_encoded = cv2.imencode(".png", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
    img_bytes = img_encoded.tobytes()

    response = client.post(
        "/api/v1/analyze/ocr",
        files={"file": ("banner.png", img_bytes, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert "extracted_text" in data
    assert "regions" in data
    assert data["regions_count"] >= 1
    assert data["evidence"]["media_type"] == "IMAGE"


def test_api_analyze_ocr_video_success(client):
    """Verifies POST /api/v1/analyze/ocr with a valid video file."""
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "upload_test.mp4")

    try:
        create_synthetic_video_with_text(video_path, duration_sec=1.5, fps=25.0)
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        response = client.post(
            "/api/v1/analyze/ocr",
            files={"file": ("video.mp4", video_bytes, "video/mp4")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["evidence"]["media_type"] == "VIDEO"

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        os.rmdir(temp_dir)


def test_api_analyze_ocr_unsupported_media_type(client):
    """Verifies HTTP 400 when an unsupported content type (e.g. text/plain) is uploaded."""
    response = client.post(
        "/api/v1/analyze/ocr",
        files={"file": ("test.txt", b"plain text payload", "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported media content type" in response.json()["detail"]


def test_api_analyze_ocr_empty_file(client):
    """Verifies HTTP 400 when an empty file is uploaded."""
    response = client.post(
        "/api/v1/analyze/ocr",
        files={"file": ("empty.png", b"", "image/png")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
