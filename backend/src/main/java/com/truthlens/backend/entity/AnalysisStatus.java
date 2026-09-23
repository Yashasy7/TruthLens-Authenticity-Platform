package com.truthlens.backend.entity;

/**
 * Lifecycle states for media authenticity analysis execution.
 */
public enum AnalysisStatus {
    /**
     * Analysis task queued or awaiting execution.
     */
    PENDING,

    /**
     * Analysis actively running.
     */
    PROCESSING,

    /**
     * Analysis finished successfully with valid results.
     */
    COMPLETED,

    /**
     * Analysis encountered an unrecoverable error.
     */
    FAILED
}
