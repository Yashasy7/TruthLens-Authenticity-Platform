package com.truthlens.backend.entity;

/**
 * Lifecycle status of ingested media in TruthLens.
 */
public enum UploadStatus {
    /**
     * File has been successfully validated, hashed, quarantined, and registered.
     */
    UPLOADED,

    /**
     * File is queued or undergoing forensic analysis jobs.
     */
    PROCESSING,

    /**
     * All analysis pipelines have completed.
     */
    COMPLETED,

    /**
     * Analysis or post-ingestion job failed.
     */
    FAILED
}
