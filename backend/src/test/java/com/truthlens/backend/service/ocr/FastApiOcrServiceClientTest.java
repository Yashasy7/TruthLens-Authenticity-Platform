package com.truthlens.backend.service.ocr;

import com.truthlens.backend.dto.FastApiOcrResponse;
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

class FastApiOcrServiceClientTest {

    private static final String BASE_URL = "http://localhost:8001";

    private MockRestServiceServer mockServer;
    private FastApiOcrServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl(BASE_URL);
        mockServer = MockRestServiceServer.bindTo(builder).build();
        client = new FastApiOcrServiceClient(builder.build(), BASE_URL);
    }

    @Test
    @DisplayName("analyzeOcr: successful response is parsed into FastApiOcrResponse")
    void analyzeOcr_success_returnsParsedResponse() {
        String jsonResponse = """
            {
                "extracted_text": "TRUTHLENS FACT CHECK",
                "language": "en",
                "confidence_score": 0.94,
                "regions_count": 1,
                "regions": [
                    {
                        "text": "TRUTHLENS FACT CHECK",
                        "confidence": 0.94,
                        "bounding_box": {
                            "x": 20, "y": 40, "width": 200, "height": 30,
                            "normalized_bbox": [0.05, 0.1, 0.5, 0.08],
                            "polygon": [[20, 40], [220, 40], [220, 70], [20, 70]]
                        },
                        "language": "en"
                    }
                ],
                "evidence": {
                    "total_regions": 1,
                    "image_width": 400,
                    "image_height": 300,
                    "engine_used": "EasyOCR"
                },
                "status": "COMPLETED"
            }
            """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/ocr"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(jsonResponse, MediaType.APPLICATION_JSON));

        FastApiOcrResponse response = client.analyzeOcr("sample data".getBytes(), "image.png", "image/png");

        assertThat(response).isNotNull();
        assertThat(response.getExtractedText()).isEqualTo("TRUTHLENS FACT CHECK");
        assertThat(response.getLanguage()).isEqualTo("en");
        assertThat(response.getConfidenceScore()).isEqualTo(0.94);
        assertThat(response.getRegionsCount()).isEqualTo(1);
        assertThat(response.getRegions()).hasSize(1);
        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeOcr: null or empty media bytes throws IllegalArgumentException")
    void analyzeOcr_emptyBytes_throwsIllegalArgument() {
        assertThatThrownBy(() -> client.analyzeOcr(new byte[0], "test.png", "image/png"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("analyzeOcr: HTTP 500 error from AI service throws AiServiceException")
    void analyzeOcr_serverError_throwsAiServiceException() {
        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/ocr"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body("{\"detail\":\"Internal Pipeline Failure\"}")
                        .contentType(MediaType.APPLICATION_JSON));

        assertThatThrownBy(() -> client.analyzeOcr("bytes".getBytes(), "image.png", "image/png"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("AI OCR service failed with status 500");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeOcr: invalid out-of-range confidence score throws AiServiceException")
    void analyzeOcr_invalidScore_throwsAiServiceException() {
        String jsonResponse = """
            {
                "extracted_text": "INVALID",
                "language": "en",
                "confidence_score": 1.5,
                "regions_count": 0,
                "regions": [],
                "status": "COMPLETED"
            }
            """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/ocr"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(jsonResponse, MediaType.APPLICATION_JSON));

        assertThatThrownBy(() -> client.analyzeOcr("bytes".getBytes(), "image.png", "image/png"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("out-of-range confidence score");

        mockServer.verify();
    }
}
