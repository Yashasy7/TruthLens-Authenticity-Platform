package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.AudioAnalysisResponse;
import com.truthlens.backend.dto.AudioEvidenceDto;
import com.truthlens.backend.dto.AudioSpliceMarkerDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.security.JwtAuthenticationFilter;
import com.truthlens.backend.security.JwtService;
import com.truthlens.backend.service.audio.AudioAuthenticityService;
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

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = AudioAnalysisController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("AudioAnalysisController — WebMvc Integration Tests")
class AudioAnalysisControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private AudioAuthenticityService audioAuthenticityService;

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

    private AudioAnalysisResponse buildSampleResponse(UUID mediaId) {
        AudioSpliceMarkerDto marker = new AudioSpliceMarkerDto(1.5, 0.85, "SPECTRAL_FLUX_JUMP");
        AudioEvidenceDto evidence = new AudioEvidenceDto(
                5.0, 215.0, 142.5, 1850.0, 1500.0, 3700.0, 0.06, 0.72,
                List.of(marker), Map.of("pitch_anomaly", 0.75)
        );

        return new AudioAnalysisResponse(
                UUID.randomUUID(),
                mediaId,
                0.85,
                "/artifacts/spec_01.png",
                "base64image",
                142.5,
                0.72,
                "HIGH_SYNTHETIC_VOICE_RISK",
                AnalysisStatus.COMPLETED,
                "TruthLens-PyTorch-AASIST-AudioClassifier",
                "0.1.0-dev",
                List.of(marker),
                evidence,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis: unauthenticated request returns HTTP 401")
    void getAudioAnalysis_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();
        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis: valid authorized user returns HTTP 200 with result")
    void getAudioAnalysis_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        AudioAnalysisResponse sample = buildSampleResponse(mediaId);

        when(audioAuthenticityService.getAudioAnalysis(eq(mediaId), any())).thenReturn(sample);

        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.media_id").value(mediaId.toString()))
                .andExpect(jsonPath("$.synthetic_voice_prob").value(0.85))
                .andExpect(jsonPath("$.spectrogram_url").value("/artifacts/spec_01.png"))
                .andExpect(jsonPath("$.pitch_variance").value(142.5))
                .andExpect(jsonPath("$.phase_discontinuity").value(0.72))
                .andExpect(jsonPath("$.authenticity_assessment").value("HIGH_SYNTHETIC_VOICE_RISK"))
                .andExpect(jsonPath("$.analysis_status").value("COMPLETED"));
    }

    @Test
    @DisplayName("POST /api/media/{id}/audio-analysis: triggers re-analysis and returns fresh HTTP 200")
    void reanalyzeAudio_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        AudioAnalysisResponse sample = buildSampleResponse(mediaId);

        when(audioAuthenticityService.reanalyzeAudio(eq(mediaId), any())).thenReturn(sample);

        mockMvc.perform(post("/api/media/" + mediaId + "/audio-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.media_id").value(mediaId.toString()))
                .andExpect(jsonPath("$.synthetic_voice_prob").value(0.85));
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis/evidence: returns acoustic evidence breakdown")
    void getEvidence_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        AudioEvidenceDto evidence = new AudioEvidenceDto(
                4.5, 210.0, 110.0, 1750.0, 1400.0, 3500.0, 0.05, 0.45, List.of(), Map.of()
        );

        when(audioAuthenticityService.getEvidence(eq(mediaId), any())).thenReturn(evidence);

        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis/evidence")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.duration_seconds").value(4.5))
                .andExpect(jsonPath("$.pitch_mean").value(210.0))
                .andExpect(jsonPath("$.phase_discontinuity_score").value(0.45));
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis/splice-markers: returns detected splice markers")
    void getSpliceMarkers_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        AudioSpliceMarkerDto m1 = new AudioSpliceMarkerDto(1.8, 0.88, "SPECTRAL_FLUX_JUMP");

        when(audioAuthenticityService.getSpliceMarkers(eq(mediaId), any())).thenReturn(List.of(m1));

        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis/splice-markers")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].timestamp_seconds").value(1.8))
                .andExpect(jsonPath("$[0].reason").value("SPECTRAL_FLUX_JUMP"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis: IDOR access denial returns HTTP 403 Forbidden")
    void getAudioAnalysis_idorAccessDenied_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("stranger@truthlens.org", RoleName.USER);

        when(audioAuthenticityService.getAudioAnalysis(eq(mediaId), any()))
                .thenThrow(new AccessDeniedException("Access denied."));

        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis: non-existent media returns HTTP 404 Not Found")
    void getAudioAnalysis_notFound_returns404() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(audioAuthenticityService.getAudioAnalysis(eq(mediaId), any()))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis: non-audio media returns HTTP 400 Bad Request")
    void getAudioAnalysis_invalidMedia_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(audioAuthenticityService.getAudioAnalysis(eq(mediaId), any()))
                .thenThrow(new InvalidMediaException("Audio analysis is only supported for audio assets."));

        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("GET /api/media/{id}/audio-analysis: AI service failure returns HTTP 502 Bad Gateway")
    void getAudioAnalysis_aiServiceFailure_returns502() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(audioAuthenticityService.getAudioAnalysis(eq(mediaId), any()))
                .thenThrow(new AiServiceException("FastAPI audio service returned 500"));

        mockMvc.perform(get("/api/media/" + mediaId + "/audio-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadGateway());
    }
}
