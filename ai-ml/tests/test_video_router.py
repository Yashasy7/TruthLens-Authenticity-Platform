"""
Integration tests for services/video_analysis/router.py
Verifies exact alignment with Yashas's Spring Boot FastApiVideoAiServiceClient contract.
"""

import io
from pathlib import Path
import uuid

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from main import app
from schemas.video_analysis import BackendVideoAnalysisResponse
from services.video_analysis.model import reset_video_model


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_video_classifier():
    reset_video_model()
    yield
    reset_video_model()


@pytest.fixture
def synthetic_video_bytes() -> bytes:
    """Generate in-memory MP4 video bytes with synthetic animated frames."""
    import tempfile
    tmp = Path(tempfile.mktemp(suffix=".mp4"))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 10.0
    w, h = 80, 80
    writer = cv2.VideoWriter(str(tmp), fourcc, fps, (w, h))

    for i in range(12):
        frame = np.full((h, w, 3), 100 + i * 5, dtype=np.uint8)
        # Draw synthetic facial oval to simulate face
        cv2.ellipse(frame, (w // 2, h // 2), (20, 25), 0, 0, 360, (200, 160, 140), -1)
        cv2.circle(frame, (w // 2 - 8, h // 2 - 8), 3, (30, 30, 30), -1)
        cv2.circle(frame, (w // 2 + 8, h // 2 - 8), 3, (30, 30, 30), -1)
        writer.write(frame)
    writer.release()

    content = tmp.read_bytes()
    tmp.unlink()
    return content


class TestVideoAnalysisRouter:

    def test_video_health_returns_200(self, client):
        res = client.get("/api/video/health")
        assert res.status_code == 200
        assert res.json() == {"service": "video-analysis", "status": "ok"}

    def test_post_valid_video_multipart_returns_200(self, client, synthetic_video_bytes):
        files = {"file": ("test_deepfake.mp4", synthetic_video_bytes, "video/mp4")}
        res = client.post("/api/v1/analyze/video", files=files)

        assert res.status_code == 200, f"Error body: {res.text}"
        data = res.json()

        # Validate strictly against Pydantic schema
        validated = BackendVideoAnalysisResponse(**data)
        assert validated.status == "COMPLETED"
        assert 0.0 <= validated.deepfake_prob <= 1.0
        assert validated.total_frames_sampled > 0
        assert len(validated.model_name) > 0
        assert len(validated.model_version) > 0

    def test_post_valid_video_has_required_contract_fields(self, client, synthetic_video_bytes):
        files = {"file": ("video.mp4", synthetic_video_bytes, "video/mp4")}
        res = client.post("/api/v1/analyze/video", files=files)
        assert res.status_code == 200
        data = res.json()

        # Check required fields expected by Yashas's Spring Boot DTO
        assert "deepfake_prob" in data
        assert "face_count" in data
        assert "total_frames_sampled" in data
        assert "suspicious_timestamps" in data
        assert "frame_scores" in data
        assert "model_name" in data
        assert "model_version" in data
        assert "evidence" in data
        assert "status" in data

        evidence = data["evidence"]
        assert "duration_seconds" in evidence
        assert "details" in evidence

    def test_post_empty_file_returns_400(self, client):
        files = {"file": ("empty.mp4", b"", "video/mp4")}
        res = client.post("/api/v1/analyze/video", files=files)
        assert res.status_code == 400
        assert "empty" in res.text.lower()

    def test_post_corrupt_file_returns_400(self, client):
        files = {"file": ("corrupt.mp4", b"corrupted non-video stream bytes", "video/mp4")}
        res = client.post("/api/v1/analyze/video", files=files)
        assert res.status_code == 400

    def test_post_missing_file_param_returns_422(self, client):
        res = client.post("/api/v1/analyze/video", data={"other": "param"})
        assert res.status_code == 422

    def test_legacy_post_video_analyze_nonexistent_returns_400(self, client):
        payload = {
            "media_id": str(uuid.uuid4()),
            "video_path": "/tmp/nonexistent_video_path_truthlens.mp4",
        }
        res = client.post("/api/video/analyze", json=payload)
        assert res.status_code == 400

    def test_legacy_post_video_analyze_valid(self, client, synthetic_video_bytes, tmp_path):
        video_file = tmp_path / "legacy_test.mp4"
        video_file.write_bytes(synthetic_video_bytes)

        payload = {
            "media_id": str(uuid.uuid4()),
            "video_path": str(video_file),
        }
        res = client.post("/api/video/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert 0.0 <= data["deepfake_prob"] <= 1.0

    def test_end_to_end_video_analysis_pipeline(self, client, synthetic_video_bytes):
        """End-to-end integration test from upload to temporal evaluation."""
        files = {"file": ("interview.mp4", synthetic_video_bytes, "video/mp4")}
        response = client.post("/api/v1/analyze/video", files=files)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "COMPLETED"
        assert isinstance(data["deepfake_prob"], float)
        assert len(data["frame_scores"]) > 0

        first_frame = data["frame_scores"][0]
        assert "frame_index" in first_frame
        assert "timestamp_seconds" in first_frame
        assert "deepfake_score" in first_frame
        assert "temporal_inconsistency" in first_frame
        assert "is_suspicious" in first_frame
