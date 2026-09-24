# Database Schema: Module 10 — Speech-to-Text & Transcript Extraction

This document specifies the database table design, constraints, foreign keys, indexes, and Flyway migration script for **Module 10: Speech-to-Text & Transcript Extraction**.

---

## Migration Metadata

- **Script**: `V10__create_transcripts_schema.sql`
- **Location**: `backend/src/main/resources/db/migration/`
- **Engine Compatibility**: PostgreSQL 16.x/17.x & H2 in-memory test database (PostgreSQL mode).

---

## Table Definition: `transcripts`

Stores complete concatenated speech transcript text, detected spoken language, overall confidence score, audio duration in seconds, segments and words counts, timestamped phrase segments with word-level alignment offsets JSON, and ASR forensic evidence JSON.

| Column Name | SQL Type | Nullable | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | None | Primary Key. Unique identifier for the transcript record. |
| `media_id` | `UUID` | **NO** | None | Foreign Key referencing `media(id)` with `ON DELETE CASCADE`. One-to-one unique relation. |
| `full_text` | `TEXT` | YES | None | Full concatenated transcript text extracted from the audio/video media asset. |
| `language` | `VARCHAR(50)` | **NO** | `'en'` | Primary detected language code (e.g. `'en'`). |
| `confidence_score` | `DOUBLE PRECISION` | **NO** | `1.0` | Overall transcript confidence score ($0.0 \le \text{confidence} \le 1.0$). |
| `duration_seconds` | `DOUBLE PRECISION` | **NO** | `0.0` | Total audio/video duration analyzed in seconds. |
| `segments_count` | `INTEGER` | **NO** | `0` | Number of timestamped phrase/sentence segments. |
| `words_count` | `INTEGER` | **NO** | `0` | Total number of spoken words transcribed. |
| `timestamp_segments_json` | `TEXT` | YES | None | Serialized JSON array of timestamped segments with word offsets and confidence metrics. |
| `evidence_json` | `TEXT` | YES | None | Serialized JSON object containing ASR model metadata, compute type, and acoustic parameters. |
| `analysis_status` | `VARCHAR(30)` | **NO** | `'COMPLETED'` | Lifecycle execution status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). |
| `created_at` | `TIMESTAMPTZ` | **NO** | None | Record creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | **NO** | None | Last update timestamp in UTC. |

---

## Constraints

| Constraint Name | Type | Definition |
| :--- | :--- | :--- |
| `pk_transcripts` | Primary Key | `PRIMARY KEY (id)` |
| `uq_transcripts_media_id` | Unique | `UNIQUE (media_id)` |
| `fk_transcripts_media` | Foreign Key | `FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE` |
| `ck_transcripts_confidence` | Check | `CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)` |
| `ck_transcripts_status` | Check | `CHECK (analysis_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'))` |

---

## Indexes

| Index Name | Target Column | Index Type | Purpose |
| :--- | :--- | :--- | :--- |
| `idx_transcripts_media_id` | `media_id` | B-Tree | Fast resolution of speech transcript findings for a given media asset ID. |
| `idx_transcripts_status` | `analysis_status` | B-Tree | Filtering and indexing by pipeline execution status. |
| `idx_transcripts_language` | `language` | B-Tree | Filtering and query acceleration by detected language. |
