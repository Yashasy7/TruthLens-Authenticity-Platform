# TruthLens AI/ML Service — Image Authenticity Analysis (Module 05)

FastAPI microservice providing dual-engine image authenticity analysis, synthetic AI generation detection, and localized forensic tampering evaluation.

---

## 1. Capabilities

- **Synthetic AI-Generation Detection**: PyTorch convolutional vision model architecture analyzing generative spatial and spectral feature patterns.
- **Grad-CAM Attention Maps**: Gradient-weighted class activation mapping highlighting regions that influenced the AI generation score.
- **Error Level Analysis (ELA)**: OpenCV-based JPEG recompression difference analysis detecting compression rate inconsistencies and spliced visual elements.
- **Noise Variance & Spatial Consistency**: High-frequency residual analysis evaluating sensor noise variance and patch-based noise distribution across the image plane.
- **2D Fast Fourier Transform (FFT)**: Frequency-domain anomaly analysis detecting periodic artifacts and radial energy distribution deviations typical of generative upsampling layers.
- **Copy-Move & Local Tampering**: Keypoint detection and descriptor clustering identifying cloned visual segments and splicing boundaries.

---

## 2. API Endpoints

- `GET /api/v1/health`: Service health and model telemetry.
- `POST /api/v1/analyze/image`: Multipart image analysis producing probabilities, heatmaps, and evidence metrics.

---

## 3. Running Locally

```bash
cd ai-ml
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Run tests:
```bash
pytest -v
```
