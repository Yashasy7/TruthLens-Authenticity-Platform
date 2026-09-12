package com.truthlens.backend.dto;

/**
 * Outbound DTO returned on successful logout for Stage 8.
 *
 * <p><strong>Security contract:</strong> This DTO conveys only a client-safe
 * confirmation message. It never exposes JWT tokens, JTIs, user credentials,
 * or internal database state.</p>
 */
public class LogoutResponse {

    /** Human-readable confirmation message. */
    private String message;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public LogoutResponse() {
    }

    public LogoutResponse(String message) {
        this.message = message;
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
}
