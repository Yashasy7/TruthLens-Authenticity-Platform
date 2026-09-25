package com.truthlens.backend.service.video;

import com.truthlens.backend.dto.FastApiVideoAnalysisResponse;
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
 * REST client implementation communicating with the internal Python FastAPI Video Service (Module 06).
 */
@Service
public class FastApiVideoAiServiceClient implements VideoAiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(FastApiVideoAiServiceClient.class);

    private final RestClient restClient;
    private final String serviceUrl;

    public FastApiVideoAiServiceClient(
            RestClient.Builder restClientBuilder,
            @Value("${truthlens.ai.service-url:http://localhost:8001}") String serviceUrl,
            @Value("${truthlens.ai.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${truthlens.ai.video-read-timeout-ms:60000}") int readTimeoutMs) {

        this.serviceUrl = serviceUrl;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        this.restClient = restClientBuilder
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();

        log.info("Initialized FastApiVideoAiServiceClient targeting {}", serviceUrl);
    }

    FastApiVideoAiServiceClient(RestClient restClient, String serviceUrl) {
        this.restClient = restClient;
        this.serviceUrl = serviceUrl;
    }

    @Override
    public FastApiVideoAnalysisResponse analyzeVideo(byte[] videoBytes, String filename, String contentType) {
        if (videoBytes == null || videoBytes.length == 0) {
            throw new IllegalArgumentException("Video bytes cannot be null or empty");
        }

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        ByteArrayResource fileResource = new ByteArrayResource(videoBytes) {
            @Override
            public String getFilename() {
                return (filename != null && !filename.isBlank()) ? filename : "video.mp4";
            }
        };
        body.add("file", fileResource);

        try {
            log.debug("Sending video analysis request to AI service at {} ({} bytes)", serviceUrl, videoBytes.length);

            FastApiVideoAnalysisResponse response = restClient.post()
                    .uri("/api/v1/analyze/video")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (req, res) -> {
                        String responseBody = new String(res.getBody().readAllBytes(), StandardCharsets.UTF_8);
                        log.error("AI video service error HTTP {}: {}", res.getStatusCode(), responseBody);
                        throw new AiServiceException("AI video service failed with status " + res.getStatusCode() + ": " + responseBody);
                    })
                    .body(FastApiVideoAnalysisResponse.class);

            validateResponse(response);
            return response;

        } catch (AiServiceException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to connect to AI video service at {}: {}", serviceUrl, e.getMessage());
            throw new AiServiceException("Failed to communicate with AI video service: " + e.getMessage(), e);
        }
    }

    private void validateResponse(FastApiVideoAnalysisResponse response) {
        if (response == null) {
            throw new AiServiceException("AI video service returned a null payload");
        }
        if (response.getDeepfakeProb() < 0.0 || response.getDeepfakeProb() > 1.0) {
            throw new AiServiceException("Invalid deepfake probability received: " + response.getDeepfakeProb());
        }
    }
}
