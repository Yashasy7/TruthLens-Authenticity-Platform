# TruthLens — Audio Authenticity & Voice Forensics Module Completion Report

**Module:** Module 07 — Audio Authenticity & Voice Forensics
**Model Architecture:** AASIST-L (`clovaai/aasist` / `SpeechAntiSpoofingBenchmarks/AASIST-L`)
**Benchmark Evaluation Status:** **PENDING** (No ASVspoof2019 data downloaded, streamed, or evaluated in this phase)

---

## 1. Executive Summary

TruthLens Module 07 (Audio Authenticity & Voice Forensics) has been completed end-to-end across the **Python FastAPI AI/ML service (`ai-ml/`)**, **Spring Boot API & persistence backend (`backend/`)**, and **React TypeScript frontend (`frontend/`)**:

1. **Official Pretrained AASIST-L Classifier Integration:**
   - Replaced the earlier untrained Conv2d + Bi-GRU placeholder with the official MIT-licensed `clovaai/aasist` AASIST-L architecture (`ai-ml/services/audio_analysis/aasist_net.py`, `model.py`, `85,306` parameters) and pretrained checkpoint (`ai-ml/models/aasist_l/AASIST-L.pth`).
   - Verified raw-waveform input framing (`16 kHz` mono, deterministic `pad_or_crop_waveform` to `64,600` samples) and class logit orientation (`logits[:, 0]` = spoof, `logits[:, 1]` = bona fide).
2. **Independent Acoustic & Splice Heuristics:**
   - Preserved strict separation between AASIST-L's `synthetic_voice_prob` and handcrafted acoustic indicators (pitch contour mean/variance, STFT phase discontinuity, spectral centroid/bandwidth/roll-off/ZCR, Mel-spectrogram rendering, and heuristic splice boundary markers).
3. **Safe Failure Modes & Evidence-Grounded Verdicts:**
   - Enforced four verdict categories (`Likely Authentic`, `Potentially Synthetic Voice`, `Potentially Spliced`, `Inconclusive`) in Python (`classify_audio_authenticity`) and `MODEL_UNAVAILABLE_INCONCLUSIVE` handling in Spring Boot (`AudioAuthenticityService`) whenever the neural checkpoint is unavailable or failed.
   - An absent or broken checkpoint never falls back to `0.0` spoof probability or `Likely Authentic`.
4. **Cross-Stack Format Alignment & Spectrogram Artifacts:**
   - Aligned supported audio formats across frontend (`Upload.tsx`), Spring Boot (`MediaValidationService.java`), and Python (`ingestion.py`, powered by `soundfile==0.14.0` / `libsndfile 1.2.2`) to **WAV, FLAC, OGG, MP3**.
   - Persisted PNG Mel-spectrogram artifacts cleanly across Python (`ai-ml/storage/spectrogram/`) and Spring Boot (`StorageService` + `GET /api/media/{id}/audio-analysis/artifacts/spectrogram`), rendered in React (`Analysis.tsx` & `ForensicArtifactViewer.tsx`).

> [!IMPORTANT]
> **Benchmark Evaluation Pending:** Per project execution restrictions, the **ASVspoof2019 Logical Access (`ASVspoof2019_LA`)** dataset was **NOT** downloaded, streamed, or evaluated. Therefore, no benchmark accuracy, precision, recall, F1, ROC-AUC, or EER claims are made in this report.

---

## 2. Implemented & Preserved Components

### 2.1 Python AI/ML Service (`ai-ml/`)
- **Checkpoint & Architecture Files:**
  - `ai-ml/models/aasist_l/AASIST-L.pth` (official pretrained `SpeechAntiSpoofingBenchmarks/AASIST-L` checkpoint)
  - `ai-ml/services/audio_analysis/aasist_net.py` (MIT-licensed official `clovaai/aasist` network definition)
  - `ai-ml/services/audio_analysis/model.py` (`AASISTLClassifier`, `AASIST_L_INPUT_SAMPLES = 64600`, `pad_or_crop_waveform`, `load_audio_classifier`, `predict_synthetic_voice_probability`, `reset_audio_model`)
