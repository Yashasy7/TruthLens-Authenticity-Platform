-- =============================================================================
-- V10__create_transcripts_schema.sql
-- TruthLens — Module 10: Speech-to-Text & Transcript Extraction
--
-- Creates the transcripts table for persisting transcribed spoken speech,
-- timestamped segments with word-level timing offsets, detected language,
-- confidence scores, and Faster-Whisper ASR evidence metadata.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE transcripts (
    id                      UUID             NOT NULL,
    media_id                UUID             NOT NULL,
    full_text               TEXT,
    language                VARCHAR(50)      NOT NULL DEFAULT 'en',
    confidence_score        DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    duration_seconds        DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    segments_count          INTEGER          NOT NULL DEFAULT 0,
    words_count             INTEGER          NOT NULL DEFAULT 0,
    timestamp_segments_json TEXT,
    evidence_json           TEXT,
    analysis_status         VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    created_at              TIMESTAMPTZ      NOT NULL,
    updated_at              TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_transcripts PRIMARY KEY (id),
    CONSTRAINT uq_transcripts_media_id UNIQUE (media_id),
    CONSTRAINT fk_transcripts_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_transcripts_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
);

CREATE INDEX idx_transcripts_media_id ON transcripts (media_id);
CREATE INDEX idx_transcripts_status   ON transcripts (analysis_status);
CREATE INDEX idx_transcripts_language ON transcripts (language);

COMMENT ON TABLE  transcripts                         IS 'Stores speech-to-text transcripts extracted from audio tracks and video clips, including timestamped segments, word-level offsets, language, and confidence scores.';
COMMENT ON COLUMN transcripts.id                      IS 'UUID primary key.';
COMMENT ON COLUMN transcripts.media_id                IS 'FK -> media.id. Target media asset (1:1 relation).';
COMMENT ON COLUMN transcripts.full_text               IS 'Complete concatenated speech transcript text.';
COMMENT ON COLUMN transcripts.language                IS 'Detected or configured language code (e.g. en, es, fr).';
COMMENT ON COLUMN transcripts.confidence_score        IS 'Overall transcript acoustic confidence score (0.0 to 1.0).';
COMMENT ON COLUMN transcripts.duration_seconds        IS 'Total processed speech duration in seconds.';
COMMENT ON COLUMN transcripts.segments_count          IS 'Total count of timestamped segments.';
COMMENT ON COLUMN transcripts.words_count             IS 'Total count of transcribed word tokens.';
COMMENT ON COLUMN transcripts.timestamp_segments_json IS 'JSON array of timestamped segments with phrase text, offsets, and word timings.';
COMMENT ON COLUMN transcripts.evidence_json           IS 'Detailed JSON object containing ASR model parameters, compute device, and language probability.';
COMMENT ON COLUMN transcripts.analysis_status         IS 'Lifecycle status of the analysis (PENDING, PROCESSING, COMPLETED, FAILED).';
COMMENT ON COLUMN transcripts.created_at              IS 'Record creation timestamp.';
COMMENT ON COLUMN transcripts.updated_at              IS 'Record last update timestamp.';
