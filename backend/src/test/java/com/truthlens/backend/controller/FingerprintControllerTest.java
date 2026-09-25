package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.DuplicateDetailResponse;
import com.truthlens.backend.dto.MediaHashResponse;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.security.JwtAuthenticationFilter;
import com.truthlens.backend.security.JwtService;
import com.truthlens.backend.service.fingerprint.MediaFingerprintService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
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
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = FingerprintController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("FingerprintController — WebMvc Integration Tests (S-01, F-03)")
class FingerprintControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private MediaFingerprintService mediaFingerprintService;

    @MockBean
    private RevokedTokenRepository revokedTokenRepository;

    private String createBearerToken(String email, RoleName roleName) throws Exception {
        Role role = new Role(roleName, "description");
        User user = new User(email, "hash", "Test User");
        user.getRoles().add(role);

        Field idField = user.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(user, UUID.randomUUID());

        return "Bearer " + jwtService.generateToken(user);
    }

    @ParameterizedTest
    @EnumSource(RoleName.class)
    @DisplayName("S-01 Role Authorization: All five system roles can access fingerprint endpoints")
    void getFingerprint_allFiveRolesPermitted_returns200(RoleName role) throws Exception {
        String email = role.name().toLowerCase() + "@truthlens.org";
        String token = createBearerToken(email, role);
        UUID mediaId = UUID.randomUUID();

        MediaHashResponse mockResponse = new MediaHashResponse(
                UUID.randomUUID(), mediaId, "sha256_hash_value", "1234567890abcdef", null,
                false, null, 0.0, "NONE", OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaFingerprintService.getFingerprint(eq(mediaId), eq(email)))
                .thenReturn(mockResponse);

        mockMvc.perform(get("/api/media/" + mediaId + "/fingerprint")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()));
    }

    @Test
    @DisplayName("GET /api/media/{id}/fingerprint — returns 200 with fingerprint metadata for authorized user")
    void getFingerprint_authorized_returns200() throws Exception {
        String token = createBearerToken("owner@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();

        MediaHashResponse mockResponse = new MediaHashResponse(
                UUID.randomUUID(), mediaId, "sha256_hash_value", "1234567890abcdef", null,
                false, null, 0.0, "NONE", OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaFingerprintService.getFingerprint(eq(mediaId), eq("owner@truthlens.org")))
                .thenReturn(mockResponse);

        mockMvc.perform(get("/api/media/" + mediaId + "/fingerprint")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.sha256Hash").value("sha256_hash_value"))
                .andExpect(jsonPath("$.phash").value("1234567890abcdef"))
                .andExpect(jsonPath("$.isDuplicate").value(false));
    }

    @Test
    @DisplayName("GET /api/media/{id}/fingerprint — returns 401 when unauthenticated")
    void getFingerprint_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();

        mockMvc.perform(get("/api/media/" + mediaId + "/fingerprint"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/fingerprint — returns 403 on IDOR unauthorized access")
    void getFingerprint_idorAttempt_returns403() throws Exception {
        String token = createBearerToken("intruder@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();

        when(mediaFingerprintService.getFingerprint(eq(mediaId), eq("intruder@truthlens.org")))
                .thenThrow(new AccessDeniedException("Access denied. You do not have permission to access this media's fingerprint."));

        mockMvc.perform(get("/api/media/" + mediaId + "/fingerprint")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error").value("FORBIDDEN"));
    }

    @Test
    @DisplayName("F-03 Remediation: POST /api/media/{id}/fingerprint — invokes re-evaluation and returns 200")
    void generateFingerprint_authorized_returns200() throws Exception {
        String token = createBearerToken("owner@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();

        MediaHashResponse mockResponse = new MediaHashResponse(
                UUID.randomUUID(), mediaId, "sha256_hash_value", "1234567890abcdef", null,
                false, null, 0.0, "NONE", OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaFingerprintService.generateOrReevaluateFingerprint(eq(mediaId), eq("owner@truthlens.org")))
                .thenReturn(mockResponse);

        mockMvc.perform(post("/api/media/" + mediaId + "/fingerprint")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()));
    }

    @Test
    @DisplayName("GET /api/media/{id}/duplicates — returns 200 with duplicate analysis details")
    void getDuplicateDetails_duplicateFound_returns200() throws Exception {
        String token = createBearerToken("owner@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();
        UUID duplicateOfId = UUID.randomUUID();

        DuplicateDetailResponse mockResponse = new DuplicateDetailResponse(
                mediaId, true, "EXACT_SHA256", 1.0, duplicateOfId, "Verified Reference Item", OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaFingerprintService.getDuplicateDetails(eq(mediaId), eq("owner@truthlens.org")))
                .thenReturn(mockResponse);

        mockMvc.perform(get("/api/media/" + mediaId + "/duplicates")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.isDuplicate").value(true))
                .andExpect(jsonPath("$.matchType").value("EXACT_SHA256"))
                .andExpect(jsonPath("$.similarityScore").value(1.0))
                .andExpect(jsonPath("$.duplicateOfMediaId").value(duplicateOfId.toString()))
                .andExpect(jsonPath("$.duplicateOfFilename").value("Verified Reference Item"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/duplicates — returns 404 when media does not exist")
    void getDuplicateDetails_notFound_returns404() throws Exception {
        String token = createBearerToken("owner@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();

        when(mediaFingerprintService.getDuplicateDetails(eq(mediaId), eq("owner@truthlens.org")))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/" + mediaId + "/duplicates")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("MEDIA_NOT_FOUND"));
    }
}