- **Configuration & Ingestion:**
  - `ai-ml/config/settings.py`: configured `audio_model_name="AASIST-L (clovaai/aasist)"`, `audio_model_version="1.0.0-aasist-l-asvspoof19la"`, `audio_classifier_checkpoint="aasist_l/AASIST-L.pth"`, `audio_window_duration_seconds=4.0375`, `audio_window_hop_seconds=2.0`.
  - `ai-ml/services/audio_analysis/ingestion.py`: added `soundfile` decoding (`SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3"}`, `SUPPORTED_SNDFILE_FORMATS = {"WAV", "FLAC", "OGG", "MP3"}`) with strict extension/container validation and WAV fallback.
  - `ai-ml/requirements.txt`: added minimal audio decoding dependency `soundfile==0.14.0` (verified installed in `ai-ml/venv`).
- **Temporal Windowing, Schema, Service & Health Router:**
  - `ai-ml/services/audio_analysis/temporal.py`: evaluates 16 kHz mono 64,600-sample windows directly through `AASISTLClassifier`.
  - `ai-ml/schemas/audio_analysis.py`: updated `synthetic_voice_prob` to `Optional[float]`, added `AudioAnalysisStatus.MODEL_UNAVAILABLE`, aligned `AudioSpliceMarker` (`timestamp_seconds`, `score`, `reason`) and `AudioEvidence`.
  - `ai-ml/services/audio_analysis/service.py` & `router.py`: implemented `classify_audio_authenticity`, `MODEL_UNAVAILABLE` propagation when `checkpoint_loaded` is false, spectrogram directory auto-creation before write, filename validation pass-through, and updated `/api/audio/health`.
- **Training/Evaluation Utilities & Prepared Benchmark Script:**
  - `ai-ml/services/audio_analysis/trainer.py`: updated `AudioAuthenticityDataset` and `evaluate_audio_classifier` for 64,600-sample raw waveforms and `logits[:, 0]` spoof probability; preserved `compute_eer`.
  - `ai-ml/evaluate_audio.py`: standalone ASVspoof2019 LA evaluation script (`SpeechAntiSpoofingBenchmarks/ASVspoof2019_LA`, streaming split, deterministic `seed=42`, default 500 bona fide + 500 spoof), ready for future execution (**not yet run**).

### 2.2 Spring Boot Backend (`backend/`)
- `MediaValidationService.java`: aligned accepted audio MIME types strictly to WAV, FLAC, OGG, MP3.
- `FastApiAudioAnalysisResponse.java` & `FastApiAudioAiServiceClient.java`: made `syntheticVoiceProb` nullable (`Double`) and restricted null responses strictly to `status == "MODEL_UNAVAILABLE"`.
- `AudioAuthenticityService.java` & `AudioAnalysisController.java`: added spectrogram PNG persistence via `StorageService` / `StorageKeyGenerator`, added `GET /api/media/{id}/audio-analysis/artifacts/spectrogram`, rewrote cached/returned `spectrogram_url` paths cleanly, and implemented `MODEL_UNAVAILABLE_INCONCLUSIVE` handling.

### 2.3 React Frontend (`frontend/`)
- `frontend/src/types/forensics.ts`: aligned `AudioSpliceMarkerDto` and `AudioEvidenceDto` field shapes with FastAPI/Spring Boot JSON payloads.
- `frontend/src/services/api.ts`: added `forensicsApi.getAudioArtifactUrl(mediaId, 'spectrogram')`.
- `frontend/src/pages/Upload.tsx`: restricted audio file accept/validation rules to WAV, FLAC, OGG, MP3.
- `frontend/src/components/ForensicArtifactViewer.tsx` & `frontend/src/pages/Analysis.tsx`: added Mel-spectrogram viewer integration, loading/error states, spoof probability hiding when model unavailable/pending/failed, model provenance display, scope limitation note, pitch/phase/spectral metrics, and splice markers list.

