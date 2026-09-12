package com.truthlens.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Inbound DTO for the {@code POST /api/auth/login} endpoint.
 *
 * <p>Carries the credentials a user must supply to authenticate.
 * Email is normalised in the service layer (trim + lowercase) before any
 * lookup, consistent with registration normalisation.</p>
 */
public class LoginRequest {

    /**
     * The user's email address.
     * Must be a well-formed email string.
     */
    @NotBlank(message = "Email is required")
    @Email(message = "Email must be a valid email address")
    @Size(max = 255, message = "Email must not exceed 255 characters")
    private String email;

    /**
     * The user's password supplied in plaintext over HTTPS.
     * Verified against the stored BCrypt hash using {@code PasswordEncoder.matches()}.
     */
    @NotBlank(message = "Password is required")
    private String password;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public LoginRequest() {
    }

    public LoginRequest(String email, String password) {
        this.email    = email == null ? null : email.strip();
        this.password = password;
    }

    // -------------------------------------------------------------------------
    // Accessors
    // -------------------------------------------------------------------------

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email == null ? null : email.strip();
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }
}
