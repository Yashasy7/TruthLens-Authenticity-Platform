# Database Schema: Module 09 — Optical Character Recognition (OCR)

This document specifies the database table design, constraints, foreign keys, indexes, and Flyway migration script for **Module 09: OCR Text Extraction**.

---

## Migration Metadata

- **Script**: `V9__create_ocr_results_schema.sql`
- **Location**: `backend/src/main/resources/db/migration/`
- **Engine Compatibility**: PostgreSQL 16.x/17.x & H2 in-memory test database (PostgreSQL mode).

---

## Table Definition: `ocr_results`

Stores complete concatenated extracted text, detected language, average OCR confidence score, identified text regions count, bounding boxes / polygon coordinates JSON, and forensic evidence JSON.

| Column Name | SQL Type | Nullable | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | None | Primary Key. Unique identifier for the OCR record. |
| `media_id` | `UUID` | **NO** | None | Foreign Key referencing `media(id)` with `ON DELETE CASCADE`. One-to-one unique relation. |
| `extracted_text` | `TEXT` | YES | None | Full concatenated text extracted from the visual asset. |
| `language` | `VARCHAR(50)` | **NO** | `'en'` | Primary detected language code (e.g. `'en'`). |
| `confidence_score` | `DOUBLE PRECISION` | **NO** | `1.0` | Average OCR confidence score across all regions ($0.0 \le \text{confidence} \le 1.0$). |
| `regions_count` | `INTEGER` | **NO** | `0` | Number of distinct text regions / lines extracted. |
| `bounding_boxes_json` | `TEXT` | YES | None | Serialized JSON array of text regions with spatial bounding boxes and timestamps. |
| `evidence_json` | `TEXT` | YES | None | Serialized JSON object containing preprocessing parameters and engine diagnostics. |
| `analysis_status` | `VARCHAR(30)` | **NO** | `'COMPLETED'` | Lifecycle execution status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). |
| `created_at` | `TIMESTAMPTZ` | **NO** | None | Record creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | **NO** | None | Last update timestamp in UTC. |

---

## Constraints

| Constraint Name | Type | Definition |
| :--- | :--- | :--- |
| `pk_ocr_results` | Primary Key | `PRIMARY KEY (id)` |
| `uq_ocr_results_media_id` | Unique | `UNIQUE (media_id)` |
| `fk_ocr_results_media` | Foreign Key | `FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE` |
| `ck_ocr_results_confidence` | Check | `CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)` |

---

## Indexes

| Index Name | Target Column | Index Type | Purpose |
| :--- | :--- | :--- | :--- |
| `idx_ocr_results_media_id` | `media_id` | B-Tree | Fast resolution of OCR findings for a given media asset ID. |
| `idx_ocr_results_status` | `analysis_status` | B-Tree | Filtering and indexing by pipeline execution status. |
| `idx_ocr_results_language` | `language` | B-Tree | Filtering and query acceleration by detected language. |
