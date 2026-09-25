# TruthLens — AI/ML Microservice

**Blueprint Modules Implemented:**
- **Module 05 — Image Authenticity Analysis**
- **Module 06 — Video Deepfake Detection & Forensics**
- **Module 07 — Audio Authenticity & Voice Forensics**
- **Module 08 — Audio-Visual Synchronization & Lip-Sync Forensics**
- **Module 09 — OCR & Visual Text Extraction**
- **Module 10 — Speech-to-Text & Transcript Extraction**  
**Owner:** Vishal (AI/ML Developer)  
**Status:** Completed & Backend-Aligned (Blueprint Section L / Modules 05, 06, 07, 08, 09 & 10)

---

## Overview

This directory contains the **Python FastAPI microservice** powering the AI/ML authenticity, forensic, visual extraction, and speech transcription engines for the TruthLens platform. It executes deep learning models (2D/3D CNNs, spectro-temporal AASIST models, two-stream SyncNet embeddings, Faster-Whisper ASR) and classical forensic signal processing / computer vision algorithms to evaluate media integrity:
- **Module 05 (Image):** Detects synthetic (Diffusion/GAN) generation, localized Error Level Analysis (ELA) anomalies, noise variance inconsistencies, and copy-move/splicing cloning.
- **Module 06 (Video):** Ingests video streams, deterministically samples frames, detects/tracks facial regions, evaluates 3D-CNN temporal deepfake features, measures frame-to-frame inconsistency, and generates an explainable suspicious timeline.
- **Module 07 (Audio):** Decodes audio tracks to deterministic 16 kHz mono waveforms, extracts Mel-spectrograms (Base64 PNG artifacts) and MFCCs, performs pitch tracking (F0) and pitch variance analysis, estimates phase discontinuity and vocoder spectral anomalies, detects splicing boundaries, and executes PyTorch AASIST anti-spoofing classification over temporal windows.
- **Module 08 (AV Sync):** Cross-correlates speech acoustic envelopes with visual lip dynamics (MAR velocity + motion flux), projects 5-frame mouth visemes and 20-frame log-Mel spectrograms into 128-d SyncNet embedding space, identifies millisecond-level offsets, and segments localized anomalies (DUBBING, MUTED_SPEECH, DESYNC).
- **Module 09 (OCR & Text Extraction):** Preprocesses images and video keyframes via CLAHE, bilateral filtering, deskewing, and dual Otsu/adaptive binarization; extracts visual text and bounding boxes using pluggable OCR engines (Tesseract, EasyOCR, or OpenCV morphological fallback); detects language; and deduplicates persistent video chyrons/news banners across consecutive frames.
- **Module 10 (Speech-to-Text & Transcripts):** Demuxes audio streams from audio and video containers into 16 kHz mono WAV, evaluates acoustic silence gating, and transcribes speech into timestamped phrase segments and word-level timing offsets with language detection and confidence scoring via Faster-Whisper / Acoustic Energy ASR.

The service is consumed internally by Yashas's Spring Boot backend orchestration gateway (`FastApiAiServiceClient.java`, `FastApiVideoAiServiceClient.java`, `FastApiAudioAiServiceClient.java`, `FastApiAvSyncServiceClient.java`, `FastApiOcrServiceClient.java`, and `FastApiTranscriptServiceClient.java`).

---

## Target Pipeline Architectures

### Module 05: Image Authenticity Pipeline
```
Spring Boot Backend (FastApiAiServiceClient)
        │  POST /api/v1/analyze/image (multipart/form-data with 'file')
        ▼
FastAPI Module 05 Router & Service
        │
        ├── 1. In-Memory Validation & Loading (image_utils.py)
        ├── 2. Image Preprocessing (224×224 ImageNet normalization)
        ├── 3. Error Level Analysis (ela.py: JPEG recompression residual heatmap)
        ├── 4. Noise Variance Analysis (noise.py: Laplacian spatial variance)
        ├── 5. 2-D FFT Spectral Analysis (noise.py: high-frequency energy ratio)
        ├── 6. Copy-Move & Splicing (copy_move.py: ORB + Lowe's ratio + RANSAC)
        ├── 7. Authenticity Classifier (classifier.py: timm EfficientNet-B0)
        ├── 8. Grad-CAM Explainability (gradcam.py: Conv2d attention hooks)
        └── 9. Base64 Artifact Encoding (service.py: PNG Base64 strings)
        ▼
Spring Boot Backend (FastApiImageAnalysisResponse DTO)
```

### Module 06: Video Deepfake Detection Pipeline
```
Spring Boot Backend (FastApiVideoAiServiceClient)
        │  POST /api/v1/analyze/video (multipart/form-data with 'file')
        ▼
FastAPI Module 06 Router & Service
        │
        ├── 1. Ingestion & Validation (ingestion.py: safe temp file, metadata probe)
        ├── 2. Deterministic Frame Sampling (ingestion.py: uniform temporal indexation)
        ├── 3. Face Detection & Tracking (face_detector.py: OpenCV/RetinaFace, 20% margin)
        ├── 4. Temporal Tensor Preprocessing (preprocessing.py: (1, 3, T, 112, 112))
        ├── 5. 3D-CNN Video Classifier (model.py: torchvision r3d_18 backbone)
        ├── 6. Temporal Inconsistency Analysis (temporal.py: inter-frame warping Δ_temp)
        └── 7. Suspicious Timeline Clustering (temporal.py: contiguous event grouping)
        ▼
Spring Boot Backend (FastApiVideoAnalysisResponse DTO: deepfake_prob, timeline, frame_scores)
```

### Module 07: Audio Authenticity & Voice Forensics Pipeline
```
Spring Boot Backend (FastApiAudioAiServiceClient)
        │  POST /api/v1/analyze/audio (multipart/form-data with 'file')
        ▼
FastAPI Module 07 Router & Service
        │
        ├── 1. Ingestion & Validation (ingestion.py: safe temp file, WAV decoding to 16 kHz mono)
        ├── 2. Acoustic Feature Extraction (features.py: Mel-spectrogram, MFCC, spectral centroid/bandwidth/rolloff/flux/ZCR/RMS)
        ├── 3. Mel-Spectrogram Visualization (features.py: Viridis colormapped Base64 PNG)
        ├── 4. Pitch & Fundamental Frequency Forensics (pitch.py: F0 autocorrelation, pitch variance, unvoiced handling)
        ├── 5. Phase & Spectral Discontinuity (phase_spectral.py: instantaneous phase derivative, vocoder anomaly)
        ├── 6. Splicing Boundary Detection (splicing.py: joint energy flux & phase boundary markers)
        ├── 7. AASIST Classifier Temporal Windows (temporal.py & model.py: PyTorch anti-spoofing evaluation)
        └── 8. Response Packaging (service.py: FastApiAudioAnalysisResponse DTO)
        ▼
Spring Boot Backend (FastApiAudioAnalysisResponse DTO: synthetic_voice_prob, pitch_variance, splice_markers, evidence)
```

### Module 08: Audio-Visual Synchronization Pipeline
```
Spring Boot Backend (FastApiAvSyncServiceClient)
        │  POST /api/v1/analyze/av-sync (multipart/form-data with 'file')
        ▼
FastAPI Module 08 Router & Service
        │
        ├── 1. Ingestion & Multi-Modal Demuxing (ingestion.py: safe temp container, 16 kHz WAV, 25 fps video)
        ├── 2. Primary Face Lip Tracking (lip_tracker.py: OpenCV face detection, 96×96 mouth ROI, MAR & visual flux)
        ├── 3. Speech Envelope & Mel-Spectrogram (correlator.py: RMS + spectral flux, 80-band log-Mel)
        ├── 4. Envelope Cross-Correlation (correlator.py: ±500 ms lag scan, peak offset & correlation score)
        ├── 5. Dual-Stream SyncNet Evaluation (syncnet.py: 5-frame mouth visemes & 20-frame log-Mel → 128-d embeddings)
        ├── 6. Anomaly Segmentation & Scoring (alignment.py: DUBBING, MUTED_SPEECH, DESYNC markers & drift analysis)
        └── 7. Response Packaging (service.py: FastApiAvSyncAnalysisResponse DTO)
        ▼
Spring Boot Backend (FastApiAvSyncAnalysisResponse DTO: sync_score, offset_ms, sync_status, mismatch_segments)
```

