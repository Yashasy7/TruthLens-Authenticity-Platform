package com.truthlens.backend.service.claim;

import com.truthlens.backend.dto.FastApiClaimRequest;
import com.truthlens.backend.dto.FastApiClaimResponse;
import com.truthlens.backend.exception.AiServiceException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * REST client implementation communicating with the internal Python FastAPI Text & Claim Analysis Service (Module 11).
 */
@Service
public class FastApiClaimServiceClient implements ClaimAiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(FastApiClaimServiceClient.class);

    private final RestClient restClient;
    private final String serviceUrl;

    public FastApiClaimServiceClient(
            RestClient.Builder restClientBuilder,
            @Value("${truthlens.ai.service-url:http://localhost:8001}") String serviceUrl,
            @Value("${truthlens.ai.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${truthlens.ai.claim-read-timeout-ms:30000}") int readTimeoutMs) {

        this.serviceUrl = serviceUrl;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        this.restClient = restClientBuilder
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();

        log.info("Initialized FastApiClaimServiceClient targeting {}", serviceUrl);
    }

    FastApiClaimServiceClient(RestClient restClient, String serviceUrl) {
        this.restClient = restClient;
        this.serviceUrl = serviceUrl;
    }

    @Override
    public FastApiClaimResponse analyzeClaims(String text, String sourceType, String language) {
        if (text == null) {
            throw new IllegalArgumentException("Text cannot be null");
        }

        FastApiClaimRequest request = new FastApiClaimRequest(text, sourceType, language);

        try {
            log.debug("Sending Text & Claim Analysis request to AI service at {} ({} chars)", serviceUrl, text.length());

            FastApiClaimResponse response = restClient.post()
                    .uri("/api/v1/analyze/claims")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(request)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, (req, res) -> {
                        String responseBody = new String(res.getBody().readAllBytes(), StandardCharsets.UTF_8);
                        log.error("AI Claim service error HTTP {}: {}", res.getStatusCode(), responseBody);
                        throw new AiServiceException(
                                "AI Claim service returned HTTP " + res.getStatusCode() + ": " + responseBody
                        );
                    })
                    .body(FastApiClaimResponse.class);

            if (response == null) {
                throw new AiServiceException("AI Claim service returned an empty response");
            }

            log.debug("Successfully received Claim Analysis findings with {} claims", response.getClaimsCount());
            return response;

        } catch (AiServiceException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to communicate with AI Claim service at {}: {}", serviceUrl, e.getMessage(), e);
            throw new AiServiceException("Failed to reach AI Claim service: " + e.getMessage(), e);
        }
    }
}
