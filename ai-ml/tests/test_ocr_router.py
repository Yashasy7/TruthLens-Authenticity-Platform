"""
TruthLens AI/ML — Module 09: OCR FastAPI Router Integration Tests
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def synthetic_image_png_bytes() -> bytes:
    """Generate a clean 400x150 PNG with a dark banner and white text."""
    img = np.full((150, 400, 3), 30, dtype=np.uint8)
    cv2.putText(img, "OFFICIAL VERIFIED", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (250, 250, 250), 2)
    success, encoded = cv2.imencode(".png", img)
    assert success
    return encoded.tobytes()


@pytest.fixture
def synthetic_video_mp4_bytes() -> bytes:
    """Generate a short 1-second video with text banner."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        path = Path(tmp.name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, 25.0, (320, 240))
    for i in range(25):
        frame = np.full((240, 320, 3), 220, dtype=np.uint8)
        cv2.putText(frame, "NEWS TICKER", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (10, 10, 10), 2)
        out.write(frame)
    out.release()
    content = path.read_bytes()
    path.unlink(missing_ok=True)
    return content


def test_root_endpoint_includes_m09(client: TestClient):
    """GET / must list Module 09 in active modules."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "09-ocr-text-extraction" in data["modules"]


def test_global_health_endpoint_includes_ocr(client: TestClient):
    """GET /health must include OCR module status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["modules"]["ocr_analysis"] == "healthy"


def test_ocr_health_endpoint(client: TestClient):
    """GET /api/ocr/health returns operational status."""
    response = client.get("/api/ocr/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "09-ocr-text-extraction"
    assert data["engine_ready"] is True


def test_analyze_ocr_v1_empty_file(client: TestClient):
    """POST /api/v1/analyze/ocr with empty file returns 400 Bad Request."""
    files = {"file": ("empty.png", b"", "image/png")}
    response = client.post("/api/v1/analyze/ocr", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_ocr_v1_corrupt_file(client: TestClient):
    """POST /api/v1/analyze/ocr with corrupt bytes returns 400 Bad Request."""
    files = {"file": ("corrupt.png", b"CORRUPT_NOT_AN_IMAGE", "image/png")}
    response = client.post("/api/v1/analyze/ocr", files=files)
    assert response.status_code == 400


def test_analyze_ocr_v1_missing_file_param(client: TestClient):
    """POST /api/v1/analyze/ocr without file returns 422 Unprocessable Entity."""
    response = client.post("/api/v1/analyze/ocr")
    assert response.status_code == 422


def test_analyze_ocr_v1_valid_image(client: TestClient, synthetic_image_png_bytes: bytes):
    """POST /api/v1/analyze/ocr with valid image returns 200 and matches DTO contract."""
    files = {"file": ("banner.png", synthetic_image_png_bytes, "image/png")}
    response = client.post("/api/v1/analyze/ocr", files=files)
    assert response.status_code == 200
    data = response.json()

    assert "extracted_text" in data
    assert "language" in data
    assert "confidence_score" in data
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert "regions_count" in data
    assert "regions" in data
    assert "evidence" in data
    assert data["status"] == "COMPLETED"

    evidence = data["evidence"]
    assert evidence["media_type"] == "IMAGE"
    assert evidence["frames_analyzed"] == 1
    assert evidence["image_width"] == 400
    assert evidence["image_height"] == 150


def test_analyze_ocr_v1_valid_video(client: TestClient, synthetic_video_mp4_bytes: bytes):
    """POST /api/v1/analyze/ocr with valid video returns 200 with video evidence."""
    files = {"file": ("clip.mp4", synthetic_video_mp4_bytes, "video/mp4")}
    response = client.post("/api/v1/analyze/ocr", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "COMPLETED"
    evidence = data["evidence"]
    assert evidence["media_type"] == "VIDEO"
    assert evidence["frames_analyzed"] >= 1


def test_analyze_ocr_legacy_missing_path(client: TestClient):
    """POST /api/ocr/analyze with non-existent path returns 404."""
    payload = {"media_path": "/nonexistent/path/image.png", "media_id": "test-id"}
    response = client.post("/api/ocr/analyze", json=payload)
    assert response.status_code == 404
