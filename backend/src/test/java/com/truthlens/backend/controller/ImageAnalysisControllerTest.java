package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.ImageAnalysisResponse;
import com.truthlens.backend.dto.ImageEvidenceDto;
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
import com.truthlens.backend.service.image.ImageAuthenticityService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = ImageAnalysisController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("ImageAnalysisController — WebMvc Integration Tests")
class ImageAnalysisControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private ImageAuthenticityService imageAuthenticityService;

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

    private ImageAnalysisResponse buildSampleResponse(UUID mediaId) {
        ImageEvidenceDto ev = new ImageEvidenceDto(18.5, 0.05, 0.35, true, false, 800, 600, Map.of());
        return new ImageAnalysisResponse(
                UUID.randomUUID(),
                mediaId,
                0.85,
                0.42,
                "HIGH_SYNTHETIC_RISK",
                "/api/media/" + mediaId + "/image-analysis/artifacts/ela",
                "/api/media/" + mediaId + "/image-analysis/artifacts/gradcam",
                18.5,
                0.35,
                true,
                false,
                AnalysisStatus.COMPLETED,
                "TruthLens-DiffusionClassifier-0.1.0-dev",
                ev,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis: unauthenticated request returns HTTP 401")
    void getAnalysis_unauthenticated_returns401() throws Exception {
        mockMvc.perform(get("/api/media/" + UUID.randomUUID() + "/image-analysis"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis: authenticated USER receives HTTP 200 with analysis")
    void getAnalysis_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        ImageAnalysisResponse response = buildSampleResponse(mediaId);

        when(imageAuthenticityService.getImageAnalysis(eq(mediaId), any())).thenReturn(response);

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.aiProb").value(0.85))
                .andExpect(jsonPath("$.manipulationProb").value(0.42))
                .andExpect(jsonPath("$.authenticityAssessment").value("HIGH_SYNTHETIC_RISK"))
                .andExpect(jsonPath("$.analysisStatus").value("COMPLETED"))
                .andExpect(jsonPath("$.copyMoveDetected").value(true));
    }

    @Test
    @DisplayName("POST /api/media/{id}/image-analysis: triggers re-analysis, returns HTTP 200")
    void postAnalysis_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        ImageAnalysisResponse response = buildSampleResponse(mediaId);

        when(imageAuthenticityService.reanalyzeImage(eq(mediaId), any())).thenReturn(response);

        mockMvc.perform(post("/api/media/" + mediaId + "/image-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.modelVersion").value("TruthLens-DiffusionClassifier-0.1.0-dev"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis/evidence: returns HTTP 200 with forensic evidence")
    void getEvidence_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        ImageEvidenceDto ev = new ImageEvidenceDto(14.0, 0.02, 0.20, false, false, 1024, 768, Map.of());

        when(imageAuthenticityService.getEvidence(eq(mediaId), any())).thenReturn(ev);

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis/evidence")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.noiseVariance").value(14.0))
                .andExpect(jsonPath("$.fftAnomalyScore").value(0.20))
                .andExpect(jsonPath("$.imageWidth").value(1024));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis/artifacts/ela: streams PNG heatmap artifact")
    void getArtifact_ela_returns200ImagePng() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        byte[] fakePng = new byte[]{(byte) 137, 80, 78, 71, 13, 10, 26, 10};

        when(imageAuthenticityService.getArtifactStream(eq(mediaId), eq("ela"), any()))
                .thenReturn(new ByteArrayInputStream(fakePng));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis/artifacts/ela")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.IMAGE_PNG))
                .andExpect(content().bytes(fakePng));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis: IDOR access denial returns HTTP 403 Forbidden")
    void getAnalysis_idorAccessDenied_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("attacker@truthlens.org", RoleName.USER);

        when(imageAuthenticityService.getImageAnalysis(eq(mediaId), any()))
                .thenThrow(new AccessDeniedException("Access denied"));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error").value("FORBIDDEN"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis: non-existent media returns HTTP 404")
    void getAnalysis_mediaNotFound_returns404() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(imageAuthenticityService.getImageAnalysis(eq(mediaId), any()))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("MEDIA_NOT_FOUND"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis: non-image media returns HTTP 400 Bad Request")
    void getAnalysis_nonImageMedia_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(imageAuthenticityService.getImageAnalysis(eq(mediaId), any()))
                .thenThrow(new InvalidMediaException("Image authenticity analysis is only supported for image assets"));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("INVALID_MEDIA"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis: AI service failure returns HTTP 502 Bad Gateway")
    void getAnalysis_aiServiceFailure_returns502() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(imageAuthenticityService.getImageAnalysis(eq(mediaId), any()))
                .thenThrow(new AiServiceException("Downstream FastAPI unreachable"));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error").value("AI_SERVICE_UNAVAILABLE"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis/artifacts/gradcam: streams PNG heatmap artifact")
    void getArtifact_gradcam_returns200ImagePng() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        byte[] fakePng = new byte[]{(byte) 137, 80, 78, 71, 13, 10, 26, 10};

        when(imageAuthenticityService.getArtifactStream(eq(mediaId), eq("gradcam"), any()))
                .thenReturn(new ByteArrayInputStream(fakePng));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis/artifacts/gradcam")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.IMAGE_PNG))
                .andExpect(content().bytes(fakePng));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis/artifacts/invalid: invalid artifact type returns HTTP 400 Bad Request")
    void getArtifact_invalidType_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(imageAuthenticityService.getArtifactStream(eq(mediaId), eq("invalid_type"), any()))
                .thenThrow(new IllegalArgumentException("Unsupported artifact type: 'invalid_type'. Supported types: 'ela', 'gradcam'"));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis/artifacts/invalid_type")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("INVALID_PARAMETER"))
                .andExpect(jsonPath("$.message").value("Unsupported artifact type: 'invalid_type'. Supported types: 'ela', 'gradcam'"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/image-analysis/artifacts/{type}: path traversal attempt returns HTTP 400 without filesystem leakage")
    void getArtifact_pathTraversalType_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        // Path traversal with raw '..' rejected at HTTP routing level with 400
        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis/artifacts/..")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest());

        // Traversal argument that reaches controller is intercepted by IllegalArgumentException returning 400 with INVALID_PARAMETER
        when(imageAuthenticityService.getArtifactStream(eq(mediaId), eq("..etc..passwd"), any()))
                .thenThrow(new IllegalArgumentException("Unsupported artifact type: '..etc..passwd'. Supported types: 'ela', 'gradcam'"));

        mockMvc.perform(get("/api/media/" + mediaId + "/image-analysis/artifacts/..etc..passwd")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("INVALID_PARAMETER"))
                .andExpect(jsonPath("$.message").value("Unsupported artifact type: '..etc..passwd'. Supported types: 'ela', 'gradcam'"));
    }
}
