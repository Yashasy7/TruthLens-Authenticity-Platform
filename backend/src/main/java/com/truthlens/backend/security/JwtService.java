package com.truthlens.backend.security;

import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.User;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.SecurityException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Date;
import java.util.List;
import java.util.UUID;

/**
 * Service responsible for JWT token generation, parsing, claim extraction,
 * and cryptographic validation for TruthLens — Stage 5.
 *
 * <p>Uses HMAC-SHA256 signing via JJWT 0.12.x. All secrets are passed through
 * configuration/environment variables and never hardcoded in source code.</p>
 *
 * <p><strong>Security Policy:</strong></p>
 * <ul>
 *   <li>JWT tokens, passwords, and signing keys are NEVER logged.</li>
 *   <li>Validation failures are logged with exception type only, omitting token payload.</li>
 *   <li>Roles in the token claim are explicitly formatted with the {@code ROLE_} prefix
 *       to match Spring Security authority expectations.</li>
 * </ul>
 */
@Service
public class JwtService {

    private static final Logger log = LoggerFactory.getLogger(JwtService.class);

    private static final String CLAIM_USER_ID = "userId";
    private static final String CLAIM_ROLES   = "roles";
    private static final String ROLE_PREFIX   = "ROLE_";

    private final SecretKey signingKey;
    private final long expirationMs;

    public JwtService(
            @Value("${truthlens.jwt.secret}") String secret,
            @Value("${truthlens.jwt.expiration-ms:86400000}") long expirationMs) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalArgumentException("JWT signing secret must not be null or blank.");
        }
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        if (keyBytes.length < 32) {
            throw new IllegalArgumentException(
                    "JWT signing secret must be at least 256 bits (32 bytes) for HMAC-SHA256.");
        }
        if (expirationMs <= 0) {
            throw new IllegalArgumentException("JWT expiration duration must be greater than zero.");
        }
        this.signingKey = Keys.hmacShaKeyFor(keyBytes);
        this.expirationMs = expirationMs;
    }

    // -------------------------------------------------------------------------
    // Token Generation
    // -------------------------------------------------------------------------

    /**
     * Generates a signed JWT access token for the authenticated user.
     *
     * <p>Standard claims:</p>
     * <ul>
     *   <li>{@code sub} — normalized email address (primary user identifier)</li>
     *   <li>{@code iat} — issuance timestamp</li>
     *   <li>{@code exp} — expiration timestamp (now + configured validity period)</li>
     * </ul>
     *
     * <p>Custom claims:</p>
     * <ul>
     *   <li>{@code userId} — String representation of the user UUID</li>
     *   <li>{@code roles} — List of strings with {@code ROLE_} prefix (e.g. {@code ["ROLE_USER"]})</li>
     * </ul>
     *
     * @param user the authenticated User entity
     * @return a compact, URL-safe JWT string
     */
    public String generateToken(User user) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expirationMs);

        List<String> roles = user.getRoles().stream()
                .map(Role::getName)
                .map(name -> ROLE_PREFIX + name.name())
                .sorted()
                .toList();

        return Jwts.builder()
                .id(UUID.randomUUID().toString())
                .subject(user.getEmail())
                .claim(CLAIM_USER_ID, user.getId().toString())
                .claim(CLAIM_ROLES, roles)
                .issuedAt(now)
                .expiration(expiryDate)
                .signWith(signingKey)
                .compact();
    }

    // -------------------------------------------------------------------------
    // Token Validation
    // -------------------------------------------------------------------------

    /**
     * Validates that the provided JWT token is well-formed, correctly signed with
     * the platform key, and not expired.
     *
     * @param token the compact JWT string to validate
     * @return {@code true} if valid; {@code false} if invalid, expired, or malformed
     */
    public boolean validateToken(String token) {
        if (token == null || token.isBlank()) {
            return false;
        }
        try {
            Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(token);
            return true;
        } catch (SecurityException ex) {
            log.debug("Invalid JWT signature");
        } catch (MalformedJwtException ex) {
            log.debug("Malformed JWT token");
        } catch (ExpiredJwtException ex) {
            log.debug("Expired JWT token");
        } catch (UnsupportedJwtException ex) {
            log.debug("Unsupported JWT token");
        } catch (IllegalArgumentException ex) {
            log.debug("JWT claims string is empty or illegal");
        } catch (JwtException ex) {
            log.debug("JWT validation failed: {}", ex.getClass().getSimpleName());
        }
        return false;
    }

    // -------------------------------------------------------------------------
    // Claim Extraction
    // -------------------------------------------------------------------------

    /**
     * Extracts the subject (user email) from the token.
     *
     * @param token the signed JWT
     * @return the subject email
     */
    public String extractEmail(String token) {
        return extractAllClaims(token).getSubject();
    }

    /**
     * Extracts the user UUID from the custom {@code userId} claim.
     *
     * @param token the signed JWT
     * @return the user UUID
     */
    public UUID extractUserId(String token) {
        String userIdStr = extractAllClaims(token).get(CLAIM_USER_ID, String.class);
        return userIdStr != null ? UUID.fromString(userIdStr) : null;
    }

    /**
     * Extracts the role names from the custom {@code roles} claim.
     *
     * @param token the signed JWT
     * @return list of role strings (with {@code ROLE_} prefix)
     */
    @SuppressWarnings("unchecked")
    public List<String> extractRoles(String token) {
        List<?> rawRoles = extractAllClaims(token).get(CLAIM_ROLES, List.class);
        if (rawRoles == null) {
            return List.of();
        }
        return rawRoles.stream()
                .map(Object::toString)
                .toList();
    }

    /**
     * Parses and returns all claims from a signed JWT.
     *
     * @param token the signed JWT
     * @return the Claims payload
     */
    public Claims extractAllClaims(String token) {
        return Jwts.parser()
                .verifyWith(signingKey)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * Extracts the unique JWT ID (jti) claim from the token.
     *
     * @param token the signed JWT
     * @return the JTI string, or null if absent
     */
    public String extractJti(String token) {
        return extractAllClaims(token).getId();
    }

    /**
     * Extracts the token expiration timestamp as an {@link OffsetDateTime}.
     *
     * @param token the signed JWT
     * @return the expiration timestamp in UTC, or null if absent
     */
    public OffsetDateTime extractExpiration(String token) {
        Date exp = extractAllClaims(token).getExpiration();
        return exp != null ? exp.toInstant().atOffset(ZoneOffset.UTC) : null;
    }
}
