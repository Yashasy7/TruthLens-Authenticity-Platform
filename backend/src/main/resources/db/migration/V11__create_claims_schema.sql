-- =============================================================================
-- V11__create_claims_schema.sql
-- TruthLens — Module 11: Text & Claim Analysis
--
-- Creates the claims table for persisting structured claim objects extracted
-- from OCR text (Module 09) and audio transcripts (Module 10) using NER
-- and NLP claim decomposition into Subject, Action, and Value components.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE claims (
    id                    UUID             NOT NULL,
    media_id              UUID             NOT NULL,
    claim_text            TEXT             NOT NULL,
    normalized_claim_text TEXT             NOT NULL,
    claim_type            VARCHAR(50)      NOT NULL DEFAULT 'FACTUAL_CLAIM',
    subject               VARCHAR(255),
    action                VARCHAR(255),
    "value"               TEXT,
    entity_type           VARCHAR(50)      NOT NULL DEFAULT 'GENERAL',
    confidence_score      DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    claim_hash            VARCHAR(64)      NOT NULL,
    source_type           VARCHAR(50)      NOT NULL DEFAULT 'TRANSCRIPT',
    sentence_index        INTEGER          NOT NULL DEFAULT 0,
    start_char            INTEGER          NOT NULL DEFAULT 0,
    end_char              INTEGER          NOT NULL DEFAULT 0,
    entities_json         TEXT,
    analysis_status       VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    created_at            TIMESTAMPTZ      NOT NULL,
    updated_at            TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_claims PRIMARY KEY (id),
    CONSTRAINT fk_claims_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT uq_claims_media_hash UNIQUE (media_id, claim_hash),
    CONSTRAINT ck_claims_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT ck_claims_status CHECK (analysis_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'))
);

CREATE INDEX idx_claims_media_id    ON claims (media_id);
CREATE INDEX idx_claims_hash        ON claims (claim_hash);
CREATE INDEX idx_claims_entity_type ON claims (entity_type);
CREATE INDEX idx_claims_claim_type  ON claims (claim_type);
CREATE INDEX idx_claims_status      ON claims (analysis_status);

COMMENT ON TABLE  claims                       IS 'Stores structured factual statements, entities, and verifiable claims extracted from OCR visual text and audio transcripts.';
COMMENT ON COLUMN claims.id                    IS 'UUID primary key.';
COMMENT ON COLUMN claims.media_id              IS 'FK -> media.id. Target media asset.';
COMMENT ON COLUMN claims.claim_text            IS 'Original extracted surface claim statement.';
COMMENT ON COLUMN claims.normalized_claim_text IS 'Canonical normalized claim text representation.';
COMMENT ON COLUMN claims.claim_type            IS 'Statement classification (FACTUAL_CLAIM, OPINION, QUESTION, NON_CLAIM, UNCERTAIN).';
COMMENT ON COLUMN claims.subject               IS 'Extracted nominal subject of the claim.';
COMMENT ON COLUMN claims.action                IS 'Extracted verb predicate or action.';
COMMENT ON COLUMN claims."value"               IS 'Extracted object, complement, or quantified value.';
COMMENT ON COLUMN claims.entity_type           IS 'Dominant entity category (PERSON, ORG, LOCATION, DATE, MONEY, QUANTITY, EVENT, GENERAL).';
COMMENT ON COLUMN claims.confidence_score      IS 'Claim extraction and classification confidence (0.0 to 1.0).';
COMMENT ON COLUMN claims.claim_hash            IS 'Deterministic SHA-256 hash of canonical claim tuple.';
COMMENT ON COLUMN claims.source_type           IS 'Origin of claim text: OCR, TRANSCRIPT, COMBINED, or DIRECT_TEXT.';
COMMENT ON COLUMN claims.sentence_index        IS 'Zero-based sentence index within source text.';
COMMENT ON COLUMN claims.start_char            IS 'Document start character offset.';
COMMENT ON COLUMN claims.end_char              IS 'Document end character offset.';
COMMENT ON COLUMN claims.entities_json         IS 'JSON array of recognized named entities in this claim.';
COMMENT ON COLUMN claims.analysis_status       IS 'Execution status (PENDING, PROCESSING, COMPLETED, FAILED).';
COMMENT ON COLUMN claims.created_at            IS 'Record creation timestamp.';
COMMENT ON COLUMN claims.updated_at            IS 'Record last update timestamp.';
