package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.Set;
import java.util.UUID;

/**
 * Outbound DTO representing a safe user profile for Stage 7.
 *
 * <p><strong>Security contract:</strong> This DTO exposes only non-sensitive
 * user attributes. It must never expose {@code passwordHash}, JWT credentials,
 * or internal security fields.</p>
 */
public class UserProfileResponse {

    /** The user's unique identifier. */
    private UUID id;

    /** The user's email address. */
    private String email;

    /** The user's display name. May be {@code null}. */
    private String fullName;

    /** The user's account lifecycle status (e.g. {@code "ACTIVE"}). */
    private String status;

    /** The names of roles assigned to the user. */
    private Set<String> roles;

    /** Account creation timestamp. */
    private OffsetDateTime createdAt;

    /** Account last-updated timestamp. */
    private OffsetDateTime updatedAt;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public UserProfileResponse() {
    }

    public UserProfileResponse(UUID id, String email, String fullName, String status,
                               Set<String> roles, OffsetDateTime createdAt, OffsetDateTime updatedAt) {
        this.id        = id;
        this.email     = email;
        this.fullName  = fullName;
        this.status    = status;
        this.roles     = roles;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    // -------------------------------------------------------------------------
    // Accessors
    // -------------------------------------------------------------------------

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
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

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