### Module 09: OCR & Visual Text Extraction Pipeline
```
Spring Boot Backend (FastApiOcrServiceClient)
        │  POST /api/v1/analyze/ocr (multipart/form-data with 'file' - Image or Video)
        ▼
FastAPI Module 09 Router & Service
        │
        ├── 1. Ingestion & Modality Routing (service.py: header inspection for IMAGE vs VIDEO)
        │
        ├── [IF IMAGE]
        │   ├── 2a. OpenCV Preprocessing (preprocessor.py: CLAHE, bilateral filter, deskewing, dual binarization)
        │   ├── 2b. OCR Engine Execution (engine.py: Tesseract / EasyOCR / OpenCV morphological fallback)
        │   └── 2c. Bounding Box Rescaling (engine.py: normalized [0,1] & original pixel coordinates)
        │
        ├── [IF VIDEO]
        │   ├── 3a. Deterministic Keyframe Sampling (video_pipeline.py: uniform 1.0s interval up to 30 frames)
        │   ├── 3b. Keyframe Preprocessing & OCR (video_pipeline.py: per-frame text & bounding boxes)
        │   └── 3c. Temporal Chyron Deduplication (video_pipeline.py: merge persistent banners across consecutive frames)
        │
        ├── 4. Language Detection & Normalization (engine.py: engine tag or script heuristic)
        └── 5. Response Packaging (service.py: FastApiOcrResponse DTO)
        ▼
Spring Boot Backend (FastApiOcrResponse DTO: extracted_text, language, confidence_score, regions, evidence)
```

### Module 10: Speech-to-Text & Transcript Extraction Pipeline
```
Spring Boot Backend (FastApiTranscriptServiceClient)
        │  POST /api/v1/analyze/speech-to-text (multipart/form-data with 'file' - Audio or Video)
        ▼
FastAPI Module 10 Router & Service
        │
        ├── 1. Ingestion & Container Validation (preprocessor.py: media format verification, reject images)
        ├── 2. Audio Demuxing & Normalization (preprocessor.py: ffmpeg/afconvert/WAV to 16 kHz mono 16-bit PCM)
        ├── 3. Duration & Acoustic Silence Gating (preprocessor.py: <= 600s limit, RMS energy evaluation)
        │
        ├── [IF SILENT]
        │   └── 4a. Bypass ASR (engine.py: empty transcript, 0 segments, 1.0 confidence, is_silent=True)
        │
        ├── [IF SPEECH DETECTED]
        │   └── 4b. Faster-Whisper / Acoustic ASR Inference (engine.py: CTranslate2 int8, word_timestamps=True)
        │
        ├── 5. Segment & Word Timing Normalization (engine.py: start <= word.start <= word.end <= end)
        └── 6. Response Packaging (service.py: FastApiTranscriptResponse DTO)
        ▼
Spring Boot Backend (FastApiTranscriptResponse DTO: full_text, language, confidence_score, segments, words, evidence)
```

---

## Tech Stack

| Component | Technology | Blueprint Reference |
|---|---|---|
| Language | Python 3.11+ (tested on 3.12) | Section E |
| Microservice Framework | FastAPI + Uvicorn | Section E |
| Deep Learning Framework | PyTorch 2.2 | Section E |
| Vision & Audio Architectures | `timm` (`efficientnet_b0`), `torchvision.models.video` (`r3d_18`), `AASISTAudioClassifier`, `SyncNetDualStream` | Section E |
| OCR Engines & Text Extraction | Tesseract (`pytesseract`), EasyOCR, OpenCV Morphological Extraction | Blueprint M09 |
| Speech-to-Text (ASR) Engine | Faster-Whisper (`Systran/faster-whisper-tiny`), CTranslate2 `int8`, Acoustic Energy ASR | Blueprint M10 |
| Signal & Media Processing | SciPy (`signal`, `fft`, `io.wavfile`), OpenCV (`cv2`), Pillow (`PIL`) | Section E |
| Audio Feature Extraction | Mel-spectrogram, MFCC (DCT-II), Spectral Moments, Autocorrelation F0 | Section D, E |
| Testing Suite | pytest (251 passing tests) | Section I |

---

## Project Structure

