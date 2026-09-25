package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.FrameScoreDto;
import com.truthlens.backend.dto.SuspiciousTimestampDto;
import com.truthlens.backend.dto.VideoAnalysisResponse;
import com.truthlens.backend.dto.VideoEvidenceDto;
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
import com.truthlens.backend.service.video.VideoAuthenticityService;
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

@WebMvcTest(controllers = VideoAnalysisController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("VideoAnalysisController — WebMvc Integration Tests")
class VideoAnalysisControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private VideoAuthenticityService videoAuthenticityService;

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

    private VideoAnalysisResponse buildSampleResponse(UUID mediaId) {
        SuspiciousTimestampDto st = new SuspiciousTimestampDto(2.5, 5, 0.88, "HIGH_SYNTHETIC_FACE_PROBABILITY");
        FrameScoreDto fs = new FrameScoreDto(5, 2.5, 0.88, 0.72, 1, true);
        VideoEvidenceDto ev = new VideoEvidenceDto(1, 10, 5.0, List.of(fs), List.of(st), Map.of("p90_deepfake", 0.88));

        return new VideoAnalysisResponse(
                UUID.randomUUID(),
                mediaId,
                0.84,
                1,
                10,
                "HIGH_DEEPFAKE_RISK",
                AnalysisStatus.COMPLETED,
                "TruthLens-VideoDeepfakeClassifier-0.1.0-dev",
                List.of(st),
                ev,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis: unauthenticated request returns HTTP 401")
    void getVideoAnalysis_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();
        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis: valid authorized user returns HTTP 200 with result")
    void getVideoAnalysis_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        VideoAnalysisResponse sample = buildSampleResponse(mediaId);

        when(videoAuthenticityService.getVideoAnalysis(eq(mediaId), any())).thenReturn(sample);

        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.media_id").value(mediaId.toString()))
                .andExpect(jsonPath("$.deepfake_prob").value(0.84))
                .andExpect(jsonPath("$.face_count").value(1))
                .andExpect(jsonPath("$.total_frames_sampled").value(10))
                .andExpect(jsonPath("$.authenticity_assessment").value("HIGH_DEEPFAKE_RISK"))
                .andExpect(jsonPath("$.analysis_status").value("COMPLETED"));
    }

    @Test
    @DisplayName("POST /api/media/{id}/video-analysis: triggers re-analysis and returns fresh HTTP 200")
    void reanalyzeVideo_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        VideoAnalysisResponse sample = buildSampleResponse(mediaId);

        when(videoAuthenticityService.reanalyzeVideo(eq(mediaId), any())).thenReturn(sample);

        mockMvc.perform(post("/api/media/" + mediaId + "/video-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.media_id").value(mediaId.toString()))
                .andExpect(jsonPath("$.deepfake_prob").value(0.84));
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis/evidence: returns forensic evidence breakdown")
    void getEvidence_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        SuspiciousTimestampDto st = new SuspiciousTimestampDto(1.0, 2, 0.75, "TEMPORAL_DISCONTINUITY");
        FrameScoreDto fs = new FrameScoreDto(2, 1.0, 0.75, 0.60, 1, true);
        VideoEvidenceDto ev = new VideoEvidenceDto(1, 5, 2.5, List.of(fs), List.of(st), Map.of());

        when(videoAuthenticityService.getEvidence(eq(mediaId), any())).thenReturn(ev);

        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis/evidence")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.face_count").value(1))
                .andExpect(jsonPath("$.total_frames_sampled").value(5))
                .andExpect(jsonPath("$.frame_scores[0].timestamp_seconds").value(1.0));
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis/timeline: returns suspicious timestamps list")
    void getTimeline_authorized_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        SuspiciousTimestampDto st1 = new SuspiciousTimestampDto(1.0, 1, 0.80, "HIGH_SYNTHETIC_FACE_PROBABILITY");
        SuspiciousTimestampDto st2 = new SuspiciousTimestampDto(3.5, 3, 0.72, "TEMPORAL_DISCONTINUITY");

        when(videoAuthenticityService.getTimeline(eq(mediaId), any())).thenReturn(List.of(st1, st2));

        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis/timeline")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].timestamp_seconds").value(1.0))
                .andExpect(jsonPath("$[1].reason").value("TEMPORAL_DISCONTINUITY"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis: IDOR access denial returns HTTP 403 Forbidden")
    void getVideoAnalysis_idorAccessDenied_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("attacker@truthlens.org", RoleName.USER);

        when(videoAuthenticityService.getVideoAnalysis(eq(mediaId), any()))
                .thenThrow(new AccessDeniedException("Access denied"));

        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error").value("FORBIDDEN"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis: non-existent media returns HTTP 404")
    void getVideoAnalysis_mediaNotFound_returns404() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(videoAuthenticityService.getVideoAnalysis(eq(mediaId), any()))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("MEDIA_NOT_FOUND"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis: non-video media returns HTTP 400 Bad Request")
    void getVideoAnalysis_nonVideoMedia_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(videoAuthenticityService.getVideoAnalysis(eq(mediaId), any()))
                .thenThrow(new InvalidMediaException("Video deepfake analysis is only supported for video assets"));

        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("INVALID_MEDIA"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/video-analysis: downstream AI service failure returns HTTP 502 Bad Gateway")
    void getVideoAnalysis_aiServiceFailure_returns502() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(videoAuthenticityService.getVideoAnalysis(eq(mediaId), any()))
                .thenThrow(new AiServiceException("Downstream FastAPI video service unreachable"));

        mockMvc.perform(get("/api/media/" + mediaId + "/video-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error").value("AI_SERVICE_UNAVAILABLE"));
    }
}
