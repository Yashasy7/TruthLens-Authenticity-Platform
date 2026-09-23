import os
import tempfile
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ffmpeg_sampler import FFmpegVideoSampler
from app.services.face_detector_tracker import RetinaFaceTracker, DetectedFace
from app.services.video_deepfake_classifier import VideoDeepfakeClassifierNet, VideoDeepfakeInferenceService
from app.services.temporal_analyzer import TemporalForensicAnalyzer
from app.services.video_pipeline import VideoAnalysisPipeline


def create_synthetic_test_video(path: str, num_frames: int = 15, fps: float = 5.0):
    """Generates a small valid MP4 test video with animated content."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (160, 120))
    for i in range(num_frames):
        frame = np.full((120, 160, 3), 40 + i * 5, dtype=np.uint8)
        # Draw moving circle/face proxy
        cv2.circle(frame, (40 + i * 4, 60), 20, (200, 180, 160), -1)
        # Draw two eye dots
        cv2.circle(frame, (35 + i * 4, 55), 3, (0, 0, 0), -1)
        cv2.circle(frame, (45 + i * 4, 55), 3, (0, 0, 0), -1)
        out.write(frame)
    out.release()


@pytest.fixture
def synthetic_video():
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    create_synthetic_test_video(path, num_frames=15, fps=5.0)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_ffmpeg_sampler_ordering_and_timestamps(synthetic_video):
    sampler = FFmpegVideoSampler(sample_fps=2.0)
    frames, duration = sampler.sample_video(synthetic_video)

    assert len(frames) > 0
    assert duration > 0.0

    # Verify chronological ordering
    prev_time = -1.0
    for idx, f in enumerate(frames):
        assert f.frame_index == idx
        assert f.timestamp_seconds >= prev_time
        assert f.image_bgr.shape == (120, 160, 3)
        prev_time = f.timestamp_seconds


def test_face_detector_and_tracker_continuity():
    tracker = RetinaFaceTracker()
    img1 = np.zeros((200, 200, 3), dtype=np.uint8)
    img2 = np.zeros((200, 200, 3), dtype=np.uint8)

    # Manually associate mock faces
    f1 = DetectedFace(x=50, y=50, width=40, height=40, confidence=0.90)
    tracker.active_tracks[1] = f1

    # In frame 2, face shifted slightly
    f2 = DetectedFace(x=54, y=52, width=40, height=40, confidence=0.88)
    # Mock detect to return f2
    tracker.detect_faces = lambda img: [f2]

    tracked = tracker.track_faces_in_frame(img2, frame_index=1)
    assert len(tracked) == 1
    assert tracked[0].track_id == 1  # Retained same track ID


def test_temporal_analyzer_sensitivity():
    analyzer = TemporalForensicAnalyzer()
    face1 = np.full((100, 100, 3), 128, dtype=np.uint8)
    cv2.circle(face1, (50, 50), 20, (255, 255, 255), -1)

    face2_identical = face1.copy()
    face3_disparate = np.full((100, 100, 3), 10, dtype=np.uint8)
    cv2.rectangle(face3_disparate, (10, 10), (80, 80), (255, 0, 0), -1)

    score_identical = analyzer.analyze_temporal_inconsistency(face1, face2_identical)
    score_disparate = analyzer.analyze_temporal_inconsistency(face1, face3_disparate)

    assert 0.0 <= score_identical <= 1.0
    assert 0.0 <= score_disparate <= 1.0
    assert score_disparate > score_identical


def test_video_deepfake_classifier_reproducibility():
    service1 = VideoDeepfakeInferenceService()
    service2 = VideoDeepfakeInferenceService()

    # Verify deterministic weights
    for p1, p2 in zip(service1.model.parameters(), service2.model.parameters()):
        assert (p1 == p2).all()

    dummy_face = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    score1 = service1.score_face_crop(dummy_face)
    score2 = service2.score_face_crop(dummy_face)

    assert score1 == score2
    assert 0.0 <= score1 <= 1.0
    assert service1.model_version == "0.1.0-dev"


def test_video_pipeline_end_to_end(synthetic_video):
    pipeline = VideoAnalysisPipeline()
    result = pipeline.analyze_video(synthetic_video)

    assert result.status == "COMPLETED"
    assert 0.0 <= result.deepfake_prob <= 1.0
    assert result.total_frames_sampled > 0
    assert len(result.frame_scores) == result.total_frames_sampled
    assert result.model_version == "0.1.0-dev"

    for fs in result.frame_scores:
        assert 0.0 <= fs.deepfake_score <= 1.0
        assert 0.0 <= fs.temporal_inconsistency <= 1.0


def test_api_analyze_video_success(synthetic_video):
    client = TestClient(app)
    with open(synthetic_video, "rb") as f:
        response = client.post(
            "/api/v1/analyze/video",
            files={"file": ("test.mp4", f, "video/mp4")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "deepfake_prob" in data
    assert "frame_scores" in data
    assert "suspicious_timestamps" in data
    assert data["status"] == "COMPLETED"


def test_api_analyze_video_invalid_content_type():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze/video",
        files={"file": ("test.txt", b"plain text", "text/plain")}
    )
    assert response.status_code == 400
    assert "Must be a video" in response.json()["detail"]


def test_api_analyze_video_empty_file():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze/video",
        files={"file": ("empty.mp4", b"", "video/mp4")}
    )
    assert response.status_code == 400


# =============================================================================
# PyTorch RetinaFace Unit & Integration Tests (FINDING-06-01)
# =============================================================================

from app.services.face_detector_tracker import RetinaFaceDetector, RetinaFaceNet


def test_retinaface_detector_initialization():
    detector = RetinaFaceDetector()
    assert isinstance(detector.model, RetinaFaceNet)
    assert detector.detector_name == "RetinaFace-MobileNet0.25-PyTorch"
    assert detector.model_version == "0.1.0-dev"
    assert detector.is_production_checkpoint is False
    assert detector.confidence_threshold == 0.50
    assert detector.nms_threshold == 0.40


def test_retinaface_inference_execution_and_format():
    detector = RetinaFaceDetector(confidence_threshold=0.01)  # Low threshold to capture detections
    test_frame = np.full((120, 160, 3), 128, dtype=np.uint8)
    # Draw high-contrast facial oval with features
    cv2.ellipse(test_frame, (80, 60), (30, 40), 0, 0, 360, (220, 200, 180), -1)
    cv2.circle(test_frame, (70, 50), 4, (20, 20, 20), -1)
    cv2.circle(test_frame, (90, 50), 4, (20, 20, 20), -1)
    cv2.ellipse(test_frame, (80, 75), (12, 6), 0, 0, 180, (40, 40, 120), -1)

    detections = detector.detect_faces(test_frame)
    assert isinstance(detections, list)
    for det in detections:
        assert isinstance(det, DetectedFace)
        assert det.x >= 0 and det.y >= 0
        assert det.width > 0 and det.height > 0
        assert 0.0 <= det.confidence <= 1.0
        assert det.landmarks is not None
        assert len(det.landmarks) == 5  # 5 facial landmarks (eyes, nose, mouth corners)
        for pt in det.landmarks:
            assert len(pt) == 2


def test_retinaface_empty_or_invalid_frame_safe_handling():
    detector = RetinaFaceDetector()
    assert detector.detect_faces(None) == []
    assert detector.detect_faces(np.empty((0, 0, 3), dtype=np.uint8)) == []


def test_retinaface_missing_checkpoint_raises_error():
    with pytest.raises(FileNotFoundError, match="Configured RetinaFace model checkpoint not found"):
        RetinaFaceDetector(model_path="non_existent_retinaface_weights.pth")


# =============================================================================
# PyTorch 3D-CNN Spatiotemporal Sequence Tests (FINDING-06-02)
# =============================================================================

from app.services.video_deepfake_classifier import VideoDeepfake3DCNNNet
import torch


def test_pytorch_3dcnn_architecture_and_5d_tensor_forward():
    net = VideoDeepfake3DCNNNet()
    # Verify input tensor [Batch, Channels, Time, Height, Width]
    tensor5d = torch.randn(1, 3, 4, 112, 112)
    output = net(tensor5d)
    assert output.shape == (1, 1)
    prob = float(torch.sigmoid(output).item())
    assert 0.0 <= prob <= 1.0


def test_video_deepfake_sequence_inference_and_padding():
    service = VideoDeepfakeInferenceService(sequence_length=4)
    assert service.model_name == "TruthLens-PyTorch-3DCNN-DeepfakeClassifier"
    assert service.sequence_length == 4

    # 1. Test single frame (should pad deterministically to 4 frames)
    crop1 = np.full((112, 112, 3), 120, dtype=np.uint8)
    score_single = service.score_face_crop(crop1)
    assert 0.0 <= score_single <= 1.0

    # 2. Test multi-frame sequence of 2 frames (pads to 4)
    crop2 = np.full((112, 112, 3), 150, dtype=np.uint8)
    score_seq2 = service.score_face_sequence([crop1, crop2])
    assert 0.0 <= score_seq2 <= 1.0

    # 3. Test exact sequence of 4 frames
    seq4 = [np.full((112, 112, 3), 100 + i * 20, dtype=np.uint8) for i in range(4)]
    score_seq4 = service.score_face_sequence(seq4)
    assert 0.0 <= score_seq4 <= 1.0


def test_video_deepfake_missing_checkpoint_raises_error():
    with pytest.raises(FileNotFoundError, match="Configured video deepfake model checkpoint not found"):
        VideoDeepfakeInferenceService(model_path="non_existent_3dcnn_weights.pth")

