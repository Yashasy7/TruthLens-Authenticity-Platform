package com.truthlens.backend.service.ocr;

import com.truthlens.backend.dto.FastApiOcrResponse;

/**
 * Service client contract for invoking the internal OCR visual text extraction microservice.
 */
public interface OcrAiServiceClient {

    /**
     * Sends raw media bytes (image or video) to the OCR AI service for visual text extraction.
     *
     * @param mediaBytes  raw binary payload of the image or video
     * @param filename    original or synthetic file name (for format identification)
     * @param contentType MIME type of the uploaded media asset
     * @return {@link FastApiOcrResponse} containing extracted text, bounding boxes, and evidence
     */
    FastApiOcrResponse analyzeOcr(byte[] mediaBytes, String filename, String contentType);
}
