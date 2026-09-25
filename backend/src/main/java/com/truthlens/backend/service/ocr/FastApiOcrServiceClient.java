package com.truthlens.backend.service.ocr;

import com.truthlens.backend.dto.FastApiOcrResponse;
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
 * REST client implementation communicating with the internal Python FastAPI OCR Service (Module 09).
 */
@Service
public class FastApiOcrServiceClient implements OcrAiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(FastApiOcrServiceClient.class);

    private final RestClient restClient;
    private final String serviceUrl;

    public FastApiOcrServiceClient(
            RestClient.Builder restClientBuilder,
            @Value("${truthlens.ai.service-url:http://localhost:8001}") String serviceUrl,
            @Value("${truthlens.ai.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${truthlens.ai.ocr-read-timeout-ms:30000}") int readTimeoutMs) {

        this.serviceUrl = serviceUrl;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        this.restClient = restClientBuilder
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();

        log.info("Initialized FastApiOcrServiceClient targeting {}", serviceUrl);
    }

    FastApiOcrServiceClient(RestClient restClient, String serviceUrl) {
        this.restClient = restClient;
        this.serviceUrl = serviceUrl;
    }

    @Override
    public FastApiOcrResponse analyzeOcr(byte[] mediaBytes, String filename, String contentType) {
        if (mediaBytes == null || mediaBytes.length == 0) {
            throw new IllegalArgumentException("Media bytes cannot be null or empty");
        }

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        ByteArrayResource fileResource = new ByteArrayResource(mediaBytes) {
            @Override
            public String getFilename() {
                return (filename != null && !filename.isBlank()) ? filename : "media.png";
            }
        };
        body.add("file", fileResource);

        try {
            log.debug("Sending OCR text extraction request to AI service at {} ({} bytes)", serviceUrl, mediaBytes.length);

            FastApiOcrResponse response = restClient.post()
                    .uri("/api/v1/analyze/ocr")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (req, res) -> {
                        String responseBody = new String(res.getBody().readAllBytes(), StandardCharsets.UTF_8);
                        log.error("AI OCR service error HTTP {}: {}", res.getStatusCode(), responseBody);
                        throw new AiServiceException("AI OCR service failed with status " + res.getStatusCode() + ": " + responseBody);
                    })
                    .body(FastApiOcrResponse.class);

            validateResponse(response);
            return response;

        } catch (AiServiceException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to connect to AI OCR service at {}: {}", serviceUrl, e.getMessage());
            throw new AiServiceException("Failed to communicate with AI OCR service: " + e.getMessage(), e);
        }
    }

    private void validateResponse(FastApiOcrResponse response) {
        if (response == null) {
            throw new AiServiceException("AI OCR service returned a null payload");
        }
        if (Double.isNaN(response.getConfidenceScore()) || Double.isInfinite(response.getConfidenceScore())) {
            throw new AiServiceException("AI OCR service returned an invalid confidence score (NaN or Infinite)");
        }
        if (response.getConfidenceScore() < 0.0 || response.getConfidenceScore() > 1.0) {
            throw new AiServiceException("AI OCR service returned an out-of-range confidence score: " + response.getConfidenceScore());
        }
        if (response.getRegions() == null) {
            throw new AiServiceException("AI OCR service returned a null regions list");
        }
    }
}