```
ai-ml/
├── main.py                              # FastAPI entry point & router registration (M05–M10)
├── train.py                             # Multi-modal CLI training entrypoint (Image & Audio)
├── requirements.txt                     # Pinned project dependencies (zero unapproved additions)
├── .env.example                         # Environment configuration template
├── conftest.py                          # pytest sys.path configuration
│
├── config/
│   └── settings.py                      # Pydantic BaseSettings (Image, Video, Audio, AV Sync, OCR & STT settings)
│
├── schemas/
│   ├── image_analysis.py                # Pydantic models for Module 05 (BackendImageAnalysisResponse)
│   ├── video_analysis.py                # Pydantic models for Module 06 (BackendVideoAnalysisResponse)
│   ├── audio_analysis.py                # Pydantic models for Module 07 (BackendAudioAnalysisResponse, AudioEvidence)
│   ├── av_sync.py                       # Pydantic models for Module 08 (BackendAvSyncAnalysisResponse, AvSyncEvidence)
│   ├── ocr.py                           # Pydantic models for Module 09 (BackendOcrResponse, OcrEvidence, OcrTextRegion)
│   └── transcript.py                    # Pydantic models for Module 10 (BackendTranscriptResponse, TranscriptSegment, TranscriptWord)
│
├── utils/
│   ├── image_utils.py                   # Image loaders, preprocessing, Base64 PNG encoders
│   └── storage.py                       # File artifact storage utilities
│
├── services/
│   ├── image_analysis/                  # Module 05: Image Authenticity Analysis
│   │   ├── classifier.py                # EfficientNet-B0 inference & checkpoint loader
│   │   ├── copy_move.py                 # ORB + RANSAC copy-move & splicing forensic engine
│   │   ├── ela.py                       # Error Level Analysis (ELA) heatmap generator
│   │   ├── gradcam.py                   # Grad-CAM spatial attention exporter
│   │   ├── noise.py                     # Laplacian noise variance & 2-D FFT spectral analysis
│   │   ├── service.py                   # Module 05 orchestrator (byte & path execution)
│   │   ├── trainer.py                   # Reproducible classifier training pipeline
│   │   └── router.py                    # Module 05 FastAPI routes (/api/v1/analyze/image)
│   │
│   ├── video_analysis/                  # Module 06: Video Deepfake Detection
│   │   ├── __init__.py                  # Module 06 package marker
│   │   ├── face_detector.py             # OpenCV/RetinaFace face detection & bounding box tracking
│   │   ├── ingestion.py                 # Video validation, metadata probing & deterministic sampling
│   │   ├── model.py                     # 3D-CNN (r3d_18) video deepfake model wrapper
│   │   ├── preprocessing.py             # Face crop normalization & 5-D temporal tensor formatting
│   │   ├── temporal.py                  # Temporal discrepancy analysis & timeline clustering
│   │   ├── service.py                   # Module 06 orchestrator (analyze_video_bytes)
│   │   └── router.py                    # Module 06 FastAPI routes (/api/v1/analyze/video)
│   │
│   ├── audio_analysis/                  # Module 07: Audio Authenticity & Voice Forensics
│   │   ├── __init__.py                  # Module 07 package marker
│   │   ├── ingestion.py                 # Audio decoding, validation, mono downmixing & 16kHz resampling
│   │   ├── features.py                  # Mel-spectrogram, MFCC, spectral moments & Base64 PNG generator
│   │   ├── pitch.py                     # F0 pitch contour tracking & pitch variance forensics
│   │   ├── phase_spectral.py            # Phase trajectory discontinuity & vocoder anomaly forensics
│   │   ├── splicing.py                  # Audio splice boundary detection & timestamp marking
│   │   ├── model.py                     # AASIST PyTorch spectro-temporal anti-spoofing classifier
│   │   ├── temporal.py                  # Temporal windowing evaluation & aggregate scoring
│   │   ├── trainer.py                   # Audio classifier training pipeline & EER metric calculation
│   │   ├── service.py                   # Module 07 orchestrator (analyze_audio_bytes)
│   │   └── router.py                    # Module 07 FastAPI routes (/api/v1/analyze/audio)
│   │
│   ├── av_sync/                         # Module 08: AV Synchronization & Lip-Sync Forensics
│   │   ├── __init__.py                  # Module 08 package marker
│   │   ├── ingestion.py                 # Safe container extraction, audio/video demuxing & metadata probe
│   │   ├── lip_tracker.py               # Primary face tracking, mouth ROI extraction, MAR & visual flux
│   │   ├── correlator.py                # Acoustic envelope extraction, log-Mel spectrogram & cross-correlation
│   │   ├── syncnet.py                   # Two-stream SyncNet (visual & audio Conv2D embeddings, metric distance)
│   │   ├── alignment.py                 # Composite sync scoring, status classification & anomaly segmenter
│   │   ├── service.py                   # Module 08 orchestrator (analyze_av_sync_bytes)
│   │   └── router.py                    # Module 08 FastAPI routes (/api/v1/analyze/av-sync)
│   │
│   ├── ocr/                             # Module 09: OCR & Visual Text Extraction
│   │   ├── __init__.py                  # Module 09 package marker
│   │   ├── preprocessor.py              # OpenCV CLAHE, bilateral filtering, deskewing & dual binarization
│   │   ├── engine.py                    # BaseOcrEngine, Tesseract, EasyOCR & OpenCV morphological fallback
│   │   ├── video_pipeline.py            # Deterministic keyframe sampling & chyron temporal deduplication
│   │   ├── service.py                   # Module 09 orchestrator (analyze_ocr_bytes & path execution)
│   │   └── router.py                    # Module 09 FastAPI routes (/api/v1/analyze/ocr)
│   │
│   └── transcript/                      # Module 10: Speech-to-Text & Transcript Extraction
│       ├── __init__.py                  # Module 10 package marker
│       ├── preprocessor.py              # Audio/video demuxing, 16kHz mono normalization, duration limit & silence gating
│       ├── engine.py                    # BaseSpeechTranscriber, FasterWhisperTranscriber & AcousticEnergyTranscriber fallback
│       ├── service.py                   # Module 10 orchestrator (analyze_speech_to_text_bytes & path execution)
│       └── router.py                    # Module 10 FastAPI routes (/api/v1/analyze/speech-to-text)
│
└── tests/
    ├── test_backend_contract.py         # M05, M07, M08, M09 & M10 multipart API contract tests
    ├── test_classifier.py               # M05 model architecture & inference tests
    ├── test_copy_move.py                # M05 copy-move & splicing forensic tests
    ├── test_ela.py                      # M05 ELA heatmap & residual tests
    ├── test_gradcam.py                  # M05 Grad-CAM attention shape & hook tests
    ├── test_image_router.py             # M05 legacy JSON endpoint & health probe tests
    ├── test_noise.py                    # M05 noise variance & FFT ratio tests
    ├── test_trainer_and_checkpoint.py   # M05 classifier fine-tuning & checkpoint tests
    ├── test_video_face_detector.py      # M06 face detection & tracking tests
    ├── test_video_ingestion.py          # M06 video sampling tests
    ├── test_video_model.py              # M06 3D-CNN model tests
    ├── test_video_preprocessing.py      # M06 temporal clip tensor tests
    ├── test_video_router.py             # M06 video API endpoint tests
    ├── test_video_temporal.py           # M06 temporal inconsistency tests
    ├── test_audio_ingestion.py          # M07 audio decoding & resampling tests
    ├── test_audio_features.py           # M07 Mel-spectrogram & acoustic moments tests
    ├── test_audio_pitch.py              # M07 pitch tracking & variance tests
    ├── test_audio_phase_spectral.py     # M07 phase discontinuity & spectral tests
    ├── test_audio_splicing.py           # M07 splice boundary detection tests
    ├── test_audio_model.py              # M07 AASIST model & checkpoint tests
    ├── test_audio_router.py             # M07 audio API endpoint & contract tests
    ├── test_audio_trainer.py            # M07 audio training pipeline & EER tests
    ├── test_av_sync_ingestion.py        # M08 video/audio container ingestion & demuxing tests
    ├── test_av_sync_lip_tracker.py      # M08 mouth ROI, MAR & visual flux tests
    ├── test_av_sync_correlator.py       # M08 envelope extraction & cross-correlation tests
    ├── test_av_sync_syncnet.py          # M08 SyncNet dual-stream embedding tests
    ├── test_av_sync_alignment.py        # M08 composite sync scoring & anomaly segmentation tests
    ├── test_av_sync_router.py           # M08 AV sync FastAPI endpoint tests
    ├── test_ocr_preprocessor.py         # M09 OpenCV preprocessing & deskewing tests
    ├── test_ocr_engine.py               # M09 OCR engine abstraction & morphological fallback tests
    ├── test_ocr_video_pipeline.py       # M09 video keyframe sampling & chyron deduplication tests
    ├── test_ocr_router.py               # M09 OCR API endpoint & contract tests
    ├── test_transcript_preprocessor.py  # M10 audio demuxing, silence detection & duration limit tests
    ├── test_transcript_engine.py        # M10 ASR engine abstraction & word timestamp alignment tests
    ├── test_transcript_service.py       # M10 speech-to-text service orchestration tests
    └── test_transcript_router.py        # M10 speech-to-text FastAPI endpoint tests
```

---

## API Contract Specifications

### Module 05 — Image Authenticity: `POST /api/v1/analyze/image`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (Binary image file)
- **Response:** `BackendImageAnalysisResponse`
  - `ai_prob`: Float $[0.0, 1.0]$
  - `manipulation_prob`: Float $[0.0, 1.0]$
  - `noise_variance`: Non-negative float
  - `fft_anomaly_score`: Float $[0.0, 1.0]$
  - `copy_move_detected`: Boolean
  - `splicing_detected`: Boolean
  - `model_name`: String
  - `model_version`: String
  - `ela_heatmap_base64`: Base64 PNG string
  - `gradcam_heatmap_base64`: Base64 PNG string or null
  - `evidence`: Detailed sub-metrics dictionary
  - `status`: `"COMPLETED"`

### Module 06 — Video Deepfake Detection: `POST /api/v1/analyze/video`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (Binary video file: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`)
- **Response:** `BackendVideoAnalysisResponse`
  ```json
  {
    "deepfake_prob": 0.8420,
    "face_count": 1,
    "total_frames_sampled": 16,
    "suspicious_timestamps": [
      {
        "timestamp_seconds": 2.50,
        "frame_index": 5,
        "score": 0.8920,
        "reason": "Facial synthesis anomaly & boundary discontinuity (score: 0.89)"
      }
    ],
    "frame_scores": [
      {
        "frame_index": 0,
        "timestamp_seconds": 0.0,
        "deepfake_score": 0.2100,
        "temporal_inconsistency": 0.0,
        "faces_detected": 1,
        "is_suspicious": false
      },
      {
        "frame_index": 5,
        "timestamp_seconds": 2.50,
        "deepfake_score": 0.8920,
        "temporal_inconsistency": 0.5210,
        "faces_detected": 1,
        "is_suspicious": true
      }
    ],
    "model_name": "TruthLens-3DCNN-VideoClassifier",
    "model_version": "0.1.0-dev",
    "evidence": {
      "face_count": 1,
      "total_frames_sampled": 16,
      "duration_seconds": 8.0,
      "frame_scores": [...],
      "suspicious_timestamps": [...],
      "details": {
        "fps": 25.0,
        "resolution": [1280, 720],
        "total_video_frames": 200,
        "base_clip_score": 0.7810,
        "processing_time_ms": 1420
      }
    },
    "status": "COMPLETED"
  }
  ```

