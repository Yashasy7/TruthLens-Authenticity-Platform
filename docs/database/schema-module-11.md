# Database Schema: Module 11 — Text & Claim Analysis

This document specifies the database table design, constraints, foreign keys, indexes, and Flyway migration script for **Module 11: Text & Claim Analysis**.

---

## Migration Metadata

- **Script**: `V11__create_claims_schema.sql`
- **Location**: `backend/src/main/resources/db/migration/`
- **Engine Compatibility**: PostgreSQL 16.x/17.x & H2 in-memory test database (PostgreSQL mode).

---

## Table Definition: `claims`

Stores structured factual statements, entities, and verifiable claims extracted from OCR visual text and audio transcripts using spaCy Named Entity Recognition and syntactic/semantic claim decomposition.

| Column Name | SQL Type | Nullable | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `UUID` | **NO** | None | Primary Key. Unique identifier for the claim record. |
| `media_id` | `UUID` | **NO** | None | Foreign Key referencing `media(id)` with `ON DELETE CASCADE`. |
| `claim_text` | `TEXT` | **NO** | None | Original surface assertion text extracted from OCR or speech transcript. |
| `normalized_claim_text` | `TEXT` | **NO** | None | Canonical normalized representation for deduplication and matching. |
| `claim_type` | `VARCHAR(50)` | **NO** | `'FACTUAL_CLAIM'` | Statement classification (`FACTUAL_CLAIM`, `OPINION`, `QUESTION`, `NON_CLAIM`, `UNCERTAIN`). |
| `subject` | `VARCHAR(255)` | YES | None | Extracted nominal subject or agent of the claim statement. |
| `action` | `VARCHAR(255)` | YES | None | Extracted main verb predicate or action clause. |
| `"value"` | `TEXT` | YES | None | Extracted direct object, predicate complement, or quantified value. |
| `entity_type` | `VARCHAR(50)` | **NO** | `'GENERAL'` | Dominant entity classification (`PERSON`, `ORG`, `LOCATION`, `DATE`, `MONEY`, `QUANTITY`, `EVENT`, `GENERAL`). |
| `confidence_score` | `DOUBLE PRECISION` | **NO** | `1.0` | Overall claim extraction and classification confidence ($0.0 \le \text{confidence} \le 1.0$). |
| `claim_hash` | `VARCHAR(64)` | **NO** | None | Deterministic cryptographic SHA-256 hash of canonical normalized claim tuple. |
| `source_type` | `VARCHAR(50)` | **NO** | `'TRANSCRIPT'` | Origin of analyzed text (`OCR`, `TRANSCRIPT`, `COMBINED`, `DIRECT_TEXT`). |
| `sentence_index` | `INTEGER` | **NO** | `0` | Zero-based index of the sentence within the analyzed document. |
| `start_char` | `INTEGER` | **NO** | `0` | Character start offset within the source text. |
| `end_char` | `INTEGER` | **NO** | `0` | Character end offset within the source text. |
| `entities_json` | `TEXT` | YES | None | Serialized JSON array of extracted named entity spans with labels and character bounds. |
| `analysis_status` | `VARCHAR(30)` | **NO** | `'COMPLETED'` | Pipeline execution lifecycle status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). |
| `created_at` | `TIMESTAMPTZ` | **NO** | None | Record creation timestamp in UTC. |
| `updated_at` | `TIMESTAMPTZ` | **NO** | None | Last update timestamp in UTC. |

---

## Constraints

| Constraint Name | Type | Definition |
| :--- | :--- | :--- |
| `pk_claims` | Primary Key | `PRIMARY KEY (id)` |
| `fk_claims_media` | Foreign Key | `FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE` |
| `uq_claims_media_hash` | Unique | `UNIQUE (media_id, claim_hash)` |
| `ck_claims_confidence` | Check | `CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)` |
| `ck_claims_status` | Check | `CHECK (analysis_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'))` |

---

## Indexes

| Index Name | Target Column(s) | Index Type | Purpose |
| :--- | :--- | :--- | :--- |
| `idx_claims_media_id` | `media_id` | B-Tree | Fast lookup of all extracted claims belonging to a media asset. |
| `idx_claims_hash` | `claim_hash` | B-Tree | Global deduplication and cross-media claim comparison. |
| `idx_claims_entity_type` | `entity_type` | B-Tree | Filtering claims by primary entity domain (e.g. POLITICIAN, ORG, MONEY). |
| `idx_claims_claim_type` | `claim_type` | B-Tree | Filtering claims by statement type (e.g. FACTUAL_CLAIM vs OPINION). |
| `idx_claims_status` | `analysis_status` | B-Tree | Query acceleration by processing lifecycle status. |
