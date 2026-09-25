import io
import math
import numpy as np
import pytest
import soundfile as sf
import tempfile
import os
import cv2
from fastapi.testclient import TestClient

from app.main import app
from app.services.speech_preprocessor import SpeechPreprocessor
from app.services.speech_transcriber import SpeechTranscriber
from app.services.transcript_pipeline import TranscriptPipeline


def create_synthetic_wav(
    duration_seconds: float = 2.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    is_silent: bool = False,
) -> bytes:
    """Generates synthetic in-memory WAV audio bytes."""
    num_samples = int(duration_seconds * sample_rate)
    if is_silent:
        audio = np.zeros(num_samples, dtype=np.float32)
    else:
        t = np.linspace(0, duration_seconds, num_samples, endpoint=False)
        audio = 0.5 * np.sin(2 * np.pi * frequency * t).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def create_synthetic_video_with_audio(
    duration_seconds: float = 2.0,
    fps: float = 10.0,
    sample_rate: int = 16000,
) -> bytes:
    """Generates a synthetic MP4 video container with an audio track."""
    import subprocess
    import imageio_ffmpeg

    # Create video frame file
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
        vid_path = tmp_vid.name

    total_frames = int(duration_seconds * fps)
    out = cv2.VideoWriter(vid_path, fourcc, fps, (320, 240))
    for _ in range(total_frames):
        frame = np.full((240, 320, 3), 128, dtype=np.uint8)
        out.write(frame)
    out.release()

    # Create audio file
    wav_bytes = create_synthetic_wav(duration_seconds, sample_rate)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_aud:
        aud_path = tmp_aud.name
        tmp_aud.write(wav_bytes)

    # Mux into final mp4
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_mux:
        mux_path = tmp_mux.name

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", vid_path,
        "-i", aud_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        mux_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    with open(mux_path, "rb") as f:
        muxed_bytes = f.read()

    for p in [vid_path, aud_path, mux_path]:
        if os.path.exists(p):
            os.remove(p)

    return muxed_bytes


def test_speech_preprocessor_resampling_and_duration():
    """Verifies that speech preprocessor converts audio and measures duration accurately."""
    wav_bytes = create_synthetic_wav(duration_seconds=2.5, sample_rate=22050, frequency=300.0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        preprocessor = SpeechPreprocessor(target_sample_rate=16000)
        result = preprocessor.preprocess(tmp_path, media_type="AUDIO")

        assert os.path.isfile(result.wav_path)
        assert result.sample_rate == 16000
        assert math.isclose(result.duration_seconds, 2.5, abs_tol=0.2)
        assert not result.is_silent
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if "result" in locals():
            result.cleanup()


def test_speech_preprocessor_silent_audio_detection():
    """Verifies that silent audio is correctly identified by low RMS energy."""
    wav_bytes = create_synthetic_wav(duration_seconds=1.5, is_silent=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        preprocessor = SpeechPreprocessor()
        result = preprocessor.preprocess(tmp_path, media_type="AUDIO")

        assert result.is_silent is True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if "result" in locals():
            result.cleanup()


def test_speech_preprocessor_oversized_duration_raises_error():
    """Verifies that audio exceeding maximum duration triggers ValueError."""
    wav_bytes = create_synthetic_wav(duration_seconds=3.0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        preprocessor = SpeechPreprocessor(max_duration_seconds=2.0)
        with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
            preprocessor.preprocess(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_speech_transcriber_transcribe_audio():
    """Verifies Faster-Whisper ASR transcription output and word alignments."""
    wav_bytes = create_synthetic_wav(duration_seconds=2.0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        transcriber = SpeechTranscriber()
        full_text, lang, conf, segments, words_count, details = transcriber.transcribe(tmp_path)

        assert isinstance(full_text, str)
        assert isinstance(lang, str)
        assert 0.0 <= conf <= 1.0
        assert isinstance(segments, list)
        assert isinstance(words_count, int)
        assert details.get("engine") in ["Faster-Whisper", "AcousticFallbackASR"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_speech_transcriber_silent_audio_returns_empty():
    """Verifies that silent audio returns empty transcript and 1.0 confidence."""
    wav_bytes = create_synthetic_wav(duration_seconds=1.0, is_silent=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        transcriber = SpeechTranscriber()
        full_text, lang, conf, segments, words_count, details = transcriber.transcribe(
            tmp_path, is_silent=True
        )

        assert full_text == ""
        assert conf == 1.0
        assert len(segments) == 0
        assert words_count == 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_transcript_pipeline_audio_end_to_end():
    """Verifies end-to-end transcript extraction on audio input."""
    wav_bytes = create_synthetic_wav(duration_seconds=2.0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        pipeline = TranscriptPipeline()
        result = pipeline.analyze(tmp_path, media_type="AUDIO")

        assert result.status == "COMPLETED"
        assert result.duration_seconds > 0.0
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.evidence.media_type == "AUDIO"
        assert result.evidence.audio_sample_rate == 16000
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_transcript_pipeline_video_end_to_end():
    """Verifies end-to-end transcript extraction on video container with audio track."""
    muxed_bytes = create_synthetic_video_with_audio(duration_seconds=2.0)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(muxed_bytes)
        tmp_path = tmp.name

    try:
        pipeline = TranscriptPipeline()
        result = pipeline.analyze(tmp_path, media_type="VIDEO")

        assert result.status == "COMPLETED"
        assert result.evidence.media_type == "VIDEO"
        assert result.duration_seconds > 0.0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_api_analyze_stt_audio_success():
    """Tests FastAPI POST /api/v1/analyze/speech-to-text with audio upload."""
    client = TestClient(app)
    wav_bytes = create_synthetic_wav(duration_seconds=1.5)

    response = client.post(
        "/api/v1/analyze/speech-to-text",
        files={"file": ("interview.wav", io.BytesIO(wav_bytes), "audio/wav")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "full_text" in data
    assert "language" in data
    assert "confidence_score" in data
    assert "segments" in data
    assert data["status"] == "COMPLETED"
    assert data["evidence"]["media_type"] == "AUDIO"


def test_api_analyze_stt_video_success():
    """Tests FastAPI POST /api/v1/analyze/speech-to-text with video upload."""
    client = TestClient(app)
    muxed_bytes = create_synthetic_video_with_audio(duration_seconds=1.5)

    response = client.post(
        "/api/v1/analyze/speech-to-text",
        files={"file": ("broadcast.mp4", io.BytesIO(muxed_bytes), "video/mp4")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["evidence"]["media_type"] == "VIDEO"


def test_api_analyze_stt_unsupported_media_type():
    """Tests that images and unsupported types are rejected with HTTP 400."""
    client = TestClient(app)
    img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

    response = client.post(
        "/api/v1/analyze/speech-to-text",
        files={"file": ("photo.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert response.status_code == 400
    assert "Unsupported media content type" in response.json()["detail"]


def test_api_analyze_stt_empty_file():
    """Tests that empty files are rejected with HTTP 400."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze/speech-to-text",
        files={"file": ("empty.wav", io.BytesIO(b""), "audio/wav")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
