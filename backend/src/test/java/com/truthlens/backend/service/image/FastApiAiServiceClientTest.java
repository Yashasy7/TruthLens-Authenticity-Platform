package com.truthlens.backend.service.image;

import com.truthlens.backend.dto.FastApiImageAnalysisResponse;
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

@DisplayName("FastApiAiServiceClient — Unit Tests")
class FastApiAiServiceClientTest {

    private MockRestServiceServer mockServer;
    private FastApiAiServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost:8001");
        mockServer = MockRestServiceServer.bindTo(builder).build();
        RestClient restClient = builder.build();
        client = new FastApiAiServiceClient(restClient, "http://localhost:8001");
    }

    @Test
    @DisplayName("analyzeImage: successfully invokes FastAPI and parses response")
    void analyzeImage_success() {
        String responseJson = """
                {
                    "ai_prob": 0.85,
                    "manipulation_prob": 0.15,
                    "noise_variance": 12.4,
                    "fft_anomaly_score": 0.28,
                    "copy_move_detected": false,
                    "splicing_detected": false,
                    "model_name": "DiffusionClassifierNet",
                    "model_version": "TruthLens-DiffusionClassifier-0.1.0-dev",
                    "ela_heatmap_base64": "fake_ela",
                    "gradcam_heatmap_base64": "fake_gradcam",
                    "evidence": { "patchNoiseVariance": 0.04 },
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/image"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(responseJson, MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{1, 2, 3, 4};
        FastApiImageAnalysisResponse response = client.analyzeImage(fakeBytes, "test.jpg", "image/jpeg");

        assertThat(response).isNotNull();
        assertThat(response.getAiProb()).isEqualTo(0.85);
        assertThat(response.getManipulationProb()).isEqualTo(0.15);
        assertThat(response.getNoiseVariance()).isEqualTo(12.4);
        assertThat(response.getStatus()).isEqualTo("COMPLETED");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeImage: empty or null image bytes throws IllegalArgumentException")
    void analyzeImage_emptyBytes_throwsException() {
        assertThatThrownBy(() -> client.analyzeImage(new byte[0], "test.jpg", "image/jpeg"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Image bytes cannot be null or empty");
    }

    @Test
    @DisplayName("analyzeImage: downstream HTTP error status throws AiServiceException")
    void analyzeImage_serverError_throwsAiServiceException() {
        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/image"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body("{\"detail\":\"Internal Model Failure\"}")
                        .contentType(MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{1, 2, 3};
        assertThatThrownBy(() -> client.analyzeImage(fakeBytes, "test.jpg", "image/jpeg"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("AI service failed with status 500");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeImage: out-of-bounds probability throws AiServiceException")
    void analyzeImage_invalidProbability_throwsAiServiceException() {
        String invalidJson = """
                {
                    "ai_prob": 1.50,
                    "manipulation_prob": 0.10,
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/image"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(invalidJson, MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{1, 2, 3};
        assertThatThrownBy(() -> client.analyzeImage(fakeBytes, "test.jpg", "image/jpeg"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("Invalid ai_prob");

        mockServer.verify();
    }
}
