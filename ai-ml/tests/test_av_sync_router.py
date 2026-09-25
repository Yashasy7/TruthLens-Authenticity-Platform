"""
TruthLens AI/ML — Module 08: Audio-Visual Synchronization FastAPI Router Tests
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def synthetic_av_mp4_bytes() -> bytes:
    """Generate a short 1-second synthetic video with black/white frames."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        path = Path(tmp.name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 25.0
    out = cv2.VideoWriter(str(path), fourcc, fps, (128, 128))
    for i in range(25):
        val = 220 if i % 2 == 0 else 30
        frame = np.full((128, 128, 3), val, dtype=np.uint8)
        out.write(frame)
    out.release()

    video_bytes = path.read_bytes()
    path.unlink(missing_ok=True)
    return video_bytes


@pytest.fixture
def synthetic_wav_bytes() -> bytes:
    """Generate 1 second of 16kHz sine wave audio."""
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    samples = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    wavfile.write(str(wav_path), sr, samples)
    content = wav_path.read_bytes()
    wav_path.unlink(missing_ok=True)
    return content


def test_root_endpoint_includes_m08(client: TestClient):
    """GET / must list Module 08 in active modules."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "08-av-synchronization" in data["modules"]


def test_av_sync_health_endpoint(client: TestClient):
    """GET /api/av-sync/health returns operational status."""
    response = client.get("/api/av-sync/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "08-av-synchronization"
    assert data["model_ready"] is True
    assert "TruthLens-SyncNet" in data["model_name"]


def test_analyze_av_sync_v1_empty_file(client: TestClient):
    """POST /api/v1/analyze/av-sync with empty file returns 400 Bad Request."""
    files = {"file": ("empty.mp4", b"", "video/mp4")}
    response = client.post("/api/v1/analyze/av-sync", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_av_sync_v1_corrupt_file(client: TestClient):
    """POST /api/v1/analyze/av-sync with corrupt media bytes returns 400 Bad Request."""
    files = {"file": ("corrupt.mp4", b"NOT_A_VALID_VIDEO_FILE", "video/mp4")}
    response = client.post("/api/v1/analyze/av-sync", files=files)
    assert response.status_code == 400


def test_analyze_av_sync_v1_missing_file_param(client: TestClient):
    """POST /api/v1/analyze/av-sync without file returns 422 Unprocessable Entity."""
    response = client.post("/api/v1/analyze/av-sync")
    assert response.status_code == 422


def test_analyze_av_sync_v1_with_valid_media(client: TestClient, synthetic_av_mp4_bytes: bytes):
    """
    POST /api/v1/analyze/av-sync with valid video returns 200 and matches BackendAvSyncResponse contract.
    """
    files = {"file": ("test_clip.mp4", synthetic_av_mp4_bytes, "video/mp4")}
    response = client.post("/api/v1/analyze/av-sync", files=files)
    assert response.status_code == 200
    data = response.json()

    # Verify Spring Boot contract fields
    assert "sync_score" in data
    assert "lip_offset_ms" in data
    assert "confidence" in data
    assert "mismatch_segments" in data
    assert "model_name" in data
    assert "model_version" in data
    assert "evidence" in data
    assert data["status"] == "COMPLETED"

    # Verify evidence sub-object
    evidence = data["evidence"]
    assert "cross_correlation_score" in evidence
    assert "syncnet_distance" in evidence
    assert "audio_track_present" in evidence
    assert "face_detected" in evidence
    assert "total_frames_analyzed" in evidence
    assert "video_duration_seconds" in evidence
    assert "temporal_drift_score" in evidence
    assert "sync_status" in evidence


def test_analyze_av_sync_legacy_missing_path(client: TestClient):
    """POST /api/av-sync/analyze with non-existent path returns 404."""
    payload = {"video_path": "/nonexistent/video.mp4", "media_id": "test-123"}
    response = client.post("/api/av-sync/analyze", json=payload)
    assert response.status_code == 404
