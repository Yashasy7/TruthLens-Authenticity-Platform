-- =============================================================================
-- V7__create_audio_analysis_schema.sql
-- TruthLens — Module 07: Audio Authenticity & Voice Forensics
--
-- Creates the audio_analysis table for persisting voice cloning / synthetic voice
-- probabilities, Mel-spectrogram artifact URLs, pitch variance, phase discontinuity,
-- splice boundary markers, and granular acoustic forensic evidence.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE audio_analysis (
    id                         UUID             NOT NULL,
    media_id                   UUID             NOT NULL,
    synthetic_voice_prob       DOUBLE PRECISION NOT NULL,
    spectrogram_url            VARCHAR(1024),
    pitch_variance             DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    phase_discontinuity        DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    splice_markers_json        TEXT,
    evidence_json              TEXT,
    analysis_status            VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    model_name                 VARCHAR(100),
    model_version              VARCHAR(100),
    created_at                 TIMESTAMPTZ      NOT NULL,
    updated_at                 TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_audio_analysis PRIMARY KEY (id),
    CONSTRAINT uq_audio_analysis_media_id UNIQUE (media_id),
    CONSTRAINT fk_audio_analysis_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_audio_analysis_synthetic_voice_prob CHECK (synthetic_voice_prob >= 0.0 AND synthetic_voice_prob <= 1.0)
);

CREATE INDEX idx_audio_analysis_media_id             ON audio_analysis (media_id);
CREATE INDEX idx_audio_analysis_status               ON audio_analysis (analysis_status);
CREATE INDEX idx_audio_analysis_synthetic_voice_prob ON audio_analysis (synthetic_voice_prob);

COMMENT ON TABLE  audio_analysis                            IS 'Stores audio authenticity detection probabilities, Mel-spectrogram artifacts, pitch variance, and voice cloning forensic metrics.';
COMMENT ON COLUMN audio_analysis.id                         IS 'UUID primary key.';
COMMENT ON COLUMN audio_analysis.media_id                   IS 'FK -> media.id. Target audio asset (1:1 relation).';
COMMENT ON COLUMN audio_analysis.synthetic_voice_prob       IS 'Probability that the audio speech track is synthetic or cloned (0.0 to 1.0).';
COMMENT ON COLUMN audio_analysis.spectrogram_url            IS 'File path or storage URL to the generated 80-band Mel-spectrogram PNG artifact.';
COMMENT ON COLUMN audio_analysis.pitch_variance             IS 'Acoustic pitch variance across voiced speech segments (YIN estimator).';
COMMENT ON COLUMN audio_analysis.phase_discontinuity        IS 'STFT phase divergence coherence score (0.0 to 1.0).';
COMMENT ON COLUMN audio_analysis.splice_markers_json        IS 'JSON array of detected audio splicing transition timestamps and confidence scores.';
COMMENT ON COLUMN audio_analysis.evidence_json              IS 'Detailed JSON object containing granular acoustic metrics and AASIST inference metadata.';
COMMENT ON COLUMN audio_analysis.analysis_status            IS 'Lifecycle status of the analysis (PENDING, PROCESSING, COMPLETED, FAILED).';
COMMENT ON COLUMN audio_analysis.model_name                 IS 'Classifier architecture name (e.g. TruthLens-PyTorch-AASIST-AudioClassifier).';
COMMENT ON COLUMN audio_analysis.model_version              IS 'Version identifier of the model checkpoint.';
COMMENT ON COLUMN audio_analysis.created_at                 IS 'Record creation timestamp.';
COMMENT ON COLUMN audio_analysis.updated_at                 IS 'Record last update timestamp.';