### Module 07 — Audio Authenticity & Voice Forensics: `POST /api/v1/analyze/audio`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (Binary audio file: `.wav`, `.mp3`, `.flac`, etc.)
- **Response:** `BackendAudioAnalysisResponse` (matching Spring Boot `FastApiAudioAnalysisResponse.java` exactly)
  ```json
  {
    "synthetic_voice_prob": 0.5132,
    "spectrogram_url": "/storage/spectrogram/3f9...png",
    "spectrogram_base64": "iVBORw0KGgoAAAANSUhEUgAAAEwAAA...",
    "pitch_variance": 0.1383,
    "splice_markers": [
      {
        "timestamp_seconds": 1.01,
        "score": 0.7123,
        "reason": "Abrupt acoustic transition at 1.01s (score: 0.71) with joint spectral flux and phase discontinuity."
      }
    ],
    "model_name": "TruthLens-AASIST-AudioClassifier",
    "model_version": "0.1.0-dev-untrained",
    "evidence": {
      "duration_seconds": 2.0,
      "pitch_mean": 303.24,
      "pitch_variance": 0.1383,
      "spectral_centroid_mean": 450.12,
      "spectral_bandwidth_mean": 68.45,
      "spectral_rolloff_mean": 462.10,
      "zero_crossing_rate_mean": 0.0542,
      "phase_discontinuity_score": 0.3072,
      "splice_markers": [...],
      "details": {
        "channels": 1,
        "original_sample_rate": 16000,
        "processed_sample_rate": 16000,
        "voiced_fraction": 0.8520,
        "spectral_anomaly_score": 0.3241,
        "high_freq_attenuation_ratio": 0.0120,
        "processing_time_ms": 45,
        "temporal": {
          "window_count": 1,
          "max_window_synthetic_prob": 0.5132
        }
      }
    },
    "status": "COMPLETED"
  }
  ```

### Module 08 — Audio-Visual Synchronization: `POST /api/v1/analyze/av-sync`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (Binary video file: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`)
- **Response:** `BackendAvSyncAnalysisResponse` (matching Spring Boot `FastApiAvSyncAnalysisResponse.java` exactly)
  ```json
  {
    "sync_score": 0.8845,
    "offset_ms": -38.5,
    "sync_status": "ALIGNED",
    "confidence_score": 0.9120,
    "temporal_drift_score": 0.0420,
    "mismatch_segments": [],
    "model_name": "TruthLens-SyncNet-LipSyncClassifier",
    "model_version": "0.1.0-dev",
    "evidence": {
      "audio_duration_seconds": 4.5,
      "video_duration_seconds": 4.5,
      "video_fps": 25.0,
      "cross_correlation_peak": 0.8250,
      "syncnet_min_distance": 0.3450,
      "faces_tracked_fraction": 1.0,
      "mismatch_segments": []
    },
    "status": "COMPLETED"
  }
  ```

### Module 09 — OCR & Visual Text Extraction: `POST /api/v1/analyze/ocr`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (Binary image or video file)
- **Response:** `BackendOcrResponse` (matching Spring Boot `FastApiOcrResponse.java` exactly)
  ```json
  {
    "extracted_text": "BREAKING NEWS SPECIAL REPORT",
    "language": "en",
    "confidence_score": 0.8750,
    "regions_count": 2,
    "regions": [
      {
        "text": "BREAKING NEWS",
        "confidence": 0.9200,
        "bounding_box": {
          "x": 45,
          "y": 620,
          "width": 380,
          "height": 45,
          "normalized_x": 0.035,
          "normalized_y": 0.861,
          "normalized_width": 0.297,
          "normalized_height": 0.063
        },
        "frame_index": 0,
        "timestamp_seconds": 0.0
      },
      {
        "text": "SPECIAL REPORT",
        "confidence": 0.8300,
        "bounding_box": {
          "x": 440,
          "y": 620,
          "width": 350,
          "height": 45,
          "normalized_x": 0.344,
          "normalized_y": 0.861,
          "normalized_width": 0.273,
          "normalized_height": 0.063
        },
        "frame_index": 0,
        "timestamp_seconds": 0.0
      }
    ],
    "evidence": {
      "engine": "OpenCV-Morphological-Fallback",
      "preprocessed": true,
      "total_frames_sampled": 1,
      "language_detected": "en",
      "text_density_score": 0.1240,
      "details": {
        "media_type": "IMAGE",
        "original_resolution": [1280, 720]
      }
    },
    "status": "COMPLETED"
  }
  ```

### Module 10 — Speech-to-Text & Transcript Extraction: `POST /api/v1/analyze/speech-to-text`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (Binary audio or video file: `.wav`, `.mp3`, `.mp4`, `.mov`, `.m4a`, etc.)
- **Response:** `BackendTranscriptResponse` (matching Spring Boot `FastApiTranscriptResponse.java` exactly)
  ```json
  {
    "full_text": "Truth and speech verification system is now active.",
    "language": "en",
    "confidence_score": 0.8850,
    "duration_seconds": 3.924,
    "segments_count": 1,
    "words_count": 8,
    "segments": [
      {
        "id": 0,
        "seek": 0,
        "start": 0.0,
        "end": 3.42,
        "text": "Truth and speech verification system is now active.",
        "tokens": [1, 2, 3, 4, 5, 6, 7, 8],
        "temperature": 0.0,
        "avg_logprob": -0.122,
        "compression_ratio": 1.0,
        "no_speech_prob": 0.01,
        "confidence": 0.8850,
        "words": [
          {"word": "Truth", "start": 0.0, "end": 0.46, "probability": 0.94},
          {"word": "and", "start": 0.46, "end": 0.62, "probability": 0.92},
          {"word": "speech", "start": 0.62, "end": 1.08, "probability": 0.90},
          {"word": "verification", "start": 1.08, "end": 1.86, "probability": 0.89},
          {"word": "system", "start": 1.86, "end": 2.42, "probability": 0.88},
          {"word": "is", "start": 2.42, "end": 2.62, "probability": 0.87},
          {"word": "now", "start": 2.62, "end": 2.88, "probability": 0.86},
          {"word": "active.", "start": 2.88, "end": 3.42, "probability": 0.85}
        ]
      }
    ],
    "evidence": {
      "model_name": "Faster-Whisper",
      "model_size": "tiny",
      "compute_type": "int8",
      "device": "cpu",
      "detected_language": "en",
      "language_probability": 0.98,
      "duration_seconds": 3.924,
      "audio_sample_rate": 16000,
      "media_type": "AUDIO",
      "details": {
        "engine": "Faster-Whisper",
        "beam_size": 5,
        "word_timestamps": true
      }
    },
    "status": "COMPLETED",
    "error_message": null
  }
  ```

### Health & Diagnostic Endpoints
- `GET /`: Returns service version and registered modules (`["05-image-authenticity", "06-video-deepfake", "07-audio-authenticity", "08-av-sync", "09-ocr-text-extraction", "10-speech-to-text"]`).
- `GET /health`: Global platform health probe across all sub-analyzers.
- `GET /api/image/health`: Module 05 liveness probe.
- `GET /api/video/health`: Module 06 liveness probe.
- `GET /api/audio/health`: Module 07 liveness probe & model metadata.
- `GET /api/av-sync/health`: Module 08 liveness probe & SyncNet metadata.
- `GET /api/ocr/health`: Module 09 liveness probe & OCR engine metadata.
- `GET /api/stt/health`: Module 10 liveness probe & Faster-Whisper capability probe.
- `GET /api/transcript/health`: Module 10 alias diagnostic probe.

---

## Module 06 Video Forensic Engines

### 1. Ingestion & Deterministic Sampling (`ingestion.py`)
- Reads raw video bytes into a secured temp file with auto-cleanup.
- Probes container metadata via OpenCV (`CAP_PROP_FRAME_COUNT`, `CAP_PROP_FPS`, dimensions, duration).
- Samples up to `settings.video_max_sampled_frames` (default: 16) deterministically spaced across the video duration using `np.linspace(0, total_frames - 1, max_frames)`.

