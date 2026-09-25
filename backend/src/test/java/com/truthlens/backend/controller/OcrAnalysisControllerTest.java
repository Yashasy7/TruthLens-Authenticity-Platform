package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.OcrBoundingBoxDto;
import com.truthlens.backend.dto.OcrEvidenceDto;
import com.truthlens.backend.dto.OcrResultResponse;
import com.truthlens.backend.dto.OcrTextRegionDto;
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
import com.truthlens.backend.service.ocr.OcrAnalysisService;
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

@WebMvcTest(controllers = OcrAnalysisController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("OcrAnalysisController — WebMvc Integration Tests")
class OcrAnalysisControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private OcrAnalysisService ocrAnalysisService;

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

    private OcrResultResponse buildSampleResponse(UUID mediaId) {
        OcrBoundingBoxDto bbox = new OcrBoundingBoxDto(20, 40, 200, 30, List.of(0.05, 0.1, 0.5, 0.08), List.of());
        OcrTextRegionDto region = new OcrTextRegionDto("BREAKING NEWS", 0.94, bbox, "en", 0, 0.0, 0.0, 1.0);
        OcrEvidenceDto evidence = new OcrEvidenceDto(1, List.of("en"), 400, 300, "EasyOCR", List.of("CLAHE"), "IMAGE", 1, Map.of());

        return new OcrResultResponse(
                UUID.randomUUID(),
                mediaId,
                "BREAKING NEWS",
                "en",
                0.94,
                1,
                List.of(region),
                evidence,
                AnalysisStatus.COMPLETED,
                OffsetDateTime.now(ZoneOffset.UTC),
                OffsetDateTime.now(ZoneOffset.UTC)
        );
    }

    @Test
    @DisplayName("GET /api/media/{id}/ocr: unauthenticated request returns HTTP 401")
    void getOcrResult_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();
        mockMvc.perform(get("/api/media/{id}/ocr", mediaId))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id}/ocr: authenticated request returns HTTP 200 with result")
    void getOcrResult_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(ocrAnalysisService.getOcrResult(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(get("/api/media/{id}/ocr", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.extractedText").value("BREAKING NEWS"))
                .andExpect(jsonPath("$.confidenceScore").value(0.94))
                .andExpect(jsonPath("$.regionsCount").value(1))
                .andExpect(jsonPath("$.regions").isArray());
    }

    @Test
    @DisplayName("POST /api/media/{id}/ocr: re-analysis triggers fresh evaluation")
    void reanalyzeOcr_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(ocrAnalysisService.reanalyzeOcr(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/ocr", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.extractedText").value("BREAKING NEWS"));
    }

    @Test
    @DisplayName("POST /api/media/{id}/ocr/analyze: re-analysis triggers via explicit /analyze subpath")
    void reanalyzeOcr_explicitAnalyzeSubpath_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);

        when(ocrAnalysisService.reanalyzeOcr(eq(mediaId), eq("analyst@truthlens.org")))
                .thenReturn(buildSampleResponse(mediaId));

        mockMvc.perform(post("/api/media/{id}/ocr/analyze", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mediaId").value(mediaId.toString()))
                .andExpect(jsonPath("$.extractedText").value("BREAKING NEWS"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/ocr/bounding-boxes: returns list of text regions")
    void getBoundingBoxes_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        OcrBoundingBoxDto bbox = new OcrBoundingBoxDto(20, 40, 200, 30, List.of(0.05, 0.1, 0.5, 0.08), List.of());
        OcrTextRegionDto region = new OcrTextRegionDto("HEADLINE", 0.94, bbox, "en", 0, 0.0, 0.0, 1.0);

        when(ocrAnalysisService.getBoundingBoxes(eq(mediaId), eq("user@truthlens.org")))
                .thenReturn(List.of(region));

        mockMvc.perform(get("/api/media/{id}/ocr/bounding-boxes", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].text").value("HEADLINE"))
                .andExpect(jsonPath("$[0].confidence").value(0.94));
    }

    @Test
    @DisplayName("GET /api/media/{id}/ocr/text: returns raw extracted text map")
    void getExtractedText_authenticated_returns200() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(ocrAnalysisService.getExtractedText(eq(mediaId), eq("user@truthlens.org")))
                .thenReturn("BREAKING NEWS ALERT");

        mockMvc.perform(get("/api/media/{id}/ocr/text", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.extracted_text").value("BREAKING NEWS ALERT"));
    }

    @Test
    @DisplayName("GET /api/media/{id}/ocr: IDOR attempt returns HTTP 403 Forbidden")
    void getOcrResult_idor_returns403() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("unauthorized@truthlens.org", RoleName.USER);

        when(ocrAnalysisService.getOcrResult(eq(mediaId), eq("unauthorized@truthlens.org")))
                .thenThrow(new AccessDeniedException("Access denied. You do not have permission to access this media's analysis."));

        mockMvc.perform(get("/api/media/{id}/ocr", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("GET /api/media/{id}/ocr: wrong media type returns HTTP 400 Bad Request")
    void getOcrResult_wrongMediaType_returns400() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(ocrAnalysisService.getOcrResult(eq(mediaId), eq("user@truthlens.org")))
                .thenThrow(new InvalidMediaException("OCR text extraction is only supported for image and video assets."));

        mockMvc.perform(get("/api/media/{id}/ocr", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("GET /api/media/{id}/ocr: media not found returns HTTP 404 Not Found")
    void getOcrResult_notFound_returns404() throws Exception {
        UUID mediaId = UUID.randomUUID();
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        when(ocrAnalysisService.getOcrResult(eq(mediaId), eq("user@truthlens.org")))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/{id}/ocr", mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound());
    }
}
