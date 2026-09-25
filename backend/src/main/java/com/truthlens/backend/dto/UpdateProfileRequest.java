package com.truthlens.backend.dto;

import jakarta.validation.constraints.Size;

/**
 * Inbound DTO for updating the authenticated user's profile in Stage 7.
 *
 * <p><strong>Security contract:</strong> Only safe, editable fields are accepted.
 * Protected attributes such as {@code id}, {@code email}, {@code passwordHash},
 * {@code roles}, {@code status}, {@code createdAt}, and {@code updatedAt} are not
 * present in this DTO and cannot be altered through profile updates.</p>
 */
public class UpdateProfileRequest {

    /**
     * The user's updated display name.
     * Optional; when provided, must not exceed 100 characters to match
     * the database schema ({@code users.full_name VARCHAR(100)}).
     */
    @Size(max = 100, message = "Full name must not exceed 100 characters")
    private String fullName;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public UpdateProfileRequest() {
    }

    public UpdateProfileRequest(String fullName) {
        this.fullName = fullName;
    }

    // -------------------------------------------------------------------------
    // Accessors
    // -------------------------------------------------------------------------

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }
}
