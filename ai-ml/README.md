# TruthLens — AI/ML Microservice

**Blueprint Module 05 — Image Authenticity Analysis**  
**Owner:** Vishal (AI/ML Developer)  
**Status:** Phase 2 — Media Intelligence (Blueprint Section L)

---

## Overview

This directory contains the **Python FastAPI microservice** that powers the AI/ML analysis engines for the TruthLens platform. It is consumed internally by the Spring Boot backend orchestration gateway (Module 19).

Currently implemented: **Module 05 — Image Authenticity Analysis**

---

## Architecture

```
Spring Boot Backend (Module 19)
        │
        │  POST /api/image/analyze  (internal HTTP)
        ▼
TruthLens AI/ML FastAPI Service  (this directory)
        │
        ├── PyTorch EfficientNet-B0 (timm)   → synthetic_prob
        ├── OpenCV ELA Generator              → manipulation_prob + ela_heatmap_url
        ├── Noise Variance / FFT Analyser     → noise_variance
        └── Grad-CAM Attention Exporter       → grad_cam_url
        │
        ▼
Results JSON → Spring Boot → image_analysis DB table → Module 15 (Risk Engine)
                                                      → Module 16 (Dashboard)
```

---

## Tech Stack

| Component | Technology | Blueprint Reference |
|---|---|---|
| Language | Python 3.11 | Section E |
| Microservice | FastAPI + Uvicorn | Section E |
| Deep Learning | PyTorch 2.2 | Section E |
| Vision Models | timm (efficientnet_b0) | Section E |
| Computer Vision | OpenCV | Section E |
| Image I/O | Pillow | Section E (implied) |
| Testing | pytest | Section I |

---

## Project Structure

```
ai-ml/
├── main.py                              # FastAPI app entry point
├── requirements.txt                     # All dependencies (pinned)
├── .env.example                         # Config template (no secrets)
├── conftest.py                          # pytest path setup
│
├── config/
│   └── settings.py                      # Pydantic settings
│
├── schemas/
│   └── image_analysis.py                # Request / Response Pydantic models
│
├── utils/
│   ├── image_utils.py                   # Load, validate, preprocess images
│   └── storage.py                       # Save heatmap PNGs to disk
│
├── services/
│   └── image_analysis/
│       ├── ela.py                       # OpenCV ELA heatmap generator
│       ├── noise.py                     # Noise variance + FFT analysis
│       ├── classifier.py                # PyTorch timm inference wrapper
│       ├── gradcam.py                   # Grad-CAM attention exporter
│       ├── service.py                   # Pipeline orchestrator
│       └── router.py                    # FastAPI router (POST /api/image/analyze)
│
└── tests/
    ├── test_ela.py                      # ELA unit tests
    ├── test_noise.py                    # Noise/FFT unit tests
    ├── test_classifier.py               # Classifier unit tests
    ├── test_gradcam.py                  # Grad-CAM unit tests
    └── test_image_router.py             # Full HTTP integration tests
```

---

## Setup

### 1. Create and activate a virtual environment

```bash
cd ai-ml
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env if needed — defaults are fine for local development
```

---

## Running the Service

### Development (with auto-reload)

```bash
cd ai-ml
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 2
```

The service will be available at `http://localhost:8001`.  
API documentation: `http://localhost:8001/docs`

---

## API Endpoints

### `POST /api/image/analyze`
**Role Required:** INTERNAL / API (called by Spring Boot, not exposed publicly)

**Request body:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_path": "/path/to/uploaded/image.jpg"
}
```

**Response body:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "synthetic_prob": 0.87,
  "manipulation_prob": 0.64,
  "ela_heatmap_url": "storage/ela/550e8400-....png",
  "grad_cam_url": "storage/gradcam/550e8400-....png",
  "noise_variance": 142.5,
  "confidence": 0.74,
  "processing_time_ms": 1240,
  "status": "completed",
  "error_message": null
}
```

**Error responses:**
| Code | Cause |
|---|---|
| `400` | Image file not found, unsupported format, or corrupted file |
| `422` | Missing/invalid request fields (Pydantic validation) |
| `500` | Unexpected internal error |

### `GET /api/image/health`
Liveness probe. Returns `{"service": "image-analysis", "status": "ok"}`.

---

## Running Tests

```bash
cd ai-ml
pytest tests/ -v --tb=short
```

### Test coverage:
| Test file | What it covers |
|---|---|
| `test_ela.py` | ELA heatmap shape, dtype, value range, solid/noisy image behavior |
| `test_noise.py` | Laplacian variance and FFT ratio types, ranges, ordering |
| `test_classifier.py` | Model load, eval mode, singleton, output range, determinism |
| `test_gradcam.py` | Grad-CAM shape, dtype, resize correctness |
| `test_image_router.py` | Full HTTP: valid input (all fields), 400 invalid path, 422 missing fields |

---

## Integration Notes for Backend Team (Yashas)

### 1. HTTP Call Pattern

Module 19 (job worker) should call this service after receiving an image analysis job from Redis:

```http
POST http://ai-ml-service:8001/api/image/analyze
Content-Type: application/json

{
  "media_id": "<UUID from analysis_jobs table>",
  "image_path": "<storage_path from media table>"
}
```

### 2. Database — `image_analysis` table

The response fields map to the following columns (Blueprint Section F):

| Response Field | DB Column | Type |
|---|---|---|
| `synthetic_prob` | `synthetic_prob` | FLOAT |
| `ela_heatmap_url` | `ela_heatmap_path` | VARCHAR |
| `noise_variance` | `noise_variance` | FLOAT |
| `manipulation_prob` | `manipulation_prob` ⚠️ | FLOAT |

> ⚠️ **Action required (Yashas):** `manipulation_prob` appears in Module 05 Build Scope but is missing from the Section F `image_analysis` schema table. Please add this column to the Hibernate entity and migration script.

### 3. Storage Volume

The AI/ML service writes ELA heatmaps and Grad-CAM PNGs to `STORAGE_DIR` (default: `./storage`).  
The Spring Boot backend must mount the same volume to serve these files via the media storage API (MinIO or local disk — Blueprint Section E).

### 4. Service Port

Default port: `8001`. Configure via `PORT` env var.

---

## Model Information

| Property | Value |
|---|---|
| Architecture | `efficientnet_b0` (timm pretrained) |
| Head | Linear(num_features → 1) + Sigmoid |
| Weights | ImageNet pretrained backbone + untrained binary head |
| Fine-tuning | Drop a `.pt` checkpoint in `models/` and set `CLASSIFIER_CHECKPOINT` in `.env` |
| Target datasets | CIFAKE, Midjourney-v6 Bench (Blueprint Section K) |

> **Note:** The binary head is randomly initialised until fine-tuned on CIFAKE or equivalent dataset. The pretrained ImageNet backbone still provides meaningful texture/frequency features for the demo.

---

## Security Notes (AGENTS.md compliance)

- ✅ No API keys, credentials, or secrets in this codebase
- ✅ No model weights committed to the repository  
- ✅ All implementation kept inside `ai-ml/`
- ✅ No backend, frontend, or devops files modified

---

## Limitations & TODOs

| Item | Priority | Notes |
|---|---|---|
| Fine-tune classifier on CIFAKE | HIGH | Use `CLASSIFIER_CHECKPOINT` env var to load weights |
| MinIO integration for heatmap storage | MEDIUM | Currently writes to local disk; backend team handles MinIO |
| Copy-move / splicing detection | FUTURE | Blueprint mentions these; not yet implemented in noise.py |
| Async endpoint | LOW | Current endpoint is synchronous; Module 19 manages async via Redis queue |
