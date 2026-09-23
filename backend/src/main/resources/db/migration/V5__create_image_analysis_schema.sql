-- =============================================================================
-- V5__create_image_analysis_schema.sql
-- TruthLens — Module 05: Image Authenticity Analysis
--
-- Creates the image_analysis table for persisting synthetic AI generation probabilities,
-- localized physical manipulation probabilities, ELA / Grad-CAM heatmap artifact references,
-- noise variance metrics, FFT spectral anomaly scores, and explainable forensic evidence.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE image_analysis (
    id                     UUID             NOT NULL,
    media_id               UUID             NOT NULL,
    ai_prob                DOUBLE PRECISION NOT NULL,
    manipulation_prob      DOUBLE PRECISION NOT NULL,
    ela_heatmap_url        VARCHAR(500),
    gradcam_heatmap_url    VARCHAR(500),
    noise_variance         DOUBLE PRECISION,
    fft_anomaly_score      DOUBLE PRECISION,
    copy_move_detected     BOOLEAN          NOT NULL DEFAULT FALSE,
    splicing_detected      BOOLEAN          NOT NULL DEFAULT FALSE,
    analysis_status        VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    model_version          VARCHAR(100),
    evidence_json          TEXT,
    created_at             TIMESTAMPTZ      NOT NULL,
    updated_at             TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_image_analysis PRIMARY KEY (id),
    CONSTRAINT uq_image_analysis_media_id UNIQUE (media_id),
    CONSTRAINT fk_image_analysis_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_image_analysis_ai_prob CHECK (ai_prob >= 0.0 AND ai_prob <= 1.0),
    CONSTRAINT ck_image_analysis_manipulation_prob CHECK (manipulation_prob >= 0.0 AND manipulation_prob <= 1.0)
);

CREATE INDEX idx_image_analysis_media_id   ON image_analysis (media_id);
CREATE INDEX idx_image_analysis_status     ON image_analysis (analysis_status);
CREATE INDEX idx_image_analysis_ai_prob    ON image_analysis (ai_prob);
CREATE INDEX idx_image_analysis_manip_prob ON image_analysis (manipulation_prob);

COMMENT ON TABLE  image_analysis                        IS 'Stores synthetic AI probabilities, localized manipulation scores, and forensic evidence for images.';
COMMENT ON COLUMN image_analysis.id                     IS 'UUID primary key.';
COMMENT ON COLUMN image_analysis.media_id                IS 'FK -> media.id. Media asset analyzed (1:1 relation).';
COMMENT ON COLUMN image_analysis.ai_prob                IS 'Probability that the image is synthetic / AI-generated (0.0 to 1.0).';
COMMENT ON COLUMN image_analysis.manipulation_prob      IS 'Probability of localized physical manipulation/tampering (0.0 to 1.0).';
COMMENT ON COLUMN image_analysis.ela_heatmap_url        IS 'Storage reference or URL to the generated Error Level Analysis heatmap image.';
COMMENT ON COLUMN image_analysis.gradcam_heatmap_url    IS 'Storage reference or URL to the Grad-CAM model attention heatmap overlay.';
COMMENT ON COLUMN image_analysis.noise_variance         IS 'Calculated global surface noise variance.';
COMMENT ON COLUMN image_analysis.fft_anomaly_score      IS 'Calculated 2D FFT spectral frequency anomaly score.';
COMMENT ON COLUMN image_analysis.copy_move_detected     IS 'Whether cloned or duplicated keypoint clusters were detected.';
COMMENT ON COLUMN image_analysis.splicing_detected      IS 'Whether boundary or sensor noise splicing anomalies were detected.';
COMMENT ON COLUMN image_analysis.analysis_status        IS 'Lifecycle status of the analysis (PENDING, PROCESSING, COMPLETED, FAILED).';
COMMENT ON COLUMN image_analysis.model_version          IS 'Version identifier of the vision model checkpoint used.';
COMMENT ON COLUMN image_analysis.evidence_json          IS 'Detailed structured JSON payload containing forensic metrics and explanations.';
COMMENT ON COLUMN image_analysis.created_at             IS 'Record creation timestamp.';
COMMENT ON COLUMN image_analysis.updated_at             IS 'Record last update timestamp.';
