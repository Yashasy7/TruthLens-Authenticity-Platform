package com.truthlens.backend.config;

import com.truthlens.backend.security.JwtAuthenticationFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Spring Security configuration for Stage 5 & 6 — JWT Authentication & RBAC.
 *
 * <p>Secures the application with stateless JWT authentication and method-level RBAC:</p>
 * <ul>
 *   <li>{@code /api/auth/**} endpoints are publicly accessible (registration and login).</li>
 *   <li>{@link JwtAuthenticationFilter} intercepts all incoming requests to validate
 *       Bearer tokens and establish authentication in the {@code SecurityContext}.</li>
 *   <li>Method-level security is enabled with {@link EnableMethodSecurity} for role checks
 *       via {@code @PreAuthorize}.</li>
 *   <li>Unauthenticated requests to protected endpoints receive HTTP 401 Unauthorized.</li>
 *   <li>Sessions are stateless; CSRF is disabled for the REST API.</li>
 * </ul>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
    }

    /**
     * Security filter chain configuring stateless JWT authentication and authorization.
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
            .exceptionHandling(exceptions -> exceptions
                .authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED))
            )
            .authorizeHttpRequests(auth -> auth
                // Public authentication endpoints — no token required.
                .requestMatchers("/api/auth/**").permitAll()
                // All other requests require authentication.
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
