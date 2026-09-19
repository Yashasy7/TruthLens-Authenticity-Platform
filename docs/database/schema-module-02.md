# Database Schema: Media Ingestion (Module 02)

This document describes the relational database schema implemented in **Flyway Migration V2** (`V2__create_media_schema.sql`).

---

## 1. Schema Overview

- **Migration Script**: `V2__create_media_schema.sql`
- **Table Introduced**: `media`
- **Engine**: PostgreSQL 16 / 17
- **Dependencies**: References `users(id)` from `V1__create_authentication_schema.sql`

---

## 2. Table: `media`

Stores metadata for ingested multimedia files in quarantined storage.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY` | Unique media identifier. |
| `user_id` | `UUID` | `NOT NULL, FK → users(id) ON DELETE CASCADE` | Identity of the uploader. |
| `original_filename`| `VARCHAR(255)` | `NOT NULL` | Sanitized display filename. |
| `storage_path` | `VARCHAR(500)` | `NOT NULL` | Server-controlled storage key in quarantine. |
| `media_type` | `VARCHAR(20)` | `NOT NULL` | Category: `IMAGE`, `VIDEO`, `AUDIO`, `TEXT`. |
| `mime_type` | `VARCHAR(100)` | `NOT NULL` | True MIME type verified via Apache Tika. |
| `file_size` | `BIGINT` | `NOT NULL, CHECK (file_size > 0)` | File size in bytes. |
| `sha256_hash` | `VARCHAR(64)` | `NOT NULL` | 64-character lowercase hexadecimal hash. |
| `upload_status` | `VARCHAR(30)` | `NOT NULL, DEFAULT 'UPLOADED'` | Status: `UPLOADED`, `PROCESSING`, `COMPLETED`, `FAILED`. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Upload / quarantine ingestion timestamp. |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | Timestamp of last record update. |

---

## 3. Indexes & Constraints

- **Foreign Key**: `fk_media_user` references `users(id)` with `ON DELETE CASCADE`. If a user is deleted, all their media records are cleaned up.
- **Check Constraints**:
  - `ck_media_media_type`: `media_type IN ('IMAGE', 'VIDEO', 'AUDIO', 'TEXT')`
  - `ck_media_upload_status`: `upload_status IN ('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED')`
  - `ck_media_file_size`: `file_size > 0`
- **Indexes**:
  - `idx_media_user_id`: Fast retrieval of user uploads (`/api/media/my`).
  - `idx_media_sha256_hash`: Key index for future duplicate detection (Module 03).
  - `idx_media_media_type`: Filtering by media category.
  - `idx_media_upload_status`: Queue selection by status (`UPLOADED`).
  - `idx_media_created_at`: Chronological ordering.