---

## 3. Verification Results

All tests below were run and observed passing after final edits:

### 3.1 Python AI/ML Automated Tests
1. **Core DSP & Feature Unit Suites (sandboxed):**
   - Command: `ai-ml\venv\Scripts\python.exe -m pytest ai-ml/tests/test_audio_features.py ai-ml/tests/test_audio_phase_spectral.py ai-ml/tests/test_audio_pitch.py ai-ml/tests/test_audio_splicing.py -v`
   - Result: **20 passed, 0 failed** (`5.12s`) — `test_audio_features.py` (10), `test_audio_phase_spectral.py` (3), `test_audio_pitch.py` (4), `test_audio_splicing.py` (3).
2. **Ingestion, AASIST-L Model & Evaluation Helper Suites (sandboxed):**
   - Command: `ai-ml\venv\Scripts\python.exe -m pytest ai-ml/tests/test_audio_ingestion.py ai-ml/tests/test_audio_model.py ai-ml/tests/test_audio_trainer.py -v`
   - Result: **26 passed, 0 failed** (`12.82s`) — `test_audio_ingestion.py` (16: WAV/stereo/resampling/FLAC/OGG/MP3 roundtrips & `.m4a`/`.aac`/`.mp4`/`.txt` rejections), `test_audio_model.py` (7: framing, forward pass, real CPU checkpoint load of `85,306` params, `index 0` spoof orientation verification, missing checkpoint `FileNotFoundError` & `MODEL_UNAVAILABLE`/`Inconclusive` safeguard), `test_audio_trainer.py` (3: `(64600,)` waveform dataset, evaluation helper, `compute_eer` & `compute_roc_auc`).
3. **FastAPI Router & Backend Contract Suites (`BypassSandbox: true` for Windows TestClient loopback):**
   - Command: `ai-ml\venv\Scripts\python.exe -m pytest ai-ml/tests/test_audio_router.py ai-ml/tests/test_backend_contract.py -k "test_audio_router or TestBackendAudioAnalysisContract or TestAudioRouter" -v`
   - Result: **12 passed, 26 deselected, 0 failed** (`32.40s`) — `test_audio_router.py` (8) and `TestBackendAudioAnalysisContract` (4).

### 3.2 Actual Model Inference & Spectrogram Persistence Verification
Verified directly on CPU (`load_audio_classifier(require_checkpoint=True)` -> `model_name="AASIST-L (clovaai/aasist)"`, `model_version="1.0.0-aasist-l-asvspoof19la"`, `parameter_count=85306`, `checkpoint_loaded=True`, `class_mapping={"0": "spoof", "1": "bonafide"}`):
- **Synthetic Format & Pipeline Probes (NOT accuracy evidence):**
  - `harmonic_probe_wav` (`WAV`): `status=COMPLETED`, `synthetic_voice_prob=1.0`, `verdict_category="Potentially Synthetic Voice"`, persisted PNG `6,141` bytes (`\x89PNG\r\n\x1a\n` verified on disk & Base64).
  - `harmonic_probe_flac` (`FLAC`): `status=COMPLETED`, `synthetic_voice_prob=1.0`, `verdict_category="Potentially Synthetic Voice"`, persisted PNG `6,146` bytes.
  - `harmonic_probe_ogg` (`OGG`): `status=COMPLETED`, `synthetic_voice_prob=1.0`, `verdict_category="Potentially Synthetic Voice"`, persisted PNG `6,470` bytes.
  - `harmonic_probe_mp3` (`MP3`): `status=COMPLETED`, `synthetic_voice_prob=1.0`, `verdict_category="Potentially Synthetic Voice"`, persisted PNG `6,542` bytes.
  - `spliced_probe_wav` (`WAV`): `status=COMPLETED`, `synthetic_voice_prob=0.9822`, `verdict_category="Potentially Synthetic Voice"`, persisted PNG `1,740` bytes.
