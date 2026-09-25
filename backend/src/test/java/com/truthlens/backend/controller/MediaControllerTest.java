package com.truthlens.backend.controller;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.MediaResponse;
import com.truthlens.backend.dto.MediaUploadResponse;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.FileSizeExceededException;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.security.JwtAuthenticationFilter;
import com.truthlens.backend.security.JwtService;
import com.truthlens.backend.service.MediaService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Set;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = MediaController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("MediaController — WebMvc Integration Tests")
class MediaControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private MediaService mediaService;

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

    @Test
    @DisplayName("POST /api/media/upload — returns 201 when upload is valid and authenticated")
    void uploadMedia_authenticated_success() throws Exception {
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        MockMultipartFile file = new MockMultipartFile(
                "file", "photo.jpg", "image/jpeg", "image content".getBytes()
        );

        UUID mediaId = UUID.randomUUID();
        UUID uploaderId = UUID.randomUUID();
        MediaUploadResponse mockResponse = new MediaUploadResponse(
                "Media uploaded and quarantined successfully",
                mediaId,
                uploaderId,
                "photo.jpg",
                "quarantine/image/20260919/uuid.jpg",
                "IMAGE",
                "image/jpeg",
                100,
                "hash123",
                "UPLOADED",
                OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaService.uploadMedia(any(), eq("analyst@truthlens.org"))).thenReturn(mockResponse);

        mockMvc.perform(multipart("/api/media/upload")
                        .file(file)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(mediaId.toString()))
                .andExpect(jsonPath("$.originalFilename").value("photo.jpg"))
                .andExpect(jsonPath("$.mediaType").value("IMAGE"))
                .andExpect(jsonPath("$.uploadStatus").value("UPLOADED"));
    }

    @Test
    @DisplayName("POST /api/media/upload — returns 401 Unauthorized when unauthenticated")
    void uploadMedia_unauthenticated_returns401() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", "photo.jpg", "image/jpeg", "image content".getBytes()
        );

        mockMvc.perform(multipart("/api/media/upload").file(file))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("POST /api/media/upload — returns 400 Bad Request when file is invalid")
    void uploadMedia_invalidMedia_returns400() throws Exception {
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        MockMultipartFile file = new MockMultipartFile(
                "file", "bad.elf", "application/octet-stream", "bad".getBytes()
        );

        when(mediaService.uploadMedia(any(), eq("analyst@truthlens.org")))
                .thenThrow(new InvalidMediaException("Unsupported file format: 'application/octet-stream'"));

        mockMvc.perform(multipart("/api/media/upload")
                        .file(file)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("INVALID_MEDIA"))
                .andExpect(jsonPath("$.message").value("Unsupported file format: 'application/octet-stream'"));
    }

    @Test
    @DisplayName("POST /api/media/upload — returns 413 Payload Too Large when file exceeds limit")
    void uploadMedia_fileTooLarge_returns413() throws Exception {
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        MockMultipartFile file = new MockMultipartFile(
                "file", "giant.mp4", "video/mp4", new byte[10]
        );

        when(mediaService.uploadMedia(any(), eq("analyst@truthlens.org")))
                .thenThrow(new FileSizeExceededException("File size exceeds maximum limit"));

        mockMvc.perform(multipart("/api/media/upload")
                        .file(file)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isPayloadTooLarge())
                .andExpect(jsonPath("$.error").value("FILE_SIZE_EXCEEDED"));
    }

    @Test
    @DisplayName("GET /api/media/{id} — returns 200 OK with media metadata for owner")
    void getMediaById_authenticatedOwner_returns200() throws Exception {
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();

        MediaResponse mockResponse = new MediaResponse(
                mediaId, UUID.randomUUID(), "photo.png", "quarantine/path.png",
                "IMAGE", "image/png", 500, "hash", "UPLOADED",
                OffsetDateTime.now(ZoneOffset.UTC), OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaService.getMediaById(eq(mediaId), eq("user@truthlens.org"))).thenReturn(mockResponse);

        mockMvc.perform(get("/api/media/" + mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(mediaId.toString()))
                .andExpect(jsonPath("$.originalFilename").value("photo.png"));
    }

    @Test
    @DisplayName("GET /api/media/{id} — returns 403 Forbidden on IDOR attempt by unauthorized user")
    void getMediaById_idorAccessDenied_returns403() throws Exception {
        String token = createBearerToken("attacker@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();

        when(mediaService.getMediaById(eq(mediaId), eq("attacker@truthlens.org")))
                .thenThrow(new org.springframework.security.access.AccessDeniedException("Access denied. You do not have permission to access this media."));

        mockMvc.perform(get("/api/media/" + mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error").value("FORBIDDEN"))
                .andExpect(jsonPath("$.message").value("Access denied. You do not have permission to access this resource."));
    }

    @Test
    @DisplayName("GET /api/media/{id} — returns 200 OK for elevated ANALYST role accessing any media")
    void getMediaById_elevatedAnalyst_returns200() throws Exception {
        String token = createBearerToken("analyst@truthlens.org", RoleName.ANALYST);
        UUID mediaId = UUID.randomUUID();

        MediaResponse mockResponse = new MediaResponse(
                mediaId, UUID.randomUUID(), "case_evidence.png", "quarantine/path.png",
                "IMAGE", "image/png", 500, "hash", "UPLOADED",
                OffsetDateTime.now(ZoneOffset.UTC), OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaService.getMediaById(eq(mediaId), eq("analyst@truthlens.org"))).thenReturn(mockResponse);

        mockMvc.perform(get("/api/media/" + mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(mediaId.toString()))
                .andExpect(jsonPath("$.originalFilename").value("case_evidence.png"));
    }

    @Test
    @DisplayName("GET /api/media/{id} — returns 401 Unauthorized when unauthenticated")
    void getMediaById_unauthenticated_returns401() throws Exception {
        UUID mediaId = UUID.randomUUID();

        mockMvc.perform(get("/api/media/" + mediaId))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/media/{id} — returns 404 when media does not exist")
    void getMediaById_notFound_returns404() throws Exception {
        String token = createBearerToken("user@truthlens.org", RoleName.USER);
        UUID mediaId = UUID.randomUUID();

        when(mediaService.getMediaById(eq(mediaId), eq("user@truthlens.org")))
                .thenThrow(new MediaNotFoundException("Media not found with id: " + mediaId));

        mockMvc.perform(get("/api/media/" + mediaId)
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("MEDIA_NOT_FOUND"));
    }

    @Test
    @DisplayName("GET /api/media/my — returns 200 OK with user media list")
    void getMyMedia_authenticated_returnsList() throws Exception {
        String token = createBearerToken("user@truthlens.org", RoleName.USER);

        MediaResponse item = new MediaResponse(
                UUID.randomUUID(), UUID.randomUUID(), "doc.txt", "quarantine/doc.txt",
                "TEXT", "text/plain", 200, "hash", "UPLOADED",
                OffsetDateTime.now(ZoneOffset.UTC), OffsetDateTime.now(ZoneOffset.UTC)
        );

        when(mediaService.getMediaForUser("user@truthlens.org")).thenReturn(List.of(item));

        mockMvc.perform(get("/api/media/my")
                        .header(HttpHeaders.AUTHORIZATION, token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].originalFilename").value("doc.txt"))
                .andExpect(jsonPath("$[0].mediaType").value("TEXT"));
    }
}
