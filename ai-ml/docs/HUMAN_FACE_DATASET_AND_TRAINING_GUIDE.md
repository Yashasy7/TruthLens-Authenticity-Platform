# TruthLens — Stage 1: Human-Face Dataset Preparation & Google Colab GPU Training Guide

**Status:** Stage 1 Preparation Complete (No full dataset downloaded; no production inference files modified)
**Target Architecture:** ImageNet-pretrained `efficientnet_b0` (`timm==1.0.3`) -> 3-class linear head (`genuine`, `ai_generated`, `manipulated`)
**Production Scope Lock:** Active image pipeline (`ai-ml/services/image_analysis/`, UnivFD), audio module, Spring Boot backend, and React frontend remain completely untouched pending dataset acquisition and Colab checkpoint evaluation.

---

## 1. Dataset Access & Licensing Report

### 1.1 Primary Candidate: AI-Face (`Purdue-M2/AI-Face-FairnessBench`, CVPR 2025)
* **Source:** [`Purdue-M2/AI-Face-FairnessBench`](https://github.com/Purdue-M2/AI-Face-FairnessBench) (`arXiv:2406.00783`)
* **Published Scale:** **400,885** genuine human face images and **1,245,660** synthetic/deepfake face images spanning **37 generation methods** (GANs, diffusion models, and deepfake video benchmarks), plus demographic attributes (`Gender`, `Age`, `Skin Tone` on the Monk Skin Tone Scale, and `Intersection`).
* **Access Mechanism:** Publicly browsable code repository, while image `.tar` archives and CSV annotation files (`train.csv`, `test.csv`) are hosted behind a **Google Form + signed End-User License Agreement (EULA)** verification process (distributed via Google Drive / institutional links upon approval).
* **Annotation Caveat:** The CSV `Target` column is strictly binary (`0` = real, `1` = fake). It does **not** separate whole-face AI generation (`ai_generated`) from face-swap/reenactment (`manipulated`). All 3-class labels MUST be resolved from `Image Path` / method metadata (verified in Section 2).

#### Legal & Licensing Assessment — `CC BY-NC-ND 4.0`
The AI-Face release carries **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (`CC BY-NC-ND 4.0`)**, layered atop upstream component dataset licenses:

1. **NonCommercial (`NC`) Clause:** Restricts use to non-commercial academic, research, or educational evaluation. While TruthLens is currently an academic capstone prototype, any future commercial SaaS deployment or paid API hosting **cannot** distribute models or assets in violation of `NC` terms without explicit rights-holder permission.
2. **NoDerivatives (`ND`) Clause (Documented Legal Uncertainty):**
   * Under CC 4.0 Section 4, creating and sharing *Adapted Material* (derivative works) is forbidden.
   * **Unsettled legal boundary for ML:** Whether supervised feature extraction and weight updates into a classifier checkpoint (or intermediate cropped/resized working copies in Google Drive) qualify as non-expressive statistical analysis or an unauthorized derivative adaptation remains legally unsettled and varies by jurisdiction (for example, statutory Text & Data Mining exceptions vs contractual EULA/CC intent).
   * **Operational Mitigation for Stage 1:** Do not redistribute raw AI-Face images, avoid storing resized dataset mirrors publicly, keep training artifacts private/non-commercial for academic research, and read the exact AI-Face EULA document before downloading archives via Google Form.
3. **Upstream Sub-Dataset Restrictions:** Underlying sources aggregated inside AI-Face (e.g., `CelebA`, `FF++`, `DFDC`, `Celeb-DF-v2`) retain their original non-commercial/research constraints and citation requirements.

#### 1.1.1 Official AI-Face EULA Inspection Checklist (Verify Before Download)
**Important:** Do not claim or assume any permission beyond what is explicitly stated in the signed AI-Face EULA and upstream component agreements. Before downloading archives or uploading subsets to cloud infrastructure, verify every point below directly in the official EULA document provided with the Google Form:

- [ ] **Academic Model Training:** Does the EULA explicitly allow supervised neural-network fine-tuning (training a 3-class detector) beyond running the unmodified benchmark scripts?
- [ ] **Google Drive & Google Colab Processing:** Are third-party cloud uploads (storing extracted image subsets or archives on Google Drive and reading them inside Google Colab VMs) permitted under data-redistribution / third-party-server clauses?
- [ ] **Model Weights Storage, Sharing & Distribution:** May trained model weights be saved to team cloud storage, shared privately among capstone project members, or published publicly? *(CC BY-NC-ND 4.0 and EULA terms do **not** automatically grant permission to distribute trained weights.)*
- [ ] **Project Demonstration & GitHub Repository:** Are live academic capstone demonstrations (local or hosted UI) and committing non-weight training/prep code to a public or private GitHub repository permitted? Must example face screenshots/crops from the dataset be excluded from reports or repositories?
- [ ] **Attribution, Retention & Deletion Obligations:** What exact attribution/citation notice (`CC BY-NC-ND 4.0`, CVPR 2025 paper, dataset creators) is mandatory, and does the EULA require deleting local/cloud dataset copies once research/coursework concludes?
- [ ] **Upstream Subset Permissions (`FF++`, `DFDC`, `Celeb-DF-v2`):** Does signing the AI-Face EULA cover academic access to FaceForensics++, DFDC, and Celeb-DF-v2 frames bundled inside AI-Face, or must separate upstream forms/agreements (e.g., TUM FaceForensics Terms of Use, Meta DFDC access agreement) be signed beforehand?

### 1.2 Supplementary Dataset Assessments

| Dataset | Local Status | Provenance & Verified Classes Available | Access & Licensing Terms | Recommendation |
|---|---|---|---|---|
| **Local `datasets/DeepFakeDetection/`** (`140,000` files, `256x256` JPG) | Present locally (`70k real`, `70k fake`; also split into `ai-ml/data/deepfake_detection/` and `5k` in `expanded_image_detection/human_portraits/`) | Derived from **Kaggle `xhlulu/140k-real-and-fake-faces`**: `real/` (`00000.jpg`–`69999.jpg`) = **FFHQ (`genuine`)**; `fake/` (random 10-char IDs) = **StyleGAN (`ai_generated`)**. Documented in `expanded_manifest.json`. Contains **0 manipulated face-swap images**. | Kaggle `"Other (specified in description)"`; inherits FFHQ (`CC BY-NC-SA 4.0`) + Nvidia StyleGAN research usage terms. | **Approved for `genuine` (0) and `ai_generated` (1) supplementation** using `--local-profile kaggle_140k_ffhq_stylegan`. Must undergo SHA-256 + perceptual `dhash` deduplication against AI-Face FFHQ/StyleGAN subsets before splitting. |
| **DFDC (Deepfake Detection Challenge)** | Not downloaded | Meta acted-consent deepfake video benchmark (`genuine` + `manipulated` video frames). | Meta/Kaggle non-commercial research access agreement + citation requirement (`arXiv:2006.07397`). | Acquire only via AI-Face approved subset or official Kaggle/Meta agreement; isolate per-video IDs across splits. |
| **FaceForensics++ (`FF++`)** | Not downloaded | Real YouTube clips (`original_sequences`) + 4/5 manipulation methods (`Deepfakes`, `Face2Face`, `FaceSwap`, `FaceShifter`, `NeuralTextures`). | Strictly academic/non-commercial **FaceForensics Terms of Use** (signed TUM access form + indemnification clauses). | Ideal `manipulated` (`Class 2`) source if AI-Face approval includes FF++ or after signing official TUM request. Keep video pairs grouped so train/val/test never share source clip IDs. |

### 1.3 Feasibility vs Initial Experiment Targets (`15,000 / 15,000 / 15,000`)
* **Class 0 (`genuine`) — 15,000 target:** Immediately achievable from local FFHQ (`70,000` unique images verified) + AI-Face real subsets (`FFHQ`, `CelebA`, `IMDB-WIKI`, real `FF++`/`DFDC`).
* **Class 1 (`ai_generated`) — 15,000 target:** Partially covered locally by StyleGAN (`70,000`), but training solely on StyleGAN harms diffusion generalization. Combining StyleGAN with approved **AI-Face GAN + Diffusion** archives (`ProGAN`, `StyleGAN2/3`, `Latent Diffusion`, `Stable Diffusion v1.5`, `DALLE2`, `Midjourney`, `SDXL`) easily meets 15,000 with multi-generator diversity.
* **Class 2 (`manipulated`) — 15,000 target (DATA GAP WITHOUT UPSTREAM APPROVAL):** Existing local workspace data contains **zero verified face-swap or facial-reenactment images**. Meeting the 15,000 target for Class 2 strictly requires downloading approved **AI-Face deepfake subsets** (`FF++`, `DFDC`, `DFD`, `Celeb-DF-v2`) or approved **FaceForensics++ / DFDC** data after signing their academic access forms.

---

## 2. Verified 3-Class Source & Generator Mapping

Implemented deterministically in [`ai-ml/human_face_dataset.py`](../human_face_dataset.py) via `VERIFIED_SUBSET_REGISTRY` and `resolve_subset_class()`:

| TruthLens Class | Label ID | Verified Subsets / Methods | Notes & Strict Guardrails |
|---|---:|---|---|
| **`genuine`** | `0` | `ffhq`, `celeba`, `celeba_hq`, `imdb_wiki`, `original_sequences` / `youtube_real` (`FF++`), plus verified real polarity (`Target == 0`) inside `ff_pp`, `dfdc`, `dfd`, `celeb_df_v2` | Any image whose binary `Target != 0` is rejected (`target_mismatch_expected_real`). |
| **`ai_generated`** | `1` | **GANs:** `stylegan`, `stylegan2`, `stylegan3`, `progan`, `mmdgan`, `msg_gan`, `sngan`, `vqgan`<br>**Diffusion:** `latent_diffusion`, `ldm`, `stable_diffusion_v1_5` (`sdv1_5`), `sdxl`, `dalle2`, `if` (`deepfloyd_if`), `midjourney`, `dcface`, `ddim`, `ddpm` | Pure whole-face synthesis. Requires `Target == 1` when CSV target exists. `midjourney` and `sdxl` are held out to `test` by default as unseen generators. |
| **`manipulated`** | `2` | **Video Deepfakes:** `deepfakes`, `faceswap`, `face2face`, `neuraltextures`, `faceshifter`, fake polarity (`Target == 1`) of `ff_pp`, `dfdc`, `dfd`, `celeb_df_v2`<br>**Image Swap:** `simswap`, `blendface`, `facedancer`, `infoswap`, `uniface`, `diffswap` | Face swap or facial reenactment. `celeb_df_v2` and `faceshifter` are held out to `test` by default as unseen manipulation benchmarks. |
| **Quarantined (`ambiguous`)** | *Excluded* (default) | `attgan`, `stgan`, `stargan`, `palette`, `stable_diffusion_inpainting` (`sd_inpainting`) | Partial attribute-editing & conditional inpainting blur the line between `ai_generated` and `manipulated`. Excluded by default (`--ambiguous-policy exclude`) and logged in `dataset_audit_report.json`, or mapped to `manipulated` ONLY via explicit `--ambiguous-policy manipulated`. |
| **Unmapped / Generic `fake`** | *Rejected* | Unknown directory or `fake/` without verified provenance profile | **Never inferred from binary `Target == 1`.** Rejected as `unverified_subset`. |

---

## 3. Dataset Manifest Specification

Generated by `ai-ml/human_face_dataset.py` into `<output-dir>/dataset_manifest.json` alongside `<output-dir>/dataset_audit_report.json`:

```json
{
  "schema_version": "1.0.0",
  "dataset_name": "TruthLens-HumanFace-3Class",
  "created_at": "UTC ISO-8601 timestamp",
  "class_names": ["genuine", "ai_generated", "manipulated"],
  "class_to_id": {"genuine": 0, "ai_generated": 1, "manipulated": 2},
  "total_images": 45000,
  "target_per_class": 15000,
  "split_counts": {
    "train": {"genuine": 12000, "ai_generated": 12000, "manipulated": 12000},
    "val":   {"genuine": 1500,  "ai_generated": 1500,  "manipulated": 1500},
    "test":  {"genuine": 1500,  "ai_generated": 1500,  "manipulated": 1500}
  },
  "leakage_check": {
    "sha256_train_val": 0,
    "sha256_train_test": 0,
    "sha256_val_test": 0,
    "dhash_train_val": 0,
    "dhash_train_test": 0,
    "dhash_val_test": 0,
    "group_train_val": 0,
    "group_train_test": 0,
    "group_val_test": 0,
    "total_leaks": 0
  },
  "images": [
    {
      "image_path": "train/manipulated/deepfakes_0000123_a1b2c3d4.jpg",
      "source_path": "/abs/path/to/source.jpg",
      "split": "train",
      "label": 2,
      "class_name": "manipulated",
      "source_subset": "deepfakes",
      "source_dataset": "AI-Face",
      "source_group_id": "deepfakes::dir::001_002",
      "resolution_reason": "verified_registry_match",
      "md5": "...",
      "sha256": "...",
      "dhash": "16-hex-char 64-bit perceptual hash",
      "width": 256,
      "height": 256,
      "format": "JPEG",
      "demographics": {"gender": "1", "age": "3", "skin_tone": "..."}
    }
  ]
}
```

### Leakage & Deduplication Rules Enforced Before Splitting
1. **Exact & Perceptual Near-Duplicate Removal:** Images sharing identical `sha256` digests OR 64-bit difference hashes (`dhash`) within Hamming distance `<= 4` (`--dhash-hamming-threshold 4`) are deduplicated deterministically (independent of CSV/directory traversal order, prioritizing `unseen_test` > `unseen_val` > `shared`) before split assignment.
2. **Paired Video & Identity Group Isolation:** Paired real/fake clips (`FF++` clip/pair IDs, `Celeb-DF-v2` actor IDs) share canonical `identity_tokens` / `source_group_id` clusters via Union-Find so related real and forged identities never cross splits. Generic folders (`train`, `part_01`, `batch_01`) are never collapsed into one group.
3. **Unseen-Generator Holdout:** By default, `midjourney`, `sdxl`, `celeb_df_v2`, and `faceshifter` (along with paired real-source identities sharing a held-out cluster/container) route strictly to `test`.
4. **Colab-Portable Paths & Quota Shortfall Reporting:** Always emits POSIX relative `image_path` entries (`--materialize` recommended when combining multiple source directories). Class quota shortfalls are logged explicitly in `dataset_audit_report.json` rather than silently underfilling or slicing identity groups.

---

## 4. Expected Storage Requirements

*(Note: Official AI-Face `.tar` byte sizes are not enumerated in `arXiv:2406.00783`; the full-dataset figures below are engineering estimates based on average face-crop file sizes, whereas manifest/checkpoint/local figures are observed/exact specs.)*

| Component | Item Count | Estimated / Expected Footprint | Fit Check |
|---|---:|---:|---|
| **Full AI-Face Dataset** *(not needed)* | ~1,646,545 images | **~150–400+ GB** (compressed/extracted depending on PNG vs JPEG resolution) | Exceeds Google Drive Free (15 GB) & Colab Free disk (~78–107 GB). Extract only needed `.tar` subsets! |
| **Target 3-Class Subset (Experiment 1)** | `45,000` images (`15k × 3`) | **~1.1–3.6 GB** (`25–80 KB/img` JPEG/PNG face crops) | Fits cleanly inside **Google Drive Free (15 GB)** and **Colab VM SSD**. |
| **Archive + Unzip Overhead During Colab Transfer** | 1 subset archive | **~2.5–7.5 GB** peak during `.tar`/`.zip` extraction | Delete temporary archives on local VM once extracted or stream materialized folders. |
| **Dataset Manifest JSON (`45k` rows)** | `45,000` records | **~22–28 MB** | Negligible. |
| **Deployment Checkpoint (`.pt`, weights only)** | 1 file | **~16.2 MB** (`efficientnet_b0`, 3-class linear head, no optimizer state) | Fits easily inside local git/storage & Drive. |
| **Resumable Colab Checkpoint (with AdamW + GradScaler)** | 1 file | **~48–60 MB** | Fits cleanly on Drive (`resume_checkpoint.pt`). |
| **Local Workspace Staging Copy (if `--materialize` with NTFS hardlinks on same drive)** | `45,000` files | **~0 GB extra** (local NTFS hardlinks), or **~1.1–3.6 GB** if zipped for Drive upload | Verify NTFS same-volume paths before `--materialize`. |

---

## 5. Google Colab GPU Training Notebook & Checkpoint Contract

Notebook location: [`ai-ml/notebooks/train_human_face_colab.ipynb`](../notebooks/train_human_face_colab.ipynb)

### Architecture & Contract Preserved for Future TruthLens Integration
* Backbone: `timm.create_model("efficientnet_b0", pretrained=True, num_classes=0)`
* Head: `nn.Sequential(nn.Dropout(p=0.2), nn.Linear(1280, 3))` (`head.1.weight` shape `[3, 1280]`, `head.1.bias` shape `[3]`)
* Input size & normalization: `224×224`, ImageNet `mean=(0.485, 0.456, 0.406)`, `std=(0.229, 0.224, 0.225)` (matching `utils/image_utils.py`).
* Two-stage training schedule:
  * **Stage 1 (`4 epochs`, `lr=3e-4`):** Backbone frozen in `.eval()`, `head` (including `Dropout(p=0.2)`) kept in `.train()`.
  * **Stage 2 (`up to 12 epochs`):** Unfreezes `blocks.5.`, `blocks.6.`, `conv_head.`, `bn2.`, `head.` (`backbone lr=1e-5`, `head lr=1e-4`), keeping earlier BatchNorm layers frozen in `.eval()`, and resetting early-stopping patience upon entering Stage 2.
* Best model selection metric: **Validation `macro_f1`** (requiring all 3 classes present; class-weighted cross entropy loss + AMP `GradScaler`).
* **Exported Deployment Checkpoint Keys (`human_face_efficientnet_b0_best.pt`):**
  `model_state_dict`, `backbone`, `num_classes`, `class_names`, `input_size`, `normalization`, `model_version`, `dataset_manifest`, `best_val_metrics`, `training_config`, `epoch`, `created_at` (with `optimizer_state_dict` strictly omitted).

---

## 6. Beginner-Friendly Google Colab Setup Instructions

1. **Create / Verify Google Account & Drive Space:**
   * Ensure at least **6 GB free** on Google Drive (free 15 GB tier is plenty for the 45k subset + checkpoints).
   * Create folder `MyDrive/TruthLens/human_face/`.
2. **Prepare Your Balanced Dataset Locally (after obtaining approved AI-Face / FF++ / DFDC archives):**
   * Run Command B below (`--materialize`) to build clean `train/`, `val/`, `test/` folders plus `dataset_manifest.json`.
   * Package the materialized folder into `human_face_subset.zip` or `human_face_subset.tar` and upload both `dataset_manifest.json` and the archive to `MyDrive/TruthLens/human_face/`.
3. **Open the Notebook in Colab:**
   * Go to [Google Colab](https://colab.research.google.com/) -> **File -> Upload notebook** -> select `ai-ml/notebooks/train_human_face_colab.ipynb`.
4. **Select GPU Runtime:**
   * In the top menu click **Runtime -> Change runtime type -> Hardware accelerator: `T4 GPU` -> Save**.
   * Confirm Step 1 outputs a NVIDIA T4 GPU (`~15 GB VRAM`). Free Colab sessions support T4 GPUs cleanly at `batch_size=32` with `use_amp=True`.
5. **Configure Paths in Step 3:**
   * Set `DRIVE_ROOT = Path("/content/drive/MyDrive/TruthLens/human_face")`.
   * Recommended for speed: set `OPTIONAL_ARCHIVE_PATH = DRIVE_ROOT / "human_face_subset.zip"` (or `.tar`/`.tar.gz`). Step 3 extracts either format onto Colab's local VM SSD (`/content/human_face_data`) and auto-detects the extracted dataset root.
6. **Handle Colab Timeouts Without Losing Progress:**
   * Each epoch writes `resume_checkpoint.pt` (including `no_improve_count`) back to Drive. If Colab disconnects, reconnect GPU, remount Drive, keep `CONFIG["resume_if_available"] = True`, and **Run All**.
7. **Collect Outputs:**
   * Download `human_face_efficientnet_b0_best.pt` and `test_evaluation_report.json` from `MyDrive/TruthLens/human_face/checkpoints/hf_effnet_b0_v1/`.
   * Evaluate locally using `ai-ml/evaluate_human_face.py` before proposing any Stage 2 production integration.

---

## 7. Exact Commands to Prepare, Validate, and Audit the Dataset

Run all commands from the repository root (`TruthLens-Authenticity-Platform`) in Windows PowerShell using the existing virtual environment:

### A. Dry Local Sanity Test (Optional — Genuine + StyleGAN only; Class 2 will show 0 gap)
```powershell
ai-ml\venv\Scripts\python.exe ai-ml\human_face_dataset.py `
  --local-source datasets\DeepFakeDetection `
  --local-profile kaggle_140k_ffhq_stylegan `
  --output-dir ai-ml\data\human_face_local_check `
  --target-per-class 2000
```

### B. Full 3-Class Preparation Once Approved AI-Face Archives Are Downloaded
*(Replace paths with where you extracted AI-Face `.tar` subsets and CSV annotations)*:
```powershell
ai-ml\venv\Scripts\python.exe ai-ml\human_face_dataset.py `
  --aiface-csv path\to\AI-Face\dataset\train.csv `
  --aiface-csv path\to\AI-Face\dataset\test.csv `
  --aiface-root path\to\AI-Face `
  --local-source datasets\DeepFakeDetection `
  --local-profile kaggle_140k_ffhq_stylegan `
  --output-dir ai-ml\data\human_face_v1 `
  --target-per-class 15000 `
  --ambiguous-policy exclude `
  --unseen-test-generators midjourney sdxl celeb_df_v2 faceshifter `
  --materialize
```

### C. Validate Zero Leakage, Exact Quotas, and Unseen-Generator Separation
```powershell
ai-ml\venv\Scripts\python.exe ai-ml\evaluate_human_face.py `
  --manifest ai-ml\data\human_face_v1\dataset_manifest.json `
  --verify-only `
  --check-files-exist
```

### D. Evaluate Downloaded Colab Checkpoint Locally (CPU) After Training
```powershell
ai-ml\venv\Scripts\python.exe ai-ml\evaluate_human_face.py `
  --manifest ai-ml\data\human_face_v1\dataset_manifest.json `
  --checkpoint ai-ml\models\candidates\human_face_efficientnet_b0_best.pt `
  --split test `
  --data-root ai-ml\data\human_face_v1 `
  --output-dir ai-ml\reports\human_face_v1
```

---

## 7. Video-to-Face Extraction Pipeline (`ai-ml/extract_manipulated_faces.py`)

### 7.1 Purpose & Role in 3-Class Strategy
Because existing local data contains 70,000 genuine faces (FFHQ) and 70,000 AI-generated faces (StyleGAN), but **0 manipulated faces**, the extraction script [`ai-ml/extract_manipulated_faces.py`](../extract_manipulated_faces.py) extracts and aligns face crops from authorized deepfake video datasets (such as **FaceForensics++**, **Celeb-DF-v2**, or **DFDC**).

### 7.2 Key Architectural Safeguards
1. **Zero Centre-Crop Fallback:** When face detection fails or faces fall below `--min-face-size`, the pipeline explicitly logs `no_face_detected` and **skips the frame**. It never fabricates arbitrary center crops.
2. **Margin-Expanded Square Alignment:** Expands face bounding boxes by `--margin-percent` (default 25%) and applies reflection padding (`cv2.BORDER_REFLECT_101`) if bounding boxes touch frame edges, outputting clean square crops (e.g., 256×256) preserving facial contours.
3. **Paired Identity/Video Grouping:** Extracts canonical `source_group_id` and `identity_tokens`:
   - FaceForensics++: `001_002.mp4` (manipulated) and `001.mp4` (genuine) share `ffpp::clip::001`.
   - Celeb-DF-v2: `id0_id1_0001.mp4` (manipulated) and `id0_0001.mp4` (genuine) share `celebdf::actor::id0`.
4. **Intra-Video Deduplication:** Suppresses near-identical consecutive crops within the same video using perceptual difference hashing (`dhash`) with a configurable Hamming distance threshold (`--dedup-threshold 4`).
5. **Stage 1 Manifest Compatibility:** Generates `extracted_faces_manifest.json` and `extraction_report.json` with schema version `1.1.0`, compatible with [`ai-ml/human_face_dataset.py`](../human_face_dataset.py).

### 7.3 Example Usage Commands

#### A. Extract Faces from FaceForensics++ Directory
```powershell
ai-ml\venv\Scripts\python.exe ai-ml\extract_manipulated_faces.py `
  --input path\to\FaceForensics++ `
  --output-dir ai-ml\data\extracted_ffpp `
  --frame-interval 15 `
  --max-frames-per-video 40 `
  --crop-size 256 `
  --margin-percent 0.25 `
  --min-face-size 64 `
  --confidence-threshold 0.5 `
  --dedup-threshold 4
```

#### B. Extract Faces from Celeb-DF-v2 Directory
```powershell
ai-ml\venv\Scripts\python.exe ai-ml\extract_manipulated_faces.py `
  --input path\to\Celeb-DF-v2 `
  --output-dir ai-ml\data\extracted_celebdf `
  --frame-interval 10 `
  --max-frames-per-video 50 `
  --crop-size 256 `
  --dedup-threshold 4
```

#### C. Extract from a Single Video (Test / Ad-Hoc)
```powershell
ai-ml\venv\Scripts\python.exe ai-ml\extract_manipulated_faces.py `
  --input path\to\video.mp4 `
  --output-dir ai-ml\data\single_video_faces `
  --frame-interval 5 `
  --verbose
```
