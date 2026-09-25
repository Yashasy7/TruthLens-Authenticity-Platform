package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.TranscriptEvidenceDto;
import com.truthlens.backend.dto.TranscriptResponse;
import com.truthlens.backend.dto.TranscriptSegmentDto;
import com.truthlens.backend.dto.TranscriptWordDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.security.JwtAuthenticationFilter;
import com.truthlens.backend.security.JwtService;
import com.truthlens.backend.service.stt.SpeechToTextService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = TranscriptController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("TranscriptController — WebMvc Integration Tests")
class TranscriptControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private SpeechToTextService speechToTextService;

    @MockBean
    private RevokedTokenRepository revokedTokenRepository;

    private String createBearerToken(String email, RoleName roleName) throws Exception {
        Role role = new Role(roleName, "description");
        User user = new User(email, "hashed_password", "Test User");
        user.getRoles().add(role);

        Field idField = User.class.getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(user, UUID.randomUUID());

        return "Bearer " + jwtService.generateToken(user);
    }

    private TranscriptResponse buildSampleResponse(UUID mediaId) {
        TranscriptWordDto word = new TranscriptWordDto("TruthLens", 0.0, 0.5, 0.98);
        TranscriptSegmentDto segment = new TranscriptSegmentDto(
                0, 0, 0.0, 2.5, "TruthLens audio verification", List.of(101, 102), 0.0, -0.05, 1.1, 0.01, 0.96, List.of(word)
        );
        TranscriptEvidenceDto evidence = new TranscriptEvidenceDto(
                "Faster-Whisper", "tiny", "int8", "cpu", "en", 0.99, 2.5, 16000, "AUDIO", Map.of()
        );

        return new TranscriptResponse(
                UUID.randomUUID(),
                mediaId,
                "TruthLens audio verification",
                "en",
                0.96,
                2.5,
                1,
                3,
                List.of(segment),
                evidence,
                AnalysisStatus.COMPLETED,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/transcript: unauthenticated request returns HTTP 401")
    void getTranscript_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();
        mockMvc.perform(get("/api/media/{id}/transcript", mediaId))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/transcript: authenticated request returns HTTP 200 with result")
    void getTranscript_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(speechToTextService.getTranscript(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(get("/api/media/{id}/transcript", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.fullText").value("TruthLens audio verification"))
                .andExpect(jsonPath("$.confidenceScore").value(0.96))
                .andExpect(jsonPath("$.segmentsCount").value(1))
                .andExpect(jsonPath("$.segments").isArray());
    }

    @Test
    @DisplayName("POST /api/media/{id}/transcript: re-analysis triggers fresh evaluation")
    void reanalyzeTranscript_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(speechToTextService.reanalyzeTranscript(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/transcript", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.fullText").value("TruthLens audio verification"));
    }

    @Test
    @DisplayName("POST /api/media/{id}/transcript/analyze: re-analysis triggers via explicit /analyze subpath")
    void reanalyzeTranscript_explicitAnalyzeSubpath_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(speechToTextService.reanalyzeTranscript(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/transcript/analyze", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.fullText").value("TruthLens audio verification"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/transcript/segments: returns list of timestamped segments")
    void getSegments_returnsSegmentsList() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        TranscriptSegmentDto segment = new TranscriptSegmentDto(
                0, 0, 0.0, 2.5, "TruthLens audio verification", List.of(), 0.0, 0.0, 1.0, 0.0, 0.95, List.of()
        );

        when(speechToTextService.getSegments(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(List.of(segment));

        mockMvc.perform(get("/api/media/{id}/transcript/segments", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$[0].text").value("TruthLens audio verification"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/transcript/text: returns raw full text in map")
    void getFullText_returnsTextMap() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(speechToTextService.getFullText(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn("TruthLens audio verification");

        mockMvc.perform(get("/api/media/{id}/transcript/text", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.full_text").value("TruthLens audio verification"));
    }

    @Test
    @DisplayName("IDOR protection: unauthorized user returns HTTP 403 Forbidden")
    void idor_unauthorizedUser_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("intruder@truthlens.org", RoleName.USER);

        when(speechToTextService.getTranscript(eq(mediaId), eq("intruder@truthlens.org")))
                .thenThrow(new AccessDeniedException("Access denied. You do not have permission to access this media's transcript."));

        mockMvc.perform(get("/api/media/{id}/transcript", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.message").value("Access denied. You do not have permission to access this resource."));
    }

    @Test
    @DisplayName("Invalid media type (IMAGE): returns HTTP 400 Bad Request")
    void invalidMediaType_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(speechToTextService.getTranscript(eq(mediaId), eq("analyst@truthlens.org")))
                .thenThrow(new InvalidMediaException("Speech-to-text transcription is only supported for audio and video assets. Target media type: IMAGE"));

        mockMvc.perform(get("/api/media/{id}/transcript", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Speech-to-text transcription is only supported for audio and video assets. Target media type: IMAGE"));
    }

    @Test
    @DisplayName("Media not found: returns HTTP 404 Not Found")
    void mediaNotFound_returns404() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(speechToTextService.getTranscript(eq(mediaId), eq("analyst@truthlens.org")))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/{id}/transcript", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("Media not found with id: " + mediaId));
    }
}
