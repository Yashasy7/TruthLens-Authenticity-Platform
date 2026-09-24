package com.truthlens.backend.service.avsync;

import com.truthlens.backend.dto.FastApiAvSyncResponse;

/**
 * Client interface for interacting with the AI/ML Audio-Video Synchronization microservice (Module 08).
 */
public interface AvSyncAiServiceClient {

    /**
     * Submits a video payload containing audio to the AI/ML service for AV sync analysis.
     *
     * @param videoBytes  raw binary content of the video
     * @param filename    original filename
     * @param contentType MIME type of the video
     * @return {@link FastApiAvSyncResponse} containing scores, offset, and mismatch segments
     */
    FastApiAvSyncResponse analyzeAvSync(byte[] videoBytes, String filename, String contentType);
}
