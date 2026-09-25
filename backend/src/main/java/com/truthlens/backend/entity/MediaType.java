package com.truthlens.backend.entity;

/**
 * Supported multimedia categories for TruthLens authenticity analysis.
 *
 * <p>Determined by magic-byte content inspection via Apache Tika rather than
 * client-supplied MIME headers or file extensions.</p>
 */
public enum MediaType {
    /**
     * Visual raster graphics (JPEG, PNG, WEBP, GIF, BMP, TIFF).
     */
    IMAGE,

    /**
     * Video files containing temporal frame sequences (MP4, MOV, AVI, WEBM, MKV).
     */
    VIDEO,

    /**
     * Audio voice and sound recordings (MP3, WAV, OGG, FLAC, M4A, AAC).
     */
    AUDIO,

    /**
     * Text documents and transcripts (Plain text, CSV, HTML, JSON, PDF).
     */
    TEXT
}
