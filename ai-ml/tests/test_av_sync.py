import os
import subprocess
import tempfile
import cv2
import numpy as np
import soundfile as sf
import torch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.mediapipe_lip_tracker import MediaPipeLipTracker, FrameLipData
from app.services.audio_envelope_correlator import AudioEnvelopeCorrelator
from app.services.syncnet_evaluator import SyncNetEvaluator, SyncNetDualModel
from app.services.av_sync_pipeline import AvSyncAnalysisPipeline
from app.services.face_detector_tracker import DetectedFace


# =============================================================================
# Synthetic Video & Audio Fixtures with FFmpeg Demuxing Support
# =============================================================================

def create_synthetic_av_video(
    video_path: str,
    duration_sec: float = 2.0,
    fps: float = 25.0,
    audio_freq: float = 440.0,
    offset_sec: float = 0.0,
) -> None:
    """
    Creates a small valid MP4 test video containing both:
    1. Visual frames with an animated talking mouth proxy.
    2. A synchronized (or offset) audio speech tone stream.
    Uses FFmpeg to mux video and audio tracks.
    """
    num_frames = int(duration_sec * fps)
    temp_dir = tempfile.mkdtemp(prefix="truthlens_test_av_")

    raw_video_path = os.path.join(temp_dir, "raw_video.mp4")
    raw_audio_path = os.path.join(temp_dir, "raw_audio.wav")

    try:
        # 1. Generate video frames
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(raw_video_path, fourcc, fps, (160, 160))
        for i in range(num_frames):
            frame = np.full((160, 160, 3), 40, dtype=np.uint8)
            # Face circle
            cv2.circle(frame, (80, 80), 45, (200, 180, 160), -1)
            # Eyes
            cv2.circle(frame, (65, 65), 5, (0, 0, 0), -1)
            cv2.circle(frame, (95, 65), 5, (0, 0, 0), -1)
            # Nose
            cv2.circle(frame, (80, 80), 3, (0, 0, 0), -1)
            # Animated mouth opening with sinusoidal cycle (simulating syllables)
            mouth_opening = int(4 + 8 * (0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * (i / fps))))
            cv2.ellipse(frame, (80, 105), (16, mouth_opening), 0, 0, 360, (50, 20, 20), -1)
            out.write(frame)
        out.release()

        # 2. Generate audio waveform
        sr = 16000
        n_samples = int(duration_sec * sr)
        t = np.linspace(0, duration_sec, n_samples, endpoint=False)
        # Audio energy modulated in sync with visual mouth opening (or offset by offset_sec)
        t_delayed = t - offset_sec
        envelope = np.clip(0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t_delayed), 0.0, 1.0)
        carrier = np.sin(2 * np.pi * audio_freq * t)
        waveform = (envelope * carrier).astype(np.float32)
        sf.write(raw_audio_path, waveform, sr)

        # 3. Mux using FFmpeg
        correlator = AudioEnvelopeCorrelator()
        ffmpeg_cmd = correlator._resolve_ffmpeg_cmd()

        cmd = [
            ffmpeg_cmd,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", raw_video_path,
            "-i", raw_audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            video_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg muxing failed: {res.stderr}")

    finally:
        # Cleanup temporary intermediate files
        for p in [raw_video_path, raw_audio_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass


@pytest.fixture
def synchronized_video():
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    create_synthetic_av_video(path, duration_sec=1.5, fps=25.0, audio_freq=440.0, offset_sec=0.0)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def offset_video():
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    # 200ms audio lag
    create_synthetic_av_video(path, duration_sec=1.5, fps=25.0, audio_freq=440.0, offset_sec=0.200)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def video_without_audio():
    """Video file containing image frames but strictly no audio track."""
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, 25.0, (120, 120))
    for _ in range(25):
        frame = np.full((120, 120, 3), 100, dtype=np.uint8)
        out.write(frame)
    out.release()
    yield path
    if os.path.exists(path):
        os.remove(path)


# =============================================================================
# Unit Tests — MediaPipe Lip Tracker
# =============================================================================

def test_lip_tracker_valid_face():
    tracker = MediaPipeLipTracker(crop_size=96)
    # Generate 5 test frames with a face
    frames = []
    timestamps = []
    for i in range(5):
        img = np.full((160, 160, 3), 50, dtype=np.uint8)
        # Face rectangle
        cv2.circle(img, (80, 80), 40, (200, 180, 160), -1)
        # Mouth
        cv2.ellipse(img, (80, 100), (15, 5 + i * 2), 0, 0, 360, (0, 0, 0), -1)
        frames.append(img)
        timestamps.append(i * 0.04)

    res = tracker.track_lips(frames, timestamps)
    assert len(res.timestamps) == 5
    assert len(res.lip_crops) == 5
    assert res.lip_crops[0].shape == (96, 96)
    assert len(res.lip_activity) == 5
    assert 0.0 <= res.tracking_stability <= 1.0


def test_lip_tracker_no_face():
    tracker = MediaPipeLipTracker()
    blank_frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(5)]
    timestamps = [i * 0.04 for i in range(5)]

    res = tracker.track_lips(blank_frames, timestamps)
    assert res.detected_faces_count == 0
    assert res.primary_track_id == -1
    assert res.tracking_stability == 0.0
    assert len(res.lip_crops) == 5
    assert len(res.lip_activity) == 5


