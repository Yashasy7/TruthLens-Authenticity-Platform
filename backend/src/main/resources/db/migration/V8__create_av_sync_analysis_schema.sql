-- =============================================================================
-- V8__create_av_sync_analysis_schema.sql
-- TruthLens — Module 08: Audio-Video Synchronization Analysis
--
-- Creates the av_sync_analysis table for persisting audio-video synchronization
-- scores, lip/audio temporal offsets (in milliseconds), mismatch timestamps/segments,
-- and explainable cross-modal evidence.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE av_sync_analysis (
    id                     UUID             NOT NULL,
    media_id               UUID             NOT NULL,
    sync_score             DOUBLE PRECISION NOT NULL,
    lip_offset_ms          DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence             DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    mismatch_segments_json TEXT,
    evidence_json          TEXT,
    analysis_status        VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    model_name             VARCHAR(100),
    model_version          VARCHAR(100),
    created_at             TIMESTAMPTZ      NOT NULL,
    updated_at             TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_av_sync_analysis PRIMARY KEY (id),
    CONSTRAINT uq_av_sync_analysis_media_id UNIQUE (media_id),
    CONSTRAINT fk_av_sync_analysis_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_av_sync_analysis_sync_score CHECK (sync_score >= 0.0 AND sync_score <= 1.0),
    CONSTRAINT ck_av_sync_analysis_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX idx_av_sync_analysis_media_id   ON av_sync_analysis (media_id);
CREATE INDEX idx_av_sync_analysis_status     ON av_sync_analysis (analysis_status);
CREATE INDEX idx_av_sync_analysis_sync_score ON av_sync_analysis (sync_score);

COMMENT ON TABLE  av_sync_analysis                        IS 'Stores audio-video synchronization scores, measured lip/audio offsets, mismatch segments, and cross-modal evidence.';
COMMENT ON COLUMN av_sync_analysis.id                     IS 'UUID primary key.';
COMMENT ON COLUMN av_sync_analysis.media_id               IS 'FK -> media.id. Target video asset (1:1 relation).';
COMMENT ON COLUMN av_sync_analysis.sync_score             IS 'Overall audio-video synchronization score (0.0 to 1.0, 1.0 = perfectly synced).';
COMMENT ON COLUMN av_sync_analysis.lip_offset_ms          IS 'Measured temporal offset in milliseconds between visual visemes and spoken audio phonemes (positive = audio lags video).';
COMMENT ON COLUMN av_sync_analysis.confidence             IS 'Forensic confidence score of the synchronization assessment (0.0 to 1.0).';
COMMENT ON COLUMN av_sync_analysis.mismatch_segments_json IS 'JSON array of marked mismatch segments containing start/end timestamps, local offsets, confidence, and diagnostic reasons.';
COMMENT ON COLUMN av_sync_analysis.evidence_json          IS 'Detailed JSON object containing tracking stability, envelope cross-correlation, and SyncNet distance metrics.';
COMMENT ON COLUMN av_sync_analysis.analysis_status        IS 'Lifecycle status of the analysis (PENDING, PROCESSING, COMPLETED, FAILED).';
COMMENT ON COLUMN av_sync_analysis.model_name             IS 'Classifier architecture name (e.g. TruthLens-PyTorch-SyncNet-DualStream).';
COMMENT ON COLUMN av_sync_analysis.model_version          IS 'Version identifier of the model checkpoint.';
COMMENT ON COLUMN av_sync_analysis.created_at             IS 'Record creation timestamp.';
COMMENT ON COLUMN av_sync_analysis.updated_at             IS 'Record last update timestamp.';
