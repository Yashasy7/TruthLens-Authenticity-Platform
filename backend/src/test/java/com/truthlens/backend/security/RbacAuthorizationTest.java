package com.truthlens.backend.security;

import com.truthlens.backend.config.SecurityConfig;
import com.truthlens.backend.controller.RbacTestController;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.GlobalExceptionHandler;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.lang.reflect.Field;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Integration tests verifying Role-Based Access Control (RBAC) and method-level security — Stage 6.
 *
 * <p>Tests the complete request authorization lifecycle:</p>
 * <ul>
 *   <li>JWT extraction and validation by {@link JwtAuthenticationFilter}</li>
 *   <li>SecurityContext population with {@code ROLE_*} authorities</li>
 *   <li>Method-level security evaluation via {@code @PreAuthorize}</li>
 *   <li>Centralized exception handling for access-denied responses (HTTP 403)</li>
 *   <li>Rejection of unauthenticated requests (HTTP 401)</li>
 *   <li>Exact role matching without unapproved inheritance</li>
 * </ul>
 */
@WebMvcTest(controllers = RbacTestController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtService.class, GlobalExceptionHandler.class})
@TestPropertySource(locations = "classpath:application-test.properties")
@DisplayName("RBAC Authorization — integration tests")
class RbacAuthorizationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    private String createTokenWithRole(RoleName roleName) {
        User user = new User(roleName.name().toLowerCase() + "@truthlens.io", "hashedPassword", "Test User");
        try {
            Field idField = User.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(user, UUID.randomUUID());
        } catch (Exception e) {
            throw new RuntimeException("Failed to set user ID for test", e);
        }
        user.getRoles().add(new Role(roleName, "Test " + roleName.name() + " role"));
        return jwtService.generateToken(user);
    }

    @Test
    @DisplayName("1. Method-level security is enabled on SecurityConfig with prePostEnabled = true")
    void methodLevelSecurity_isEnabled() {
        EnableMethodSecurity annotation = SecurityConfig.class.getAnnotation(EnableMethodSecurity.class);
        assertThat(annotation).isNotNull();
        assertThat(annotation.prePostEnabled()).isTrue();
    }

    @Test
    @DisplayName("2. A valid USER JWT can access the USER endpoint")
    void validUserJwt_canAccessUserEndpoint() throws Exception {
        String token = createTokenWithRole(RoleName.USER);

        mockMvc.perform(get("/api/rbac/user")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Authorized: USER"));
    }

    @Test
    @DisplayName("3. A USER JWT cannot access the ANALYST endpoint (403 Forbidden)")
    void userJwt_cannotAccessAnalystEndpoint() throws Exception {
        String token = createTokenWithRole(RoleName.USER);

        mockMvc.perform(get("/api/rbac/analyst")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403))
                .andExpect(jsonPath("$.error").value("FORBIDDEN"))
                .andExpect(jsonPath("$.message").value("Access denied. You do not have permission to access this resource."))
                .andExpect(jsonPath("$.path").value("/api/rbac/analyst"));
    }

    @Test
    @DisplayName("4. A valid ANALYST JWT can access the ANALYST endpoint")
    void validAnalystJwt_canAccessAnalystEndpoint() throws Exception {
        String token = createTokenWithRole(RoleName.ANALYST);

        mockMvc.perform(get("/api/rbac/analyst")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Authorized: ANALYST"));
    }

    @Test
    @DisplayName("5. A MODERATOR JWT can access the MODERATOR endpoint")
    void moderatorJwt_canAccessModeratorEndpoint() throws Exception {
        String token = createTokenWithRole(RoleName.MODERATOR);

        mockMvc.perform(get("/api/rbac/moderator")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Authorized: MODERATOR"));
    }

    @Test
    @DisplayName("6. An ADMIN JWT can access the ADMIN endpoint")
    void adminJwt_canAccessAdminEndpoint() throws Exception {
        String token = createTokenWithRole(RoleName.ADMIN);

        mockMvc.perform(get("/api/rbac/admin")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Authorized: ADMIN"));
    }

    @Test
    @DisplayName("7. A RESEARCHER JWT can access the RESEARCHER endpoint")
    void researcherJwt_canAccessResearcherEndpoint() throws Exception {
        String token = createTokenWithRole(RoleName.RESEARCHER);

        mockMvc.perform(get("/api/rbac/researcher")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Authorized: RESEARCHER"));
    }

    @Test
    @DisplayName("8. A request without authentication receives 401 Unauthorized")
    void unauthenticatedRequest_receives401Unauthorized() throws Exception {
        mockMvc.perform(get("/api/rbac/user"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/rbac/admin"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("9. A request with an authenticated but unauthorized role receives 403 Forbidden")
    void authenticatedUnauthorizedRole_receives403Forbidden() throws Exception {
        // RESEARCHER attempts to access ADMIN endpoint
        String researcherToken = createTokenWithRole(RoleName.RESEARCHER);

        mockMvc.perform(get("/api/rbac/admin")
                        .header("Authorization", "Bearer " + researcherToken))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403))
                .andExpect(jsonPath("$.error").value("FORBIDDEN"))
                .andExpect(jsonPath("$.message").value("Access denied. You do not have permission to access this resource."))
                .andExpect(jsonPath("$.path").value("/api/rbac/admin"));

        // MODERATOR attempts to access ANALYST endpoint (exact role matching, no inheritance)
        String moderatorToken = createTokenWithRole(RoleName.MODERATOR);

        mockMvc.perform(get("/api/rbac/analyst")
                        .header("Authorization", "Bearer " + moderatorToken))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403))
                .andExpect(jsonPath("$.error").value("FORBIDDEN"));
    }
}
