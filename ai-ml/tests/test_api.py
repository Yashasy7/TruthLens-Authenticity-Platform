from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["model_loaded"] is True
    assert "TruthLens" in data["model_name"]


def test_analyze_image_valid_jpeg(sample_jpeg_bytes):
    files = {"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert 0.0 <= data["ai_prob"] <= 1.0
    assert 0.0 <= data["manipulation_prob"] <= 1.0
    assert "noise_variance" in data
    assert "fft_anomaly_score" in data
    assert "copy_move_detected" in data
    assert "splicing_detected" in data
    assert data["status"] == "COMPLETED"
    assert len(data["ela_heatmap_base64"]) > 0
    assert len(data["gradcam_heatmap_base64"]) > 0
    assert "evidence" in data


def test_analyze_image_valid_png(sample_png_bytes):
    files = {"file": ("test.png", sample_png_bytes, "image/png")}
    response = client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["evidence"]["image_width"] == 200
    assert data["evidence"]["image_height"] == 200


def test_analyze_image_corrupt_payload(corrupt_bytes):
    files = {"file": ("broken.jpg", corrupt_bytes, "image/jpeg")}
    response = client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 400
    assert "Corrupt or unreadable" in response.json()["detail"]


def test_analyze_image_empty_file():
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    response = client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_image_unsupported_content_type():
    files = {"file": ("document.pdf", b"%PDF-1.5...", "application/pdf")}
    response = client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 400
    assert "Must be an image" in response.json()["detail"]
