package com.truthlens.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.dto.UpdateProfileRequest;
import com.truthlens.backend.dto.UserProfileResponse;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.security.JwtAuthenticationFilter;
import com.truthlens.backend.security.JwtService;
import com.truthlens.backend.service.UserService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = UserController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("UserController — integration tests")
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private UserService userService;

    @MockBean
    private RevokedTokenRepository revokedTokenRepository;

    private String generateToken(String email, RoleName roleName) {
        User user = new User(email, "hashedPassword", "Test User");
        try {
            Field idField = User.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(user, UUID.randomUUID());
        } catch (Exception e) {
            throw new RuntimeException("Failed to set user ID for test", e);
        }
        user.getRoles().add(new Role(roleName, "Role description"));
        return jwtService.generateToken(user);
    }

    @Test
    @DisplayName("GET /api/users/me — authenticated user receives 200 with safe profile")
    void getCurrentUser_authenticated_returns200AndSafeProfile() throws Exception {
        String email = "alice@truthlens.io";
        String token = generateToken(email, RoleName.USER);
        UUID userId = UUID.randomUUID();
        OffsetDateTime now = OffsetDateTime.now();

        UserProfileResponse profileResponse = new UserProfileResponse(
                userId, email, "Alice Smith", "ACTIVE", Set.of("USER"), now, now);

        when(userService.getProfile(email)).thenReturn(profileResponse);

        mockMvc.perform(get("/api/users/me")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(userId.toString()))
                .andExpect(jsonPath("$.email").value(email))
                .andExpect(jsonPath("$.fullName").value("Alice Smith"))
                .andExpect(jsonPath("$.status").value("ACTIVE"))
                .andExpect(jsonPath("$.roles[0]").value("USER"))
                .andExpect(jsonPath("$.createdAt").exists())
                .andExpect(jsonPath("$.updatedAt").exists())
                // Verify sensitive fields are NOT exposed
                .andExpect(jsonPath("$.password").doesNotExist())
                .andExpect(jsonPath("$.passwordHash").doesNotExist())
                .andExpect(jsonPath("$.token").doesNotExist());
    }

    @Test
    @DisplayName("GET /api/users/me — unauthenticated request receives 401 Unauthorized")
    void getCurrentUser_unauthenticated_returns401() throws Exception {
        mockMvc.perform(get("/api/users/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("GET /api/users/me — user not found in database receives 404 Not Found")
    void getCurrentUser_userNotFound_returns404() throws Exception {
        String email = "deleted@truthlens.io";
        String token = generateToken(email, RoleName.USER);

        when(userService.getProfile(email))
                .thenThrow(new UserNotFoundException("User not found with email: " + email));

        mockMvc.perform(get("/api/users/me")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.error").value("USER_NOT_FOUND"))
                .andExpect(jsonPath("$.path").value("/api/users/me"));
    }

    @Test
    @DisplayName("PUT /api/users/me — authenticated user can update fullName")
    void updateCurrentUser_authenticated_returns200AndUpdatedProfile() throws Exception {
        String email = "alice@truthlens.io";
        String token = generateToken(email, RoleName.USER);
        UUID userId = UUID.randomUUID();
        OffsetDateTime created = OffsetDateTime.now().minusHours(1);
        OffsetDateTime updated = OffsetDateTime.now();

        UpdateProfileRequest request = new UpdateProfileRequest("Alice Johnson");
        UserProfileResponse profileResponse = new UserProfileResponse(
                userId, email, "Alice Johnson", "ACTIVE", Set.of("USER"), created, updated);

        when(userService.updateProfile(eq(email), any(UpdateProfileRequest.class)))
                .thenReturn(profileResponse);

        mockMvc.perform(put("/api/users/me")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(userId.toString()))
                .andExpect(jsonPath("$.email").value(email))
                .andExpect(jsonPath("$.fullName").value("Alice Johnson"))
                .andExpect(jsonPath("$.status").value("ACTIVE"))
                .andExpect(jsonPath("$.updatedAt").exists())
                .andExpect(jsonPath("$.passwordHash").doesNotExist());
    }

    @Test
    @DisplayName("PUT /api/users/me — unauthenticated request receives 401 Unauthorized")
    void updateCurrentUser_unauthenticated_returns401() throws Exception {
        UpdateProfileRequest request = new UpdateProfileRequest("New Name");

        mockMvc.perform(put("/api/users/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("PUT /api/users/me — invalid fullName exceeding 100 characters returns 400 Bad Request")
    void updateCurrentUser_invalidFullName_returns400() throws Exception {
        String email = "alice@truthlens.io";
        String token = generateToken(email, RoleName.USER);

        String tooLongName = "A".repeat(101);
        UpdateProfileRequest request = new UpdateProfileRequest(tooLongName);

        mockMvc.perform(put("/api/users/me")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.error").value("VALIDATION_ERROR"))
                .andExpect(jsonPath("$.message").value("Full name must not exceed 100 characters"))
                .andExpect(jsonPath("$.path").value("/api/users/me"));
    }

    @Test
    @DisplayName("PUT /api/users/me — user not found receives 404 Not Found")
    void updateCurrentUser_userNotFound_returns404() throws Exception {
        String email = "ghost@truthlens.io";
        String token = generateToken(email, RoleName.USER);

        when(userService.updateProfile(eq(email), any(UpdateProfileRequest.class)))
                .thenThrow(new UserNotFoundException("User not found with email: " + email));

        UpdateProfileRequest request = new UpdateProfileRequest("Ghost Name");

        mockMvc.perform(put("/api/users/me")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.error").value("USER_NOT_FOUND"));
    }

    @Test
    @DisplayName("PUT /api/users/me — protected fields in request body are ignored by DTO binding")
    void updateCurrentUser_protectedFieldsInPayload_areIgnored() throws Exception {
        String email = "alice@truthlens.io";
        String token = generateToken(email, RoleName.USER);
        UUID userId = UUID.randomUUID();
        OffsetDateTime now = OffsetDateTime.now();

        // Attempt to maliciously inject protected fields into JSON payload
        Map<String, Object> maliciousPayload = Map.of(
                "fullName", "Alice Legitimate",
                "id", UUID.randomUUID().toString(),
                "email", "hacked@evil.com",
                "status", "ADMIN",
                "roles", Set.of("ADMIN"),
                "passwordHash", "evilHash"
        );

        UserProfileResponse safeResponse = new UserProfileResponse(
                userId, email, "Alice Legitimate", "ACTIVE", Set.of("USER"), now, now);

        when(userService.updateProfile(eq(email), any(UpdateProfileRequest.class)))
                .thenAnswer(invocation -> {
                    UpdateProfileRequest req = invocation.getArgument(1);
                    // Verify only fullName is bound by the DTO
                    assertThat(req.getFullName()).isEqualTo("Alice Legitimate");
                    return safeResponse;
                });

        mockMvc.perform(put("/api/users/me")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(maliciousPayload)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value(email))
                .andExpect(jsonPath("$.fullName").value("Alice Legitimate"))
                .andExpect(jsonPath("$.status").value("ACTIVE"))
                .andExpect(jsonPath("$.roles[0]").value("USER"));

        verify(userService).updateProfile(eq(email), any(UpdateProfileRequest.class));
    }
}
