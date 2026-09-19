-- =============================================================================
-- V2__create_media_schema.sql
-- TruthLens — Module 02: Media Upload & Secure Ingestion
--
-- Creates the media table for storing quarantined uploaded media metadata.
--
-- Supported media categories: IMAGE, VIDEO, AUDIO, TEXT.
--
-- PostgreSQL 16.x/17.x compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: media
-- Central registry for ingested media files.
-- -----------------------------------------------------------------------------
CREATE TABLE media (
    id                UUID         NOT NULL,
    user_id           UUID         NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path      VARCHAR(500) NOT NULL,
    media_type        VARCHAR(20)  NOT NULL,
    mime_type         VARCHAR(100) NOT NULL,
    file_size         BIGINT       NOT NULL,
    sha256_hash       VARCHAR(64)  NOT NULL,
    upload_status     VARCHAR(30)  NOT NULL DEFAULT 'UPLOADED',
    created_at        TIMESTAMPTZ  NOT NULL,
    updated_at        TIMESTAMPTZ  NOT NULL,

    CONSTRAINT pk_media               PRIMARY KEY (id),
    CONSTRAINT fk_media_user          FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_media_media_type    CHECK (media_type IN ('IMAGE', 'VIDEO', 'AUDIO', 'TEXT')),
    CONSTRAINT ck_media_upload_status CHECK (upload_status IN ('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    CONSTRAINT ck_media_file_size     CHECK (file_size > 0)
);

CREATE INDEX idx_media_user_id       ON media (user_id);
CREATE INDEX idx_media_sha256_hash   ON media (sha256_hash);
CREATE INDEX idx_media_media_type    ON media (media_type);
CREATE INDEX idx_media_upload_status ON media (upload_status);
CREATE INDEX idx_media_created_at    ON media (created_at DESC);

COMMENT ON TABLE  media                   IS 'Central registry for ingested multimedia files in quarantined storage.';
COMMENT ON COLUMN media.id                IS 'UUID primary key.';
COMMENT ON COLUMN media.user_id           IS 'FK → users.id. Uploader identity. Cascades on delete.';
COMMENT ON COLUMN media.original_filename IS 'Sanitized original filename submitted by uploader.';
COMMENT ON COLUMN media.storage_path      IS 'Server-controlled storage key/path in quarantined storage.';
COMMENT ON COLUMN media.media_type        IS 'TruthLens media category: IMAGE, VIDEO, AUDIO, TEXT.';
COMMENT ON COLUMN media.mime_type         IS 'Verified MIME type detected via Apache Tika magic-bytes.';
COMMENT ON COLUMN media.file_size         IS 'File size in bytes.';
COMMENT ON COLUMN media.sha256_hash       IS 'Cryptographic SHA-256 hash (64 lowercase hex chars).';
COMMENT ON COLUMN media.upload_status     IS 'Upload/processing lifecycle status: UPLOADED, PROCESSING, COMPLETED, FAILED.';
COMMENT ON COLUMN media.created_at        IS 'Timestamp when the media was ingested into quarantined storage.';
COMMENT ON COLUMN media.updated_at        IS 'Timestamp when the media record was last updated.';
