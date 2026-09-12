package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.Set;
import java.util.UUID;

/**
 * Outbound DTO returned by both {@code /api/auth/register} and
 * {@code /api/auth/login} in Stage 4.
 *
 * <p><strong>Security contract:</strong> this DTO must never include
 * {@code passwordHash} or any other credential material. Only safe,
 * non-sensitive user attributes are exposed.</p>
 *
 * <p>The {@code message} field carries a human-readable summary of the result
 * (e.g. {@code "Registration successful"}, {@code "Login successful"}).
 * The {@code token} field contains the signed JWT on successful login;
 * {@code tokenType} specifies {@code "Bearer"}. For endpoints that do not issue
 * a token (such as registration), these fields remain {@code null}.</p>
 */
public class AuthResponse {

    /** Human-readable result message. */
    private String message;

    /** The signed JWT access token (populated on successful login). */
    private String token;

    /** The token type (e.g. "Bearer"). */
    private String tokenType;

    /** The authenticated/registered user's UUID. */
    private UUID userId;

    /** The user's email address (normalised). */
    private String email;

    /** The user's display name. May be {@code null}. */
    private String fullName;

    /** The user's account status at the time of the response. */
    private String status;

    /** The names of roles currently assigned to the user. */
    private Set<String> roles;

    /** Account creation timestamp. */
    private OffsetDateTime createdAt;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public AuthResponse() {
    }

    /**
     * Constructor for responses without a JWT (e.g. registration).
     */
    public AuthResponse(String message, UUID userId, String email, String fullName,
                        String status, Set<String> roles, OffsetDateTime createdAt) {
        this(message, null, null, userId, email, fullName, status, roles, createdAt);
    }

    /**
     * Full constructor for responses with a JWT (e.g. successful login).
     */
    public AuthResponse(String message, String token, String tokenType, UUID userId,
                        String email, String fullName, String status, Set<String> roles,
                        OffsetDateTime createdAt) {
        this.message   = message;
        this.token     = token;
        this.tokenType = tokenType;
        this.userId    = userId;
        this.email     = email;
        this.fullName  = fullName;
        this.status    = status;
        this.roles     = roles;
        this.createdAt = createdAt;
    }

    // -------------------------------------------------------------------------
    // Accessors
    // -------------------------------------------------------------------------

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getToken() {
        return token;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public String getTokenType() {
        return tokenType;
    }

    public void setTokenType(String tokenType) {
        this.tokenType = tokenType;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Set<String> getRoles() {
        return roles;
    }

    public void setRoles(Set<String> roles) {
        this.roles = roles;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
