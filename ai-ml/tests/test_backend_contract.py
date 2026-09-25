"""
Integration tests for POST /api/v1/analyze/image
Verifies exact alignment with Yashas's Spring Boot FastApiAiServiceClient contract.
"""

import base64
import io
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app
from schemas.image_analysis import BackendImageAnalysisResponse
from services.image_analysis.classifier import reset_model


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_classifier():
    reset_model()
    yield
    reset_model()


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Create a 128x128 valid PNG byte stream."""
    rng = np.random.default_rng(77)
    arr = rng.integers(0, 255, (128, 128, 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Create a 128x128 valid JPEG byte stream."""
    rng = np.random.default_rng(88)
    arr = rng.integers(0, 255, (128, 128, 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class TestBackendImageAnalysisContract:

    def test_post_valid_png_multipart(self, client, sample_png_bytes):
        files = {"file": ("test_image.png", sample_png_bytes, "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)

        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()

        # Validate with Pydantic model
        validated = BackendImageAnalysisResponse(**data)
        assert validated.status == "COMPLETED"
        assert 0.0 <= validated.ai_prob <= 1.0
        assert 0.0 <= validated.manipulation_prob <= 1.0
        assert validated.noise_variance is not None and validated.noise_variance >= 0.0
        assert validated.fft_anomaly_score is not None and 0.0 <= validated.fft_anomaly_score <= 1.0
        assert isinstance(validated.copy_move_detected, bool)
        assert isinstance(validated.splicing_detected, bool)
        assert len(validated.model_name) > 0
        assert len(validated.model_version) > 0

    def test_post_valid_jpeg_multipart(self, client, sample_jpeg_bytes):
        files = {"file": ("photo.jpg", sample_jpeg_bytes, "image/jpeg")}
        response = client.post("/api/v1/analyze/image", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"

    def test_ela_base64_heatmap_is_valid_png(self, client, sample_png_bytes):
        files = {"file": ("sample.png", sample_png_bytes, "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)
        assert response.status_code == 200
        data = response.json()

        ela_b64 = data["ela_heatmap_base64"]
        assert isinstance(ela_b64, str)
        assert len(ela_b64) > 50

        # Decode Base64 string directly as Java's Base64.getDecoder().decode does
        raw_bytes = base64.b64decode(ela_b64)
        # Check standard PNG 8-byte magic header: \x89PNG\r\n\x1a\n
        assert raw_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        # Verify decoded bytes can be loaded by PIL
        img = Image.open(io.BytesIO(raw_bytes))
        assert img.format == "PNG"

    def test_gradcam_base64_heatmap_is_valid_png(self, client, sample_png_bytes):
        files = {"file": ("sample.png", sample_png_bytes, "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)
        assert response.status_code == 200
        data = response.json()

        gradcam_b64 = data.get("gradcam_heatmap_base64")
        if gradcam_b64 is not None:
            raw_bytes = base64.b64decode(gradcam_b64)
            assert raw_bytes[:8] == b"\x89PNG\r\n\x1a\n"
            img = Image.open(io.BytesIO(raw_bytes))
            assert img.format == "PNG"

    def test_empty_file_returns_400(self, client):
        files = {"file": ("empty.jpg", b"", "image/jpeg")}
        response = client.post("/api/v1/analyze/image", files=files)
        assert response.status_code == 400
        assert "empty" in response.text.lower()

    def test_non_image_corrupted_file_returns_400(self, client):
        files = {"file": ("test.txt", b"This is plain text, not an image.", "text/plain")}
        response = client.post("/api/v1/analyze/image", files=files)
        assert response.status_code == 400

    def test_missing_file_parameter_returns_422(self, client):
        # Empty multipart without the 'file' field
        response = client.post("/api/v1/analyze/image", data={"extra": "data"})
        assert response.status_code == 422

    def test_evidence_structure_contains_forensics(self, client, sample_png_bytes):
        files = {"file": ("evidence_test.png", sample_png_bytes, "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)
        assert response.status_code == 200
        data = response.json()

        evidence = data.get("evidence", {})
        assert "noise_variance" in evidence
        assert "fft_high_freq_ratio" in evidence
        assert "fft_anomaly_score" in evidence
        assert "copy_move" in evidence
        assert "confidence" in evidence


class TestBackendAudioAnalysisContract:
    """Verifies exact alignment with Spring Boot FastApiAudioAiServiceClient contract."""

    @pytest.fixture
    def sample_wav_bytes(self) -> bytes:
        import scipy.io.wavfile as wavfile
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        data = (np.sin(2 * np.pi * 440.0 * t) * 32767).astype(np.int16)
        buf = io.BytesIO()
        wavfile.write(buf, sr, data)
        return buf.getvalue()

    def test_post_valid_audio_multipart(self, client, sample_wav_bytes):
        from schemas.audio_analysis import BackendAudioAnalysisResponse

        files = {"file": ("speech.wav", sample_wav_bytes, "audio/wav")}
        response = client.post("/api/v1/analyze/audio", files=files)

        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()

        validated = BackendAudioAnalysisResponse(**data)
        assert validated.status == "COMPLETED"
        assert 0.0 <= validated.synthetic_voice_prob <= 1.0
        assert validated.pitch_variance >= 0.0
        assert len(validated.spectrogram_base64) > 50
        assert validated.model_name
        assert validated.model_version

        # Verify Base64 is valid PNG
        raw_bytes = base64.b64decode(validated.spectrogram_base64)
        assert raw_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        evidence = validated.evidence
        assert evidence.duration_seconds == pytest.approx(1.0, abs=0.05)
        assert evidence.pitch_mean >= 0.0
        assert evidence.spectral_centroid_mean >= 0.0
        assert 0.0 <= evidence.phase_discontinuity_score <= 1.0
        assert isinstance(evidence.splice_markers, list)

    def test_audio_empty_file_returns_400(self, client):
        files = {"file": ("empty.wav", b"", "audio/wav")}
        response = client.post("/api/v1/analyze/audio", files=files)
        assert response.status_code == 400
        assert "empty" in response.text.lower()

    def test_audio_corrupt_file_returns_400(self, client):
        files = {"file": ("corrupt.wav", b"not_a_valid_wav_payload", "audio/wav")}
        response = client.post("/api/v1/analyze/audio", files=files)
        assert response.status_code == 400

    def test_audio_missing_file_returns_422(self, client):
        response = client.post("/api/v1/analyze/audio", data={"field": "test"})
        assert response.status_code == 422


class TestBackendAvSyncContract:
    """Verifies exact alignment with Spring Boot FastApiAvSyncServiceClient contract."""

    @pytest.fixture
    def sample_video_bytes(self) -> bytes:
        import cv2
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            path = Path(tmp.name)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(path), fourcc, 25.0, (128, 128))
        for i in range(25):
            val = 200 if i % 2 == 0 else 50
            frame = np.full((128, 128, 3), val, dtype=np.uint8)
            out.write(frame)
        out.release()
        content = path.read_bytes()
        path.unlink(missing_ok=True)
        return content

    def test_post_valid_av_sync_multipart(self, client, sample_video_bytes):
        from schemas.av_sync import BackendAvSyncResponse

        files = {"file": ("interview.mp4", sample_video_bytes, "video/mp4")}
        response = client.post("/api/v1/analyze/av-sync", files=files)

        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()

        validated = BackendAvSyncResponse(**data)
        assert validated.status == "COMPLETED"
        assert 0.0 <= validated.sync_score <= 1.0
        assert isinstance(validated.lip_offset_ms, float)
        assert 0.0 <= validated.confidence <= 1.0
        assert isinstance(validated.mismatch_segments, list)
        assert validated.model_name
        assert validated.model_version

        evidence = validated.evidence
        assert isinstance(evidence.cross_correlation_score, float)
        assert isinstance(evidence.syncnet_distance, float)
        assert isinstance(evidence.audio_track_present, bool)
        assert isinstance(evidence.face_detected, bool)
        assert evidence.total_frames_analyzed >= 0
        assert evidence.video_duration_seconds >= 0.0
        assert isinstance(evidence.sync_status, str)

    def test_av_sync_empty_file_returns_400(self, client):
        files = {"file": ("empty.mp4", b"", "video/mp4")}
        response = client.post("/api/v1/analyze/av-sync", files=files)
        assert response.status_code == 400
        assert "empty" in response.text.lower()

    def test_av_sync_corrupt_file_returns_400(self, client):
        files = {"file": ("corrupt.mp4", b"not_a_valid_mp4_container", "video/mp4")}
        response = client.post("/api/v1/analyze/av-sync", files=files)
        assert response.status_code == 400

    def test_av_sync_missing_file_returns_422(self, client):
        response = client.post("/api/v1/analyze/av-sync", data={"extra": "param"})
        assert response.status_code == 422


class TestBackendOcrContract:
    """Verifies exact alignment with Spring Boot FastApiOcrServiceClient contract."""

    @pytest.fixture
    def sample_ocr_png_bytes(self) -> bytes:
        import cv2
        img = np.full((120, 400, 3), 40, dtype=np.uint8)
        cv2.putText(img, "BREAKING NEWS", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 240, 240), 2)
        success, encoded = cv2.imencode(".png", img)
        assert success
        return encoded.tobytes()

    @pytest.fixture
    def sample_ocr_video_bytes(self) -> bytes:
        import cv2
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            path = Path(tmp.name)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(path), fourcc, 25.0, (320, 240))
        for i in range(25):
            frame = np.full((240, 320, 3), 200, dtype=np.uint8)
            cv2.putText(frame, "SAMPLE BANNER", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (10, 10, 10), 2)
            out.write(frame)
        out.release()
        content = path.read_bytes()
        path.unlink(missing_ok=True)
        return content

    def test_post_valid_ocr_image_multipart(self, client, sample_ocr_png_bytes):
        from schemas.ocr import BackendOcrResponse

        files = {"file": ("banner.png", sample_ocr_png_bytes, "image/png")}
        response = client.post("/api/v1/analyze/ocr", files=files)

        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()

        validated = BackendOcrResponse(**data)
        assert validated.status == "COMPLETED"
        assert 0.0 <= validated.confidence_score <= 1.0
        assert isinstance(validated.extracted_text, str)
        assert isinstance(validated.regions, list)
        assert validated.regions_count == len(validated.regions)

        evidence = validated.evidence
        assert evidence.media_type == "IMAGE"
        assert evidence.total_regions == validated.regions_count
        assert evidence.image_width == 400
        assert evidence.image_height == 120
        assert len(evidence.preprocessing_applied) > 0

    def test_post_valid_ocr_video_multipart(self, client, sample_ocr_video_bytes):
        from schemas.ocr import BackendOcrResponse

        files = {"file": ("broadcast.mp4", sample_ocr_video_bytes, "video/mp4")}
        response = client.post("/api/v1/analyze/ocr", files=files)

        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()

        validated = BackendOcrResponse(**data)
        assert validated.status == "COMPLETED"
        assert validated.evidence.media_type == "VIDEO"
        assert validated.evidence.frames_analyzed >= 1

    def test_ocr_empty_file_returns_400(self, client):
        files = {"file": ("empty.png", b"", "image/png")}
        response = client.post("/api/v1/analyze/ocr", files=files)
        assert response.status_code == 400
        assert "empty" in response.text.lower()

    def test_ocr_corrupt_file_returns_400(self, client):
        files = {"file": ("corrupt.png", b"NOT_A_VALID_IMAGE_OR_VIDEO", "image/png")}
        response = client.post("/api/v1/analyze/ocr", files=files)
        assert response.status_code == 400

    def test_ocr_missing_file_returns_422(self, client):
        response = client.post("/api/v1/analyze/ocr", data={"other": "field"})
        assert response.status_code == 422


class TestBackendTranscriptContract:
    """
    Contract tests verifying exact alignment with Spring Boot FastApiTranscriptServiceClient:
    - POST /api/v1/analyze/speech-to-text
    - multipart/form-data with 'file'
    - Response schema matches FastApiTranscriptResponse DTO exactly
    """

    @pytest.fixture
    def speech_wav_bytes(self) -> bytes:
        import scipy.io.wavfile as wavfile
        sr = 16000
        t = np.linspace(0, 2.5, int(sr * 2.5), endpoint=False)
        audio = (0.5 * np.sin(2 * np.pi * 320 * t) * 32767).astype(np.int16)
        buf = io.BytesIO()
        wavfile.write(buf, sr, audio)
        return buf.getvalue()

    @pytest.fixture
    def silent_wav_bytes(self) -> bytes:
        import scipy.io.wavfile as wavfile
        sr = 16000
        audio = np.zeros(int(sr * 1.5), dtype=np.int16)
        buf = io.BytesIO()
        wavfile.write(buf, sr, audio)
        return buf.getvalue()

    def test_post_valid_transcript_audio_multipart(self, client, speech_wav_bytes):
        from schemas.transcript import BackendTranscriptResponse

        files = {"file": ("recording.wav", speech_wav_bytes, "audio/wav")}
        data = {"language": "en"}
        response = client.post("/api/v1/analyze/speech-to-text", files=files, data=data)

        assert response.status_code == 200, f"Error: {response.text}"
        payload = response.json()

        validated = BackendTranscriptResponse(**payload)
        assert validated.status == "COMPLETED"
        assert len(validated.full_text) > 0
        assert validated.language == "en"
        assert 0.0 <= validated.confidence_score <= 1.0
        assert 2.4 <= validated.duration_seconds <= 2.6
        assert validated.segments_count == len(validated.segments)
        assert validated.segments_count >= 1
        assert validated.words_count > 0
        assert validated.error_message is None

        # Verify segment structure and nested words
        for seg in validated.segments:
            assert seg.start >= 0.0
            assert seg.end > seg.start
            assert 0.0 <= seg.confidence <= 1.0
            assert len(seg.text) > 0

            for w in seg.words:
                assert seg.start <= w.start <= w.end <= seg.end
                assert 0.0 <= w.probability <= 1.0
                assert len(w.word) > 0

        # Verify evidence metadata
        evidence = validated.evidence
        assert evidence.model_name in ["Faster-Whisper", "Faster-Whisper-Fallback"]
        assert evidence.audio_sample_rate == 16000
        assert evidence.media_type == "AUDIO"
        assert 0.0 <= evidence.language_probability <= 1.0

    def test_transcript_silent_audio_returns_completed_empty(self, client, silent_wav_bytes):
        from schemas.transcript import BackendTranscriptResponse

        files = {"file": ("silent.wav", silent_wav_bytes, "audio/wav")}
        response = client.post("/api/v1/analyze/speech-to-text", files=files)

        assert response.status_code == 200
        data = response.json()
        validated = BackendTranscriptResponse(**data)
        assert validated.status == "COMPLETED"
        assert validated.full_text == ""
        assert validated.segments_count == 0
        assert validated.words_count == 0
        assert validated.confidence_score == 1.0

    def test_transcript_empty_file_returns_400(self, client):
        files = {"file": ("empty.wav", b"", "audio/wav")}
        response = client.post("/api/v1/analyze/speech-to-text", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_transcript_image_file_returns_400(self, client):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        files = {"file": ("photo.png", fake_png, "image/png")}
        response = client.post("/api/v1/analyze/speech-to-text", files=files)
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()

    def test_transcript_missing_file_returns_422(self, client):
        response = client.post("/api/v1/analyze/speech-to-text", data={"language": "en"})
        assert response.status_code == 422


class TestBackendClaimContract:
    """
    Contract tests verifying exact alignment with Spring Boot FastApiClaimServiceClient:
    - POST /api/v1/analyze/claims
    - application/json with 'text', 'source_type', 'language'
    - Response schema matches FastApiClaimResponse DTO exactly
    """

    def test_post_valid_claim_analysis_request(self, client):
        from schemas.claim import FastApiClaimResponse

        payload = {
            "text": "The Prime Minister announced a 15 billion euro relief package in Paris on Monday.",
            "source_type": "TRANSCRIPT",
            "language": "en",
        }
        response = client.post("/api/v1/analyze/claims", json=payload)

        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()

        validated = FastApiClaimResponse(**data)
        assert validated.status == "COMPLETED"
        assert validated.source_type == "TRANSCRIPT"
        assert validated.claims_count >= 1
        assert len(validated.claims) == validated.claims_count
        assert validated.error_message is None

        # Verify structured claim object aligns 1:1 with FastApiStructuredClaim.java
        claim = validated.claims[0]
        assert len(claim.claim_text) > 0
        assert len(claim.normalized_claim_text) > 0
        assert claim.claim_type in ["FACTUAL_CLAIM", "OPINION", "QUESTION", "NON_CLAIM", "UNCERTAIN"]
        assert claim.subject is not None
        assert claim.action is not None
        assert 0.0 <= claim.confidence_score <= 1.0
        assert len(claim.claim_hash) == 64
        assert claim.sentence_index == 0
        assert claim.start_char >= 0
        assert claim.end_char > claim.start_char

        # Verify entity spans align 1:1 with ClaimEntityDto.java
        assert len(claim.entities) >= 1
        for ent in claim.entities:
            assert len(ent.text) > 0
            assert len(ent.label) > 0
            assert ent.normalized_label in [
                "PERSON", "ORG", "LOCATION", "DATE", "MONEY", "QUANTITY", "EVENT", "GENERAL"
            ]
            assert ent.start_char >= 0
            assert ent.end_char > ent.start_char

        # Verify evidence aligns 1:1 with ClaimEvidenceDto.java
        evidence = validated.evidence
        assert evidence is not None
        assert len(evidence.model_name) > 0
        assert evidence.claims_count == validated.claims_count
        assert evidence.entities_count == len(validated.entities)
        assert evidence.duration_seconds >= 0.0

    def test_post_direct_text_ad_hoc(self, client):
        from schemas.claim import FastApiClaimResponse

        payload = {
            "text": "The Federal Reserve cut interest rates by 25 basis points in Washington.",
            "source_type": "DIRECT_TEXT",
            "language": "en",
        }
        response = client.post("/api/v1/analyze/claims", json=payload)
        assert response.status_code == 200

        validated = FastApiClaimResponse(**response.json())
        assert validated.status == "COMPLETED"
        assert validated.source_type == "DIRECT_TEXT"
        assert validated.claims_count == 1
        assert "Federal Reserve" in (validated.claims[0].subject or "")
        assert validated.claims[0].action == "cut"

    def test_post_empty_text_returns_200_empty(self, client):
        from schemas.claim import FastApiClaimResponse

        response = client.post("/api/v1/analyze/claims", json={"text": "", "source_type": "DIRECT_TEXT"})
        assert response.status_code == 200

        validated = FastApiClaimResponse(**response.json())
        assert validated.status == "COMPLETED"
        assert validated.claims_count == 0
        assert validated.claims == []
        assert validated.entities == []

    def test_post_oversized_text_returns_400(self, client):
        from config.settings import settings

        huge_text = "Claim " * (settings.claim_max_text_length // 4 + 10)
        response = client.post("/api/v1/analyze/claims", json={"text": huge_text})
        assert response.status_code == 400
        assert "exceeds maximum allowed limit" in response.json()["detail"]