def test_lip_tracker_intermittent_and_multi_face():
    tracker = MediaPipeLipTracker()
    frames = []
    timestamps = []
    for i in range(8):
        img = np.zeros((160, 160, 3), dtype=np.uint8)
        if i % 2 == 0:
            # Face 1 (speaker)
            cv2.circle(img, (50, 80), 30, (200, 180, 160), -1)
            # Face 2 (silent bystander)
            cv2.circle(img, (120, 80), 20, (180, 180, 180), -1)
        frames.append(img)
        timestamps.append(i * 0.04)

    res = tracker.track_lips(frames, timestamps)
    assert len(res.lip_crops) == 8
    assert res.tracking_stability >= 0.0


# =============================================================================
# Unit Tests — Audio Envelope Correlator
# =============================================================================

def test_audio_envelope_extraction(synchronized_video):
    correlator = AudioEnvelopeCorrelator()
    wav_path = correlator.extract_audio_from_video(synchronized_video)

    assert os.path.isfile(wav_path)
    assert os.path.getsize(wav_path) > 0

    y, sr = sf.read(wav_path)
    os.remove(wav_path)

    assert sr == 16000
    assert len(y) > 0

    # Compute envelope on video timeline
    target_ts = np.linspace(0.0, 1.0, 25)
    env = correlator.compute_audio_envelope(y, sr, target_ts)
    assert len(env) == 25
    assert np.max(env) <= 1.0
    assert np.min(env) >= 0.0


def test_audio_envelope_correlation_zero_and_offset():
    correlator = AudioEnvelopeCorrelator()
    fps = 25.0
    n = 100
    t = np.arange(n) / fps

    # Synthetic synchronized signals (3 Hz syllables)
    lip_activity = 0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t)
    audio_env = lip_activity.copy()

    # 1. Aligned test
    offset_ms, corr, conf, lags, corrs = correlator.correlate(lip_activity, audio_env, fps=fps)
    assert abs(offset_ms) <= 40.0  # Within 1 frame
    assert corr > 0.80
    assert conf > 0.50

    # 2. Offset test (+200ms audio lag = 5 frames lag at 25 fps)
    lag_frames = 5
    audio_delayed = np.roll(audio_env, lag_frames)
    offset_ms_lag, corr_lag, conf_lag, _, _ = correlator.correlate(lip_activity, audio_delayed, fps=fps)
    assert offset_ms_lag > 0.0  # Positive lag detected


def test_video_without_audio_fails_extraction(video_without_audio):
    correlator = AudioEnvelopeCorrelator()
    with pytest.raises(ValueError, match="no audio stream"):
        correlator.extract_audio_from_video(video_without_audio)


# =============================================================================
# Unit Tests — SyncNet Evaluator
# =============================================================================

