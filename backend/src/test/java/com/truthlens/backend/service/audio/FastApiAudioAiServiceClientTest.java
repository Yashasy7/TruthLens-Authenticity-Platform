package com.truthlens.backend.service.audio;

import com.truthlens.backend.dto.FastApiAudioAnalysisResponse;
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

@DisplayName("FastApiAudioAiServiceClient — Unit Tests")
class FastApiAudioAiServiceClientTest {

    private MockRestServiceServer mockServer;
    private FastApiAudioAiServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost:8001");
        mockServer = MockRestServiceServer.bindTo(builder).build();
        RestClient restClient = builder.build();
        client = new FastApiAudioAiServiceClient(restClient, "http://localhost:8001");
    }

    @Test
    @DisplayName("analyzeAudio: successfully invokes FastAPI and parses response")
    void analyzeAudio_success() {
        String responseJson = """
                {
                    "synthetic_voice_prob": 0.8250,
                    "spectrogram_url": "/artifacts/spec_01.png",
                    "spectrogram_base64": "iVBORw0KGgoAAAANSUhEUg==",
                    "pitch_variance": 128.45,
                    "splice_markers": [
                        {
                            "timestamp_seconds": 1.45,
                            "score": 0.88,
                            "reason": "SPECTRAL_FLUX_JUMP"
                        }
                    ],
                    "model_name": "TruthLens-PyTorch-AASIST-AudioClassifier",
                    "model_version": "0.1.0-dev",
                    "evidence": {
                        "duration_seconds": 3.2,
                        "pitch_mean": 215.4,
                        "pitch_variance": 128.45,
                        "spectral_centroid_mean": 1850.2,
                        "spectral_bandwidth_mean": 1420.5,
                        "spectral_rolloff_mean": 3800.0,
                        "zero_crossing_rate_mean": 0.082,
                        "phase_discontinuity_score": 0.65,
                        "splice_markers": [],
                        "details": {}
                    },
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/audio"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(responseJson, MediaType.APPLICATION_JSON));

        byte[] dummyAudio = new byte[]{1, 2, 3, 4, 5};
        FastApiAudioAnalysisResponse response = client.analyzeAudio(dummyAudio, "test.wav", "audio/wav");

        mockServer.verify();
        assertThat(response).isNotNull();
        assertThat(response.getSyntheticVoiceProb()).isEqualTo(0.8250);
        assertThat(response.getSpectrogramUrl()).isEqualTo("/artifacts/spec_01.png");
        assertThat(response.getPitchVariance()).isEqualTo(128.45);
        assertThat(response.getModelName()).isEqualTo("TruthLens-PyTorch-AASIST-AudioClassifier");
        assertThat(response.getSpliceMarkers()).hasSize(1);
        assertThat(response.getSpliceMarkers().get(0).reason()).isEqualTo("SPECTRAL_FLUX_JUMP");
    }

    @Test
    @DisplayName("analyzeAudio: rejects null or empty byte payload")
    void analyzeAudio_nullOrEmptyBytes() {
        assertThatThrownBy(() -> client.analyzeAudio(null, "test.wav", "audio/wav"))
                .isInstanceOf(IllegalArgumentException.class);

        assertThatThrownBy(() -> client.analyzeAudio(new byte[0], "test.wav", "audio/wav"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("analyzeAudio: server error throws AiServiceException")
    void analyzeAudio_serverError_throwsAiServiceException() {
        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/audio"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body("{\"detail\":\"Inference memory error\"}")
                        .contentType(MediaType.APPLICATION_JSON));

        byte[] dummyAudio = new byte[]{1, 2, 3};
        assertThatThrownBy(() -> client.analyzeAudio(dummyAudio, "test.wav", "audio/wav"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("AI audio service failed with status 500");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeAudio: invalid probability throws AiServiceException")
    void analyzeAudio_invalidProbability_throwsAiServiceException() {
        String invalidJson = """
                {
                    "synthetic_voice_prob": 1.45,
                    "pitch_variance": 50.0,
                    "model_name": "AASIST",
                    "model_version": "0.1.0-dev",
                    "status": "COMPLETED"
                }
                """;

        mockServer.expect(requestTo("http://localhost:8001/api/v1/analyze/audio"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(invalidJson, MediaType.APPLICATION_JSON));

        byte[] dummyAudio = new byte[]{1, 2, 3};
        assertThatThrownBy(() -> client.analyzeAudio(dummyAudio, "test.wav", "audio/wav"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("Invalid synthetic voice probability");

        mockServer.verify();
    }
}
