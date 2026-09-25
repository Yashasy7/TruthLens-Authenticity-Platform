package com.truthlens.backend.service.stt;

import com.truthlens.backend.dto.FastApiTranscriptResponse;
import com.truthlens.backend.exception.AiServiceException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * REST client implementation communicating with the internal Python FastAPI Speech-to-Text Service (Module 10).
 */
@Service
public class FastApiTranscriptServiceClient implements TranscriptAiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(FastApiTranscriptServiceClient.class);

    private final RestClient restClient;
    private final String serviceUrl;

    public FastApiTranscriptServiceClient(
            RestClient.Builder restClientBuilder,
            @Value("${truthlens.ai.service-url:http://localhost:8001}") String serviceUrl,
            @Value("${truthlens.ai.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${truthlens.ai.stt-read-timeout-ms:60000}") int readTimeoutMs) {

        this.serviceUrl = serviceUrl;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        this.restClient = restClientBuilder
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();

        log.info("Initialized FastApiTranscriptServiceClient targeting {}", serviceUrl);
    }

    FastApiTranscriptServiceClient(RestClient restClient, String serviceUrl) {
        this.restClient = restClient;
        this.serviceUrl = serviceUrl;
    }

    @Override
    public FastApiTranscriptResponse analyzeSpeechToText(byte[] mediaBytes, String filename, String contentType) {
        if (mediaBytes == null || mediaBytes.length == 0) {
            throw new IllegalArgumentException("Media bytes cannot be null or empty");
        }

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        ByteArrayResource fileResource = new ByteArrayResource(mediaBytes) {
            @Override
            public String getFilename() {
                return (filename != null && !filename.isBlank()) ? filename : "media.wav";
            }
        };
        body.add("file", fileResource);

        try {
            log.debug("Sending Speech-to-Text transcription request to AI service at {} ({} bytes)", serviceUrl, mediaBytes.length);

            FastApiTranscriptResponse response = restClient.post()
                    .uri("/api/v1/analyze/speech-to-text")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (req, res) -> {
                        String responseBody = new String(res.getBody().readAllBytes(), StandardCharsets.UTF_8);
                        log.error("AI STT service error HTTP {}: {}", res.getStatusCode(), responseBody);
                        throw new AiServiceException("AI STT service failed with status " + res.getStatusCode() + ": " + responseBody);
                    })
                    .body(FastApiTranscriptResponse.class);

            validateResponse(response);
            return response;

        } catch (AiServiceException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to connect to AI STT service at {}: {}", serviceUrl, e.getMessage());
            throw new AiServiceException("Failed to communicate with AI STT service: " + e.getMessage(), e);
        }
    }

    private void validateResponse(FastApiTranscriptResponse response) {
        if (response == null) {
            throw new AiServiceException("AI STT service returned a null payload");
        }
        if (Double.isNaN(response.getConfidenceScore()) || Double.isInfinite(response.getConfidenceScore())) {
            throw new AiServiceException("AI STT service returned an invalid confidence score (NaN or Infinite)");
        }
        if (response.getConfidenceScore() < 0.0 || response.getConfidenceScore() > 1.0) {
            throw new AiServiceException("AI STT service returned an out-of-range confidence score: " + response.getConfidenceScore());
        }
        if (response.getSegments() == null) {
            throw new AiServiceException("AI STT service returned a null segments list");
        }
    }
}
