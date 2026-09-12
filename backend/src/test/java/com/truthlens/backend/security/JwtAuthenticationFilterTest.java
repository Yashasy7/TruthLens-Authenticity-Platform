package com.truthlens.backend.security;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("JwtAuthenticationFilter — unit tests")
class JwtAuthenticationFilterTest {

    @Mock
    private JwtService jwtService;

    private JwtAuthenticationFilter filter;
    private MockHttpServletRequest request;
    private MockHttpServletResponse response;
    private MockFilterChain filterChain;

    @BeforeEach
    void setUp() {
        filter = new JwtAuthenticationFilter(jwtService);
        request = new MockHttpServletRequest();
        response = new MockHttpServletResponse();
        filterChain = new MockFilterChain();
        SecurityContextHolder.clearContext();
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("valid Bearer token sets SecurityContext with subject and authorities")
    void validBearerToken_setsSecurityContext() throws Exception {
        String token = "valid.jwt.token";
        request.addHeader("Authorization", "Bearer " + token);

        when(jwtService.validateToken(token)).thenReturn(true);
        when(jwtService.extractEmail(token)).thenReturn("user@truthlens.io");
        when(jwtService.extractRoles(token)).thenReturn(List.of("ROLE_USER", "ROLE_ANALYST"));

        filter.doFilter(request, response, filterChain);

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        assertThat(auth).isNotNull();
        assertThat(auth.getPrincipal()).isEqualTo("user@truthlens.io");
        assertThat(auth.getAuthorities())
                .extracting("authority")
                .containsExactlyInAnyOrder("ROLE_USER", "ROLE_ANALYST");
    }

    @Test
    @DisplayName("missing Authorization header does not authenticate and proceeds filter chain")
    void missingAuthorizationHeader_doesNotAuthenticate() throws Exception {
        filter.doFilter(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verifyNoInteractions(jwtService);
    }

    @Test
    @DisplayName("non-Bearer header does not authenticate and proceeds filter chain")
    void nonBearerHeader_doesNotAuthenticate() throws Exception {
        request.addHeader("Authorization", "Basic dXNlcjpwYXNz");

        filter.doFilter(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verifyNoInteractions(jwtService);
    }

    @Test
    @DisplayName("invalid token does not authenticate and proceeds filter chain")
    void invalidToken_doesNotAuthenticate() throws Exception {
        String token = "invalid.token";
        request.addHeader("Authorization", "Bearer " + token);

        when(jwtService.validateToken(token)).thenReturn(false);

        filter.doFilter(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verify(jwtService).validateToken(token);
    }

    @Test
    @DisplayName("expired token does not authenticate and proceeds filter chain")
    void expiredToken_doesNotAuthenticate() throws Exception {
        String token = "expired.token";
        request.addHeader("Authorization", "Bearer " + token);

        when(jwtService.validateToken(token)).thenReturn(false);

        filter.doFilter(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verify(jwtService).validateToken(token);
    }

    @Test
    @DisplayName("existing authentication is not overwritten by new Bearer token")
    void existingAuthentication_isNotOverwritten() throws Exception {
        Authentication existingAuth = new UsernamePasswordAuthenticationToken(
                "existingUser", null, List.of(new SimpleGrantedAuthority("ROLE_USER")));
        SecurityContextHolder.getContext().setAuthentication(existingAuth);

        request.addHeader("Authorization", "Bearer some.new.token");

        filter.doFilter(request, response, filterChain);

        // SecurityContext should still hold the original existing authentication
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isSameAs(existingAuth);
        verifyNoInteractions(jwtService);
    }
}
