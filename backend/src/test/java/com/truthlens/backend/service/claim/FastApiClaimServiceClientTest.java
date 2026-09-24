package com.truthlens.backend.service.claim;

import com.truthlens.backend.dto.FastApiClaimResponse;
import com.truthlens.backend.exception.AiServiceException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class FastApiClaimServiceClientTest {

    private static final String BASE_URL = "http://localhost:8001";

    private MockRestServiceServer mockServer;
    private FastApiClaimServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl(BASE_URL);
        mockServer = MockRestServiceServer.bindTo(builder).build();
        client = new FastApiClaimServiceClient(builder.build(), BASE_URL);
    }

    @Test
    @DisplayName("analyzeClaims: successful response is parsed into FastApiClaimResponse")
    void analyzeClaims_success_returnsParsedResponse() {
        String jsonResponse = """
            {
                "text": "The Prime Minister announced a $5 billion stimulus in London on Monday.",
                "source_type": "TRANSCRIPT",
                "sentences_count": 1,
                "claims_count": 1,
                "claims": [
                    {
                        "claim_text": "The Prime Minister announced a $5 billion stimulus in London on Monday.",
                        "normalized_claim_text": "the prime minister announced a $5 billion stimulus in london on monday.",
                        "claim_type": "FACTUAL_CLAIM",
                        "subject": "The Prime Minister",
                        "action": "announced",
                        "value": "a $5 billion stimulus",
                        "entity_type": "MONEY",
                        "confidence_score": 0.95,
                        "claim_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
                        "sentence_index": 0,
                        "start_char": 0,
                        "end_char": 71,
                        "entities": [
                            {"text": "London", "label": "GPE", "normalized_label": "LOCATION", "start_char": 53, "end_char": 59}
                        ]
                    }
                ],
                "entities": [
                    {"text": "London", "label": "GPE", "normalized_label": "LOCATION", "start_char": 53, "end_char": 59}
                ],
                "evidence": {
                    "model_name": "spaCy-en_core_web_sm",
                    "sentences_count": 1,
                    "claims_count": 1,
                    "entities_count": 1,
                    "duration_seconds": 0.05,
                    "details": {}
                },
                "status": "COMPLETED",
                "error_message": null
            }
            """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/claims"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(jsonResponse, MediaType.APPLICATION_JSON));

        FastApiClaimResponse response = client.analyzeClaims("The Prime Minister announced a $5 billion stimulus in London on Monday.", "TRANSCRIPT", "en");

        mockServer.verify();
        assertThat(response).isNotNull();
        assertThat(response.getClaimsCount()).isEqualTo(1);
        assertThat(response.getClaims()).hasSize(1);
        assertThat(response.getClaims().get(0).getClaimType()).isEqualTo("FACTUAL_CLAIM");
        assertThat(response.getClaims().get(0).getSubject()).isEqualTo("The Prime Minister");
        assertThat(response.getClaims().get(0).getAction()).isEqualTo("announced");
        assertThat(response.getClaims().get(0).getClaimHash()).isEqualTo("a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0");
    }

    @Test
    @DisplayName("analyzeClaims: 500 error from AI service throws AiServiceException")
    void analyzeClaims_serverError_throwsAiServiceException() {
        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/claims"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                        .contentType(MediaType.APPLICATION_JSON)
                        .body("{\"detail\":\"Internal NLP Pipeline Failure\"}"));

        assertThatThrownBy(() -> client.analyzeClaims("Some text", "DIRECT_TEXT", "en"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("AI Claim service returned HTTP 500");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeClaims: null text throws IllegalArgumentException")
    void analyzeClaims_nullText_throwsException() {
        assertThatThrownBy(() -> client.analyzeClaims(null, "DIRECT_TEXT", "en"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Text cannot be null");
    }
}