### 2. Facial Detection & Bounding Box Tracking (`face_detector.py`)
- Detects faces in sampled frames.
- Expands bounding boxes by 20% margin to ensure jawline, hairline, and blend boundaries are preserved.
- When multiple faces are present, selects the primary face by bounding box area and temporal spatial tracking.
- If no face is detected in a frame, falls back gracefully to a centered crop with an explanatory fallback flag.
- Pluggable architecture supports `OpenCVFaceDetector` (standard) and `RetinaFaceDetector` (blueprint interface).

### 3. Preprocessing & Temporal Tensor Assembly (`preprocessing.py`)
- Normalizes face crops to standard spatial dimension ($112 \times 112$) using ImageNet mean/standard deviation.
- Assembles temporal sequences into a 5-D tensor $(B=1, C=3, T=16, H=112, W=112)$ ready for 3D-CNN spatiotemporal convolution.

### 4. 3D-CNN Video Classifier (`model.py`)
- Backbone: `torchvision.models.video.r3d_18` (ResNet3D-18) with a binary classification head (`Linear` $\to$ `Sigmoid`).
- Inference runs in `torch.no_grad()` and `eval()` mode.
- Configurable via `VIDEO_CLASSIFIER_CHECKPOINT` and `REQUIRE_VIDEO_CHECKPOINT`. When production enforcement is enabled (`REQUIRE_VIDEO_CHECKPOINT=True`), missing weights fail fast rather than returning pseudo-predictions.

### 5. Temporal Inconsistency & Suspicious Timeline (`temporal.py`)
- Evaluates inter-frame pixel and structural discrepancy $\Delta_{\text{temp}} = |I_{t} - I_{t-1}|$ between consecutive face crops.
- Calculates per-frame deepfake scores blending the 3D-CNN clip score ($70\%$) with temporal jitter ($30\%$).
- Aggregates overall video probability using top-35% percentile pooling.
- Consolidates contiguous anomalous frames into distinct timeline event markers to prevent cluttering investigator interfaces.

---

## Module 07 Audio Forensic Engines

### 1. Ingestion & Preprocessing (`ingestion.py`)
- Reads raw binary audio into a secured temp file with guaranteed cleanup via `temp_audio_file`.
- Decodes WAV formats (8/16/24/32-bit PCM, 32/64-bit float) using `scipy.io.wavfile` and Python stdlib `wave`.
- Automatically downmixes multi-channel audio to mono and resamples deterministically to 16 kHz using `scipy.signal.resample`.
- Normalizes waveform amplitudes to $[-1.0, 1.0]$ and sanitizes any non-finite values.

### 2. Acoustic Feature Extraction & Mel-Spectrogram (`features.py`)
- Computes STFT (Hann window, $N_{\text{fft}}=1024$, hop length $=256$) and applies an 80-band triangular Mel filterbank.
- Generates log-Mel energy spectrogram ($10 \log_{10}(\max(M, 10^{-10}))$) and 20 MFCC coefficients via orthonormal Type-II DCT (`scipy.fft.dct`).
- Extracts frame-level and global acoustic moments:
  - Spectral centroid (center of mass)
  - Spectral bandwidth (2nd central moment)
  - Spectral roll-off (85% energy threshold)
  - Zero-crossing rate (ZCR)
  - RMS energy
  - Spectral flux (frame-to-frame Euclidean distance)
- Renders normalized, colormapped (Viridis) Mel-spectrograms to Base64-encoded PNG strings using OpenCV and Pillow.

### 3. Pitch & Acoustic Variance Forensics (`pitch.py`)
- Tracks fundamental frequency (F0) across voiced segments using normalized autocorrelation analysis in the range $[60\text{ Hz}, 500\text{ Hz}]$.
- Uses sub-sample parabolic peak interpolation for frequency accuracy.
- Robustly identifies silent/unvoiced frames and returns `pitch_variance = 0.0` when fewer than two voiced frames exist.
- Pitch variance serves as an explainable evidence metric for detecting monotonic synthetic speech or exaggerated pitch jitter.

### 4. Phase Discontinuity & Vocoder Forensics (`phase_spectral.py`)
- Analyzes instantaneous phase deviation across consecutive STFT frames:
  $D(k, t) = \text{angle}(e^{i(\phi(k, t) - \phi(k, t-1) - \omega_k \Delta t)})$.
- Computes a magnitude-weighted phase discontinuity score in $[0.0, 1.0]$, sensitive to neural vocoder (HiFi-GAN, WaveGlow) phase reconstruction artifacts.
- Measures high-frequency to mid-frequency attenuation ratio to identify characteristic sample-rate cutoffs in synthetic speech.

### 5. Audio Splice Boundary Detection (`splicing.py`)
- Analyzes joint discontinuities in relative RMS step change ($|\Delta\text{RMS}| / \text{RMS}$), spectral flux, and frame phase deviations.
- Applies anomaly floor gating to prevent false positives on smooth continuous speech.
- Uses `scipy.signal.find_peaks` with non-maximum suppression (default: 0.35s separation) to produce timestamped `AudioSpliceMarker`s.

### 6. AASIST Synthetic Voice Classifier (`model.py` & `temporal.py`)
- Implements an AASIST-inspired Spectro-Temporal Neural Network (`AASISTAudioClassifier`):
  - 2-D Convolutional Spectro-Temporal Front-End (3 Conv2D blocks with BatchNorm and MaxPool).
  - Bi-directional GRU (2 layers, 128 hidden) for temporal context aggregation.
  - Binary classification head (`Linear` $\to$ `BatchNorm` $\to$ `ReLU` $\to$ `Dropout` $\to$ `Linear(2)`).
- Slides 2.0s windows with 1.0s hop across the audio track.
- Aggregates window scores using 85th percentile pooling ($70\%$) combined with mean score ($30\%$) to detect localized voice cloning within longer recordings.
---

## Module 08 Audio-Visual Synchronization & Lip-Sync Forensics

### 1. Media Ingestion & Multi-Modal Demuxing (`ingestion.py`)
- Reads raw multi-modal video/audio payload into a secured temporary container with guaranteed lifecycle cleanup via `temp_video_file`.
- Samples video frames deterministically at `settings.av_sync_fps` (default: 25.0 fps) via OpenCV `VideoCapture`.
- Extracts audio stream downmixed to 16 kHz mono float32 waveform using system audio conversion (`/usr/bin/afconvert` or `ffmpeg`) or direct audio parsing (`load_and_preprocess_audio`).
- Extracts container-level forensic metadata: video duration, audio duration, native fps, frame counts, sample rate.
- Gracefully handles edge cases: video without audio, audio without video, corrupted containers, zero-byte uploads.

### 2. Primary Speaker Lip Tracking & Mouth ROI Normalization (`lip_tracker.py`)
- Reuses Module 06 facial detection and temporal tracking to identify the primary speaking face across frames.
- Deterministically crops mouth region using facial bounding box geometry (centered horizontally in lower third of face: $0.52 \times W$, $0.32 \times H$).
- Resizes mouth visemes to standard $96 \times 96$ grayscale crops (`mouth_crop_size`).
- Computes frame-level Mouth Aspect Ratio (MAR) combining spatial height-to-width ratio with Otsu-thresholded oral cavity opening ratio.
- Evaluates inter-frame pixel motion $\Delta M_t = \frac{1}{HW} \sum |C_t - C_{t-1}|$ between consecutive normalized mouth crops.
- Fuses first-order MAR velocity ($60\%$) with visual motion energy ($40\%$) to generate a continuous 1D normalized lip activity timeline in $[0.0, 1.0]$.
- Implements deterministic center-bottom fallback when facial occlusion occurs, preserving frame counts and timestamps without crashing.

### 3. Acoustic Speech Envelope & Spectrogram Analysis (`correlator.py`)
- Derives continuous vocal activity envelope from audio waveform by fusing frame-wise RMS energy ($70\%$) with STFT spectral flux ($30\%$).
- Resamples acoustic activity envelope onto exact video frame timestamps using piecewise linear interpolation (`np.interp`).
- Reuses Module 07 acoustic feature generator to produce an 80-band triangular log-Mel spectrogram ($N_{\text{fft}}=1024$, hop length $=256$).

