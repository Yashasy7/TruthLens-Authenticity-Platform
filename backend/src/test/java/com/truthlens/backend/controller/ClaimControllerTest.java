package com.truthlens.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.AdHocTextClaimRequest;
import com.truthlens.backend.dto.ClaimAnalysisResponse;
import com.truthlens.backend.dto.ClaimDto;
import com.truthlens.backend.dto.ClaimEntityDto;
import com.truthlens.backend.dto.ClaimEvidenceDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.ClaimEntityType;
import com.truthlens.backend.entity.ClaimSourceType;
import com.truthlens.backend.entity.ClaimType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.security.JwtAuthenticationFilter;
import com.truthlens.backend.security.JwtService;
import com.truthlens.backend.service.claim.TextClaimAnalysisService;
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

@WebMvcTest(controllers = ClaimController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("ClaimController — WebMvc Integration Tests")
class ClaimControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private TextClaimAnalysisService textClaimAnalysisService;

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

    private ClaimDto buildSampleClaimDto(UUID mediaId) {
        ClaimEntityDto entityDto = new ClaimEntityDto("Federal Reserve", "ORG", "ORGANIZATION", 0, 15);
        return new ClaimDto(
                UUID.randomUUID(),
                mediaId,
                "The Federal Reserve cut interest rates by 25 basis points.",
                "the federal reserve cut interest rates by 25 basis points",
                ClaimType.FACTUAL_CLAIM,
                "Federal Reserve",
                "cut",
                "interest rates by 25 basis points",
                ClaimEntityType.ORG,
                0.95,
                "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
                ClaimSourceType.TRANSCRIPT,
                0,
                0,
                58,
                List.of(entityDto),
                AnalysisStatus.COMPLETED,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    private ClaimAnalysisResponse buildSampleAnalysisResponse(UUID mediaId) {
        ClaimDto claimDto = buildSampleClaimDto(mediaId);
        ClaimEntityDto entityDto = new ClaimEntityDto("Federal Reserve", "ORG", "ORGANIZATION", 0, 15);
        ClaimEvidenceDto evidence = new ClaimEvidenceDto(
                "spaCy/en_core_web_sm",
                1,
                1,
                1,
                0.05,
                Map.of("model", "en_core_web_sm")
        );
        return new ClaimAnalysisResponse(
                mediaId,
                ClaimSourceType.TRANSCRIPT,
                58,
                1,
                1,
                List.of(claimDto),
                List.of(entityDto),
                evidence,
                AnalysisStatus.COMPLETED,
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/claims: unauthenticated request returns HTTP 401")
    void getClaims_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();
        mockMvc.perform(get("/api/media/{id}/claims", mediaId))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/claims: authenticated request returns HTTP 200 with claim analysis response")
    void getClaims_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(textClaimAnalysisService.getClaims(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleAnalysisResponse(mediaId));

        mockMvc.perform(get("/api/media/{id}/claims", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.claimsCount").value(1))
                .andExpect(jsonPath("$.claims[0].subject").value("Federal Reserve"))
                .andExpect(jsonPath("$.claims[0].action").value("cut"))
                .andExpect(jsonPath("$.claims[0].claimType").value("FACTUAL_CLAIM"))
                .andExpect(jsonPath("$.evidence.model_name").value("spaCy/en_core_web_sm"));
    }

    @Test
    @DisplayName("POST /api/media/{id}/claims: re-analysis triggers fresh evaluation")
    void reanalyzeClaims_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(textClaimAnalysisService.reanalyzeClaims(eq(mediaId), eq("analyst@truthlens.org"), any()))
                .thenReturn(buildSampleAnalysisResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/claims", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.claimsCount").value(1));
    }

    @Test
    @DisplayName("POST /api/media/{id}/claims/analyze: re-analysis triggers via explicit /analyze subpath")
    void reanalyzeClaims_subpath_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(textClaimAnalysisService.reanalyzeClaims(eq(mediaId), eq("analyst@truthlens.org"), any()))
                .thenReturn(buildSampleAnalysisResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/claims/analyze", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.claimsCount").value(1));
    }

    @Test
    @DisplayName("GET /api/media/{id}/claims/{claimId}: returns single claim DTO")
    void getClaimById_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        ClaimDto claimDto = buildSampleClaimDto(mediaId);
        UUID claimId = claimDto.getId();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(textClaimAnalysisService.getClaimById(eq(mediaId), eq(claimId), eq("analyst@truthlens.org")))
                .thenReturn(claimDto);

        mockMvc.perform(get("/api/media/{id}/claims/{claimId}", mediaId, claimId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(claimId.toString()))
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.subject").value("Federal Reserve"))
                .andExpect(jsonPath("$.action").value("cut"));
    }

    @Test
    @DisplayName("POST /api/claims/analyze-text: authenticated request analyzes arbitrary text")
    void analyzeAdHocText_authenticated_returns200() throws Exception {
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        AdHocTextClaimRequest request = new AdHocTextClaimRequest(
                "The Prime Minister signed the accord yesterday in Paris.",
                "DIRECT_TEXT",
                "en"
        );

        when(textClaimAnalysisService.analyzeDirectText(
                eq(request.getText()),
                eq("DIRECT_TEXT"),
                eq(request.getLanguage()),
                eq("analyst@truthlens.org")))
                .thenReturn(buildSampleAnalysisResponse(null));

        mockMvc.perform(post("/api/claims/analyze-text")
                        .header(HttpHeaders.AUTHORIZATION, token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.claimsCount").value(1));
    }

    @Test
    @DisplayName("POST /api/claims/extract: blueprint endpoint extracts claims from text")
    void extractClaims_blueprintRoute_returns200() throws Exception {
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        AdHocTextClaimRequest request = new AdHocTextClaimRequest(
                "The Prime Minister signed the accord yesterday in Paris.",
                "DIRECT_TEXT",
                "en"
        );

        when(textClaimAnalysisService.analyzeDirectText(
                eq(request.getText()),
                eq("DIRECT_TEXT"),
                eq(request.getLanguage()),
                eq("analyst@truthlens.org")))
                .thenReturn(buildSampleAnalysisResponse(null));

        mockMvc.perform(post("/api/claims/extract")
                        .header(HttpHeaders.AUTHORIZATION, token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.claimsCount").value(1));
    }

    @Test
    @DisplayName("POST /api/claims/analyze-text: empty text returns HTTP 400 Bad Request")
    void analyzeAdHocText_blankText_returns400() throws Exception {
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        AdHocTextClaimRequest request = new AdHocTextClaimRequest(
                "",
                "DIRECT_TEXT",
                "en"
        );

        mockMvc.perform(post("/api/claims/analyze-text")
                        .header(HttpHeaders.AUTHORIZATION, token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("IDOR protection: unauthorized non-owner returns HTTP 403 Forbidden")
    void idor_unauthorizedUser_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("intruder@truthlens.org", RoleName.USER);

        when(textClaimAnalysisService.getClaims(eq(mediaId), eq("intruder@truthlens.org")))
                .thenThrow(new AccessDeniedException("Access denied. You do not have permission to access claims for this media."));

        mockMvc.perform(get("/api/media/{id}/claims", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.message").value("Access denied. You do not have permission to access this resource."));
    }

    @Test
    @DisplayName("Media not found: returns HTTP 404 Not Found")
    void mediaNotFound_returns404() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(textClaimAnalysisService.getClaims(eq(mediaId), eq("analyst@truthlens.org")))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/{id}/claims", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("Media not found with id: " + mediaId));
    }
}
