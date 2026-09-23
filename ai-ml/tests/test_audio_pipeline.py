import os
import io
import tempfile
import numpy as np
import soundfile as sf
import torch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.librosa_extractor import LibrosaAcousticExtractor
from app.services.spectrogram_generator import SpectrogramGenerator
from app.services.aasist_classifier import AASISTClassifierNet, AudioAuthenticityInferenceService
from app.services.audio_pipeline import AudioAnalysisPipeline


def create_synthetic_wav(path: str, duration_sec: float = 1.0, sr: int = 16000, freq_hz: float = 440.0):
    """Generates a small valid WAV test audio with pure harmonic sine tone."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    # Fundamental + harmonics to simulate vocal cords
    waveform = (
        0.6 * np.sin(2 * np.pi * freq_hz * t)
        + 0.3 * np.sin(2 * np.pi * 2 * freq_hz * t)
        + 0.1 * np.sin(2 * np.pi * 3 * freq_hz * t)
    )
    sf.write(path, waveform.astype(np.float32), sr)


@pytest.fixture
def synthetic_wav():
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    create_synthetic_wav(path, duration_sec=1.5, sr=16000, freq_hz=440.0)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_librosa_acoustic_extractor_features(synthetic_wav):
    extractor = LibrosaAcousticExtractor()
    decoded = extractor.decode_audio(synthetic_wav, target_sr=16000, max_duration=10.0)

    assert decoded.sample_rate == 16000
    assert 1.4 <= decoded.duration_seconds <= 1.6
    assert len(decoded.audio) > 0
    assert np.max(np.abs(decoded.audio)) <= 1.0

    # 1. Mel Spectrogram
    mel_db = extractor.extract_log_mel_spectrogram(decoded.audio, decoded.sample_rate, n_mels=80)
    assert mel_db.shape[0] == 80
    assert mel_db.shape[1] > 0

    # 2. Fundamental Frequency (F0) & Pitch Variance via YIN
    f0_mean, f0_variance = extractor.compute_pitch_and_variance(decoded.audio, decoded.sample_rate)
    assert 400.0 <= f0_mean <= 480.0
    assert f0_variance >= 0.0

    # 3. Phase Discontinuity
    phase_disc = extractor.compute_phase_discontinuity(decoded.audio)
    assert 0.0 <= phase_disc <= 1.0

    # 4. Spectral Features
    spectral = extractor.compute_spectral_features(decoded.audio, decoded.sample_rate)
    assert "spectral_centroid_mean" in spectral
    assert "spectral_bandwidth_mean" in spectral
    assert "spectral_rolloff_mean" in spectral
    assert "zero_crossing_rate_mean" in spectral
    assert spectral["spectral_centroid_mean"] > 0.0

    # 5. Splicing Boundaries
    markers = extractor.detect_splice_boundaries(decoded.audio, decoded.sample_rate)
    assert isinstance(markers, list)


def test_spectrogram_generator():
    gen = SpectrogramGenerator()
    dummy_spec = np.random.uniform(-80.0, 0.0, (80, 120))
    artifact_path, base64_png = gen.generate_spectrogram_image(dummy_spec, filename_prefix="test_spec")

    assert os.path.isfile(artifact_path)
    assert os.path.getsize(artifact_path) > 0
    assert len(base64_png) > 100
    if os.path.exists(artifact_path):
        os.remove(artifact_path)


def test_aasist_classifier_architecture_and_service():
    model = AASISTClassifierNet(node_dim=64)
    # Test batch forward pass
    dummy_audio = torch.randn(2, 1, 16000)
    logits = model(dummy_audio)
    assert logits.shape == (2, 2)

    # Test inference service
    service = AudioAuthenticityInferenceService()
    prob, details = service.predict_audio(dummy_audio[0, 0].numpy(), sample_rate=16000)
    assert 0.0 <= prob <= 1.0
    assert details["samples_analyzed"] == 16000
    assert service.model_name == "TruthLens-PyTorch-AASIST-AudioClassifier"
    assert service.model_version == "0.1.0-dev"


def test_audio_analysis_pipeline_e2e(synthetic_wav):
    pipeline = AudioAnalysisPipeline()
    result = pipeline.analyze_audio(synthetic_wav)

    assert result.status == "COMPLETED"
    assert 0.0 <= result.synthetic_voice_prob <= 1.0
    assert result.pitch_variance >= 0.0
    assert result.spectrogram_base64 is not None
    assert len(result.spectrogram_base64) > 50
    assert result.evidence.duration_seconds > 1.0
    assert result.evidence.pitch_mean > 0.0
    assert result.evidence.phase_discontinuity_score >= 0.0

    # Clean up generated artifact
    if result.spectrogram_url and os.path.exists(result.spectrogram_url):
        os.remove(result.spectrogram_url)


def test_audio_endpoint_success(synthetic_wav):
    client = TestClient(app)
    with open(synthetic_wav, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/analyze/audio",
        files={"file": ("test.wav", file_bytes, "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "synthetic_voice_prob" in data
    assert 0.0 <= data["synthetic_voice_prob"] <= 1.0
    assert "spectrogram_base64" in data
    assert "pitch_variance" in data
    assert "evidence" in data
    assert data["model_name"] == "TruthLens-PyTorch-AASIST-AudioClassifier"
    assert data["status"] == "COMPLETED"


def test_audio_endpoint_validation_errors():
    client = TestClient(app)

    # 1. Invalid content type
    response = client.post(
        "/api/v1/analyze/audio",
        files={"file": ("bad.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported media content type" in response.json()["detail"]

    # 2. Empty file
    response = client.post(
        "/api/v1/analyze/audio",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
