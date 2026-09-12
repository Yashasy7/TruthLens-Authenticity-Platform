package com.truthlens.backend.security;

import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DisplayName("JwtService — unit tests")
class JwtServiceTest {

    // 256-bit test secret strictly for automated tests
    private static final String TEST_SECRET =
            "404E635266556A586E3272357538782F413F4428472B4B6250645367566B5970";
    private static final long EXPIRATION_MS = 3600000L; // 1 hour

    private JwtService jwtService;

    @BeforeEach
    void setUp() {
        jwtService = new JwtService(TEST_SECRET, EXPIRATION_MS);
    }

    private User createSampleUser(String email, UUID userId, RoleName... roleNames) {
        User user = new User(email, "hashedPassword", "Test User");
        // Set ID using reflection or construct mock user
        try {
            var idField = User.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(user, userId);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        for (RoleName rn : roleNames) {
            user.getRoles().add(new Role(rn, "Description"));
        }
        return user;
    }

    @Test
    @DisplayName("constructor — rejects null, empty, or short secret")
    void constructor_invalidSecret() {
        assertThatThrownBy(() -> new JwtService(null, EXPIRATION_MS))
                .isInstanceOf(IllegalArgumentException.class);

        assertThatThrownBy(() -> new JwtService("   ", EXPIRATION_MS))
                .isInstanceOf(IllegalArgumentException.class);

        // Secret shorter than 32 bytes (256 bits)
        assertThatThrownBy(() -> new JwtService("short-secret-key", EXPIRATION_MS))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("generateToken and validateToken — valid token returns true and extracts claims")
    void generateToken_successAndValidation() {
        UUID userId = UUID.randomUUID();
        User user = createSampleUser("alice@truthlens.io", userId, RoleName.USER, RoleName.ANALYST);

        String token = jwtService.generateToken(user);

        assertThat(token).isNotBlank();
        assertThat(jwtService.validateToken(token)).isTrue();

        // Check subject
        assertThat(jwtService.extractEmail(token)).isEqualTo("alice@truthlens.io");

        // Check userId
        assertThat(jwtService.extractUserId(token)).isEqualTo(userId);

        // Check roles are prefixed with ROLE_
        List<String> roles = jwtService.extractRoles(token);
        assertThat(roles).containsExactlyInAnyOrder("ROLE_USER", "ROLE_ANALYST");

        // Check JTI is present and extractable
        String jti = jwtService.extractJti(token);
        assertThat(jti).isNotBlank();
        assertThat(UUID.fromString(jti)).isNotNull();

        // Check expiration is extractable and in the future
        assertThat(jwtService.extractExpiration(token)).isNotNull();
    }

    @Test
    @DisplayName("generateToken — assigns unique JTI to each generated token")
    void generateToken_uniqueJti() {
        User user1 = createSampleUser("user1@truthlens.io", UUID.randomUUID(), RoleName.USER);
        User user2 = createSampleUser("user2@truthlens.io", UUID.randomUUID(), RoleName.USER);

        String token1 = jwtService.generateToken(user1);
        String token2 = jwtService.generateToken(user2);

        String jti1 = jwtService.extractJti(token1);
        String jti2 = jwtService.extractJti(token2);

        assertThat(jti1).isNotBlank();
        assertThat(jti2).isNotBlank();
        assertThat(jti1).isNotEqualTo(jti2);
    }

    @Test
    @DisplayName("validateToken — returns false for expired token")
    void validateToken_expired() {
        SecretKey key = Keys.hmacShaKeyFor(TEST_SECRET.getBytes(StandardCharsets.UTF_8));
        long now = System.currentTimeMillis();

        String expiredToken = Jwts.builder()
                .subject("bob@truthlens.io")
                .issuedAt(new Date(now - 100000))
                .expiration(new Date(now - 1000))
                .signWith(key)
                .compact();

        assertThat(jwtService.validateToken(expiredToken)).isFalse();
    }

    @Test
    @DisplayName("validateToken — returns false for token signed with a different key")
    void validateToken_invalidSignature() {
        String differentSecret =
                "999E635266556A586E3272357538782F413F4428472B4B6250645367566B9999";
        SecretKey otherKey = Keys.hmacShaKeyFor(differentSecret.getBytes(StandardCharsets.UTF_8));

        String tokenWithDifferentKey = Jwts.builder()
                .subject("carol@truthlens.io")
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + 60000))
                .signWith(otherKey)
                .compact();

        assertThat(jwtService.validateToken(tokenWithDifferentKey)).isFalse();
    }

    @Test
    @DisplayName("validateToken — returns false for malformed or null token")
    void validateToken_malformedOrNull() {
        assertThat(jwtService.validateToken(null)).isFalse();
        assertThat(jwtService.validateToken("")).isFalse();
        assertThat(jwtService.validateToken("   ")).isFalse();
        assertThat(jwtService.validateToken("invalid.token.payload")).isFalse();
        assertThat(jwtService.validateToken("not-a-jwt-at-all")).isFalse();
    }
}
