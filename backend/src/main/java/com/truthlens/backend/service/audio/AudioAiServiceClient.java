package com.truthlens.backend.service.audio;

import com.truthlens.backend.dto.FastApiAudioAnalysisResponse;

/**
 * Client abstraction for communicating with the internal Python AI/ML Audio Service (Module 07).
 */
public interface AudioAiServiceClient {

    /**
     * Sends an audio payload to the AI service for synthetic voice detection,
     * Mel-spectrogram rendering, pitch analysis, and acoustic forensic evaluation.
     *
     * @param audioBytes  raw bytes of the audio file
     * @param filename    filename reference for multipart payload
     * @param contentType MIME type of the audio (e.g. audio/wav, audio/mpeg)
     * @return structured {@link FastApiAudioAnalysisResponse}
     * @throws com.truthlens.backend.exception.AiServiceException if the AI service fails or is unreachable
     */
    FastApiAudioAnalysisResponse analyzeAudio(byte[] audioBytes, String filename, String contentType);
}
