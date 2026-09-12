package com.truthlens.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Inbound DTO for the {@code POST /api/auth/register} endpoint.
 *
 * <p>Carries the three fields a user must supply to create an account.
 * All validation constraints are evaluated by Spring's Bean Validation layer
 * before the request reaches {@code AuthService}.</p>
 *
 * <p><strong>Security notes:</strong></p>
 * <ul>
 *   <li>Email is stripped of surrounding whitespace by the Jackson setter so
 *       that {@code @Email} validation passes for inputs like
 *       {@code "  user@Example.com  "}. Lowercasing is then applied in the
 *       service layer for consistent storage and lookup.</li>
 *   <li>The raw password is never stored; it is hashed with BCrypt immediately
 *       after validation succeeds.</li>
 * </ul>
 */
public class RegisterRequest {

    /**
     * The user's email address.
     * Surrounding whitespace is stripped by the setter before validation.
     * Must be a well-formed email and must not exceed 255 characters.
     */
    @NotBlank(message = "Email is required")
    @Email(message = "Email must be a valid email address")
    @Size(max = 255, message = "Email must not exceed 255 characters")
    private String email;

    /**
     * The user's chosen password, supplied in plaintext over HTTPS.
     * Never persisted; BCrypt hash is stored instead.
     * Minimum 8 characters to enforce a reasonable baseline security level.
     */
    @NotBlank(message = "Password is required")
    @Size(min = 8, message = "Password must be at least 8 characters")
    private String password;

    /**
     * The user's display name. Optional; may be {@code null} or blank.
     * When provided it must not exceed 100 characters
     * (matching {@code users.full_name VARCHAR(100)} in the database).
     */
    @Size(max = 100, message = "Full name must not exceed 100 characters")
    private String fullName;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public RegisterRequest() {
    }

    public RegisterRequest(String email, String password, String fullName) {
        this.email    = email == null ? null : email.strip();
        this.password = password;
        this.fullName = fullName;
    }

    // -------------------------------------------------------------------------
    // Accessors
    // -------------------------------------------------------------------------

    public String getEmail() {
        return email;
    }

    /**
     * Strips leading/trailing whitespace from the email before Bean Validation
     * runs. Jackson calls this setter during request deserialization, so the
     * field is clean before any constraint annotation is evaluated.
     * Lowercasing is handled separately in {@code AuthService.normaliseEmail()}.
     */
    public void setEmail(String email) {
        this.email = email == null ? null : email.strip();
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }
}
