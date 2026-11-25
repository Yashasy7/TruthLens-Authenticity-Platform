# TruthLens — Image Authenticity Analysis Engine Completion & Stabilization Report

**Module:** Module 05 — Image Authenticity Analysis
**Engineer:** Vishal (AI/ML Lead)
**Date:** November 2026
**Status:** STABILIZED & FROZEN (Research / Evaluation Baseline — Not Universal Production-Ready)

---

## 1. Executive Summary

TruthLens Module 05 (Image Authenticity Analysis) implements a dual-engine pipeline separating **AI-generated image detection** from **classical physical manipulation forensics**:

1. **AI-Generated Image Detector:** **UniversalFakeDetect (UnivFD)** built on frozen OpenAI **CLIP ViT-L/14** visual embeddings and its pretrained CVPR 2023 linear classification head (`fc_weights.pth`).
   - Significantly reduces false positives on genuine photographs compared to earlier EfficientNet-B0 checkpoints (Test Set A real FPR dropped from 56.4% to 5.74% at $\tau = 0.50$), and performs strongly on portrait deepfakes (**0.9643 ROC-AUC** on Test Set B).
   - **Important Limitation:** General-scene discrimination remains weak (**0.5744 ROC-AUC** on Test Set A), with very poor recall on unseen modern diffusion generators such as Midjourney (**1.68%** at $\tau = 0.50$, **11.17%** at $\tau = 0.0298$). **UnivFD is not a reliable universal AI-image detector.**

2. **Physical Image Manipulation Forensics Engine:**
   - **Format-Aware Error Level Analysis (ELA):** Computes JPEG recompression differences for lossy formats (`is_applicable=True`) while bypassing quantitative risk scoring on lossless rasters such as PNG (`is_applicable=False`) with an explicit disclaimer.
   - **Copy-Move Cloning Detection:** ORB keypoint self-matching with Lowe's ratio test, spatial distance filtering, RANSAC affine geometric verification ($\ge 6$ inliers), and circular shift-vector variance filtering.
   - **Spatial Noise & Splicing Indicators:** High-pass Laplacian noise residuals, patch noise variance, and sky/bokeh-masked regional noise inconsistency (`splicing_score`, `splicing_detected`), framed strictly as **heuristic forensic indicators** rather than an independently validated classifier.
   - **2D FFT Frequency-Domain Indicators:** Log-magnitude 2D Fourier spectrum visualization, outer high-frequency energy ratio, and spectral peak-to-median spike detection (`fft_anomaly_score`).

3. **Evidence-Grounded Verdict Categories & Independence:**
   - `ai_prob` and `manipulation_prob` remain strictly separated. Heuristic ELA, noise, FFT, and copy-move signals are never treated as AI-generation probabilities or blended into a misleading combined certainty score.
   - Assessment logic enforces four clear categories: **`Likely Authentic`**, **`Potentially AI-Generated`**, **`Potentially Manipulated`**, and **`Inconclusive`**, returning **`Inconclusive`** whenever evidence is weak, conflicting, low-resolution/uniform, or compressed with a lossless format (PNG) where ELA cannot run.

---

## 2. Implemented vs. Deferred Features

### 2.1 Implemented & Verified Features
- **UnivFD Inference (`classifier.py`):** Loads `ai-ml/models/univfd/ViT-L-14.pt` and `ai-ml/models/univfd/fc_weights.pth`, passing unnormalized CLIP ViT-L/14 features to `Linear(768, 1)` + `Sigmoid`. Preserves legacy `deepfake_detection_efficientnet_b0*.pt` checkpoints in `ai-ml/models/` without further training.
- **Format-Preserving Image Loading (`image_utils.py`):** Preserves `Image.format` across RGB conversion (plus filename extension fallback in `analyze_image_bytes`) so PNGs are accurately detected as lossless.
- **Physical Forensics (`ela.py`, `noise.py`, `copy_move.py`):** Computes format-aware ELA heatmaps, Laplacian noise residual maps (`COLORMAP_INFERNO`), 2D FFT spectrum overlays (`COLORMAP_VIRIDIS`), and RANSAC copy-move vector overlays.
- **Honest Verdict & Confidence Boundedness (`service.py`, `classifier.py`):**
  - Negative-class classifier confidence (`prob < 0.5`) is capped conservatively (`<= 0.35`) rather than computing `abs(prob - 0.5) * 2.0`, preventing manufactured certainty (e.g., 96% confidence on low-probability unseen diffusion images).
  - Pipeline `Likely Authentic` operational strength is conservatively capped (`<= 0.55`) and only assigned when lossy JPEG ELA is applicable and all checks pass cleanly.
