# Database Schema: Module 08 — Audio-Video Synchronization Analysis

This document specifies the database table design, constraints, foreign keys, indexes, and Flyway migration script for **Module 08: Audio-Video Synchronization Analysis**.

---

## Migration Metadata

- **Script**: `V8__create_av_sync_analysis_schema.sql`
- **Location**: `backend/src/main/resources/db/migration/`
- **Engine Compatibility**: PostgreSQL 16.x/17.x & H2 in-memory test database (PostgreSQL mode).

---

## Table Definition: `av_sync_analysis`

Stores physical speech phoneme and visual viseme synchronization metrics, estimated temporal offset in milliseconds, detected mismatch segments, and diagnostic cross-modal evidence.

| Column Name | SQL Type | Nullable | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | None | Primary Key. Unique identifier for the analysis record. |
| `media_id` | `UUID` | **NO** | None | Foreign Key referencing `media(id)` with `ON DELETE CASCADE`. One-to-one unique relation. |
| `sync_score` | `DOUBLE PRECISION` | **NO** | None | Global AV synchronization score ($0.0 \le \text{sync\_score} \le 1.0$). 1.0 = perfect alignment, 0.0 = severe desync/dubbing. |
| `lip_offset_ms` | `DOUBLE PRECISION` | **NO** | `0.0` | Measured lip-to-audio temporal offset in milliseconds (positive = audio lags video, negative = audio leads video). |
| `confidence` | `DOUBLE PRECISION` | **NO** | `0.0` | Overall forensic confidence score ($0.0 \le \text{confidence} \le 1.0$). |
| `mismatch_segments_json` | `TEXT` | YES | None | JSON array of detected temporal mismatch windows (`start_time`, `end_time`, `offset_ms`, `confidence`, `reason`). |
| `evidence_json` | `TEXT` | YES | None | Granular JSON object with tracking stability, envelope correlation, and SyncNet distance metrics. |
| `analysis_status` | `VARCHAR(30)` | **NO** | `'COMPLETED'` | Lifecycle execution status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). |
| `model_name` | `VARCHAR(100)` | YES | None | Model architecture identifier (e.g. `TruthLens-PyTorch-SyncNet-DualStream`). |
| `model_version` | `VARCHAR(100)` | YES | None | Checkpoint version (e.g. `TruthLens-SyncNet-v1.0-dev`). |
| `created_at` | `TIMESTAMPTZ` | **NO** | None | Record creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | **NO** | None | Last update timestamp in UTC. |

---

## Constraints

| Constraint Name | Type | Definition |
| :--- | :--- | :--- |
| `pk_av_sync_analysis` | Primary Key | `PRIMARY KEY (id)` |
| `uq_av_sync_analysis_media_id` | Unique | `UNIQUE (media_id)` |
| `fk_av_sync_analysis_media` | Foreign Key | `FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE` |
| `ck_av_sync_analysis_sync_score` | Check | `CHECK (sync_score >= 0.0 AND sync_score <= 1.0)` |
| `ck_av_sync_analysis_confidence` | Check | `CHECK (confidence >= 0.0 AND confidence <= 1.0)` |

---

## Indexes

| Index Name | Target Column | Index Type | Purpose |
| :--- | :--- | :--- | :--- |
| `idx_av_sync_analysis_media_id` | `media_id` | B-Tree | Fast lookup when resolving analyses by media asset ID. |
| `idx_av_sync_analysis_status` | `analysis_status` | B-Tree | Optimizes background queue querying by analysis state. |
| `idx_av_sync_analysis_sync_score` | `sync_score` | B-Tree | Accelerates range queries and risk-scoring filters for desynchronized media. |