### 4. Cross-Correlation Temporal Alignment (`correlator.py`)
- Computes normalized cross-correlation between audio activity envelope and visual lip activity timeline across a configurable temporal lag range ($-500\text{ ms}$ to $+500\text{ ms}$).
- Determines optimal alignment offset $\tau_{\text{corr}}$ and peak correlation coefficient $r_{\text{peak}} \in [-1.0, 1.0]$.
- Strictly follows Spring Boot contract sign convention:
  - **Positive offset (+ms):** Audio lags video (speech heard after mouth movement is visible).
  - **Negative offset (-ms):** Audio leads video (speech heard before mouth movement begins).
  - **Near-zero offset ($\pm 40\text{ ms}$):** Synchronized.
- Calculates correlation confidence based on peak prominence and multi-modal energy factors.

### 5. SyncNet Dual-Stream Metric Architecture (`syncnet.py`)
- Implements two-stream deep neural network projecting visual mouth dynamics and acoustic speech representations into a shared 128-dimensional Euclidean metric space:
  - `SyncNetVisualNet`: Processes 5 contiguous $96 \times 96$ grayscale mouth frames $(B, 5, 96, 96) \to 4 \times \text{Conv2D} \to \text{Linear} \to L_2\text{-normalized } 128\text{-d vector}$.
  - `SyncNetAudioNet`: Processes 20-frame log-Mel spectrogram chunks $(B, 1, 80, 20) \to 4 \times \text{Conv2D} \to \text{Linear} \to L_2\text{-normalized } 128\text{-d vector}$.
  - Computes Euclidean distance $d(v, a) = \|v - a\|_2 \in [0.0, 2.0]$.
- Evaluates distance across a sliding shift range ($\pm 12$ frames, $\pm 480\text{ ms}$) to identify the minimum distance trough and metric confidence.
- Supports strict checkpoint enforcement (`REQUIRE_AV_SYNC_CHECKPOINT=True`) and deterministic development initialization (`0.1.0-dev`).

### 6. Forensic Scoring & Localized Mismatch Scanner (`alignment.py`)
- Combines envelope cross-correlation and SyncNet metric distance into a composite synchronization score $S_{\text{sync}} \in [0.0, 1.0]$:
  - Offset tolerance: broadcast standard $\le 60\text{ ms}$ has zero penalty; offsets $> 60\text{ ms}$ incur progressive penalties.
  - Correlation scaling: maps correlation coefficient to forensic confidence.
  - Categorical sync status: `ALIGNED` ($\le 80\text{ ms}$), `SLIGHT_DESYNC` ($80 - 160\text{ ms}$), `SEVERE_DESYNC` ($> 160\text{ ms}$), `NO_FACE_DETECTED`, `NO_AUDIO_TRACK`, `SILENT_OR_INACTIVE`.
- Slides a 1.0s window with 0.5s step to scan and flag localized forensic anomalies:
  - **DUBBING:** Active acoustic speech energy with closed/stationary mouth (dubbing signature).
  - **MUTED_SPEECH:** Active visual mouth opening dynamics without corresponding acoustic speech.
  - **DESYNC:** Localized temporal offset exceeding tolerance.
  - **FACE_OCCLUSION:** Face tracking lost during active speech track.
  - Contiguous segments of matching type are merged into unified forensic intervals.
- Computes temporal drift score by dividing the media into quarters and calculating offset variance over time.

---

## Module 09 OCR & Visual Text Extraction Engines

### 1. Multi-Modal Ingestion & Validation (`service.py`)
- Ingests raw multipart file payloads for both standalone `IMAGE` and `VIDEO` formats.
- Performs untrusted media verification: checks for non-empty bytes, verifies magic byte signatures, decodes image/video headers, and bounds maximum spatial dimensions (`ocr_max_image_dimension`, default: 2048px).
- Returns HTTP 400 with structured detail on empty uploads, corrupted files, or unsupported formats.

### 2. OpenCV Image Preprocessor (`preprocessor.py`)
- Implements the blueprint's OpenCV image preprocessor with deterministic execution:
  - **Downscaling:** Aspect-ratio preserving downscale to $\le 2048\text{px}$ to bound OCR computational latency, returning scaling factors $(s_x, s_y)$.
  - **Grayscale Conversion:** Standard luminance transform.
  - **Noise Reduction:** Bilateral filtering (`d=5, sigmaColor=50, sigmaSpace=50`) that smooths background sensor noise while sharply preserving text character edges.
  - **Contrast Enhancement:** Contrast Limited Adaptive Histogram Equalization (CLAHE, `clipLimit=2.5, tileGridSize=(8, 8)`) to equalize uneven illumination across social media screenshots, posters, and news tickers.
  - **Text Baseline Deskewing:** Analyzes minimum area bounding rectangle angle on Otsu edge contours; applies affine rotation matrix for skew angles within $[-45^\circ, +45^\circ]$.
  - **Dual Binarization:** Fuses Otsu global thresholding with adaptive Gaussian thresholding (`blockSize=15, C=8`) using morphological reconstruction, ensuring robust segmentation under non-uniform illumination.

### 3. Pluggable OCR Engine Abstraction (`engine.py`)
- Defines `BaseOcrEngine` interface with standardized `OcrResult` and `OcrRegion` data structures:
  - `TesseractOcrEngine`: PyTesseract interface extracting word-level bounding boxes, text content, and confidence values.
  - `EasyOcrEngine`: PyTorch-backed CRNN/CRAFT engine extracting polygon bounding boxes, text sequences, and detection confidences.
  - `OpenCVMorphologicalOcrEngine`: High-performance, zero-dependency computer vision fallback. Uses vertical Sobel edge gradients, horizontal morphological closing $(17, 3)$, contour hierarchy extraction, reading-order sorting (top-to-bottom, left-to-right), and local contrast variance confidence scoring.
  - Configurable engine selection (`OCR_ENGINE="auto"` | `"tesseract"` | `"easyocr"` | `"opencv"`).
  - Strict production enforcement: setting `REQUIRE_OCR_ENGINE=True` causes the service to fail fast rather than falling back when external OCR binaries are missing.

### 4. Coordinate Normalization & Rescaling
- Automatically maps bounding box coordinates from preprocessed resolution back to the original image dimensions $(x, y, w, h)$ using scaling factors.
- Provides normalized coordinates $[0.0, 1.0]$ (`normalized_x`, `normalized_y`, `normalized_width`, `normalized_height`) to ensure frontend and downstream consumers can render overlays across any display viewport.

### 5. Video Keyframe Sampling & Temporal Chyron Deduplication (`video_pipeline.py`)
- Samples video keyframes deterministically at uniform intervals (default: 1.0s, up to 30 frames) without decoding every frame unnecessarily.
- Tracks frame index and timestamp (seconds) for every extracted text region.
- **Temporal Chyron Deduplication:** News banners and scrolling tickers frequently persist across consecutive frames. The pipeline tracks bounding boxes across frames using spatial Intersection-over-Union (IoU $\ge 0.5$) and text similarity, consolidating persistent text into continuous intervals with `start_timestamp` and `end_timestamp`.

### 6. Language Detection & Normalization
- Normalizes language identifiers to standard ISO-639-1 two-letter codes (e.g., `"en"`).
- Uses engine-reported language metadata when available; otherwise applies a lightweight Unicode script detector (Latin, Devanagari, Arabic, CJK, Cyrillic) with a fallback to `"unknown"` when confidence is insufficient.

---

## Module 10 Speech-to-Text & Transcript Extraction Engines