- **API & Frontend Integration:**
  - FastAPI endpoints `POST /api/image/analyze` (`ImageAnalysisResponse`) and `POST /api/v1/analyze/image` (`BackendImageAnalysisResponse`) verified against Spring Boot `FastApiImageAnalysisResponse` and `ImageEvidenceDto` (including `evidence.details` propagation).
  - React `Analysis.tsx` and `ForensicArtifactViewer.tsx` render the active model (`UnivFD (CLIP ViT-L/14)`), avoid stamping low-AI-probability results as `"AUTHENTIC"`, label splicing as an indicator, and handle `gradcamHeatmapUrl = null` gracefully.

### 2.2 Explicitly Deferred Features
- **Grad-CAM Neural Attention for Vision Transformers (`gradcam.py`):**
  - `gradcam.py` hooks the last `nn.Conv2d` layer, which is valid only for convolutional architectures (historical EfficientNet-B0 checkpoints).
  - Because OpenAI CLIP ViT-L/14 is a Vision Transformer (`visual.conv1` is an input patch tokenizer, not a semantic spatial feature map), `service.py` intentionally skips Grad-CAM when `univfd` is active and sets `grad_cam_url = None`, `gradcam_heatmap_base64 = None`, and `evidence.gradcam_status = "DEFERRED_VIT_ARCHITECTURE"`.
  - Spring Boot (`ImageAuthenticityService`) and React (`ForensicArtifactViewer.tsx`) safely handle `null` Grad-CAM URLs without failing or querying missing artifacts.
- **Dedicated Endpoint Streaming for Secondary Heatmaps:**
  - Base64 PNG strings for `noise_residual_map_base64`, `fft_spectrum_base64`, and `copy_move_overlay_base64` are returned inside the FastAPI `evidence` payload. However, the Spring Boot `/api/media/{id}/image-analysis/artifacts/{type}` endpoint currently streams only `"ela"` (and `"gradcam"` when present). Extending backend artifact storage/streaming for secondary maps is outside Module 05 closure.

---

## 3. Weight Provenance & Historical Checkpoints

- **Active AI Detector Backbone:** `ai-ml/models/univfd/ViT-L-14.pt` (932.7 MB, OpenAI CLIP TorchScript).
- **Active Linear Head:** `ai-ml/models/univfd/fc_weights.pth` (4.2 KB, Wisconsin AI Vision UnivFD `Linear(768, 1)`).
- **Preserved Historical Checkpoints (Experimental / Inactive by Default):**
  - `ai-ml/models/deepfake_detection_efficientnet_b0.pt` (16.2 MB)
  - `ai-ml/models/deepfake_detection_efficientnet_b0_generalized.pt` (16.2 MB)

---

## 4. Validation Calibration & Measured Benchmark Performance

