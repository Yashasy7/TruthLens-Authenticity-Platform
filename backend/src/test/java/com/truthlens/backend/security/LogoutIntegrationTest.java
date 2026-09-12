package com.truthlens.backend.security;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.controller.AuthController;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import com.truthlens.backend.repository.RevokedTokenRepository;
import com.truthlens.backend.service.AuthService;
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
import java.util.UUID;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Integration tests verifying secure logout and token revocation — Stage 8.
 *
 * <p>Tests the complete logout lifecycle:</p>
 * <ul>
 *   <li>Protection of {@code POST /api/auth/logout} (requires authentication)</li>
 *   <li>Successful revocation of active JWT</li>
 *   <li>Rejection of revoked JWTs on subsequent calls (HTTP 401)</li>
 *   <li>Preservation of public access for registration and login</li>
 * </ul>
 */
@WebMvcTest(controllers = AuthController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("Logout & Token Revocation — integration tests")
class LogoutIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @MockBean
    private AuthService authService;

    @MockBean
    private RevokedTokenRepository revokedTokenRepository;

    private String generateToken(String email) {
        User user = new User(email, "hashedPassword", "Test User");
        try {
            Field idField = User.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(user, UUID.randomUUID());
        } catch (Exception e) {
            throw new RuntimeException("Failed to set user ID for test", e);
        }
        user.getRoles().add(new Role(RoleName.USER, "Standard user"));
        return jwtService.generateToken(user);
    }

    @Test
    @DisplayName("POST /api/auth/logout — unauthenticated request returns 401 Unauthorized")
    void logout_unauthenticated_returns401() throws Exception {
        mockMvc.perform(post("/api/auth/logout"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(authService);
    }

    @Test
    @DisplayName("POST /api/auth/logout — authenticated user successfully logs out (200 OK)")
    void logout_authenticated_returns200AndRevokesToken() throws Exception {
        String email = "alice@truthlens.io";
        String token = generateToken(email);
        String jti = jwtService.extractJti(token);

        when(revokedTokenRepository.existsByTokenIdentifier(jti)).thenReturn(false);

        mockMvc.perform(post("/api/auth/logout")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Logout successful"));

        verify(authService).logout(token, email);
    }

    @Test
    @DisplayName("POST /api/auth/logout — repeated logout with revoked token returns 401 Unauthorized")
    void logout_repeatedWithRevokedToken_returns401() throws Exception {
        String email = "alice@truthlens.io";
        String token = generateToken(email);
        String jti = jwtService.extractJti(token);

        // Simulate token already recorded as revoked
        when(revokedTokenRepository.existsByTokenIdentifier(jti)).thenReturn(true);

        mockMvc.perform(post("/api/auth/logout")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(authService);
    }

    @Test
    @DisplayName("Public auth endpoints — register and login remain accessible without authentication")
    void publicEndpoints_remainAccessibleWithoutAuth() throws Exception {
        // Register without credentials returns 400 validation error (meaning it reached the controller, not 401)
        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest());

        // Login without credentials returns 400 validation error (meaning it reached the controller, not 401)
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /api/auth/logout — malformed or non-Bearer header returns 401 Unauthorized")
    void logout_malformedHeader_returns401() throws Exception {
        mockMvc.perform(post("/api/auth/logout")
                        .header("Authorization", "Token abc123xyz"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(authService);
    }
}
