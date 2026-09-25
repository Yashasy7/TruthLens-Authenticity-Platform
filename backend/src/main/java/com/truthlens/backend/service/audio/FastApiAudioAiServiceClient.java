package com.truthlens.backend.service.audio;

import com.truthlens.backend.dto.FastApiAudioAnalysisResponse;
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
 * REST client implementation communicating with the internal Python FastAPI Audio Service (Module 07).
 */
@Service
public class FastApiAudioAiServiceClient implements AudioAiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(FastApiAudioAiServiceClient.class);

    private final RestClient restClient;
    private final String serviceUrl;

    public FastApiAudioAiServiceClient(
            RestClient.Builder restClientBuilder,
            @Value("${truthlens.ai.service-url:http://localhost:8001}") String serviceUrl,
            @Value("${truthlens.ai.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${truthlens.ai.audio-read-timeout-ms:60000}") int readTimeoutMs) {

        this.serviceUrl = serviceUrl;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        this.restClient = restClientBuilder
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();

        log.info("Initialized FastApiAudioAiServiceClient targeting {}", serviceUrl);
    }

    FastApiAudioAiServiceClient(RestClient restClient, String serviceUrl) {
        this.restClient = restClient;
        this.serviceUrl = serviceUrl;
    }

    @Override
    public FastApiAudioAnalysisResponse analyzeAudio(byte[] audioBytes, String filename, String contentType) {
        if (audioBytes == null || audioBytes.length == 0) {
            throw new IllegalArgumentException("Audio bytes cannot be null or empty");
        }

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        ByteArrayResource fileResource = new ByteArrayResource(audioBytes) {
            @Override
            public String getFilename() {
                return (filename != null && !filename.isBlank()) ? filename : "audio.wav";
            }
        };
        body.add("file", fileResource);

        try {
            log.debug("Sending audio analysis request to AI service at {} ({} bytes)", serviceUrl, audioBytes.length);

            FastApiAudioAnalysisResponse response = restClient.post()
                    .uri("/api/v1/analyze/audio")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (req, res) -> {
                        String responseBody = new String(res.getBody().readAllBytes(), StandardCharsets.UTF_8);
                        log.error("AI audio service error HTTP {}: {}", res.getStatusCode(), responseBody);
                        throw new AiServiceException("AI audio service failed with status " + res.getStatusCode() + ": " + responseBody);
                    })
                    .body(FastApiAudioAnalysisResponse.class);

            validateResponse(response);
            return response;

        } catch (AiServiceException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to connect to AI audio service at {}: {}", serviceUrl, e.getMessage());
            throw new AiServiceException("Failed to communicate with AI audio service: " + e.getMessage(), e);
        }
    }

    private void validateResponse(FastApiAudioAnalysisResponse response) {
        if (response == null) {
            throw new AiServiceException("AI audio service returned a null payload");
        }
        if (response.getSyntheticVoiceProb() < 0.0 || response.getSyntheticVoiceProb() > 1.0) {
            throw new AiServiceException("Invalid synthetic voice probability received: " + response.getSyntheticVoiceProb());
        }
    }
}
