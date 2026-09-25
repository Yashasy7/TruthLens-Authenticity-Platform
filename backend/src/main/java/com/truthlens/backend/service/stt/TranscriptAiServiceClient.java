package com.truthlens.backend.service.stt;

import com.truthlens.backend.dto.FastApiTranscriptResponse;

/**
 * Service client contract for invoking the internal Speech-to-Text & Transcript microservice.
 */
public interface TranscriptAiServiceClient {

    /**
     * Sends raw audio/video media bytes to the STT AI service for speech transcription.
     *
     * @param mediaBytes  raw binary payload of the audio or video
     * @param filename    original or synthetic file name (for format identification)
     * @param contentType MIME type of the uploaded media asset
     * @return {@link FastApiTranscriptResponse} containing transcript text, segments, words, and evidence
     */
    FastApiTranscriptResponse analyzeSpeechToText(byte[] mediaBytes, String filename, String contentType);
}
