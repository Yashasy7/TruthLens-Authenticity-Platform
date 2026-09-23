# Database Schema: Module 07 — Audio Authenticity & Voice Forensics

This document specifies the PostgreSQL relational database schema for **Module 07: Audio Authenticity & Voice Forensics**, managed via Flyway migration `V7__create_audio_analysis_schema.sql`.

---

## 1. Table Overview: `audio_analysis`

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY` | Unique analysis record identifier. |
| `media_id` | `UUID` | `NOT NULL`, `UNIQUE`, `FK -> media(id) ON DELETE CASCADE` | Associated audio media asset (1:1 relation). |
| `synthetic_voice_prob` | `DOUBLE PRECISION` | `NOT NULL`, `CHECK (synthetic_voice_prob >= 0.0 AND synthetic_voice_prob <= 1.0)` | Probability that speech track is synthetic or voice-cloned. |
| `spectrogram_url` | `VARCHAR(1024)` | `NULLABLE` | File storage path or URL to generated 80-band Mel-spectrogram artifact. |
| `pitch_variance` | `DOUBLE PRECISION` | `NOT NULL DEFAULT 0.0` | Fundamental frequency pitch variance across voiced speech segments (YIN). |
| `phase_discontinuity` | `DOUBLE PRECISION` | `NOT NULL DEFAULT 0.0` | Normalized STFT second-order phase divergence metric in `[0.0, 1.0]`. |
| `splice_markers_json` | `TEXT` | `NULLABLE` | JSON array of detected audio splicing transition timestamps and confidence scores. |
| `evidence_json` | `TEXT` | `NULLABLE` | JSON object containing granular acoustic metrics and AASIST inference metadata. |
| `analysis_status` | `VARCHAR(30)` | `NOT NULL DEFAULT 'COMPLETED'` | Status lifecycle (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). |
| `model_name` | `VARCHAR(100)` | `NULLABLE` | Classifier model name (`TruthLens-PyTorch-AASIST-AudioClassifier`). |
| `model_version` | `VARCHAR(100)` | `NULLABLE` | Model checkpoint version identifier (`0.1.0-dev`, `1.0.0-prod`). |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Record creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | Record last update timestamp. |

---

## 2. Indexes

| Index Name | Table | Columns | Type | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `idx_audio_analysis_media_id` | `audio_analysis` | `media_id` | B-Tree | Fast lookup for media asset analysis queries. |
| `idx_audio_analysis_status` | `audio_analysis` | `analysis_status` | B-Tree | Filtering by analysis state. |
| `idx_audio_analysis_synthetic_voice_prob` | `audio_analysis` | `synthetic_voice_prob` | B-Tree | Querying flagged deepfake / voice-cloned audio assets. |

---

## 3. Data Integrity & Constraints

1. **Foreign Key Integrity**: `fk_audio_analysis_media` references `media(id)` with `ON DELETE CASCADE`. If an audio asset is deleted, its analysis findings and evidence are purged automatically.
2. **One-to-One Media Integrity**: `uq_audio_analysis_media_id` guarantees each media asset has at most one analysis record.
3. **Probability Bounding**: `ck_audio_analysis_synthetic_voice_prob` enforces that `synthetic_voice_prob` cannot exceed $[0.0, 1.0]$.
