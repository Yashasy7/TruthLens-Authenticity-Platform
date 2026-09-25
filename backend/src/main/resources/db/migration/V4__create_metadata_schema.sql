-- =============================================================================
-- V4__create_metadata_schema.sql
-- TruthLens — Module 04: Metadata Forensics
--
-- Creates the metadata table for storing normalized EXIF/container header details,
-- camera profiles, software tags, raw JSON metadata trees, and detected forensic anomaly flags.
--
-- PostgreSQL 16.x/17.x & H2 compatible.
-- Managed by Flyway; do NOT apply this script manually.
-- =============================================================================

CREATE TABLE metadata (
    id                 UUID             NOT NULL,
    media_id           UUID             NOT NULL,
    camera_make        VARCHAR(100),
    camera_model       VARCHAR(100),
    lens_model         VARCHAR(150),
    software_tag       VARCHAR(255),
    captured_at        TIMESTAMPTZ,
    modified_at        TIMESTAMPTZ,
    gps_latitude       DOUBLE PRECISION,
    gps_longitude      DOUBLE PRECISION,
    gps_altitude       DOUBLE PRECISION,
    width              INTEGER,
    height             INTEGER,
    duration_seconds   DOUBLE PRECISION,
    bitrate            BIGINT,
    frame_rate         DOUBLE PRECISION,
    video_codec        VARCHAR(50),
    audio_codec        VARCHAR(50),
    audio_sample_rate  INTEGER,
    audio_channels     INTEGER,
    container_format   VARCHAR(50),
    raw_json           TEXT,
    anomaly_flags      TEXT,
    has_anomalies      BOOLEAN          NOT NULL DEFAULT FALSE,
    anomaly_count      INTEGER          NOT NULL DEFAULT 0,
    forensic_score     DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    extraction_engine  VARCHAR(50)      NOT NULL DEFAULT 'JAVA_METADATA_EXTRACTOR',
    created_at         TIMESTAMPTZ      NOT NULL,
    updated_at         TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_metadata               PRIMARY KEY (id),
    CONSTRAINT uq_metadata_media_id      UNIQUE (media_id),
    CONSTRAINT fk_metadata_media         FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_metadata_forensic_score CHECK (forensic_score >= 0.0 AND forensic_score <= 1.0)
);

CREATE INDEX idx_metadata_media_id       ON metadata (media_id);
CREATE INDEX idx_metadata_has_anomalies  ON metadata (has_anomalies);
CREATE INDEX idx_metadata_camera_model   ON metadata (camera_model);
CREATE INDEX idx_metadata_software_tag   ON metadata (software_tag);

COMMENT ON TABLE  metadata                   IS 'Forensic metadata table storing EXIF, container headers, raw JSON trees, and forensic anomaly flags.';
COMMENT ON COLUMN metadata.id                IS 'UUID primary key.';
COMMENT ON COLUMN metadata.media_id           IS 'FK → media.id. Media item this metadata belongs to (1:1).';
COMMENT ON COLUMN metadata.camera_make       IS 'Camera or device manufacturer (e.g. Canon, Apple, Sony).';
COMMENT ON COLUMN metadata.camera_model      IS 'Camera or device model (e.g. EOS 5D Mark IV, iPhone 14 Pro).';
COMMENT ON COLUMN metadata.lens_model        IS 'Lens specification if present in EXIF.';
COMMENT ON COLUMN metadata.software_tag      IS 'Software / encoder tag found in headers (e.g. Adobe Photoshop, ffmpeg).';
COMMENT ON COLUMN metadata.captured_at       IS 'Original capture/creation timestamp from EXIF/container.';
COMMENT ON COLUMN metadata.modified_at       IS 'Modification timestamp recorded in media headers.';
COMMENT ON COLUMN metadata.gps_latitude      IS 'GPS latitude coordinate if embedded.';
COMMENT ON COLUMN metadata.gps_longitude     IS 'GPS longitude coordinate if embedded.';
COMMENT ON COLUMN metadata.gps_altitude      IS 'GPS altitude in meters if embedded.';
COMMENT ON COLUMN metadata.width             IS 'Visual width in pixels.';
COMMENT ON COLUMN metadata.height            IS 'Visual height in pixels.';
COMMENT ON COLUMN metadata.duration_seconds  IS 'Duration in seconds for video/audio.';
COMMENT ON COLUMN metadata.bitrate           IS 'Estimated bitrate in bits per second.';
COMMENT ON COLUMN metadata.frame_rate        IS 'Video frame rate in frames per second.';
COMMENT ON COLUMN metadata.video_codec       IS 'Video stream codec (e.g. H.264, HEVC, VP9).';
COMMENT ON COLUMN metadata.audio_codec       IS 'Audio stream codec (e.g. AAC, MP3, Opus).';
COMMENT ON COLUMN metadata.audio_sample_rate IS 'Audio sampling rate in Hz (e.g. 44100, 48000).';
COMMENT ON COLUMN metadata.audio_channels    IS 'Audio channel count (1 = mono, 2 = stereo, etc.).';
COMMENT ON COLUMN metadata.container_format  IS 'Container format (e.g. QuickTime/MP4, JPEG, RIFF/WAV).';
COMMENT ON COLUMN metadata.raw_json          IS 'Full hierarchical metadata tree serialized as JSON.';
COMMENT ON COLUMN metadata.anomaly_flags     IS 'JSON array of forensic anomaly findings and rule evaluations.';
COMMENT ON COLUMN metadata.has_anomalies     IS 'Boolean flag indicating if any forensic anomalies were flagged.';
COMMENT ON COLUMN metadata.anomaly_count     IS 'Total number of flagged anomalies.';
COMMENT ON COLUMN metadata.forensic_score    IS 'Normalized suspicion score (0.0 = authentic, 1.0 = highly anomalous).';
COMMENT ON COLUMN metadata.extraction_engine IS 'Identification of the engine used for extraction.';
COMMENT ON COLUMN metadata.created_at        IS 'Record creation timestamp.';
COMMENT ON COLUMN metadata.updated_at        IS 'Record last update timestamp.';
