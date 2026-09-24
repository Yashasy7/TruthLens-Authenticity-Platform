package com.truthlens.backend.service.stt;

import com.truthlens.backend.dto.FastApiTranscriptResponse;
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

class FastApiTranscriptServiceClientTest {

    private static final String BASE_URL = "http://localhost:8001";

    private MockRestServiceServer mockServer;
    private FastApiTranscriptServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl(BASE_URL);
        mockServer = MockRestServiceServer.bindTo(builder).build();
        client = new FastApiTranscriptServiceClient(builder.build(), BASE_URL);
    }

    @Test
    @DisplayName("analyzeSpeechToText: successful response is parsed into FastApiTranscriptResponse")
    void analyzeSpeechToText_success_returnsParsedResponse() {
        String jsonResponse = """
            {
                "full_text": "Good morning TruthLens audio verification.",
                "language": "en",
                "confidence_score": 0.95,
                "duration_seconds": 3.2,
                "segments_count": 1,
                "words_count": 5,
                "segments": [
                    {
                        "id": 0,
                        "seek": 0,
                        "start": 0.0,
                        "end": 3.2,
                        "text": "Good morning TruthLens audio verification.",
                        "tokens": [101, 102],
                        "temperature": 0.0,
                        "avg_logprob": -0.05,
                        "compression_ratio": 1.2,
                        "no_speech_prob": 0.01,
                        "confidence": 0.95,
                        "words": [
                            {"word": "Good", "start": 0.0, "end": 0.5, "probability": 0.98},
                            {"word": "morning", "start": 0.5, "end": 1.1, "probability": 0.96}
                        ]
                    }
                ],
                "evidence": {
                    "model_name": "Faster-Whisper",
                    "model_size": "tiny",
                    "compute_type": "int8",
                    "device": "cpu",
                    "detected_language": "en",
                    "language_probability": 0.99,
                    "duration_seconds": 3.2,
                    "audio_sample_rate": 16000,
                    "media_type": "AUDIO"
                },
                "status": "COMPLETED"
            }
            """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/speech-to-text"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(jsonResponse, MediaType.APPLICATION_JSON));

        FastApiTranscriptResponse response = client.analyzeSpeechToText("audio bytes".getBytes(), "speech.wav", "audio/wav");

        assertThat(response).isNotNull();
        assertThat(response.getFullText()).isEqualTo("Good morning TruthLens audio verification.");
        assertThat(response.getLanguage()).isEqualTo("en");
        assertThat(response.getConfidenceScore()).isEqualTo(0.95);
        assertThat(response.getDurationSeconds()).isEqualTo(3.2);
        assertThat(response.getSegmentsCount()).isEqualTo(1);
        assertThat(response.getWordsCount()).isEqualTo(5);
        assertThat(response.getSegments()).hasSize(1);
        assertThat(response.getSegments().get(0).getWords()).hasSize(2);
        assertThat(response.getEvidence().getModelName()).isEqualTo("Faster-Whisper");
        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeSpeechToText: null or empty media bytes throws IllegalArgumentException")
    void analyzeSpeechToText_emptyBytes_throwsIllegalArgument() {
        assertThatThrownBy(() -> client.analyzeSpeechToText(new byte[0], "speech.wav", "audio/wav"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("analyzeSpeechToText: HTTP 500 error from AI service throws AiServiceException")
    void analyzeSpeechToText_serverError_throwsAiServiceException() {
        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/speech-to-text"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body("{\"detail\":\"Internal ASR Engine Failure\"}")
                        .contentType(MediaType.APPLICATION_JSON));

        assertThatThrownBy(() -> client.analyzeSpeechToText("bytes".getBytes(), "speech.wav", "audio/wav"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("AI STT service failed with status 500");

        mockServer.verify();
    }

    @Test
    @DisplayName("analyzeSpeechToText: invalid out-of-range confidence score throws AiServiceException")
    void analyzeSpeechToText_invalidScore_throwsAiServiceException() {
        String jsonResponse = """
            {
                "full_text": "INVALID",
                "language": "en",
                "confidence_score": 1.5,
                "duration_seconds": 1.0,
                "segments_count": 0,
                "words_count": 0,
                "segments": [],
                "status": "COMPLETED"
            }
            """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/analyze/speech-to-text"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(jsonResponse, MediaType.APPLICATION_JSON));

        assertThatThrownBy(() -> client.analyzeSpeechToText("bytes".getBytes(), "speech.wav", "audio/wav"))
                .isInstanceOf(AiServiceException.class)
                .hasMessageContaining("out-of-range confidence score");

        mockServer.verify();
    }
}
