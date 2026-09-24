package com.truthlens.backend.service.avsync;

import com.truthlens.backend.dto.FastApiAvSyncResponse;
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
 * REST client implementation communicating with the internal Python FastAPI AV Sync Service (Module 08).
 */
@Service
public class FastApiAvSyncServiceClient implements AvSyncAiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(FastApiAvSyncServiceClient.class);

    private final RestClient restClient;
    private final String serviceUrl;

    public FastApiAvSyncServiceClient(
            RestClient.Builder restClientBuilder,
            @Value("${truthlens.ai.service-url:http://localhost:8001}") String serviceUrl,
            @Value("${truthlens.ai.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${truthlens.ai.av-sync-read-timeout-ms:60000}") int readTimeoutMs) {

        this.serviceUrl = serviceUrl;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        this.restClient = restClientBuilder
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();

        log.info("Initialized FastApiAvSyncServiceClient targeting {}", serviceUrl);
    }

    FastApiAvSyncServiceClient(RestClient restClient, String serviceUrl) {
        this.restClient = restClient;
        this.serviceUrl = serviceUrl;
    }

    @Override
    public FastApiAvSyncResponse analyzeAvSync(byte[] videoBytes, String filename, String contentType) {
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
            log.debug("Sending AV sync analysis request to AI service at {} ({} bytes)", serviceUrl, videoBytes.length);

            FastApiAvSyncResponse response = restClient.post()
                    .uri("/api/v1/analyze/av-sync")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (req, res) -> {
                        String responseBody = new String(res.getBody().readAllBytes(), StandardCharsets.UTF_8);
                        log.error("AI AV sync service error HTTP {}: {}", res.getStatusCode(), responseBody);
                        throw new AiServiceException("AI AV sync service failed with status " + res.getStatusCode() + ": " + responseBody);
                    })
                    .body(FastApiAvSyncResponse.class);

            validateResponse(response);
            return response;

        } catch (AiServiceException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to connect to AI AV sync service at {}: {}", serviceUrl, e.getMessage());
            throw new AiServiceException("Failed to communicate with AI AV sync service: " + e.getMessage(), e);
        }
    }

    private void validateResponse(FastApiAvSyncResponse response) {
        if (response == null) {
            throw new AiServiceException("AI AV sync service returned a null payload");
        }
        if (Double.isNaN(response.getSyncScore()) || Double.isInfinite(response.getSyncScore())) {
            throw new AiServiceException("AI AV sync service returned an invalid sync score (NaN or Infinite)");
        }
        if (response.getSyncScore() < 0.0 || response.getSyncScore() > 1.0) {
            throw new AiServiceException("AI AV sync service returned an out-of-range sync score: " + response.getSyncScore());
        }
        if (Double.isNaN(response.getLipOffsetMs()) || Double.isInfinite(response.getLipOffsetMs())) {
            throw new AiServiceException("AI AV sync service returned an invalid lip offset (NaN or Infinite)");
        }
        if (Double.isNaN(response.getConfidence()) || Double.isInfinite(response.getConfidence())) {
            throw new AiServiceException("AI AV sync service returned an invalid confidence score (NaN or Infinite)");
        }
    }
}