- **Verdict Mapping Checks (`classify_audio_authenticity`):**
  - Verified all branches return expected category names: `Likely Authentic`, `Potentially Synthetic Voice`, `Potentially Spliced`, `Inconclusive` (borderline), and `Inconclusive` (missing checkpoint).
- **Missing Checkpoint Safeguard (`analyze_audio_bytes` with unavailable model):**
  - Returned `status="MODEL_UNAVAILABLE"`, `synthetic_voice_prob=None`, `verdict_category="Inconclusive"`.

### 3.3 Spring Boot Backend Tests (`BypassSandbox: true` + JDK 21)
- Command:
  ```powershell
  $env:JAVA_HOME = 'C:\Program Files\Java\jdk-21'; $env:PATH = "$env:JAVA_HOME\bin;$env:PATH"; mvn -f backend/pom.xml test "-Dtest=AudioAnalysisControllerTest,AudioAuthenticityServiceTest,FastApiAudioAiServiceClientTest,MediaValidationServiceTest"
  ```
- Result: **34 passed, 0 failed, 0 errors, 0 skipped (`BUILD SUCCESS`, `26.308 s`)**:
  - `AudioAnalysisControllerTest`: `10` passed
  - `AudioAuthenticityServiceTest`: `11` passed
  - `FastApiAudioAiServiceClientTest`: `4` passed
  - `MediaValidationServiceTest`: `9` passed

### 3.4 React Frontend Build
- Command: `npm --prefix frontend run build`
- Result: **`tsc -b && vite build` exited with code `0`** (`1826 modules transformed`, built in `2.02s`).

### 3.5 Dataset Isolation Confirmation
- `ai-ml/data/` contains only image datasets (`deepfake_detection`, `expanded_image_detection`).
- `%USERPROFILE%\.cache\huggingface\datasets` does not exist (`NO_HF_DATASETS_CACHE`).
- `ai-ml/models/audio_evaluation` does not exist (`NO_AUDIO_EVAL_DIR`).

---

## 4. Pending Benchmark Evaluation & Ready-to-Run Command

Benchmark accuracy/EER evaluation on real human bona fide vs. spoofed speech from **ASVspoof2019_LA** remains **PENDING**. When ready to run with network access and the Hugging Face `datasets` package installed:

```powershell
ai-ml\venv\Scripts\python.exe ai-ml\evaluate_audio.py --bonafide 500 --spoof 500 --seed 42 --split eval
```

Outputs will be written to `ai-ml/models/audio_evaluation/`:
- `asvspoof2019_la_sample_manifest.json`
- `asvspoof2019_la_evaluation_report.json`

---

## 5. Known Limitations & Scope Notes

1. **Unmeasured Real-Speech Benchmark Accuracy:** Until `ai-ml/evaluate_audio.py` is run against `ASVspoof2019_LA`, empirical EER, ROC-AUC, FPR, and FNR on authentic vs. cloned human speech are unverified in this environment.
2. **Domain Scope of AASIST-L:** Pretrained `AASIST-L` targets ASVspoof2019 Logical Access TTS/VC attacks (`16 kHz` speech); it is not calibrated as a universal detector across unseen modern commercial voice-cloning systems or heavy post-processing/telephony channels.
3. **Synthetic Test Probes vs. Real Speech:** Local harmonic/spliced probes confirm end-to-end decoding, feature extraction, PNG spectrogram persistence, and schema outputs, not real-speech classification accuracy (non-speech harmonic tones triggered `spoof_prob = 1.0`).
4. **Spring Boot / Python Integration Tested via Contract & Mocked HTTP Clients:** Full live HTTP upload between running Spring Boot -> running FastAPI -> PostgreSQL was verified at the component/contract boundary (`TestBackendAudioAnalysisContract` + `FastApiAudioAiServiceClientTest` + `AudioAnalysisControllerTest`), without leaving live daemon servers running.
