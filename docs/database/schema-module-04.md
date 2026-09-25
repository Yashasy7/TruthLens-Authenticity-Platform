# Database Schema — Module 04: Metadata Forensics

This document defines the database tables, constraints, relationships, and indexes introduced by Flyway migration `V4__create_metadata_schema.sql`.

---

## Table: `metadata`

Stores normalized EXIF/container header properties, camera profiles, software tags, raw hierarchical JSON metadata trees, and flagged forensic anomalies with computed suspicion scores.

### Column Definitions

| Column | Type | Nullable | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | **NO** | — | Primary key. |
| `media_id` | `UUID` | **NO** | — | Foreign key to `media(id)`. Unique (1:1 relation). |
| `camera_make` | `VARCHAR(100)` | YES | — | Camera or device manufacturer (e.g. Canon, Apple, Sony). |
| `camera_model` | `VARCHAR(100)` | YES | — | Camera or device model (e.g. EOS 5D Mark IV, iPhone 14 Pro). |
| `lens_model` | `VARCHAR(150)` | YES | — | Lens model specification. |
| `software_tag` | `VARCHAR(255)` | YES | — | Software/encoder tag found in headers. |
| `captured_at` | `TIMESTAMPTZ` | YES | — | Original capture/creation timestamp. |
| `modified_at` | `TIMESTAMPTZ` | YES | — | Modification timestamp recorded in media headers. |
| `gps_latitude` | `DOUBLE PRECISION` | YES | — | GPS latitude coordinate. |
| `gps_longitude` | `DOUBLE PRECISION` | YES | — | GPS longitude coordinate. |
| `gps_altitude` | `DOUBLE PRECISION` | YES | — | GPS altitude in meters. |
| `width` | `INTEGER` | YES | — | Visual image/video width in pixels. |
| `height` | `INTEGER` | YES | — | Visual image/video height in pixels. |
| `duration_seconds` | `DOUBLE PRECISION` | YES | — | Video/audio duration in seconds. |
| `bitrate` | `BIGINT` | YES | — | Bitrate in bits per second. |
| `frame_rate` | `DOUBLE PRECISION` | YES | — | Video frame rate in frames per second. |
| `video_codec` | `VARCHAR(50)` | YES | — | Video track codec (e.g. H.264, HEVC, VP9). |
| `audio_codec` | `VARCHAR(50)` | YES | — | Audio track codec (e.g. AAC, MP3, Opus). |
| `audio_sample_rate` | `INTEGER` | YES | — | Audio sample rate in Hz (e.g. 44100, 48000). |
| `audio_channels` | `INTEGER` | YES | — | Audio channel count (1 = mono, 2 = stereo). |
| `container_format` | `VARCHAR(50)` | YES | — | Multimedia container format (MP4, QuickTime, JPEG). |
| `raw_json` | `TEXT` | YES | — | Hierarchical JSON metadata tree. |
| `anomaly_flags` | `TEXT` | YES | — | JSON array of detected forensic anomalies. |
| `has_anomalies` | `BOOLEAN` | **NO** | `FALSE` | Boolean flag indicating if any anomalies were detected. |
| `anomaly_count` | `INTEGER` | **NO** | `0` | Count of detected anomalies. |
| `forensic_score` | `DOUBLE PRECISION` | **NO** | `0.0` | Suspicion score between 0.0000 and 1.0000. |
| `extraction_engine` | `VARCHAR(50)` | **NO** | `'JAVA_METADATA_EXTRACTOR'` | Active extraction engine used. |
| `created_at` | `TIMESTAMPTZ` | **NO** | — | Record creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | **NO** | — | Record update timestamp. |

---

## Constraints

| Constraint Name | Type | Definition |
| :--- | :--- | :--- |
| `pk_metadata` | Primary Key | `PRIMARY KEY (id)` |
| `uq_metadata_media_id` | Unique | `UNIQUE (media_id)` |
| `fk_metadata_media` | Foreign Key | `FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE` |
| `ck_metadata_forensic_score` | Check | `CHECK (forensic_score >= 0.0 AND forensic_score <= 1.0)` |

---

## Indexes

| Index Name | Target Column(s) | Purpose |
| :--- | :--- | :--- |
| `idx_metadata_media_id` | `media_id` | Fast lookup by parent media ID. |
| `idx_metadata_has_anomalies` | `has_anomalies` | High-efficiency filtering of anomalous media. |
| `idx_metadata_camera_model` | `camera_model` | Accelerated search across camera profiles. |
| `idx_metadata_software_tag` | `software_tag` | Fast indexing for editing software investigation. |
