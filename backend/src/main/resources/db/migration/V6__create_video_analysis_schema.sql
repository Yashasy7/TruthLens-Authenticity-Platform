-- =============================================================================
-- V6__create_video_analysis_schema.sql
-- TruthLens — Module 06: Video Deepfake & Forensic Analysis
--
-- Creates the video_analysis table for persisting deepfake manipulation probabilities,
-- face count metrics, sampled frame quantities, suspicious timestamps, and frame-level
-- forensic scores.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE video_analysis (
    id                         UUID             NOT NULL,
    media_id                   UUID             NOT NULL,
    deepfake_prob              DOUBLE PRECISION NOT NULL,
    face_count                 INTEGER          NOT NULL DEFAULT 0,
    total_frames_sampled       INTEGER          NOT NULL DEFAULT 0,
    suspicious_timestamps_json TEXT,
    frame_scores_json          TEXT,
    analysis_status            VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    model_version              VARCHAR(100),
    created_at                 TIMESTAMPTZ      NOT NULL,
    updated_at                 TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_video_analysis PRIMARY KEY (id),
    CONSTRAINT uq_video_analysis_media_id UNIQUE (media_id),
    CONSTRAINT fk_video_analysis_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_video_analysis_deepfake_prob CHECK (deepfake_prob >= 0.0 AND deepfake_prob <= 1.0)
);

CREATE INDEX idx_video_analysis_media_id      ON video_analysis (media_id);
CREATE INDEX idx_video_analysis_status        ON video_analysis (analysis_status);
CREATE INDEX idx_video_analysis_deepfake_prob ON video_analysis (deepfake_prob);

COMMENT ON TABLE  video_analysis                            IS 'Stores video deepfake detection probabilities, timeline anomaly markers, and frame scores.';
COMMENT ON COLUMN video_analysis.id                         IS 'UUID primary key.';
COMMENT ON COLUMN video_analysis.media_id                   IS 'FK -> media.id. Target video asset (1:1 relation).';
COMMENT ON COLUMN video_analysis.deepfake_prob              IS 'Aggregate probability that the video contains synthetic/deepfake content (0.0 to 1.0).';
COMMENT ON COLUMN video_analysis.face_count                 IS 'Number of distinct continuous face tracks observed.';
COMMENT ON COLUMN video_analysis.total_frames_sampled       IS 'Total count of frames extracted and scored.';
COMMENT ON COLUMN video_analysis.suspicious_timestamps_json IS 'JSON array of marked suspicious timestamps and forensic reasons.';
COMMENT ON COLUMN video_analysis.frame_scores_json          IS 'Detailed JSON array of per-frame deepfake and temporal anomaly scores.';
COMMENT ON COLUMN video_analysis.analysis_status            IS 'Lifecycle status of the analysis (PENDING, PROCESSING, COMPLETED, FAILED).';
COMMENT ON COLUMN video_analysis.model_version              IS 'Version identifier of the deepfake classification model checkpoint.';
COMMENT ON COLUMN video_analysis.created_at                 IS 'Record creation timestamp.';
COMMENT ON COLUMN video_analysis.updated_at                 IS 'Record last update timestamp.';