Raw continuous probabilities and predictions were recorded in [`univfd_evaluation_report.json`](file:///c:/Users/Yashas%20H%20L/IdeaProjects/TruthLens/TruthLens-Authenticity-Platform/ai-ml/models/univfd_evaluation_report.json). Threshold selection ($\tau^* = 0.0298$) was performed exclusively on the 800-image validation split before evaluating untouched test sets.

### 4.1 Validation Set (800 Images: 400 Real, 400 Fake)
- **ROC-AUC:** **0.9299** | Mean $P(\text{AI})$: Real = `0.0380`, Fake = `0.5367`
- **At $\tau = 0.5000$:** Accuracy **75.00%**, Precision **96.73%**, Recall **51.75%**, F1 **0.6743**, FPR **1.75%** (7/400), FNR **48.25%**
- **At $\tau^* = 0.0298$ (Val F1-optimal):** Accuracy **84.88%**, Precision **82.37%**, Recall **88.75%**, F1 **0.8544**, FPR **19.00%**, FNR **11.25%**

### 4.2 Official Test Benchmarks

| Test Set | Threshold | Accuracy | Precision | Recall | F1 Score | ROC-AUC | FPR | FNR |
|---|---|---|---|---|---|---|---|---|
| **Test Set A — General Scenes (1,358 imgs)** | $\tau = 0.5000$ | 49.93% | 49.35% | 5.60% | 0.1005 | **0.5744** | **5.74%** | 94.40% |
| **Test Set A — General Scenes (1,358 imgs)** | $\tau^* = 0.0298$ | 53.61% | 56.11% | 33.14% | 0.4167 | **0.5744** | 25.92% | 66.86% |
| **Test Set B — Portraits (2,000 imgs)** | $\tau = 0.5000$ | 85.95% | **97.12%** | 74.10% | 0.8406 | **0.9643** | **2.20%** | 25.90% |
| **Test Set B — Portraits (2,000 imgs)** | $\tau^* = 0.0298$ | **86.15%** | 80.66% | **95.10%** | **0.8729** | **0.9643** | 22.80% | **4.90%** |

#### Test Set A Generator Breakdown (679 Real ImageNet, 179 Midjourney, 500 Wukong):
- **Real ImageNet (679):** Mean $P = 0.0770$ | FPR @ $0.50$ = **5.74%** (39/679) | FPR @ $0.0298$ = **25.92%** (176/679)
- **Midjourney (179):** Mean $P = 0.0225$ | Recall @ $0.50$ = **1.68%** (3/179) | Recall @ $0.0298$ = **11.17%** (20/179)
- **Wukong (500):** Mean $P = 0.1051$ | Recall @ $0.50$ = **7.00%** (35/500) | Recall @ $0.0298$ = **41.00%** (205/500)

#### Test Set B Confusion Matrices (1,000 Real, 1,000 Fake):
- **At $\tau = 0.5000$:** TP=741, FN=259, FP=22, TN=978 (Mean $P$: Real `0.0436`, Fake `0.7305`)
- **At $\tau^* = 0.0298$:** TP=951, FN=49, FP=228, TN=772

#### CPU Resource Footprint (8-Thread CPU):
- **Peak RAM:** **889.57 MB**
- **Average Inference Latency:** **1,054.53 ms/image** (Test Set A), **1,042.11 ms/image** (Test Set B)

---

## 5. Actual Verification & Test Results

All stabilization fixes were verified across Python, Spring Boot, and React layers:

1. **Python Module 05 Unit & Router Suite (`pytest`):**
   - Files: `test_ela.py` (8), `test_noise.py` (7), `test_copy_move.py` (6), `test_gradcam.py` (5), `test_image_classifier_fixes.py` (13), `test_classifier.py` (8), `test_image_router.py` (16), `test_image_evaluation.py` (7), `test_trainer_and_checkpoint.py` (7).
   - **Result:** **77 passed, 0 failed** (`120.72s`).
2. **Backend Contract Suite (`test_backend_contract.py -k TestBackendImageAnalysisContract`):**
   - Verified `POST /api/v1/analyze/image` multipart JPEG/PNG responses, Base64 PNG magic header validation for ELA, `gradcam_heatmap_base64=None` handling, error codes (`400`, `422`), and `evidence` structure.
   - **Result:** **8 passed, 0 failed** (`23.28s`).
3. **Spring Boot Backend Tests (`mvn -f backend/pom.xml test` with JDK 21):**
   - `ImageAnalysisControllerTest` (12), `FastApiAiServiceClientTest` (4), `ImageAuthenticityServiceTest` (8).
   - **Result:** **24 passed, 0 failed** (`23.43s`).
4. **React Frontend Build (`npm --prefix frontend run build`):**
   - **Result:** `tsc -b && vite build` passed with **0 TypeScript/bundle errors** (`2.51s`).
5. **End-to-End FastAPI Verification Across Image Types (`POST /api/v1/analyze/image`):**
   - **Ordinary JPEG photograph (`real_0000_e4fd842a.jpg`):** `ai_prob=0.0058`, `manipulation_prob=0.0`, `ela_applicable=True`, `fft_anomaly_score=0.0`, `confidence=0.55` -> **`Likely Authentic`**.
   - **Ordinary PNG photograph (`photo.png`):** `ai_prob=0.0058`, `manipulation_prob=0.0`, `ela_applicable=False`, `confidence=0.25` -> **`Inconclusive`** (lossless container prevents ELA).
   - **Synthetic portrait (`008Y48BIX8.jpg`):** `ai_prob=0.8997`, `manipulation_prob=0.0`, `confidence=0.8997` -> **`Potentially AI-Generated`**.
   - **Copy-move tampered JPEG (`cloned.jpg`):** `ai_prob=0.0472`, `manipulation_prob=1.0`, `copy_move_detected=True`, `confidence=0.90` -> **`Potentially Manipulated`**.

---

## 6. Known Limitations & Closure Statement

1. **Not a Universal AI-Image Detector:** UnivFD was trained on ProGAN representations. While effective on portrait deepfakes (**0.9643 ROC-AUC**), its general-scene discrimination is near chance (**0.5744 ROC-AUC**) and its recall on modern Midjourney imagery is very low (**1.68%** at $\tau = 0.50$). It must not be treated as sufficient standalone proof that a general scene is human-photographed.
2. **System Not Production-Ready as a Standalone Arbiter:** Because modern diffusion generators frequently yield low `ai_prob`, and physical heuristics (ELA, noise CV, FFT, splicing) are sensitive to post-processing, recompression, and natural depth-of-field variations, human analyst review is required for high-stakes decisions.
3. **Heuristic Physical Forensics:** ELA, FFT spectral ratios, Laplacian noise variance, and regional noise CV splicing flags are uncalibrated forensic indicators rather than statistically calibrated probabilities.
4. **CPU Latency & Memory:** CLIP ViT-L/14 (~304M parameters) uses ~890 MB RAM and ~1.05 s/image on an 8-thread CPU; GPU acceleration is advisable for high-throughput workloads.
5. **Deferred ViT Attention Maps:** Spatial Grad-CAM heatmaps remain deferred for ViT-L/14; attention-rollout/ViT explainability would be needed if visual token attribution is required in future iterations.

*Module 05 (Image Authenticity Analysis) is now stabilized and frozen.*
