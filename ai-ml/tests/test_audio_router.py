"""
TruthLens AI/ML — Module 07 Tests: FastAPI Audio Routes & Backend Contract Alignment
"""

import base64
import io
import numpy as np
import pytest
import scipy.io.wavfile as wavfile
from starlette.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _make_test_wav_bytes(duration: float = 1.0, sr: int = 16000, freq: float = 440.0) -> bytes:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    data = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sr, data)
    return buf.getvalue()


class TestAudioRouter:
    """FastAPI endpoint and Spring Boot backend contract integration tests."""

    def test_root_endpoint_lists_audio_module(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "07-audio-authenticity" in data["modules"]

    def test_audio_health_check(self, client: TestClient):
        response = client.get("/api/audio/health")
        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "07-audio-authenticity"
        assert data["status"] in ("healthy", "degraded")
        assert "model_name" in data
        assert "model_version" in data
        assert "sample_rate" in data

    def test_v1_analyze_audio_valid_upload_matches_spring_boot_contract(self, client: TestClient):
        wav_bytes = _make_test_wav_bytes(duration=1.2, sr=16000, freq=350.0)
        files = {"file": ("test_speech.wav", wav_bytes, "audio/wav")}

        response = client.post("/api/v1/analyze/audio", files=files)
        assert response.status_code == 200
        data = response.json()

        # Spring Boot FastApiAudioAnalysisResponse top-level contract fields
        assert "synthetic_voice_prob" in data
        assert isinstance(data["synthetic_voice_prob"], float)
        assert 0.0 <= data["synthetic_voice_prob"] <= 1.0

        assert "spectrogram_url" in data
        assert "spectrogram_base64" in data
        assert isinstance(data["spectrogram_base64"], str)
        assert len(data["spectrogram_base64"]) > 50

        # Verify Base64 is valid PNG
        raw_png = base64.b64decode(data["spectrogram_base64"])
        assert raw_png.startswith(b"\x89PNG\r\n\x1a\n")

        assert "pitch_variance" in data
        assert isinstance(data["pitch_variance"], float)
        assert data["pitch_variance"] >= 0.0

        assert "splice_markers" in data
        assert isinstance(data["splice_markers"], list)

        assert "model_name" in data
        assert "model_version" in data
        assert data["status"] == "COMPLETED"

        # Evidence sub-object (AudioEvidenceDto)
        evidence = data["evidence"]
        assert "duration_seconds" in evidence
        assert evidence["duration_seconds"] == pytest.approx(1.2, abs=0.05)
        assert "pitch_mean" in evidence
        assert "pitch_variance" in evidence
        assert "spectral_centroid_mean" in evidence
        assert "spectral_bandwidth_mean" in evidence
        assert "spectral_rolloff_mean" in evidence
        assert "zero_crossing_rate_mean" in evidence
        assert "phase_discontinuity_score" in evidence
        assert 0.0 <= evidence["phase_discontinuity_score"] <= 1.0
        assert "splice_markers" in evidence
        assert "details" in evidence
        assert isinstance(evidence["details"], dict)

    def test_v1_analyze_audio_empty_file_returns_400(self, client: TestClient):
        files = {"file": ("empty.wav", b"", "audio/wav")}
        response = client.post("/api/v1/analyze/audio", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_v1_analyze_audio_corrupt_file_returns_400(self, client: TestClient):
        files = {"file": ("corrupt.wav", b"invalid_binary_garbage_audio", "audio/wav")}
        response = client.post("/api/v1/analyze/audio", files=files)
        assert response.status_code == 400

    def test_v1_analyze_audio_missing_file_parameter_returns_422(self, client: TestClient):
        response = client.post("/api/v1/analyze/audio", data={"other_param": "test"})
        assert response.status_code == 422

    def test_legacy_analyze_audio_endpoint(self, client: TestClient, tmp_path):
        wav_bytes = _make_test_wav_bytes(duration=0.8, sr=16000)
        audio_file = tmp_path / "legacy_test.wav"
        audio_file.write_bytes(wav_bytes)

        payload = {
            "media_id": "00000000-0000-0000-0000-000000000001",
            "audio_path": str(audio_file),
        }
        response = client.post("/api/audio/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["media_id"] == "00000000-0000-0000-0000-000000000001"
        assert 0.0 <= data["synthetic_voice_prob"] <= 1.0
        assert data["status"] == "COMPLETED"

    def test_legacy_analyze_audio_nonexistent_file_returns_404(self, client: TestClient):
        payload = {
            "media_id": "00000000-0000-0000-0000-000000000001",
            "audio_path": "/path/to/nonexistent_audio_file.wav",
        }
        response = client.post("/api/audio/analyze", json=payload)
        assert response.status_code == 404
