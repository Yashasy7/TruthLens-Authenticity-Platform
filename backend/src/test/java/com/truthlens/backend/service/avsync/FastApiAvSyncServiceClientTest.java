package com.truthlens.backend.service.avsync;

import com.truthlens.backend.dto.FastApiAvSyncResponse;
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

@DisplayName("FastApiAvSyncServiceClient — Unit Tests")
class FastApiAvSyncServiceClientTest {

    private MockRestServiceServer mockServer;
    private FastApiAvSyncServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost:8001");
        mockServer = MockRestServiceServer.bindTo(builder).build();
        RestClient restClient = builder.build();
        client = new FastApiAvSyncServiceClient(restClient, "http://localhost:8001");
    }

    @Test
    @DisplayName("analyzeAvSync: successfully invokes FastAPI and parses response")
    void analyzeAvSync_success() {
        String responseJson = """
                {
                    "sync_score": 0.88,
                    "lip_offset_ms": -15.5,
                    "confidence": 0.92,
                    "mismatch_segments": [
                        {
                            "start_time": 1.2,
                            "end_time": 2.5,
                            "offset_ms": -15.5,
                            "confidence": 0.85,
                            "reason": "Slight localized offset"
                        }
                    ],
                    "model_name": "TruthLens-PyTorch-SyncNet-DualStream",
                    "model_version": "TruthLens-SyncNet-v1.0-dev",
                    "evidence": {
                        "detected_faces_count": 1,
                        "selected_face_track_id": 1,
                        "video_duration_seconds": 3.0,
                        "audio_duration_seconds": 3.0,
                        "fps": 25.0,
                        "envelope_correlation": 0.86,
                        "syncnet_min_distance": 0.38,
                        "syncnet_confidence": 0.89,
                        "tracking_stability": 0.95,
                        "is_development_model": true,
                        "details": {}
                    },
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/av-sync"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(responseJson, MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{0, 0, 0, 20, 102, 116, 121, 112}; // MP4 ftyp header
        FastApiAvSyncResponse response = client.analyzeAvSync(fakeBytes, "test.mp4", "video/mp4");

        assertThat(response).isNotNull();
        assertThat(response.getSyncScore()).isEqualTo(0.88);
        assertThat(response.getLipOffsetMs()).isEqualTo(-15.5);
        assertThat(response.getConfidence()).isEqualTo(0.92);
        assertThat(response.getMismatchSegments()).hasSize(1);
        assertThat(response.getStatus()).isEqualTo("COMPLETED");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeAvSync: empty or null video bytes throws IllegalArgumentException")
    void analyzeAvSync_emptyBytes_throwsException() {
        assertThatThrownBy(() -> client.analyzeAvSync(new byte[0], "test.mp4", "video/mp4"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Video bytes cannot be null or empty");
    }

    @Test
    @DisplayName("analyzeAvSync: downstream HTTP error status throws AiServiceException")
    void analyzeAvSync_httpError_throwsAiServiceException() {
        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/av-sync"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.BAD_REQUEST).body("{\"detail\":\"Video contains no audio stream\"}"));

        byte[] fakeBytes = new byte[]{0, 0, 0, 20, 102, 116, 121, 112};
        assertThatThrownBy(() -> client.analyzeAvSync(fakeBytes, "test.mp4", "video/mp4"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("AI AV sync service failed with status 400");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeAvSync: out of range sync score throws AiServiceException")
    void analyzeAvSync_outOfRangeScore_throwsAiServiceException() {
        String invalidJson = """
                {
                    "sync_score": 1.45,
                    "lip_offset_ms": 0.0,
                    "confidence": 0.8,
                    "mismatch_segments": [],
                    "model_name": "TestModel",
                    "model_version": "v1",
                    "evidence": {
                        "detected_faces_count": 1,
                        "selected_face_track_id": 1,
                        "video_duration_seconds": 1.0,
                        "audio_duration_seconds": 1.0,
                        "fps": 25.0,
                        "envelope_correlation": 0.5,
                        "syncnet_min_distance": 0.5,
                        "syncnet_confidence": 0.5,
                        "tracking_stability": 1.0,
                        "is_development_model": true,
                        "details": {}
                    },
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/av-sync"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(invalidJson, MediaType.APPLICATION_JSON));

        byte[] fakeBytes = new byte[]{0, 0, 0, 20, 102, 116, 121, 112};
        assertThatThrownBy(() -> client.analyzeAvSync(fakeBytes, "test.mp4", "video/mp4"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("out-of-range sync score");

        mockServer.verify();
    }
}
