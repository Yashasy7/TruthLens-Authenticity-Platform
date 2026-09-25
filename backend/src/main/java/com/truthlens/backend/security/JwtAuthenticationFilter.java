package com.truthlens.backend.security;

import com.truthlens.backend.repository.RevokedTokenRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * HTTP filter that intercepts requests to extract, validate, and check revocation of Bearer JWT tokens.
 *
 * <p>Extends {@link OncePerRequestFilter} to guarantee a single execution per request.
 * If a valid and unrevoked JWT is extracted from the {@code Authorization: Bearer <token>} header,
 * the user's identity and authorities are stored in the Spring Security
 * {@link SecurityContextHolder}.</p>
 *
 * <p><strong>Security Requirements:</strong></p>
 * <ul>
 *   <li>Only headers starting with {@code Bearer } (case-sensitive) are processed.</li>
 *   <li>Never authenticates malformed, expired, revoked, or signature-invalid tokens.</li>
 *   <li>Tokens without a valid JTI claim are rejected.</li>
 *   <li>Never overwrites an authentication that is already established.</li>
 *   <li>Never logs token values, claims, or credentials.</li>
 *   <li>Always passes control to the next filter in the chain.</li>
 * </ul>
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthenticationFilter.class);

    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX        = "Bearer ";

    private final JwtService             jwtService;
    private final RevokedTokenRepository revokedTokenRepository;

    public JwtAuthenticationFilter(JwtService jwtService, RevokedTokenRepository revokedTokenRepository) {
        this.jwtService             = jwtService;
        this.revokedTokenRepository = revokedTokenRepository;
    }

    @Override
    protected void doFilterInternal(
            @NonNull HttpServletRequest request,
            @NonNull HttpServletResponse response,
            @NonNull FilterChain filterChain) throws ServletException, IOException {

        final String authHeader = request.getHeader(AUTHORIZATION_HEADER);

        if (authHeader != null && authHeader.startsWith(BEARER_PREFIX)) {
            final String jwt = authHeader.substring(BEARER_PREFIX.length()).trim();

            if (!jwt.isEmpty() && SecurityContextHolder.getContext().getAuthentication() == null) {
                if (jwtService.validateToken(jwt)) {
                    String jti = jwtService.extractJti(jwt);

                    if (jti == null || jti.isBlank() || revokedTokenRepository.existsByTokenIdentifier(jti)) {
                        log.debug("JWT token is revoked or lacks a valid JTI");
                    } else {
                        String email = jwtService.extractEmail(jwt);
                        List<String> roleNames = jwtService.extractRoles(jwt);

                        List<SimpleGrantedAuthority> authorities = roleNames.stream()
                                .map(SimpleGrantedAuthority::new)
                                .toList();

                        UsernamePasswordAuthenticationToken authToken =
                                new UsernamePasswordAuthenticationToken(email, null, authorities);
                        authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

                        SecurityContextHolder.getContext().setAuthentication(authToken);
                        log.debug("Successfully authenticated request for subject via JWT");
                    }
                } else {
                    log.debug("JWT validation failed for incoming request");
                }
            }
        }

        filterChain.doFilter(request, response);
    }
}
