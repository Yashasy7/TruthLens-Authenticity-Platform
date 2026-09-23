package com.truthlens.backend.service.image;

import com.truthlens.backend.dto.FastApiImageAnalysisResponse;

/**
 * Client abstraction for communicating with the internal Python AI/ML Vision Service.
 */
public interface AiServiceClient {

    /**
     * Sends an image payload to the AI service for deepfake and forensic manipulation analysis.
     *
     * @param imageBytes  raw bytes of the image file
     * @param filename    filename reference for multipart payload
     * @param contentType MIME type of the image
     * @return structured {@link FastApiImageAnalysisResponse}
     * @throws com.truthlens.backend.exception.AiServiceException if the AI service fails or is unreachable
     */
    FastApiImageAnalysisResponse analyzeImage(byte[] imageBytes, String filename, String contentType);
}
