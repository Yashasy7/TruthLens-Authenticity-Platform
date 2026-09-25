-- =============================================================================
-- V9__create_ocr_results_schema.sql
-- TruthLens — Module 09: OCR & Visual Text Extraction
--
-- Creates the ocr_results table for persisting extracted visual text strings,
-- text region bounding boxes (spatial/polygon coordinates and temporal timestamps),
-- detected language, confidence scores, and visual preprocessing evidence.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE ocr_results (
    id                  UUID             NOT NULL,
    media_id            UUID             NOT NULL,
    extracted_text      TEXT,
    language            VARCHAR(50)      NOT NULL DEFAULT 'en',
    confidence_score    DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    regions_count       INTEGER          NOT NULL DEFAULT 0,
    bounding_boxes_json TEXT,
    evidence_json       TEXT,
    analysis_status     VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    created_at          TIMESTAMPTZ      NOT NULL,
    updated_at          TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_ocr_results PRIMARY KEY (id),
    CONSTRAINT uq_ocr_results_media_id UNIQUE (media_id),
    CONSTRAINT fk_ocr_results_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_ocr_results_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
);

CREATE INDEX idx_ocr_results_media_id ON ocr_results (media_id);
CREATE INDEX idx_ocr_results_status   ON ocr_results (analysis_status);
CREATE INDEX idx_ocr_results_language ON ocr_results (language);

COMMENT ON TABLE  ocr_results                     IS 'Stores visual text extracted from images and video keyframes via OCR, including spatial bounding boxes, language detection, and confidence scores.';
COMMENT ON COLUMN ocr_results.id                  IS 'UUID primary key.';
COMMENT ON COLUMN ocr_results.media_id            IS 'FK -> media.id. Target media asset (1:1 relation).';
COMMENT ON COLUMN ocr_results.extracted_text       IS 'Full concatenated visual text extracted from the media item.';
COMMENT ON COLUMN ocr_results.language            IS 'Primary detected language code (e.g. en, es, fr).';
COMMENT ON COLUMN ocr_results.confidence_score    IS 'Average OCR recognition confidence across all extracted text regions (0.0 to 1.0).';
COMMENT ON COLUMN ocr_results.regions_count       IS 'Total count of distinct text regions identified.';
COMMENT ON COLUMN ocr_results.bounding_boxes_json IS 'JSON array of extracted text regions with spatial coordinates, polygons, and timestamps.';
COMMENT ON COLUMN ocr_results.evidence_json       IS 'Detailed JSON object containing visual preprocessing metadata, image dimensions, and engine information.';
COMMENT ON COLUMN ocr_results.analysis_status     IS 'Lifecycle status of the analysis (PENDING, PROCESSING, COMPLETED, FAILED).';
COMMENT ON COLUMN ocr_results.created_at          IS 'Record creation timestamp.';
COMMENT ON COLUMN ocr_results.updated_at          IS 'Record last update timestamp.';
