package com.truthlens.backend.service.video;

import com.truthlens.backend.dto.FastApiVideoAnalysisResponse;
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

@DisplayName("FastApiVideoAiServiceClient — Unit Tests")
class FastApiVideoAiServiceClientTest {

    private MockRestServiceServer mockServer;
    private FastApiVideoAiServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost:8001");
        mockServer = MockRestServiceServer.bindTo(builder).build();
        RestClient restClient = builder.build();
        client = new FastApiVideoAiServiceClient(restClient, "http://localhost:8001");
    }

    @Test
    @DisplayName("analyzeVideo: successfully invokes FastAPI and parses response")
    void analyzeVideo_success() {
        String responseJson = """
                {
                    "deepfake_prob": 0.88,
                    "face_count": 2,
                    "total_frames_sampled": 12,
                    "suspicious_timestamps": [
                        {
                            "timestamp_seconds": 2.0,
                            "frame_index": 4,
                            "score": 0.91,
                            "reason": "HIGH_SYNTHETIC_FACE_PROBABILITY"
                        }
                    ],
                    "frame_scores": [
                        {
                            "frame_index": 4,
                            "timestamp_seconds": 2.0,
                            "deepfake_score": 0.91,
                            "temporal_inconsistency": 0.75,
                            "faces_detected": 2,
                            "is_suspicious": true
                        }
                    ],
                    "model_name": "TruthLens-VideoDeepfakeClassifier",
                    "model_version": "TruthLens-VideoDeepfakeClassifier-0.1.0-dev",
                    "evidence": {
                        "face_count": 2,
                        "total_frames_sampled": 12,
                        "duration_seconds": 6.0,
                        "frame_scores": [],
                        "suspicious_timestamps": [],
                        "details": {}
                    },
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/video"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(responseJson, MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{0, 0, 0, 20, 102, 116, 121, 112}; // MP4 ftyp header
        FastApiVideoAnalysisResponse response = client.analyzeVideo(fakeBytes, "test.mp4", "video/mp4");

        assertThat(response).isNotNull();
        assertThat(response.getDeepfakeProb()).isEqualTo(0.88);
        assertThat(response.getFaceCount()).isEqualTo(2);
        assertThat(response.getTotalFramesSampled()).isEqualTo(12);
        assertThat(response.getStatus()).isEqualTo("COMPLETED");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeVideo: empty or null video bytes throws IllegalArgumentException")
    void analyzeVideo_emptyBytes_throwsException() {
        assertThatThrownBy(() -> client.analyzeVideo(new byte[0], "test.mp4", "video/mp4"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Video bytes cannot be null or empty");
    }

    @Test
    @DisplayName("analyzeVideo: downstream HTTP error status throws AiServiceException")
    void analyzeVideo_serverError_throwsAiServiceException() {
        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/video"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body("{\"detail\":\"Internal Video Pipeline Failure\"}")
                        .contentType(MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{1, 2, 3};
        assertThatThrownBy(() -> client.analyzeVideo(fakeBytes, "test.mp4", "video/mp4"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("AI video service failed with status 500");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeVideo: out-of-bounds probability throws AiServiceException")
    void analyzeVideo_invalidProbability_throwsAiServiceException() {
        String invalidJson = """
                {
                    "deepfake_prob": 1.5,
                    "face_count": 1,
                    "total_frames_sampled": 10,
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/video"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(invalidJson, MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{1, 2, 3};
        assertThatThrownBy(() -> client.analyzeVideo(fakeBytes, "test.mp4", "video/mp4"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("Invalid deepfake probability received: 1.5");

        mockServer.verify();
    }
}
