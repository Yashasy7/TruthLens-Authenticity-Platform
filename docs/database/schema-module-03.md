# Database Schema: Module 03 (media_hashes)

Managed by Flyway migration: `backend/src/main/resources/db/migration/V3__create_media_hashes_schema.sql`

---

## 1. Table: `media_hashes`

Stores cryptographic digests, perceptual visual hashes (dHash/phash_vector), and acoustic signatures (chromaprint/chromaprint_hash) associated 1-to-1 with ingested media records in `media`.

| Column | Type | Nullable | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | **NO** | - | Primary Key. Unique identifier for the fingerprint record. |
| `media_id` | `UUID` | **NO** | - | Foreign Key &rarr; `media(id)` ON DELETE CASCADE. Unique constraint (1:1 with media). |
| `sha256_hash` | `VARCHAR(64)` | **NO** | - | Cryptographic SHA-256 hex digest (64 characters). Indexed. |
| `phash` | `VARCHAR(64)` | YES | NULL | Perceptual difference hash (16 hex chars) for image/visual media. Indexed. |
| `phash_vector` | `VARCHAR(128)` | YES | NULL | Vector representation of perceptual hash for similarity search (blueprint compliance). |
| `chromaprint` | `VARCHAR(1000)`| YES | NULL | Spectral acoustic signature sequence for audio media. |
| `chromaprint_hash`| `VARCHAR(64)`| YES | NULL | Compact acoustic signature hash for indexed candidate lookup. Indexed. |
| `is_duplicate` | `BOOLEAN` | **NO** | `FALSE` | Flag indicating whether this media was matched as a duplicate. Indexed. |
| `duplicate_of_id` | `UUID` | YES | NULL | Foreign Key &rarr; `media(id)` ON DELETE SET NULL. Canonical original media duplicated. Indexed. |
| `similarity_score`| `DOUBLE PRECISION` | YES | NULL | Computed similarity score between 0.0 and 1.0 (1.0 = exact duplicate). |
| `match_type` | `VARCHAR(30)` | **NO** | `'NONE'` | Classification: `NONE`, `EXACT_SHA256`, `NEAR_MATCH_PHASH`, `ACOUSTIC_MATCH`. |
| `created_at` | `TIMESTAMPTZ` | **NO** | - | Timestamp when fingerprint was computed. |
| `updated_at` | `TIMESTAMPTZ` | **NO** | - | Timestamp when fingerprint record was last updated. |

---

## 2. Constraints & Indexes

```sql
CONSTRAINT pk_media_hashes              PRIMARY KEY (id)
CONSTRAINT uq_media_hashes_media_id     UNIQUE (media_id)
CONSTRAINT fk_media_hashes_media        FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE
CONSTRAINT fk_media_hashes_duplicate_of FOREIGN KEY (duplicate_of_id) REFERENCES media (id) ON DELETE SET NULL
CONSTRAINT ck_media_hashes_match_type   CHECK (match_type IN ('NONE', 'EXACT_SHA256', 'NEAR_MATCH_PHASH', 'ACOUSTIC_MATCH'))

CREATE INDEX idx_media_hashes_media_id        ON media_hashes (media_id);
CREATE INDEX idx_media_hashes_sha256_hash     ON media_hashes (sha256_hash);
CREATE INDEX idx_media_hashes_phash           ON media_hashes (phash);
CREATE INDEX idx_media_hashes_chromaprint_hash ON media_hashes (chromaprint_hash);
CREATE INDEX idx_media_hashes_is_duplicate    ON media_hashes (is_duplicate);
CREATE INDEX idx_media_hashes_duplicate_of    ON media_hashes (duplicate_of_id);
```
