package com.truthlens.backend.service.video;

import com.truthlens.backend.dto.FastApiVideoAnalysisResponse;

/**
 * Client abstraction for communicating with the internal Python AI/ML Video Service (Module 06).
 */
public interface VideoAiServiceClient {

    /**
     * Sends a video payload to the AI service for deepfake detection, face tracking,
     * and temporal forensic evaluation.
     *
     * @param videoBytes  raw bytes of the video file
     * @param filename    filename reference for multipart payload
     * @param contentType MIME type of the video (e.g. video/mp4)
     * @return structured {@link FastApiVideoAnalysisResponse}
     * @throws com.truthlens.backend.exception.AiServiceException if the AI service fails or is unreachable
     */
    FastApiVideoAnalysisResponse analyzeVideo(byte[] videoBytes, String filename, String contentType);
}
