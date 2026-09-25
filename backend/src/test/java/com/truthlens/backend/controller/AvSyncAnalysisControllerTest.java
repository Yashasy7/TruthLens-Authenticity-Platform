package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.AvSyncAnalysisResponse;
import com.truthlens.backend.dto.AvSyncEvidenceDto;
import com.truthlens.backend.dto.MismatchSegmentDto;
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
import com.truthlens.backend.service.avsync.AvSyncAnalysisService;
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

@WebMvcTest(controllers = AvSyncAnalysisController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("AvSyncAnalysisController — WebMvc Integration Tests")
class AvSyncAnalysisControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private AvSyncAnalysisService avSyncAnalysisService;

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

    private AvSyncAnalysisResponse buildSampleResponse(UUID mediaId) {
        MismatchSegmentDto segment = new MismatchSegmentDto(1.0, 2.0, -20.0, 0.85, "Normal speech window");
        AvSyncEvidenceDto evidence = new AvSyncEvidenceDto();
        evidence.setDetectedFacesCount(1);
        evidence.setSelectedFaceTrackId(1);
        evidence.setVideoDurationSeconds(3.0);
        evidence.setAudioDurationSeconds(3.0);
        evidence.setFps(25.0);
        evidence.setEnvelopeCorrelation(0.85);
        evidence.setSyncnetMinDistance(0.35);
        evidence.setSyncnetConfidence(0.88);
        evidence.setTrackingStability(0.95);
        evidence.setDevelopmentModel(true);
        evidence.setDetails(Map.of("sample", "data"));

        return new AvSyncAnalysisResponse(
                UUID.randomUUID(),
                mediaId,
                0.88,
                -20.0,
                0.90,
                "SYNCHRONIZED",
                AnalysisStatus.COMPLETED,
                "TruthLens-PyTorch-SyncNet-DualStream",
                "TruthLens-SyncNet-v1.0-dev",
                List.of(segment),
                evidence,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/av-sync: unauthenticated request returns HTTP 401")
    void getAvSyncAnalysis_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();
        mockMvc.perform(get("/api/media/{id}/av-sync", mediaId))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/av-sync: authenticated request returns HTTP 200 with result")
    void getAvSyncAnalysis_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(avSyncAnalysisService.getAvSyncAnalysis(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(get("/api/media/{id}/av-sync", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.syncScore").value(0.88))
                .andExpect(jsonPath("$.lipOffsetMs").value(-20.0))
                .andExpect(jsonPath("$.assessment").value("SYNCHRONIZED"))
                .andExpect(jsonPath("$.mismatchSegments").isArray())
                .andExpect(jsonPath("$.evidence.envelope_correlation").value(0.85));
    }

    @Test
    @DisplayName("POST /api/media/{id}/av-sync: re-analysis triggers fresh evaluation")
    void reanalyzeAvSync_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(avSyncAnalysisService.reanalyzeAvSync(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/av-sync", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.syncScore").value(0.88));
    }

    @Test
    @DisplayName("POST /api/media/{id}/av-sync/analyze: re-analysis triggers via explicit /analyze subpath")
    void reanalyzeAvSync_explicitAnalyzeSubpath_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(avSyncAnalysisService.reanalyzeAvSync(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/av-sync/analyze", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.syncScore").value(0.88));
    }

    @Test
    @DisplayName("GET /api/media/{id}/av-sync/evidence: returns evidence DTO")
    void getEvidence_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        AvSyncEvidenceDto evidence = new AvSyncEvidenceDto();
        evidence.setDetectedFacesCount(1);
        evidence.setEnvelopeCorrelation(0.85);

        when(avSyncAnalysisService.getEvidence(eq(mediaId), eq("user@truthlens.org")))
                .thenReturn(evidence);

        mockMvc.perform(get("/api/media/{id}/av-sync/evidence", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.detected_faces_count").value(1))
                .andExpect(jsonPath("$.envelope_correlation").value(0.85));
    }

    @Test
    @DisplayName("GET /api/media/{id}/av-sync/mismatch-segments: returns list of mismatch segments")
    void getMismatchSegments_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        MismatchSegmentDto segment = new MismatchSegmentDto(0.5, 1.5, -20.0, 0.88, "Audible speech window");
        when(avSyncAnalysisService.getMismatchSegments(eq(mediaId), eq("user@truthlens.org")))
                .thenReturn(List.of(segment));

        mockMvc.perform(get("/api/media/{id}/av-sync/mismatch-segments", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].start_time").value(0.5))
                .andExpect(jsonPath("$[0].end_time").value(1.5))
                .andExpect(jsonPath("$[0].reason").value("Audible speech window"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/av-sync: IDOR attempt returns HTTP 403 Forbidden")
    void getAvSyncAnalysis_idor_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("unauthorized@truthlens.org", RoleName.USER);

        when(avSyncAnalysisService.getAvSyncAnalysis(eq(mediaId), eq("unauthorized@truthlens.org")))
                .thenThrow(new AccessDeniedException("Access denied. You do not have permission to access this media's analysis."));

        mockMvc.perform(get("/api/media/{id}/av-sync", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("GET /api/media/{id}/av-sync: wrong media type returns HTTP 400 Bad Request")
    void getAvSyncAnalysis_wrongMediaType_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(avSyncAnalysisService.getAvSyncAnalysis(eq(mediaId), eq("user@truthlens.org")))
                .thenThrow(new InvalidMediaException("Audio-video synchronization analysis is only supported for video assets."));

        mockMvc.perform(get("/api/media/{id}/av-sync", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("GET /api/media/{id}/av-sync: media not found returns HTTP 404 Not Found")
    void getAvSyncAnalysis_notFound_returns404() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(avSyncAnalysisService.getAvSyncAnalysis(eq(mediaId), eq("user@truthlens.org")))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/{id}/av-sync", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound());
    }
}
