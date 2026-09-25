-- =============================================================================
-- V3__create_media_hashes_schema.sql
-- TruthLens — Module 03: Media Fingerprinting & Duplicate Detection
--
-- Creates the media_hashes table for storing cryptographic hashes, perceptual
-- hashes (pHash/dHash/phash_vector), acoustic fingerprints (chromaprint/chromaprint_hash),
-- and duplicate detection results.
--
-- PostgreSQL 16.x/17.x compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE media_hashes (
    id                UUID             NOT NULL,
    media_id          UUID             NOT NULL,
    sha256_hash       VARCHAR(64)      NOT NULL,
    phash             VARCHAR(64),
    phash_vector      VARCHAR(128),
    chromaprint       VARCHAR(1000),
    chromaprint_hash  VARCHAR(64),
    is_duplicate      BOOLEAN          NOT NULL DEFAULT FALSE,
    duplicate_of_id   UUID,
    similarity_score  DOUBLE PRECISION,
    match_type        VARCHAR(30)      NOT NULL DEFAULT 'NONE',
    created_at        TIMESTAMPTZ      NOT NULL,
    updated_at        TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_media_hashes              PRIMARY KEY (id),
    CONSTRAINT uq_media_hashes_media_id     UNIQUE (media_id),
    CONSTRAINT fk_media_hashes_media        FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_media_hashes_duplicate_of FOREIGN KEY (duplicate_of_id)
        REFERENCES media (id)
        ON DELETE SET NULL,
    CONSTRAINT ck_media_hashes_match_type   CHECK (match_type IN ('NONE', 'EXACT_SHA256', 'NEAR_MATCH_PHASH', 'ACOUSTIC_MATCH'))
);

CREATE INDEX idx_media_hashes_media_id        ON media_hashes (media_id);
CREATE INDEX idx_media_hashes_sha256_hash     ON media_hashes (sha256_hash);
CREATE INDEX idx_media_hashes_phash           ON media_hashes (phash);
CREATE INDEX idx_media_hashes_chromaprint_hash ON media_hashes (chromaprint_hash);
CREATE INDEX idx_media_hashes_is_duplicate    ON media_hashes (is_duplicate);
CREATE INDEX idx_media_hashes_duplicate_of    ON media_hashes (duplicate_of_id);

COMMENT ON TABLE  media_hashes                  IS 'Fingerprinting table storing cryptographic sha256_hash, perceptual phash/phash_vector, and acoustic chromaprint.';
COMMENT ON COLUMN media_hashes.id               IS 'UUID primary key.';
COMMENT ON COLUMN media_hashes.media_id          IS 'FK → media.id. The media item being fingerprinted (1:1).';
COMMENT ON COLUMN media_hashes.sha256_hash      IS 'Cryptographic SHA-256 hash (64 hex characters).';
COMMENT ON COLUMN media_hashes.phash            IS 'Perceptual visual hash (pHash/dHash 16 hex chars) for image/video.';
COMMENT ON COLUMN media_hashes.phash_vector     IS 'Vector representation of perceptual hash for similarity search.';
COMMENT ON COLUMN media_hashes.chromaprint      IS 'Acoustic fingerprint representation for audio.';
COMMENT ON COLUMN media_hashes.chromaprint_hash IS 'Compact acoustic signature hash for indexed retrieval.';
COMMENT ON COLUMN media_hashes.is_duplicate     IS 'Boolean flag indicating whether this media is an exact or near duplicate.';
COMMENT ON COLUMN media_hashes.duplicate_of_id  IS 'FK → media.id. Reference to the original media this item duplicates, if any.';
COMMENT ON COLUMN media_hashes.similarity_score IS 'Computed similarity score (0.0 to 1.0; 1.0 = identical).';
COMMENT ON COLUMN media_hashes.match_type       IS 'Classification of match: NONE, EXACT_SHA256, NEAR_MATCH_PHASH, ACOUSTIC_MATCH.';
COMMENT ON COLUMN media_hashes.created_at       IS 'Timestamp when fingerprint record was created.';
COMMENT ON COLUMN media_hashes.updated_at       IS 'Timestamp when fingerprint record was last updated.';
