package com.truthlens.backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Minimal Spring Security configuration for Stage 4.
 *
 * <p>This class opens the {@code /api/auth/**} endpoints so that registration
 * and login can be tested without a session or JWT. All other endpoints remain
 * locked down by default.</p>
 *
 * <p><strong>Stage boundary:</strong> this is intentionally minimal. Full RBAC
 * authorization rules, JWT filter registration, and per-role access control will
 * be added in Stage 5 once JWT infrastructure is in place.</p>
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /**
     * Security filter chain for Stage 4.
     *
     * <ul>
     *   <li>CSRF disabled — this is a stateless REST API; CSRF protection is
     *       session-based and does not apply here.</li>
     *   <li>Session creation policy STATELESS — no HTTP session is created or
     *       used; every request must be self-contained (JWT in Stage 5).</li>
     *   <li>{@code /api/auth/**} — permitted without authentication so that
     *       registration and login endpoints are reachable in Stage 4.</li>
     *   <li>All other requests — require authentication (default deny).</li>
     * </ul>
     *
     * @param http the {@link HttpSecurity} builder provided by Spring Security
     * @return the configured {@link SecurityFilterChain}
     * @throws Exception if the security configuration fails
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // Authentication endpoints are public — no token required at this stage.
                .requestMatchers("/api/auth/**").permitAll()
                // Everything else requires authentication (full RBAC rules in Stage 5).
                .anyRequest().authenticated()
            );

        return http.build();
    }
}
