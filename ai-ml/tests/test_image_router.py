"""
Integration tests for services/image_analysis/router.py
Blueprint Section G: POST /api/image/analyze
Blueprint Section I: pytest unit tests for Python ML services

Uses FastAPI's TestClient (via httpx) to call the full HTTP stack.
"""

import io
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

# --- Override STORAGE_DIR to a temp directory before app import ---
_TMP_DIR = Path(tempfile.mkdtemp(prefix="truthlens_test_"))
os.environ["STORAGE_DIR"] = str(_TMP_DIR)
os.environ["MODEL_DIR"] = str(_TMP_DIR / "models")


from main import app  # noqa: E402 — must be after env override
from services.image_analysis.classifier import reset_model  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the full FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_classifier():
    reset_model()
    yield
    reset_model()


@pytest.fixture(scope="module")
def sample_image_path(tmp_path_factory) -> str:
    """Write a real PNG image to a temp file and return the path."""
    rng = np.random.default_rng(99)
    data = rng.integers(0, 255, (128, 128, 3), dtype=np.uint8)
    img = Image.fromarray(data, mode="RGB")
    tmp_dir = tmp_path_factory.mktemp("images")
    path = tmp_dir / "test_image.png"
    img.save(str(path), format="PNG")
    return str(path)


@pytest.fixture(scope="module")
def nonexistent_image_path() -> str:
    return "/tmp/this_file_does_not_exist_truthlens.png"


@pytest.fixture(scope="module")
def non_image_path(tmp_path_factory) -> str:
    """Write a text file (not an image) and return its path."""
    tmp_dir = tmp_path_factory.mktemp("bad_files")
    path = tmp_dir / "not_an_image.txt"
    path.write_text("This is not an image file.")
    return str(path)


# ------------------------------------------------------------------ #
# Health check
# ------------------------------------------------------------------ #
class TestHealthCheck:
    def test_health_endpoint_returns_200(self, client):
        response = client.get("/api/image/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "image-analysis"

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "TruthLens" in response.json()["service"]


# ------------------------------------------------------------------ #
# Valid image analysis
# ------------------------------------------------------------------ #
class TestAnalyzeImageValid:

    def test_valid_image_returns_200(self, client, sample_image_path):
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        assert response.status_code == 200, f"Response body: {response.text}"

    def test_valid_image_response_has_required_fields(self, client, sample_image_path):
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        data = response.json()
        for field in [
            "media_id", "synthetic_prob", "manipulation_prob",
            "ela_heatmap_url", "noise_variance", "confidence",
            "processing_time_ms", "status",
        ]:
            assert field in data, f"Missing required field: {field}"

    def test_valid_image_status_is_completed(self, client, sample_image_path):
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        assert response.json()["status"] == "completed"

    def test_synthetic_prob_in_range(self, client, sample_image_path):
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        prob = response.json()["synthetic_prob"]
        assert 0.0 <= prob <= 1.0, f"synthetic_prob out of range: {prob}"

    def test_manipulation_prob_in_range(self, client, sample_image_path):
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        prob = response.json()["manipulation_prob"]
        assert 0.0 <= prob <= 1.0

    def test_ela_heatmap_file_created(self, client, sample_image_path):
        """ELA heatmap PNG should be saved to the storage directory."""
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        ela_url = response.json().get("ela_heatmap_url", "")
        if ela_url:
            full_path = Path(ela_url)
            assert full_path.exists() or (
                _TMP_DIR / "ela" / f"{media_id}.png"
            ).exists(), "ELA heatmap file should exist on disk"

    def test_processing_time_positive(self, client, sample_image_path):
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        assert response.json()["processing_time_ms"] >= 0

    def test_media_id_echoed_in_response(self, client, sample_image_path):
        media_id = str(uuid.uuid4())
        payload = {"media_id": media_id, "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        assert response.json()["media_id"] == media_id


# ------------------------------------------------------------------ #
# Invalid input — file does not exist
# ------------------------------------------------------------------ #
class TestAnalyzeImageInvalidPath:

    def test_nonexistent_file_returns_400(self, client, nonexistent_image_path):
        payload = {
            "media_id": str(uuid.uuid4()),
            "image_path": nonexistent_image_path,
        }
        response = client.post("/api/image/analyze", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    def test_non_image_file_returns_400(self, client, non_image_path):
        payload = {
            "media_id": str(uuid.uuid4()),
            "image_path": non_image_path,
        }
        response = client.post("/api/image/analyze", json=payload)
        assert response.status_code == 400, f"Expected 400 for non-image file"


# ------------------------------------------------------------------ #
# Missing required fields — Pydantic validation (422)
# ------------------------------------------------------------------ #
class TestAnalyzeImageMissingFields:

    def test_missing_media_id_returns_422(self, client, sample_image_path):
        payload = {"image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        assert response.status_code == 422

    def test_missing_image_path_returns_422(self, client):
        payload = {"media_id": str(uuid.uuid4())}
        response = client.post("/api/image/analyze", json=payload)
        assert response.status_code == 422

    def test_empty_image_path_returns_422(self, client):
        payload = {"media_id": str(uuid.uuid4()), "image_path": "   "}
        response = client.post("/api/image/analyze", json=payload)
        assert response.status_code == 422

    def test_invalid_uuid_returns_422(self, client, sample_image_path):
        payload = {"media_id": "not-a-valid-uuid", "image_path": sample_image_path}
        response = client.post("/api/image/analyze", json=payload)
        assert response.status_code == 422
