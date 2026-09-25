"""
API integration tests for Module 10 Speech-to-Text router endpoints:
- POST /api/v1/analyze/speech-to-text
- POST /api/stt/analyze
- GET /api/stt/health
- GET /api/transcript/health
"""

import io
import numpy as np
import pytest
import scipy.io.wavfile as wavfile
from fastapi.testclient import TestClient

from main import app
from schemas.transcript import BackendTranscriptResponse


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_wav_bytes() -> bytes:
    sr = 16000
    t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    audio = (0.5 * np.sin(2 * np.pi * 400 * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sr, audio)
    return buf.getvalue()


@pytest.fixture
def silent_wav_bytes() -> bytes:
    sr = 16000
    audio = np.zeros(int(sr * 1.0), dtype=np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sr, audio)
    return buf.getvalue()


class TestTranscriptRouter:

    def test_post_valid_audio_multipart(self, client, valid_wav_bytes):
        files = {"file": ("speech.wav", valid_wav_bytes, "audio/wav")}
        data = {"language": "en"}
        response = client.post("/api/v1/analyze/speech-to-text", files=files, data=data)

        assert response.status_code == 200, f"Error: {response.text}"
        body = response.json()

        validated = BackendTranscriptResponse(**body)
        assert validated.status == "COMPLETED"
        assert len(validated.full_text) > 0
        assert validated.language == "en"
        assert 0.0 <= validated.confidence_score <= 1.0
        assert validated.segments_count >= 1
        assert validated.words_count > 0
        assert validated.evidence.media_type == "AUDIO"

    def test_post_silent_audio_multipart(self, client, silent_wav_bytes):
        files = {"file": ("silence.wav", silent_wav_bytes, "audio/wav")}
        response = client.post("/api/v1/analyze/speech-to-text", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "COMPLETED"
        assert body["full_text"] == ""
        assert body["segments_count"] == 0
        assert body["words_count"] == 0
        assert body["confidence_score"] == 1.0

    def test_post_empty_file_returns_400(self, client):
        files = {"file": ("empty.wav", b"", "audio/wav")}
        response = client.post("/api/v1/analyze/speech-to-text", files=files)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_post_image_returns_400(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        files = {"file": ("photo.png", fake_png, "image/png")}
        response = client.post("/api/v1/analyze/speech-to-text", files=files)

        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()

    def test_post_corrupt_media_returns_400(self, client):
        files = {"file": ("corrupt.wav", b"not-a-valid-audio-file-format", "audio/wav")}
        response = client.post("/api/v1/analyze/speech-to-text", files=files)

        assert response.status_code == 400

    def test_missing_file_field_returns_422(self, client):
        response = client.post("/api/v1/analyze/speech-to-text", data={"language": "en"})
        assert response.status_code == 422

    def test_stt_health_endpoint(self, client):
        response = client.get("/api/stt/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "10-speech-to-text"
        assert "faster_whisper_available" in data
        assert "active_engine" in data

    def test_transcript_health_endpoint(self, client):
        response = client.get("/api/transcript/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_legacy_path_transcription(self, client, valid_wav_bytes, tmp_path):
        tmp_wav = str(tmp_path / "legacy_test.wav")
        with open(tmp_wav, "wb") as f:
            f.write(valid_wav_bytes)

        payload = {"media_path": tmp_wav, "language": "en"}
        response = client.post("/api/stt/analyze", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"
        assert len(response.json()["full_text"]) > 0