def test_syncnet_architecture_and_forward():
    model = SyncNetDualModel(embedding_dim=128)
    model.eval()

    # B=2, 5 frames of 96x96
    v_input = torch.randn(2, 5, 96, 96)
    # B=2, 1 channel, 80 mel bands x 20 time steps
    a_input = torch.randn(2, 1, 80, 20)

    e_dist, c_sim = model(v_input, a_input)
    assert e_dist.shape == (2,)
    assert c_sim.shape == (2,)
    # Normalized embeddings Euclidean distance is in [0.0, 2.0]
    assert (e_dist >= 0.0).all() and (e_dist <= 2.0).all()
    # Cosine similarity in [-1.0, 1.0]
    assert (c_sim >= -1.0).all() and (c_sim <= 1.0).all()


def test_syncnet_evaluator_development_mode():
    evaluator = SyncNetEvaluator(checkpoint_path="")
    assert evaluator.is_development_model is True
    assert "dev" in evaluator.model_version

    # Evaluate on dummy crops and mel
    dummy_crops = [np.random.randint(0, 255, (96, 96), dtype=np.uint8) for _ in range(15)]
    dummy_mel = np.random.randn(80, 60).astype(np.float32)

    res = evaluator.evaluate_sync(dummy_crops, dummy_mel, fps=25.0)
    assert "best_offset_ms" in res
    assert "min_distance" in res
    assert "confidence" in res
    assert 0.0 <= res["min_distance"] <= 2.0


# =============================================================================
# Pipeline End-to-End & Real Runtime Tests
# =============================================================================

def test_av_sync_pipeline_synchronized_video(synchronized_video):
    pipeline = AvSyncAnalysisPipeline()
    result = pipeline.analyze_video(synchronized_video)

    assert result.status == "COMPLETED"
    assert 0.0 <= result.sync_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.evidence.video_duration_seconds > 0.0
    assert result.evidence.audio_duration_seconds > 0.0
    assert result.evidence.fps == 25.0
    assert result.evidence.is_development_model is True
    assert result.model_name == "TruthLens-PyTorch-SyncNet-DualStream"


def test_av_sync_pipeline_offset_video(offset_video):
    pipeline = AvSyncAnalysisPipeline()
    result = pipeline.analyze_video(offset_video)

    assert result.status == "COMPLETED"
    assert 0.0 <= result.sync_score <= 1.0
    # Desynchronized / offset video should report offset or mismatch segments
    assert isinstance(result.mismatch_segments, list)


def test_av_sync_pipeline_missing_audio_raises_error(video_without_audio):
    pipeline = AvSyncAnalysisPipeline()
    with pytest.raises(ValueError, match="no audio stream"):
        pipeline.analyze_video(video_without_audio)


# =============================================================================
# FastAPI Endpoint Tests
# =============================================================================

def test_api_analyze_av_sync_success(synchronized_video):
    client = TestClient(app)
    with open(synchronized_video, "rb") as f:
        response = client.post(
            "/api/v1/analyze/av-sync",
            files={"file": ("test_sync.mp4", f, "video/mp4")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "sync_score" in data
    assert "lip_offset_ms" in data
    assert "mismatch_segments" in data
    assert "evidence" in data
    assert data["status"] == "COMPLETED"
    assert 0.0 <= data["sync_score"] <= 1.0


def test_api_analyze_av_sync_unsupported_media_type():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze/av-sync",
        files={"file": ("image.jpg", b"fake-jpg-content", "image/jpeg")}
    )
    assert response.status_code == 400
    assert "Must be a video format" in response.json()["detail"]


def test_api_analyze_av_sync_empty_file():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze/av-sync",
        files={"file": ("empty.mp4", b"", "video/mp4")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_api_analyze_av_sync_missing_audio(video_without_audio):
    client = TestClient(app)
    with open(video_without_audio, "rb") as f:
        response = client.post(
            "/api/v1/analyze/av-sync",
            files={"file": ("silent.mp4", f, "video/mp4")}
        )
    assert response.status_code == 400
    assert "audio stream" in response.json()["detail"].lower()