### 1. Multi-Modal Ingestion & Audio Demuxing (`preprocessor.py`)
- Accepts audio (`.wav`, `.mp3`, `.flac`, `.aac`, `.ogg`, `.m4a`) and video (`.mp4`, `.mov`, `.avi`, `.webm`, `.mkv`) containers.
- Untrusted media validation: rejects 0-byte uploads, corrupt containers, and image files (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`).
- System-level demuxing: extracts audio streams to 16 kHz mono 16-bit linear PCM WAV using FFmpeg or macOS native `/usr/bin/afconvert`.
- Missing audio detection: detects video containers devoid of audio streams and raises HTTP 400 (`Media contains no decodable audio stream.`).
- Enforces strict 600-second maximum duration limit to protect against denial-of-service workloads.

### 2. Acoustic Energy & Silence Gating (`preprocessor.py`)
- Measures root-mean-square (RMS) acoustic energy $\sqrt{\frac{1}{N}\sum x^2}$ across the waveform.
- Audio tracks with $\text{RMS} < 10^{-4}$ or maximum peak amplitude $< 10^{-4}$ are gated as silence.
- Silent media bypasses ASR inference completely, generating an empty full-text transcript (`""`), zero segments, and $1.0$ confidence score with `is_silent=True` diagnostic evidence to prevent token hallucination.

### 3. ASR Engine Abstraction & Model Lifecycle (`engine.py`)
- Defines `BaseSpeechTranscriber` interface standardizing ASR inputs and `TranscriptResult` outputs:
  - `FasterWhisperTranscriber`: Production ASR engine leveraging Faster-Whisper (`Systran/faster-whisper-tiny`) with CTranslate2 `int8` quantization for fast, deterministic CPU/CUDA inference.
  - `AcousticEnergyTranscriber`: Zero-dependency, deterministic development and testing engine. Uses short-term frame energy analysis to segment voiced regions, producing realistic timestamped tokens and word-level alignments.
  - Thread-safe lazy model loading: uses process-level singleton caching with a mutex lock to avoid re-loading model weights per request.
  - Strict production enforcement: setting `REQUIRE_ASR_MODEL=True` fails fast when Faster-Whisper weights are missing.

### 4. Normalized Segments & Word-Level Timing
- Computes normalized acoustic segment confidence scores via $\min(1.0, \max(0.0, \exp(\text{avg\_logprob})))$.
- Enforces strict monotonic timestamp boundary constraints: $0.0 \le \text{segment.start} \le \text{word.start} \le \text{word.end} \le \text{segment.end}$.
- Preserves word-level token text, start/end timing offsets (seconds), and alignment probabilities.

### 5. Deterministic Full-Text Assembly & Language Detection
- Assembles consolidated `full_text` deterministically from non-empty phrase segments without token repetition or semantic editing.
- Provides ISO-639-1 language identification and classification probabilities, with support for language overrides via `language` form parameters.

---

## Module 11 Text & Claim Analysis Engines

### 1. Text Normalization & Canonicalization (`preprocessor.py`)
- **Unicode Canonicalization:** Applies Unicode NFKC normalization to handle full-width characters, typographic ligatures, and inconsistent encodings.
- **Whitespace & Control Character Cleansing:** Collapses irregular multispaces, tabs, and newlines into single spaces while stripping unsafe ASCII/non-printable control codes.
- **Punctuation & Syntax Preservation:** Strictly preserves commas, quotes, hyphens, periods, question marks, and currency symbols without paraphrase or editorial rewrites.
- **Abbreviation-Aware Sentence Segmentation:** Segments sentences while respecting honorifics, organizational acronyms (e.g. `U.S.`, `E.U.`, `D.C.`), numeric decimals (`3.14`), and lowercase lookaheads, outputting exact character offsets `(start_char, end_char)`.
- **Deterministic Claim Hashing:** Computes collision-resistant 64-character SHA-256 hashes over canonical claim tuples: $\text{SHA-256}(\text{norm\_claim} \parallel \text{norm\_subject} \parallel \text{norm\_action} \parallel \text{norm\_value})$.

### 2. Named Entity Recognition (NER) (`engine.py`)
- Standardizes extracted entity spans into canonical TruthLens categories:
  - `PERSON`: Identifies public officials, executives, and individuals (e.g. "Satya Nadella", "The Prime Minister", "Emmanuel Macron").
  - `ORG`: Identifies governmental bodies, international agencies, and corporations (e.g. "European Union", "NASA", "Federal Reserve", "Microsoft", "Ministry of Health").
  - `LOCATION`: Identifies cities, sovereign nations, geopolitical entities, and planetary bodies (e.g. "Redmond", "Paris", "Brussels", "Washington", "Jupiter").
  - `DATE`: Extracts absolute dates, calendar months, days of week, and temporal anchors (e.g. "January 15", "Monday", "2024", "yesterday").
  - `MONEY`: Identifies monetary figures and currencies (e.g. "$10 billion", "15 billion euro", "€500").
  - `QUANTITY`: Identifies percentages, metrics, headcount, and numerical basis points (e.g. "25%", "25 basis points", "5,000", "10,000 people").
  - `EVENT`: Identifies named legislation, summits, and public accords (e.g. "Artificial Intelligence Act", "Summit", "Olympics").
  - `GENERAL`: Other recognized entity spans.
- Enforces strict character offset alignment: for every recognized entity, `text[start_char:end_char] == entity.text`.

### 3. Sentence Classification & Assertiveness Detection (`engine.py`)
- Categorizes candidate sentences into explainable assertiveness classes:
  - `FACTUAL_CLAIM`: Declarative assertions containing factual predicates (`announced`, `increased`, `reported`, `signed`, `approved`, `launched`, `cut`, `acquired`), named entities, or numerical figures (confidence $\ge 0.70$).
  - `OPINION`: Subjective expressions containing cognitive markers (`i think`, `i believe`, `in my opinion`, `we believe`) or extreme sentiment superlatives (`worst`, `best`, `terrible`, `fantastic`).
  - `QUESTION`: Interrogative structures ending with `?` or beginning with inverted auxiliary starters (`what`, `why`, `how`, `who`, `is it`, `can you`, `why did`).
  - `NON_CLAIM`: Short fragments ($< 3$ words) or imperative commands lacking verifiable assertiveness (`click here`, `subscribe now`, `watch this`).
  - `UNCERTAIN`: Ambiguous or borderline statements.

### 4. Semantic Claim Decomposition & SVO Triples (`engine.py`)
- **Semantic Triple Extraction:** Decomposes declarative assertions into grammatical/semantic triples: `Subject`, `Action` (predicate verb phrase), and `Value` (object, attribute, or complement).
- **Atomic Claim Decomposition:** When complex sentences combine multiple factual assertions via coordinating conjunctions (e.g., *"Company X acquired Company Y in 2024 and employs 10,000 people."*), the engine decomposes the statement into atomic assertions:
  - Claim 1: *"Company X acquired Company Y in 2024"*
  - Claim 2: *"Company X employs 10,000 people."*
- Propagates semantic subjects across coordinate predicates while retaining sentence index provenance.

### 5. Multi-Modal Ingestion & Cross-Source Deduplication (`service.py`)
- **Direct Text:** Evaluates ad-hoc input strings directly.
- **OCR Ingestion (Module 09):** Ingests visual text regions, linking bounding boxes `{"x", "y", "width", "height"}` and frame indices directly to extracted claims.
- **Transcript Ingestion (Module 10):** Ingests timestamped speech segments, preserving start and end timing offsets (`start_time`, `end_time`) on extracted claims.
- **Cross-Source Deduplication:** Eliminates repeated OCR tickers and redundant broadcast phrases, consolidating evidence without discarding spatial or temporal provenance.
- **Factuality Boundary:** Strictly separates NLP extraction confidence from truth factuality. M11 records `factuality_verified = False` and routes truth evaluation to downstream Module 12.

---

## Testing & Verification

The microservice includes **303 comprehensive automated tests** across 43 test suites with 100% pass rate:

```bash
cd ai-ml
./venv/bin/pytest tests/ -v
```

### Complete Test Breakdown:
| Test File | Tests | Coverage |
|---|---|---|
| `test_backend_contract.py` | 30 | M05 Image, M07 Audio, M08 AV Sync, M09 OCR, M10 STT & M11 Claims contracts |
| `test_classifier.py` | 8 | M05 Image classifier architecture & inference |
| `test_copy_move.py` | 6 | M05 ORB self-matching & RANSAC geometric verification |
| `test_ela.py` | 8 | M05 Error Level Analysis heatmap residuals |
| `test_gradcam.py` | 5 | M05 Grad-CAM Conv2d gradient hooks |
| `test_image_router.py` | 16 | M05 Legacy JSON routes & health probes |
| `test_noise.py` | 7 | M05 Laplacian noise variance & FFT spectral analysis |
| `test_trainer_and_checkpoint.py` | 5 | M05 Classifier fine-tuning & checkpoint loading |
| `test_video_face_detector.py` | 7 | M06 Face detection, margin expansion & tracking tests |
| `test_video_ingestion.py` | 7 | M06 Video metadata, validation & frame sampling tests |
| `test_video_model.py` | 7 | M06 3D-CNN model loading, inference & eval mode tests |
| `test_video_preprocessing.py` | 7 | M06 5-D temporal clip tensor formatting tests |
| `test_video_router.py` | 9 | M06 Multipart upload contract & end-to-end pipeline tests |
| `test_video_temporal.py` | 5 | M06 Temporal inconsistency & timeline clustering tests |
| `test_audio_ingestion.py` | 9 | M07 Audio decoding, resampling, mono downmixing & cleanup |
| `test_audio_features.py` | 10 | M07 Mel-spectrogram, MFCC, spectral moments & Base64 PNG |
| `test_audio_pitch.py` | 4 | M07 Pitch tracking, pitch variance & unvoiced handling |
| `test_audio_phase_spectral.py` | 3 | M07 Phase discontinuity & vocoder anomaly scores |
| `test_audio_splicing.py` | 3 | M07 Splice boundary detection & timestamp markers |
| `test_audio_model.py` | 6 | M07 AASIST model & checkpoint tests |
| `test_audio_router.py` | 8 | M07 Audio API endpoint & contract tests |
| `test_audio_trainer.py` | 4 | M07 Audio training pipeline, EER metric & checkpoint save |
| `test_av_sync_ingestion.py` | 5 | M08 Video/audio container ingestion, demuxing & fallback |
| `test_av_sync_lip_tracker.py` | 4 | M08 Primary face mouth ROI, MAR dynamics & motion timeline |
| `test_av_sync_correlator.py` | 7 | M08 Envelope extraction, cross-correlation, positive/negative offsets |
| `test_av_sync_syncnet.py` | 6 | M08 Dual-stream SyncNet embeddings, metric distance & eval |
| `test_av_sync_alignment.py` | 6 | M08 Composite scoring, drift estimation & mismatch scanner |
| `test_av_sync_router.py` | 7 | M08 FastAPI routes, multipart contract & error handling |
| `test_ocr_preprocessor.py` | 4 | M09 OpenCV CLAHE, bilateral filtering, deskewing & dual binarization |
| `test_ocr_engine.py` | 6 | M09 Engine abstraction, OpenCV morphological fallback, factory & strict mode |
| `test_ocr_video_pipeline.py` | 2 | M09 Video keyframe sampling, chyron deduplication & persistent tickers |
| `test_ocr_router.py` | 9 | M09 OCR FastAPI routes, multipart contracts, invalid inputs & error handling |
| `test_transcript_preprocessor.py` | 6 | M10 audio demuxing, silence detection, duration limit & cleanup tests |
| `test_transcript_engine.py` | 5 | M10 ASR engine abstraction, word timestamp alignment & strict mode tests |
| `test_transcript_service.py` | 5 | M10 speech-to-text service orchestration & validation tests |
| `test_transcript_router.py` | 9 | M10 speech-to-text FastAPI endpoint, multipart contracts & health tests |
| `test_claim_preprocessor.py` | 11 | M11 Unicode normalization, whitespace collapsing, abbreviation splitting & SHA-256 hash |
| `test_claim_ner.py` | 7 | M11 Named Entity Recognition across PERSON, ORG, LOC, DATE, MONEY, QUANTITY, EVENT |
| `test_claim_detector.py` | 8 | M11 Sentence classification into FACTUAL_CLAIM, OPINION, QUESTION, and NON_CLAIM |
| `test_claim_decomposer.py` | 5 | M11 SVO semantic decomposition, conjunction splitting & atomic assertion extraction |
| `test_claim_engine.py` | 4 | M11 Engine abstraction, singleton lifecycle, strict mode & sentence clipping |
| `test_claim_service.py` | 6 | M11 Multi-modal ingestion, OCR/transcript provenance & deduplication |
| `test_claim_router.py` | 7 | M11 Primary FastAPI endpoint, module routes, health probes & error handling |
| **Total** | **303** | **100% Passing** |

---

## Running the Service

### Development Mode
```bash
cd ai-ml
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Production Mode
```bash
cd ai-ml
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

API documentation (Swagger UI): `http://localhost:8001/docs`.

---

## Limitations & Project Scope Notes

1. **Facial Dependency (Video & AV Sync):** Video deepfake analysis and AV synchronization require visible human faces. For videos without human faces, M06 evaluates whole-frame center crops and M08 reports `sync_status = "NO_FACE_DETECTED"` with `sync_score = 0.0` and an explainable mismatch segment.
2. **Audio Track Presence (AV Sync & STT):** When a video container does not contain a decodable audio track, M08 returns `sync_status = "NO_AUDIO_TRACK"` with `sync_score = 0.0`, and M10 returns HTTP 400 (`Media contains no decodable audio stream.`) rather than failing silently or crashing.
3. **Production Checkpoint Enforcement:** In accordance with team rules (`AGENTS.md`), large binary weights for deep networks (e.g. trained on FaceForensics++, DFDC, ASVspoof 2021, or LRS2/LRS3) are not committed to Git. The service runs in development mode with explicit untrained architectures (`0.1.0-dev`) or loads custom fine-tuned weights via `CLASSIFIER_CHECKPOINT`, `VIDEO_CLASSIFIER_CHECKPOINT`, `AUDIO_CLASSIFIER_CHECKPOINT`, and `AV_SYNC_CLASSIFIER_CHECKPOINT`. When production enforcement is enabled (`REQUIRE_AV_SYNC_CHECKPOINT=True`), missing weights fail fast rather than returning pseudo-predictions.
4. **Forensic Evidence vs. Definite Manipulation:** Synchronization offsets and localized mismatches are exposed as forensic evidence. Temporal desynchronization may arise from compression artifacts, network jitter, or non-malicious broadcast delays; downstream triage must evaluate AV sync evidence alongside M05, M06, and M07 findings.
5. **Cross-Module Scope:** Modules 12–14 (Fact Verification, Vector Index Search, and Cross-Modal Reasoning) are distinct downstream modules and are not implemented here. No backend Java or frontend React files were modified.
6. **OCR Engine Deployment & Fallback:** The service automatically detects whether system Tesseract (`tesseract`) or EasyOCR is present. In environments without external OCR binaries, the pipeline engages the zero-dependency OpenCV morphological text engine. In production, setting `REQUIRE_OCR_ENGINE=True` enforces that a full OCR engine is present.
7. **Downstream M11 Claim Separation:** M09 extracts and structures visual text, bounding boxes, and temporal chyrons. Downstream claim decomposition, entity extraction, and truth verification are strictly reserved for Module 11.
8. **ASR Model Deployment & CTranslate2 Quantization:** The microservice integrates Faster-Whisper (`Systran/faster-whisper-tiny` with `int8` quantization). In headless development or test environments where external weights are not pre-downloaded, the pipeline engages the deterministic `AcousticEnergyTranscriber` fallback to preserve timing offsets and test isolation. Setting `REQUIRE_ASR_MODEL=True` strictly enforces model availability.
9. **NLP Engine Deployment & Fallback:** Module 11 integrates an extensible engine architecture supporting spaCy (`en_core_web_sm`) or HuggingFace pipelines. In test or development environments where spaCy model weights are not pre-installed, the pipeline engages the deterministic `RuleBasedClaimEngine` fallback, providing rule-based NER, sentence segmentation, SVO triples, and conjunction decomposition. Setting `REQUIRE_NLP_MODEL=True` enforces strict model availability.
10. **Factuality & Truth Verification Separation:** M11 extracts, structures, and classifies verifiable statements and assigns extraction confidence scores. It explicitly does not evaluate the truth or falsity of claims; external fact retrieval, source credibility scoring, and truth verdicts are strictly reserved for Module 12 (Claim Verification & Evidence Retrieval).

