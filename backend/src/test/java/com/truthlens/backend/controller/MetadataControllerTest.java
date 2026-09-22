package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.ForensicAnomalyDto;
import com.truthlens.backend.dto.MediaMetadataResponse;
import com.truthlens.backend.dto.MetadataAnomalyReportResponse;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.security.JwtAuthenticationFilter;
import com.truthlens.backend.security.JwtService;
import com.truthlens.backend.service.metadata.MediaMetadataService;
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
import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = MetadataController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("MetadataController — WebMvc Integration Tests")
class MetadataControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private MediaMetadataService mediaMetadataService;

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

    private MediaMetadataResponse buildSampleResponse(UUID mediaId) {
        return new MediaMetadataResponse(
                UUID.randomUUID(),
                mediaId,
                "Canon",
                "Canon EOS 5D Mark IV",
                "EF 24-70mm f/2.8L II USM",
                "Firmware 1.3.3",
                OffsetDateTime.now(ZoneOffset.UTC).minusDays(1),
                OffsetDateTime.now(ZoneOffset.UTC).minusDays(1),
                37.7749,
                -122.4194,
                15.0,
                1920,
                1080,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                "JPEG",
                List.of(),
                false,
                0,
                0.0,
                "CLEAN",
                "JAVA_METADATA_EXTRACTOR",
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/metadata returns 200 OK with metadata response")
    void getMetadata_success() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(mediaMetadataService.getMetadata(eq(mediaId), eq("user@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(get("/api/media/{id}/metadata", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.cameraMake").value("Canon"))
                .andExpect(jsonPath("$.cameraModel").value("Canon EOS 5D Mark IV"))
                .andExpect(jsonPath("$.hasAnomalies").value(false))
                .andExpect(jsonPath("$.forensicScore").value(0.0));
    }

    @Test
    @DisplayName("POST /api/media/{id}/metadata re-extracts and returns 200 OK")
    void generateOrReevaluateMetadata_success() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(mediaMetadataService.generateOrReevaluateMetadata(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/metadata", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.cameraMake").value("Canon"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/metadata/anomalies returns 200 OK with anomaly details")
    void getAnomalyReport_success() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("moderator@truthlens.org", RoleName.MODERATOR);

        ForensicAnomalyDto anomaly = new ForensicAnomalyDto(
                "ANOM_EDITING_SOFTWARE",
                "SOFTWARE_MODIFICATION",
                "HIGH",
                "Editing Software Detected",
                "Photoshop tags present",
                "Adobe Photoshop 2024",
                0.95,
                0.35
        );

        MetadataAnomalyReportResponse report = new MetadataAnomalyReportResponse(
                mediaId,
                true,
                1,
                0.35,
                "SUSPICIOUS",
                List.of(anomaly),
                "Evaluation complete",
                OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaMetadataService.getAnomalyReport(eq(mediaId), eq("moderator@truthlens.org")))
                .thenReturn(report);

        mockMvc.perform(get("/api/media/{id}/metadata/anomalies", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.hasAnomalies").value(true))
                .andExpect(jsonPath("$.anomalyCount").value(1))
                .andExpect(jsonPath("$.anomalies[0].ruleId").value("ANOM_EDITING_SOFTWARE"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/metadata/raw returns 200 OK with raw JSON tree")
    void getRawMetadataJson_success() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        String rawJson = "{\"EXIF IFD0\":{\"Make\":\"Canon\",\"Model\":\"EOS 5D\"}}";
        when(mediaMetadataService.getRawMetadataJson(eq(mediaId), eq("user@truthlens.org")))
                .thenReturn(rawJson);

        mockMvc.perform(get("/api/media/{id}/metadata/raw", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(content().json(rawJson));
    }

    @ParameterizedTest
    @EnumSource(RoleName.class)
    @DisplayName("All 5 roles (USER, RESEARCHER, ANALYST, MODERATOR, ADMIN) can access metadata endpoints")
    void getMetadata_allRolesPermittedAtController(RoleName roleName) throws Exception {
        UUID mediaId = UUID.randomUUID();
        String email = roleName.name().toLowerCase() + "@truthlens.org";
        String token = createBearerToken(email, roleName);

        when(mediaMetadataService.getMetadata(eq(mediaId), eq(email)))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(get("/api/media/{id}/metadata", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("Returns 403 Forbidden when unauthorized user attempts access (IDOR defense)")
    void getMetadata_unauthorizedUser_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("unauthorized@truthlens.org", RoleName.USER);

        when(mediaMetadataService.getMetadata(eq(mediaId), eq("unauthorized@truthlens.org")))
                .thenThrow(new AccessDeniedException("Access denied. You do not have permission to access this media's metadata."));

        mockMvc.perform(get("/api/media/{id}/metadata", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Returns 404 Not Found when media ID does not exist")
    void getMetadata_notFound_returns404() throws Exception {
        UUID unknownId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(mediaMetadataService.getMetadata(eq(unknownId), eq("user@truthlens.org")))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + unknownId));

        mockMvc.perform(get("/api/media/{id}/metadata", unknownId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("Returns 401 Unauthorized when unauthenticated")
    void getMetadata_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();

        mockMvc.perform(get("/api/media/{id}/metadata", mediaId))
                .andExpect(status().isUnauthorized());
    }
}
