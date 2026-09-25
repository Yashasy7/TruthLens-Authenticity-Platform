package com.truthlens.backend.service.image;

import com.truthlens.backend.dto.FastApiImageAnalysisResponse;
import com.truthlens.backend.exception.AiServiceException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
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
 * REST client implementation invoking the internal Python FastAPI Vision Service.
 */
@Service
public class FastApiAiServiceClient implements AiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(FastApiAiServiceClient.class);

    private final RestClient restClient;
    private final String serviceUrl;

    @Autowired
    public FastApiAiServiceClient(
            RestClient.Builder restClientBuilder,
            @Value("${truthlens.ai.service-url:http://localhost:8001}") String serviceUrl,
            @Value("${truthlens.ai.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${truthlens.ai.read-timeout-ms:30000}") int readTimeoutMs) {

        this.serviceUrl = serviceUrl;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        this.restClient = restClientBuilder
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();

        log.info("Initialized FastApiAiServiceClient targeting {}", serviceUrl);
    }

    FastApiAiServiceClient(RestClient restClient, String serviceUrl) {
        this.restClient = restClient;
        this.serviceUrl = serviceUrl;
    }

    @Override
    public FastApiImageAnalysisResponse analyzeImage(byte[] imageBytes, String filename, String contentType) {
        if (imageBytes == null || imageBytes.length == 0) {
            throw new IllegalArgumentException("Image bytes cannot be null or empty");
        }

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        ByteArrayResource fileResource = new ByteArrayResource(imageBytes) {
            @Override
            public String getFilename() {
                return (filename != null && !filename.isBlank()) ? filename : "image.jpg";
            }
        };
        body.add("file", fileResource);

        try {
            log.debug("Sending image analysis request to AI service at {} ({} bytes)", serviceUrl, imageBytes.length);

            FastApiImageAnalysisResponse response = restClient.post()
                    .uri("/api/v1/analyze/image")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (req, res) -> {
                        String responseBody = new String(res.getBody().readAllBytes(), StandardCharsets.UTF_8);
                        log.error("AI service error HTTP {}: {}", res.getStatusCode(), responseBody);
                        throw new AiServiceException("AI service failed with status " + res.getStatusCode() + ": " + responseBody);
                    })
                    .body(FastApiImageAnalysisResponse.class);

            validateResponse(response);
            return response;

        } catch (AiServiceException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to connect to AI vision service at {}: {}", serviceUrl, e.getMessage());
            throw new AiServiceException("Failed to communicate with AI vision service: " + e.getMessage(), e);
        }
    }

    private void validateResponse(FastApiImageAnalysisResponse response) {
        if (response == null) {
            throw new AiServiceException("AI service returned a null payload");
        }
        if (response.getAiProb() < 0.0 || response.getAiProb() > 1.0) {
            throw new AiServiceException("Invalid ai_prob from AI service: " + response.getAiProb());
        }
        if (response.getManipulationProb() < 0.0 || response.getManipulationProb() > 1.0) {
            throw new AiServiceException("Invalid manipulation_prob from AI service: " + response.getManipulationProb());
        }
        if (response.getStatus() == null || response.getStatus().isBlank()) {
            throw new AiServiceException("AI service returned empty status");
        }
    }
}
